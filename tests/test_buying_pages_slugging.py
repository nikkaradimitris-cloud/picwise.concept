from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages.slugging import normalize_keyword_text, slugify_keyword  # noqa: E402


class BuyingPagesSluggingTests(unittest.TestCase):
    def test_slug_generation_is_deterministic(self) -> None:
        source = "Power   Bank 20000mAh for iPhone!!"
        self.assertEqual(slugify_keyword(source), "power-bank-20000mah-for-iphone")
        self.assertEqual(slugify_keyword(source), "power-bank-20000mah-for-iphone")

    def test_duplicate_aliases_normalize_to_same_key(self) -> None:
        alias_a = normalize_keyword_text("Dash-Cam   Gia Taxi")
        alias_b = normalize_keyword_text("dash cam gia taxi")
        self.assertEqual(alias_a, alias_b)

    def test_unicode_normalization_is_stable(self) -> None:
        self.assertEqual(
            normalize_keyword_text("Kompiouteráki Casio gia Panellinies"),
            "kompiouteraki casio gia panellinies",
        )


if __name__ == "__main__":
    unittest.main()
