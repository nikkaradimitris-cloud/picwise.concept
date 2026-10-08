"""Mission delivery coverage for the purchase-intent decision path.

Covers the Decision Contract items that the provider-feed surface previously left
unmet (docs/PICWISE_DECISION_CONTRACT.md):

- an inbound purchase-intent query on `/` must return the decision, not an empty
  landing page (concept: "Όταν έρχεται από Google ... δεν πρέπει να μπει σε κενή
  σελίδα search")
- the store line must name the merchant the feed names, never a hardcoded shop
- every CTA must emit a tracking event and redirect through PicWise

Also guards the feed caches added for the PROJECT_RULES section 9 latency targets:
a cache that served stale offers after a feed change would be a correctness bug,
not a speed win.
"""
from __future__ import annotations

import gzip
import io
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.index import _APP, app as wsgi_app  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.contracts import ProviderFeedConfig  # noqa: E402
from picwise_providers.state import (  # noqa: E402
    clear_provider_feed_pipeline_cache,
    resolve_card_eligible_provider_feed_product_by_id,
    resolve_provider_feed_pipeline,
)

FIXTURE_CSV = ROOT / "tests" / "fixtures" / "provider_feed_local_test_fixture.csv"
_FEED_ENV = "AWIN_FEED_FILE"


def _call(path: str, query_string: str = "") -> tuple[str, dict[str, str], str]:
    holder: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        holder["status"] = status
        holder["headers"] = {key: value for key, value in headers}

    environ: dict[str, object] = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "wsgi.input": io.BytesIO(b""),
        "CONTENT_LENGTH": "0",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "80",
        "wsgi.url_scheme": "https",
    }
    body = b"".join(wsgi_app(environ, start_response)).decode("utf-8")
    return (
        str(holder.get("status") or ""),
        dict(holder.get("headers") or {}),
        body,
    )


def _clear_feed_caches() -> None:
    clear_awin_feed_parse_cache()
    clear_provider_feed_pipeline_cache()


class _FixtureFeedTestCase(unittest.TestCase):
    """Point the app at the in-repo fixture feed for the duration of the test."""

    def setUp(self) -> None:
        self._previous_feed = os.environ.get(_FEED_ENV)
        os.environ[_FEED_ENV] = str(FIXTURE_CSV)
        _clear_feed_caches()
        _APP.clear_feed_outbound_click_events()
        self.addCleanup(self._restore_feed_env)
        self.addCleanup(_clear_feed_caches)
        self.addCleanup(_APP.clear_feed_outbound_click_events)

    def _restore_feed_env(self) -> None:
        if self._previous_feed is None:
            os.environ.pop(_FEED_ENV, None)
        else:
            os.environ[_FEED_ENV] = self._previous_feed


class InboundQueryLandsOnDecisionTests(_FixtureFeedTestCase):
    def test_root_with_purchase_intent_query_returns_the_decision(self) -> None:
        status, _headers, body = _call("/", "q=laptop")
        self.assertTrue(status.startswith("200"), status)
        self.assertIn("Showing 4 selected real products for: laptop", body)

    def test_root_without_a_query_stays_the_plain_landing(self) -> None:
        status, _headers, body = _call("/")
        self.assertTrue(status.startswith("200"), status)
        self.assertNotIn("Showing 4 selected real products", body)

    def test_root_and_search_agree_for_the_same_query(self) -> None:
        _status_a, _h, root_body = _call("/", "q=laptop")
        _status_b, _h2, search_body = _call("/search", "q=laptop")
        for product_id in ("fx-laptop-1", "fx-laptop-4"):
            self.assertIn(product_id, root_body)
            self.assertIn(product_id, search_body)

    def test_root_keeps_safe_empty_state_for_unstocked_query(self) -> None:
        status, _headers, body = _call("/", "q=office+chair")
        self.assertTrue(status.startswith("200"), status)
        self.assertNotIn("Showing 4 selected real products", body)


