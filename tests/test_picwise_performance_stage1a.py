from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import PicwiseLocalApp  # noqa: E402
from picwise_search import resolve_live_search  # noqa: E402
from picwise_search.index_resolver_adapter import get_cached_offline_search_index  # noqa: E402
from picwise_search.live_search_resolver import _vocabulary_registry  # noqa: E402
from picwise_search_memory.canonical_registry import (  # noqa: E402
    build_canonical_vocabulary_registry,
    get_cached_canonical_vocabulary_registry,
)


def _assert_landing_shell(test_case: unittest.TestCase, body: str) -> None:
    expected_links = (
        ("/", "Home"),
        ("/demo", "Demo"),
        ("/picwise-reference", "PicWise Reference"),
        ("/terms", "Terms"),
        ("/privacy", "Privacy"),
        ("/cookies", "Cookies"),
        ("/affiliate-disclosure", "Affiliate Disclosure"),
        ("/contact", "Contact"),
    )
    for href, label in expected_links:
        test_case.assertIn(f'class="pw-footer-link" href="{href}">{label}<', body)
    test_case.assertIn("See the 4 best products before you buy", body)
    test_case.assertIn("Live safe mode", body)
    test_case.assertIn('action="/search"', body)
    test_case.assertIn('method="get"', body)
    test_case.assertIn('name="q"', body)
    test_case.assertIn("What is PicWise?", body)


class PicwisePerformanceStage1ATests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = PicwiseLocalApp()

    def test_empty_homepage_does_not_call_resolve_live_search(self) -> None:
        with patch("picwise_app.app.resolve_live_search") as resolve_mock:
            html = self.app.root_landing_html()
        resolve_mock.assert_not_called()
        _assert_landing_shell(self, html)

    def test_whitespace_reference_query_does_not_call_resolve_live_search(self) -> None:
        with patch("picwise_app.app.resolve_live_search") as resolve_mock:
            html = self.app.picwise_reference_html("  \t  ")
        resolve_mock.assert_not_called()
        self.assertIn('value="  \t  "', html)
        _assert_landing_shell(self, html)

    def test_non_empty_reference_query_still_calls_resolve_live_search(self) -> None:
        with patch("picwise_app.app.resolve_live_search", wraps=resolve_live_search) as resolve_mock:
            html = self.app.picwise_reference_html("power bank")
        resolve_mock.assert_called_once_with("power bank")
        self.assertIn("View on Amazon", html)

    def test_shared_registry_cache_returns_equivalent_data(self) -> None:
        import picwise_search.index_resolver_adapter as index_adapter
        import picwise_search_memory.canonical_registry as canonical_registry
        from picwise_search_memory.search_runtime_artifact import _reset_search_runtime_artifact_for_tests

        index_adapter._CACHED_OFFLINE_INDEX = None
        canonical_registry._CACHED_REGISTRY = None
        _reset_search_runtime_artifact_for_tests()

        build_calls: list[str] = []

        def _counting_build() -> object:
            build_calls.append("build")
            return build_canonical_vocabulary_registry()

        with patch(
            "picwise_search_memory.search_runtime_artifact.try_hydrate_runtime_from_artifact",
            return_value=None,
        ):
            with patch(
                "picwise_search_memory.canonical_registry.build_canonical_vocabulary_registry",
                side_effect=_counting_build,
            ):
                get_cached_offline_search_index()
                adapter_registry = get_cached_canonical_vocabulary_registry()
                live_registry = _vocabulary_registry()

        self.assertEqual(len(build_calls), 1)
        self.assertIs(adapter_registry, live_registry)
        fresh = build_canonical_vocabulary_registry()
        self.assertEqual(
            tuple(record.canonical_id for record in adapter_registry.records),
            tuple(record.canonical_id for record in fresh.records),
        )


if __name__ == "__main__":
    unittest.main()
