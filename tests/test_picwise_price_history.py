"""A card's price note: down, up or the same, from the catalogue's memory
(`picwise_providers.price_history`; the owner, 2026-11-13: «Συμφωνώ με το σχεδιασμό»).

The rule, as put to the owner that day: today's price is compared with the last price
the shop kept for at least 7 nights seen. Pinned here with the owner's own examples:

- a drop after 3 weeks at one price shows from its first night ("▼ £40 since 6 Dec");
- a short sale shows at once, and its chip goes when the price comes back;
- a price raised for 2 nights and brought back never reads as a discount;
- a price shown one night, hidden 10 nights and brought back lower is no kept price;
- a change under £1 or under 1% is not told, nor one older than 30 nights;
- 7 nights or more at one price read "the same for N nights", 6 do not;
- the file is written beside the prepared catalogue, holds no link, and a worker shows
  its notes only beside the catalogue of the same preparation.

Every product is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers import price_history  # noqa: E402
from picwise_providers.catalogue_memory import remember_night  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.price_history import (  # noqa: E402
    DOWN,
    PRICE_NOTES_ENV,
    SAME,
    UP,
    PriceRun,
    notes_for_catalogue,
    read_price_notes,
    write_price_notes,
)

SHOP = "Fixture Shop One"
FIRST = datetime(2026, 11, 6, 4, 23, tzinfo=timezone.utc)


def _product(pid: str, price: str, currency: str = "GBP") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin", provider_product_id=pid, title=f"Fixturon Sofa {pid}", brand="Fixturon",
        category_text="Furniture > Sofas", product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg", price_text=price,
        availability_text="in stock", currency=currency, raw={"merchant_name": SHOP},
    )


class _Nights:
    """Prepares nights one after another; each product's price that night, or None when
    the shop did not list it."""

    def __init__(self) -> None:
        folder = Path(tempfile.mkdtemp())
        self.memory = folder / "memory.sqlite"
        self.out = folder / price_history.PRICE_NOTES_NAME
        self.night = FIRST - timedelta(days=1)

    def run(self, prices: dict[str, str | None], nights: int = 1, currency: str = "GBP") -> None:
        for _ in range(nights):
            self.night += timedelta(days=1)
            listed = [_product(pid, price, currency) for pid, price in prices.items() if price is not None]
            remember_night(self.memory, listed, prepared_at=self.night)

    def notes(self):
        write_price_notes(self.memory, self.out, prepared_at=self.night)
        return read_price_notes(self.out)

    def note(self, pid: str):
        return self.notes().note(SHOP, pid, currency="GBP")


class RuleTests(unittest.TestCase):
    def test_a_drop_after_three_weeks_shows_from_its_first_night(self) -> None:
        nights = _Nights()
        nights.run({"a": "1238.00"}, 21)
        nights.run({"a": "1198.00"})
        note = nights.note("a")
        self.assertEqual((note.kind, note.change_pence, note.since), (DOWN, 4000, nights.night.date()))
        # The last 30 nights: 21 at £1,238 then 1 at £1,198, oldest first.
        self.assertEqual(
            [(run.nights, run.pence) for run in note.runs], [(21, 123800), (1, 119800)]
        )
        # Days later it still says since when.
        nights.run({"a": "1198.00"}, 5)
        note = nights.note("a")
        self.assertEqual((note.kind, note.since), (DOWN, nights.night.date() - timedelta(days=5)))

    def test_a_short_sale_shows_at_once_and_goes_when_the_price_comes_back(self) -> None:
        nights = _Nights()
        nights.run({"a": "100.00"}, 30)
        nights.run({"a": "80.00"})
        self.assertEqual((nights.note("a").kind, nights.note("a").change_pence), (DOWN, 2000))
        nights.run({"a": "80.00"})
        self.assertEqual(nights.note("a").kind, DOWN)
        nights.run({"a": "100.00"})
        self.assertIsNone(nights.note("a"))

    def test_a_price_raised_two_nights_and_brought_back_is_no_discount(self) -> None:
        nights = _Nights()
        nights.run({"a": "100.00"}, 30)
        nights.run({"a": "150.00"})
        # The rise is true and shown.
        self.assertEqual((nights.note("a").kind, nights.note("a").change_pence), (UP, 5000))
        nights.run({"a": "150.00"})
        nights.run({"a": "100.00"})
        # Back to the price kept a month: nothing to tell, never "▼ £50".
        self.assertIsNone(nights.note("a"))
        nights.run({"a": "100.00"}, 6)
        note = nights.note("a")
        self.assertEqual((note.kind, note.nights), (SAME, 7))

    def test_a_price_shown_once_then_hidden_is_no_kept_price(self) -> None:
        nights = _Nights()
        nights.run({"a": "100.00"}, 3)
        nights.run({"a": "150.00"})
        nights.run({"a": None}, 10)
        nights.run({"a": "100.00"})
        # £150 was seen one night: counted by the calendar it would have "held" 11.
        self.assertIsNone(nights.note("a"))

    def test_a_kept_price_before_a_gap_is_still_the_one_compared_with(self) -> None:
        nights = _Nights()
        nights.run({"a": "100.00"}, 8)
        nights.run({"a": None}, 3)
        nights.run({"a": "90.00"})
        note = nights.note("a")
        self.assertEqual((note.kind, note.change_pence, note.since), (DOWN, 1000, nights.night.date()))
        # The chart shows the gap: two runs, three nights apart.
        first, second = note.runs
        self.assertEqual((second.start - first.end).days, 4)

    def test_a_change_under_a_pound_or_under_one_percent_is_not_told(self) -> None:
        nights = _Nights()
        nights.run({"cheap": "100.00", "dear": "500.00", "six": "20.00"}, 10)
        nights.run({"cheap": "99.50", "dear": "496.00", "six": "26.00"})
        notes = nights.notes()
        self.assertIsNone(notes.note(SHOP, "cheap"))
        self.assertIsNone(notes.note(SHOP, "dear"))
        self.assertEqual(notes.note(SHOP, "six").kind, UP)
        self.assertEqual(notes.note(SHOP, "six").change_pence, 600)

    def test_a_change_older_than_thirty_nights_reads_as_the_same_price(self) -> None:
        nights = _Nights()
        nights.run({"a": "100.00"}, 10)
        nights.run({"a": "80.00"}, 30)
        self.assertEqual(nights.note("a").kind, DOWN)
        nights.run({"a": "80.00"})
        note = nights.note("a")
        self.assertEqual((note.kind, note.nights), (SAME, 30))

    def test_seven_nights_at_one_price_read_the_same_and_six_do_not(self) -> None:
        nights = _Nights()
        nights.run({"seven": "50.00", "six": None}, 1)
        nights.run({"seven": "50.00", "six": "50.00"}, 6)
        notes = nights.notes()
        self.assertEqual((notes.note(SHOP, "seven").kind, notes.note(SHOP, "seven").nights), (SAME, 7))
        self.assertIsNone(notes.note(SHOP, "six"))

    def test_a_new_currency_is_no_change_in_price(self) -> None:
        nights = _Nights()
        nights.run({"a": "100.00"}, 10)
        nights.run({"a": "80.00"}, currency="EUR")
        self.assertIsNone(nights.note("a"))

    def test_a_product_not_listed_tonight_has_no_note(self) -> None:
        nights = _Nights()
        nights.run({"a": "100.00", "b": "100.00"}, 10)
        nights.run({"a": "100.00"})
        notes = nights.notes()
        self.assertIsNone(notes.note(SHOP, "b"))
        self.assertEqual(notes.note(SHOP, "a").kind, SAME)

    def test_runs_are_cut_to_the_last_thirty_nights(self) -> None:
        nights = _Nights()
        nights.run({"a": "100.00"}, 40)
        nights.run({"a": "70.00"})
        note = nights.note("a")
        self.assertEqual(note.runs[0].start, nights.night.date() - timedelta(days=29))
        self.assertEqual(sum(run.nights for run in note.runs), 30)


class FileTests(unittest.TestCase):
    def setUp(self) -> None:
        price_history._reset_price_notes_for_tests()
        self.addCleanup(price_history._reset_price_notes_for_tests)

    def test_the_file_holds_counts_keys_and_no_link(self) -> None:
        nights = _Nights()
        nights.run({"a": "100.00", "b": "20.00"}, 8)
        nights.run({"a": "90.00", "b": "20.00"})
        summary = write_price_notes(nights.memory, nights.out, prepared_at=nights.night)
        self.assertEqual(
            summary,
            {"file": "price_notes.json.gz", "night": nights.night.date().isoformat(), "notes": 2,
             "down": 1, "up": 0, "same": 1},
        )
        with gzip.open(nights.out, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual(payload["min_hold_nights"], 7)
        self.assertEqual(payload["notes"][f"{SHOP}\x1fb"], 9)
        self.assertNotIn("http", json.dumps(payload))
        self.assertFalse(nights.out.with_name(nights.out.name + ".partial").exists())

    def test_a_night_without_the_memory_of_tonight_writes_no_note(self) -> None:
        nights = _Nights()
        nights.run({"a": "100.00"}, 8)
        summary = write_price_notes(nights.memory, nights.out, prepared_at=nights.night + timedelta(days=1))
        self.assertEqual(summary["notes"], 0)

    def test_a_worker_shows_notes_only_beside_the_same_preparations_catalogue(self) -> None:
        nights = _Nights()
        nights.run({"a": "100.00"}, 8)
        write_price_notes(nights.memory, nights.out, prepared_at=nights.night)
        os.environ[PRICE_NOTES_ENV] = str(nights.out)
        self.addCleanup(os.environ.pop, PRICE_NOTES_ENV, None)
        notes = notes_for_catalogue(nights.night)
        self.assertIsNotNone(notes)
        self.assertEqual(notes.note(SHOP, "a").kind, SAME)
        # Another preparation's catalogue (a later one whose notes failed): none.
        self.assertIsNone(notes_for_catalogue(nights.night + timedelta(hours=5)))
        self.assertIsNone(notes_for_catalogue(None))

    def test_an_unreadable_file_or_none_shows_nothing(self) -> None:
        folder = Path(tempfile.mkdtemp())
        broken = folder / "price_notes.json.gz"
        broken.write_bytes(b"not a gzip file")
        self.assertIsNone(read_price_notes(broken))
        self.assertIsNone(read_price_notes(folder / "missing.json.gz"))
        os.environ[PRICE_NOTES_ENV] = str(broken)
        self.addCleanup(os.environ.pop, PRICE_NOTES_ENV, None)
        self.assertEqual(price_history.refresh_price_notes(kept=False), "refused")
        self.assertIsNone(notes_for_catalogue(FIRST))

    def test_the_keeper_loads_a_new_file_once(self) -> None:
        nights = _Nights()
        nights.run({"a": "100.00"}, 8)
        write_price_notes(nights.memory, nights.out, prepared_at=nights.night)
        os.environ[PRICE_NOTES_ENV] = str(nights.out)
        self.addCleanup(os.environ.pop, PRICE_NOTES_ENV, None)
        self.assertEqual(price_history.refresh_price_notes(), "loaded")
        self.assertEqual(price_history.refresh_price_notes(), "current")
        nights.run({"a": "100.00"})
        write_price_notes(nights.memory, nights.out, prepared_at=nights.night)
        self.assertEqual(price_history.refresh_price_notes(), "loaded")
        self.assertEqual(notes_for_catalogue(nights.night).note(SHOP, "a").nights, 9)

    def test_a_same_price_note_is_one_run_at_the_cards_price(self) -> None:
        nights = _Nights()
        nights.run({"a": "100.00"}, 12)
        note = nights.note("a")
        self.assertEqual(note.runs, (PriceRun(nights.night.date() - timedelta(days=11), nights.night.date(), 12, 0, "GBP"),))


class PreparationTests(unittest.TestCase):
    """The night's preparation writes the notes beside the catalogue, after the memory."""

    def _prepare(self, folder: Path, *extra: str) -> tuple[str, dict]:
        env = {key: value for key, value in os.environ.items() if not key.startswith(("AWIN_", "PICWISE_"))}
        feed = ROOT / "tests" / "fixtures" / "provider_feed_coverage_matrix_fixture.csv"
        done = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "prepare_catalogue.py"), "--feed-file", str(feed),
             "--out", str(folder / "catalogue.json.gz"), "--static-dir", str(folder), *extra],
            env=env, capture_output=True, text=True, check=True,
        )
        return done.stdout, json.loads((folder / "prepared.json").read_text(encoding="utf-8"))

    def test_with_a_memory_the_notes_are_written_beside_the_catalogue(self) -> None:
        folder = Path(tempfile.mkdtemp())
        out, note = self._prepare(folder, "--memory", str(folder / "catalogue_memory.sqlite"))
        # The first night: no price has been kept 7 nights yet.
        self.assertEqual(note["price_notes"]["notes"], 0)
        self.assertIn("prepare_catalogue: the price notes: 0 products, 0 down, 0 up", out)
        notes = read_price_notes(folder / "price_notes.json.gz")
        self.assertIsNotNone(notes)
        self.assertEqual(notes.prepared_at, datetime.fromisoformat(note["prepared_at"]).replace(
            microsecond=notes.prepared_at.microsecond))

    def test_without_a_memory_no_notes(self) -> None:
        folder = Path(tempfile.mkdtemp())
        _out, note = self._prepare(folder)
        self.assertNotIn("price_notes", note)
        self.assertFalse((folder / "price_notes.json.gz").exists())


if __name__ == "__main__":
    unittest.main()
