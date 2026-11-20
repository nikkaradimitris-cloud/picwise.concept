"""The products whose AI line is in doubt, asked again with more care
(`deployment/server/reask_shelves.py`; owner, 2026-11-20 20:51: «Πρώτα διόρθωση: να
ξαναρωτηθεί το AI μόνο για τα περίπου 16.000 προϊόντα ... και μετά νέα μέτρηση»)."""
from __future__ import annotations

import gzip
import json
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import reask_shelves  # noqa: E402
import scan_shelves  # noqa: E402
from picwise_ai import shelves  # noqa: E402
from picwise_providers.ai_shelves import _levels  # noqa: E402

LINES = shelves.taxonomy_lines()
NUMBER = {line: number for number, line in enumerate(LINES, 1)}
WATCHES = "Apparel & Accessories > Jewelry > Watches"
BANDS = "Apparel & Accessories > Jewelry > Watch Accessories > Watch Bands"
TYRES = "Vehicles & Parts > Vehicle Parts & Accessories > Motor Vehicle Parts > Motor Vehicle Wheel Systems > Motor Vehicle Tires"
HARDTOPS = "Vehicles & Parts > Vehicle Parts & Accessories > Motor Vehicle Parts > Motor Vehicle Frame & Body Parts"
LISTS = {"watch": ((_levels(WATCHES), False),), "tyres": ((_levels(TYRES), False),)}


class DoubtedTests(unittest.TestCase):
    def test_a_slip_and_a_line_off_its_kinds_list_are_asked_again(self) -> None:
        rows = [
            ("slip", frozenset({"watch"})),
            ("strap", frozenset({"watch"})),
            ("tyre", frozenset({"tyres", "__pet__"})),
            ("watch", frozenset({"watch"})),
            ("unlisted", frozenset({"laptop"})),
            ("unasked", frozenset({"watch"})),
            ("no kind", frozenset({"__uncertain_kind__"})),
        ]
        lines = {"slip": "Animals & Pet Supplies", "strap": BANDS, "tyre": HARDTOPS, "watch": WATCHES,
                 "unlisted": BANDS, "unasked": None, "no kind": "Animals & Pet Supplies > Live Animals"}
        found = reask_shelves.doubted_keys(rows, lines, LISTS)
        self.assertEqual(found, {"slip": "slip", "strap": "taken", "tyre": "taken", "no kind": "slip"})

    def test_a_key_is_taken_when_any_of_its_kinds_lists_does_not_hold_it(self) -> None:
        found = reask_shelves.doubted_keys([("k", frozenset({"watch", "tyres"}))], {"k": WATCHES}, LISTS)
        self.assertEqual(found, {"k": "taken"})


class SettleTests(unittest.TestCase):
    def test_a_new_line_keeps_the_old_beside_it_a_refusal_keeps_the_old(self) -> None:
        before = {
            "a": {"k": "a", "line": HARDTOPS, "tries": 1},
            "b": {"k": "b", "line": "Animals & Pet Supplies", "tries": 1},
            "c": {"k": "c", "line": WATCHES, "tries": 1},
        }
        answers = dict(before)
        answers["a"] = {"k": "a", "line": TYRES, "tries": 1}
        answers["c"] = {"k": "c", "line": WATCHES, "tries": 1}
        tally = reask_shelves.settle(["a", "b", "c"], before, answers, "2026-11-20")
        self.assertEqual(answers["a"]["line"], TYRES)
        self.assertEqual(answers["a"]["was"], HARDTOPS)
        self.assertEqual(answers["a"]["again"], "2026-11-20")
        self.assertIs(answers["b"], before["b"])
        self.assertEqual(tally, {"another line": 1, "kept (refused or not asked)": 1, "the same line": 1})


