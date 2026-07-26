"""test_resolve_args.py — Tests for resolve_args() in viirs-nightlights-download."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

import viirs_nightlights_download  # noqa: E402


def make_args(**kwargs):
    defaults = dict(
        product="annual",
        bbox=None,
        place=None,
        preset=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestResolveArgs(unittest.TestCase):
    def test_bbox_wins(self):
        args = make_args(bbox="100,20,120,40", place="北京市")
        bbox, label, err = viirs_nightlights_download.resolve_args(args)
        self.assertIsNone(err)
        self.assertEqual(bbox, (100.0, 20.0, 120.0, 40.0))
        self.assertIn("--bbox", label)

    def test_place(self):
        args = make_args(place="北京市")
        bbox, label, err = viirs_nightlights_download.resolve_args(args)
        self.assertIsNone(err)
        self.assertEqual(bbox, (115.7, 39.4, 116.8, 40.3))
        self.assertIn("北京市", label)

    def test_preset_fills_bbox_and_product(self):
        args = make_args(preset="china-lights")
        bbox, label, err = viirs_nightlights_download.resolve_args(args)
        self.assertIsNone(err)
        self.assertEqual(bbox, (73.0, 18.0, 135.0, 54.0))
        self.assertEqual(args.product, "annual")  # product already 'annual' default, fine

    def test_no_extent_returns_none(self):
        args = make_args()
        bbox, label, err = viirs_nightlights_download.resolve_args(args)
        self.assertIsNone(err)
        self.assertIsNone(bbox)

    def test_place_with_yangtze(self):
        args = make_args(place="长江流域")
        bbox, label, err = viirs_nightlights_download.resolve_args(args)
        self.assertIsNone(err)
        self.assertEqual(bbox, (90.0, 24.0, 122.0, 36.0))

    def test_invalid_bbox_returns_err(self):
        args = make_args(bbox="200,20,120,40")
        bbox, label, err = viirs_nightlights_download.resolve_args(args)
        self.assertEqual(err, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
