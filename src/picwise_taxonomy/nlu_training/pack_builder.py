from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict

from picwise_taxonomy.mega_category_registry import get_mega_category_registry
from picwise_taxonomy.nlu_export import (
    TaxonomyNLUExportRecord,
    TaxonomyNLUExportStatus,
    build_taxonomy_nlu_export,
)

from .contracts import (
    MegaCategoryTrainingPack,
    NLUTrainingExample,
    NLUTrainingPackBuildInput,
    NLUTrainingPackBuildResult,
    NLUTrainingPackStatus,
    QueryVariantType,
)
from .validation import validate_training_pack_result

_NORMALIZE_PATTERN = re.compile(r"[^a-z0-9\u0370-\u03ff]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_GREEK_CHAR_PATTERN = re.compile(r"[\u0370-\u03ff]")
_LATIN_CHAR_PATTERN = re.compile(r"[a-z]")
_RECORD_STATUS_TO_SAFETY = {
    TaxonomyNLUExportStatus.ACTIVE: "safe_training_example",
    TaxonomyNLUExportStatus.REVIEW_ONLY: "review_only",
    TaxonomyNLUExportStatus.DISABLED_GAP: "disabled_gap",
}


def _normalize_query(value: str) -> str:
    lowered = _WHITESPACE_PATTERN.sub(" ", str(value or "").strip().lower())
    return _NORMALIZE_PATTERN.sub("_", lowered).strip("_")


def _stable_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    cleaned = {
        str(raw_value).strip()
        for raw_value in values
        if isinstance(raw_value, str) and str(raw_value).strip()
    }
    return tuple(sorted(cleaned, key=lambda item: item.lower()))


def _language_script_marker(text: str, variant_type: QueryVariantType) -> str:
    has_greek = bool(_GREEK_CHAR_PATTERN.search(text))
    has_latin = bool(_LATIN_CHAR_PATTERN.search(text.lower()))
    if variant_type == QueryVariantType.TYPO_VARIANT:
        return "typo"
    if variant_type == QueryVariantType.GREEK_ALIAS:
        return "greek"
    if variant_type == QueryVariantType.GREEKLISH_ALIAS:
        return "greeklish"
    if has_greek and has_latin:
        return "mixed"
    if has_greek:
        return "greek"
    if has_latin:
        return "english"
    return "mixed"


def _example_id(
    *,
    mega_category_id: str,
    variant_type: QueryVariantType,
    normalized_query: str,
    intent_label: str,
) -> str:
    digest_input = "::".join((mega_category_id, variant_type.value, normalized_query, intent_label))
    return hashlib.sha1(digest_input.encode("utf-8")).hexdigest()[:20]


def _make_example(
    *,
    query_text: str,
    variant_type: QueryVariantType,
    intent_label: str,
    record: TaxonomyNLUExportRecord,
) -> NLUTrainingExample | None:
    normalized_query = _normalize_query(query_text)
    if not normalized_query:
        return None
    refs = tuple(sorted(set((record.export_id, *record.source_stage_refs)), key=lambda item: item.lower()))
    return NLUTrainingExample(
        example_id=_example_id(
            mega_category_id=record.mega_category_id,
            variant_type=variant_type,
            normalized_query=normalized_query,
            intent_label=intent_label,
        ),
        query_text=query_text.strip(),
        normalized_query=normalized_query,
        expected_engine_id=record.engine_id,
        expected_mega_category_id=record.mega_category_id,
        expected_department=record.department,
        expected_subcategory=record.subcategory,
        expected_product_family=record.product_family,
        language_script=_language_script_marker(query_text, variant_type),
        intent_label=intent_label,
        variant_type=variant_type,
        source_taxonomy_refs=refs,
        safety_status=_RECORD_STATUS_TO_SAFETY[record.status],
    )


def _alias_examples(record: TaxonomyNLUExportRecord) -> tuple[NLUTrainingExample, ...]:
    examples = [
        _make_example(
            query_text=alias,
            variant_type=QueryVariantType.ALIAS,
            intent_label="catalog_lookup",
            record=record,
        )
        for alias in _stable_unique(record.aliases)
    ]
    return tuple(example for example in examples if example is not None)


def _greek_alias_examples(record: TaxonomyNLUExportRecord) -> tuple[NLUTrainingExample, ...]:
    examples = [
        _make_example(
            query_text=alias,
            variant_type=QueryVariantType.GREEK_ALIAS,
            intent_label="catalog_lookup",
            record=record,
        )
        for alias in _stable_unique(record.greek_aliases)
    ]
    return tuple(example for example in examples if example is not None)


def _greeklish_alias_examples(record: TaxonomyNLUExportRecord) -> tuple[NLUTrainingExample, ...]:
    examples = [
        _make_example(
            query_text=alias,
            variant_type=QueryVariantType.GREEKLISH_ALIAS,
            intent_label="catalog_lookup",
            record=record,
        )
        for alias in _stable_unique(record.greeklish_aliases)
    ]
    return tuple(example for example in examples if example is not None)


def _typo_examples(record: TaxonomyNLUExportRecord) -> tuple[NLUTrainingExample, ...]:
    examples = [
        _make_example(
            query_text=alias,
            variant_type=QueryVariantType.TYPO_VARIANT,
            intent_label="catalog_lookup",
            record=record,
        )
        for alias in _stable_unique(record.typo_variants)
    ]
    return tuple(example for example in examples if example is not None)


def _spec_intent_examples(record: TaxonomyNLUExportRecord) -> tuple[NLUTrainingExample, ...]:
    aliases = _stable_unique(record.aliases)[:5]
    spec_fields = _stable_unique(record.spec_fields)
    intent_patterns = _stable_unique(record.intent_patterns)
    built: list[NLUTrainingExample] = []
    for intent in intent_patterns:
        for spec in spec_fields:
            for alias in aliases:
                query = f"{intent} {alias} with {spec}"
                maybe_example = _make_example(
                    query_text=query,
                    variant_type=QueryVariantType.SPEC_INTENT,
                    intent_label="spec_lookup",
                    record=record,
                )
                if maybe_example is not None:
                    built.append(maybe_example)
    return tuple(built)


def _priority_examples(record: TaxonomyNLUExportRecord) -> tuple[NLUTrainingExample, ...]:
    aliases = _stable_unique(record.aliases)[:5]
    priorities = _stable_unique(record.priority_terms)
    built: list[NLUTrainingExample] = []
    for priority in priorities:
        for alias in aliases:
            query = f"{priority} {alias}"
            maybe_example = _make_example(
                query_text=query,
                variant_type=QueryVariantType.PRIORITY_TERM,
                intent_label="priority_lookup",
                record=record,
            )
            if maybe_example is not None:
                built.append(maybe_example)
    return tuple(built)


def _mixed_intent_examples(record: TaxonomyNLUExportRecord) -> tuple[NLUTrainingExample, ...]:
    aliases = _stable_unique(record.aliases)[:4]
    intents = _stable_unique(record.intent_patterns)[:8]
    priorities = _stable_unique(record.priority_terms)[:8]
    specs = _stable_unique(record.spec_fields)[:8]
    built: list[NLUTrainingExample] = []
    for alias in aliases:
        for intent in intents:
            for priority in priorities:
                for spec in specs:
                    query = f"{intent} {alias} prioritize {priority} and {spec}"
                    maybe_example = _make_example(
                        query_text=query,
                        variant_type=QueryVariantType.MIXED_INTENT,
                        intent_label="mixed_intent_lookup",
                        record=record,
                    )
                    if maybe_example is not None:
                        built.append(maybe_example)
    return tuple(built)


def _generate_record_examples(record: TaxonomyNLUExportRecord) -> tuple[NLUTrainingExample, ...]:
    variant_buckets = (
        _alias_examples(record),
        _greek_alias_examples(record),
        _greeklish_alias_examples(record),
        _typo_examples(record),
        _spec_intent_examples(record),
        _priority_examples(record),
        _mixed_intent_examples(record),
    )
    combined = [example for bucket in variant_buckets for example in bucket]
    return tuple(
        sorted(
            combined,
            key=lambda item: (item.variant_type.value, item.language_script, item.normalized_query, item.example_id),
        )
    )


def _pack_status(
    *,
    total_examples: int,
    safe_examples: int,
    has_review_or_disabled: bool,
    min_examples_for_ready: int,
) -> NLUTrainingPackStatus:
    if safe_examples >= min_examples_for_ready and not has_review_or_disabled:
        return NLUTrainingPackStatus.READY
    if safe_examples >= min_examples_for_ready and has_review_or_disabled:
        return NLUTrainingPackStatus.NEEDS_REVIEW
    if safe_examples > 0:
        return NLUTrainingPackStatus.PARTIAL
    if total_examples > 0:
        return NLUTrainingPackStatus.NEEDS_REVIEW
    return NLUTrainingPackStatus.INSUFFICIENT_DATA


def _pack_id(mega_category_id: str) -> str:
    return f"stage27b__{mega_category_id}"


def _select_examples(
    examples: tuple[NLUTrainingExample, ...],
    *,
    max_examples_per_pack: int,
) -> tuple[NLUTrainingExample, ...]:
    ordered = sorted(
        examples,
        key=lambda item: (item.variant_type.value, item.language_script, item.normalized_query, item.example_id),
    )
    unique: dict[str, NLUTrainingExample] = {}
    for example in ordered:
        unique_key = f"{example.variant_type.value}:{example.normalized_query}:{example.safety_status}"
        unique.setdefault(unique_key, example)
    unique_values = list(unique.values())
    seeded: list[NLUTrainingExample] = []
    for variant_type in QueryVariantType:
        first_match = next(
            (example for example in unique_values if example.variant_type == variant_type),
            None,
        )
        if first_match is not None:
            seeded.append(first_match)
    selected_ids = {example.example_id for example in seeded}
    remaining = [example for example in unique_values if example.example_id not in selected_ids]
    selected = (seeded + remaining)[:max_examples_per_pack]
    return tuple(selected)


def _empty_pack(engine_id: str, mega_category_id: str) -> MegaCategoryTrainingPack:
    return MegaCategoryTrainingPack(
        pack_id=_pack_id(mega_category_id),
        engine_id=engine_id,
        mega_category_id=mega_category_id,
        status=NLUTrainingPackStatus.INSUFFICIENT_DATA,
        examples=(),
        source_record_ids=(),
        signal_counts={},
        warnings=("needs_more_taxonomy_input", "no_stage27a_export_records"),
    )


def build_nlu_training_packs(
    build_input: NLUTrainingPackBuildInput | None = None,
) -> NLUTrainingPackBuildResult:
    if build_input is None:
        active_input = NLUTrainingPackBuildInput(export_records=build_taxonomy_nlu_export().records)
    else:
        active_input = build_input
    export_records = active_input.export_records
    records_by_mega: dict[str, list[TaxonomyNLUExportRecord]] = defaultdict(list)
    for record in export_records:
        records_by_mega[record.mega_category_id].append(record)

    packs: list[MegaCategoryTrainingPack] = []
    mega_registry = sorted(get_mega_category_registry(), key=lambda item: str(item.get("mega_category_id", "")).strip())
    for mega in mega_registry:
        mega_category_id = str(mega.get("mega_category_id", "")).strip()
        engine_id = str(mega.get("engine_id", "")).strip()
        mega_records = sorted(
            records_by_mega.get(mega_category_id, []),
            key=lambda item: (item.status.value, item.export_id),
        )
        if not mega_records:
            packs.append(_empty_pack(engine_id, mega_category_id))
            continue

        all_examples = tuple(example for record in mega_records for example in _generate_record_examples(record))
        selected_examples = _select_examples(all_examples, max_examples_per_pack=active_input.max_examples_per_pack)
        safe_examples = sum(1 for example in selected_examples if example.safety_status == "safe_training_example")
        has_review_or_disabled = any(
            example.safety_status in {"review_only", "disabled_gap"} for example in selected_examples
        )
        status = _pack_status(
            total_examples=len(selected_examples),
            safe_examples=safe_examples,
            has_review_or_disabled=has_review_or_disabled,
            min_examples_for_ready=active_input.min_examples_for_ready,
        )
        warnings: list[str] = []
        if len(selected_examples) < active_input.min_examples_for_ready:
            warnings.append("needs_more_taxonomy_input")
        if has_review_or_disabled:
            warnings.append("contains_non_active_export_sources")
        variant_counts = Counter(example.variant_type.value for example in selected_examples)
        for required_variant in QueryVariantType:
            if variant_counts.get(required_variant.value, 0) == 0:
                warnings.append(f"missing_variant_type:{required_variant.value}")
        signal_counts = {
            "records": len(mega_records),
            "aliases": sum(len(record.aliases) for record in mega_records),
            "greek_aliases": sum(len(record.greek_aliases) for record in mega_records),
            "greeklish_aliases": sum(len(record.greeklish_aliases) for record in mega_records),
            "typo_variants": sum(len(record.typo_variants) for record in mega_records),
            "spec_fields": sum(len(record.spec_fields) for record in mega_records),
            "intent_patterns": sum(len(record.intent_patterns) for record in mega_records),
            "priority_terms": sum(len(record.priority_terms) for record in mega_records),
        }
        packs.append(
            MegaCategoryTrainingPack(
                pack_id=_pack_id(mega_category_id),
                engine_id=engine_id,
                mega_category_id=mega_category_id,
                status=status,
                examples=selected_examples,
                source_record_ids=tuple(record.export_id for record in mega_records),
                signal_counts=signal_counts,
                warnings=tuple(sorted(set(warnings))),
            )
        )

    ordered_packs = tuple(sorted(packs, key=lambda item: (item.engine_id, item.mega_category_id)))
    status_counts = Counter(pack.status.value for pack in ordered_packs)
    all_examples = [example for pack in ordered_packs for example in pack.examples]
    validation = validate_training_pack_result(
        NLUTrainingPackBuildResult(
            packs=ordered_packs,
            total_packs=len(ordered_packs),
            ready_packs=status_counts.get(NLUTrainingPackStatus.READY.value, 0),
            partial_packs=status_counts.get(NLUTrainingPackStatus.PARTIAL.value, 0),
            insufficient_data_packs=status_counts.get(NLUTrainingPackStatus.INSUFFICIENT_DATA.value, 0),
            needs_review_packs=status_counts.get(NLUTrainingPackStatus.NEEDS_REVIEW.value, 0),
            total_examples=len(all_examples),
            examples_by_mega_category=dict(
                sorted((pack.mega_category_id, len(pack.examples)) for pack in ordered_packs)
            ),
            examples_by_engine=dict(
                sorted(
                    Counter(example.expected_engine_id for example in all_examples).items(),
                    key=lambda item: item[0],
                )
            ),
            examples_by_variant_type=dict(
                sorted(
                    Counter(example.variant_type.value for example in all_examples).items(),
                    key=lambda item: item[0],
                )
            ),
            examples_by_language_script=dict(
                sorted(
                    Counter(example.language_script for example in all_examples).items(),
                    key=lambda item: item[0],
                )
            ),
            valid=True,
            warnings=(),
            stage_title=active_input.stage_title,
        )
    )
    warnings = [warning for pack in ordered_packs for warning in pack.warnings]
    warnings.extend(validation["reasons"])
    return NLUTrainingPackBuildResult(
        packs=ordered_packs,
        total_packs=len(ordered_packs),
        ready_packs=status_counts.get(NLUTrainingPackStatus.READY.value, 0),
        partial_packs=status_counts.get(NLUTrainingPackStatus.PARTIAL.value, 0),
        insufficient_data_packs=status_counts.get(NLUTrainingPackStatus.INSUFFICIENT_DATA.value, 0),
        needs_review_packs=status_counts.get(NLUTrainingPackStatus.NEEDS_REVIEW.value, 0),
        total_examples=len(all_examples),
        examples_by_mega_category=dict(sorted((pack.mega_category_id, len(pack.examples)) for pack in ordered_packs)),
        examples_by_engine=dict(sorted(Counter(example.expected_engine_id for example in all_examples).items())),
        examples_by_variant_type=dict(sorted(Counter(example.variant_type.value for example in all_examples).items())),
        examples_by_language_script=dict(sorted(Counter(example.language_script for example in all_examples).items())),
        valid=validation["valid"],
        warnings=tuple(sorted(set(warnings))),
        stage_title=active_input.stage_title,
    )
