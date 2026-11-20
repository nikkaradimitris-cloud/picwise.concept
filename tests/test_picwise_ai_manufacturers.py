"""The manufacturers' file, the AI's part: PicWise's kinds as the model reads them, the answers
it checks, and the trial on 200 brands (`picwise_ai.manufacturers`,
`deployment/server/measure_manufacturers.py`; owner, 2026-11-20: «Από το AI, με δοκιμή
πρώτα», a trial on 200 brands under $1 before the whole)."""
from __future__ import annotations

import io
import sys
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import measure_manufacturers  # noqa: E402
from picwise_ai import manufacturers  # noqa: E402
from picwise_ai.client import Asked  # noqa: E402
from picwise_nlu.concept_understanding import ACCESSORY_MARKER  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402

KINDS = manufacturers.kinds_list()


def _number(concept_id: str) -> int:
    return [kind for kind, _name in KINDS].index(concept_id) + 1


def _kind(concept_id: str) -> dict:
    return {"k": _number(concept_id), "name": KINDS[_number(concept_id) - 1][1]}


def _asked(answer, *, cost=0.002, error="") -> Asked:
    return Asked(answer, "end_turn", manufacturers.MODEL, 1000, 300, 0, 0, cost, 3.0, error)


def _product(pid: str, title: str, brand: str, shop: str = "Shop One") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=title,
        brand=brand,
        category_text="",
        product_url="",
        image_url="",
        price_text="9.99",
        availability_text="in stock",
        currency="GBP",
        raw={"merchant_name": shop},
    )


class KindsTests(unittest.TestCase):
    def test_the_kinds_are_the_searchs_own_each_name_once(self) -> None:
        names = [name for _kind, name in KINDS]
        self.assertGreater(len(KINDS), 250)
        self.assertEqual(len(names), len(set(names)))
        self.assertIn(("vacuum_cleaner", "vacuum cleaner"), KINDS)
        self.assertIn(("television", "tv"), KINDS)

    def test_the_list_numbers_each_kind(self) -> None:
        lines = manufacturers.kinds_text(KINDS).splitlines()
        self.assertEqual(lines[_number("vacuum_cleaner") - 1], f"{_number('vacuum_cleaner')} vacuum cleaner")
        self.assertEqual(len(lines), len(KINDS))


class RequestTests(unittest.TestCase):
    def test_the_instructions_and_the_kinds_are_the_same_on_every_call_and_cached(self) -> None:
        one = manufacturers.request_kwargs([{"name": "Dyson"}])
        two = manufacturers.request_kwargs([{"name": "Samsung", "titles": ["Samsung 55in TV"]}, {"name": "Bosch"}])
        self.assertEqual(one["system"], two["system"])
        self.assertEqual(one["system"][-1]["cache_control"], {"type": "ephemeral"})
        self.assertEqual(one["model"], "claude-haiku-5-5")
        self.assertEqual(one["output_config"]["effort"], "low")
        self.assertEqual(one["output_config"]["format"], {"type": "json_schema", "schema": manufacturers.SCHEMA})
        self.assertNotEqual(one["messages"], two["messages"])

    def test_each_brand_is_numbered_with_its_name_and_a_few_titles(self) -> None:
        message = manufacturers.user_message(
            [{"name": "Samsung", "titles": ["Samsung 55in TV", "Samsung Galaxy S25", "Samsung Monitor", "Samsung Buds"]},
             {"name": "Dyson", "titles": []}]
        )
        self.assertEqual(
            message.splitlines(),
            [
                "Brands (2):",
                "1. Samsung | its products here: Samsung 55in TV; Samsung Galaxy S25; Samsung Monitor",
                "2. Dyson",
            ],
        )

    def test_a_long_name_or_title_is_cut(self) -> None:
        line = manufacturers.brand_line(1, {"name": "x" * 200, "titles": ["y" * 300]})
        self.assertLess(len(line), manufacturers.NAME_CHARS + manufacturers.TITLE_CHARS + 40)
        self.assertIn("…", line)


