from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import PicwiseLocalApp  # noqa: E402
from picwise_search import resolve_live_search, search_warmup  # noqa: E402
from picwise_search.index_resolver_adapter import (  # noqa: E402
    get_cached_offline_search_index,
    resolve_query_with_search_index,
)
from picwise_search.search_warmup import get_search_warmup_state, schedule_search_warmup_if_needed  # noqa: E402
from picwise_search_memory import build_offline_search_index, lookup_offline_search_index  # noqa: E402
from picwise_search_memory.canonical_registry import (  # noqa: E402
    build_canonical_vocabulary_registry,
    get_cached_canonical_vocabulary_registry,
)
from picwise_search_memory.search_runtime_artifact import (  # noqa: E402
    _reset_search_runtime_artifact_for_tests,
    build_search_runtime_artifact_envelope,
    compute_source_fingerprint,
    get_fingerprint_source_paths,
    get_search_runtime_artifact_status,
    hydrate_search_runtime_artifact,
    parse_search_runtime_artifact_bytes,
    try_hydrate_runtime_from_artifact,
    write_search_runtime_artifact,
)


def _reset_runtime_caches() -> None:
    import picwise_search.index_resolver_adapter as index_adapter
    import picwise_search_memory.canonical_registry as canonical_registry

    index_adapter._CACHED_OFFLINE_INDEX = None
    canonical_registry._CACHED_REGISTRY = None
    _reset_search_runtime_artifact_for_tests()


def _build_live_outputs(query: str) -> dict[str, object]:
    _reset_runtime_caches()
    with patch(
        "picwise_search_memory.search_runtime_artifact.try_hydrate_runtime_from_artifact",
        return_value=None,
    ):
        live_registry = build_canonical_vocabulary_registry()
        live_index = build_offline_search_index(registry=live_registry)
        return {
            "live_search": resolve_live_search(query).to_dict(),
            "index_resolver": resolve_query_with_search_index(query).to_dict(),
            "lookup": lookup_offline_search_index(query, live_index).to_dict(),
        }


def _build_artifact_outputs(query: str, *, artifact_path: Path) -> dict[str, object]:
    _reset_runtime_caches()
    bundle = try_hydrate_runtime_from_artifact(artifact_path=artifact_path)
    assert bundle is not None
    registry, index = bundle
    return {
        "live_search": resolve_live_search(query).to_dict(),
        "index_resolver": resolve_query_with_search_index(query).to_dict(),
        "lookup": lookup_offline_search_index(query, index).to_dict(),
    }


