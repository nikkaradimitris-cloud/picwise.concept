from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from picwise_nlu.query_variant_generator import _GENERATOR_VERSION as STAGE3_GENERATOR_VERSION

from .contracts import CanonicalVocabularyRegistry
from .index_contracts import SearchIndex
from .validation import validate_registry

_ARTIFACT_SCHEMA_VERSION = "1.0.0"
_BUILDER_VERSION = "1.0.0"
_REGISTRY_SCHEMA_VERSION = "1.0.0"
_INDEX_SCHEMA_VERSION = "1.0.0"
_ARTIFACT_FILENAME = "search_runtime_v1.json.gz"

_DEEP_PACK_FILES = (
    "home_living_appliances.py",
    "tech_electronics_office.py",
    "auto_moto_mobility.py",
    "tools_diy_garden_repair.py",
    "health_beauty_family_lifestyle.py",
    "fashion_footwear_jewelry_accessories.py",
)

_TAXONOMY_BRIDGE_STAGE_FILES: tuple[tuple[str, str], ...] = (
    ("stage24c", "src/picwise_taxonomy/importers/google_taxonomy_importer.py"),
    ("stage24d", "src/picwise_taxonomy/mapping/google_stage24d.py"),
    ("stage24e", "src/picwise_taxonomy/mapping/gap_report_stage24e.py"),
    ("stage25a", "src/picwise_taxonomy/canonical/registry_builder.py"),
    ("stage25b", "src/picwise_taxonomy/canonical/coverage_matrix.py"),
    ("stage25c", "src/picwise_taxonomy/canonical/deduplication.py"),
    ("stage27a", "src/picwise_taxonomy/nlu_export/exporter.py"),
    ("stage27b", "src/picwise_taxonomy/nlu_training/pack_builder.py"),
    ("stage27c", "src/picwise_taxonomy/nlu_audit/auditor.py"),
)

_logger = logging.getLogger(__name__)

_artifact_status: dict[str, Any] = {
    "state": "not_loaded",
    "source": None,
    "reason": None,
    "artifact_path": None,
    "source_fingerprint": None,
    "artifact_fingerprint": None,
}

_hydrated_bundle: tuple[CanonicalVocabularyRegistry, SearchIndex] | None = None
_load_attempted = False


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_artifact_path() -> Path:
    return Path(__file__).resolve().parent / "artifacts" / _ARTIFACT_FILENAME


def get_fingerprint_source_paths() -> tuple[str, ...]:
    paths: list[str] = [
        "src/picwise_nlu/vocabulary_source.py",
        *[f"src/picwise_taxonomy/deep_packs/{name}" for name in _DEEP_PACK_FILES],
        "src/picwise_search_memory/canonical_vocabulary_coverage.py",
        "src/picwise_search_memory/taxonomy_search_memory_bridge.py",
        *[relative_path for _stage, relative_path in _TAXONOMY_BRIDGE_STAGE_FILES],
        "src/picwise_search_memory/canonical_registry.py",
        "src/picwise_search_memory/validation.py",
        "src/picwise_taxonomy/mega_category_registry.py",
        "src/picwise_search_memory/index_builder.py",
        "src/picwise_search_memory/lookup_safety.py",
        "src/picwise_nlu/query_variant_generator.py",
    ]
    return tuple(sorted(set(paths)))


