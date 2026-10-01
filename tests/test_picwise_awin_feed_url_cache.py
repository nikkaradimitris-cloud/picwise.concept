"""An Awin feed given as a URL is downloaded once and reused, never per search.

`file://` URLs stand in for Awin's download link, so these tests touch no network.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_providers import awin_adapter  # noqa: E402
from picwise_providers.awin_adapter import (  # noqa: E402
    awin_feed_config_from_env,
    clear_awin_feed_parse_cache,
    load_awin_provider_feed,
    materialize_feed_url,
)
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "provider_feed_coverage_matrix_fixture.csv"
_ENV = (
    "AWIN_FEED_FILE",
    "AWIN_FEED_URL",
    "AWIN_FEED_CACHE_DIR",
    "AWIN_FEED_CACHE_TTL_SECONDS",
    "AWIN_FEED_MAX_STALE_SECONDS",
)


class FeedUrlCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {name: os.environ.get(name) for name in _ENV}
        self.cache_dir = tempfile.mkdtemp()
        self.source_dir = tempfile.mkdtemp()
        self.source = Path(self.source_dir) / "feed.csv"
        shutil.copy(FIXTURE, self.source)
        self.url = self.source.as_uri()
        for name in _ENV:
            os.environ.pop(name, None)
        os.environ["AWIN_FEED_CACHE_DIR"] = self.cache_dir
        awin_adapter._FAILED_FETCHES.clear()
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        shutil.rmtree(self.cache_dir, ignore_errors=True)
        shutil.rmtree(self.source_dir, ignore_errors=True)
        awin_adapter._FAILED_FETCHES.clear()
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    def test_a_feed_url_is_downloaded_to_a_local_file(self) -> None:
        path, errors = materialize_feed_url(self.url)
        self.assertEqual(errors, tuple())
        self.assertEqual(Path(path).read_bytes(), FIXTURE.read_bytes())

    def test_the_cache_file_name_does_not_reveal_the_url(self) -> None:
        # Awin download links carry the account's API key.
        path = awin_adapter._feed_cache_path(
            "https://productdata.awin.com/datafeed/download/apikey/SECRETKEY/fid/1/format/csv/"
        )
        self.assertNotIn("SECRETKEY", path)
        self.assertNotIn("awin.com", path)

    def test_a_fresh_copy_is_reused_without_downloading(self) -> None:
        path, _ = materialize_feed_url(self.url)
        self.source.unlink()  # the source vanishing must not matter while fresh
        again, errors = materialize_feed_url(self.url)
        self.assertEqual(again, path)
        self.assertEqual(errors, tuple())

    def test_a_stale_copy_is_refreshed(self) -> None:
        path, _ = materialize_feed_url(self.url)
        self.source.write_text("aw_product_id,product_name\nnew-1,Refreshed\n", encoding="utf-8")
        old = time.time() - 7 * 3600
        os.utime(path, (old, old))
        materialize_feed_url(self.url)
        self.assertIn("Refreshed", Path(path).read_text(encoding="utf-8"))

    def test_a_failed_refresh_serves_the_previous_copy_for_a_while(self) -> None:
        path, _ = materialize_feed_url(self.url)
        self.source.unlink()
        old = time.time() - 7 * 3600
        os.utime(path, (old, old))
        served, errors = materialize_feed_url(self.url)
        self.assertEqual(served, path)
        self.assertIn("serving_previous_feed_copy", errors)

    def test_a_copy_past_the_staleness_limit_is_not_served(self) -> None:
        path, _ = materialize_feed_url(self.url)
        self.source.unlink()
        old = time.time() - 30 * 3600
        os.utime(path, (old, old))
        served, errors = materialize_feed_url(self.url)
        self.assertIsNone(served)
        self.assertTrue(any(error.startswith("feed_url_fetch_failed") for error in errors))

    def test_a_broken_url_is_not_retried_on_every_request(self) -> None:
        missing = (Path(self.source_dir) / "missing.csv").as_uri()
        first, _ = materialize_feed_url(missing)
        second, errors = materialize_feed_url(missing)
        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertIn("feed_url_fetch_failed:recently", errors)

    def test_the_environment_url_reaches_the_pipeline_as_a_file(self) -> None:
        os.environ["AWIN_FEED_URL"] = self.url
        config = awin_feed_config_from_env()
        self.assertTrue(config.feed_file)
        self.assertIsNone(config.feed_url)
        result = load_awin_provider_feed(config)
        self.assertEqual(result.status, "provider_feed_loaded")
        self.assertEqual(len(result.products), 132)

    def test_an_unreachable_url_reports_the_feed_as_failed(self) -> None:
        os.environ["AWIN_FEED_URL"] = (Path(self.source_dir) / "missing.csv").as_uri()
        result = load_awin_provider_feed(awin_feed_config_from_env())
        self.assertEqual(result.status, "provider_feed_parse_failed")


if __name__ == "__main__":
    unittest.main()
