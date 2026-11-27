"""The home page's kinds, the site's width and the rows that slide (2026-11-27).

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
- «γενικά το site να παίζει σε όλη την οθόνη»: every page across the whole screen up to
  1,920 px;
- «Όλα πρέπει να γλιστράνε εάν είναι καρουζέλ και τα πρώτα μπάνερ»: on a computer what
  slides on a phone slides too, with an arrow at each end where its row does not fit;
- shown it, «Να κρατηθεί η ίδια λογική με το κινητό να κρατηθεί η ίδια διάταξη απλά τα
  ανοίγματα είναι μεγαλύτερα»: the sections one under another on a computer too.
"""
from __future__ import annotations

import json
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

from picwise_surface import home_store  # noqa: E402
from picwise_surface.browser_lists import BROWSER_LISTS_STYLES  # noqa: E402
from picwise_surface.home_store import (  # noqa: E402
    HOME_STORE_SCRIPT,
    HOME_STORE_STYLES,
    Banner,
    BannerKind,
    HomeFacts,
    banner_as_shown,
    load_departments,
    load_home_lists,
    render_home_store_page,
)
from picwise_surface.page_styles import _PAGE_STYLES  # noqa: E402
from picwise_surface.store_pages import STORE_PAGES_STYLES  # noqa: E402
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
        self.assertEqual(len(lists.banners), 7)
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
        # No offer to show: the offers' banner is not drawn; the six of kinds are.
        self.assertEqual(page.count('class="pw-hs-banner pw-hs-banner-'), 6)
        without = frozenset(everything - {"watch", "ring", "necklace", "earrings"})
        page = render_home_store_page(
            catalogue=(100000, 101), indexable=False, trends=load_trends_panel(),
            facts=HomeFacts(prepared_at=None, tiles_with_products=without),
        )
        self.assertNotIn("WATCHES &amp; JEWELLERY", page)
        self.assertEqual(page.count('class="pw-hs-banner pw-hs-banner-'), 5)


class TheWholeScreenTests(unittest.TestCase):
    def test_one_width_for_every_page(self) -> None:
        for name, styles in (("search", _PAGE_STYLES), ("lists", BROWSER_LISTS_STYLES), ("store", HOME_STORE_STYLES)):
            self.assertNotIn("1190px", styles, name)
        self.assertIn(".pw-topbar-inner{max-width:1920px;", _PAGE_STYLES)
        self.assertIn(".pw-reference-frame{width:100%;max-width:1920px;", _PAGE_STYLES)
        self.assertIn(".pw-panels{position:relative;width:100%;max-width:1920px;", BROWSER_LISTS_STYLES)
        self.assertEqual(HOME_STORE_STYLES.count("max-width:1920px"), 3)

    def test_a_wide_card_keeps_its_price_and_button_on_the_first_screen(self) -> None:
        self.assertIn(
            '@media (min-width:1200px){.pw-grid:not([data-layout="single"]) .pw-product-image-wrap{aspect-ratio:auto;height:260px;}}',
            _PAGE_STYLES,
        )
        # The photo's box is square as before on every narrower screen.
        self.assertIn(".pw-product-image-wrap{position:relative;aspect-ratio:1/1;", _PAGE_STYLES)

    def test_the_other_pages_use_the_width(self) -> None:
        wide = STORE_PAGES_STYLES.split("@media (min-width:1000px){", 1)[1]
        self.assertIn(".pw-hs-groups{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));", wide)
        self.assertIn(".pw-hs-shopblocks{display:grid;", wide)


class TheRowsThatSlideTests(unittest.TestCase):
    def test_on_a_computer_a_row_is_a_row_never_a_grid(self) -> None:
        computer = HOME_STORE_STYLES.split("@media (min-width:700px){", 1)[1]
        for selector in (".pw-hs-offer-row{", ".pw-hs-band-row{", ".pw-hs-depts .pw-hs-scroll{", ".pw-hs-sec-row .pw-hs-scroll{", ".pw-hs-banner-row{"):
            for rule in re.findall(re.escape(selector) + r"([^}]*)\}", computer):
                self.assertNotIn("display:grid", rule, selector)
                self.assertNotIn("overflow:visible", rule, selector)

    def test_the_arrows_are_a_computer_s(self) -> None:
        phone = HOME_STORE_STYLES.split("@media (min-width:700px){", 1)[0]
        self.assertIn(".pw-hs-car-btn{position:absolute;top:50%;z-index:3;display:none;", phone)
        self.assertIn("width:48px;height:48px;", phone.split(".pw-hs-car-btn{", 1)[1].split("}", 1)[0])
        self.assertIn(".pw-hs-car-btn[hidden]{display:none!important;}", phone)
        computer = HOME_STORE_STYLES.split("@media (min-width:700px){", 1)[1]
        self.assertIn(".pw-hs-car-btn{display:flex;}", computer)
        # A row's own bar is hidden only where the script draws the arrows.
        self.assertIn(".pw-js .pw-hs-scroll,.pw-js .pw-hs-band-row{scrollbar-width:none;}", computer)

    def test_the_script_gives_every_row_its_arrows(self) -> None:
        self.assertIn('document.querySelectorAll(".pw-hs-banner-row,.pw-hs-band-row,.pw-hs-scroll")', HOME_STORE_SCRIPT)
        self.assertIn('button("pw-hs-car-prev","Previous",-1)', HOME_STORE_SCRIPT)
        self.assertIn('button("pw-hs-car-next","Next",1)', HOME_STORE_SCRIPT)
        # An arrow only while its side has more to show.
        self.assertIn("prev.hidden=el.scrollLeft<=2;next.hidden=el.scrollLeft>=most-2;", HOME_STORE_SCRIPT)
        self.assertNotIn("__CHEVRON__", HOME_STORE_SCRIPT)
        self.assertIn(json.dumps(home_store._CHEVRON), HOME_STORE_SCRIPT)

    def test_on_a_computer_the_sections_stand_as_on_a_phone(self) -> None:
        # Owner, 2026-11-27, shown two sections side by side: «Να κρατηθεί η ίδια λογική με
        # το κινητό να κρατηθεί η ίδια διάταξη απλά τα ανοίγματα είναι μεγαλύτερα».
        self.assertNotIn(".pw-hs-secs{", HOME_STORE_STYLES)
        self.assertNotIn("grid-column:1 / -1", HOME_STORE_STYLES.split("@media (min-width:1000px){", 1)[1])
        wide = HOME_STORE_STYLES.split("@media (min-width:1000px){", 1)[1]
        # A row's tiles fill the line where they fit and slide where they do not.
        self.assertIn(".pw-hs-sec-row .pw-hs-scroll .pw-hs-tile{flex:1 0 170px;}", wide)

    def test_the_banners_slide_where_they_do_not_fit(self) -> None:
        wide = HOME_STORE_STYLES.split("@media (min-width:1000px){", 1)[1]
        self.assertIn(".pw-hs-banner{flex:1 0 320px;width:auto;max-width:440px;}", wide)
        self.assertNotIn(".pw-hs-banner-row{display:grid", wide)


if __name__ == "__main__":
    unittest.main()
