from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_search_graph.contracts import (  # noqa: E402
    BrandEntity,
    EntityEdge,
    MegaCategoryEntity,
    ProductFamilyEntity,
    QueryAlias,
    SearchEntityGraphEnvelope,
    SearchEntityGraphEntities,
    SubcategoryEntity,
)
from picwise_search_graph.export import export_graph_search_memory_terms  # noqa: E402
from picwise_search_memory.canonical_registry import build_canonical_vocabulary_registry  # noqa: E402
from picwise_search_memory.index_builder import build_offline_search_index  # noqa: E402
from picwise_search_memory.index_lookup import lookup_offline_search_index  # noqa: E402
from picwise_search_memory.validation import known_mega_category_ids  # noqa: E402

_TEST_SOURCE = "test_fixture_stage1db2_registry"
_TEST_FLAGS = ("test_fixture", "graph_derived")


def _graph_only_fixture_term() -> SearchEntityGraphEnvelope:
    product_family = ProductFamilyEntity(
        entity_id="pf_samplebrand_drill_fixture",
        mega_category_id="power_tools_workshop",
        subcategory_id="cordless_tools_fixture",
        product_family_id="samplebrand_drill_fixture",
        canonical_name="samplebrand drill",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    query_alias = QueryAlias(
        entity_id="qa_samplebrand_drill_alias_fixture",
        normalized_alias="samplebrand cordless drill",
        target_entity_id="pf_samplebrand_drill_fixture",
        target_entity_type="ProductFamilyEntity",
        alias_type="synonym",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    return SearchEntityGraphEnvelope(
        graph_schema_version="1.0.0",
        source=_TEST_SOURCE,
        entities=SearchEntityGraphEntities(
            mega_categories=(
                MegaCategoryEntity(
                    entity_id="mc_power_tools_fixture",
                    mega_category_id="power_tools_workshop",
                    display_name="Power Tools",
                    source=_TEST_SOURCE,
                    quality_flags=_TEST_FLAGS,
                ),
            ),
            subcategories=(
                SubcategoryEntity(
                    entity_id="sub_cordless_fixture",
                    mega_category_id="power_tools_workshop",
                    subcategory_id="cordless_tools_fixture",
                    display_name="Cordless Tools",
                    source=_TEST_SOURCE,
                    quality_flags=_TEST_FLAGS,
                ),
            ),
            product_families=(product_family,),
            query_aliases=(query_alias,),
        ),
        edges=(
            EntityEdge(
                edge_id="edge_pf_belongs_sub_fixture",
                from_entity_id="pf_samplebrand_drill_fixture",
                to_entity_id="sub_cordless_fixture",
                edge_type="belongs_to",
                source=_TEST_SOURCE,
                quality_flags=_TEST_FLAGS,
            ),
            EntityEdge(
                edge_id="edge_alias_maps_pf_fixture",
                from_entity_id="qa_samplebrand_drill_alias_fixture",
                to_entity_id="pf_samplebrand_drill_fixture",
                edge_type="maps_to_product_family",
                source=_TEST_SOURCE,
                quality_flags=_TEST_FLAGS,
            ),
        ),
    )


class PicWiseSearchGraphRegistryIntegrationStage1DB2Tests(unittest.TestCase):
    def test_build_canonical_vocabulary_registry_includes_graph_source_layer(self) -> None:
        registry = build_canonical_vocabulary_registry()
        graph_records = [record for record in registry.records if record.source == "search_entity_graph"]
        self.assertGreater(len(graph_records), 0)
        self.assertTrue(all("graph_derived" in record.quality_flags for record in graph_records))

    def test_graph_derived_fixture_term_becomes_canonical_vocabulary_record(self) -> None:
        fixture_terms = export_graph_search_memory_terms(_graph_only_fixture_term())
        fixture_term = next(term for term in fixture_terms if term.projection_type == "product_family_canonical")
        registry = build_canonical_vocabulary_registry()
        matches = [
            record
            for record in registry.records
            if record.normalized_term == "ebike"
            and record.source == "search_entity_graph"
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].mega_category_id, "moto_bicycle_mobility_gear")
        self.assertEqual(fixture_term.canonical_term, "samplebrand drill")

    def test_graph_derived_aliases_are_preserved(self) -> None:
        registry = build_canonical_vocabulary_registry()
        graph_with_aliases = [
            record
            for record in registry.records
            if record.source == "search_entity_graph" and record.aliases
        ]
        self.assertGreater(len(graph_with_aliases), 0)

    def test_existing_registry_counts_for_all_18_megas_still_present(self) -> None:
        registry = build_canonical_vocabulary_registry()
        known = known_mega_category_ids()
        self.assertEqual(len(known), 18)
        for mega_category_id in sorted(known):
            self.assertGreater(registry.report.counts_by_mega_category.get(mega_category_id, 0), 0)

    def test_duplicate_graph_and_existing_terms_do_not_create_duplicate_records(self) -> None:
        registry = build_canonical_vocabulary_registry()
        signatures = [(record.mega_category_id, record.normalized_term) for record in registry.records]
        self.assertEqual(len(signatures), len(set(signatures)))

    def test_build_offline_search_index_includes_graph_derived_term(self) -> None:
        registry = build_canonical_vocabulary_registry()
        graph_records = [record for record in registry.records if record.source == "search_entity_graph"]
        self.assertGreater(len(graph_records), 0)
        index = build_offline_search_index(registry=registry)
        sample = graph_records[0]
        exact = [
            entry
            for entry in index.entries
            if entry.normalized_term == sample.normalized_term
            and entry.mega_category_id == sample.mega_category_id
            and entry.variant_type == "exact_canonical"
        ]
        self.assertEqual(len(exact), 1)

    def test_graph_derived_alias_becomes_source_alias_path(self) -> None:
        registry = build_canonical_vocabulary_registry()
        from picwise_search_memory.lookup_safety import derive_source_alias_variants

        graph_variants = [
            variant
            for variant in derive_source_alias_variants(registry)
            if variant.get("source") == "search_entity_graph"
        ]
        self.assertGreater(len(graph_variants), 0)
        sample = graph_variants[0]
        index = build_offline_search_index(registry=registry)
        alias_entries = [
            entry
            for entry in index.entries
            if entry.normalized_variant == sample["variant"]
            and entry.mega_category_id == sample["mega_category_id"]
            and entry.variant_type == "source_alias"
        ]
        self.assertGreaterEqual(len(alias_entries), 1)

    def test_lookup_offline_search_index_can_resolve_graph_derived_term(self) -> None:
        registry = build_canonical_vocabulary_registry()
        graph_term = next(record for record in registry.records if record.source == "search_entity_graph")
        index = build_offline_search_index(registry=registry)
        result = lookup_offline_search_index(graph_term.normalized_term, index)
        self.assertEqual(result.status, "match")
        self.assertIsNotNone(result.matched_entry)
        self.assertEqual(result.matched_entry.mega_category_id, graph_term.mega_category_id)


if __name__ == "__main__":
    unittest.main()
