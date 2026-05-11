from __future__ import annotations

from .contracts import (
    GapReason,
    MappingConfidence,
    MappingStatus,
    MappingTarget,
    TaxonomyMappingResult,
)
from .validation import (
    MappingCatalog,
    build_mapping_catalog,
    normalize_path_segments,
    normalize_text,
    split_normalized_tokens,
    validate_mapping_input,
    validate_mapping_target,
)


def _confidence_for_score(score: int, exact_hit: bool, alias_hit: bool) -> MappingConfidence:
    if exact_hit:
        return MappingConfidence.EXACT
    if alias_hit:
        return MappingConfidence.STRONG_ALIAS
    if score >= 4:
        return MappingConfidence.PATH_MATCH
    if score > 0:
        return MappingConfidence.WEAK
    return MappingConfidence.NONE


def _best_scored_candidate(scores: dict[str, int]) -> tuple[str | None, bool]:
    if not scores:
        return None, False
    ordered = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
    top_score = ordered[0][1]
    if top_score <= 0:
        return None, False
    top = [candidate for candidate, score in ordered if score == top_score]
    return ordered[0][0], len(top) > 1


def _score_mega_candidates(
    *,
    catalog: MappingCatalog,
    normalized_label: str,
    normalized_parent: str,
    normalized_path_segments: list[str],
    proposed_mega_id: str,
) -> tuple[dict[str, int], dict[str, bool], dict[str, bool]]:
    mega_scores: dict[str, int] = {}
    exact_hits: dict[str, bool] = {}
    alias_hits: dict[str, bool] = {}
    segments = [normalized_label, normalized_parent] + normalized_path_segments
    segment_tokens = [split_normalized_tokens(segment) for segment in segments if segment]
    for mega_id, seeds in catalog.mega_seeds.items():
        score = 0
        exact_hit = False
        alias_hit = False
        if proposed_mega_id and proposed_mega_id == mega_id:
            score += 8
            exact_hit = True
        if normalized_label and normalized_label in seeds.product_family_labels:
            score += 8
            exact_hit = True
        elif normalized_label and normalized_label in seeds.subcategory_labels:
            score += 7
            exact_hit = True
        elif normalized_label and normalized_label in seeds.department_labels:
            score += 6
            exact_hit = True
        if normalized_parent and normalized_parent in seeds.subcategory_labels:
            score += 5
        elif normalized_parent and normalized_parent in seeds.department_labels:
            score += 4
        if normalized_label and normalized_label in seeds.mega_alias_labels:
            score += 6
            alias_hit = True
        for segment in normalized_path_segments:
            if segment in seeds.mega_alias_labels:
                score += 3
                alias_hit = True
            elif segment in seeds.department_labels:
                score += 3
            elif segment in seeds.subcategory_labels:
                score += 4
            elif segment in seeds.product_family_labels:
                score += 5
        mega_tokens = split_normalized_tokens(" ".join(seeds.mega_alias_labels))
        for tokens in segment_tokens:
            overlap = len(tokens.intersection(mega_tokens))
            score += min(overlap, 2)
        mega_scores[mega_id] = score
        exact_hits[mega_id] = exact_hit
        alias_hits[mega_id] = alias_hit
    return mega_scores, exact_hits, alias_hits


def _build_result(
    *,
    source_item_id: str,
    status: MappingStatus,
    confidence: MappingConfidence,
    normalized_label: str,
    normalized_path: str,
    gap_reason: GapReason | None = None,
    operator_action_hint: str = "",
    target: MappingTarget | None = None,
    suggested_engine_id: str = "",
    suggested_mega_category_id: str = "",
) -> TaxonomyMappingResult:
    return TaxonomyMappingResult(
        source_item_id=source_item_id,
        status=status,
        confidence=confidence,
        target=target,
        normalized_label=normalized_label,
        normalized_path=normalized_path,
        gap_reason=gap_reason,
        operator_action_hint=operator_action_hint,
        suggested_engine_id=suggested_engine_id,
        suggested_mega_category_id=suggested_mega_category_id,
    )


