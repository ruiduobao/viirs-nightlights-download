"""Shared test fixtures for VIIRS nightlights downloader tests."""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Load viirs-nightlights-download.py as a module with underscore name
MODULE_PATH = Path(__file__).parent.parent / "viirs-nightlights-download.py"
spec = importlib.util.spec_from_file_location("viirs_nightlights_download", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
sys.modules["viirs_nightlights_download"] = mod


@pytest.fixture
def downloader(tmp_path):
    """Create a ViirsDownloader instance with temp output directory."""
    return mod.ViirsDownloader(output_dir=str(tmp_path))


@pytest.fixture
def mock_session():
    """Create a mock requests session."""
    session = MagicMock()
    session.headers = {}
    return session


@pytest.fixture
def mock_response():
    """Create a mock response with streaming content."""
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {"content-length": "1024"}
    resp.iter_content.return_value = [b"x" * 512, b"y" * 512]
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture
def sample_search_result():
    """Sample search result data."""
    return {
        "year": 2023,
        "product": "annual",
        "month": None,
        "url": "https://eogdata.mines.edu/products/vnl/v2/2023/annual/VNL_v2_npp-j2023_vcmslcfg_v2_c202303062300.average_masked.dat.tif.gz",
        "filename": "VNL_annual_2023.tif.gz",
    }


@pytest.fixture
def valid_bbox():
    """Valid bounding box: (west, south, east, north)."""
    return (100.0, 20.0, 120.0, 40.0)


@pytest.fixture
def bbox_str():
    """Valid bounding box string."""
    return "100,20,120,40"