class PicwisePerformanceStage1CTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_runtime_caches()
        search_warmup._reset_search_warmup_for_tests()

    def tearDown(self) -> None:
        _reset_runtime_caches()
        search_warmup._reset_search_warmup_for_tests()

    def test_artifact_can_be_built_from_current_source_data(self) -> None:
        registry = build_canonical_vocabulary_registry()
        index = build_offline_search_index(registry=registry)
        envelope = build_search_runtime_artifact_envelope(registry, index, repo_root=ROOT)
        artifact_path = write_search_runtime_artifact(envelope)
        self.assertTrue(artifact_path.exists())
        self.assertLess(artifact_path.stat().st_size, 3 * 1024 * 1024)

    def test_artifact_includes_schema_fingerprint_counts_and_payloads(self) -> None:
        registry = build_canonical_vocabulary_registry()
        index = build_offline_search_index(registry=registry)
        envelope = build_search_runtime_artifact_envelope(registry, index, repo_root=ROOT)
        required_keys = {
            "artifact_schema_version",
            "builder_version",
            "source_fingerprint",
            "built_at",
            "counts",
            "registry_schema_version",
            "index_schema_version",
            "generator_version",
            "registry",
            "search_index",
        }
        self.assertTrue(required_keys.issubset(envelope.keys()))
        counts = envelope["counts"]
        self.assertEqual(counts["registry_records"], len(registry.records))
        self.assertEqual(counts["index_entries"], len(index.entries))
        self.assertIn("records", envelope["registry"])
        self.assertIn("entries", envelope["search_index"])

    def test_valid_artifact_loads_and_hydrates_registry_and_index(self) -> None:
        registry = build_canonical_vocabulary_registry()
        index = build_offline_search_index(registry=registry)
        envelope = build_search_runtime_artifact_envelope(registry, index, repo_root=ROOT)
        artifact_path = write_search_runtime_artifact(envelope)
        _reset_runtime_caches()
        loaded = parse_search_runtime_artifact_bytes(raw=artifact_path.read_bytes())
        hydrated_registry, hydrated_index = hydrate_search_runtime_artifact(loaded)
        self.assertEqual(len(hydrated_registry.records), len(registry.records))
        self.assertEqual(len(hydrated_index.entries), len(index.entries))

    def test_valid_artifact_avoids_slow_live_builder(self) -> None:
        registry = build_canonical_vocabulary_registry()
        index = build_offline_search_index(registry=registry)
        envelope = build_search_runtime_artifact_envelope(registry, index, repo_root=ROOT)
        artifact_path = write_search_runtime_artifact(envelope)
        _reset_runtime_caches()

        with patch(
            "picwise_search_memory.canonical_registry.build_canonical_vocabulary_registry",
        ) as registry_build_mock:
            with patch(
                "picwise_search.index_resolver_adapter.build_offline_search_index",
            ) as index_build_mock:
                bundle = try_hydrate_runtime_from_artifact(artifact_path=artifact_path)
                self.assertIsNotNone(bundle)
                get_cached_canonical_vocabulary_registry()
                get_cached_offline_search_index()

        registry_build_mock.assert_not_called()
        index_build_mock.assert_not_called()
        status = get_search_runtime_artifact_status()
        self.assertEqual(status["state"], "loaded")
        self.assertEqual(status["source"], "artifact")

    def test_fingerprint_mismatch_rejects_artifact_and_falls_back(self) -> None:
        registry = build_canonical_vocabulary_registry()
        index = build_offline_search_index(registry=registry)
        envelope = build_search_runtime_artifact_envelope(registry, index, repo_root=ROOT)
        envelope["source_fingerprint"] = "deadbeef"
        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_path = Path(tmp_dir) / "bad_fingerprint.json.gz"
            write_search_runtime_artifact(envelope, artifact_path=artifact_path)
            _reset_runtime_caches()

            with patch(
                "picwise_search_memory.canonical_registry.build_canonical_vocabulary_registry",
                return_value=registry,
            ) as registry_build_mock:
                bundle = try_hydrate_runtime_from_artifact(artifact_path=artifact_path)
                self.assertIsNone(bundle)
                get_cached_canonical_vocabulary_registry()

        registry_build_mock.assert_called_once()
        status = get_search_runtime_artifact_status()
        self.assertEqual(status["state"], "fallback")
        self.assertIn("source_fingerprint_mismatch", status["reason"])

    def test_corrupt_artifact_rejects_and_falls_back_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_path = Path(tmp_dir) / "corrupt.json.gz"
            artifact_path.write_bytes(b"not-a-valid-gzip-artifact")
            _reset_runtime_caches()

            with patch(
                "picwise_search_memory.canonical_registry.build_canonical_vocabulary_registry",
            ) as registry_build_mock:
                bundle = try_hydrate_runtime_from_artifact(artifact_path=artifact_path)
                self.assertIsNone(bundle)
                get_cached_canonical_vocabulary_registry()

        registry_build_mock.assert_called_once()
        status = get_search_runtime_artifact_status()
        self.assertEqual(status["state"], "fallback")
        self.assertIn("artifact_gzip_decompress_failed", status["reason"])

    def test_artifact_loaded_search_output_equals_builder_loaded_output(self) -> None:
        registry = build_canonical_vocabulary_registry()
        index = build_offline_search_index(registry=registry)
        envelope = build_search_runtime_artifact_envelope(registry, index, repo_root=ROOT)
        artifact_path = write_search_runtime_artifact(envelope)

        queries = (
            "power bank",
            "powerbanks",
            "laptop",
            "phone charger",
            "coffe grindr",
            "power",
        )
        for query in queries:
            with self.subTest(query=query):
                live = _build_live_outputs(query)
                artifact = _build_artifact_outputs(query, artifact_path=artifact_path)
                self.assertEqual(artifact["live_search"], live["live_search"])
                self.assertEqual(artifact["index_resolver"], live["index_resolver"])
                self.assertEqual(artifact["lookup"], live["lookup"])

    def test_empty_homepage_still_skips_resolver(self) -> None:
        app = PicwiseLocalApp()
        with patch("picwise_app.app.resolve_live_search") as resolve_mock:
            html = app.root_landing_html()
        resolve_mock.assert_not_called()
        self.assertIn("See the 4 best products before you buy", html)

    def test_stage1b_warmup_still_works_with_artifact_backed_cache(self) -> None:
        registry = build_canonical_vocabulary_registry()
        index = build_offline_search_index(registry=registry)
        envelope = build_search_runtime_artifact_envelope(registry, index, repo_root=ROOT)
        artifact_path = write_search_runtime_artifact(envelope)
        _reset_runtime_caches()

        captured: dict[str, object] = {}

        class _ImmediateTimer:
            def __init__(self, delay: float, callback) -> None:
                captured["callback"] = callback

            def start(self) -> None:
                return None

            def cancel(self) -> None:
                return None

        with patch.object(search_warmup, "_timer_factory", _ImmediateTimer):
            schedule_search_warmup_if_needed()
            callback = captured["callback"]
            self.assertEqual(get_search_warmup_state(), "scheduled")
            callback()

        self.assertEqual(get_search_warmup_state(), "ready")
        status = get_search_runtime_artifact_status()
        self.assertEqual(status["state"], "loaded")
        self.assertEqual(status["artifact_path"], str(artifact_path))

    def test_homepage_html_size_and_content_remain_unchanged(self) -> None:
        registry = build_canonical_vocabulary_registry()
        index = build_offline_search_index(registry=registry)
        envelope = build_search_runtime_artifact_envelope(registry, index, repo_root=ROOT)
        write_search_runtime_artifact(envelope)
        _reset_runtime_caches()

        app = PicwiseLocalApp()
        with patch(
            "picwise_search_memory.search_runtime_artifact.try_hydrate_runtime_from_artifact",
            return_value=None,
        ):
            baseline_html = app.root_landing_html()

        _reset_runtime_caches()
        artifact_html = app.root_landing_html()
        self.assertEqual(len(artifact_html), len(baseline_html))
        self.assertEqual(artifact_html, baseline_html)

    def test_fingerprint_source_list_is_centralized(self) -> None:
        paths = get_fingerprint_source_paths()
        self.assertIn("src/picwise_nlu/vocabulary_source.py", paths)
        self.assertIn("src/picwise_search_memory/canonical_registry.py", paths)
        self.assertIn("src/picwise_search_memory/index_builder.py", paths)
        self.assertEqual(compute_source_fingerprint(repo_root=ROOT), compute_source_fingerprint(repo_root=ROOT))


if __name__ == "__main__":
    unittest.main()
