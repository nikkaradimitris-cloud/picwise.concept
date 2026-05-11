from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations

from .contracts import CanonicalSourceReference, CanonicalTaxonomyRecord

_NORMALIZE_NON_ALNUM = re.compile(r"[^0-9a-zA-Z\u0370-\u03FF]+")
_SPACE_NORMALIZER = re.compile(r"\s+")
_ABBREVIATION_PATTERNS = (
    (re.compile(r"\be[\s_-]?scooter\b"), "electric scooter"),
    (re.compile(r"\bev\b"), "electric vehicle"),
    (re.compile(r"\btv\b"), "television"),
)
_GENERIC_AMBIGUOUS_TERMS = {"accessories", "parts", "tools", "care", "system"}
_STAGE = "Stage 25C — Taxonomy Deduplication / Merge Rules"

_GREEK_TO_LATIN = {
    "α": "a",
    "β": "v",
    "γ": "g",
    "δ": "d",
    "ε": "e",
    "ζ": "z",
    "η": "i",
    "θ": "th",
    "ι": "i",
    "κ": "k",
    "λ": "l",
    "μ": "m",
    "ν": "n",
    "ξ": "x",
    "ο": "o",
    "π": "p",
    "ρ": "r",
    "σ": "s",
    "ς": "s",
    "τ": "t",
    "υ": "y",
    "φ": "f",
    "χ": "ch",
    "ψ": "ps",
    "ω": "o",
}


class MergeStatus(str, Enum):
    MERGE_ALLOWED = "merge_allowed"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class MergeReason(str, Enum):
    EXACT_NORMALIZED_MATCH = "exact_normalized_match"
    ALIAS_MATCH = "alias_match"
    GREEK_GREEKLISH_MATCH = "greek_greeklish_match"
    TYPO_VARIANT_MATCH = "typo_variant_match"
    ABBREVIATION_MATCH = "abbreviation_match"
    AMBIGUOUS_MATCH = "ambiguous_match"
    INCOMPATIBLE_ENGINE = "incompatible_engine"
    INCOMPATIBLE_MEGA_CATEGORY = "incompatible_mega_category"
    WEAK_MATCH = "weak_match"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True)
class DeduplicationInput:
    records: tuple[CanonicalTaxonomyRecord, ...] = field(default_factory=tuple)
    coverage_context: tuple[object, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MergeDecision:
    status: MergeStatus
    reasons: tuple[MergeReason, ...]
    matched_terms: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MergeCandidate:
    candidate_id: str
    record_ids: tuple[str, str]
    engine_ids: tuple[str, str]
    mega_category_ids: tuple[str, str]
    decision: MergeDecision
    source_references: tuple[CanonicalSourceReference, ...] = field(default_factory=tuple)
    provenance: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DeduplicationResult:
    candidates: tuple[MergeCandidate, ...]
    total_candidates: int
    merge_allowed_count: int
    review_required_count: int
    blocked_count: int
    counts_by_engine: dict[str, int]
    counts_by_mega_category: dict[str, int]
    valid: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)
    stage: str = _STAGE
    dedup_rules_created: bool = True
    deep_packs_created: bool = False

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "candidates": [
                {
                    "candidate_id": candidate.candidate_id,
                    "record_ids": list(candidate.record_ids),
                    "engine_ids": list(candidate.engine_ids),
                    "mega_category_ids": list(candidate.mega_category_ids),
                    "decision": {
                        "status": candidate.decision.status.value,
                        "reasons": [reason.value for reason in candidate.decision.reasons],
                        "matched_terms": list(candidate.decision.matched_terms),
                    },
                    "source_references": [
                        {
                            "source_item_id": reference.source_item_id,
                            "source_name": reference.source_name,
                            "source_type": reference.source_type,
                            "mapping_status": reference.mapping_status,
                            "mapping_confidence": reference.mapping_confidence,
                            "mapping_gap_reason": reference.mapping_gap_reason,
                            "stage": reference.stage,
                        }
                        for reference in candidate.source_references
                    ],
                    "provenance": list(candidate.provenance),
                }
                for candidate in self.candidates
            ],
            "summary": {
                "total_candidates": self.total_candidates,
                "merge_allowed_count": self.merge_allowed_count,
                "review_required_count": self.review_required_count,
                "blocked_count": self.blocked_count,
                "counts_by_engine": dict(sorted(self.counts_by_engine.items())),
                "counts_by_mega_category": dict(sorted(self.counts_by_mega_category.items())),
                "valid": self.valid,
                "warnings": list(self.warnings),
            },
            "dedup_rules_created": self.dedup_rules_created,
            "deep_packs_created": self.deep_packs_created,
        }


