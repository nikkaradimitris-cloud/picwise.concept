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
    SuggestionCandidate,
)
from picwise_search_graph.suggestions import (  # noqa: E402
    QueryAssistSuggestion,
    build_query_assist_suggestions,
)

_TEST_SOURCE = "test_fixture_stage1dc_query_assist"
_TEST_FLAGS = ("test_fixture", "graph_derived", "query_assist_fixture")


def _query_assist_fixture_envelope() -> SearchEntityGraphEnvelope:
    """Fixture-only graph with nike/apple/bosch entities for Stage 1D-C tests."""
    mega_footwear = MegaCategoryEntity(
        entity_id="mc_footwear_fixture",
        mega_category_id="footwear_shoes_sneakers_boots",
        display_name="Footwear",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    mega_tools = MegaCategoryEntity(
        entity_id="mc_tools_fixture",
        mega_category_id="tools_diy_hardware",
        display_name="Tools",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    mega_computers = MegaCategoryEntity(
        entity_id="mc_computers_fixture",
        mega_category_id="computers_office_peripherals",
        display_name="Computers",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    sub_running = SubcategoryEntity(
        entity_id="sub_running_fixture",
        mega_category_id="footwear_shoes_sneakers_boots",
        subcategory_id="running_footwear_fixture",
        display_name="Running Footwear",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    sub_power_tools = SubcategoryEntity(
        entity_id="sub_power_tools_fixture",
        mega_category_id="tools_diy_hardware",
        subcategory_id="power_tools_fixture",
        display_name="Power Tools",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    sub_tablets = SubcategoryEntity(
        entity_id="sub_tablets_fixture",
        mega_category_id="computers_office_peripherals",
        subcategory_id="tablets_fixture",
        display_name="Tablets",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )

    pf_running_shoes = ProductFamilyEntity(
        entity_id="pf_running_shoes_fixture",
        mega_category_id="footwear_shoes_sneakers_boots",
        subcategory_id="running_footwear_fixture",
        product_family_id="running_shoes_fixture",
        canonical_name="running shoes",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    pf_nike_running_shoes = ProductFamilyEntity(
        entity_id="pf_nike_running_shoes_fixture",
        mega_category_id="footwear_shoes_sneakers_boots",
        subcategory_id="running_footwear_fixture",
        product_family_id="nike_running_shoes_fixture",
        canonical_name="nike running shoes",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    pf_bosch_drill = ProductFamilyEntity(
        entity_id="pf_bosch_drill_fixture",
        mega_category_id="tools_diy_hardware",
        subcategory_id="power_tools_fixture",
        product_family_id="bosch_drill_fixture",
        canonical_name="bosch drill",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    pf_apple_tablet = ProductFamilyEntity(
        entity_id="pf_apple_tablet_fixture",
        mega_category_id="computers_office_peripherals",
        subcategory_id="tablets_fixture",
        product_family_id="apple_tablet_fixture",
        canonical_name="apple tablet",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    pf_apple_ipad = ProductFamilyEntity(
        entity_id="pf_apple_ipad_fixture",
        mega_category_id="computers_office_peripherals",
        subcategory_id="tablets_fixture",
        product_family_id="apple_ipad_fixture",
        canonical_name="apple ipad",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )

    brand_nike = BrandEntity(
        entity_id="brand_nike_fixture",
        normalized_brand_name="nike",
        display_name="Nike",
        aliases=(),
        standalone_behavior="suggestions_only",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    brand_bosch = BrandEntity(
        entity_id="brand_bosch_fixture",
        normalized_brand_name="bosch",
        display_name="Bosch",
        aliases=(),
        standalone_behavior="suggestions_only",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    brand_apple = BrandEntity(
        entity_id="brand_apple_fixture",
        normalized_brand_name="apple",
        display_name="Apple",
        aliases=(),
        standalone_behavior="suggestions_only",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )

    alias_apple_tablet = QueryAlias(
        entity_id="qa_apple_tablet_fixture",
        normalized_alias="apple tablet",
        target_entity_id="pf_apple_tablet_fixture",
        target_entity_type="ProductFamilyEntity",
        alias_type="brand_modifier",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    alias_apple_ipad = QueryAlias(
        entity_id="qa_apple_ipad_fixture",
        normalized_alias="apple ipad",
        target_entity_id="pf_apple_ipad_fixture",
        target_entity_type="ProductFamilyEntity",
        alias_type="brand_modifier",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    alias_nike_only = QueryAlias(
        entity_id="qa_nike_only_fixture",
        normalized_alias="nike",
        target_entity_id="brand_nike_fixture",
        target_entity_type="BrandEntity",
        alias_type="brand_modifier",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )

    suggestion_running_shoes = SuggestionCandidate(
        entity_id="sugg_running_shoes_fixture",
        suggestion_text="running shoes",
        target_entity_ids=("pf_running_shoes_fixture",),
        suggestion_type="product_family",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    suggestion_nike_running_shoes = SuggestionCandidate(
        entity_id="sugg_nike_running_shoes_fixture",
        suggestion_text="nike running shoes",
        target_entity_ids=("brand_nike_fixture", "pf_nike_running_shoes_fixture"),
        suggestion_type="brand_product",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )
    suggestion_bosch_drill = SuggestionCandidate(
        entity_id="sugg_bosch_drill_fixture",
        suggestion_text="bosch drill",
        target_entity_ids=("brand_bosch_fixture", "pf_bosch_drill_fixture"),
        suggestion_type="brand_product",
        source=_TEST_SOURCE,
        quality_flags=_TEST_FLAGS,
    )

    entities = SearchEntityGraphEntities(
        mega_categories=(mega_footwear, mega_tools, mega_computers),
        subcategories=(sub_running, sub_power_tools, sub_tablets),
        product_families=(
            pf_running_shoes,
            pf_nike_running_shoes,
            pf_bosch_drill,
            pf_apple_tablet,
            pf_apple_ipad,
        ),
        brands=(brand_nike, brand_bosch, brand_apple),
        query_aliases=(alias_apple_tablet, alias_apple_ipad, alias_nike_only),
        suggestions=(suggestion_running_shoes, suggestion_nike_running_shoes, suggestion_bosch_drill),
    )
    edges = (
        EntityEdge(
            edge_id="edge_nike_appears_nike_running_fixture",
            from_entity_id="brand_nike_fixture",
            to_entity_id="pf_nike_running_shoes_fixture",
            edge_type="appears_in",
            source=_TEST_SOURCE,
            quality_flags=_TEST_FLAGS,
        ),
        EntityEdge(
            edge_id="edge_bosch_appears_bosch_drill_fixture",
            from_entity_id="brand_bosch_fixture",
            to_entity_id="pf_bosch_drill_fixture",
            edge_type="appears_in",
            source=_TEST_SOURCE,
            quality_flags=_TEST_FLAGS,
        ),
        EntityEdge(
            edge_id="edge_apple_appears_apple_tablet_fixture",
            from_entity_id="brand_apple_fixture",
            to_entity_id="pf_apple_tablet_fixture",
            edge_type="appears_in",
            source=_TEST_SOURCE,
            quality_flags=_TEST_FLAGS,
        ),
        EntityEdge(
            edge_id="edge_apple_tablet_maps_brand_fixture",
            from_entity_id="qa_apple_tablet_fixture",
            to_entity_id="brand_apple_fixture",
            edge_type="maps_to_brand",
            source=_TEST_SOURCE,
            quality_flags=_TEST_FLAGS,
        ),
        EntityEdge(
            edge_id="edge_apple_ipad_maps_brand_fixture",
            from_entity_id="qa_apple_ipad_fixture",
            to_entity_id="brand_apple_fixture",
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
        export_notes=("fixture_only", "query_assist_stage1dc"),
    )


def _empty_brand_graph_envelope() -> SearchEntityGraphEnvelope:
    return SearchEntityGraphEnvelope(
        graph_schema_version="1.0.0",
        source="test_fixture_stage1dc_empty",
        entities=SearchEntityGraphEntities(),
        edges=(),
        export_notes=("fixture_only", "no_brands"),
    )


def _suggestion_texts(suggestions: tuple[QueryAssistSuggestion, ...]) -> list[str]:
    return [row.suggestion_text for row in suggestions]


class PicWiseSearchGraphQueryAssistStage1DCTests(unittest.TestCase):
    def setUp(self) -> None:
        self.envelope = _query_assist_fixture_envelope()

    def test_product_family_partial_run_sho_returns_running_shoes(self) -> None:
        suggestions = build_query_assist_suggestions(self.envelope, "run sho")
        self.assertIn("running shoes", _suggestion_texts(suggestions))
        running = next(row for row in suggestions if row.suggestion_text == "running shoes")
        self.assertEqual(running.suggestion_type, "product_family")

    def test_brand_prefix_nik_returns_nike_running_shoes(self) -> None:
        suggestions = build_query_assist_suggestions(self.envelope, "nik")
        self.assertIn("nike running shoes", _suggestion_texts(suggestions))

    def test_brand_prefix_nike_returns_nike_running_shoes(self) -> None:
        suggestions = build_query_assist_suggestions(self.envelope, "nike")
        self.assertIn("nike running shoes", _suggestion_texts(suggestions))

    def test_brand_product_partial_bosch_dr_returns_bosch_drill(self) -> None:
        suggestions = build_query_assist_suggestions(self.envelope, "bosch dr")
        self.assertIn("bosch drill", _suggestion_texts(suggestions))

    def test_brand_product_partial_appel_tab_returns_apple_tablet_or_ipad(self) -> None:
        suggestions = build_query_assist_suggestions(self.envelope, "appel tab")
        texts = set(_suggestion_texts(suggestions))
        self.assertTrue(texts.intersection({"apple tablet", "apple ipad"}))

    def test_brand_only_suggestions_do_not_include_product_card_fields(self) -> None:
        suggestions = build_query_assist_suggestions(self.envelope, "nik")
        for suggestion in suggestions:
            payload = suggestion.to_dict()
            forbidden = {
                "provider_key",
                "price",
                "price_text",
                "url",
                "product_url",
                "popularity",
                "popularity_score",
                "show_product_card",
                "ui_eligible",
            }
            self.assertTrue(forbidden.isdisjoint(set(payload.keys())))
            self.assertFalse(_is_brand_only_suggestion(suggestion))

    def test_no_nike_suggestions_without_graph_entities(self) -> None:
        suggestions = build_query_assist_suggestions(_empty_brand_graph_envelope(), "nik")
        self.assertEqual(suggestions, ())

    def test_duplicate_candidate_phrases_returned_once(self) -> None:
        suggestions = build_query_assist_suggestions(self.envelope, "nike run")
        texts = _suggestion_texts(suggestions)
        self.assertEqual(len(texts), len(set(texts)))

    def test_highest_score_first_and_max_suggestions_respected(self) -> None:
        suggestions = build_query_assist_suggestions(self.envelope, "a", max_suggestions=2)
        self.assertLessEqual(len(suggestions), 2)
        scores = [row.score for row in suggestions]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_deterministic_ordering_for_equal_scores(self) -> None:
        first = build_query_assist_suggestions(self.envelope, "apple")
        second = build_query_assist_suggestions(self.envelope, "apple")
        self.assertEqual(first, second)

    def test_query_assist_suggestion_is_json_serializable(self) -> None:
        suggestions = build_query_assist_suggestions(self.envelope, "run sho", max_suggestions=1)
        self.assertEqual(len(suggestions), 1)
        payload = suggestions[0].to_dict()
        restored = QueryAssistSuggestion.from_dict(payload)
        self.assertEqual(restored, suggestions[0])


def _is_brand_only_suggestion(suggestion: QueryAssistSuggestion) -> bool:
    tokens = suggestion.suggestion_text.split()
    return len(tokens) < 2


if __name__ == "__main__":
    unittest.main()
