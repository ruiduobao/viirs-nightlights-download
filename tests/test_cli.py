"""Tests for CLI argument parsing and command dispatch."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from conftest import mod


class TestBuildParser:
    """Tests for build_parser function."""

    def test_parser_creation(self):
        parser = mod.build_parser()
        assert parser is not None

    def test_parser_prog_name(self):
        parser = mod.build_parser()
        assert parser.prog == "viirs-nightlights-download"

    def test_search_subcommand_exists(self):
        parser = mod.build_parser()
        args = parser.parse_args(["search", "--year", "2023"])
        assert args.command == "search"
        assert args.year == 2023

    def test_download_subcommand_exists(self):
        parser = mod.build_parser()
        args = parser.parse_args(["download", "--year", "2023"])
        assert args.command == "download"
        assert args.year == 2023

    def test_search_default_product(self):
        parser = mod.build_parser()
        args = parser.parse_args(["search", "--year", "2023"])
        assert args.product == "annual"

    def test_search_monthly_product(self):
        parser = mod.build_parser()
        args = parser.parse_args(["search", "--year", "2023", "--product", "monthly", "--month", "6"])
        assert args.product == "monthly"
        assert args.month == 6

    def test_download_default_output_dir(self):
        parser = mod.build_parser()
        args = parser.parse_args(["download", "--year", "2023"])
        assert args.output_dir == "."

    def test_download_custom_output_dir(self):
        parser = mod.build_parser()
        args = parser.parse_args(["download", "--year", "2023", "-o", "/tmp/out"])
        assert args.output_dir == "/tmp/out"

    def test_download_force_flag(self):
        parser = mod.build_parser()
        args = parser.parse_args(["download", "--year", "2023", "--force"])
        assert args.force is True

    def test_download_timeout(self):
        parser = mod.build_parser()
        args = parser.parse_args(["download", "--year", "2023", "--timeout", "60"])
        assert args.timeout == 60

    def test_download_bbox(self):
        parser = mod.build_parser()
        args = parser.parse_args(["download", "--year", "2023", "--bbox", "100,20,120,40"])
        assert args.bbox == "100,20,120,40"

    def test_version_flag(self):
        parser = mod.build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0

    def test_no_command(self):
        parser = mod.build_parser()
        args = parser.parse_args([])
        assert args.command is None


class TestMain:
    """Tests for main entry point."""

    def test_main_no_command_returns_1(self):
        result = mod.main([])
        assert result == 1

    def test_main_search_calls_cmd_search(self):
        with patch.object(mod, "cmd_search", return_value=0) as mock_search:
            result = mod.main(["search", "--year", "2023"])
            assert result == 0
            mock_search.assert_called_once()

    def test_main_download_calls_cmd_download(self):
        with patch.object(mod, "cmd_download", return_value=0) as mock_dl:
            result = mod.main(["download", "--year", "2023"])
            assert result == 0
            mock_dl.assert_called_once()

    def test_main_search_prints_results(self, capsys):
        result = mod.main(["search", "--year", "2023"])
        captured = capsys.readouterr()
        assert "2023" in captured.out

    def test_main_search_error_handling(self, capsys):
        result = mod.main(["search", "--year", "9999"])
        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err
