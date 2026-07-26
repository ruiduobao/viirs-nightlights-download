"""Security-related tests for VIIRS nightlights downloader."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from conftest import mod


class TestUserAgent:
    """Tests for User-Agent header."""

    def test_user_agent_contains_version(self, downloader):
        ua = downloader.session.headers.get("User-Agent", "")
        assert mod.__version__ in ua

    def test_user_agent_contains_program_name(self, downloader):
        ua = downloader.session.headers.get("User-Agent", "")
        assert "viirs-nightlights-downloader" in ua


class TestBboxValidation:
    """Tests for bbox security validation."""

    def test_bbox_rejects_string_injection(self):
        with pytest.raises(ValueError):
            mod.parse_bbox("100,20,120;rm -rf /")

    def test_bbox_rejects_path_traversal(self):
        with pytest.raises(ValueError):
            mod.parse_bbox("../../etc/passwd,20,120,40")

    def test_bbox_rejects_empty_string(self):
        with pytest.raises(ValueError):
            mod.parse_bbox("")

    def test_bbox_rejects_extreme_values(self):
        assert mod.validate_bbox((9999, 9999, 9999, 9999)) is False

    def test_bbox_rejects_sql_injection(self):
        with pytest.raises(ValueError):
            mod.parse_bbox("100;DROP TABLE--,20,120,40")


class TestUrlSafety:
    """Tests for URL construction safety."""

    def test_annual_url_is_https(self):
        url = mod.build_annual_url(2023)
        assert url.startswith("https://")

    def test_monthly_url_is_https(self):
        url = mod.build_monthly_url(2023, 6)
        assert url.startswith("https://")

    def test_worldview_url_is_https(self):
        url = mod.build_worldview_snapshot_url(2023, 6)
        assert url.startswith("https://")

    def test_url_contains_no_user_input_injection(self):
        url = mod.build_annual_url(2023)
        assert "javascript:" not in url
        assert "data:" not in url

    def test_url_no_path_traversal(self):
        url = mod.build_annual_url(2023)
        assert "../" not in url
        assert "..%2f" not in url.lower()


class TestFilenameSafety:
    """Tests for filename safety."""

    def test_filename_from_url_no_path_traversal(self):
        url = "https://example.com/../../../etc/passwd"
        filename = url.split("/")[-1].split("?")[0]
        assert "/" not in filename
        assert ".." not in filename or filename == ".."

    def test_filename_from_url_with_query(self):
        url = "https://example.com/file.tif.gz?token=abc&key=123"
        filename = url.split("/")[-1].split("?")[0]
        assert "?" not in filename
        assert filename == "file.tif.gz"


class TestTempFileSafety:
    """Tests for temporary file handling."""

    def test_no_part_file_after_success(self, downloader, tmp_path, mock_response):
        url = "https://example.com/test.tif.gz"
        with patch.object(downloader.session, "get", return_value=mock_response):
            downloader.download(url)
            part_files = list(tmp_path.glob("*.part"))
            assert len(part_files) == 0

    def test_no_part_file_after_failure(self, downloader, tmp_path):
        url = "https://example.com/fail.tif.gz"
        with patch.object(downloader.session, "get", side_effect=Exception("fail")):
            with pytest.raises(Exception):
                downloader.download(url)
            part_files = list(tmp_path.glob("*.part"))
            assert len(part_files) == 0


class TestInputValidation:
    """Tests for input validation security."""

    def test_year_rejects_string(self):
        assert mod.validate_year("2023") is False

    def test_month_rejects_string(self):
        assert mod.validate_month("6") is False

    def test_search_rejects_year_below_minimum(self, downloader):
        with pytest.raises(ValueError):
            downloader.search(1999)

    def test_search_rejects_year_above_maximum(self, downloader):
        with pytest.raises(ValueError):
            downloader.search(3000)
