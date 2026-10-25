"""Step 5 of the price-first plan: the feed prepared once a day.

`src/picwise_providers/prepared_catalogue.py`, `tools/prepare_catalogue.py`. Pinned here:

- a prepared file reads back exactly what was prepared, and never the feed's link;
- pages answered from it are the pages the feed itself gives, and the feed is not read;
- a file that is too old, written by other code, in another format or broken is not
  used, and the feed is read as before;
- an offer whose validity window closed after the file was written is left out;
- the outbound redirect finds a prepared product, and nothing else;
- with a purchasability cache configured the prepared file is not used;
- a server reads a file only when one is configured, or built into a Vercel deployment;
- the readiness page says whether the server answers from a prepared file, and why not;
- a deployment's build leaves a public note of what it prepared, and a failure while
  preparing neither fails the build nor prints the error's text.

Every row is written with fictional brands and `.invalid` URLs; the page tests are
served through api/index.py, the deployed entry point.
"""
from __future__ import annotations

import csv
import gzip
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_providers import prepared_catalogue, state  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.prepared_catalogue import (  # noqa: E402
    PREPARED_CATALOGUE_ENV,
    PREPARED_MAX_AGE_ENV,
    prepared_catalogue_path,
    read_prepared_catalogue,
    write_prepared_catalogue,
)
from picwise_providers.purchasability_cache import (  # noqa: E402
    CACHE_ENV_VAR,
    clear_purchasability_cache_configuration,
    configure_purchasability_cache,
)
from picwise_providers.state import (  # noqa: E402
    clear_provider_feed_pipeline_cache,
    prepare_feed_catalogue,
    resolve_card_eligible_provider_feed_product_by_id,
    search_suggestions,
)
from test_picwise_price_first import _PageMixin, _ean  # noqa: E402

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "product_type", "merchant_category",
    "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock", "merchant_name",
    "description", "data_provenance", "ean", "condition", "valid_to",
    # Two columns no rule reads, which the prepared file leaves out (LEFT_OUT_COLUMNS).
    "aw_thumb_url", "delivery_cost",
)


def _row(pid: str, title: str, price: float, *, kind: str = "Kettles", condition: str = "",
         valid_to: str = "", code: int = 0) -> list[str]:
    return [
        pid, title, title.split()[0], kind, "Kitchen Appliances" if kind == "Kettles" else "Computers",
        f"https://fixture.example.invalid/out/{pid}", f"https://fixture.example.invalid/img/{pid}.jpg",
        f"{price:.2f}", "GBP", "1", "Fixture Store One", fixture_description(), "local_test_fixture",
        _ean(500000006000 + code) if code else "", condition, valid_to,
        f"https://fixture.example.invalid/thumb/{pid}.jpg", "3.95",
    ]


def _feed_rows(valid_to: str = "") -> list[list[str]]:
    rows = [
        _row(f"k{index}", f"Fixturon Electric Kettle {index} 1.7L", 15.0 + 5 * index, code=index)
        for index in range(1, 10)
    ]
    rows.append(_row("r1", "Fixturon Electric Kettle Refurbished", 9.0, condition="Refurbished", code=20))
    rows.append(_row("w1", "Fixturon Electric Kettle 21 1.7L", 12.0, valid_to=valid_to, code=21))
    rows += [
        _row(f"l{index}", f"Fixturon Notebook Laptop {index} 15 inch", 300.0 + 25 * index,
             kind="Laptops", code=40 + index)
        for index in range(1, 6)
    ]
    return rows


class _PreparedMixin(_PageMixin):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        self.prepared_path = self.folder / "catalogue.json.gz"
        saved = {name: os.environ.get(name) for name in (
            PREPARED_CATALOGUE_ENV, PREPARED_MAX_AGE_ENV, CACHE_ENV_VAR, "VERCEL", "AWIN_FEED_FILE",
        )}
        for name in (PREPARED_CATALOGUE_ENV, PREPARED_MAX_AGE_ENV, CACHE_ENV_VAR, "VERCEL"):
            os.environ.pop(name, None)
        clear_purchasability_cache_configuration()

        def restore() -> None:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            clear_purchasability_cache_configuration()
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)

    def _write_feed(self, rows: list[list[str]], name: str = "feed.csv") -> Path:
        path = self.folder / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            writer.writerows(rows)
        os.environ["AWIN_FEED_FILE"] = str(path)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()
        return path

    def _prepare(self, *, now: datetime | None = None) -> None:
        prepared = prepare_feed_catalogue(now=now)
        self.assertIsNotNone(prepared)
        write_prepared_catalogue(prepared, self.prepared_path)

    def _answer_from_prepared(self) -> None:
        os.environ[PREPARED_CATALOGUE_ENV] = str(self.prepared_path)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    def _ids(self, page: str) -> list[str]:
        return [card["id"] for card in self._cards(page)]


