from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages.seo_slug_builder import build_buying_page_slug  # noqa: E402


class PickWiseStage37SlugBuilderTests(unittest.TestCase):
    def test_slug_builder_is_deterministic_and_safe(self) -> None:
        first = build_buying_page_slug("quiet tyres 195 65 r15")
        second = build_buying_page_slug("quiet tyres 195 65 r15")
        self.assertTrue(first.valid)
        self.assertEqual(first.slug, "quiet-tyres-195-65-r15")
        self.assertEqual(first.slug, second.slug)
        self.assertEqual(first.canonical_path, "/best/quiet-tyres-195-65-r15")

    def test_slug_builder_strips_unsafe_characters(self) -> None:
        result = build_buying_page_slug("Best@@@ Tyres ### 205/55 R16!!!")
        self.assertTrue(result.valid)
        self.assertEqual(result.slug, "best-tyres-205-55-r16")

    def test_slug_builder_blocks_empty_or_too_short(self) -> None:
        empty = build_buying_page_slug("   ")
        tiny = build_buying_page_slug("a")
        self.assertFalse(empty.valid)
        self.assertEqual(empty.reason_code, "empty_slug_after_normalization")
        self.assertFalse(tiny.valid)
        self.assertEqual(tiny.reason_code, "slug_too_short")

    def test_slug_builder_blocks_reserved_routes(self) -> None:
        result = build_buying_page_slug("search")
        self.assertFalse(result.valid)
        self.assertEqual(result.reason_code, "reserved_slug")


if __name__ == "__main__":
    unittest.main()
