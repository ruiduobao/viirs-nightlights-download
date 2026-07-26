"""Integration tests for VIIRS nightlights downloader (mocked network)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from conftest import mod


class TestSearchAndDownloadFlow:
    """Integration tests for search-then-download workflow."""

    def test_search_then_download_annual(self, downloader, tmp_path):
        results = downloader.search(2023, product="annual")
        assert len(results) == 1
        url = results[0]["url"]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"data"]
        mock_resp.raise_for_status = MagicMock()

        with patch.object(downloader.session, "get", return_value=mock_resp):
            path = downloader.download(url, results[0]["filename"])
            assert path.exists()
            assert path.name == "VNL_annual_2023.tif.gz"

    def test_search_then_download_monthly(self, downloader, tmp_path):
        results = downloader.search(2023, product="monthly", month=6)
        assert len(results) == 1
        url = results[0]["url"]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"data"]
        mock_resp.raise_for_status = MagicMock()

        with patch.object(downloader.session, "get", return_value=mock_resp):
            path = downloader.download(url, results[0]["filename"])
            assert path.exists()
            assert "monthly" in path.name

    def test_search_then_download_all_months(self, downloader, tmp_path):
        results = downloader.search(2023, product="monthly")
        assert len(results) == 12

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"data"]
        mock_resp.raise_for_status = MagicMock()

        with patch.object(downloader.session, "get", return_value=mock_resp):
            for r in results:
                path = downloader.download(r["url"], r["filename"])
                assert path.exists()

        downloaded = list(tmp_path.glob("VNL_monthly_2023_*.tif.gz"))
        assert len(downloaded) == 12


class TestMainSearchIntegration:
    """Integration tests for main search command."""

    def test_main_search_annual(self, capsys):
        result = mod.main(["search", "--year", "2023", "--product", "annual"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data) == 1
        assert data[0]["year"] == 2023

    def test_main_search_monthly(self, capsys):
        result = mod.main(["search", "--year", "2023", "--product", "monthly", "--month", "1"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data) == 1
        assert data[0]["month"] == 1

    def test_main_search_all_months(self, capsys):
        result = mod.main(["search", "--year", "2023", "--product", "monthly"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data) == 12

    def test_main_search_invalid_year(self, capsys):
        result = mod.main(["search", "--year", "2011"])
        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err


class TestMainDownloadIntegration:
    """Integration tests for main download command."""

    def test_main_download_annual(self, tmp_path):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"data"]
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.Session.get", return_value=mock_resp):
            result = mod.main(["download", "--year", "2023", "-o", str(tmp_path)])
            assert result == 0
            files = list(tmp_path.glob("*.tif.gz"))
            assert len(files) >= 1

    def test_main_download_monthly_single(self, tmp_path):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"data"]
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.Session.get", return_value=mock_resp):
            result = mod.main(["download", "--year", "2023", "--product", "monthly", "--month", "6", "-o", str(tmp_path)])
            assert result == 0

    def test_main_download_with_bbox(self, tmp_path):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"data"]
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.Session.get", return_value=mock_resp):
            result = mod.main(["download", "--year", "2023", "--bbox", "100,20,120,40", "-o", str(tmp_path)])
            assert result == 0

    def test_main_download_invalid_bbox(self, capsys):
        result = mod.main(["download", "--year", "2023", "--bbox", "200,20,120,40"])
        assert result == 1

    def test_main_download_force_flag(self, tmp_path):
        existing = tmp_path / "VNL_annual_2023.tif.gz"
        existing.write_bytes(b"old")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"new"]
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.Session.get", return_value=mock_resp):
            result = mod.main(["download", "--year", "2023", "--force", "-o", str(tmp_path)])
            assert result == 0
            assert existing.read_bytes() == b"new"

    def test_main_download_skip_existing(self, tmp_path):
        existing = tmp_path / "VNL_annual_2023.tif.gz"
        existing.write_bytes(b"original")

        result = mod.main(["download", "--year", "2023", "-o", str(tmp_path)])
        assert result == 0
        assert existing.read_bytes() == b"original"


class TestEndToEndWorkflow:
    """End-to-end workflow integration tests."""

    def test_full_workflow_search_download_verify(self, downloader, tmp_path):
        results = downloader.search(2024, product="annual")
        assert len(results) == 1
        resource = results[0]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-length": "2048"}
        mock_resp.iter_content.return_value = [b"x" * 1024, b"y" * 1024]
        mock_resp.raise_for_status = MagicMock()

        with patch.object(downloader.session, "get", return_value=mock_resp):
            path = downloader.download_resource("annual", 2024)
            assert path.exists()
            assert path.stat().st_size == 2048