def compute_source_fingerprint(*, repo_root: Path | None = None) -> str:
    root = repo_root or _repo_root()
    parts: list[str] = []
    for relative_path in get_fingerprint_source_paths():
        path = root / relative_path
        if path.exists():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            parts.append(f"{relative_path}:{digest}")
        else:
            parts.append(f"{relative_path}:missing")
    parts.extend(
        [
            f"registry_schema_version:{_REGISTRY_SCHEMA_VERSION}",
            f"index_schema_version:{_INDEX_SCHEMA_VERSION}",
            f"generator_version:{STAGE3_GENERATOR_VERSION}",
        ]
    )
    payload = "\n".join(parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _artifact_counts(registry: CanonicalVocabularyRegistry, index: SearchIndex) -> dict[str, int]:
    report = index.report
    return {
        "registry_records": len(registry.records),
        "registry_categories": len(registry.report.counts_by_mega_category),
        "index_entries": len(index.entries),
        "generated_variants": int(report.total_generated_variants),
        "exact_canonical_entries": int(report.counts_by_variant_type.get("exact_canonical", 0)),
    }


def build_search_runtime_artifact_envelope(
    registry: CanonicalVocabularyRegistry,
    index: SearchIndex,
    *,
    repo_root: Path | None = None,
    built_at: str | None = None,
) -> dict[str, Any]:
    counts = _artifact_counts(registry, index)
    return {
        "artifact_schema_version": _ARTIFACT_SCHEMA_VERSION,
        "builder_version": _BUILDER_VERSION,
        "source_fingerprint": compute_source_fingerprint(repo_root=repo_root),
        "built_at": built_at or datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "registry_schema_version": registry.schema_version,
        "index_schema_version": index.schema_version,
        "generator_version": STAGE3_GENERATOR_VERSION,
        "registry": registry.to_dict(),
        "search_index": index.to_dict(),
    }


def write_search_runtime_artifact(
    envelope: dict[str, Any],
    *,
    artifact_path: Path | None = None,
) -> Path:
    target = artifact_path or default_artifact_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(envelope, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    target.write_bytes(gzip.compress(payload))
    return target


def read_search_runtime_artifact_bytes(*, artifact_path: Path | None = None) -> bytes:
    target = artifact_path or default_artifact_path()
    return target.read_bytes()


def parse_search_runtime_artifact_bytes(raw: bytes) -> dict[str, Any]:
    try:
        decompressed = gzip.decompress(raw)
    except OSError as error:
        raise ValueError("artifact_gzip_decompress_failed") from error
    try:
        payload = json.loads(decompressed.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("artifact_json_parse_failed") from error
    if not isinstance(payload, dict):
        raise ValueError("artifact_envelope_not_object")
    return payload


def _validate_envelope_counts(envelope: dict[str, Any], registry: CanonicalVocabularyRegistry, index: SearchIndex) -> None:
    counts = envelope.get("counts")
    if not isinstance(counts, dict):
        raise ValueError("artifact_counts_missing")
    expected = _artifact_counts(registry, index)
    for key, expected_value in expected.items():
        actual_value = counts.get(key)
        if actual_value != expected_value:
            raise ValueError(f"artifact_count_mismatch:{key}")


def _validate_envelope_metadata(envelope: dict[str, Any]) -> None:
    if envelope.get("artifact_schema_version") != _ARTIFACT_SCHEMA_VERSION:
        raise ValueError("artifact_schema_version_mismatch")
    if envelope.get("registry_schema_version") != _REGISTRY_SCHEMA_VERSION:
        raise ValueError("registry_schema_version_mismatch")
    if envelope.get("index_schema_version") != _INDEX_SCHEMA_VERSION:
        raise ValueError("index_schema_version_mismatch")
    if envelope.get("generator_version") != STAGE3_GENERATOR_VERSION:
        raise ValueError("generator_version_mismatch")
    expected_fingerprint = compute_source_fingerprint()
    artifact_fingerprint = str(envelope.get("source_fingerprint") or "")
    if not artifact_fingerprint:
        raise ValueError("source_fingerprint_missing")
    if artifact_fingerprint != expected_fingerprint:
        raise ValueError("source_fingerprint_mismatch")


def hydrate_search_runtime_artifact(envelope: dict[str, Any]) -> tuple[CanonicalVocabularyRegistry, SearchIndex]:
    _validate_envelope_metadata(envelope)
    registry_payload = envelope.get("registry")
    index_payload = envelope.get("search_index")
    if not isinstance(registry_payload, dict):
        raise ValueError("registry_payload_missing")
    if not isinstance(index_payload, dict):
        raise ValueError("search_index_payload_missing")
    registry = CanonicalVocabularyRegistry.from_dict(registry_payload)
    index = SearchIndex.from_dict(index_payload)
    _validate_envelope_counts(envelope, registry, index)
    validation_result = validate_registry(registry)
    if not validation_result["valid"]:
        reasons = ", ".join(validation_result["reasons"])  # type: ignore[arg-type]
        raise ValueError(f"registry_validation_failed:{reasons}")
    if not index.entries:
        raise ValueError("search_index_empty")
    return registry, index


def _set_artifact_status(*, state: str, reason: str | None, artifact_path: Path | None = None, envelope: dict[str, Any] | None = None) -> None:
    _artifact_status["state"] = state
    _artifact_status["source"] = "artifact" if state == "loaded" else "live_builder"
    _artifact_status["reason"] = reason
    _artifact_status["artifact_path"] = str(artifact_path) if artifact_path else None
    _artifact_status["source_fingerprint"] = compute_source_fingerprint()
    _artifact_status["artifact_fingerprint"] = (
        str(envelope.get("source_fingerprint")) if envelope is not None else None
    )


def get_search_runtime_artifact_status() -> dict[str, Any]:
    return dict(_artifact_status)


def populate_runtime_caches(registry: CanonicalVocabularyRegistry, index: SearchIndex) -> None:
    import picwise_search.index_resolver_adapter as index_adapter
    import picwise_search_memory.canonical_registry as canonical_registry

    canonical_registry._CACHED_REGISTRY = registry
    index_adapter._CACHED_OFFLINE_INDEX = index


def try_hydrate_runtime_from_artifact(*, artifact_path: Path | None = None) -> tuple[CanonicalVocabularyRegistry, SearchIndex] | None:
    global _hydrated_bundle, _load_attempted

    if _hydrated_bundle is not None:
        return _hydrated_bundle
    if _load_attempted:
        return None

    _load_attempted = True
    target = artifact_path or default_artifact_path()
    if not target.exists():
        _set_artifact_status(state="fallback", reason="artifact_missing", artifact_path=target)
        _logger.info("Search runtime artifact missing at %s; falling back to live builder", target)
        return None

    try:
        envelope = parse_search_runtime_artifact_bytes(raw=target.read_bytes())
        registry, index = hydrate_search_runtime_artifact(envelope)
    except (OSError, ValueError) as error:
        reason = str(error)
        _set_artifact_status(state="fallback", reason=reason, artifact_path=target)
        _logger.warning("Search runtime artifact rejected (%s); falling back to live builder", reason)
        return None

    _hydrated_bundle = (registry, index)
    populate_runtime_caches(registry, index)
    _set_artifact_status(state="loaded", reason=None, artifact_path=target, envelope=envelope)
    _logger.info("Search runtime artifact loaded from %s", target)
    return _hydrated_bundle


def _reset_search_runtime_artifact_for_tests() -> None:
    global _hydrated_bundle, _load_attempted
    _hydrated_bundle = None
    _load_attempted = False
    _artifact_status.update(
        {
            "state": "not_loaded",
            "source": None,
            "reason": None,
            "artifact_path": None,
            "source_fingerprint": None,
            "artifact_fingerprint": None,
        }
    )
