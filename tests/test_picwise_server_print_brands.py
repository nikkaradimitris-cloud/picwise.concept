"""The brands of the server's catalogue, measured before the brands' list is built.

`deployment/server/print_brands.py`, run by `.github/workflows/brands-measure.yml` on a
copy of the server's file (the owner's series of work, step 3, 2026-11-19; taken up on
2026-11-20: «PicWise: συνέχισε το βήμα 3, τη λίστα brands, όπως γράφει το handoff»).
Pinned here, on a prepared catalogue of the test's own:

- one name for the ways a brand is written: case, accents, punctuation, "&"/"and", a
  leading "The" and an ending such as "Ltd" or "UK" set aside, never the only word;
  punctuation alone and the feeds' placeholders are no brand;
- slips: a letter more, less or other, or two swapped; the names a few slips from a
  name found without comparing it with every name; a slip made as "samsung" is typed
  "samsnug", never into a name or word that exists;
- each brand's products, shops, kinds and accessories; a shop's own name where the
  brand goes; what a search for a brand alone could show;
- the report: the brands, their kinds, their spellings, the names that are words, the
  near names, and the searches as the site answers them from the copy; nothing printed
  is a link; an unreadable file says so; every case exits 0;
- from 2026-11-20, with the brands' list built (`picwise_providers.brand_list`): a
  brand's spellings joined with its letters mended, the searches' question and
  correction told, and the list as the search reads it (part 7).

Every product is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = ROOT / "deployment" / "server" / "print_brands.py"
for path in (HERE, ROOT, ROOT / "deployment" / "server", ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import audit_search  # noqa: E402
import print_brands  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402
from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue  # noqa: E402
from picwise_providers.search_selection import _product_search_fields  # noqa: E402

KETTLES = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Kettles"
TOASTERS = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Toasters"
LAPTOPS = "Electronics > Computers > Laptops"
DECOR = "Home & Garden > Decor"

# (brand as written, title, shelf, how many, the first price, the shop)
_ROWS = (
    ("Fixturon", "Fixturon Electric Kettle {n}", KETTLES, 4, 20.0, "Fictional Store One"),
    ("FIXTURON", "Fixturon Electric Kettle Steel {n}", KETTLES, 1, 26.0, "Fictional Store Two"),
    ("Fixturon Ltd", "Fixturon Toaster {n}", TOASTERS, 4, 25.0, "Fictional Store Two"),
    ("Fixturon", "Fixturon Book {n} Laptop 8GB", LAPTOPS, 3, 300.0, "Fictional Store Two"),
    ("Fixtuorn", "Fixtuorn Electric Kettle {n}", KETTLES, 1, 18.0, "Fictional Store Two"),
    ("Testline", "Testline Electric Kettle {n}", KETTLES, 4, 22.0, "Fictional Store One"),
    ("Generic", "Garden Gnome Statue {n}", DECOR, 3, 12.0, "Fictional Store One"),
    ("", "Garden Gnome Figure {n}", DECOR, 2, 14.0, "Fictional Store One"),
    ("Fictional Gnomes", "Fictional Gnomes Garden Gnome {n}", DECOR, 3, 15.0, "Fictional Gnomes UK"),
    ("Sampleworks", "Sampleworks Toaster {n} for Fixturon Kitchens", TOASTERS, 3, 30.0, "Fictional Store Two"),
    ("Velvet", "Velvet Toaster {n}", TOASTERS, 3, 28.0, "Fictional Store Two"),
)


def _product(number: int, brand: str, title: str, category: str, price: float, shop: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=f"row-{number}",
        title=title,
        brand=brand,
        category_text=category,
        product_url=f"https://shop.invalid/p/{number}",
        image_url=f"https://shop.invalid/i/{number}.jpg",
        price_text=f"{price:.2f}",
        availability_text="in stock",
        currency="GBP",
        raw={"merchant_name": shop, "in_stock": "1", "description": fixture_description()},
    )


def _write(path: Path) -> None:
    products = []
    for brand, title, category, count, price, shop in _ROWS:
        for step in range(count):
            products.append(
                _product(len(products) + 1, brand, title.format(n=step + 1), category, price + step, shop)
            )
    products = tuple(products)
    prepared = PreparedCatalogue(
        prepared_at=datetime(2026, 11, 20, 4, 21, tzinfo=timezone.utc),
        feed_status=ProviderFeedStatus(
            status="provider_feed_ready", provider_key="awin", product_count=len(products), eligible_count=len(products)
        ),
        availability_context=build_feed_availability_context(products),
        products=products,
        non_new=tuple("" for _product in products),
        kinds=tuple(frozenset() for _product in products),
        eligible_count=len(products),
        shop_count=3,
        suggestions=(),
        search_fields=tuple(_product_search_fields(product) for product in products),
    )
    write_prepared_catalogue(prepared, path)


class NameTests(unittest.TestCase):
    def test_one_name_for_the_ways_a_brand_is_written(self) -> None:
        for written in ("Samsung", "SAMSUNG", "Samsung UK", "Samsung Ltd", "samsung  "):
            self.assertEqual(print_brands.brand_key(written), "samsung", written)
        for written in ("Black & Decker", "BLACK+DECKER", "Black and Decker", "Black-Decker"):
            self.assertEqual(print_brands.brand_key(written), "blackdecker", written)
        self.assertEqual(print_brands.brand_key("The North Face"), "northface")
        self.assertEqual(print_brands.brand_key("Nestlé"), "nestle")
        self.assertEqual(print_brands.brand_key("Levi's"), "levis")
        # An ending is never the only word, and a lone "The" stays a name.
        self.assertEqual(print_brands.brand_key("UK"), "uk")
        self.assertEqual(print_brands.brand_key("The"), "the")
        # Punctuation alone is no name; letters no ASCII holds are kept.
        self.assertEqual(print_brands.brand_key(" - "), "")
        self.assertEqual(print_brands.brand_key("Πλαίσιο"), "πλαίσιο")
        self.assertEqual(print_brands.spoken("Russell Hobbs UK"), "russell hobbs")

    def test_the_placeholders_are_no_brand(self) -> None:
        for written in ("Generic", "UNBRANDED", "N/A", "Does Not Apply", "No Brand", "", "-"):
            self.assertTrue(print_brands.is_placeholder(print_brands.brand_key(written)), written)
        self.assertFalse(print_brands.is_placeholder(print_brands.brand_key("Fixturon")))

    def test_slips(self) -> None:
        self.assertEqual(print_brands.slips("samsung", "samsung"), 0)
        self.assertEqual(print_brands.slips("samsung", "samsnug"), 1)
        self.assertEqual(print_brands.slips("dyson", "dysn"), 1)
        self.assertEqual(print_brands.slips("dyson", "dysone"), 1)
        self.assertEqual(print_brands.slips("bosch", "bosh"), 1)
        self.assertEqual(print_brands.slips("bosch", "bose"), 2)
        self.assertEqual(print_brands.slips("samsung", "sony"), 3)
        self.assertEqual(print_brands.slips("ab", "abcdef"), 3)

    def test_the_names_a_few_slips_away(self) -> None:
        index = print_brands.NearIndex(["samsung", "bosch", "bose", "boss", "sony"], 2)
        self.assertEqual(index.near("bosch", 1), {})
        self.assertEqual(index.near("bosch", 2), {"bose": 2, "boss": 2})
        self.assertEqual(index.near("samsnug", 1), {"samsung": 1})
        self.assertEqual(index.near("sonny", 1), {"sony": 1})

    def test_a_slip_as_a_name_is_mistyped(self) -> None:
        self.assertEqual(print_brands.a_slip_of("samsung", lambda word: False), "samsnug")
        self.assertEqual(print_brands.a_slip_of("dyson", lambda word: False), "dyosn")
        # Never a name or word that exists: the next place is taken.
        self.assertEqual(print_brands.a_slip_of("samsung", lambda word: word == "samsnug"), "samusng")
        self.assertEqual(print_brands.a_slip_of("bosh", lambda word: False), "")
        self.assertEqual(print_brands.a_slip_of("3m100", lambda word: False), "")

    def test_the_word_list_gives_lowercase_words_of_letters(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "words"
            path.write_text("kettle\nVelvet\nvelvet\nab\nrock's\nSamsung\ngarden\n", encoding="utf-8")
            self.assertEqual(print_brands.read_words(str(path)), frozenset({"kettle", "velvet", "garden"}))
        self.assertEqual(print_brands.read_words(""), frozenset())
        self.assertEqual(print_brands.read_words("/nonexistent/words"), frozenset())


class CatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.folder = tempfile.TemporaryDirectory()
        cls.path = Path(cls.folder.name) / "catalogue.json.gz"
        _write(cls.path)
        cls.prepared = audit_search.load_catalogue(cls.path)
        cls.brands = print_brands.read_brands(cls.prepared.products, cls.prepared.kinds)
        cls.words = frozenset({"velvet", "garden", "statue"})

    @classmethod
    def tearDownClass(cls) -> None:
        cls.folder.cleanup()

    def test_each_brand_with_its_spellings_shops_and_kinds(self) -> None:
        fixturon = self.brands["fixturon"]
        self.assertEqual(fixturon.products, 12)
        self.assertEqual(fixturon.forms, {"Fixturon": 7, "FIXTURON": 1, "Fixturon Ltd": 4})
        self.assertEqual(fixturon.name, "Fixturon")
        self.assertEqual(fixturon.shops, {"Fictional Store One": 4, "Fictional Store Two": 8})
        self.assertEqual(fixturon.kinds["kettle"], 5)
        self.assertEqual(fixturon.kinds["toaster"], 4)
        self.assertEqual(fixturon.kinds["laptop"], 3)
        self.assertTrue(fixturon.real)
        self.assertEqual(print_brands.brand_shape(fixturon), print_brands.SOME_KINDS)
        self.assertEqual([kind for kind, _count in fixturon.choices()], ["kettle", "toaster", "laptop"])
        self.assertEqual(print_brands.brand_shape(self.brands["testline"]), print_brands.ONE_KIND)
        # No brand written, and a placeholder.
        self.assertEqual(self.brands[""].products, 2)
        self.assertTrue(self.brands["generic"].placeholder)
        self.assertFalse(self.brands["generic"].real)
        # The shop's own name where the brand goes ("Fictional Gnomes UK" reads as it).
        gnomes = self.brands["fictionalgnomes"]
        self.assertTrue(gnomes.shops_own)
        self.assertFalse(gnomes.real)

    def test_the_report(self) -> None:
        lines: list[str] = []
        print_brands.print_brands(self.prepared, self.brands, self.words, out=lines.append)
        out = "\n".join(lines)
        self.assertIn("== 1. THE BRANDS AS THE FEEDS WRITE THEM", out)
        self.assertIn("products: 31; with a brand 26 (83.9%); none written 2; a placeholder 3", out)
        self.assertIn("  the placeholders: Generic 3", out)
        self.assertIn("a shop's own name where the brand goes: 1 names, 3 products", out)
        self.assertIn("  Fictional Gnomes: 3 (Fictional Gnomes UK 3)", out)
        self.assertIn("  Fixturon: 12 | 2 shops | 3 kinds | kettle 5, toaster 4, laptop 3", out)
        self.assertIn("== 2. THE KINDS OF EACH BRAND", out)
        self.assertIn(f"  {print_brands.SOME_KINDS}: 1 brands, 12 products", out)
        self.assertIn("  dyson: no product of the catalogue carries it", out)
        self.assertIn("== 3. ONE BRAND, SEVERAL SPELLINGS", out)
        self.assertIn("  Fixturon (12): Fixturon 7, Fixturon Ltd 4, FIXTURON 1", out)
        self.assertIn("== 4. BRANDS WHOSE NAME IS ALSO A WORD", out)
        self.assertIn("  Velvet (3): other brands' titles 0;", out)
        self.assertIn("d. a word the search reads as describing a product: 1 brands: Velvet (3)", out)
        self.assertIn("  Fixturon: in 3 titles of other brands, 12 of its own 12", out)
        self.assertIn("== 5. NEAR-IDENTICAL NAMES", out)
        self.assertIn("  Fixturon (12; kettle 5, toaster 4, +1 more)  ~  Fixtuorn (1; kettle 1)", out)
        self.assertNotIn("invalid", out)

    def test_the_searches_as_the_site_answers(self) -> None:
        lines: list[str] = []
        answered = print_brands.print_searches(
            self.prepared,
            self.brands,
            self.words,
            3,
            out=lines.append,
            examples=(("fixturon kettle", "fixturon", "kettle"),),
        )
        out = "\n".join(lines)
        self.assertIn("== 6. THE SEARCH TODAY", out)
        self.assertIn('  "fixturon kettle": 4 of 5 shown; of the first 4: 4 the brand\'s, 4 kettle;', out)
        # The three largest real brands, each four ways where it can be: Fixturon,
        # Testline, Sampleworks (Velvet is as large, and comes after by name).
        self.assertIn("the 3 largest real brands, each searched four ways:", out)
        queries = [result["q"] for result in answered]
        self.assertIn("testline", queries)
        self.assertIn("testline kettle", queries)
        self.assertIn("testlnie", queries)
        self.assertIn("testlnie kettle", queries)
        self.assertNotIn("velvet", queries)
        self.assertTrue(all(result["seconds"] >= 0 for result in answered))
        self.assertNotIn("invalid", out)
        # With the brands' list (owner, 2026-11-20): a brand of several kinds asks which,
        # with no Recommended; a slip of one brand is read as it, and said.
        self.assertIn(
            '  "fixturon": 4 of 12 shown; of the first 4: 4 the brand\'s; first: Fixturon Electric Kettle 1 | '
            "asks What kind of Fixturon product? fixturon kettle, fixturon toaster, fixturon laptop | "
            "no recommendation several kinds |",
            out,
        )
        self.assertIn("understood as: Testline", out)
        self.assertIn("  alone: 3 searches; shown 3;", out)

    def test_the_list_as_the_search_reads_it(self) -> None:
        lines: list[str] = []
        print_brands.print_searches(self.prepared, self.brands, self.words, 1, out=lambda line: None, examples=())
        real = sorted(
            (brand for brand in self.brands.values() if brand.real and brand.products >= print_brands.COUNTED),
            key=lambda brand: (-brand.products, brand.key),
        )
        print_brands.print_the_list(self.brands, real, out=lines.append)
        out = "\n".join(lines)
        self.assertIn("== 7. THE BRANDS' LIST AS THE SEARCH READS IT", out)
        self.assertIn(
            "listed: 5 brands of 3 products or more, 25 products; one kind 3, several kinds (a question) 1, "
            "no kind read 1",
            out,
        )
        self.assertIn("names the reading never corrects: 4 of one word, 1 of several", out)
        self.assertNotIn("invalid", out)


class WorkflowTests(unittest.TestCase):
    def test_the_workflow_only_reads_the_server_and_runs_on_its_own_branch(self) -> None:
        text = (ROOT / ".github" / "workflows" / "brands-measure.yml").read_text(encoding="utf-8")
        # Run by a push of its own file to the brands' branch, never the work or site branch.
        self.assertIn("    branches: [claude/brands-2026-11-20]\n", text)
        self.assertIn("      - '.github/workflows/brands-measure.yml'\n", text)
        self.assertNotIn("ccr-1361f1a7-dcpo60", text)
        self.assertIn("permissions:\n  contents: read\n", text)
        self.assertIn("  group: server-setup", text)
        # The server's identity as search-audit.yml checks it, its names masked.
        self.assertIn("pin=$(HOST_KEY=\"$host_key\" python3 .github/scripts/host_key_pin.py)", text)
        self.assertIn("::add-mask::", text)
        # The server is only read: one copy of its prepared file, nothing written to it.
        self.assertEqual(text.count("ssh -n picwise 'sudo cat /srv/picwise/shared/prepared/catalogue.json.gz'"), 1)
        self.assertNotIn("sudo tee", text)
        self.assertNotIn("systemctl", text)
        self.assertNotIn("ANTHROPIC_API_KEY", text)
        self.assertIn('print_brands.py "$RUNNER_TEMP/catalogue.json.gz" --words /usr/share/dict/words', text)
        self.assertIn('rm -f ~/.ssh/deploy_key ~/.ssh/config "$RUNNER_TEMP/catalogue.json.gz"', text)


class ScriptTests(unittest.TestCase):
    def test_the_script_on_a_file_and_on_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            _write(path)
            words = Path(folder) / "words"
            words.write_text("velvet\ngarden\n", encoding="utf-8")
            done = subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--words", str(words), "--no-searches"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn("the copy: prepared at 2026-11-20 04:21 UTC, 31 products, 3 shops", done.stdout)
            self.assertIn("c. an English word (the word list, 2 words): 1 brands", done.stdout)
            self.assertNotIn("== 6.", done.stdout)
            self.assertNotIn("invalid", done.stdout)
            missing = subprocess.run(
                [sys.executable, str(SCRIPT), str(Path(folder) / "none.json.gz"), "--no-searches"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(missing.returncode, 0)
            self.assertIn("no prepared catalogue could be read", missing.stdout)


if __name__ == "__main__":
    unittest.main()
