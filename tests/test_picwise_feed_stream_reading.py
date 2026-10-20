"""A feed read as a stream, row by row, keeping only each row's filled columns.

`src/picwise_providers/awin_adapter.py`. Owner, 2026-10-18: many more shops first. A
feed held whole costs its compressed bytes, its text and every row with all 149 Awin
columns at once: measured on a fictional Awin-shaped feed, the 8 GB of a Vercel build
would run out near 380,000 rows. Pinned here: a row keeps only its filled columns; the
reading is otherwise the one before (a UTF-8 mark, Latin-1 for a feed that is not
UTF-8 even far down, line endings, a quoted line break, a repeated column name, blank
lines, a row too short or too long); and a broken or cut gzip file is a feed that
failed to parse, not an error.

Every row is local test data: fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import gzip
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.awin_adapter import clear_awin_feed_parse_cache, load_awin_provider_feed  # noqa: E402
from picwise_providers.contracts import ProviderFeedConfig  # noqa: E402


class StreamReadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        clear_awin_feed_parse_cache()
        self.addCleanup(clear_awin_feed_parse_cache)

    def _load(self, name: str, data: bytes):
        path = self.folder / name
        path.write_bytes(data)
        return load_awin_provider_feed(ProviderFeedConfig(provider_key="awin", feed_file=str(path)))

    def test_a_row_keeps_only_its_filled_columns(self) -> None:
        result = self._load(
            "feed.csv.gz",
            gzip.compress(
                b"aw_product_id,product_name,aw_deep_link,brand_name,colour,ean\n"
                b"A1,Fixturon Kettle,https://fixture.example.invalid/a1,Fixturon,,\n"
                b"A2,Fixturon Lamp,https://fixture.example.invalid/a2,,Black,\n"
            ),
        )
        self.assertEqual(result.status, "provider_feed_loaded")
        self.assertEqual(
            [dict(product.raw) for product in result.products],
            [
                {"aw_product_id": "A1", "product_name": "Fixturon Kettle",
                 "aw_deep_link": "https://fixture.example.invalid/a1", "brand_name": "Fixturon"},
                {"aw_product_id": "A2", "product_name": "Fixturon Lamp",
                 "aw_deep_link": "https://fixture.example.invalid/a2", "colour": "Black"},
            ],
        )
        self.assertEqual(result.products[1].brand, "")

    def test_text_is_read_as_before(self) -> None:
        with self.subTest("a UTF-8 mark at the start"):
            result = self._load("bom.csv", "﻿product_id,title,url\nB1,Café Kettle,https://x.example.invalid/b1\n".encode("utf-8"))
            self.assertEqual(result.products[0].provider_product_id, "B1")
            self.assertEqual(result.products[0].title, "Café Kettle")
        with self.subTest("a byte that is not UTF-8, far down the feed: all of it as Latin-1"):
            rows = "".join(f"P{index},Fixturon Kettle {index},https://x.example.invalid/{index}\n" for index in range(5000))
            data = ("product_id,title,url\n" + rows).encode("utf-8") + b"Z1,Caf\xe9 Lamp,https://x.example.invalid/z1\n"
            result = self._load("latin.csv", data)
            self.assertEqual(len(result.products), 5001)
            self.assertEqual(result.products[-1].title, "Caf\xe9 Lamp")
        with self.subTest("CRLF endings and a quoted line break"):
            result = self._load(
                "crlf.csv",
                b'product_id,title,url,description\r\nC1,Kettle,https://x.example.invalid/c1,"one\r\ntwo"\r\n'
                b"C2,Lamp,https://x.example.invalid/c2,\r\n",
            )
            self.assertEqual([product.title for product in result.products], ["Kettle", "Lamp"])
            self.assertEqual(result.products[0].raw["description"], "one\r\ntwo")
            self.assertNotIn("description", result.products[1].raw)
        with self.subTest("a repeated column name takes its last value"):
            result = self._load(
                "repeated.csv",
                b"product_id,title,url,brand,brand\nD1,Kettle,https://x.example.invalid/d1,One,\n"
                b"D2,Lamp,https://x.example.invalid/d2,,Two\n",
            )
            self.assertEqual([product.brand for product in result.products], ["", "Two"])
        with self.subTest("blank lines, a short row and a long one"):
            result = self._load(
                "uneven.csv",
                b"product_id,title,url,brand\nE1,Kettle,https://x.example.invalid/e1\n\n\n"
                b"E2,Lamp,https://x.example.invalid/e2,Br,extra,more\n",
            )
            self.assertEqual([dict(product.raw) for product in result.products], [
                {"product_id": "E1", "title": "Kettle", "url": "https://x.example.invalid/e1"},
                {"product_id": "E2", "title": "Lamp", "url": "https://x.example.invalid/e2", "brand": "Br"},
            ])

    def test_a_broken_or_cut_gzip_file_failed_to_parse(self) -> None:
        whole = gzip.compress(
            ("product_id,title,url\n" + "".join(f"P{index},Kettle {index},https://x.example.invalid/{index}\n"
                                                 for index in range(20000))).encode("utf-8")
        )
        for name, data in (("broken.csv.gz", b"\x1f\x8bnot-gzip"), ("cut.csv.gz", whole[: len(whole) // 2])):
            with self.subTest(name):
                result = self._load(name, data)
                self.assertEqual(result.status, "provider_feed_parse_failed")
                self.assertTrue(result.parse_errors[0].startswith("gzip_decompress_failed:"), result.parse_errors)

    def test_an_empty_or_missing_feed(self) -> None:
        self.assertEqual(self._load("empty.csv", b"  \n\n ").reason_codes, ("feed_empty",))
        self.assertEqual(self._load("header.csv", b"product_id,title,url\n").status, "provider_feed_empty")
        missing = load_awin_provider_feed(
            ProviderFeedConfig(provider_key="awin", feed_file=os.path.join(self.folder, "no-such-feed.csv"))
        )
        self.assertEqual(missing.parse_errors, ("feed_file_read_failed:FileNotFoundError",))


if __name__ == "__main__":
    unittest.main()