class CheckedTests(unittest.TestCase):
    def test_a_makers_kinds_are_taken_when_number_and_name_agree(self) -> None:
        answer = {"brands": [{"n": 1, "status": "maker", "kinds": [_kind("vacuum_cleaner"), _kind("hair_dryer")],
                              "others": ["Hair Straightener Brush", "  "]}]}
        self.assertEqual(
            manufacturers.checked_brands(answer, 1, KINDS),
            {1: ("maker", ("vacuum_cleaner", "hair_dryer"), ("hair straightener brush",))},
        )

    def test_a_kind_whose_number_names_another_is_left_out(self) -> None:
        wrong = {"k": _number("kettle"), "name": "vacuum cleaner"}
        answer = {"brands": [{"n": 1, "status": "maker", "kinds": [wrong, _kind("toaster"), _kind("toaster"),
                                                                     {"k": 0, "name": "x"}, {"k": 10_000, "name": "x"}],
                              "others": []}]}
        self.assertEqual(manufacturers.checked_brands(answer, 1, KINDS), {1: ("maker", ("toaster",), ())})

    def test_a_shop_or_an_unknown_brand_keeps_no_kind(self) -> None:
        answer = {"brands": [
            {"n": 1, "status": "shop", "kinds": [_kind("kettle")], "others": ["mugs"]},
            {"n": 2, "status": "unknown", "kinds": [], "others": []},
        ]}
        self.assertEqual(manufacturers.checked_brands(answer, 2, KINDS), {1: ("shop", (), ()), 2: ("unknown", (), ())})

    def test_brands_answered_twice_out_of_range_or_of_no_status_are_left_out(self) -> None:
        answer = {"brands": [
            {"n": 1, "status": "maker", "kinds": [_kind("kettle")], "others": []},
            {"n": 1, "status": "maker", "kinds": [_kind("toaster")], "others": []},
            {"n": 2, "status": "brand", "kinds": [], "others": []},
            {"n": 3, "status": "maker", "kinds": [_kind("kettle")], "others": []},
            {"n": True, "status": "maker", "kinds": [], "others": []},
            "not a brand",
        ]}
        self.assertEqual(manufacturers.checked_brands(answer, 2, KINDS), {})
        self.assertEqual(manufacturers.checked_brands(None, 2, KINDS), {})
        self.assertEqual(manufacturers.checked_brands({"brands": "x"}, 2, KINDS), {})

    def test_at_most_so_many_kinds_and_others(self) -> None:
        many = [{"k": number, "name": name} for number, (_kind, name) in enumerate(KINDS[:20], 1)]
        answer = {"brands": [{"n": 1, "status": "maker", "kinds": many, "others": [f"thing {i}" for i in range(9)]}]}
        status, kinds, others = manufacturers.checked_brands(answer, 1, KINDS)[1]
        self.assertEqual(len(kinds), manufacturers.MOST_KINDS)
        self.assertEqual(kinds[0], KINDS[0][0])
        self.assertEqual(len(others), manufacturers.MOST_OTHERS)


