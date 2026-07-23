"""Tests for download functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from conftest import mod


class TestViirsDownloaderInit:
    """Tests for ViirsDownloader initialization."""

    def test_default_init(self, tmp_path):
        dl = mod.ViirsDownloader(output_dir=str(tmp_path))
        assert dl.output_dir == tmp_path
        assert dl.timeout == 120
        assert dl.chunk_size == 8192

    def test_custom_timeout(self, tmp_path):
        dl = mod.ViirsDownloader(output_dir=str(tmp_path), timeout=60)
        assert dl.timeout == 60

    def test_custom_chunk_size(self, tmp_path):
        dl = mod.ViirsDownloader(output_dir=str(tmp_path), chunk_size=4096)
        assert dl.chunk_size == 4096

    def test_creates_output_dir(self, tmp_path):
        new_dir = tmp_path / "subdir"
        dl = mod.ViirsDownloader(output_dir=str(new_dir))
        assert new_dir.exists()

    def test_session_has_user_agent(self, tmp_path):
        dl = mod.ViirsDownloader(output_dir=str(tmp_path))
        assert "viirs-nightlights-downloader" in dl.session.headers.get("User-Agent", "")

    def test_close(self, tmp_path):
        dl = mod.ViirsDownloader(output_dir=str(tmp_path))
        dl.session = MagicMock()
        dl.close()
        dl.session.close.assert_called_once()


class TestCheckUrl:
    """Tests for check_url method."""

    def test_check_url_success(self, downloader):
        with patch.object(downloader.session, "head") as mock_head:
            mock_head.return_value = MagicMock(status_code=200)
            assert downloader.check_url("https://example.com/file.tif") is True

    def test_check_url_failure_404(self, downloader):
        with patch.object(downloader.session, "head") as mock_head:
            mock_head.return_value = MagicMock(status_code=404)
            assert downloader.check_url("https://example.com/missing.tif") is False

    def test_check_url_exception(self, downloader):
        with patch.object(downloader.session, "head") as mock_head:
            mock_head.side_effect = Exception("Connection error")
            assert downloader.check_url("https://example.com/file.tif") is False


class TestDownload:
    """Tests for download method."""

    def test_download_success(self, downloader, tmp_path, mock_response):
        url = "https://example.com/VNL_annual_2023.tif.gz"
        with patch.object(downloader.session, "get", return_value=mock_response):
            result = downloader.download(url)
            assert result.exists()
            assert result.name == "VNL_annual_2023.tif.gz"
            assert result.read_bytes() == b"x" * 512 + b"y" * 512

    def test_download_no_part_file_left(self, downloader, tmp_path, mock_response):
        url = "https://example.com/test.tif.gz"
        with patch.object(downloader.session, "get", return_value=mock_response):
            downloader.download(url)
            part_files = list(tmp_path.glob("*.part"))
            assert len(part_files) == 0

    def test_download_custom_filename(self, downloader, tmp_path, mock_response):
        url = "https://example.com/somefile.tif.gz"
        with patch.object(downloader.session, "get", return_value=mock_response):
            result = downloader.download(url, filename="custom.tif.gz")
            assert result.name == "custom.tif.gz"

    def test_download_skip_existing(self, downloader, tmp_path):
        existing = tmp_path / "existing.tif.gz"
        existing.write_bytes(b"existing data")
        url = "https://example.com/existing.tif.gz"
        result = downloader.download(url)
        assert result.read_bytes() == b"existing data"

    def test_download_force_overwrite(self, downloader, tmp_path, mock_response):
        existing = tmp_path / "existing.tif.gz"
        existing.write_bytes(b"old data")
        url = "https://example.com/existing.tif.gz"
        with patch.object(downloader.session, "get", return_value=mock_response):
            result = downloader.download(url, force=True)
            assert result.read_bytes() != b"old data"

    def test_download_cleans_part_on_error(self, downloader, tmp_path):
        url = "https://example.com/fail.tif.gz"
        with patch.object(downloader.session, "get", side_effect=Exception("Network error")):
            with pytest.raises(Exception, match="Network error"):
                downloader.download(url)
            part_files = list(tmp_path.glob("*.part"))
            assert len(part_files) == 0

    def test_download_filename_from_url(self, downloader, tmp_path, mock_response):
        url = "https://example.com/path/to/data.tif.gz?token=abc"
        with patch.object(downloader.session, "get", return_value=mock_response):
            result = downloader.download(url)
            assert result.name == "data.tif.gz"

    def test_download_empty_content_length(self, downloader, tmp_path):
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {}
        resp.iter_content.return_value = [b"data"]
        resp.raise_for_status = MagicMock()
        with patch.object(downloader.session, "get", return_value=resp):
            result = downloader.download("https://example.com/file.tif")
            assert result.exists()


class TestDownloadResource:
    """Tests for download_resource method."""

    def test_download_annual_resource(self, downloader, tmp_path, mock_response):
        with patch.object(downloader, "download", return_value=tmp_path / "VNL_annual_2023.tif.gz") as mock_dl:
            result = downloader.download_resource("annual", 2023)
            mock_dl.assert_called_once()
            call_args = mock_dl.call_args
            assert "2023" in call_args[0][0]

    def test_download_monthly_resource(self, downloader, tmp_path, mock_response):
        with patch.object(downloader, "download", return_value=tmp_path / "VNL_monthly_2023_06.tif.gz") as mock_dl:
            result = downloader.download_resource("monthly", 2023, month=6)
            mock_dl.assert_called_once()

    def test_download_monthly_no_month_raises(self, downloader):
        with pytest.raises(ValueError, match="month is required"):
            downloader.download_resource("monthly", 2023)

    def test_download_resource_with_bbox(self, downloader, tmp_path):
        with patch.object(downloader, "download", return_value=tmp_path / "file.tif.gz") as mock_dl:
            downloader.download_resource("annual", 2023, bbox=(100.0, 20.0, 120.0, 40.0))
            call_args = mock_dl.call_args
            assert "bbox" in call_args[1] or "bbox" in str(call_args)

    def test_download_resource_invalid_product(self, downloader):
        with pytest.raises(ValueError, match="Unknown product"):
            downloader.download_resource("weekly", 2023)