class MerchantAttributionTests(_FixtureFeedTestCase):
    def test_store_line_names_the_merchant_from_the_feed_row(self) -> None:
        _status, _headers, body = _call("/search", "q=laptop")
        self.assertIn("Fixture Store One via Awin", body)

    def test_missing_merchant_is_reported_as_unknown_not_invented(self) -> None:
        # The fixture's monitor rows deliberately carry no merchant_name.
        _status, _headers, body = _call("/search", "q=monitor")
        self.assertIn("Awin provider feed (merchant not named in feed)", body)

    def test_no_hardcoded_merchant_name_is_injected(self) -> None:
        reference_source = (SRC / "picwise_surface" / "reference.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("Geekbuying", reference_source)
        for query in ("laptop", "mouse", "monitor"):
            with self.subTest(query=query):
                _status, _headers, body = _call("/search", f"q={quote(query)}")
                self.assertNotIn("Geekbuying", body)


class TrackedRedirectTests(_FixtureFeedTestCase):
    def test_every_feed_cta_routes_through_the_tracked_redirect(self) -> None:
        _status, _headers, body = _call("/search", "q=laptop")
        self.assertIn("/out/feed?pid=", body)
        self.assertNotIn('href="https://fixture.example.invalid', body)

    def test_exactly_one_cta_is_flagged_as_the_recommendation(self) -> None:
        _status, _headers, body = _call("/search", "q=laptop")
        self.assertEqual(body.count("&amp;rec=1"), 1)
        self.assertEqual(body.count("&amp;rec=0"), 3)

    def test_click_records_events_and_redirects_to_the_product(self) -> None:
        status, headers, _body = _call(
            "/out/feed", "pid=fx-laptop-4&q=laptop&src=search&rec=1"
        )
        self.assertTrue(status.startswith("302"), status)
        self.assertEqual(
            headers.get("Location"),
            "https://fixture.example.invalid/products/sampleworks-lite-13",
        )
        names = [event["event_name"] for event in _APP.get_feed_outbound_click_events()]
        self.assertIn("recommended_click", names)
        self.assertIn("redirect_success", names)

    def test_non_recommended_click_is_recorded_under_its_own_event(self) -> None:
        _status, _headers, _body = _call(
            "/out/feed", "pid=fx-laptop-1&q=laptop&src=search&rec=0"
        )
        names = [event["event_name"] for event in _APP.get_feed_outbound_click_events()]
        self.assertIn("non_recommended_click", names)
        self.assertNotIn("recommended_click", names)

    def test_recorded_events_never_carry_invented_revenue_or_session(self) -> None:
        _call("/out/feed", "pid=fx-laptop-4&q=laptop&src=search&rec=1")
        events = _APP.get_feed_outbound_click_events()
        self.assertTrue(events)
        for event in events:
            self.assertEqual(event["revenue_value"], "not_applicable")
            self.assertEqual(event["conversion_value"], "not_applicable")
            self.assertEqual(event["session_id"], "not_connected")

    def test_unavailable_product_is_refused_instead_of_redirected(self) -> None:
        for product_id in ("fx-laptop-oos", "fx-laptop-eol"):
            with self.subTest(product_id=product_id):
                _APP.clear_feed_outbound_click_events()
                status, headers, body = _call(
                    "/out/feed", f"pid={product_id}&q=laptop&src=search&rec=0"
                )
                self.assertTrue(status.startswith("200"), status)
                self.assertIsNone(headers.get("Location"))
                self.assertIn("no longer available", body)
                names = [
                    event["event_name"]
                    for event in _APP.get_feed_outbound_click_events()
                ]
                self.assertEqual(names, ["redirect_failure"])

    def test_unknown_product_id_is_refused(self) -> None:
        status, headers, body = _call("/out/feed", "pid=not-a-real-id&q=laptop")
        self.assertTrue(status.startswith("200"), status)
        self.assertIsNone(headers.get("Location"))
        self.assertIn("no longer available", body)

    def test_empty_product_id_is_refused(self) -> None:
        status, headers, _body = _call("/out/feed", "q=laptop")
        self.assertTrue(status.startswith("200"), status)
        self.assertIsNone(headers.get("Location"))


class ImpressionTrackingTests(_FixtureFeedTestCase):
    """Decision Contract item 7 covers impression events, not only click and redirect."""

    def setUp(self) -> None:
        super().setUp()
        _APP.clear_decision_impression_events()
        self.addCleanup(_APP.clear_decision_impression_events)

    def _events(self, path: str, query_string: str = "") -> list[dict[str, str]]:
        _APP.clear_decision_impression_events()
        _call(path, query_string)
        return _APP.get_decision_impression_events()

    def _names(self, path: str, query_string: str = "") -> list[str]:
        return [event["event_name"] for event in self._events(path, query_string)]

    def test_rendered_decision_emits_the_full_impression_set(self) -> None:
        names = self._names("/search", "q=laptop")
        for expected in (
            "page_impression",
            "query_served",
            "choices_shown",
            "recommended_shown",
        ):
            self.assertIn(expected, names)

    def test_choices_shown_reports_the_rendered_count_and_provider(self) -> None:
        events = self._events("/search", "q=laptop")
        shown = next(e for e in events if e["event_name"] == "choices_shown")
        self.assertEqual(shown["choice_count"], "4")
        self.assertEqual(shown["provider_id"], "awin")

    def test_recommended_shown_names_the_rendered_recommendation(self) -> None:
        events = self._events("/search", "q=laptop")
        recommended = next(e for e in events if e["event_name"] == "recommended_shown")
        self.assertTrue(recommended["choice_id"].startswith("fx-"))
        self.assertTrue(recommended["recommendation_confidence"])

    def test_safe_empty_page_never_claims_choices_were_shown(self) -> None:
        events = self._events("/search", "q=office+chair")
        names = [event["event_name"] for event in events]
        self.assertIn("page_impression", names)
        self.assertNotIn("recommended_shown", names)
        shown = next(e for e in events if e["event_name"] == "choices_shown")
        self.assertEqual(shown["choice_count"], "0")

    def test_landing_without_a_query_emits_no_query_served(self) -> None:
        names = self._names("/")
        self.assertIn("page_impression", names)
        self.assertNotIn("query_served", names)
        self.assertNotIn("recommended_shown", names)

    def test_impression_events_never_carry_invented_values(self) -> None:
        for path, query_string in (("/search", "q=laptop"), ("/", "")):
            with self.subTest(path=path):
                for event in self._events(path, query_string):
                    self.assertEqual(event["session_id"], "not_connected")
                    self.assertEqual(event["conversion_value"], "not_applicable")
                    self.assertEqual(event["revenue_value"], "not_applicable")

    def test_choices_shown_follows_the_renderer_not_the_backend(self) -> None:
        # "tv" has a backend selection the surface refuses to render. The event must
        # report what was shown, so it may not claim choices were shown.
        from picwise_search.live_search_resolver import resolve_live_search
        from picwise_surface import provider_feed_cards_will_render

        resolution = resolve_live_search("tv")
        self.assertFalse(provider_feed_cards_will_render(resolution))
        events = self._events("/search", "q=tv")
        shown = next(e for e in events if e["event_name"] == "choices_shown")
        self.assertEqual(shown["choice_count"], "0")
        self.assertNotIn(
            "recommended_shown", [event["event_name"] for event in events]
        )


class FeedCacheCorrectnessTests(unittest.TestCase):
    """The latency caches must never serve offers from a superseded feed."""

    def setUp(self) -> None:
        self._previous_feed = os.environ.get(_FEED_ENV)
        _clear_feed_caches()
        self.addCleanup(self._restore_feed_env)
        self.addCleanup(_clear_feed_caches)

    def _restore_feed_env(self) -> None:
        if self._previous_feed is None:
            os.environ.pop(_FEED_ENV, None)
        else:
            os.environ[_FEED_ENV] = self._previous_feed

    def test_changed_feed_file_is_re_read_not_served_from_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feed_path = Path(tmp) / "feed.csv"
            shutil.copyfile(FIXTURE_CSV, feed_path)
            config = ProviderFeedConfig(provider_key="awin", feed_file=str(feed_path))

            first = resolve_provider_feed_pipeline(config)
            self.assertEqual(first.feed_status.status, "provider_feed_ready")
            self.assertIsNotNone(
                resolve_card_eligible_provider_feed_product_by_id(
                    "fx-laptop-1", feed_config=config
                )
            )

            # Rewrite the feed with that product marked out of stock.
            text = feed_path.read_text(encoding="utf-8")
            rewritten = "\n".join(
                line.replace(",in stock,", ",out of stock,")
                if line.startswith("fx-laptop-1,")
                else line
                for line in text.splitlines()
            )
            time.sleep(0.01)
            feed_path.write_text(rewritten + "\n", encoding="utf-8")

            self.assertIsNone(
                resolve_card_eligible_provider_feed_product_by_id(
                    "fx-laptop-1", feed_config=config
                ),
                msg="a cached parse must not keep an out-of-stock offer redirectable",
            )

    def test_gzip_and_plain_feeds_resolve_to_the_same_eligibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gz_path = Path(tmp) / "feed.csv.gz"
            gz_path.write_bytes(gzip.compress(FIXTURE_CSV.read_bytes()))
            plain = resolve_provider_feed_pipeline(
                ProviderFeedConfig(provider_key="awin", feed_file=str(FIXTURE_CSV))
            )
            gzipped = resolve_provider_feed_pipeline(
                ProviderFeedConfig(provider_key="awin", feed_file=str(gz_path))
            )
            self.assertEqual(
                gzipped.feed_status.eligible_count, plain.feed_status.eligible_count
            )

    def test_skipping_graph_projection_does_not_change_eligibility(self) -> None:
        config = ProviderFeedConfig(provider_key="awin", feed_file=str(FIXTURE_CSV))
        with_graph = resolve_provider_feed_pipeline(config, include_graph_projection=True)
        without_graph = resolve_provider_feed_pipeline(
            config, include_graph_projection=False
        )
        self.assertIsNotNone(with_graph.graph_projection)
        self.assertIsNone(without_graph.graph_projection)
        self.assertEqual(
            with_graph.feed_status.eligible_count,
            without_graph.feed_status.eligible_count,
        )
        self.assertEqual(
            len(with_graph.eligibility_results), len(without_graph.eligibility_results)
        )


class SearchRuntimeArtifactFreshnessTests(unittest.TestCase):
    """A stale committed artifact silently costs every cold start seconds.

    When the artifact stops matching its fingerprint sources the app falls back to
    the live index builder and only logs a warning, which is how a first request
    grew to ~8.8s unnoticed. Fail loudly instead, with the rebuild command.
    """

    def test_committed_artifact_matches_its_fingerprint_sources(self) -> None:
        from picwise_search_memory.search_runtime_artifact import (
            compute_source_fingerprint,
            default_artifact_path,
            parse_search_runtime_artifact_bytes,
        )

        artifact_path = default_artifact_path()
        self.assertTrue(
            artifact_path.is_file(),
            msg=f"search runtime artifact missing at {artifact_path}",
        )
        envelope = parse_search_runtime_artifact_bytes(raw=artifact_path.read_bytes())
        self.assertEqual(
            str(envelope.get("source_fingerprint") or ""),
            compute_source_fingerprint(),
            msg=(
                "The committed search runtime artifact no longer matches its source "
                "files, so every process start will rebuild the index live and the "
                "first render will miss the PROJECT_RULES section 9 target. Rebuild "
                "it with: python tools/build_picwise_search_artifact.py"
            ),
        )


if __name__ == "__main__":
    unittest.main()
