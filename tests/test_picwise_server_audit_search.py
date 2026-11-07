"""The debugging's measure on the server's catalogue, judged by Claude Haiku 5.5 (owner, 2026-11-07).

`deployment/server/audit_search.py`, run by `.github/workflows/search-audit.yml` (owner:
«ζητάω μία μεγάλη γενική απασφαλμάτωση»; the method's steps 2 and 3, about $3, «Ναι σε όλα»;
«Κατάλαβα τη διευκρίνιση δεν χρειάζεται να τα ελέγξουμε όλα»; «Ανέβασε μετά τη μέτρηση..»).
Pinned here, on a prepared catalogue of the test's own and an AI of the test's own (no call
leaves the test):

- the searches: each kind's names and its commonest brand with its name, each with its
  kind and category, written once for both sets of rules;
- the cards: each search answered as the site answers it from the copy, its first 12;
- what is asked: the products of each kind the reports flag (an accessory word, no word
  of the kind, a price far under the middle one), cheapest first, and others as a sample;
  products with no kind; every card for the kind its search was for, each pair once;
- the report: per kind, the products not of it; the gaps; per category and set of rules,
  the share of cards right, the absurd ones, the searches with no card;
- the budget stops the calls; a dry run asks nothing; nothing printed is a link.

Every product is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = ROOT / "deployment" / "server" / "audit_search.py"
for path in (HERE, ROOT, ROOT / "deployment" / "server", ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import audit_search  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_ai.client import Asked  # noqa: E402
from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context  # noqa: E402
from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue  # noqa: E402
from picwise_providers.search_selection import _product_search_fields  # noqa: E402

KETTLES = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Kettles"
LAPTOPS = "Electronics > Computers > Laptops"
TOASTERS = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Toasters"


def _product(number: int, title: str, category: str, price: float, brand: str = "Fixturon") -> ProviderProduct:
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
        raw={"merchant_name": "Fictional Store One", "in_stock": "1", "description": fixture_description()},
    )


def _write(path: Path) -> None:
    products = []
    for title, category, count, base in (
        ("Fixturon Electric Kettle {n}", KETTLES, 12, 20.0),
        # A kettle by its shelf whose title names no kettle, and one far under the middle
        # price: both flagged.
        ("Fixturon Aqua Boil {n} 1.7L", KETTLES, 2, 30.0),
        ("Fixturon Electric Kettle Travel {n}", KETTLES, 1, 3.0),
        ("Fixturon Book {n} Laptop 8GB", LAPTOPS, 8, 300.0),
        ("Fixturon Laptop Sleeve Case {n}", LAPTOPS, 3, 9.0),
        ("Testline Toaster {n}", TOASTERS, 6, 25.0),
        ("Sampleworks Garden Gnome Statue {n}", "Home & Garden > Decor", 5, 15.0),
    ):
        for step in range(count):
            products.append(_product(len(products) + 1, title.format(n=step + 1), category, base + step))
    products = tuple(products)
    prepared = PreparedCatalogue(
        prepared_at=datetime(2026, 11, 7, 4, 21, tzinfo=timezone.utc),
        feed_status=ProviderFeedStatus(
            status="provider_feed_ready", provider_key="awin", product_count=len(products), eligible_count=len(products)
        ),
        availability_context=build_feed_availability_context(products),
        products=products,
        non_new=tuple("" for _product in products),
        kinds=tuple(frozenset() for _product in products),
        eligible_count=len(products),
        shop_count=1,
        suggestions=(),
        search_fields=tuple(_product_search_fields(product) for product in products),
    )
    write_prepared_catalogue(prepared, path)


def _fake_ask(request: dict, *, client: object) -> Asked:
    """An AI of the test's own: an "Aqua Boil" is no kettle; a laptop sleeve, with no kind,
    is a laptop bag; a gnome is no kind; everything else is what was asked for."""
    content = request["messages"][0]["content"]
    lines = [line for line in content.splitlines() if line[:1].isdigit()]
    if "The kinds:" in request["system"][0]["text"]:
        answers = [
            {"n": i, "kind": "laptop_bag" if "Sleeve" in line else "none"} for i, line in enumerate(lines, 1)
        ]
    else:
        first = content.split("\n")[0]
        answers = [
            {"n": i, "answer": "no" if "Aqua Boil" in line or ("laptop bag" in first and "Kettle" in line) else "yes"}
            for i, line in enumerate(lines, 1)
        ]
    return Asked({"answers": answers}, "end_turn", "claude-haiku-5-5", 100, 50, 0, 0, 0.001, 0.1, "")


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.folder = tempfile.TemporaryDirectory()
        cls.path = Path(cls.folder.name) / "catalogue.json.gz"
        _write(cls.path)
        cls.prepared = audit_search.load_catalogue(cls.path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.folder.cleanup()

    def test_the_searches_are_each_kinds_names_and_its_commonest_brand(self) -> None:
        searches = audit_search.build_searches(self.prepared)
        by_text = {search["q"]: search for search in searches}
        self.assertEqual(by_text["kettle"]["kind"], "kettle")
        self.assertEqual(by_text["kettle"]["category"], "KI")
        self.assertIn("Fixturon kettle", by_text)
        self.assertEqual(by_text["Fixturon kettle"]["how"], "brand")
        self.assertTrue(any(search["how"].startswith("read as another kind offline") for search in searches))
        self.assertEqual(len(by_text), len(searches))

    def test_the_cards_are_the_first_twelve_as_the_site_answers(self) -> None:
        answered = audit_search.search_cards([{"q": "kettle", "kind": "kettle", "category": "KI", "how": "name"}])
        self.assertEqual(len(answered[0]["cards"]), 12)
        self.assertEqual(answered[0]["total"], 15)
        unsure = audit_search.search_cards([{"q": "laptop bgs", "kind": "laptop_bag", "category": "JW", "how": "x"}])
        self.assertEqual(unsure[0]["cards"], [])

    def test_the_flags_cheapest_first_and_a_sample_of_the_rest(self) -> None:
        chosen = audit_search.flagged_and_sampled(self.prepared)
        flagged_titles = [self.prepared.products[i].title for i in chosen["kettle"]["flagged"]]
        self.assertEqual(
            flagged_titles,
            ["Fixturon Electric Kettle Travel 1", "Fixturon Aqua Boil 1 1.7L", "Fixturon Aqua Boil 2 1.7L"],
        )
        self.assertEqual(len(chosen["kettle"]["sample"]), 12)
        # The laptop sleeves are read as accessories by the rules: no laptop's.
        self.assertEqual(len(chosen["laptop"]["flagged"]) + len(chosen["laptop"]["sample"]), 8)

    def test_the_judgements_and_the_report(self) -> None:
        searches = [
            {"q": "laptop", "kind": "laptop", "category": "CO", "how": "name"},
            {"q": "kettle", "kind": "kettle", "category": "KI", "how": "name"},
        ]
        cards = {"this commit": audit_search.search_cards(searches)}
        lines: list[str] = []
        asker = audit_search.Asker(object(), 3.0, _fake_ask)
        report = audit_search.judge(self.prepared, searches, cards, asker=asker, out=lines.append)
        out = "\n".join(lines)
        self.assertIn("== THE PRODUCTS IN EACH KIND", out)
        self.assertIn("  kettle (KI): 2 not of it (0 of the 12 unflagged)", out)
        self.assertIn("Fixturon Aqua Boil 1 1.7L | 30.00 GBP", out)
        self.assertIn("== THE PRODUCTS WITH NO KIND", out)
        self.assertIn("  laptop_bag (JW): 3, e.g.", out)
        scores = report["scores"]["this commit"]
        # The first 12 kettles, cheapest first, hold one "Aqua Boil": not right, but of
        # the search's category, so not absurd.
        self.assertEqual((scores["KI"]["judged"], scores["KI"]["right"], scores["KI"]["absurd"]), (12, 11, 0))
        self.assertEqual(scores["CO"]["right"], scores["CO"]["judged"])
        self.assertIn("the AI: ", out)
        self.assertNotIn("shop.invalid", out)

    def test_a_card_not_right_and_of_no_kind_of_the_searchs_category_is_absurd(self) -> None:
        searches = [{"q": "kettle", "kind": "laptop_bag", "category": "JW", "how": "name"}]
        cards = {"this commit": audit_search.search_cards(searches)}
        lines: list[str] = []
        report = audit_search.judge(
            self.prepared, searches, cards, asker=audit_search.Asker(object(), 3.0, _fake_ask), out=lines.append
        )
        row = report["scores"]["this commit"]["JW"]
        self.assertEqual((row["judged"], row["right"], row["absurd"]), (12, 0, 12))
        self.assertIn('  absurd cards with this commit: 12 listed', "\n".join(lines))

    def test_the_budget_stops_the_calls(self) -> None:
        asker = audit_search.Asker(object(), 0.0015, _fake_ask)
        lines: list[str] = []
        audit_search.judge(self.prepared, [], {"this commit": []}, asker=asker, out=lines.append)
        self.assertGreater(asker.stopped, 0)
        self.assertLessEqual(asker.calls, 2 + audit_search.WORKERS)


class WorkflowTests(unittest.TestCase):
    def test_the_workflow_runs_only_when_turned_on_within_its_budget(self) -> None:
        text = (ROOT / ".github" / "workflows" / "search-audit.yml").read_text(encoding="utf-8")
        self.assertIn("    branches: [ccr-4f47068a-99ikwe]", text)
        self.assertIn("      - '.github/workflows/search-audit.yml'", text)
        self.assertIn("    if: false\n", text)
        self.assertIn("      BUDGET: '3.00'", text)
        self.assertIn("      COMPARE_WITH: 75fd3d0", text)
        self.assertIn("  group: server-setup", text)
        for part in ("audit_search.py searches", "audit_search.py cards", "--src \"$RUNNER_TEMP/rules-before\"",
                     "audit_search.py judge", "--budget \"$BUDGET\""):
            self.assertIn(part, text)
        self.assertIn("ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}", text)
        self.assertIn("--require-hashes", text)
        self.assertIn("::add-mask::", text)
        self.assertIn("rm -f ~/.ssh/deploy_key ~/.ssh/config", text)


class ScriptTests(unittest.TestCase):
    def test_the_three_parts_from_the_command_line_with_a_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            catalogue = Path(folder) / "catalogue.json.gz"
            searches = Path(folder) / "searches.json"
            cards = Path(folder) / "cards.json"
            _write(catalogue)
            env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}
            for part in (["searches", str(catalogue), str(searches)],
                         ["cards", str(catalogue), str(searches), str(cards)],
                         ["judge", str(catalogue), str(searches), str(cards), "--before", str(cards),
                          "--before-name", "75fd3d0", "--dry-run"]):
                done = subprocess.run([sys.executable, str(SCRIPT), *part], capture_output=True, text=True,
                                      check=False, timeout=900, env=env)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertNotIn("shop.invalid", done.stdout)
            self.assertTrue(json.loads(searches.read_text(encoding="utf-8")))
            self.assertTrue(json.loads(cards.read_text(encoding="utf-8")))
            self.assertIn("the AI: not asked (a dry run, or no key)", done.stdout)
            self.assertIn("to ask: ", done.stdout)
            self.assertIn("75fd3d0: ", done.stdout)
            self.assertIn("this commit: ", done.stdout)


if __name__ == "__main__":
    unittest.main()