def _strip_diacritics(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def _normalize_text(value: object) -> str:
    lowered = str(value or "").strip().lower()
    if not lowered:
        return ""
    lowered = _strip_diacritics(lowered)
    lowered = _NORMALIZE_NON_ALNUM.sub(" ", lowered)
    lowered = _SPACE_NORMALIZER.sub(" ", lowered).strip()
    return lowered


def _to_greeklish(normalized_text: str) -> str:
    return "".join(_GREEK_TO_LATIN.get(character, character) for character in normalized_text)


def _normalize_abbreviation(normalized_text: str) -> str:
    transformed = normalized_text
    for pattern, replacement in _ABBREVIATION_PATTERNS:
        transformed = pattern.sub(replacement, transformed)
    return _SPACE_NORMALIZER.sub(" ", transformed).strip()


def _collect_terms(record: CanonicalTaxonomyRecord) -> tuple[str, ...]:
    terms = {record.product_family}
    terms.update(record.aliases)
    normalized_terms = sorted({_normalize_text(term) for term in terms if _normalize_text(term)})
    return tuple(normalized_terms)


def _levenshtein_distance(value_a: str, value_b: str) -> int:
    if value_a == value_b:
        return 0
    if not value_a:
        return len(value_b)
    if not value_b:
        return len(value_a)

    previous = list(range(len(value_b) + 1))
    for index_a, char_a in enumerate(value_a, start=1):
        current = [index_a]
        for index_b, char_b in enumerate(value_b, start=1):
            insert_cost = current[index_b - 1] + 1
            delete_cost = previous[index_b] + 1
            replace_cost = previous[index_b - 1] + (0 if char_a == char_b else 1)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def _typo_matches(left_terms: tuple[str, ...], right_terms: tuple[str, ...]) -> tuple[str, ...]:
    matches: list[str] = []
    for left in left_terms:
        for right in right_terms:
            compact_left = left.replace(" ", "")
            compact_right = right.replace(" ", "")
            if len(compact_left) < 6 or len(compact_right) < 6:
                continue
            if abs(len(compact_left) - len(compact_right)) > 1:
                continue
            if compact_left[:1] != compact_right[:1]:
                continue
            if _levenshtein_distance(compact_left, compact_right) <= 1:
                matches.append(f"{left}~{right}")
    return tuple(sorted(set(matches)))


def _ambiguous_overlap(left_terms: tuple[str, ...], right_terms: tuple[str, ...]) -> tuple[str, ...]:
    overlaps = set(left_terms).intersection(right_terms)
    ambiguous = [
        term
        for term in overlaps
        if term in _GENERIC_AMBIGUOUS_TERMS or (len(term.split()) == 1 and len(term) <= 4)
    ]
    return tuple(sorted(set(ambiguous)))


def _stable_reason_order(reasons: set[MergeReason]) -> tuple[MergeReason, ...]:
    ordered = [
        MergeReason.EXACT_NORMALIZED_MATCH,
        MergeReason.ALIAS_MATCH,
        MergeReason.GREEK_GREEKLISH_MATCH,
        MergeReason.TYPO_VARIANT_MATCH,
        MergeReason.ABBREVIATION_MATCH,
        MergeReason.AMBIGUOUS_MATCH,
        MergeReason.INCOMPATIBLE_ENGINE,
        MergeReason.INCOMPATIBLE_MEGA_CATEGORY,
        MergeReason.WEAK_MATCH,
        MergeReason.INSUFFICIENT_EVIDENCE,
    ]
    return tuple(reason for reason in ordered if reason in reasons)


def _decision_for_pair(left: CanonicalTaxonomyRecord, right: CanonicalTaxonomyRecord) -> MergeDecision | None:
    left_terms = _collect_terms(left)
    right_terms = _collect_terms(right)
    if not left_terms or not right_terms:
        return None

    reasons: set[MergeReason] = set()
    matched_terms: set[str] = set()

    direct_overlap = set(left_terms).intersection(right_terms)
    if direct_overlap:
        reasons.add(MergeReason.EXACT_NORMALIZED_MATCH)
        matched_terms.update(direct_overlap)

    left_aliases = {term for term in _collect_terms(left) if term != _normalize_text(left.product_family)}
    right_aliases = {term for term in _collect_terms(right) if term != _normalize_text(right.product_family)}
    alias_overlap = (left_aliases & set(right_terms)) | (right_aliases & set(left_terms))
    if alias_overlap:
        reasons.add(MergeReason.ALIAS_MATCH)
        matched_terms.update(alias_overlap)

    left_greeklish = {_to_greeklish(term) for term in left_terms}
    right_greeklish = {_to_greeklish(term) for term in right_terms}
    greeklish_overlap = left_greeklish.intersection(right_greeklish)
    if greeklish_overlap and not direct_overlap:
        reasons.add(MergeReason.GREEK_GREEKLISH_MATCH)
        matched_terms.update(greeklish_overlap)

    abbreviation_overlap = {
        _normalize_abbreviation(term) for term in left_terms
    }.intersection({_normalize_abbreviation(term) for term in right_terms})
    if abbreviation_overlap and not direct_overlap:
        reasons.add(MergeReason.ABBREVIATION_MATCH)
        matched_terms.update(abbreviation_overlap)

    typo_overlap = _typo_matches(left_terms, right_terms)
    if typo_overlap and not direct_overlap:
        reasons.add(MergeReason.TYPO_VARIANT_MATCH)
        matched_terms.update(typo_overlap)

    ambiguous = _ambiguous_overlap(left_terms, right_terms)
    if ambiguous:
        reasons.add(MergeReason.AMBIGUOUS_MATCH)
        matched_terms.update(ambiguous)

    if not reasons:
        return None

    same_engine = left.engine_id == right.engine_id
    same_mega = left.mega_category_id == right.mega_category_id

    if not same_engine:
        reasons.add(MergeReason.INCOMPATIBLE_ENGINE)
    if not same_mega:
        reasons.add(MergeReason.INCOMPATIBLE_MEGA_CATEGORY)

    strong_reasons = {
        MergeReason.EXACT_NORMALIZED_MATCH,
        MergeReason.ALIAS_MATCH,
        MergeReason.GREEK_GREEKLISH_MATCH,
        MergeReason.TYPO_VARIANT_MATCH,
        MergeReason.ABBREVIATION_MATCH,
    }
    strong_found = bool(reasons.intersection(strong_reasons))
    if not strong_found:
        reasons.add(MergeReason.INSUFFICIENT_EVIDENCE)

    if reasons.intersection({MergeReason.INCOMPATIBLE_ENGINE, MergeReason.INCOMPATIBLE_MEGA_CATEGORY}):
        status = MergeStatus.BLOCKED
    elif MergeReason.AMBIGUOUS_MATCH in reasons:
        status = MergeStatus.REVIEW_REQUIRED
    elif strong_found:
        status = MergeStatus.MERGE_ALLOWED
    else:
        status = MergeStatus.REVIEW_REQUIRED
        reasons.add(MergeReason.WEAK_MATCH)

    if status != MergeStatus.MERGE_ALLOWED and not reasons.intersection({MergeReason.WEAK_MATCH, MergeReason.INSUFFICIENT_EVIDENCE}):
        reasons.add(MergeReason.WEAK_MATCH)

    return MergeDecision(
        status=status,
        reasons=_stable_reason_order(reasons),
        matched_terms=tuple(sorted(matched_terms)),
    )


def _candidate_for_pair(left: CanonicalTaxonomyRecord, right: CanonicalTaxonomyRecord, decision: MergeDecision) -> MergeCandidate:
    source_references = tuple(
        sorted(
            set(left.source_references).union(set(right.source_references)),
            key=lambda ref: (ref.source_item_id, ref.source_name, ref.source_type),
        )
    )
    provenance = tuple(sorted(set(left.provenance).union(set(right.provenance))))
    candidate_id = f"merge__{left.record_id}__{right.record_id}"
    return MergeCandidate(
        candidate_id=candidate_id,
        record_ids=(left.record_id, right.record_id),
        engine_ids=(left.engine_id, right.engine_id),
        mega_category_ids=(left.mega_category_id, right.mega_category_id),
        decision=decision,
        source_references=source_references,
        provenance=provenance,
    )


def build_taxonomy_deduplication(input_payload: DeduplicationInput) -> DeduplicationResult:
    records = tuple(input_payload.records or ())
    ordered_records = tuple(
        sorted(
            records,
            key=lambda record: (
                record.engine_id,
                record.mega_category_id,
                _normalize_text(record.product_family),
                record.record_id,
            ),
        )
    )

    candidates: list[MergeCandidate] = []
    for left, right in combinations(ordered_records, 2):
        decision = _decision_for_pair(left, right)
        if decision is None:
            continue
        candidates.append(_candidate_for_pair(left, right, decision))

    ordered_candidates = tuple(sorted(candidates, key=lambda candidate: candidate.candidate_id))
    status_counts = Counter(candidate.decision.status.value for candidate in ordered_candidates)

    engine_counts: Counter[str] = Counter()
    mega_counts: Counter[str] = Counter()
    for candidate in ordered_candidates:
        engine_key = (
            candidate.engine_ids[0]
            if candidate.engine_ids[0] == candidate.engine_ids[1]
            else "__cross_engine__"
        )
        mega_key = (
            candidate.mega_category_ids[0]
            if candidate.mega_category_ids[0] == candidate.mega_category_ids[1]
            else "__cross_mega_category__"
        )
        engine_counts[engine_key] += 1
        mega_counts[mega_key] += 1

    warnings: list[str] = []
    if status_counts.get(MergeStatus.BLOCKED.value, 0) > 0:
        warnings.append("Blocked merge candidates require manual resolution.")
    if status_counts.get(MergeStatus.REVIEW_REQUIRED.value, 0) > 0:
        warnings.append("Review-required candidates need operator validation.")

    return DeduplicationResult(
        candidates=ordered_candidates,
        total_candidates=len(ordered_candidates),
        merge_allowed_count=status_counts.get(MergeStatus.MERGE_ALLOWED.value, 0),
        review_required_count=status_counts.get(MergeStatus.REVIEW_REQUIRED.value, 0),
        blocked_count=status_counts.get(MergeStatus.BLOCKED.value, 0),
        counts_by_engine=dict(sorted(engine_counts.items())),
        counts_by_mega_category=dict(sorted(mega_counts.items())),
        valid=True,
        warnings=tuple(warnings),
    )