class TrialTests(unittest.TestCase):
    def _prepared(self) -> types.SimpleNamespace:
        products = [
            _product("1", "Fixturon 55in Smart TV", "Fixturon"),
            _product("2", "Fixturon 50in Smart TV", "Fixturon"),
            _product("3", "Fixturon 27in Monitor", "Fixturon"),
            _product("4", "Fixturon TV Remote", "Fixturon"),
            _product("5", "Shopco Mug", "Shopco", "Shopco"),
            _product("6", "Shopco Cup", "Shopco", "Shopco"),
            _product("7", "Shopco Bowl", "Shopco", "Shopco"),
            _product("8", "Dyson V8 Filter", "Dyson"),
            _product("9", "Dyson V10 Filter", "Dyson"),
            _product("10", "Dyson Wand", "Dyson"),
        ]
        kinds = [frozenset({"television"}), frozenset({"television"}), frozenset({"monitor"}),
                 frozenset({ACCESSORY_MARKER, "television"}), frozenset(), frozenset(), frozenset(),
                 frozenset({ACCESSORY_MARKER}), frozenset({ACCESSORY_MARKER}), frozenset({ACCESSORY_MARKER})]
        return types.SimpleNamespace(products=products, kinds=kinds)

    def test_the_examples_first_then_the_largest_each_with_its_main_products_first(self) -> None:
        chosen = measure_manufacturers.pick(self._prepared(), 30)
        by_key = {item.key: item for item in chosen}
        self.assertEqual(chosen[0].key, "dyson")
        self.assertEqual(by_key["dyson"].products, 3)
        self.assertEqual(by_key["dyson"].titles, ("Dyson V8 Filter", "Dyson V10 Filter", "Dyson Wand"))
        # A maker our shops do not sell is asked by its name alone.
        self.assertEqual((by_key["miele"].name, by_key["miele"].products, by_key["miele"].titles), ("Miele", 0, ()))
        self.assertEqual(by_key["lecreuset"].name, "Le Creuset")
        self.assertEqual(by_key["fixturon"].titles,
                         ("Fixturon 55in Smart TV", "Fixturon 27in Monitor", "Fixturon 50in Smart TV"))
        self.assertTrue(by_key["shopco"].shops_own)
        self.assertFalse(by_key["fixturon"].shops_own)
        self.assertEqual(len(chosen), len(measure_manufacturers.EXAMPLES) + 2)

    def test_the_answers_are_written_into_the_brands_and_the_budget_stops_the_calls(self) -> None:
        chosen = measure_manufacturers.pick(self._prepared(), 30)
        sent = []

        def ask(request):
            sent.append(request)
            count = len(request["messages"][0]["content"].splitlines()) - 1
            return _asked({"brands": [{"n": n, "status": "maker", "kinds": [_kind("television")], "others": []}
                                      for n in range(1, count + 1)]}, cost=0.30)

        with redirect_stdout(io.StringIO()):
            totals, unasked = measure_manufacturers.run(chosen, per_call=5, ask_fn=ask, budget=1.00)
        # 0.30 a call, guessed at 0.45: the third would pass the dollar.
        self.assertEqual((len(sent), unasked, totals.calls), (2, 2, 2))
        self.assertEqual(chosen[0].status, "maker")
        self.assertEqual(chosen[0].ai_kinds, ("television",))
        self.assertEqual(chosen[-1].status, "")

    def test_the_report_counts_and_compares_with_the_catalogue(self) -> None:
        chosen = measure_manufacturers.pick(self._prepared(), 30)
        answers = {
            "fixturon": ("maker", ("television", "monitor"), ()),
            "shopco": ("shop", (), ()),
            "dyson": ("maker", ("vacuum_cleaner", "hair_dryer"), ("hair straightener brush",)),
        }
        for item in chosen:
            item.status, item.ai_kinds, item.others = answers.get(item.key, ("unknown", (), ()))
        report = "\n".join(measure_manufacturers.report(chosen, measure_manufacturers.Totals(calls=1, cost=0.01), 0))
        self.assertIn("maker 2, a shop's own name 1, unknown", report)
        self.assertIn("the AI's kinds hold it (or a broader or narrower kind) for 0 of 0", report)
        self.assertIn("the AI: maker 0, shop 1, unknown 0", report)
        self.assertIn("Dyson (3 here: no kind): maker; makes vacuum cleaner, hair dryer; and hair straightener brush",
                      report)
        self.assertNotIn("http", report)

    def test_without_a_catalogue_nothing_is_asked(self) -> None:
        with redirect_stdout(io.StringIO()) as printed:
            code = measure_manufacturers.main(["/nonexistent/catalogue.json.gz", "--dry-run"])
        self.assertEqual(code, 1)
        self.assertIn("not a prepared catalogue", printed.getvalue())


class WorkflowTests(unittest.TestCase):
    text = (ROOT / ".github" / "workflows" / "brands-ai-trial.yml").read_text(encoding="utf-8")

    def test_it_runs_only_when_its_own_file_is_pushed_to_the_brands_branch(self) -> None:
        self.assertIn("    branches: [claude/brands-2026-11-20]\n    paths:\n      - '.github/workflows/brands-ai-trial.yml'\n",
                      self.text)
        self.assertNotIn("workflow_dispatch", self.text)
        self.assertIn("permissions:\n  contents: read\n", self.text)
        self.assertIn("concurrency:\n  group: server-setup\n  cancel-in-progress: false\n", self.text)

    def test_the_owners_budget_and_the_key_only_where_the_ai_is_asked(self) -> None:
        budget = float(self.text.split("BUDGET: '", 1)[1].split("'", 1)[0])
        self.assertLessEqual(budget, 1.00)
        self.assertEqual(self.text.count("secrets.ANTHROPIC_API_KEY"), 1)
        asking = self.text.split("- name: 200 brands", 1)[1].split("- name:", 1)[0]
        self.assertIn("ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}", asking)
        self.assertIn("--require-hashes", self.text)
        cleanup = self.text.split("- name: Remove the key and the copy from the runner", 1)[1]
        self.assertIn("rm -f ~/.ssh/deploy_key ~/.ssh/config \"$RUNNER_TEMP/catalogue.json.gz\"", cleanup)
        self.assertIn("if: always()", cleanup)


if __name__ == "__main__":
    unittest.main()