def map_source_item_to_taxonomy(source_item: dict, catalog: MappingCatalog | None = None) -> TaxonomyMappingResult:
    active_catalog = catalog or build_mapping_catalog()
    input_validation = validate_mapping_input(source_item)
    normalized_item = input_validation["normalized_item"]
    source_item_id = normalized_item.get("source_item_id", "")
    normalized_label = normalize_text(normalized_item.get("raw_label", ""))
    normalized_parent = normalize_text(normalized_item.get("raw_parent_label", ""))
    normalized_path_segments = normalize_path_segments(normalized_item.get("raw_path", ""))
    normalized_path = " > ".join(normalized_path_segments)

    if not input_validation["inventory_validation"]["valid"]:
        return _build_result(
            source_item_id=source_item_id,
            status=MappingStatus.INVALID_SOURCE,
            confidence=MappingConfidence.NONE,
            normalized_label=normalized_label,
            normalized_path=normalized_path,
            gap_reason=GapReason.FORBIDDEN_INVENTORY_FIELD,
            operator_action_hint="Remove product/price/offer/seller/similar commercial fields from source item.",
        )
    if not input_validation["source_validation"]["valid"]:
        return _build_result(
            source_item_id=source_item_id,
            status=MappingStatus.INVALID_SOURCE,
            confidence=MappingConfidence.NONE,
            normalized_label=normalized_label,
            normalized_path=normalized_path,
            gap_reason=GapReason.INVALID_SOURCE_ITEM,
            operator_action_hint="Fix source item required fields and allowed source_type values before remapping.",
        )

    proposed_mega_id = normalized_item.get("proposed_mega_category_id", "")
    mega_scores, exact_hits, alias_hits = _score_mega_candidates(
        catalog=active_catalog,
        normalized_label=normalized_label,
        normalized_parent=normalized_parent,
        normalized_path_segments=normalized_path_segments,
        proposed_mega_id=proposed_mega_id,
    )
    selected_mega_id, mega_ambiguous = _best_scored_candidate(mega_scores)
    if mega_ambiguous:
        return _build_result(
            source_item_id=source_item_id,
            status=MappingStatus.NEEDS_REVIEW,
            confidence=MappingConfidence.WEAK,
            normalized_label=normalized_label,
            normalized_path=normalized_path,
            gap_reason=GapReason.AMBIGUOUS_MEGA_CATEGORY,
            operator_action_hint="Resolve mega-category ambiguity manually and confirm path intent.",
        )
    if not selected_mega_id:
        return _build_result(
            source_item_id=source_item_id,
            status=MappingStatus.UNMAPPED,
            confidence=MappingConfidence.NONE,
            normalized_label=normalized_label,
            normalized_path=normalized_path,
            gap_reason=GapReason.NO_MEGA_CATEGORY_MATCH,
            operator_action_hint="Add coverage/deep-pack seeds or map this source item manually.",
        )

    selected_engine_id = active_catalog.mega_to_engine.get(selected_mega_id, "")
    if not selected_engine_id:
        return _build_result(
            source_item_id=source_item_id,
            status=MappingStatus.UNMAPPED,
            confidence=MappingConfidence.NONE,
            normalized_label=normalized_label,
            normalized_path=normalized_path,
            gap_reason=GapReason.NO_ENGINE_MATCH,
            operator_action_hint="Register the engine/mega relation before remapping.",
            suggested_mega_category_id=selected_mega_id,
        )

    confidence = _confidence_for_score(
        mega_scores.get(selected_mega_id, 0),
        exact_hits.get(selected_mega_id, False),
        alias_hits.get(selected_mega_id, False),
    )
    if confidence in {MappingConfidence.WEAK, MappingConfidence.NONE}:
        return _build_result(
            source_item_id=source_item_id,
            status=MappingStatus.NEEDS_REVIEW if confidence == MappingConfidence.WEAK else MappingStatus.UNMAPPED,
            confidence=confidence,
            normalized_label=normalized_label,
            normalized_path=normalized_path,
            gap_reason=GapReason.WEAK_MATCH_NEEDS_REVIEW
            if confidence == MappingConfidence.WEAK
            else GapReason.NO_MEGA_CATEGORY_MATCH,
            operator_action_hint="Improve source naming/path specificity or expand alias coverage before mapping.",
            suggested_engine_id=selected_engine_id,
            suggested_mega_category_id=selected_mega_id,
        )

    seeds = active_catalog.mega_seeds[selected_mega_id]
    department = normalized_label if normalized_label in seeds.department_labels else ""
    subcategory = normalized_label if normalized_label in seeds.subcategory_labels else ""
    product_family = normalized_label if normalized_label in seeds.product_family_labels else ""
    if not product_family and normalized_parent in seeds.product_family_labels:
        product_family = normalized_parent
    if not subcategory and normalized_parent in seeds.subcategory_labels:
        subcategory = normalized_parent
    if not department and normalized_parent in seeds.department_labels:
        department = normalized_parent

    target = MappingTarget(
        engine_id=selected_engine_id,
        mega_category_id=selected_mega_id,
        department=department,
        subcategory=subcategory,
        product_family=product_family,
    )
    target_validation = validate_mapping_target(target, active_catalog)
    if not target_validation["valid"]:
        gap_reason = GapReason.UNKNOWN_DEPARTMENT
        if not target_validation["subcategory_ok"]:
            gap_reason = GapReason.UNKNOWN_SUBCATEGORY
        if not target_validation["product_family_ok"]:
            gap_reason = GapReason.UNKNOWN_PRODUCT_FAMILY
        return _build_result(
            source_item_id=source_item_id,
            status=MappingStatus.NEEDS_REVIEW,
            confidence=confidence,
            normalized_label=normalized_label,
            normalized_path=normalized_path,
            gap_reason=gap_reason,
            operator_action_hint="Validate target hierarchy against curated seeds before approval.",
            suggested_engine_id=selected_engine_id,
            suggested_mega_category_id=selected_mega_id,
            target=target,
        )

    proposed_engine = normalized_item.get("proposed_engine_id", "")
    if proposed_engine and proposed_engine != selected_engine_id:
        return _build_result(
            source_item_id=source_item_id,
            status=MappingStatus.NEEDS_REVIEW,
            confidence=confidence,
            normalized_label=normalized_label,
            normalized_path=normalized_path,
            gap_reason=GapReason.AMBIGUOUS_ENGINE,
            operator_action_hint="Proposed engine conflicts with inferred mega-category engine; review manually.",
            suggested_engine_id=selected_engine_id,
            suggested_mega_category_id=selected_mega_id,
            target=target,
        )

    return _build_result(
        source_item_id=source_item_id,
        status=MappingStatus.MAPPED,
        confidence=confidence,
        target=target,
        normalized_label=normalized_label,
        normalized_path=normalized_path,
        suggested_engine_id=selected_engine_id,
        suggested_mega_category_id=selected_mega_id,
    )
