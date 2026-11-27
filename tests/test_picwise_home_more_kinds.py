"""The home page's kinds (2026-11-27).

The owner, 2026-11-27, of the home page that went live on 24/11:

- «Θέλω να προστεθούν περισσότερες κατηγορίες για παράδειγμα οθόνες δεν υπάρχουν ούτε στα
  καρουζέλ ούτε στα banners», and then «η σελίδα το homepage πρέπει να παρουσιάζει τις πιο
  διαδεδομένες κατηγορίες που μπορεί να ψάχνει ένας χρήστης», not what the catalogue holds
  now: seven banners and fourteen sections, nothing of 24/11 taken away;
- «αν μία κατηγορία έχει λιγότερο από δύο προϊόντα να κρύβεται αυτόματα από τα banners όχι
  από το site»: a kind of fewer than two products is on no tile and in no banner's words
  (`home_store.MIN_PRODUCTS`), and still in its search and its department;
- «δεν θέλω να αλλάξουμε τα γραφικά ... Μην πειράξεις χρώματα διάταξη»: the phone's rules
  are as they were; the new drawings are the old ones' family;
- shown a computer's page across the whole screen with rows that slide, which he had asked
  for the same day: «Σε pc είναι χάλια»; shown it as on 24/11 with the new kinds: «Το θέλω
  όπως ήταν πριν πριν την αλλαγή», and, asked, "the new kinds on the phone only": what the
  day added is a phone's alone (`home_store.PHONE_ONLY`), and a computer's page is the page
  of 24/11 (compared picture for picture at 700 to 1,920 px before it was shown to him).
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_surface.home_store import (  # noqa: E402
    HOME_STORE_STYLES,
    Banner,
    BannerKind,
    HomeFacts,
    banner_as_shown,
    load_departments,
    load_home_lists,
    render_home_store_page,
)
from picwise_surface.trends import load_trends_panel  # noqa: E402

# The sections and tiles of the home page of 2026-11-24: none of them is taken away.
OF_24_11 = {
    "Kitchen favourites": ("air fryer", "coffee machine", "microwave", "kettle"),
    "Style": ("boots", "trainers", "dress", "watch"),
    "Comfort at home": ("dehumidifier", "heater", "robot vacuum", "air purifier"),
    "Computers & office": ("laptop", "printer", "router", "headphones"),
    "Home & furniture": ("bed", "desk", "office chair", "lamp"),
    "Tools & garden": ("drill", "mitre saw", "lawn mower", "pressure washer"),
}


def _banner(*, lead: int = 3) -> Banner:
    return Banner(
        theme="blue",
        eyebrow="COMPUTERS & TECH",
        title="Laptops, phones & TVs",
        line="From UK shops, in stock only.",
        button="Browse computers",
        part="departments",
        href="/department/computers",
        drawings=(("laptop", "white"), ("smartphone", "mist"), ("tv", "sand")),
        kinds=(
            BannerKind("laptops", "laptop", "laptop"),
            BannerKind("phones", "smartphone", "smartphone"),
            BannerKind("TVs", "tv", "tv"),
            BannerKind("monitors", "monitor", "monitor"),
            BannerKind("tablets", "tablet", "tablet"),
        ),
        lead=lead,
    )


def _known(*queries: str) -> HomeFacts:
    return HomeFacts(prepared_at=None, tiles_with_products=frozenset(queries))


class TheListsTests(unittest.TestCase):
    def test_seven_banners_fourteen_sections_and_nothing_of_24_11_taken_away(self) -> None:
        lists = load_home_lists()
        # A phone's seven banners; a computer's four, as on 24/11.
        self.assertEqual(sum(not banner.pc for banner in lists.banners), 7)
        self.assertEqual(sum(not banner.phone for banner in lists.banners), 4)
        self.assertEqual(len(lists.sections), 14)
        by_title = {section.title: section for section in lists.sections}
        for title, queries in OF_24_11.items():
            self.assertIn(title, by_title)
            self.assertTrue(set(queries) <= {tile.query for tile in by_title[title].tiles}, title)
        for query in ("drill", "air fryer", "printer", "robot vacuum", "lawn mower", "dehumidifier"):
            self.assertIn(query, [kind.query for kind in lists.recommended])
        # The owner's example: monitors, in a banner's kinds and on a tile.
        self.assertIn("monitor", {tile.query for section in lists.sections for tile in section.tiles})
        self.assertIn("monitor", {kind.query for banner in lists.banners for kind in banner.kinds})

    def test_the_layouts_take_turns(self) -> None:
        layouts = [section.layout for section in load_home_lists().sections]
        self.assertEqual(layouts, ["grid", "row"] * 7)

    def test_every_kind_searched_is_a_kind_of_the_departments(self) -> None:
        # The words a tile and a banner search are the site's own, as its departments' file
        # writes them ("watch", not "watches"): never a new spelling.
        known = {kind.query for kinds in load_departments().kinds.values() for kind in kinds}
        lists = load_home_lists()
        asked = {tile.query for section in lists.sections for tile in section.tiles}
        asked |= {kind.query for banner in lists.banners for kind in banner.kinds}
        asked |= {kind.query for kind in lists.recommended}
        self.assertEqual(asked - known, set())

    def test_a_banner_of_kinds_names_its_first_kinds(self) -> None:
        for banner in load_home_lists().banners:
            if banner.part == "offers":
                self.assertEqual(banner.kinds, ())
                continue
            self.assertGreaterEqual(len(banner.kinds), 5, banner.eyebrow)
            # Its first kind in its own words ("Drills, saws & garden machines" says its
            # second and third in other words: chainsaws, lawn mowers).
            self.assertIn(banner.kinds[0].word.lower(), banner.title.lower(), banner.eyebrow)
            self.assertLessEqual(banner.lead, len(banner.kinds))

    def test_every_drawing_is_written_by_the_tool(self) -> None:
        # A drawing is changed in `tools/draw_home_art.py`, never in its file.
        tool = (ROOT / "tools" / "draw_home_art.py").read_text(encoding="utf-8")
        used = set(re.findall(r"'(\w+)'", tool.split("USED = (", 1)[1].split("\n)\n", 1)[0]))
        on_disk = {path.stem for path in (ROOT / "assets" / "home" / "art").glob("*.svg")}
        self.assertEqual(used, on_disk)

    def test_the_new_drawings_keep_the_family_of_colours(self) -> None:
        # Owner, 2026-11-23: «γίνεσαι παιδική χαρά»: no red, orange, green or purple.
        import colorsys

        for path in sorted((ROOT / "assets" / "home" / "art").glob("*.svg")):
            for colour in set(re.findall(r'stop-color="#([0-9a-fA-F]{6})"', path.read_text(encoding="utf-8"))):
                red, green, blue = (int(colour[index : index + 2], 16) / 255 for index in (0, 2, 4))
                hue, _light, saturation = colorsys.rgb_to_hls(red, green, blue)
                if saturation < 0.25:
                    continue  # greys
                degrees = hue * 360
                # blues (190 to 250) and golds, woods and skin (15 to 55)
                self.assertTrue(190 <= degrees <= 250 or 15 <= degrees <= 55, (path.name, colour, round(degrees)))


class ABannerTonightTests(unittest.TestCase):
    def test_while_nothing_is_counted_it_reads_as_its_file(self) -> None:
        banner = _banner()
        self.assertEqual(banner_as_shown(banner, None), (banner.title, banner.drawings))
        self.assertEqual(banner_as_shown(banner, HomeFacts(prepared_at=None)), (banner.title, banner.drawings))

    def test_with_the_kinds_its_title_names_it_reads_as_its_file(self) -> None:
        banner = _banner()
        shown = banner_as_shown(banner, _known("laptop", "smartphone", "tv"))
        self.assertEqual(shown, (banner.title, banner.drawings))

    def test_a_kind_of_fewer_than_two_products_is_not_named(self) -> None:
        title, drawings = banner_as_shown(_banner(), _known("laptop", "monitor", "tablet"))
        self.assertEqual(title, "Laptops, monitors & tablets")
        self.assertEqual(drawings, (("laptop", "white"), ("monitor", "mist"), ("tablet", "sand")))
        title, drawings = banner_as_shown(_banner(), _known("tv", "monitor"))
        self.assertEqual(title, "TVs & monitors")
        # Three drawings always: the kinds named, then the file's own.
        self.assertEqual([name for name, _ground in drawings], ["tv", "monitor", "laptop"])

    def test_a_title_that_names_two_stands_with_those_two(self) -> None:
        # "Air fryers, vacuums & more" names two kinds (`lead`).
        banner = _banner(lead=2)
        self.assertEqual(banner_as_shown(banner, _known("laptop", "smartphone"))[0], banner.title)
        self.assertEqual(banner_as_shown(banner, _known("laptop", "tv", "monitor"))[0], "Laptops, TVs & monitors")

    def test_with_fewer_than_two_kinds_it_is_not_drawn(self) -> None:
        self.assertIsNone(banner_as_shown(_banner(), _known("laptop")))
        self.assertIsNone(banner_as_shown(_banner(), _known()))

    def test_the_page_draws_it_so(self) -> None:
        lists = load_home_lists()
        everything = {tile.query for section in lists.sections for tile in section.tiles}
        everything |= {kind.query for banner in lists.banners for kind in banner.kinds}
        page = render_home_store_page(
            catalogue=(100000, 101),
            indexable=False,
            trends=load_trends_panel(),
            facts=HomeFacts(prepared_at=None, tiles_with_products=frozenset(everything - {"smartphone", "tv"})),
        )
        self.assertIn(">Laptops, monitors &amp; tablets<", page)
        self.assertNotIn(">Laptops, phones &amp; TVs<", page)
        self.assertNotIn('href="/search?q=smartphone"', page)
        # No offer to show: the offers' banner is not drawn; a phone's six of kinds are.
        self.assertEqual(len(re.findall(r'class="pw-hs-banner pw-hs-banner-\w+(?: pw-hs-phone)?"', page)), 6)
        without = frozenset(everything - {"watch", "ring", "necklace", "earrings"})
        page = render_home_store_page(
            catalogue=(100000, 101), indexable=False, trends=load_trends_panel(),
            facts=HomeFacts(prepared_at=None, tiles_with_products=without),
        )
        self.assertNotIn("WATCHES &amp; JEWELLERY", page)
        self.assertEqual(len(re.findall(r'class="pw-hs-banner pw-hs-banner-\w+(?: pw-hs-phone)?"', page)), 5)


class APhonesAloneTests(unittest.TestCase):
    """Owner, 2026-11-27: «Το θέλω όπως ήταν πριν πριν την αλλαγή»; the new kinds on the
    phone only."""

    def test_without_what_is_a_phone_s_the_lists_are_those_of_24_november(self) -> None:
        lists = load_home_lists()
        sections = [section for section in lists.sections if not section.phone]
        self.assertEqual([section.title for section in sections], list(OF_24_11))
        for section in sections:
            self.assertEqual(tuple(tile.query for tile in section.tiles if not tile.phone), OF_24_11[section.title])
        banners = [banner for banner in lists.banners if not banner.phone]
        self.assertEqual(
            [banner.title for banner in banners],
            ["Offers from UK shops", "Air fryers, vacuums & more", "Laptops, printers & routers", "Drills, saws & garden machines"],
        )
        self.assertEqual(
            [kind.query for kind in lists.recommended if not kind.phone],
            ["drill", "air fryer", "printer", "robot vacuum", "lawn mower", "dehumidifier"],
        )
        # A banner is a phone's or a computer's, never both.
        self.assertFalse(any(banner.phone and banner.pc for banner in lists.banners))

    def test_the_two_rules_stand_after_the_styles_of_24_november(self) -> None:
        self.assertTrue(
            HOME_STORE_STYLES.endswith(
                "@media (max-width:699px){.pw-hs-pc{display:none!important;}}"
                "@media (min-width:700px){.pw-hs-phone{display:none!important;}}"
            )
        )
        self.assertEqual(HOME_STORE_STYLES.count("pw-hs-phone"), 1)
        self.assertEqual(HOME_STORE_STYLES.count("pw-hs-pc"), 1)
        # A computer's page as on 24/11: its width, nothing that slides.
        self.assertIn(".pw-hs-main{width:100%;max-width:1190px;", HOME_STORE_STYLES)
        self.assertNotIn("pw-hs-car-btn", HOME_STORE_STYLES)

    def test_the_page_marks_what_is_a_phone_s(self) -> None:
        page = render_home_store_page(catalogue=(100000, 101), indexable=False, trends=load_trends_panel())
        body = page.split("</style>", 1)[1]
        sections = re.findall(r'<section class="pw-hs-sec(?: pw-hs-sec-row)?( pw-hs-phone)?"', body)
        self.assertEqual((len(sections), sections.count("")), (14, 6))
        # A computer's tiles: the 24 of 24/11 (a tile of a phone's section is hidden with it).
        computers = re.split(r'<section class="pw-hs-sec(?: pw-hs-sec-row)? pw-hs-phone"', body)
        kept = "".join(part.split("</section>", 1)[1] if index else part for index, part in enumerate(computers))
        self.assertEqual(kept.count('class="pw-hs-tile"'), 24)
        self.assertIn('<a class="pw-hs-tile pw-hs-phone" href="/search?q=monitor">', body)
        # Each banner's dot is seen where its banner is.
        self.assertEqual(len(re.findall(r'class="pw-hs-dot(?: is-on)? pw-hs-phone"', body)), 4)
        self.assertEqual(len(re.findall(r'class="pw-hs-dot(?: is-on)? pw-hs-pc"', body)), 1)

    def test_a_section_left_with_one_tile_for_a_computer_is_a_phone_s(self) -> None:
        lists = load_home_lists()
        everything = {tile.query for section in lists.sections for tile in section.tiles}
        facts = HomeFacts(prepared_at=None, tiles_with_products=frozenset(everything - {"watch", "boots", "dress"}))
        page = render_home_store_page(catalogue=(100000, 101), indexable=False, trends=load_trends_panel(), facts=facts)
        self.assertIn('<section class="pw-hs-sec pw-hs-sec-row pw-hs-phone" aria-labelledby="pw-hs-sec-2">', page)
        self.assertIn(">Style</h2>", page)


if __name__ == "__main__":
    unittest.main()
