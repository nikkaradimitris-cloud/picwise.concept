from __future__ import annotations

import json
import subprocess
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
from picwise_search_graph.manifest import validate_search_entity_graph_manifest  # noqa: E402
from picwise_search_graph.validation import (  # noqa: E402
    product_offer_implies_ui_eligibility,
    validate_brand_entity,
    validate_entity_edge,
    validate_product_offer_entity,
    validate_query_alias,
    validate_search_entity_graph_envelope,
    validate_suggestion_candidate,
)

_ALLOWED_STAGE_FILES = {
    "docs/picwise_search_entity_graph_stage1db1.md",
    "src/picwise_search_graph/__init__.py",
    "src/picwise_search_graph/contracts.py",
    "src/picwise_search_graph/manifest.py",
    "src/picwise_search_graph/validation.py",
    "tests/test_picwise_search_graph_contracts_stage1db1.py",
}

_TEST_SOURCE = "test_fixture_stage1db1"
_TEST_FLAGS = ("test_fixture",)


def _fixture_entities() -> SearchEntityGraphEntities:
    mega = MegaCategoryEntity(
        entity_id="mc_sports_outdoor_fixture",
        mega_category_id="sports_outdoor_fixture",
        display_name="Sports Outdoor Fixture",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    subcategory = SubcategoryEntity(
        entity_id="sub_running_footwear_fixture",
        mega_category_id="sports_outdoor_fixture",
        subcategory_id="running_footwear_fixture",
        display_name="Running Footwear Fixture",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    product_family = ProductFamilyEntity(
        entity_id="pf_running_shoes_fixture",
        mega_category_id="sports_outdoor_fixture",
        subcategory_id="running_footwear_fixture",
        product_family_id="running_shoes_fixture",
        canonical_name="running shoes",
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
    return SearchEntityGraphEntities(
        mega_categories=(mega,),
        subcategories=(subcategory,),
        product_families=(product_family,),
        brands=(brand,),
    )


class PicWiseSearchGraphContractsStage1DB1Tests(unittest.TestCase):
    def test_valid_product_world_graph_entities_are_accepted(self) -> None:
        entities = _fixture_entities()
        envelope = SearchEntityGraphEnvelope(
            graph_schema_version="1.0.0",
            source=_TEST_SOURCE,
            entities=entities,
            edges=(),
            export_notes=("fixture_only",),
        )
        result = validate_search_entity_graph_envelope(envelope)
        self.assertTrue(result["valid"])
        self.assertEqual(result["reasons"], ())

    def test_brand_entity_with_product_cards_is_rejected(self) -> None:
        brand = BrandEntity(
            entity_id="brand_bad_fixture",
            normalized_brand_name="samplebrand",
            display_name="SampleBrand",
            aliases=(),
            standalone_behavior="product_cards",
            source=_TEST_SOURCE,
            quality_flags=_TEST_FLAGS,
        )
        reasons = validate_brand_entity(brand)
        self.assertIn("brand:standalone_behavior_product_cards_forbidden", reasons)

    def test_brand_entity_with_suggestions_only_is_accepted(self) -> None:
        brand = BrandEntity(
            entity_id="brand_safe_fixture",
            normalized_brand_name="samplebrand",
            display_name="SampleBrand",
            aliases=(),
            standalone_behavior="suggestions_only",
            source=_TEST_SOURCE,
            quality_flags=_TEST_FLAGS,
        )
        reasons = validate_brand_entity(brand)
        self.assertEqual(reasons, [])

    def test_product_offer_entity_does_not_imply_ui_eligibility(self) -> None:
        offer = ProductOfferEntity(
            entity_id="offer_fixture_eligible",
            provider_key="fixture_provider",
            provider_product_id="fixture-sku-001",
            title="samplebrand running shoes",
            brand_entity_id="brand_samplebrand_fixture",
            product_family_id="running_shoes_fixture",
            subcategory_id="running_footwear_fixture",
            mega_category_id="sports_outdoor_fixture",
            url="",
            image_url="",
            price_text="",
            availability_text="",
            source=_TEST_SOURCE,
            eligibility_status="eligible",
            quality_flags=_TEST_FLAGS,
        )
        reasons = validate_product_offer_entity(offer)
        self.assertEqual(reasons, [])
        self.assertFalse(product_offer_implies_ui_eligibility(offer))
        payload = offer.to_dict()
        self.assertNotIn("ui_eligible", payload)
        self.assertNotIn("show_product_card", payload)
        self.assertEqual(payload["eligibility_status"], "eligible")

    def test_query_alias_maps_noisy_phrase_to_product_family(self) -> None:
        alias = QueryAlias(
            entity_id="qa_running_shoe_typo_fixture",
            normalized_alias="runing shose",
            target_entity_id="pf_running_shoes_fixture",
            target_entity_type="ProductFamilyEntity",
            alias_type="typo_seed",
            source=_TEST_SOURCE,
            quality_flags=_TEST_FLAGS,
        )
        reasons = validate_query_alias(alias)
        self.assertEqual(reasons, [])
        self.assertEqual(alias.target_entity_type, "ProductFamilyEntity")

    def test_suggestion_candidate_brand_product_rejects_brand_only_text(self) -> None:
        bad = SuggestionCandidate(
            entity_id="sugg_brand_only_fixture",
            suggestion_text="samplebrand",
            target_entity_ids=("brand_samplebrand_fixture",),
            suggestion_type="brand_product",
            source=_TEST_SOURCE,
            quality_flags=_TEST_FLAGS,
        )
        good = SuggestionCandidate(
            entity_id="sugg_brand_product_fixture",
            suggestion_text="samplebrand running shoes",
            target_entity_ids=("pf_running_shoes_fixture",),
            suggestion_type="brand_product",
            source=_TEST_SOURCE,
            quality_flags=_TEST_FLAGS,
        )
        self.assertIn(
            "suggestion:brand_product_must_not_be_brand_only",
            validate_suggestion_candidate(bad),
        )
        self.assertEqual(validate_suggestion_candidate(good), [])

    def test_entity_edge_supports_required_relationships(self) -> None:
        edges = (
            EntityEdge(
                edge_id="edge_pf_belongs_sub_fixture",
                from_entity_id="pf_running_shoes_fixture",
                to_entity_id="sub_running_footwear_fixture",
                edge_type="belongs_to",
                source=_TEST_SOURCE,
                quality_flags=_TEST_FLAGS,
            ),
            EntityEdge(
                edge_id="edge_brand_appears_pf_fixture",
                from_entity_id="brand_samplebrand_fixture",
                to_entity_id="pf_running_shoes_fixture",
                edge_type="appears_in",
                source=_TEST_SOURCE,
                quality_flags=_TEST_FLAGS,
            ),
            EntityEdge(
                edge_id="edge_offer_has_brand_fixture",
                from_entity_id="offer_fixture_eligible",
                to_entity_id="brand_samplebrand_fixture",
                edge_type="has_brand",
                source=_TEST_SOURCE,
                quality_flags=_TEST_FLAGS,
            ),
            EntityEdge(
                edge_id="edge_alias_maps_pf_fixture",
                from_entity_id="qa_running_shoe_typo_fixture",
                to_entity_id="pf_running_shoes_fixture",
                edge_type="maps_to_product_family",
                source=_TEST_SOURCE,
                quality_flags=_TEST_FLAGS,
            ),
        )
        for edge in edges:
            self.assertEqual(validate_entity_edge(edge), [])

    def test_envelope_rejects_duplicate_entity_ids(self) -> None:
        duplicate_brand = BrandEntity(
            entity_id="brand_samplebrand_fixture",
            normalized_brand_name="samplebrand",
            display_name="SampleBrand",
            aliases=(),
            standalone_behavior="suggestions_only",
            source=_TEST_SOURCE,
            quality_flags=_TEST_FLAGS,
        )
        entities = SearchEntityGraphEntities(
            brands=(duplicate_brand, duplicate_brand),
        )
        envelope = SearchEntityGraphEnvelope(
            graph_schema_version="1.0.0",
            source=_TEST_SOURCE,
            entities=entities,
            edges=(),
        )
        result = validate_search_entity_graph_envelope(envelope)
        self.assertFalse(result["valid"])
        self.assertTrue(any("duplicate_entity_id" in reason for reason in result["reasons"]))

    def test_envelope_rejects_duplicate_edge_ids(self) -> None:
        edge = EntityEdge(
            edge_id="edge_duplicate_fixture",
            from_entity_id="pf_running_shoes_fixture",
            to_entity_id="sub_running_footwear_fixture",
            edge_type="belongs_to",
            source=_TEST_SOURCE,
            quality_flags=_TEST_FLAGS,
        )
        envelope = SearchEntityGraphEnvelope(
            graph_schema_version="1.0.0",
            source=_TEST_SOURCE,
            entities=SearchEntityGraphEntities(),
            edges=(edge, edge),
        )
        result = validate_search_entity_graph_envelope(envelope)
        self.assertFalse(result["valid"])
        self.assertIn("envelope:duplicate_edge_id:edge_duplicate_fixture", result["reasons"])

    def test_manifest_is_valid_and_json_serializable(self) -> None:
        result = validate_search_entity_graph_manifest()
        self.assertTrue(result["valid"])
        self.assertTrue(result["does_not_show_product_cards"])
        self.assertTrue(result["does_not_replace_resolver"])

    def test_contracts_are_json_serializable(self) -> None:
        envelope = SearchEntityGraphEnvelope(
            graph_schema_version="1.0.0",
            source=_TEST_SOURCE,
            entities=_fixture_entities(),
            edges=(),
        )
        json.dumps(envelope.to_dict(), sort_keys=True)

    def test_no_runtime_integration_files_changed(self) -> None:
        diff = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        changed = {line.strip().replace("\\", "/") for line in diff.stdout.splitlines() if line.strip()}
        unexpected = changed - _ALLOWED_STAGE_FILES
        self.assertEqual(
            unexpected,
            set(),
            msg=f"Unexpected changed files outside Stage 1D-B1 allowlist: {sorted(unexpected)}",
        )


if __name__ == "__main__":
    unittest.main()
