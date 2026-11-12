"""The category detector's term patterns are made once, not on every search.

Measured 2026-11-10 (the audit): a search asked about 1,700 of the vocabulary's terms
through `re.search` with a pattern built on the fly; `re` keeps 512 patterns, so about
1,400 were compiled again on every search, some 60 ms of each one.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.category_detector import _contains_term, _term_pattern, detect_category  # noqa: E402


class TermPatternTests(unittest.TestCase):
    def test_a_term_is_found_as_a_whole_word_or_phrase_only(self) -> None:
        cases = (
            ("power bank 20000mah", "power bank", True),
            ("a powerbank for travel", "power bank", False),
            ("laptops", "laptop", False),
            ("usb-c cable", "usb-c", True),
            ("c++ book", "c++", True),
            ("tv stand", "tv", True),
            ("tvs", "tv", False),
            ("", "tv", False),
        )
        for text, term, expected in cases:
            with self.subTest(text=text, term=term):
                self.assertIs(_contains_term(text, term), expected)
                # As the pattern built on the fly read it, before it was kept.
                self.assertIs(bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text)), expected)

    def test_a_pattern_is_made_once_for_each_term(self) -> None:
        _term_pattern.cache_clear()
        _contains_term("kettle 1.7l", "kettle")
        _contains_term("another kettle", "kettle")
        info = _term_pattern.cache_info()
        self.assertEqual(info.misses, 1)
        self.assertEqual(info.hits, 1)

    def test_a_second_search_compiles_no_pattern(self) -> None:
        first = detect_category("washing machine 9kg")
        made = _term_pattern.cache_info().misses
        self.assertGreater(made, 0)
        second = detect_category("washing machine 9kg")
        self.assertEqual(first, second)
        self.assertEqual(_term_pattern.cache_info().misses, made)


if __name__ == "__main__":
    unittest.main()
