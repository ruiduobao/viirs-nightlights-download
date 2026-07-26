"""test_place_resolver.py — Tests for place_resolver used by viirs-nightlights-download."""

import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

from place_resolver import (  # noqa: E402
    HARDCODED_BBOXES,
    PRESETS,
    format_bbox,
    get_preset,
    list_presets,
    resolve_place,
    PlaceNotFoundError,
)


class TestResolvePlace(unittest.TestCase):
    def test_china(self):
        self.assertEqual(resolve_place("中国"), (73.0, 18.0, 135.0, 54.0))

    def test_beijing(self):
        self.assertEqual(resolve_place("北京"), (115.7, 39.4, 116.8, 40.3))

    def test_alias(self):
        self.assertEqual(resolve_place("北京市"), resolve_place("北京"))

    def test_english(self):
        self.assertEqual(resolve_place("china"), (73.0, 18.0, 135.0, 54.0))

    def test_unknown(self):
        with self.assertRaises(PlaceNotFoundError):
            resolve_place("不存在的地点xyz", use_nominatim=False)


class TestPresets(unittest.TestCase):
    def test_china_lights(self):
        p = get_preset("china-lights")
        self.assertEqual(p["product"], "annual")
        self.assertEqual(p["bbox"], (73.0, 18.0, 135.0, 54.0))

    def test_beijing_lights(self):
        p = get_preset("beijing-lights")
        self.assertEqual(p["bbox"], (115.7, 39.4, 116.8, 40.3))

    def test_unknown_preset(self):
        with self.assertRaises(ValueError):
            get_preset("not-a-preset")

    def test_list_presets(self):
        text = list_presets()
        self.assertIn("china-lights", text)
        self.assertIn("beijing-lights", text)


class TestFormatBbox(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(format_bbox((1.0, 2.0, 3.0, 4.0)), "1.0 2.0 3.0 4.0")


class TestAllBboxesValid(unittest.TestCase):
    def test(self):
        for k, b in HARDCODED_BBOXES.items():
            self.assertEqual(len(b), 4, k)
            w, s, e, n = b
            self.assertLess(w, e)
            self.assertLess(s, n)


if __name__ == "__main__":
    unittest.main(verbosity=2)
