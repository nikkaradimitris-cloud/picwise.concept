"""The night's preparation reads the feed once, even when its downloaded copy expires in the
middle of the run (owner, 2026-11-20: «Φτιάξε και αυτό Η επεξεργασία να διαβάζει το feed
μία φορά, ακόμα κι αν λήξει στη μέση»).

On 2026-11-20 at 10:04 UTC a deployment's preparation began from the night's download of
04:17, which `awin_adapter.materialize_feed_url` keeps for six hours. It wrote the catalogue
at 10:19:40; then its intake (`state.measure_configured_feed_intake`) asked for the feed
again, found the copy past its six hours, downloaded both links again and, the new files
missing the pipeline's cache, parsed all 2.7 million rows a second time beside the first:
the run passed its memory ceiling (18.4 GB of 18) and was killed. Pinned here: the copy is
chosen once (`tools/prepare_catalogue.py`), and the intake reads what the catalogue was
read from: with a copy that expires at once (a lifetime of 0 s), the link is downloaded
once and the feed parsed once, and the note still counts every shop.

Every row is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
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
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "product_type", "merchant_category", "aw_deep_link",
    "aw_image_url", "search_price", "currency", "in_stock", "merchant_name", "description",
)
_ENV = (
    "AWIN_FEED_FILE", "AWIN_FEED_URL", "AWIN_FEED_FILE_AWIN", "AWIN_FEED_URL_AWIN",
    "AWIN_FEED_CACHE_DIR", "AWIN_FEED_CACHE_TTL_SECONDS",
)


def _load_tool():
    spec = importlib.util.spec_from_file_location("prepare_catalogue_once_tool", ROOT / "tools" / "prepare_catalogue.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReadOnceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        saved = {name: os.environ.get(name) for name in _ENV}

        def restore() -> None:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)
        for name in _ENV:
            os.environ.pop(name, None)
        self.source = self.folder / "the-shops-feed.csv"
        with self.source.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for shop, rows in {"Alpha Shop": 30, "Beta Shop": 20}.items():
                for number in range(rows):
                    pid = f"{shop.split()[0].lower()}-{number}"
                    writer.writerow([
                        pid, f"Fixturon Electric Kettle {number} 1.7L", "Fixturon", "Kettles", "Kitchen Appliances",
                        f"https://fixture.example.invalid/out/{pid}", f"https://fixture.example.invalid/img/{pid}.jpg",
                        f"{10 + number}.00", "GBP", "1", shop, fixture_description(),
                    ])
        # A link, its downloads kept in a folder of their own, each copy expiring at once.
        os.environ["AWIN_FEED_URL"] = "https://feeds.example.invalid/datafeed/download/fixture"
        os.environ["AWIN_FEED_CACHE_DIR"] = str(self.folder / "cache")
        os.environ["AWIN_FEED_CACHE_TTL_SECONDS"] = "0"
        (self.folder / "cache").mkdir()
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    def test_a_copy_that_expires_mid_run_is_downloaded_and_parsed_once(self) -> None:
        downloads: list[str] = []
        parses: list[object] = []
        load = state.load_awin_provider_feed

        def download(feed_url: str, destination: str):
            downloads.append(feed_url)
            shutil.copyfile(self.source, destination)
            return True, ()

        def parse(config):
            parses.append(config)
            return load(config)

        printed = io.StringIO()
        with patch.object(awin_adapter, "_download_feed", download), \
                patch.object(state, "load_awin_provider_feed", parse), redirect_stdout(printed):
            code = _load_tool().main([
                "--out", str(self.folder / "catalogue.json.gz"), "--static-dir", str(self.folder / "public"),
            ])
        self.assertEqual(code, 0, printed.getvalue())
        self.assertEqual(len(downloads), 1)
        self.assertEqual(len(parses), 1)
        note = json.loads((self.folder / "public" / "prepared.json").read_text(encoding="utf-8"))
        self.assertTrue(note["prepared"])
        self.assertEqual(note["products"], 50)
        # The intake still counts every shop, from the same reading.
        rows = {entry["shop"]: entry["rows"] for entry in note["intake"]["shops"]}
        self.assertEqual(rows, {"Alpha Shop": 30, "Beta Shop": 20})


if __name__ == "__main__":
    unittest.main()
