"""The store's pages other than the home page (`docs/PICWISE_HOME_STORE_SPEC.md`, section 7;
task H4): behind the home page's switch, each only once its part is built, never indexed.
"""
from __future__ import annotations

import html
import io
import json
import re
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (ROOT, ROOT / "src", HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from picwise_surface import home_store, home_store_facts, store_pages  # noqa: E402
from picwise_surface.home_store import Pick  # noqa: E402
from picwise_surface.home_store_facts import DepartmentsFacts, KindFacts  # noqa: E402


def _call(path: str, query: str = "") -> tuple[str, dict[str, str], str]:
    seen: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        seen["status"], seen["headers"] = status, dict(headers)

    body = b"".join(
        wsgi_app(
            {"REQUEST_METHOD": "GET", "PATH_INFO": path, "QUERY_STRING": query, "wsgi.input": io.BytesIO(b""),
             "wsgi.url_scheme": "https"},
            start_response,
        )
    ).decode("utf-8")
    return str(seen["status"]), seen["headers"], body  # type: ignore[return-value]


def _markup(page: str) -> str:
    page = re.sub(r"<script\b.*?</script>", "", page, flags=re.S)
    return re.sub(r"<style\b.*?</style>", "", page, flags=re.S)


def _text(page: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", _markup(page).split("<body", 1)[1])).split())


def _links(page: str) -> list[str]:
    return [html.unescape(href) for href in re.findall(r'<a\b[^>]*\bhref="([^"]*)"', _markup(page))]


def _pick(query: str, name: str) -> Pick:
    return Pick(query=query, kind=name, link=f"See {name.lower()}", title=f"Fixture {name}", price="£20.00",
                shop="Fixture Shop", image="/assets/home/art/kettle.svg")


class _On:
    def setUp(self) -> None:
        home_store.set_home_store_on_for_tests(True)
        self.addCleanup(home_store.set_home_store_on_for_tests, None)
        home_store_facts.set_kind_facts_for_tests(None)
        self.addCleanup(home_store_facts.set_kind_facts_for_tests, None)


class TheDepartmentsFileTests(unittest.TestCase):
    def test_every_department_has_its_group_and_every_kind_its_words(self) -> None:
        departments = home_store.load_departments()
        listed = [d.slug for d in home_store.load_home_lists().departments]
        grouped = [slug for group in departments.groups for slug in group.departments]
        self.assertEqual(sorted(grouped), sorted(listed))
        self.assertEqual([g.gid for g in departments.groups], ["home-kitchen", "tech-tools", "fashion", "play-sport"])
        self.assertEqual(sorted(departments.kinds), sorted(listed))
        queries = [kind.query for kinds in departments.kinds.values() for kind in kinds]
        self.assertEqual(len(queries), len(set(queries)), "a kind in two departments")
        for kinds in departments.kinds.values():
            for kind in kinds:
                self.assertTrue(kind.name and kind.query, kind)
                if kind.drawing:
                    self.assertTrue((ROOT / "assets" / "home" / "art" / f"{kind.drawing}.svg").is_file(), kind)
        # Lighting and Perfume are one kind each: no page, their search instead (7.1).
        self.assertEqual(len(departments.kinds["lighting"]), 1)
        self.assertEqual(len(departments.kinds["perfume"]), 1)


class TheSwitchTests(unittest.TestCase):
    def test_off_no_page_of_the_store_answers(self) -> None:
        home_store.set_home_store_on_for_tests(False)
        self.addCleanup(home_store.set_home_store_on_for_tests, None)
        for path in ("/departments", "/department/kitchen"):
            self.assertTrue(_call(path)[0].startswith("404"), path)


class TheDepartmentsPageTests(_On, unittest.TestCase):
    def test_four_groups_every_department_once(self) -> None:
        status, headers, page = _call("/departments")
        self.assertTrue(status.startswith("200"))
        self.assertIn('<meta name="robots" content="noindex">', page)
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        text = _text(page)
        for words in ("All departments", "From UK shops, in stock only.", "Home & kitchen", "Tech & tools", "Fashion",
                      "Play & sport"):
            self.assertIn(words, text)
        for anchor in ("home-kitchen", "tech-tools", "fashion", "play-sport"):
            self.assertIn(f'id="{anchor}"', page)
        self.assertEqual(_markup(page).count('class="pw-hs-dept"'), 13)
        links = _links(page)
        self.assertIn("/department/kitchen", links)
        self.assertIn("/search?q=lamp", links)
        self.assertIn("/search?q=perfume", links)
        self.assertNotIn("/department/lighting", links)
        # Its header has the departments' row; the footer the owner's line, no "Cookies".
        self.assertIn('class="pw-hs-nav"', page)
        self.assertIn("No Cookie Policy", page)
        self.assertNotIn("/cookies", links)


class ADepartmentsPageTests(_On, unittest.TestCase):
    def test_without_tonight_s_facts_every_kind_and_no_number(self) -> None:
        status, _headers, page = _call("/department/kitchen")
        self.assertTrue(status.startswith("200"))
        self.assertIn('<meta name="robots" content="noindex">', page)
        text = _text(page)
        self.assertIn("DEPARTMENT Kitchen From UK shops, in stock only.", text)
        self.assertIn("All kinds in Kitchen", text)
        kinds = home_store.load_departments().kinds["kitchen"]
        self.assertEqual(_markup(page).count('class="pw-hs-row"'), len(kinds))
        self.assertNotIn("products from", text)
        self.assertNotIn("pw-hs-band", _markup(page))
        # Marked in the header's row.
        self.assertIn('<a class="is-on" aria-current="page" href="/department/kitchen">', page)

    def test_tonight_s_kinds_the_most_products_first_none_empty(self) -> None:
        facts = DepartmentsFacts(
            prepared_at=None,
            kinds={
                "toaster": KindFacts(count=55, low="£14.99", pick=_pick("toaster", "Toasters")),
                "kettle": KindFacts(count=89, low="£12.74", pick=_pick("kettle", "Kettles")),
                "juicer": KindFacts(count=1, low="£30.00", pick=None),
            },
        )
        home_store_facts.set_kind_facts_for_tests(facts)
        page = _call("/department/kitchen")[2]
        markup = _markup(page)
        self.assertEqual(markup.count('class="pw-hs-row"'), 3)
        text = _text(page)
        rows = text.split("All kinds in Kitchen", 1)[1]
        self.assertLess(rows.index("Kettles 89 products from £12.74"), rows.index("Toasters 55 products from £14.99"))
        self.assertLess(rows.index("Toasters"), rows.index("Juicers 1 product from £30.00"))
        self.assertNotIn("Microwaves", rows)
        # Tiles only for kinds with a drawing; the band with the two Recommended.
        self.assertEqual(markup.count('class="pw-hs-tile"'), 2)
        self.assertIn("pw-hs-band", markup)
        self.assertEqual(markup.count('class="pw-hs-pick"'), 2)
        for href in _links(page):
            self.assertTrue(href.startswith(("/", "#")), href)

    def test_a_department_of_one_kind_or_none_has_no_page(self) -> None:
        for path in ("/department/lighting", "/department/perfume", "/department/nothing", "/department/kitchen/x"):
            self.assertTrue(_call(path)[0].startswith("404"), path)

    def test_never_presented_as_price_comparison(self) -> None:
        for path in ("/departments", "/department/kitchen"):
            self.assertNotRegex(_text(_call(path)[2]).lower(), r"compar")


import test_picwise_price_first as price_first  # noqa: E402


class TheKindFactsOnAFeedTests(price_first._PageMixin, unittest.TestCase):
    def test_count_lowest_price_and_recommended_are_the_search_s(self) -> None:
        self._serve(self._kettles([20, 30, 40, 50, 60, 70, 80, 90, 100]))
        departments = home_store.Departments(
            groups=(),
            kinds={"kitchen": (home_store.DeptKind(kind="kettle", name="Kettles", query="kettle", drawing="kettle"),
                               home_store.DeptKind(kind="snowshoe", name="Snowshoes", query="snowshoes", drawing=""))},
        )
        facts = home_store_facts.work_out_kind_facts(departments=departments, prepared_at=None)
        self.assertEqual(set(facts.kinds), {"kettle"})
        kettle = facts.kinds["kettle"]
        self.assertEqual(kettle.count, 9)
        self.assertEqual(kettle.low, "£20.00")
        self.assertIsNotNone(kettle.pick)
        self.assertEqual(kettle.pick.price, "£60.00")
        self.assertEqual(kettle.pick.link, "See kettles")


class TheFourPagesTests(_On, unittest.TestCase):
    PAGES = {
        "/how-picwise-works": ("How PicWise works", ("1 Search", "2 See", "3 Decide", "How PicWise earns",
                                                      "the commission never changes the order")),
        "/how-we-choose": ("How we choose the Recommended", ("of 45 products, the 23rd", "Two safeguards",
                                                             "When there is no Recommended", "What never counts")),
        "/our-checks": ("Our checks", ("What is checked", "When a check fails", "What a check is not")),
        "/our-shops": ("Our shops", ("run a programme with Awin",)),
    }

    def setUp(self) -> None:
        super().setUp()
        home_store_facts.set_home_facts_for_tests(None)
        self.addCleanup(home_store_facts.set_home_facts_for_tests, None)

    def test_each_answers_with_its_words_kept_from_google(self) -> None:
        for path, (title, words) in self.PAGES.items():
            status, headers, page = _call(path)
            self.assertTrue(status.startswith("200"), path)
            self.assertIn('<meta name="robots" content="noindex">', page)
            text = _text(page)
            self.assertIn(f"ABOUT PICWISE {title}", text)
            for line in words:
                self.assertIn(line, text, path)
            self.assertIn("Last updated: 24 November 2026", text)
            self.assertNotRegex(text.lower(), r"compar")
            # The other pages' header: no departments' row (the specification, 7.4).
            self.assertNotIn('class="pw-hs-nav"', page)
            for href in _links(page):
                self.assertTrue(href.startswith(("/", "#")), href)

    def test_their_links_stand_on_lines_of_their_own(self) -> None:
        page = _call("/how-picwise-works")[2]
        for href in ("/how-we-choose", "/our-checks", "/affiliate-disclosure"):
            self.assertIn(f'<a class="pw-hs-link" href="{href}">', page)
        self.assertNotRegex(_markup(page), r"<p>[^<]*<a ")

    def test_our_shops_tonight_a_to_z_and_never_a_name_that_names_no_shop(self) -> None:
        page = _call("/our-shops")[2]
        self.assertIn("PicWise shows products from UK shops.", _text(page))
        self.assertNotIn("A to Z", _text(page))
        facts = home_store.HomeFacts(prepared_at=None, shop_names=("8wines UK", "Aosom UK", "aZengear", "Geepas"), shop_count=4)
        home_store_facts.set_home_facts_for_tests(facts)
        text = _text(_call("/our-shops")[2])
        self.assertIn("PicWise shows products from 4 UK shops tonight.", text)
        self.assertIn("A to Z 0\u20139 8wines UK A Aosom UK aZengear G Geepas", text)

    def test_the_footer_names_the_four_pages(self) -> None:
        links = _links(_call("/departments")[2])
        for href in ("/how-picwise-works", "/how-we-choose", "/our-checks", "/our-shops"):
            self.assertIn(href, links)


class TheShopsTests(unittest.TestCase):
    class _Product:
        def __init__(self, name: str) -> None:
            self.raw = {"merchant_name": name}

    def test_a_name_that_names_no_shop_is_neither_listed_nor_counted(self) -> None:
        products = [self._Product(n) for n in ("Geepas Partner Program", "Shopping Ads: Google & Bing", "Tooled Up",
                                               "Tooled Up")]
        names = home_store_facts.all_shop_names(products)
        self.assertEqual(names, ("Geepas", "Tooled Up"))
        shops, count = home_store_facts.top_shops(products)
        self.assertNotIn("Shopping Ads: Google & Bing", shops)
        self.assertEqual(count, 2)


class TheKindFactsTests(unittest.TestCase):
    def test_link_words(self) -> None:
        self.assertEqual(home_store_facts._link_words("Kettles"), "See kettles")
        self.assertEqual(home_store_facts._link_words("TVs"), "See TVs")
        self.assertEqual(home_store_facts._link_words("PC cases"), "See PC cases")

    def test_a_search_that_fails_or_shows_nothing_leaves_its_kind_out(self) -> None:
        departments = home_store.Departments(
            groups=(), kinds={"kitchen": (home_store.DeptKind(kind="kettle", name="Kettles", query="kettle", drawing=""),
                                          home_store.DeptKind(kind="toaster", name="Toasters", query="toaster", drawing=""))}
        )

        def search(query: str):
            if query == "kettle":
                raise RuntimeError("fixture")
            return None

        facts = home_store_facts.work_out_kind_facts(departments=departments, search=search, prepared_at=None)
        self.assertEqual(facts.kinds, {})


if __name__ == "__main__":
    unittest.main()
