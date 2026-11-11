"""What each page tells Google about itself (the audit, 2026-11-10; owner, the same day:
«Ζητώ διόρθωση και βελτίωση ... τις προδιαγραφές google»).

The audit found, on the live site: no canonical address on any page, while the same
pages also answer on the backup's hostname; no sitemap (`/sitemap.xml` answered 404) and
none named in `robots.txt`; no icon (`/favicon.ico` answered 404); no structured data;
one title for every search and no heading on a search's page. Pinned here, through both
route tables (`picwise_surface.seo`, `docs/PICWISE_GOOGLE_PAGES_SPEC.md` section 2):

- the seven pages Google may index each say their one address, on the site's primary
  domain whatever host answered; a search's page says none and still carries `noindex`;
- `/sitemap.xml` lists those seven addresses and nothing else, and `robots.txt` names it;
- every page carries the site's icon; the icon's files are the site's own and are served;
- the home page says who publishes the site, as schema.org data, and claims no rating,
  no review and no search box;
- a search's page is titled and headed by the search; the home page keeps its own title;
- the pages are English as written for the United Kingdom.

No page is added to Google by any of this.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unittest
from html import unescape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_surface import seo  # noqa: E402
import test_picwise_google_protection as protection  # noqa: E402
from test_picwise_google_protection import _NOINDEX, _SEARCH_PAGES, _call_wsgi, _NoFeedMixin  # noqa: E402
from test_picwise_prepared_catalogue import _PreparedMixin, _feed_rows  # noqa: E402

_ORIGIN = "https://picwise.subby.cloud"
_INDEXABLE = ("/", "/about", "/terms", "/privacy", "/cookies", "/affiliate-disclosure", "/contact")


def _canonical(body: str) -> list[str]:
    return re.findall(r'<link rel="canonical" href="([^"]*)">', body)


class OneAddressTests(_NoFeedMixin, unittest.TestCase):
    def test_each_page_google_may_index_says_its_one_address(self) -> None:
        self.assertEqual(seo.INDEXABLE_PATHS, _INDEXABLE)
        for path in _INDEXABLE:
            with self.subTest(path=path):
                status, _headers, body = _call_wsgi(path)
                self.assertEqual(status, "200 OK")
                self.assertNotIn("noindex", body)
                # On the primary domain, though the request named another host.
                self.assertEqual(_canonical(body), [_ORIGIN + path])
                self.assertIn(f'<meta property="og:url" content="{_ORIGIN + path}">', body)
                title = unescape(re.search(r"<title>(.*?)</title>", body).group(1))
                self.assertIn(f'<meta property="og:title" content="{title}">', unescape(body))

    def test_a_searchs_page_says_no_address_and_stays_out_of_google(self) -> None:
        for path, query in _SEARCH_PAGES:
            with self.subTest(path=path, query=query):
                _status, _headers, body = _call_wsgi(path, query)
                self.assertIn(_NOINDEX, body)
                self.assertEqual(_canonical(body), [])
                self.assertNotIn("application/ld+json", body)
        _status, _headers, demo = _call_wsgi("/demo")
        self.assertEqual(_canonical(demo), [])
        status, _headers, missing = _call_wsgi("/no-such-page")
        self.assertEqual(status, "404 Not Found")
        self.assertEqual(_canonical(missing), [])

    def test_another_origin_is_named_without_changing_code(self) -> None:
        saved = os.environ.get(seo.CANONICAL_ORIGIN_ENV)
        self.addCleanup(
            lambda: os.environ.pop(seo.CANONICAL_ORIGIN_ENV, None)
            if saved is None
            else os.environ.__setitem__(seo.CANONICAL_ORIGIN_ENV, saved)
        )
        os.environ[seo.CANONICAL_ORIGIN_ENV] = "https://picwise.example/"
        self.assertEqual(seo.canonical_url("/about"), "https://picwise.example/about")
        # Only a plain https origin is taken: anything else leaves the primary domain.
        for wrong in ("http://picwise.example", "https://picwise.example/uk", 'https://x"><script>', "picwise.example"):
            os.environ[seo.CANONICAL_ORIGIN_ENV] = wrong
            self.assertEqual(seo.canonical_url("/about"), _ORIGIN + "/about")


class SitemapTests(_NoFeedMixin, unittest.TestCase):
    def test_the_sitemap_lists_the_pages_google_may_index_and_nothing_else(self) -> None:
        status, headers, body = _call_wsgi("/sitemap.xml")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "application/xml; charset=utf-8")
        self.assertTrue(body.startswith('<?xml version="1.0" encoding="UTF-8"?>'))
        self.assertEqual(re.findall(r"<loc>(.*?)</loc>", body), [_ORIGIN + path for path in _INDEXABLE])
        self.assertNotIn("lastmod", body)
        self.assertNotIn("/search", body)
        # Each address it lists is a page that says that address of itself.
        for address in re.findall(r"<loc>(.*?)</loc>", body):
            _status, _headers, page = _call_wsgi(address.removeprefix(_ORIGIN))
            self.assertEqual(_canonical(page), [address])

    def test_robots_txt_names_the_sitemap(self) -> None:
        _status, _headers, body = _call_wsgi("/robots.txt")
        self.assertIn(f"Sitemap: {_ORIGIN}/sitemap.xml\n", body)
        self.assertNotIn("Disallow: /sitemap", body)
        self.assertNotIn("Disallow: /search", body)


class IconTests(_NoFeedMixin, unittest.TestCase):
    def test_every_page_carries_the_sites_icon(self) -> None:
        for path, query in (("/", ""), ("/search", "q=kettle"), ("/about", ""), ("/demo", ""), ("/no-such-page", "")):
            with self.subTest(path=path):
                _status, _headers, body = _call_wsgi(path, query)
                self.assertIn('<link rel="icon" href="/assets/picwise/favicon.svg" type="image/svg+xml">', body)
                self.assertIn('<link rel="apple-touch-icon" href="/assets/picwise/apple-touch-icon.png">', body)
                self.assertIn('<meta name="theme-color" content="#2f6fe4">', body)

    def test_the_icons_files_are_the_sites_own_and_are_served(self) -> None:
        for path, kind in (
            (seo.ICON_SVG_PATH, "image/svg+xml"),
            (seo.ICON_PNG_PATH, "image/png"),
            (seo.TOUCH_ICON_PATH, "image/png"),
            (seo.LARGE_ICON_PATH, "image/png"),
        ):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path.lstrip("/")).is_file())
                status, headers, _body = _call_wsgi_bytes(path)
                self.assertEqual(status, "200 OK")
                self.assertEqual(headers["Content-Type"], kind)
        manifest = json.loads((ROOT / seo.MANIFEST_PATH.lstrip("/")).read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "PicWise")
        for icon in manifest["icons"]:
            self.assertTrue((ROOT / icon["src"].lstrip("/")).is_file(), icon["src"])
        # The logo's own shapes and colours (`reference._PAGE_STYLES`, `.pw-logo`).
        svg = (ROOT / seo.ICON_SVG_PATH.lstrip("/")).read_text(encoding="utf-8")
        for colour in ("#30a0ff", "#1f6cff"):
            self.assertIn(colour, svg)


def _call_wsgi_bytes(path: str) -> tuple[str, dict[str, str], bytes]:
    from api.index import app

    held: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        held["status"], held["headers"] = status, dict(headers)

    body = b"".join(app({"REQUEST_METHOD": "GET", "PATH_INFO": path, "QUERY_STRING": "", "HTTP_HOST": "localhost"}, start_response))
    return str(held["status"]), dict(held["headers"]), body  # type: ignore[arg-type]


class WhoPublishesTests(_NoFeedMixin, unittest.TestCase):
    def test_the_home_page_says_who_publishes_the_site_and_claims_nothing_else(self) -> None:
        _status, _headers, body = _call_wsgi("/")
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', body, flags=re.S)
        self.assertEqual(len(blocks), 1)
        data = json.loads(blocks[0])
        self.assertEqual(data["@context"], "https://schema.org")
        kinds = {item["@type"]: item for item in data["@graph"]}
        self.assertEqual(set(kinds), {"Organization", "WebSite"})
        self.assertEqual(kinds["Organization"]["name"], "PicWise")
        self.assertEqual(kinds["Organization"]["url"], _ORIGIN + "/")
        self.assertEqual(kinds["Organization"]["logo"], _ORIGIN + "/assets/picwise/icon-512.png")
        self.assertEqual(kinds["WebSite"]["inLanguage"], "en-GB")
        self.assertEqual(kinds["WebSite"]["publisher"], {"@id": kinds["Organization"]["@id"]})
        # No rating, no review, no offer, no search box: PicWise invents none.
        for word in ("Rating", "Review", "Offer", "SearchAction", "Product"):
            self.assertNotIn(word, blocks[0])

    def test_no_other_page_carries_such_data(self) -> None:
        for path in ("/about", "/terms", "/contact"):
            _status, _headers, body = _call_wsgi(path)
            self.assertNotIn("application/ld+json", body)


class TitleAndHeadingTests(_PreparedMixin, unittest.TestCase):
    def test_a_searchs_page_is_titled_and_headed_by_the_search(self) -> None:
        self._write_feed(_feed_rows())
        page = self._page("kettle")
        self.assertIn("<title>kettle — PicWise</title>", page)
        headings = re.findall(r"<h1[^>]*>(.*?)</h1>", page, flags=re.S)
        self.assertEqual(headings, ["Results for: kettle, cheapest first"])
        self.assertIn('<h1 class="pw-query-line">', page)

    def test_a_search_with_no_answer_has_its_title_and_no_empty_heading(self) -> None:
        self._write_feed(_feed_rows())
        page = self._page("dishwasher")
        self.assertIn("<title>dishwasher — PicWise</title>", page)
        self.assertNotIn("<h1", page)

    def test_a_searchs_words_are_written_safely_and_cut_when_long(self) -> None:
        self.assertEqual(seo.search_page_title("  power   bank 20000mah "), "power bank 20000mah — PicWise")
        self.assertEqual(seo.search_page_title(""), "")
        long = seo.search_page_title("kettle " * 30)
        self.assertLessEqual(len(long), 70 + len(" — PicWise"))
        self.assertTrue(long.endswith("… — PicWise"))
        self._write_feed(_feed_rows())
        page = self._page('</title><script>alert(1)</script>')
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;/title&gt;&lt;script&gt;alert(1)&lt;/script&gt; — PicWise</title>", page)

    def test_the_home_page_keeps_its_own_title_and_heading(self) -> None:
        self._write_feed(_feed_rows())
        page = self._page("")
        self.assertIn("<title>PicWise — Find the product you want in UK shops</title>", page)
        self.assertEqual(
            re.findall(r"<h1[^>]*>(.*?)</h1>", page, flags=re.S), ["Find the product you want in UK shops"]
        )


class LanguageTests(_NoFeedMixin, unittest.TestCase):
    def test_the_pages_are_english_as_written_for_the_united_kingdom(self) -> None:
        for path, query in (("/", ""), ("/search", "q=kettle"), ("/about", ""), ("/no-such-page", "")):
            with self.subTest(path=path):
                _status, _headers, body = _call_wsgi(path, query)
                self.assertIn('<html lang="en-GB">', body)


class LocalServerBasicsTests(protection.LocalServerTests):
    """The local server answers the same (`picwise_app.app`)."""

    # The protection tests of the class this borrows its server from run in their module.
    test_every_search_page_carries_noindex = None
    test_the_home_page_and_the_demo = None
    test_robots_txt_is_the_deployments = None
    test_json_routes_are_kept_out_of_the_index = None

    def test_the_sitemap_and_robots_are_the_deployments(self) -> None:
        for path in ("/sitemap.xml", "/robots.txt"):
            status, _headers, body = self._get(path)
            self.assertEqual(status, 200)
            self.assertEqual(body, _call_wsgi(path)[2])

    def test_the_home_page_says_its_address(self) -> None:
        _status, _headers, home = self._get("/")
        self.assertEqual(_canonical(home), [_ORIGIN + "/"])
        _status, _headers, search = self._get("/search?q=kettle")
        self.assertEqual(_canonical(search), [])
        self.assertIn("<title>kettle — PicWise</title>", search)


if __name__ == "__main__":
    unittest.main()
