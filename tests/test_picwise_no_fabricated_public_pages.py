"""No public route may serve the fixture buying pages.

`picwise_buying_pages.fixtures.load_seed_buying_pages()` is deterministic test data:
brand "Picwise Demo", prices and ratings computed from the page and slot index, sellers
named "PickWise Partner N", CTAs to example.com. It was served on `/best/<slug>` and listed
in the indexable sitemap. These tests pin that it never is again, through the deployed
WSGI entrypoint (`api/index.py`) and the local server's route table.
"""
from __future__ import annotations

import io
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as deployment_app  # noqa: E402
from picwise_app.buying_routes import (  # noqa: E402
    get_buying_pages_repository,
    render_best_slug_html,
    render_buying_sitemap_xml,
)
from picwise_buying_pages import load_seed_buying_pages  # noqa: E402

_FABRICATED_RATING_RE = re.compile(r"Rating:\s*\d", flags=re.IGNORECASE)


def _call_wsgi(path: str) -> tuple[str, str]:
    captured: dict[str, str] = {}

    def start_response(status: str, _headers: list[tuple[str, str]]) -> None:
        captured["status"] = status

    body = b"".join(
        deployment_app(
            {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": path,
                "QUERY_STRING": "",
                "HTTP_HOST": "picwise.subby.cloud",
                "wsgi.url_scheme": "https",
                "wsgi.input": io.BytesIO(b""),
            },
            start_response,
        )
    )
    return captured["status"], body.decode("utf-8")


class NoFabricatedPublicPagesTests(unittest.TestCase):
    def test_public_repository_holds_no_fixture_page(self) -> None:
        self.assertEqual(get_buying_pages_repository().list_pages(), ())

    def test_sitemap_lists_no_page(self) -> None:
        xml = render_buying_sitemap_xml("https://picwise.subby.cloud")
        self.assertNotIn("<loc>", xml)
        status, body = _call_wsgi("/sitemap-buying-pages.xml")
        self.assertEqual(status, "200 OK")
        self.assertNotIn("<loc>", body)

    def test_every_seed_slug_is_not_found_on_the_deployed_entrypoint(self) -> None:
        for page in load_seed_buying_pages():
            with self.subTest(slug=page.slug):
                status, body = _call_wsgi(f"/best/{page.slug}")
                self.assertEqual(status, "404 Not Found")
                self.assertNotIn("Picwise Demo", body)
                self.assertIsNone(_FABRICATED_RATING_RE.search(body))
                route_status, _route_body = render_best_slug_html(page.slug)
                self.assertEqual(route_status, 404)

    def test_public_entry_routes_show_no_fabricated_rating_or_demo_product(self) -> None:
        for path in ("/", "/search", "/results", "/demo", "/picwise-reference"):
            with self.subTest(path=path):
                status, body = _call_wsgi(path)
                self.assertEqual(status, "200 OK")
                self.assertNotIn("Picwise Demo", body)
                self.assertIsNone(_FABRICATED_RATING_RE.search(body))


if __name__ == "__main__":
    unittest.main()
