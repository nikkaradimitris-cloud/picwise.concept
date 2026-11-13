"""The catalogue's memory: what PicWise has seen of each product, night after night
(`picwise_providers.catalogue_memory`; the owner, 12/11: «Προχώρα στην υλοποίηση στη
μνήμη του καταλόγου», then «Ναι, προχώρα με όλα»).

No feed sends a date of update or a stock quantity, and each night rebuilt the catalogue
from nothing. Pinned here:

- the first night: every product new, its price written;
- the next night: a product not seen again is counted gone, a new one new, a changed
  price written with its night, an unchanged one not written again;
- a second preparation in the same night counts the night once and takes its price;
- per shop and night, its rows, shown and kept;
- no link is kept, and the public note holds counts only;
- the night's preparation writes it when a file is named, says what it holds in its
  note and in the server's report, and keeps none when none is named;
- which prepared nights each product was seen on (`seen_nights`, owner, 2026-11-13: the
  price chips' 7 nights count only nights a price was seen): a night not seen leaves its
  bit unset, a night with no preparation is no night, a second preparation sets none
  twice, and a memory of 12-13/11 gets the column from what it knew.

Every product is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.catalogue_memory import MEMORY_FILE_ENV, remember_night  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402

NIGHT_1 = datetime(2026, 11, 12, 4, 23, tzinfo=timezone.utc)
NIGHT_2 = datetime(2026, 11, 13, 4, 21, tzinfo=timezone.utc)
NIGHT_3 = datetime(2026, 11, 14, 4, 20, tzinfo=timezone.utc)
NIGHT_4 = datetime(2026, 11, 15, 4, 22, tzinfo=timezone.utc)


def _product(pid: str, shop: str = "Fixture Shop One", price: str = "20.00", ean: str = "") -> ProviderProduct:
    raw = {"merchant_name": shop}
    if ean:
        raw["ean"] = ean
    return ProviderProduct(
        provider_key="awin", provider_product_id=pid, title=f"Fixturon Kettle {pid}", brand="Fixturon",
        category_text="Home & Garden > Kitchen", product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg", price_text=price,
        availability_text="in stock", currency="GBP", raw=raw,
    )


class MemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = Path(tempfile.mkdtemp()) / "memory.sqlite"

    def _rows(self, sql: str, *args) -> list[tuple]:
        with sqlite3.connect(str(self.path)) as db:
            return db.execute(sql, args).fetchall()

    def test_the_first_night_every_product_is_new(self) -> None:
        summary = remember_night(self.path, [_product("a"), _product("b", price="35.50")], prepared_at=NIGHT_1)
        self.assertEqual(
            summary,
            {
                "file": "memory.sqlite", "night": "2026-11-12", "nights": 1, "products_known": 2,
                "seen_tonight": 2, "new_tonight": 2, "price_changed_tonight": 0,
                "compared_with": None, "gone_since": None,
            },
        )
        self.assertEqual(
            self._rows("SELECT product_id, first_seen, last_seen, nights_seen, price_pence, currency FROM products ORDER BY 1"),
            [("a", "2026-11-12", "2026-11-12", 1, 2000, "GBP"), ("b", "2026-11-12", "2026-11-12", 1, 3550, "GBP")],
        )
        self.assertEqual(self._rows("SELECT COUNT(*) FROM prices"), [(2,)])

    def test_the_next_night_gone_new_and_a_changed_price(self) -> None:
        remember_night(self.path, [_product("a"), _product("b"), _product("c")], prepared_at=NIGHT_1)
        summary = remember_night(
            self.path, [_product("a"), _product("b", price="18.00"), _product("d")], prepared_at=NIGHT_2
        )
        self.assertEqual(
            {key: summary[key] for key in ("nights", "products_known", "seen_tonight", "new_tonight",
                                           "price_changed_tonight", "compared_with", "gone_since")},
            {"nights": 2, "products_known": 4, "seen_tonight": 3, "new_tonight": 1, "price_changed_tonight": 1,
             "compared_with": "2026-11-12", "gone_since": 1},
        )
        rows = {row[0]: row[1:] for row in self._rows(
            "SELECT product_id, first_seen, last_seen, nights_seen, price_pence, price_changed_on FROM products")}
        self.assertEqual(rows["a"], ("2026-11-12", "2026-11-13", 2, 2000, None))
        self.assertEqual(rows["b"], ("2026-11-12", "2026-11-13", 2, 1800, "2026-11-13"))
        # Gone: still known, last seen the night before.
        self.assertEqual(rows["c"], ("2026-11-12", "2026-11-12", 1, 2000, None))
        self.assertEqual(rows["d"], ("2026-11-13", "2026-11-13", 1, 2000, None))
        # Prices: each first night, and b's change; a's unchanged price not written again.
        self.assertEqual(
            self._rows("SELECT product_id, night, prices.price_pence FROM prices JOIN products USING (key) ORDER BY 1, 2"),
            [("a", "2026-11-12", 2000), ("b", "2026-11-12", 2000), ("b", "2026-11-13", 1800),
             ("c", "2026-11-12", 2000), ("d", "2026-11-13", 2000)],
        )

    def test_a_second_preparation_in_the_same_night_counts_it_once(self) -> None:
        remember_night(self.path, [_product("a")], prepared_at=NIGHT_1)
        remember_night(self.path, [_product("a")], prepared_at=NIGHT_2)
        later = NIGHT_2.replace(hour=6, minute=38)
        summary = remember_night(self.path, [_product("a", price="21.00")], prepared_at=later)
        self.assertEqual((summary["nights"], summary["seen_tonight"], summary["new_tonight"]), (2, 1, 0))
        self.assertEqual(
            self._rows("SELECT nights_seen, price_pence, price_changed_on FROM products"), [(2, 2100, "2026-11-13")]
        )
        self.assertEqual(
            self._rows("SELECT night, price_pence FROM prices ORDER BY night"),
            [("2026-11-12", 2000), ("2026-11-13", 2100)],
        )

    def test_per_shop_and_night_its_rows_shown_and_kept(self) -> None:
        intake = {"shops": [{"shop": "Fixture Shop One", "rows": 10, "shown": 4},
                            {"shop": "Fixture Shop Silent", "rows": 7, "shown": 0}]}
        remember_night(self.path, [_product("a"), _product("b"), _product("x", shop="Fixture Shop Two")],
                       prepared_at=NIGHT_1, intake=intake)
        self.assertEqual(
            self._rows("SELECT shop, rows, shown, kept FROM shop_nights ORDER BY shop"),
            [("Fixture Shop One", 10, 4, 2), ("Fixture Shop Silent", 7, 0, 0), ("Fixture Shop Two", 0, 0, 1)],
        )

    def test_no_link_is_kept_and_the_summary_holds_counts_only(self) -> None:
        base = "501234500001"
        code = base + str((10 - sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(base)) % 10) % 10)
        summary = remember_night(self.path, [_product("a", ean=code)], prepared_at=NIGHT_1)
        with sqlite3.connect(str(self.path)) as db:
            dump = "\n".join(db.iterdump())
        self.assertNotIn("http", dump)
        self.assertIn(code.zfill(14), dump)
        self.assertNotIn("http", json.dumps(summary))
        self.assertNotIn(str(self.path.parent), json.dumps(summary))


class SeenNightsTests(unittest.TestCase):
    """Which prepared nights a product was seen on: bit 0 its last, bit 1 the one before."""

    def setUp(self) -> None:
        self.path = Path(tempfile.mkdtemp()) / "memory.sqlite"

    def _bits(self) -> dict[str, int]:
        with sqlite3.connect(str(self.path)) as db:
            return dict(db.execute("SELECT product_id, seen_nights FROM products").fetchall())

    def test_each_night_seen_sets_its_bit_and_a_night_away_leaves_it_unset(self) -> None:
        remember_night(self.path, [_product("a"), _product("b")], prepared_at=NIGHT_1)
        self.assertEqual(self._bits(), {"a": 0b1, "b": 0b1})
        remember_night(self.path, [_product("a")], prepared_at=NIGHT_2)
        remember_night(self.path, [_product("a"), _product("b")], prepared_at=NIGHT_3)
        # a: 12, 13, 14; b: 12 and 14, not 13.
        self.assertEqual(self._bits(), {"a": 0b111, "b": 0b101})
        remember_night(self.path, [_product("b")], prepared_at=NIGHT_4)
        # a not seen on 15: its record stays as of its last night (14).
        self.assertEqual(self._bits(), {"a": 0b111, "b": 0b1011})

    def test_a_night_with_no_preparation_is_no_night(self) -> None:
        remember_night(self.path, [_product("a")], prepared_at=NIGHT_1)
        # 13/11 not prepared at all (the server down): seen on every night there was.
        remember_night(self.path, [_product("a")], prepared_at=NIGHT_3)
        self.assertEqual(self._bits(), {"a": 0b11})

    def test_a_second_preparation_in_the_night_sets_nothing_twice(self) -> None:
        remember_night(self.path, [_product("a")], prepared_at=NIGHT_1)
        remember_night(self.path, [_product("a")], prepared_at=NIGHT_2)
        remember_night(self.path, [_product("a")], prepared_at=NIGHT_2.replace(hour=9))
        self.assertEqual(self._bits(), {"a": 0b11})

    def test_only_the_last_62_prepared_nights_are_kept(self) -> None:
        from datetime import timedelta

        for day in range(70):
            remember_night(self.path, [_product("a")], prepared_at=NIGHT_1 + timedelta(days=day))
        self.assertEqual(self._bits(), {"a": (1 << 62) - 1})

    def test_a_memory_of_before_the_column_gets_it_from_what_it_knew(self) -> None:
        with sqlite3.connect(str(self.path)) as db:
            db.executescript(
                """
                CREATE TABLE products (key TEXT PRIMARY KEY, shop TEXT NOT NULL, product_id TEXT NOT NULL,
                    gtin TEXT NOT NULL, title TEXT NOT NULL, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
                    nights_seen INTEGER NOT NULL, price_pence INTEGER, currency TEXT NOT NULL, price_changed_on TEXT);
                CREATE TABLE prices (key TEXT NOT NULL, night TEXT NOT NULL, price_pence INTEGER,
                    currency TEXT NOT NULL, PRIMARY KEY (key, night));
                CREATE TABLE nights (night TEXT PRIMARY KEY, prepared_at TEXT NOT NULL, kept INTEGER NOT NULL);
                INSERT INTO nights VALUES ('2026-11-12', '2026-11-12T04:23:00+00:00', 3),
                                          ('2026-11-13', '2026-11-13T04:21:00+00:00', 2);
                INSERT INTO products VALUES
                    ('Fixture Shop One' || char(31) || 'both', 'Fixture Shop One', 'both', '', 't',
                     '2026-11-12', '2026-11-13', 2, 2000, 'GBP', NULL),
                    ('Fixture Shop One' || char(31) || 'new', 'Fixture Shop One', 'new', '', 't',
                     '2026-11-13', '2026-11-13', 1, 2000, 'GBP', NULL),
                    ('Fixture Shop One' || char(31) || 'gone', 'Fixture Shop One', 'gone', '', 't',
                     '2026-11-12', '2026-11-12', 1, 2000, 'GBP', NULL);
                """
            )
        remember_night(self.path, [_product("both"), _product("gone")], prepared_at=NIGHT_3)
        # both: 12, 13 (from the count), then 14; gone: 12, not 13, then 14; new: 13 only.
        self.assertEqual(self._bits(), {"both": 0b111, "gone": 0b101, "new": 0b1})


class PreparationTests(unittest.TestCase):
    """The night's preparation, run as the server runs it, on a fixture feed."""

    def _prepare(self, folder: Path, *extra: str) -> tuple[str, dict]:
        env = {key: value for key, value in os.environ.items() if not key.startswith(("AWIN_", "PICWISE_"))}
        feed = ROOT / "tests" / "fixtures" / "provider_feed_coverage_matrix_fixture.csv"
        done = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "prepare_catalogue.py"), "--feed-file", str(feed),
             "--out", str(folder / "catalogue.json.gz"), "--static-dir", str(folder), *extra],
            env=env, capture_output=True, text=True, check=True,
        )
        return done.stdout, json.loads((folder / "prepared.json").read_text(encoding="utf-8"))

    def test_it_writes_the_memory_when_named_and_says_what_it_holds(self) -> None:
        folder = Path(tempfile.mkdtemp())
        out, note = self._prepare(folder, "--memory", str(folder / "catalogue_memory.sqlite"))
        memory = note["memory"]
        self.assertEqual(memory["products_known"], note["products"])
        self.assertEqual((memory["nights"], memory["new_tonight"], memory["compared_with"]), (1, note["products"], None))
        self.assertIn(f"prepare_catalogue: the catalogue's memory: {note['products']:,} products over 1 nights", out)
        self.assertTrue((folder / "catalogue_memory.sqlite").is_file())
        report = subprocess.run(
            [sys.executable, str(ROOT / "deployment" / "server" / "print_shops.py")],
            input=json.dumps(note), capture_output=True, text=True, check=True,
        ).stdout
        self.assertIn(f"the catalogue's memory: {note['products']:,} products over 1 nights; the night of ", report)

    def test_none_is_kept_when_none_is_named(self) -> None:
        folder = Path(tempfile.mkdtemp())
        _out, note = self._prepare(folder)
        self.assertNotIn("memory", note)
        self.assertEqual(sorted(path.name for path in folder.glob("*.sqlite")), [])
        self.assertIsNone(os.environ.get(MEMORY_FILE_ENV))

    def test_the_servers_unit_names_the_memory(self) -> None:
        unit = (ROOT / "deployment" / "server" / "picwise-prepare.service").read_text(encoding="utf-8")
        self.assertIn("--memory /srv/picwise/shared/prepared/catalogue_memory.sqlite", unit)
        self.assertIn("ReadWritePaths=/srv/picwise/shared", unit)


if __name__ == "__main__":
    unittest.main()
