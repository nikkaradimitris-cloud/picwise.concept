"""The cap's two limits set on the server (owner, 2026-11-19: «Οι κανόνες αυτοί πρέπει να
είναι μεταβαλλόμενοι ... φτιάξε λοιπόν όριο 15%. Και μέγιστο όριο ανά κατηγορία»): the share
and the most a category keeps are read from the server's settings, a value that cannot be
read keeps the default, and a category never keeps more than its most, whatever the share.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from picwise_providers.catalogue_balance import CAP_SHARE, CATEGORY_MAX, cap_limits  # noqa: E402


class CapLimitsTests(unittest.TestCase):
    def test_the_defaults(self) -> None:
        self.assertEqual(cap_limits({}), (CAP_SHARE, CATEGORY_MAX))
        self.assertEqual((CAP_SHARE, CATEGORY_MAX), (0.15, 12000))

    def test_the_server_sets_them(self) -> None:
        self.assertEqual(cap_limits({"PICWISE_CAP_SHARE": "0.2", "PICWISE_CAP_CATEGORY_MAX": "20000"}), (0.2, 20000))
        self.assertEqual(cap_limits({"PICWISE_CAP_CATEGORY_MAX": "0"}), (0.15, None))

    def test_a_value_that_cannot_be_read_keeps_the_default(self) -> None:
        self.assertEqual(cap_limits({"PICWISE_CAP_SHARE": "fifteen", "PICWISE_CAP_CATEGORY_MAX": "lots"}), (0.15, 12000))
        self.assertEqual(cap_limits({"PICWISE_CAP_SHARE": "0"}), (0.15, 12000))
        self.assertEqual(cap_limits({"PICWISE_CAP_SHARE": "1.5"}), (0.15, 12000))


if __name__ == "__main__":
    unittest.main()
