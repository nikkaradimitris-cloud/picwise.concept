from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages.fixtures import load_seed_buying_pages  # noqa: E402
from picwise_surface.buying_page import render_buying_page_surface  # noqa: E402


class BuyingPageSurfaceTemplateTests(unittest.TestCase):
    def test_surface_renders_main_keyword_and_4_cards(self) -> None:
        page = load_seed_buying_pages()[0]
        html = render_buying_page_surface(page)
        self.assertIn(page.main_keyword, html)
        self.assertEqual(html.count('<article class="pw-card'), 4)

    def test_surface_renders_exactly_one_recommended_marker(self) -> None:
        html = render_buying_page_surface(load_seed_buying_pages()[0])
        self.assertEqual(html.count("Recommended by PickWise"), 1)

    def test_surface_includes_faq_related_searches_and_last_updated(self) -> None:
        page = load_seed_buying_pages()[0]
        html = render_buying_page_surface(page)
        self.assertIn("<h3>FAQ</h3>", html)
        self.assertIn("<h3>Related searches</h3>", html)
        self.assertIn("Last updated:", html)

    def test_topbar_order_matches_required_sequence(self) -> None:
        html = render_buying_page_surface(load_seed_buying_pages()[0])
        login_at = html.index("Login")
        register_at = html.index("Register")
        info_at = html.index("What is Picwise")
        self.assertLess(login_at, register_at)
        self.assertLess(register_at, info_at)

    def test_surface_does_not_include_recommended_ring_or_drop_shadow_classes(self) -> None:
        html = render_buying_page_surface(load_seed_buying_pages()[0])
        for forbidden in ("pw-rec-ring", "pw-rec-ring-a", "pw-rec-ring-b", "pw-rec-ring-c"):
            self.assertNotIn(forbidden, html)
        self.assertNotIn("drop-shadow", html)
        self.assertNotIn("box-shadow", html)


if __name__ == "__main__":
    unittest.main()
