"""The site's font, Inter, served by the site itself (owner, 2026-11-12; `picwise_surface.fonts`).

The pages had named Inter since May but never loaded it: a visitor saw the device's own
font. Now the site serves the latin part of Inter's variable font from its own address,
with the licence that goes with it.
"""
from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from picwise_app.app import ASSET_CACHE_CONTROL, CONTENT_SECURITY_POLICY  # noqa: E402
from picwise_surface.fonts import FONT_FACE_CSS, FONT_PATH, FONT_PRELOAD_HTML  # noqa: E402
from picwise_surface.legal import render_privacy_page  # noqa: E402
from picwise_surface.reference import render_picwise_reference_surface  # noqa: E402


def _get(path: str) -> tuple[str, dict[str, str], bytes]:
    answer: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        answer["status"] = status
        answer["headers"] = dict(headers)

    body = b"".join(
        wsgi_app(
            {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": path,
                "QUERY_STRING": "",
                "wsgi.input": io.BytesIO(b""),
                "wsgi.url_scheme": "https",
            },
            start_response,
        )
    )
    return str(answer["status"]), answer["headers"], body  # type: ignore[return-value]


class FontFileTests(unittest.TestCase):
    def test_the_site_serves_the_font_as_a_font_kept_a_week(self) -> None:
        status, headers, body = _get(FONT_PATH)
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "font/woff2")
        self.assertEqual(headers["Cache-Control"], ASSET_CACHE_CONTROL)
        self.assertTrue(body.startswith(b"wOF2"))
        # One small file for every weight: the first visit pays about 48 KB.
        self.assertLess(len(body), 60_000)

    def test_the_licence_goes_with_the_font(self) -> None:
        folder = ROOT / FONT_PATH.lstrip("/")
        licence = (folder.parent / "OFL.txt").read_text(encoding="utf-8")
        self.assertIn("SIL OPEN FONT LICENSE Version 1.1", licence)
        self.assertIn("The Inter Project Authors", licence)

    def test_the_security_policy_lets_the_site_load_its_own_font_only(self) -> None:
        # No font-src of its own: default-src 'self' holds, so no font service is asked.
        self.assertIn("default-src 'self';", CONTENT_SECURITY_POLICY)
        self.assertNotIn("font-src", CONTENT_SECURITY_POLICY)
        self.assertTrue(FONT_PATH.startswith("/assets/"))


class FontOnThePagesTests(unittest.TestCase):
    def test_the_search_pages_load_and_ask_early_for_the_font(self) -> None:
        for query in ("", "kettle"):
            page = render_picwise_reference_surface(query)
            self.assertIn(FONT_PRELOAD_HTML, page)
            self.assertIn(FONT_FACE_CSS, page)
            # The page's head asks for it before the style sheet that uses it.
            self.assertLess(page.index(FONT_PRELOAD_HTML), page.index("<style>"))

    def test_the_words_never_wait_for_it(self) -> None:
        self.assertIn("font-display:swap;", FONT_FACE_CSS)
        self.assertIn("font-weight:100 900;", FONT_FACE_CSS)
        self.assertIn(f'src:url({FONT_PATH}) format("woff2");', FONT_FACE_CSS)

    def test_the_info_pages_load_it_too(self) -> None:
        self.assertIn(FONT_FACE_CSS, render_privacy_page())


if __name__ == "__main__":
    unittest.main()