class CarefulTests(unittest.TestCase):
    def test_the_careful_question_says_more_and_thinks_more_the_scans_is_the_same(self) -> None:
        items = [{"title": "Toyo Proxes Comfort 195/50 R15 82H", "brand": "Toyo"}]
        plain = shelves.request_kwargs(items, LINES)
        careful = shelves.request_kwargs(items, LINES, effort="medium", careful=True)
        self.assertEqual(plain["system"][0]["text"], shelves.SYSTEM_PROMPT)
        self.assertEqual(plain["output_config"]["effort"], shelves.EFFORT)
        self.assertTrue(careful["system"][0]["text"].startswith(shelves.SYSTEM_PROMPT))
        self.assertIn("A car tyre is on the line of tyres", careful["system"][0]["text"])
        self.assertEqual(careful["output_config"]["effort"], "medium")
        self.assertEqual(careful["system"][1], plain["system"][1])

    def test_the_round_asks_with_the_careful_question_and_settles(self) -> None:
        groups = {
            "a": scan_shelves.Group("a", {"title": "Toyo Proxes Comfort"}, "Shop", "Toyo Proxes Comfort", True, ""),
            "b": scan_shelves.Group("b", {"title": "Nokian Seasonproof"}, "Shop", "Nokian Seasonproof", True, ""),
        }
        before = {"a": {"k": "a", "line": HARDTOPS, "tries": 1}, "b": {"k": "b", "line": HARDTOPS, "tries": 1}}
        answers = dict(before)
        seen: list[dict] = []

        def ask_fn(request):
            seen.append(request)
            # "a" answered with the tyres' line; "b" refused (a name of no line).
            answer = {"products": [{"n": 1, "line": NUMBER[TYRES], "name": "Motor Vehicle Tires"},
                                   {"n": 2, "line": 1, "name": "No Such Line"}]}
            return SimpleNamespace(answer=answer, error="", cost_usd=0.003, input_tokens=1, output_tokens=1,
                                   cache_write_tokens=0, cache_read_tokens=0, seconds=0.1, stop_reason=""), ""

        asking = scan_shelves.Asking(
            ask_fn=ask_fn, groups=groups, answers=answers, lines=LINES, workers=1, budget=1.0,
            deadline=time.monotonic() + 60, clock=time.monotonic, sleep=lambda seconds: None,
            request_fn=lambda items, lines: shelves.request_kwargs(items, lines, effort="medium", careful=True),
        )
        failed = scan_shelves.run_round(asking, ["a", "b"], 30, label="asked again")
        self.assertEqual(failed, ["b"])
        self.assertIn("A car tyre", seen[0]["system"][0]["text"])
        today = datetime.now(timezone.utc).date().isoformat()
        tally = reask_shelves.settle(["a", "b"], before, answers, today)
        self.assertEqual((answers["a"]["line"], answers["a"]["was"]), (TYRES, HARDTOPS))
        self.assertIs(answers["b"], before["b"])
        self.assertEqual(tally["another line"], 1)


class DryRunTests(unittest.TestCase):
    def test_a_dry_run_reads_the_catalogue_and_the_answers_and_asks_nothing(self) -> None:
        from picwise_ai.shelves import ask_key, shop_words
        from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct
        from picwise_providers.offer_health import build_feed_availability_context
        from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue

        def product(number: int, title: str) -> ProviderProduct:
            return ProviderProduct(
                provider_key="awin", provider_product_id=f"row-{number}", title=title, brand="Acme",
                category_text=WATCHES, product_url=f"https://shop.invalid/p/{number}",
                image_url=f"https://shop.invalid/i/{number}.jpg", price_text="9.00", availability_text="in stock",
                currency="GBP", raw={"merchant_name": "Shop", "product_type": "Watches", "google_product_category": WATCHES},
            )

        products = [product(1, "Nato Strap 20mm"), product(2, "Casio Classic Watch")]
        prepared = PreparedCatalogue(
            prepared_at=datetime(2026, 11, 20, 12, 6, tzinfo=timezone.utc),
            feed_status=ProviderFeedStatus(status="ok", provider_key="awin", product_count=2),
            availability_context=build_feed_availability_context(tuple(products)),
            products=tuple(products), non_new=("", ""),
            kinds=(frozenset({"watch"}), frozenset({"watch"})), eligible_count=2, shop_count=1, suggestions=(),
        )
        with tempfile.TemporaryDirectory() as folder:
            catalogue = Path(folder) / "catalogue.json.gz"
            kept = Path(folder) / "kept.jsonl.gz"
            out = Path(folder) / "out.jsonl.gz"
            write_prepared_catalogue(prepared, catalogue)
            with gzip.open(kept, "wt", encoding="utf-8") as handle:
                for item, line in ((products[0], BANDS), (products[1], WATCHES)):
                    handle.write(json.dumps({"k": ask_key(item.title, item.brand, shop_words(item.raw)), "line": line}) + "\n")
            self.assertEqual(reask_shelves.main([str(catalogue), "--answers", str(kept), "--out", str(out), "--dry-run"]), 0)
            self.assertFalse(out.exists())


class WorkflowTests(unittest.TestCase):
    workflow = (ROOT / ".github" / "workflows" / "ai-shelves-reask.yml").read_text(encoding="utf-8")

    def test_it_runs_on_its_own_branch_keeps_the_answers_before_and_removes_the_copies(self) -> None:
        self.assertIn("branches: [claude/shelves-reask]", self.workflow)
        self.assertEqual(self.workflow.count("secrets.ANTHROPIC_API_KEY"), 1)
        self.assertIn("group: shelves-scan", self.workflow)
        self.assertIn("answers.before-reask.jsonl.gz", self.workflow)
        self.assertLess(self.workflow.index("answers.before-reask"), self.workflow.index("sudo mv -f"))
        self.assertIn("BUDGET: '1.20'", self.workflow)
        self.assertNotIn("upload-artifact", self.workflow)
        self.assertIn("rm -f ~/.ssh/deploy_key", self.workflow)


if __name__ == "__main__":
    unittest.main()
