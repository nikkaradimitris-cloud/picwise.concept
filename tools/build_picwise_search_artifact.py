from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_search_memory.canonical_registry import build_canonical_vocabulary_registry  # noqa: E402
from picwise_search_memory.index_builder import build_offline_search_index  # noqa: E402
from picwise_search_memory.search_runtime_artifact import (  # noqa: E402
    build_search_runtime_artifact_envelope,
    default_artifact_path,
    write_search_runtime_artifact,
)


def main() -> None:
    registry = build_canonical_vocabulary_registry()
    index = build_offline_search_index(registry=registry)
    envelope = build_search_runtime_artifact_envelope(registry, index, repo_root=ROOT)
    artifact_path = write_search_runtime_artifact(envelope)
    counts = envelope["counts"]
    size_bytes = artifact_path.stat().st_size
    print(f"Wrote search runtime artifact: {artifact_path}")
    print(f"Artifact size bytes: {size_bytes}")
    print(f"registry_records: {counts['registry_records']}")
    print(f"registry_categories: {counts['registry_categories']}")
    print(f"index_entries: {counts['index_entries']}")
    print(f"generated_variants: {counts['generated_variants']}")
    print(f"exact_canonical_entries: {counts['exact_canonical_entries']}")
    print(f"source_fingerprint: {envelope['source_fingerprint']}")


if __name__ == "__main__":
    main()
