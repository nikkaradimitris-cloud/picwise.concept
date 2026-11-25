"""The night's preparation lets go of the rows that can never be shown as soon as every row
is judged, and prepares the same catalogue (owner, 2026-11-25: «Να χειρίζονται σε πακέτα
τα προϊόντα»).

The measure of 2026-11-25 (`tools/measure_prepare_memory.py`, both Awin links on GitHub's
runner): of 2,685,295 rows, 1,095,175 were never eligible, yet stayed in memory to the end,
held by the pipeline's cache for the intake measured after the catalogue was written; the
peak was 13.85 GB. Pinned here (`state.prepare_feed_catalogue`, `measure_intake`): the intake
is measured once every row is judged and is the same measure as before; the rows never shown
are let go before the search catalogue, the kinds and the cap; and the catalogue prepared is
the same, product for product, in the same order.

Every row is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import csv
import gc
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
import weakref
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fixture_support import fixture_description  # noqa: E402
from picwise_providers import awin_adapter, state  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.contracts import ProviderFeedConfig  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "product_type", "merchant_category", "aw_deep_link",
    "aw_image_url", "search_price", "currency", "in_stock", "merchant_name", "description",
)
_ENV = ("AWIN_FEED_FILE", "AWIN_FEED_URL", "AWIN_FEED_FILE_AWIN", "AWIN_FEED_URL_AWIN")


def _load_tool():
    spec = importlib.util.spec_from_file_location("prepare_catalogue_lets_go_tool", ROOT / "tools" / "prepare_catalogue.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fresh() -> None:
    clear_awin_feed_parse_cache()
    clear_provider_feed_pipeline_cache()
    state._CATALOGUE_CACHE.clear()


class LetsGoOfRowsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        saved = {name: os.environ.get(name) for name in _ENV}

        def restore() -> None:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            state._LAST_INTAKE = None
            _fresh()

        self.addCleanup(restore)
        for name in _ENV:
            os.environ.pop(name, None)
        self.feed = self.folder / "the-shops-feed.csv"
        self.never_shown: set[str] = set()
        with self.feed.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for shop, rows in {"Alpha Shop": 24, "Beta Shop": 18}.items():
                for number in range(rows):
                    pid = f"{shop.split()[0].lower()}-{number}"
                    image = f"https://fixture.example.invalid/img/{pid}.jpg"
                    price, currency = f"{10 + number}.00", "GBP"
                    # Two rows of every three can never be shown: one has no photo, one no price.
                    if number % 3 == 1:
                        image = ""
                        self.never_shown.add(pid)
                    elif number % 3 == 2:
                        price = ""
                        self.never_shown.add(pid)
                    writer.writerow([
                        pid, f"Fixturon Electric Kettle {number} 1.7L", "Fixturon", "Kettles", "Kitchen Appliances",
                        f"https://fixture.example.invalid/out/{pid}", image, price, currency, "1", shop,
                        fixture_description(),
                    ])
        self.config = ProviderFeedConfig(provider_key="awin", feed_file=str(self.feed))
        _fresh()

    def _prepare(self, measure_intake: bool):
        _fresh()
        state._LAST_INTAKE = None
        return state.prepare_feed_catalogue(self.config, measure_intake=measure_intake)

    def test_the_catalogue_is_the_same_product_for_product(self) -> None:
        before = self._prepare(measure_intake=False)
        after = self._prepare(measure_intake=True)
        self.assertIsNotNone(before)
        self.assertIsNotNone(after)
        self.assertEqual([p.provider_product_id for p in after.products], [p.provider_product_id for p in before.products])
        self.assertEqual(after.products, before.products)
        self.assertEqual(after.kinds, before.kinds)
        self.assertEqual(after.non_new, before.non_new)
        self.assertEqual(after.search_fields, before.search_fields)
        self.assertEqual((after.eligible_count, after.shop_count), (before.eligible_count, before.shop_count))
        self.assertEqual(after.suggestions, before.suggestions)
        self.assertEqual(after.choices, before.choices)
        self.assertEqual(after.feed_status, before.feed_status)
        self.assertEqual(after.availability_context, before.availability_context)
        # The rows that can never show are none of the catalogue's.
        self.assertTrue(self.never_shown)
        self.assertFalse(self.never_shown & {p.provider_product_id for p in after.products})

    def test_the_intake_is_measured_once_every_row_is_judged_and_is_the_same(self) -> None:
        self._prepare(measure_intake=True)
        measured, error = state.last_prepared_intake()
        self.assertIsNone(error)
        _fresh()
        self.assertEqual(measured, state.measure_configured_feed_intake(self.config))
        rows = {entry["shop"]: entry["rows"] for entry in measured["shops"]}
        self.assertEqual(rows, {"Alpha Shop": 24, "Beta Shop": 18})

    def test_without_the_intake_nothing_is_measured_and_the_pipeline_stays_cached(self) -> None:
        self._prepare(measure_intake=False)
        self.assertIsNone(state.last_prepared_intake())
        self.assertTrue(state._PIPELINE_CACHE)

    def test_the_rows_never_shown_are_let_go_before_the_kinds_and_the_cap(self) -> None:
        judged = state._enrich_provider_eligibility_result
        never: list[weakref.ref] = []

        def judge(product, **kwargs):
            row = judged(product, **kwargs)
            if row.status != "eligible":
                never.append(weakref.ref(row.product))
            return row

        alive_at_the_cap: list[int] = []

        def cap(products, kinds, feed_ctx):
            gc.collect()
            alive_at_the_cap.append(sum(1 for ref in never if ref() is not None))
            return None

        _fresh()
        with patch.object(state, "_enrich_provider_eligibility_result", judge):
            prepared = state.prepare_feed_catalogue(self.config, cap=cap, measure_intake=True)
        self.assertIsNotNone(prepared)
        self.assertTrue(never)
        # None of them is held by the time the cap is worked out.
        self.assertEqual(alive_at_the_cap, [0])
        # And no cache keeps the feed's rows or its pipeline.
        self.assertFalse(state._PIPELINE_CACHE)
        self.assertFalse(awin_adapter._PARSE_CACHE)
        self.assertNotIn("search_catalogue_every_photo", state._CATALOGUE_CACHE)

    def test_an_intake_that_fails_is_noted_and_the_catalogue_still_prepared(self) -> None:
        def broken(_pipeline):
            raise RuntimeError("the intake broke")

        _fresh()
        with patch.object(state, "_pipeline_intake", broken):
            prepared = state.prepare_feed_catalogue(self.config, measure_intake=True)
        self.assertIsNotNone(prepared)
        measured, error = state.last_prepared_intake()
        self.assertIsNone(measured)
        self.assertIsInstance(error, RuntimeError)
        noted = _load_tool()._intake(self.config)
        self.assertEqual(set(noted), {"error"})
        self.assertTrue(noted["error"].startswith("RuntimeError at "), noted)
        # Its text, which could quote the feed's link, is never in the note.
        self.assertNotIn("broke", noted["error"])

    def test_the_tool_reads_the_feed_once_and_writes_the_same_note(self) -> None:
        os.environ["AWIN_FEED_FILE"] = str(self.feed)
        parses: list[object] = []
        load = state.load_awin_provider_feed

        def parse(config):
            parses.append(config)
            return load(config)

        _fresh()
        printed = io.StringIO()
        with patch.object(state, "load_awin_provider_feed", parse), redirect_stdout(printed):
            code = _load_tool().main([
                "--out", str(self.folder / "catalogue.json.gz"), "--static-dir", str(self.folder / "public"),
            ])
        self.assertEqual(code, 0, printed.getvalue())
        self.assertEqual(len(parses), 1)
        note = json.loads((self.folder / "public" / "prepared.json").read_text(encoding="utf-8"))
        self.assertTrue(note["prepared"])
        rows = {entry["shop"]: entry["rows"] for entry in note["intake"]["shops"]}
        self.assertEqual(rows, {"Alpha Shop": 24, "Beta Shop": 18})
        held = sum(entry["held"] for entry in note["intake"]["shops"])
        self.assertEqual(held, len(self.never_shown))


if __name__ == "__main__":
    unittest.main()
