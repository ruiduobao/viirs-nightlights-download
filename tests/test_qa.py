"""Tests for the --qa sidecar summary (Phase 5 optimization)."""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

import viirs_nightlights_download as vnd  # noqa: E402


def test_write_qa_summary_writes_json(tmp_path):
    """write_qa_summary should write a JSON sidecar with key fields."""
    out_path = str(tmp_path / "out.tif")
    qa_path = str(tmp_path / "run.qa.json")
    args = mock.Mock()
    args.year = 2023
    args.product = "annual"
    args.month = None
    args.preset = "china-lights"
    args.place = "北京市"
    args.output_dir = str(tmp_path)
    vnd.write_qa_summary(
        qa_path=qa_path,
        skill="viirs-nightlights-download",
        command="download",
        args=args,
        bbox=(115.4, 39.4, 116.7, 40.2),
        output_paths=[out_path],
    )
    assert os.path.exists(qa_path)
    data = json.loads(Path(qa_path).read_text(encoding="utf-8"))
    assert data["skill"] == "viirs-nightlights-download"
    assert data["command"] == "download"
    assert data["year"] == 2023
    assert data["product"] == "annual"
    assert data["preset"] == "china-lights"
    assert data["place"] == "北京市"
    assert data["bbox"] == [115.4, 39.4, 116.7, 40.2]
    assert data["output_paths"] == [out_path]
    assert "timestamp" in data
    assert "version" in data


def test_download_parser_accepts_qa_flag():
    """The download subcommand should accept --qa."""
    from argparse import Namespace
    parser = vnd.build_parser()
    # Just parse the --qa flag with a dummy year
    ns = parser.parse_args(["download", "--year", "2023", "--qa", "out.qa.json"])
    assert ns.qa == "out.qa.json"
    assert ns.year == 2023
