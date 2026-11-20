"""Each kind of the site its own lines of Google's taxonomy, written once by the AI
(`picwise_ai.kind_lines`, `deployment/server/write_kind_lines.py`; owner, 2026-11-20:
«Κάθε είδος του site να έχει τη δική του λίστα κατηγοριών Google ... Τη λίστα να τη φτιάξει
το AI μία φορά ... και να ελεγχθεί»)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import write_kind_lines  # noqa: E402
from picwise_ai import kind_lines  # noqa: E402
from picwise_ai.shelves import taxonomy_lines  # noqa: E402
from picwise_nlu.product_concepts import get_product_concepts  # noqa: E402

LINES = taxonomy_lines()
NUMBER = {line: number for number, line in enumerate(LINES, 1)}
TABLETS = "Electronics > Computers > Tablet Computers"
WATCHES = "Apparel & Accessories > Jewelry > Watches"
BANDS = "Apparel & Accessories > Jewelry > Watch Accessories > Watch Bands"
KETTLES = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Electric Kettles"


class KindsTests(unittest.TestCase):
    def test_every_kind_once_with_its_names_department_and_relations(self) -> None:
        kinds = kind_lines.kinds_described()
        self.assertEqual([kind["id"] for kind in kinds], [concept.concept_id for concept in get_product_concepts()])
        by_id = {kind["id"]: kind for kind in kinds}
        self.assertIn("smartwatch (smartwatch)", by_id["watch"]["narrower"])
        self.assertEqual(by_id["smartwatch"]["part_of"], ["watch (watch)"])
        self.assertIn("ipad", by_id["tablet"]["names"])
        self.assertIn("a kind of: watch (watch)", kind_lines.kind_line(1, by_id["smartwatch"]))

    def test_each_call_one_department_every_kind_once(self) -> None:
        kinds = kind_lines.kinds_described()
        calls = kind_lines.batches(kinds)
        self.assertEqual(sorted(kind["id"] for call in calls for kind in call), sorted(kind["id"] for kind in kinds))
        for call in calls:
            self.assertLessEqual(len(call), kind_lines.PER_CALL)
            self.assertEqual(len({kind["department"] for kind in call}), 1)

    def test_the_request_caches_the_tree_and_names_every_kind(self) -> None:
        kinds = [kind for kind in kind_lines.kinds_described() if kind["id"] in ("tablet", "watch")]
        request = kind_lines.request_kwargs(kinds, LINES)
        self.assertEqual(request["model"], "claude-haiku-5-5")
        self.assertEqual(request["system"][1]["cache_control"], {"type": "ephemeral"})
        self.assertIn(f"{NUMBER[TABLETS]} Tablet Computers", request["system"][1]["text"])
        text = request["messages"][0]["content"]
        self.assertIn("id: tablet", text)
        self.assertIn("id: watch", text)
        self.assertEqual(request["output_config"]["format"]["schema"], kind_lines.SCHEMA)
        self.assertIn("never a part", kind_lines.SYSTEM_PROMPT)


class EvidenceTests(unittest.TestCase):
    def test_the_lines_of_the_products_read_as_a_kind_the_most_given_first(self) -> None:
        rows = [
            (frozenset({"watch", "__pet__"}), WATCHES, "Casio Classic"),
            (frozenset({"watch"}), WATCHES, "Diesel Mega Chief"),
            (frozenset({"watch"}), BANDS, "Nato Strap 20mm"),
            (frozenset({"watch"}), None, "Not asked"),
            (frozenset({"__uncertain_kind__"}), BANDS, "Doubtful"),
        ]
        found = kind_lines.evidence(rows)
        self.assertEqual(found, {"watch": [(WATCHES, 2, ["Casio Classic", "Diesel Mega Chief"]), (BANDS, 1, ["Nato Strap 20mm"])]})

    def test_the_check_asks_only_the_lines_the_list_does_not_hold(self) -> None:
        seen = [(WATCHES, 900, ["Casio Classic"]), (BANDS, 40, ["Nato Strap"]),
                ("Apparel & Accessories > Jewelry", 5, ["Gift Watch"])]
        self.assertEqual(kind_lines.candidates(seen, ["Apparel & Accessories > Jewelry > Watches"]), seen[1:])
        self.assertEqual(kind_lines.candidates(seen, ["Apparel & Accessories > Jewelry"]), [])

    def test_the_check_shows_each_line_with_its_products_and_no_taxonomy(self) -> None:
        kinds = [kind for kind in kind_lines.kinds_described() if kind["id"] == "watch"]
        request = kind_lines.judge_request([(kinds[0], [(BANDS, 40, ["Nato Strap", "Leather Band"])])])
        text = request["messages"][0]["content"]
        self.assertIn("1. id: watch | names: watch", text)
        self.assertIn(f'   1. {BANDS}: 40 products, e.g. "Nato Strap" / "Leather Band"', text)
        self.assertEqual(len(request["system"]), 1)
        self.assertNotIn("taxonomy:", request["system"][0]["text"])
        self.assertEqual(request["output_config"]["format"]["schema"], kind_lines.JUDGE_SCHEMA)
        self.assertNotIn("products", kind_lines.user_message(kinds))

    def test_each_line_answered_once_is_kept(self) -> None:
        watch = {"id": "watch", "names": ["watch"]}
        kettle = {"id": "kettle", "names": ["kettle"]}
        items = [(watch, [(BANDS, 4, []), (WATCHES, 3, []), (TABLETS, 1, [])]), (kettle, [(KETTLES, 2, [])])]
        answer = {"kinds": [
            {"id": "watch", "answers": [{"n": 1, "answer": "no"}, {"n": 2, "answer": "yes"}, {"n": 3, "answer": "yes"},
                                        {"n": 3, "answer": "no"}, {"n": 9, "answer": "yes"}]},
            {"id": "kettle", "answers": [{"n": 1, "answer": "yes"}]},
            {"id": "kettle", "answers": []},
            {"id": "tablet", "answers": [{"n": 1, "answer": "yes"}]},
        ]}
        self.assertEqual(kind_lines.checked_judgements(answer, items), {"watch": {BANDS: "no", WATCHES: "yes"}})
        self.assertEqual(kind_lines.checked_judgements(None, items), {})


class SeenInTests(unittest.TestCase):
    def test_a_prepared_file_and_the_scans_answers_give_each_kinds_lines(self) -> None:
        import gzip
        from datetime import datetime, timezone

        from picwise_ai.shelves import ask_key, shop_words
        from picwise_providers.contracts import ProviderFeedStatus, ProviderProduct
        from picwise_providers.offer_health import build_feed_availability_context
        from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue

        def product(number: int, title: str, google: str) -> ProviderProduct:
            return ProviderProduct(
                provider_key="awin", provider_product_id=f"row-{number}", title=title, brand="Acme",
                category_text=google, product_url=f"https://shop.invalid/p/{number}",
                image_url=f"https://shop.invalid/i/{number}.jpg", price_text="9.00", availability_text="in stock",
                currency="GBP", raw={"merchant_name": "Shop", "product_type": "Watches", "google_product_category": google},
            )

        products = [product(1, "Casio Classic Watch", WATCHES), product(2, "Nato Strap 20mm", WATCHES),
                    product(3, "Unasked Watch", WATCHES)]
        prepared = PreparedCatalogue(
            prepared_at=datetime(2026, 11, 20, 12, 6, tzinfo=timezone.utc),
            feed_status=ProviderFeedStatus(status="ok", provider_key="awin", product_count=3),
            availability_context=build_feed_availability_context(tuple(products)),
            products=tuple(products), non_new=("", "", ""),
            kinds=(frozenset({"watch"}), frozenset({"watch"}), frozenset({"watch"})),
            eligible_count=3, shop_count=1, suggestions=(),
        )
        with tempfile.TemporaryDirectory() as folder:
            catalogue = Path(folder) / "catalogue.json.gz"
            answers = Path(folder) / "answers.jsonl.gz"
            write_prepared_catalogue(prepared, catalogue)
            with gzip.open(answers, "wt", encoding="utf-8") as handle:
                for item, line in ((products[0], WATCHES), (products[1], BANDS)):
                    key = ask_key(item.title, item.brand, shop_words(item.raw))
                    handle.write(json.dumps({"k": key, "line": line}) + "\n")
            found, note = write_kind_lines.seen_in(catalogue, answers)
        self.assertEqual(found, {"watch": [(WATCHES, 1, ["Casio Classic Watch"]), (BANDS, 1, ["Nato Strap 20mm"])]})
        self.assertIn("3 products, 2 with a line of the AI; 1 kinds", note)


class CheckTests(unittest.TestCase):
    def test_a_line_whose_number_and_name_agree(self) -> None:
        answer = {"kinds": [
            {"id": "tablet", "lines": [{"line": NUMBER[TABLETS], "name": "Tablet Computers"}]},
            {"id": "watch", "lines": [{"line": NUMBER[WATCHES], "name": "Watches"}]},
        ]}
        found, refused = kind_lines.checked_kind_lines(answer, ["tablet", "watch"], LINES)
        self.assertEqual(found, {"tablet": [TABLETS], "watch": [WATCHES]})
        self.assertEqual(refused, 0)

    def test_a_miscopied_number_is_read_by_the_name_in_its_department_else_refused(self) -> None:
        answer = {"kinds": [
            # The number of the watch bands, the name of the watches: the same department.
            {"id": "watch", "lines": [{"line": NUMBER[BANDS], "name": "Watches"}]},
            # The number of the watches, the name of the tablets: another department.
            {"id": "tablet", "lines": [{"line": NUMBER[WATCHES], "name": "Tablet Computers"},
                                       {"line": 12, "name": "No Such Line"}, {"line": "x", "name": "Watches"}]},
            {"id": "kettle", "lines": [{"line": 999999, "name": "Electric Kettles"}]},
        ]}
        found, refused = kind_lines.checked_kind_lines(answer, ["watch", "tablet", "kettle"], LINES)
        self.assertEqual(found["watch"], [WATCHES])
        self.assertEqual(found["tablet"], [])
        self.assertEqual(found["kettle"], [KETTLES])
        self.assertEqual(refused, 3)

    def test_a_kind_answered_twice_or_not_asked_is_left_out_an_empty_list_kept(self) -> None:
        answer = {"kinds": [
            {"id": "tablet", "lines": [{"line": NUMBER[TABLETS], "name": "Tablet Computers"}]},
            {"id": "tablet", "lines": []},
            {"id": "laptop", "lines": [{"line": NUMBER[TABLETS], "name": "Tablet Computers"}]},
            {"id": "software", "lines": []},
        ]}
        found, _refused = kind_lines.checked_kind_lines(answer, ["tablet", "software"], LINES)
        self.assertEqual(found, {"software": []})
        self.assertEqual(kind_lines.checked_kind_lines(None, ["tablet"], LINES), ({}, 0))

    def test_the_same_line_twice_is_kept_once(self) -> None:
        answer = {"kinds": [{"id": "tablet", "lines": [{"line": NUMBER[TABLETS], "name": "Tablet Computers"}] * 2}]}
        self.assertEqual(kind_lines.checked_kind_lines(answer, ["tablet"], LINES)[0], {"tablet": [TABLETS]})


class FormTests(unittest.TestCase):
    def test_the_lists_in_few_characters_read_back_the_same(self) -> None:
        found = {"tablet": [TABLETS], "watch": [WATCHES, BANDS], "software": []}
        text = kind_lines.compact(found, LINES)
        self.assertIn(f"tablet={NUMBER[TABLETS]}", text)
        self.assertIn("software=", text)
        self.assertEqual(kind_lines.from_compact(text + "\nnot a row\n", LINES), found)

    def test_the_notes_keep_rows_whole(self) -> None:
        text = "\n".join(f"kind_{n}=" + ",".join(str(i) for i in range(n, n + 30)) for n in range(400))
        pieces = kind_lines.chunks(text, 3500)
        self.assertGreater(len(pieces), 1)
        self.assertTrue(all(len(piece) <= 3500 for piece in pieces))
        self.assertEqual("\n".join(pieces), text)

    def test_written_and_read_as_the_repository_keeps_them(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "lists.json"
            kind_lines.write({"tablet": [TABLETS]}, path, note={"model": "m"}, exact={"watch": [BANDS]})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["model"], "m")
            self.assertEqual(kind_lines.read(path), {"tablet": [TABLETS]})
            self.assertEqual(kind_lines.read(path, "exact"), {"watch": [BANDS]})
            self.assertEqual(kind_lines.read(Path(folder) / "none.json"), {})


class RunTests(unittest.TestCase):
    def test_every_kind_asked_and_one_not_answered_asked_again_alone(self) -> None:
        kinds = [kind for kind in kind_lines.kinds_described() if kind["id"] in ("tablet", "laptop", "watch")]
        asked: list[list[str]] = []

        def ask(request):
            text = request["messages"][0]["content"]
            ids = [row.split("id: ")[1].split(" |")[0] for row in text.splitlines()[1:]]
            asked.append(ids)
            # The first call forgets the laptop.
            given = [i for i in ids if not (i == "laptop" and len(ids) > 1)]
            return SimpleNamespace(
                answer={"kinds": [{"id": i, "lines": [{"line": NUMBER[TABLETS], "name": "Tablet Computers"}]} for i in given]},
                cost_usd=0.01, error="",
            )

        run = write_kind_lines.Run(ask, 1.0, LINES)
        write_kind_lines.run_all(run, kinds, workers=1)
        self.assertEqual(set(run.found), {"tablet", "laptop", "watch"})
        self.assertIn(["laptop"], asked)
        self.assertAlmostEqual(run.spent, 0.01 * len(asked))

    def test_the_check_adds_the_lines_judged_the_kind_itself(self) -> None:
        kinds = [kind for kind in kind_lines.kinds_described() if kind["id"] in ("watch", "kettle", "tablet")]
        by_id = {kind["id"]: kind for kind in kinds}
        by_id["watch"]["seen"] = [(WATCHES, 900, ["Casio"]), (BANDS, 40, ["Nato Strap"]),
                                  ("Apparel & Accessories > Jewelry", 6, ["Casio Gift Watch"])]
        by_id["kettle"]["seen"] = [(KETTLES, 80, ["Kettle"])]
        by_id["tablet"]["seen"] = []
        asked: list[str] = []

        def ask(request):
            text = request["messages"][0]["content"]
            asked.append(text)
            answers = []
            kind = None
            for row in text.splitlines()[1:]:
                if " id: " in row:
                    kind = {"id": row.split("id: ")[1].split(" |")[0], "answers": []}
                    answers.append(kind)
                else:
                    number = int(row.strip().split(".")[0])
                    kind["answers"].append({"n": number, "answer": "yes" if "Watch\"" in row else "no"})
            return SimpleNamespace(answer={"kinds": answers}, cost_usd=0.001, error="")

        run = write_kind_lines.Run(ask, 1.0, LINES)
        run.found = {"watch": [WATCHES], "kettle": [KETTLES], "tablet": [TABLETS]}
        self.assertEqual(write_kind_lines.judge_all(run, kinds, workers=1), 2)
        self.assertEqual(len(asked), 1)
        self.assertNotIn("Kettle", asked[0])
        self.assertEqual(run.judged, {"watch": {BANDS: "no", "Apparel & Accessories > Jewelry": "yes"}})
        self.assertEqual(run.judge_calls, 1)

    def test_it_stops_at_the_budget_and_writes_without_a_key(self) -> None:
        run = write_kind_lines.Run(lambda request: SimpleNamespace(answer=None, cost_usd=2.0, error="HTTP 500"), 1.0, LINES)
        write_kind_lines.PAUSE_SECONDS, before = 0.0, write_kind_lines.PAUSE_SECONDS
        try:
            run.one([{"id": "tablet", "names": ["tablet"], "department": "x"}])
        finally:
            write_kind_lines.PAUSE_SECONDS = before
        self.assertEqual(run.calls, 1)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "lists.json"
            self.assertEqual(write_kind_lines.main(["--out", str(out), "--dry-run"]), 0)
            self.assertEqual(kind_lines.read(out), {})


class WorkflowTests(unittest.TestCase):
    workflow = (ROOT / ".github" / "workflows" / "ai-kind-lines.yml").read_text(encoding="utf-8")

    def test_it_runs_on_its_own_branch_reads_the_server_and_changes_nothing(self) -> None:
        self.assertIn("branches: [claude/kind-lines]", self.workflow)
        self.assertEqual(self.workflow.count("secrets.ANTHROPIC_API_KEY"), 1)
        self.assertIn("contents: read", self.workflow)
        for absent in ("upload-artifact", "sudo tee", "sudo mv", "sudo install", "sudo chown"):
            self.assertNotIn(absent, self.workflow)
        self.assertIn("--require-hashes", self.workflow)
        self.assertIn("server-host-key.pin", self.workflow)
        self.assertIn("--catalogue", self.workflow)
        self.assertIn("rm -f ~/.ssh/deploy_key", self.workflow)


if __name__ == "__main__":
    unittest.main()