class PreparedFileTests(_PreparedMixin, unittest.TestCase):
    def test_a_prepared_feed_reads_back_exactly(self) -> None:
        self._write_feed(_feed_rows())
        prepared = prepare_feed_catalogue()
        size = write_prepared_catalogue(prepared, self.prepared_path)
        self.assertGreater(size, 0)
        again = read_prepared_catalogue(self.prepared_path)
        self.assertIsNotNone(again)
        # Each product as the feed gave it, less its empty fields.
        self.assertEqual(
            [replace(product, raw={}) for product in again.products],
            [replace(product, raw={}) for product in prepared.products],
        )
        # Less its empty fields, and less the columns no rule reads.
        self.assertEqual(
            [dict(product.raw) for product in again.products],
            [{key: value for key, value in product.raw.items()
              if value not in ("", None) and key not in prepared_catalogue.LEFT_OUT_COLUMNS}
             for product in prepared.products],
        )
        self.assertNotIn("condition", again.products[0].raw)
        self.assertEqual(prepared.products[0].raw["aw_thumb_url"], "https://fixture.example.invalid/thumb/k1.jpg")
        for product in again.products:
            self.assertNotIn("aw_thumb_url", product.raw)
            self.assertNotIn("delivery_cost", product.raw)
            self.assertEqual(product.raw["data_provenance"], "local_test_fixture")
        self.assertEqual(again.non_new, prepared.non_new)
        self.assertEqual(again.kinds, prepared.kinds)
        # The search fields too, so a cold server does not read every product again.
        self.assertEqual(len(again.search_fields), len(prepared.products))
        self.assertEqual(again.search_fields, prepared.search_fields)
        self.assertEqual(again.search_fields[0]["title"], "fixturon electric kettle 1 1.7l")
        self.assertEqual(again.feed_status, prepared.feed_status)
        self.assertEqual(again.availability_context, prepared.availability_context)
        self.assertEqual((again.eligible_count, again.shop_count), (prepared.eligible_count, prepared.shop_count))
        self.assertEqual(again.suggestions, prepared.suggestions)
        self.assertEqual(again.prepared_at, prepared.prepared_at)
        ids = [product.provider_product_id for product in again.products]
        self.assertIn("r1", ids)
        self.assertEqual(again.non_new[ids.index("r1")], "Refurbished")
        self.assertEqual(again.non_new[ids.index("k1")], "")
        self.assertIn("kettle", again.kinds[ids.index("k1")])
        self.assertIn("laptop", again.kinds[ids.index("l1")])

    def test_each_text_is_written_once(self) -> None:
        # A server holds the file in memory (2 GB on Vercel's free plan), so a text that
        # occurs on every product, the shop's name, is written once, and a product's
        # own title points at the feed column it was read from.
        self._write_feed(_feed_rows())
        self._prepare()
        text = gzip.decompress(self.prepared_path.read_bytes()).decode("utf-8")
        self.assertEqual(text.count('"Fixture Store One"'), 1)
        payload = json.loads(text)
        self.assertIn("Fixture Store One", payload["strings"])
        for row in payload["products"]:
            self.assertIsInstance(row[2], int)
            self.assertLess(row[2], 0)
        self.assertEqual(text.count('"Fixturon Electric Kettle 1 1.7L"'), 1)

    def test_values_that_are_not_text_come_back_as_they_were(self) -> None:
        # Only a JSON feed carries them: a number must never be read as a place in the
        # table of texts, nor a true as a 1.
        rows = []
        for index in range(1, 5):
            row = dict(zip(_COLUMNS, _row(f"j{index}", f"Fixturon Electric Kettle {index} 1.7L", 20.0 + index)))
            row.update({"stock_quantity": index - 1, "reviews": 0, "average_rating": 4.5, "custom_flag": True})
            rows.append(row)
        path = self.folder / "feed.json"
        path.write_text(json.dumps(rows), encoding="utf-8")
        os.environ["AWIN_FEED_FILE"] = str(path)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()
        prepared = prepare_feed_catalogue()
        self.assertEqual(len(prepared.products), 4)
        write_prepared_catalogue(prepared, self.prepared_path)
        again = read_prepared_catalogue(self.prepared_path)
        for before, after in zip(prepared.products, again.products):
            self.assertEqual(replace(after, raw={}), replace(before, raw={}))
            for key in ("stock_quantity", "reviews", "average_rating", "custom_flag"):
                self.assertEqual(after.raw[key], before.raw[key])
                self.assertIs(type(after.raw[key]), type(before.raw[key]))
        self.assertEqual([product.raw["stock_quantity"] for product in again.products], [0, 1, 2, 3])

    def test_the_file_holds_no_feed_link(self) -> None:
        self._write_feed(_feed_rows())
        os.environ["AWIN_FEED_URL"] = "https://productdata.example.invalid/datafeed/apikey/SECRET123/feed.csv.gz"
        self.addCleanup(os.environ.pop, "AWIN_FEED_URL", None)
        self._prepare()
        text = gzip.decompress(self.prepared_path.read_bytes()).decode("utf-8")
        self.assertNotIn("SECRET123", text)
        self.assertNotIn("productdata.example.invalid", text)


