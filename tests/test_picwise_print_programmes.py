"""Which of the catalogue's shops PicWise's Awin account is joined to, and how fresh each
shop's feed is (`deployment/server/print_programmes.py`; task 3 of the work split by model,
21/11: «Awin's feed list and programmes (joined, last update)»; read from Awin, never by a
click). Pinned here: the shops are the advertisers of every copy of the feed; each is met
with its programme by its id, under PicWise's relationship to it, and with its feeds'
membership and last import; the site's products are counted by relationship; and no token,
key, account id or link reaches the printed lines.

Every value is invented: `.invalid` links, fictional keys, ids and names.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("print_programmes", ROOT / "deployment" / "server" / "print_programmes.py")
programmes = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = programmes
_spec.loader.exec_module(programmes)

TOKEN = "tok-0f0f0f0f0f0f0f0f0f0f"
KEY = "feedkey0123456789abcdef"
PUBLISHER = "7654321"
FIRST = f"https://feeds.example.invalid/datafeed/download/apikey/{KEY}/fid/1,2/format/csv"
SECOND = f"https://feeds.example.invalid/datafeed/download/apikey/{KEY}/fid/9/format/csv/awin"


def _copy(path: Path, header: list[str], rows: list[list[str]], *, hours_ago: float = 0.0) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    when = time.time() - hours_ago * 3600
    os.utime(path, (when, when))


def _answers() -> dict[str, tuple[int, bytes]]:
    def listing(*rows: dict) -> tuple[int, bytes]:
        return 200, json.dumps(list(rows)).encode()

    api = programmes.PROGRAMMES_API
    feed_list = io.StringIO()
    writer = csv.writer(feed_list)
    writer.writerow(["Advertiser ID", "Advertiser Name", "Primary Region", "Membership Status", "Feed ID", "Feed Name",
                     "Language", "Vertical", "Last Imported", "Last Checked", "No of products", "URL"])
    writer.writerow(["101", "Kettle Shop", "GB", "active", "1", "Main", "en", "Home", "2026-11-21 03:10:00",
                     "2026-11-21 04:00:00", "900", f"https://feeds.example.invalid/x/apikey/{KEY}/fid/1"])
    writer.writerow(["202", "Tool Shop", "GB", "not joined", "9", "All", "en", "DIY", "2026-11-18 22:00:00",
                     "2026-11-21 04:00:00", "5000", f"https://feeds.example.invalid/x/apikey/{KEY}/fid/9"])
    return {
        programmes.ACCOUNTS_API: (200, json.dumps({"accounts": [{"accountId": PUBLISHER, "accountType": "publisher"}]}).encode()),
        api.format(publisher=PUBLISHER, relationship="joined"): listing({"id": 101, "name": "Kettle Shop", "status": "Active"}),
        api.format(publisher=PUBLISHER, relationship="pending"): listing(),
        api.format(publisher=PUBLISHER, relationship="notjoined"): listing({"id": 202, "name": "Tool Shop", "status": "Active"}),
        api.format(publisher=PUBLISHER, relationship="suspended"): listing(),
        api.format(publisher=PUBLISHER, relationship="rejected"): (401, b'{"error":"unauthorised"}'),
        programmes.FEED_LIST.format(key=KEY): (200, feed_list.getvalue().encode()),
    }


class ProgrammesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        cache = self.folder / "cache"
        cache.mkdir()
        _copy(cache / "picwise_awin_feed_a.bin", ["id", "title", "advertiser_id", "advertiser_name"],
              [["g1", "Kettle", "101", "Kettle Shop"], ["g2", "Lamp", "303", "Lamp Shop"]], hours_ago=0.1)
        _copy(cache / "picwise_awin_feed_b.bin", ["aw_product_id", "product_name", "merchant_id", "merchant_name"],
              [["a1", "Drill", "202", "Tool Shop"]])
        _copy(cache / "picwise_awin_feed_old.bin", ["aw_product_id", "merchant_id", "merchant_name"],
              [["o1", "404", "Gone Shop"]], hours_ago=200)
        note = {"balance": {"by_shop": [{"shop": "Tool Shop", "products": 600}, {"shop": "Kettle Shop", "products": 300},
                                        {"shop": "Lamp Shop", "products": 100}]}}
        (self.folder / "prepared.json").write_text(json.dumps(note), encoding="utf-8")
        self.asked: list[str] = []
        self.answers = _answers()

    def get(self, url: str, headers) -> tuple[int, bytes]:
        self.asked.append(url)
        return self.answers.get(url, (404, b""))

    def run_it(self, environ: dict) -> str:
        out = io.StringIO()
        with redirect_stdout(out):
            code = programmes.main(get=self.get, sleep=lambda seconds: None, environ=environ,
                                   cache_dir=str(self.folder / "cache"), note=str(self.folder / "prepared.json"))
        self.assertEqual(code, 0)
        return out.getvalue()

    def test_each_shop_with_its_relationship_its_feed_and_the_sites_products(self) -> None:
        text = self.run_it({"AWIN_API_TOKEN": TOKEN, "AWIN_FEED_URL": FIRST, "AWIN_FEED_URL_AWIN": SECOND})
        self.assertIn("the feed's copies: 2; advertisers in them: 3", text)
        self.assertIn("programmes, joined: 1 (Active 1)", text)
        self.assertIn("programmes, notjoined: 1 (Active 1)", text)
        self.assertIn("programmes, rejected: Awin answered 401", text)
        self.assertIn("the feed list: 2 feeds of 2 advertisers; membership: active 1, not joined 1", text)
        self.assertIn("the catalogue's shops: 3 advertisers in the feed's copies, 1,000 products on the site", text)
        self.assertIn("  notjoined: 1 shops, 600 products (60.0%)", text)
        self.assertIn("  joined: 1 shops, 300 products (30.0%)", text)
        self.assertIn("  in no list: 1 shops, 100 products (10.0%)", text)
        lines = [line for line in text.splitlines() if line.endswith(")") and "(" in line and line[:9].strip()[:1].isdigit()]
        self.assertEqual(len(lines), 3)
        self.assertIn("notjoined", lines[0])
        self.assertIn("not joined", lines[0])
        self.assertIn("2026-11-18 22:00:00", lines[0])
        self.assertTrue(lines[0].endswith("Tool Shop (202)"))
        self.assertIn("no feed listed", lines[2])
        # The old copy's advertiser is no shop of the catalogue.
        self.assertNotIn("Gone Shop", text)

    def test_no_token_key_account_or_link_is_printed(self) -> None:
        text = self.run_it({"AWIN_API_TOKEN": TOKEN, "AWIN_FEED_URL": FIRST, "AWIN_FEED_URL_AWIN": SECOND})
        for secret in (TOKEN, KEY, PUBLISHER, FIRST, SECOND, "feeds.example.invalid"):
            self.assertNotIn(secret, text)
        # The feed list asked with the key its links carry.
        self.assertIn(programmes.FEED_LIST.format(key=KEY), self.asked)

    def test_without_secrets_nothing_is_asked(self) -> None:
        text = self.run_it({})
        self.assertEqual(self.asked, [])
        self.assertIn("no Awin token", text)
        self.assertIn("the feed list not read", text.replace("no feed link with a key in the server's secrets: the feed list not read", "the feed list not read"))


if __name__ == "__main__":
    unittest.main()
