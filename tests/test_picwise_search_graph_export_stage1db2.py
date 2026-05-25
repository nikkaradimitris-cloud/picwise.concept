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
    ProductOfferEntity,
    QueryAlias,
    SearchEntityGraphEnvelope,
    SearchEntityGraphEntities,
    SubcategoryEntity,
    SuggestionCandidate,
)
from picwise_search_graph.export import export_graph_search_memory_terms  # noqa: E402

_TEST_SOURCE = "test_fixture_stage1db2"
_TEST_FLAGS = ("test_fixture", "graph_derived")


def _fixture_envelope() -> SearchEntityGraphEnvelope:
    mega = MegaCategoryEntity(
        entity_id="mc_footwear_fixture",
        mega_category_id="footwear_shoes_sneakers_boots",
        display_name="Footwear Fixture",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    subcategory = SubcategoryEntity(
        entity_id="sub_running_fixture",
        mega_category_id="footwear_shoes_sneakers_boots",
        subcategory_id="running_footwear_fixture",
        display_name="Running Footwear",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    product_family = ProductFamilyEntity(
        entity_id="pf_samplebrand_running_shoes_fixture",
        mega_category_id="footwear_shoes_sneakers_boots",
        subcategory_id="running_footwear_fixture",
        product_family_id="samplebrand_running_shoes_fixture",
        canonical_name="samplebrand running shoes",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    brand = BrandEntity(
        entity_id="brand_samplebrand_fixture",
        normalized_brand_name="samplebrand",
        display_name="SampleBrand",
        aliases=("sample brand",),
        standalone_behavior="suggestions_only",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    query_alias = QueryAlias(
        entity_id="qa_runing_shose_fixture",
        normalized_alias="runing shose",
        target_entity_id="pf_samplebrand_running_shoes_fixture",
        target_entity_type="ProductFamilyEntity",
        alias_type="typo_seed",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    brand_only_alias = QueryAlias(
        entity_id="qa_samplebrand_only_fixture",
        normalized_alias="samplebrand",
        target_entity_id="brand_samplebrand_fixture",
        target_entity_type="BrandEntity",
        alias_type="brand_modifier",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    brand_product_alias = QueryAlias(
        entity_id="qa_samplebrand_tablet_fixture",
        normalized_alias="samplebrand tablet",
        target_entity_id="pf_samplebrand_running_shoes_fixture",
        target_entity_type="ProductFamilyEntity",
        alias_type="brand_modifier",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    offer = ProductOfferEntity(
        entity_id="offer_samplebrand_fixture",
        provider_key="fixture_provider",
        provider_product_id="fixture-sku-001",
        title="samplebrand running shoes offer title",
        brand_entity_id="brand_samplebrand_fixture",
        product_family_id="samplebrand_running_shoes_fixture",
        subcategory_id="running_footwear_fixture",
        mega_category_id="footwear_shoes_sneakers_boots",
        url="",
        image_url="",
        price_text="",
        availability_text="",
        source=_TEST_SOURCE,
        eligibility_status="imported",
        quality_flags=_TEST_FLAGS,
    )
    suggestion = SuggestionCandidate(
        entity_id="sugg_samplebrand_fixture",
        suggestion_text="samplebrand running shoes",
        target_entity_ids=("pf_samplebrand_running_shoes_fixture",),
        suggestion_type="brand_product",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    entities = SearchEntityGraphEntities(
        mega_categories=(mega,),
        subcategories=(subcategory,),
        product_families=(product_family,),
        brands=(brand,),
        product_offers=(offer,),
        query_aliases=(query_alias, brand_only_alias, brand_product_alias),
        suggestions=(suggestion,),
    )
    edges = (
        EntityEdge(
            edge_id="edge_pf_belongs_sub_fixture",
            from_entity_id="pf_samplebrand_running_shoes_fixture",
            to_entity_id="sub_running_fixture",
            edge_type="belongs_to",
            source=_TEST_SOURCE,
            quality_flags=_TEST_FLAGS,
        ),
        EntityEdge(
            edge_id="edge_alias_maps_pf_fixture",
            from_entity_id="qa_runing_shose_fixture",
            to_entity_id="pf_samplebrand_running_shoes_fixture",
            edge_type="maps_to_product_family",
            source=_TEST_SOURCE,
            quality_flags=_TEST_FLAGS,
        ),
        EntityEdge(
            edge_id="edge_brand_product_maps_brand_fixture",
            from_entity_id="qa_samplebrand_tablet_fixture",
            to_entity_id="brand_samplebrand_fixture",
            edge_type="maps_to_brand",
            source=_TEST_SOURCE,
            quality_flags=_TEST_FLAGS,
        ),
    )
    return SearchEntityGraphEnvelope(
        graph_schema_version="1.0.0",
        source=_TEST_SOURCE,
        entities=entities,
        edges=edges,
        export_notes=("fixture_only",),
    )


class PicWiseSearchGraphExportStage1DB2Tests(unittest.TestCase):
    def test_product_family_exports_canonical_search_memory_term(self) -> None:
        terms = export_graph_search_memory_terms(_fixture_envelope())
        canonical = [term for term in terms if term.projection_type == "product_family_canonical"]
        self.assertEqual(len(canonical), 1)
        self.assertEqual(canonical[0].canonical_term, "samplebrand running shoes")
        self.assertEqual(canonical[0].source, "search_entity_graph")

    def test_query_alias_to_product_family_exports_query_alias(self) -> None:
        terms = export_graph_search_memory_terms(_fixture_envelope())
        aliases = [term for term in terms if term.projection_type == "query_alias"]
        self.assertEqual(len(aliases), 1)
        self.assertEqual(aliases[0].canonical_term, "runing shose")
        self.assertEqual(aliases[0].product_family, "samplebrand running shoes")

    def test_brand_only_alias_to_brand_entity_is_not_exported(self) -> None:
        terms = export_graph_search_memory_terms(_fixture_envelope())
        exported_terms = {term.canonical_term for term in terms}
        self.assertNotIn("samplebrand", exported_terms)

    def test_brand_product_alias_exports_only_with_product_family_mapping(self) -> None:
        terms = export_graph_search_memory_terms(_fixture_envelope())
        brand_product = [term for term in terms if term.projection_type == "brand_product_alias"]
        self.assertEqual(len(brand_product), 1)
        self.assertEqual(brand_product[0].canonical_term, "samplebrand tablet")
        self.assertEqual(brand_product[0].brand_entity_id, "brand_samplebrand_fixture")

    def test_product_offer_entity_is_not_exported_as_canonical_term(self) -> None:
        terms = export_graph_search_memory_terms(_fixture_envelope())
        exported_terms = {term.canonical_term for term in terms}
        self.assertNotIn("samplebrand running shoes offer title", exported_terms)

    def test_suggestion_candidate_is_not_exported_as_canonical_term(self) -> None:
        terms = export_graph_search_memory_terms(_fixture_envelope())
        self.assertFalse(any(term.graph_entity_type == "SuggestionCandidate" for term in terms))

    def test_output_is_deduped_and_stable_ordered(self) -> None:
        envelope = _fixture_envelope()
        first = export_graph_search_memory_terms(envelope)
        second = export_graph_search_memory_terms(envelope)
        self.assertEqual(first, second)
        signatures = [(term.mega_category_id, term.canonical_term, term.projection_type) for term in first]
        self.assertEqual(len(signatures), len(set(signatures)))


if __name__ == "__main__":
    unittest.main()