class PreparedPagesTests(_PreparedMixin, unittest.TestCase):
    _QUERIES = (
        ("kettle", 0), ("kettle", 8), ("laptop", 0), ("refurbished kettle", 0),
        ("fixturon", 0), ("electric kettle 3", 0),
    )

    def test_pages_from_the_prepared_file_are_the_pages_of_the_feed(self) -> None:
        self._write_feed(_feed_rows())
        live = {(query, shown): self._page(query, shown) for query, shown in self._QUERIES}
        self._prepare()
        self._answer_from_prepared()
        for query, shown in self._QUERIES:
            with self.subTest(query=query, shown=shown):
                page = self._page(query, shown)
                self.assertTrue(self._cards(page))
                self.assertEqual(page, live[(query, shown)])

    def test_the_feed_is_not_read_when_the_prepared_file_answers(self) -> None:
        self._write_feed(_feed_rows())
        self._prepare()
        self._answer_from_prepared()
        with patch.object(state, "load_awin_provider_feed", side_effect=AssertionError("feed read")), patch.object(
            state, "_resolve_provider_feed_pipeline_uncached", side_effect=AssertionError("feed read")
        ):
            page = self._page("kettle")
            self.assertEqual(self._counter(page), "4 of 10")
            self.assertTrue(search_suggestions())
            self.assertEqual(state.peek_search_catalogue_counts(), (16, 1))
            self.assertIsNotNone(resolve_card_eligible_provider_feed_product_by_id("k1"))

    def test_a_file_that_cannot_stand_in_for_the_feed_is_not_used(self) -> None:
        # The file is prepared from one feed and the server is given another, with other
        # prices: a page from the second feed shows the file was not used.
        self._write_feed(_feed_rows())
        self._prepare()
        good = self.prepared_path.read_bytes()
        self._write_feed(
            [_row(f"k{index}", f"Fixturon Electric Kettle {index} 1.7L", 100.0 + index, code=index)
             for index in range(1, 6)],
            name="other.csv",
        )
        live = self._ids(self._page("kettle"))
        self.assertEqual(self._counter(self._page("kettle")), "4 of 5")
        payload = json.loads(gzip.decompress(good))

        def written(change) -> bytes:
            changed = json.loads(json.dumps(payload))
            change(changed)
            return gzip.compress(json.dumps(changed).encode("utf-8"))

        old = (datetime.now(timezone.utc) - timedelta(hours=31)).isoformat()
        cases = {
            "too old": written(lambda body: body.update(prepared_at=old)),
            "other code": written(lambda body: body.update(code="0" * 64)),
            "other version": written(lambda body: body.update(version=prepared_catalogue._VERSION + 1)),
            "the first version": written(lambda body: body.update(version=1)),
            "broken": good[: len(good) // 2],
            "not gzip": b"not a prepared file",
        }
        for name, data in cases.items():
            with self.subTest(case=name):
                self.prepared_path.write_bytes(data)
                self._answer_from_prepared()
                page = self._page("kettle")
                self.assertEqual(self._ids(page), live)
                self.assertEqual(self._counter(page), "4 of 5")
        with self.subTest(case="the good file"):
            self.prepared_path.write_bytes(good)
            self._answer_from_prepared()
            self.assertEqual(self._counter(self._page("kettle")), "4 of 10")

    def test_the_age_limit_can_be_set(self) -> None:
        self._write_feed(_feed_rows())
        self._prepare(now=datetime.now(timezone.utc) - timedelta(hours=40))
        self._answer_from_prepared()
        self.assertIsNone(state._active_prepared_catalogue())
        os.environ[PREPARED_MAX_AGE_ENV] = "48"
        self._answer_from_prepared()
        self.assertIsNotNone(state._active_prepared_catalogue())

    def test_an_offer_whose_window_closed_since_is_left_out(self) -> None:
        today = datetime.now(timezone.utc).date()
        self._write_feed(_feed_rows(valid_to=today.isoformat()))
        self._prepare()
        self._answer_from_prepared()
        self.assertIn("w1", self._ids(self._page("kettle")))
        with patch.object(state, "_today", return_value=today + timedelta(days=1)):
            page = self._page("kettle")
        self.assertNotIn("w1", self._ids(page))
        self.assertEqual(self._counter(page), "4 of 9")

    def test_the_redirect_finds_a_prepared_product_and_nothing_else(self) -> None:
        self._write_feed(_feed_rows())
        self._prepare()
        self._answer_from_prepared()
        product = resolve_card_eligible_provider_feed_product_by_id("l2")
        self.assertIsNotNone(product)
        self.assertEqual(product.title, "Fixturon Notebook Laptop 2 15 inch")
        self.assertIsNone(resolve_card_eligible_provider_feed_product_by_id("no-such-product"))
        self.assertIsNone(resolve_card_eligible_provider_feed_product_by_id(""))

    def test_a_purchasability_cache_turns_the_prepared_file_off(self) -> None:
        self._write_feed(_feed_rows())
        self._prepare()
        self._answer_from_prepared()
        self.assertIsNotNone(state._active_prepared_catalogue())
        configure_purchasability_cache(str(self.folder / "checked.json"))
        self.assertIsNone(state._active_prepared_catalogue())
        self.assertEqual(self._counter(self._page("kettle")), "4 of 10")


class LeftOutColumnsTests(unittest.TestCase):
    # Where a feed product's columns are read: the rules, the pages and the redirect.
    _READERS = ("src/picwise_providers", "src/picwise_app", "src/picwise_surface", "src/picwise_search", "api")

    def test_no_rule_reads_a_column_the_file_leaves_out(self) -> None:
        # Answered from the prepared file, a rule reading a left-out column would see
        # it empty, while a server reading the feed itself sees it filled: the pages
        # would differ. A rule that comes to read one takes it off the list.
        found = []
        for folder in self._READERS:
            for path in sorted((ROOT / folder).rglob("*.py")):
                if path.name == "prepared_catalogue.py":
                    continue
                source = path.read_text(encoding="utf-8")
                for column in sorted(prepared_catalogue.LEFT_OUT_COLUMNS):
                    if f'"{column}"' in source or f"'{column}'" in source:
                        found.append(f"{path.relative_to(ROOT)} reads {column}")
        self.assertEqual(found, [])

    def test_the_columns_every_card_needs_are_kept(self) -> None:
        kept = ("aw_deep_link", "merchant_deep_link", "product_name", "search_price", "currency",
                "merchant_name", "aw_image_url", "merchant_image_url", "description", "in_stock",
                "stock_status", "condition", "ean", "mpn", "product_type", "category_name",
                "merchant_category", "last_updated", "stock_quantity")
        self.assertEqual([column for column in kept if column in prepared_catalogue.LEFT_OUT_COLUMNS], [])


class WhichFileTests(_PreparedMixin, unittest.TestCase):
    def test_a_file_is_read_only_when_configured_or_built_in(self) -> None:
        root = self.folder / "deployment"
        built = root / prepared_catalogue.DEFAULT_PREPARED_PATH
        with patch.object(prepared_catalogue, "_REPO_ROOT", root):
            self.assertIsNone(prepared_catalogue_path())
            built.parent.mkdir(parents=True)
            built.write_bytes(b"")
            # A file at the build's place is not read outside a Vercel deployment.
            self.assertIsNone(prepared_catalogue_path())
            os.environ["VERCEL"] = "1"
            self.assertEqual(prepared_catalogue_path(), built)
            os.environ[PREPARED_CATALOGUE_ENV] = "elsewhere/catalogue.json.gz"
            self.assertEqual(prepared_catalogue_path(), root / "elsewhere" / "catalogue.json.gz")


class PrepareToolTests(_PreparedMixin, unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        environment = {key: value for key, value in os.environ.items() if key not in ("AWIN_FEED_FILE", "AWIN_FEED_URL")}
        return subprocess.run(
            [sys.executable, str(ROOT / "tools" / "prepare_catalogue.py"), *args],
            capture_output=True, text=True, env=environment, timeout=600,
        )

    def test_the_tool_writes_the_file(self) -> None:
        feed = self._write_feed(_feed_rows())
        result = self._run("--feed-file", str(feed), "--out", str(self.prepared_path))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("16 products a card can show", result.stdout)
        self.assertIsNotNone(read_prepared_catalogue(self.prepared_path))

    def test_without_a_feed_the_build_goes_on(self) -> None:
        out = self.folder / "none.json.gz"
        failed = self._run("--out", str(out))
        self.assertEqual(failed.returncode, 1)
        kept_going = self._run("--out", str(out), "--keep-going")
        self.assertEqual(kept_going.returncode, 0)
        self.assertIn("nothing written", kept_going.stdout)
        self.assertFalse(out.exists())

    def test_the_build_leaves_a_public_note_of_what_it_prepared(self) -> None:
        # Vercel serves `--static-dir` as the site's static files and will not deploy it
        # empty; the note says what the build prepared, and nothing of the feed's link.
        feed = self._write_feed(_feed_rows())
        static = self.folder / "public"
        result = self._run(
            "--feed-file", str(feed), "--out", str(self.prepared_path), "--keep-going", "--static-dir", str(static)
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        note = json.loads((static / "prepared.json").read_text(encoding="utf-8"))
        self.assertEqual((note["prepared"], note["products"], note["shops"]), (True, 16, 1))
        prepared_at = read_prepared_catalogue(self.prepared_path).prepared_at
        self.assertLess(abs((datetime.fromisoformat(note["prepared_at"]) - prepared_at).total_seconds()), 1)
        self.assertEqual(
            set(note), {"prepared", "prepared_at", "products", "shops", "freshness", "intake", "kinds", "written_at"}
        )
        # Per kind, the products whose title does not name it (owner, 2026-10-23): every
        # fixture title names its kettle or laptop; and those whose title alone names it
        # (owner, 2026-10-25): every fixture shelf names it too.
        self.assertEqual(
            note["kinds"],
            {
                "products": 16,
                "title_names_no_kind": 0,
                "by_kind": [],
                "only_title_names_kind": 0,
                "by_kind_only_title": [],
            },
        )
        # How fresh the listings are (owner, 2026-10-18: "we show ghosts"), measured only.
        self.assertEqual(note["freshness"]["products"], 16)
        self.assertEqual(note["freshness"]["last_updated"]["no_date"], 16)
        # What each shop's feed brings in (owner, 2026-10-18: many shops first): the
        # refurbished kettle is shown only when asked for.
        self.assertEqual(
            {key: note["intake"][key] for key in ("rows", "shown", "not_new", "held")},
            {"rows": 16, "shown": 15, "not_new": 1, "held": 0},
        )
        self.assertEqual([shop["shop"] for shop in note["intake"]["shops"]], ["Fixture Store One"])
        self.assertNotIn("fixture.example.invalid", json.dumps(note))

        empty = self.folder / "public-without-feed"
        result = self._run("--out", str(self.folder / "none.json.gz"), "--keep-going", "--static-dir", str(empty))
        self.assertEqual(result.returncode, 0)
        note = json.loads((empty / "prepared.json").read_text(encoding="utf-8"))
        self.assertEqual((note["prepared"], note["reason"]), (False, "feed_not_readable"))

    def test_a_failure_while_preparing_never_fails_the_build_nor_shows_its_text(self) -> None:
        # An error's own text can quote the feed's link, which holds the API key.
        tool = _load_prepare_tool()
        link = "https://productdata.example.invalid/datafeed/download/apikey/SECRET123/feed.csv.gz"
        out = self.folder / "failed.json.gz"
        static = self.folder / "public"
        printed = io.StringIO()
        with patch.object(state, "prepare_feed_catalogue", side_effect=ValueError(f"cannot read {link}")):
            with redirect_stdout(printed):
                code = tool.main(["--out", str(out), "--keep-going", "--static-dir", str(static)])
            self.assertEqual(code, 0)
            self.assertIn("preparing the feed failed (ValueError at", printed.getvalue())
            self.assertNotIn("SECRET123", printed.getvalue())
            self.assertNotIn("productdata", printed.getvalue())
            self.assertFalse(out.exists())
            note = json.loads((static / "prepared.json").read_text(encoding="utf-8"))
            self.assertEqual((note["prepared"], note["reason"]), (False, "preparing_failed"))
            # Run by hand, without --keep-going, the error is shown in full.
            with redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
                tool.main(["--out", str(out)])


def _load_prepare_tool():
    spec = importlib.util.spec_from_file_location("prepare_catalogue_tool", ROOT / "tools" / "prepare_catalogue.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PreparedStatusTests(_PreparedMixin, unittest.TestCase):
    """What /private-beta-readiness says of the prepared feed (step 5): whether the
    server answers from it, and when it was prepared."""

    def _status(self) -> dict:
        def start_response(_status: str, _headers: list[tuple[str, str]]) -> None:
            return None

        body = b"".join(
            wsgi_app(
                {"REQUEST_METHOD": "GET", "PATH_INFO": "/private-beta-readiness", "QUERY_STRING": "",
                 "wsgi.input": io.BytesIO(b""), "wsgi.url_scheme": "https"},
                start_response,
            )
        )
        return json.loads(body)["prepared_feed"]

    def test_a_fresh_file_is_in_use(self) -> None:
        self._write_feed(_feed_rows())
        self.assertEqual(self._status(), {"state": "not_present"})
        prepared_at = datetime.now(timezone.utc) - timedelta(hours=3)
        self._prepare(now=prepared_at)
        self._answer_from_prepared()
        status = self._status()
        self.assertEqual(status["state"], "in_use")
        self.assertEqual(status["prepared_at"], prepared_at.isoformat(timespec="seconds"))
        self.assertEqual(status["age_hours"], 3.0)

    def test_why_a_file_is_not_used(self) -> None:
        self._write_feed(_feed_rows())
        self._prepare(now=datetime.now(timezone.utc) - timedelta(hours=40))
        self._answer_from_prepared()
        status = self._status()
        self.assertEqual(status["state"], "too_old")
        self.assertGreaterEqual(status["age_hours"], 40.0)
        good = self.prepared_path.read_bytes()
        payload = json.loads(gzip.decompress(good))
        cases = {
            "other_code": gzip.compress(json.dumps({**payload, "code": "0" * 64}).encode("utf-8")),
            "other_format": gzip.compress(
                json.dumps({**payload, "version": prepared_catalogue._VERSION + 1}).encode("utf-8")
            ),
            "unreadable": good[: len(good) // 2],
        }
        for state_name, data in cases.items():
            with self.subTest(state=state_name):
                self.prepared_path.write_bytes(data)
                self._answer_from_prepared()
                self.assertEqual(self._status(), {"state": state_name})
        with self.subTest(state="no file where one is configured"):
            self.prepared_path.unlink()
            self._answer_from_prepared()
            self.assertEqual(self._status(), {"state": "not_present"})

    def test_a_file_that_ages_past_the_limit_while_served(self) -> None:
        self._write_feed(_feed_rows())
        self._prepare(now=datetime.now(timezone.utc) - timedelta(hours=2))
        self._answer_from_prepared()
        self.assertEqual(self._status()["state"], "in_use")
        os.environ[PREPARED_MAX_AGE_ENV] = "1"
        self.assertEqual(self._status()["state"], "too_old")

    def test_a_purchasability_cache_turns_it_off(self) -> None:
        self._write_feed(_feed_rows())
        self._prepare()
        self._answer_from_prepared()
        configure_purchasability_cache(str(self.folder / "checked.json"))
        self.assertEqual(self._status(), {"state": "not_used", "reason": "purchasability_cache_configured"})


if __name__ == "__main__":
    unittest.main()
