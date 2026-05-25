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
from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402
from picwise_search_memory.canonical_registry import build_canonical_vocabulary_registry  # noqa: E402
from picwise_search_memory.search_runtime_artifact import (  # noqa: E402
    _reset_search_runtime_artifact_for_tests,
    default_artifact_path,
    get_fingerprint_source_paths,
    hydrate_search_runtime_artifact,
    parse_search_runtime_artifact_bytes,
    try_hydrate_runtime_from_artifact,
)

_TEST_SOURCE = "test_fixture_stage1db2_runtime"
_TEST_FLAGS = ("test_fixture", "graph_derived")


def _brand_product_fixture_envelope() -> SearchEntityGraphEnvelope:
    product_family = ProductFamilyEntity(
        entity_id="pf_samplebrand_tablet_fixture",
        mega_category_id="computers_office_peripherals",
        subcategory_id="tablets_fixture",
        product_family_id="samplebrand_tablet_fixture",
        canonical_name="samplebrand tablet",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    brand = BrandEntity(
        entity_id="brand_samplebrand_runtime_fixture",
        normalized_brand_name="samplebrand",
        display_name="SampleBrand",
        aliases=(),
        standalone_behavior="suggestions_only",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    brand_only = QueryAlias(
        entity_id="qa_samplebrand_only_runtime_fixture",
        normalized_alias="samplebrand",
        target_entity_id="brand_samplebrand_runtime_fixture",
        target_entity_type="BrandEntity",
        alias_type="brand_modifier",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    brand_product = QueryAlias(
        entity_id="qa_samplebrand_tablet_runtime_fixture",
        normalized_alias="samplebrand tablet",
        target_entity_id="pf_samplebrand_tablet_fixture",
        target_entity_type="ProductFamilyEntity",
        alias_type="brand_modifier",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    return SearchEntityGraphEnvelope(
        graph_schema_version="1.0.0",
        source=_TEST_SOURCE,
        entities=SearchEntityGraphEntities(
            mega_categories=(
                MegaCategoryEntity(
                    entity_id="mc_computers_fixture",
                    mega_category_id="computers_office_peripherals",
                    display_name="Computers",
                    source=_TEST_SOURCE,
                    quality_flags=_TEST_FLAGS,
                ),
            ),
            subcategories=(
                SubcategoryEntity(
                    entity_id="sub_tablets_fixture",
                    mega_category_id="computers_office_peripherals",
                    subcategory_id="tablets_fixture",
                    display_name="Tablets",
                    source=_TEST_SOURCE,
                    quality_flags=_TEST_FLAGS,
                ),
            ),
            product_families=(product_family,),
            brands=(brand,),
            query_aliases=(brand_only, brand_product),
        ),
        edges=(
            EntityEdge(
                edge_id="edge_brand_product_maps_brand_runtime_fixture",
                from_entity_id="qa_samplebrand_tablet_runtime_fixture",
                to_entity_id="brand_samplebrand_runtime_fixture",
                edge_type="maps_to_brand",
                source=_TEST_SOURCE,
                quality_flags=_TEST_FLAGS,
            ),
        ),
    )


class PicWiseSearchGraphRuntimeRecognitionStage1DB2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._artifact_path = default_artifact_path()
        if not cls._artifact_path.exists():
            raise unittest.SkipTest("search runtime artifact missing; rebuild required")

    def setUp(self) -> None:
        _reset_search_runtime_artifact_for_tests()
        import picwise_search.index_resolver_adapter as index_adapter
        import picwise_search_memory.canonical_registry as canonical_registry

        canonical_registry._CACHED_REGISTRY = None
        index_adapter._CACHED_OFFLINE_INDEX = None
        bundle = try_hydrate_runtime_from_artifact()
        self.assertIsNotNone(bundle)

    def test_artifact_fingerprint_includes_graph_source_files(self) -> None:
        paths = set(get_fingerprint_source_paths())
        expected = {
            "src/picwise_search_graph/contracts.py",
            "src/picwise_search_graph/validation.py",
            "src/picwise_search_graph/manifest.py",
            "src/picwise_search_graph/export.py",
            "src/picwise_search_graph/taxonomy_source.py",
            "src/picwise_search_graph/__init__.py",
        }
        self.assertTrue(expected.issubset(paths))

    def test_artifact_loads_from_artifact_path_without_live_builder_fallback(self) -> None:
        envelope = parse_search_runtime_artifact_bytes(raw=self._artifact_path.read_bytes())
        registry, index = hydrate_search_runtime_artifact(envelope)
        self.assertGreater(len(registry.records), 0)
        self.assertGreater(len(index.entries), 0)
        graph_records = [record for record in registry.records if record.source == "search_entity_graph"]
        self.assertGreater(len(graph_records), 0)

    def test_graph_known_product_family_term_is_not_not_understood(self) -> None:
        resolution = resolve_live_search("running shoes")
        self.assertNotEqual(resolution.resolver_state, "not_understood")
        self.assertEqual(resolution.mega_category_id, "footwear_shoes_sneakers_boots")
        self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")

    def test_graph_derived_unique_alias_is_understood_provider_not_connected(self) -> None:
        resolution = resolve_live_search("ebike")
        self.assertNotEqual(resolution.resolver_state, "not_understood")
        self.assertEqual(resolution.mega_category_id, "moto_bicycle_mobility_gear")
        self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")
        self.assertFalse(resolution.result_allowed)

    def test_power_bank_still_returns_connected_provider_results(self) -> None:
        resolution = resolve_live_search("power bank")
        self.assertEqual(resolution.resolver_state, "connected_provider_results")
        self.assertTrue(resolution.result_allowed)

    def test_brand_only_fixture_does_not_produce_connected_provider_results(self) -> None:
        resolution = resolve_live_search("samplebrand")
        self.assertNotEqual(resolution.resolver_state, "connected_provider_results")
        self.assertFalse(resolution.result_allowed)
        self.assertEqual(resolution.resolver_state, "not_understood")

    def test_brand_product_fixture_can_be_recognized_only_through_product_family_mapping(self) -> None:
        exported = export_graph_search_memory_terms(_brand_product_fixture_envelope())
        brand_product = next(term for term in exported if term.projection_type == "brand_product_alias")
        self.assertEqual(brand_product.canonical_term, "samplebrand tablet")
        self.assertEqual(brand_product.product_family, "samplebrand tablet")

        brand_only_exports = [
            term
            for term in exported
            if term.canonical_term == "samplebrand" and term.projection_type != "brand_product_alias"
        ]
        self.assertEqual(brand_only_exports, [])

        registry = build_canonical_vocabulary_registry()
        self.assertFalse(any(record.normalized_term == "samplebrand" for record in registry.records))
        self.assertFalse(
            any(
                record.normalized_term == "samplebrand tablet"
                for record in registry.records
                if record.source == "search_entity_graph"
            )
        )


if __name__ == "__main__":
    unittest.main()
