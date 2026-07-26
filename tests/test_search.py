"""Tests for search functionality."""

import pytest

from conftest import mod


class TestValidateYear:
    """Tests for validate_year function."""

    def test_valid_year_2012(self):
        assert mod.validate_year(2012) is True

    def test_valid_year_2024(self):
        assert mod.validate_year(2024) is True

    def test_valid_year_2020(self):
        assert mod.validate_year(2020) is True

    def test_invalid_year_too_low(self):
        assert mod.validate_year(2011) is False

    def test_invalid_year_too_high(self):
        assert mod.validate_year(2025) is False

    def test_invalid_year_zero(self):
        assert mod.validate_year(0) is False

    def test_invalid_year_negative(self):
        assert mod.validate_year(-1) is False


class TestValidateMonth:
    """Tests for validate_month function."""

    def test_valid_month_1(self):
        assert mod.validate_month(1) is True

    def test_valid_month_12(self):
        assert mod.validate_month(12) is True

    def test_valid_month_6(self):
        assert mod.validate_month(6) is True

    def test_invalid_month_0(self):
        assert mod.validate_month(0) is False

    def test_invalid_month_13(self):
        assert mod.validate_month(13) is False

    def test_invalid_month_negative(self):
        assert mod.validate_month(-1) is False


class TestValidateBbox:
    """Tests for validate_bbox function."""

    def test_valid_bbox(self):
        assert mod.validate_bbox((100.0, 20.0, 120.0, 40.0)) is True

    def test_valid_bbox_global(self):
        assert mod.validate_bbox((-180.0, -90.0, 180.0, 90.0)) is True

    def test_invalid_bbox_west_ge_east(self):
        assert mod.validate_bbox((120.0, 20.0, 100.0, 40.0)) is False

    def test_invalid_bbox_south_ge_north(self):
        assert mod.validate_bbox((100.0, 40.0, 120.0, 20.0)) is False

    def test_invalid_bbox_west_out_of_range(self):
        assert mod.validate_bbox((-200.0, 20.0, 120.0, 40.0)) is False

    def test_invalid_bbox_north_out_of_range(self):
        assert mod.validate_bbox((100.0, 20.0, 120.0, 100.0)) is False

    def test_invalid_bbox_wrong_length(self):
        assert mod.validate_bbox((100.0, 20.0, 120.0)) is False


class TestParseBbox:
    """Tests for parse_bbox function."""

    def test_parse_valid_bbox(self):
        result = mod.parse_bbox("100,20,120,40")
        assert result == (100.0, 20.0, 120.0, 40.0)

    def test_parse_bbox_with_spaces(self):
        result = mod.parse_bbox(" 100 , 20 , 120 , 40 ")
        assert result == (100.0, 20.0, 120.0, 40.0)

    def test_parse_bbox_with_decimals(self):
        result = mod.parse_bbox("100.5,20.3,120.7,40.1")
        assert result == (100.5, 20.3, 120.7, 40.1)

    def test_parse_bbox_too_few_values(self):
        with pytest.raises(ValueError, match="4 comma-separated values"):
            mod.parse_bbox("100,20,120")

    def test_parse_bbox_too_many_values(self):
        with pytest.raises(ValueError, match="4 comma-separated values"):
            mod.parse_bbox("100,20,120,40,50")

    def test_parse_bbox_non_numeric(self):
        with pytest.raises(ValueError, match="numbers"):
            mod.parse_bbox("abc,20,120,40")


class TestSearch:
    """Tests for ViirsDownloader.search method."""

    def test_search_annual(self, downloader):
        results = downloader.search(2023, product="annual")
        assert len(results) == 1
        assert results[0]["year"] == 2023
        assert results[0]["product"] == "annual"
        assert results[0]["month"] is None
        assert "2023" in results[0]["url"]

    def test_search_monthly_with_month(self, downloader):
        results = downloader.search(2023, product="monthly", month=6)
        assert len(results) == 1
        assert results[0]["year"] == 2023
        assert results[0]["product"] == "monthly"
        assert results[0]["month"] == 6
        assert "202306" in results[0]["url"]

    def test_search_monthly_all_months(self, downloader):
        results = downloader.search(2023, product="monthly")
        assert len(results) == 12
        months = [r["month"] for r in results]
        assert months == list(range(1, 13))

    def test_search_invalid_year(self, downloader):
        with pytest.raises(ValueError, match="Year must be between"):
            downloader.search(2011, product="annual")

    def test_search_invalid_product(self, downloader):
        with pytest.raises(ValueError, match="Product must be one of"):
            downloader.search(2023, product="weekly")

    def test_search_year_boundary_2012(self, downloader):
        results = downloader.search(2012, product="annual")
        assert len(results) == 1

    def test_search_year_boundary_2024(self, downloader):
        results = downloader.search(2024, product="annual")
        assert len(results) == 1

    def test_search_result_has_url(self, downloader):
        results = downloader.search(2023, product="annual")
        assert results[0]["url"].startswith("https://")

    def test_search_result_has_filename(self, downloader):
        results = downloader.search(2023, product="annual")
        assert results[0]["filename"].endswith(".tif.gz")


class TestBuildUrls:
    """Tests for URL builder functions."""

    def test_build_annual_url(self):
        url = mod.build_annual_url(2023)
        assert "2023" in url
        assert "annual" in url
        assert url.endswith(".tif.gz")

    def test_build_monthly_url(self):
        url = mod.build_monthly_url(2023, 6)
        assert "202306" in url
        assert "monthly" in url
        assert url.endswith(".tif.gz")

    def test_build_monthly_url_padding(self):
        url = mod.build_monthly_url(2023, 1)
        assert "202301" in url

    def test_build_worldview_url(self):
        url = mod.build_worldview_snapshot_url(2023, 6)
        assert "2023-06-01" in url
        assert "VIIRS" in url

    def test_build_worldview_url_with_bbox(self):
        url = mod.build_worldview_snapshot_url(2023, 6, (100.0, 20.0, 120.0, 40.0))
        assert "100.0" in url
        assert "20.0" in url

    def test_build_resource_url_annual(self):
        url = mod.build_resource_url("annual", 2023)
        assert "2023" in url
        assert "annual" in url

    def test_build_resource_url_monthly(self):
        url = mod.build_resource_url("monthly", 2023, month=6)
        assert "202306" in url
        assert "monthly" in url

    def test_build_resource_url_monthly_no_month(self):
        with pytest.raises(ValueError, match="month is required"):
            mod.build_resource_url("monthly", 2023)

    def test_build_resource_url_invalid_product(self):
        with pytest.raises(ValueError, match="Unknown product"):
            mod.build_resource_url("weekly", 2023)
