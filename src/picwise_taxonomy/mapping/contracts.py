from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MappingStatus(str, Enum):
    MAPPED = "mapped"
    NEEDS_REVIEW = "needs_review"
    UNMAPPED = "unmapped"
    INVALID_SOURCE = "invalid_source"


class MappingConfidence(str, Enum):
    EXACT = "exact"
    STRONG_ALIAS = "strong_alias"
    PATH_MATCH = "path_match"
    WEAK = "weak"
    NONE = "none"


class GapReason(str, Enum):
    NO_ENGINE_MATCH = "no_engine_match"
    NO_MEGA_CATEGORY_MATCH = "no_mega_category_match"
    AMBIGUOUS_ENGINE = "ambiguous_engine"
    AMBIGUOUS_MEGA_CATEGORY = "ambiguous_mega_category"
    UNKNOWN_DEPARTMENT = "unknown_department"
    UNKNOWN_SUBCATEGORY = "unknown_subcategory"
    UNKNOWN_PRODUCT_FAMILY = "unknown_product_family"
    INVALID_SOURCE_ITEM = "invalid_source_item"
    FORBIDDEN_INVENTORY_FIELD = "forbidden_inventory_field"
    WEAK_MATCH_NEEDS_REVIEW = "weak_match_needs_review"
    UNSUPPORTED_GOOGLE_PATH = "unsupported_google_path"


@dataclass(frozen=True)
class MappingTarget:
    engine_id: str
    mega_category_id: str
    department: str = ""
    subcategory: str = ""
    product_family: str = ""


@dataclass(frozen=True)
class TaxonomyMappingInput:
    source_item_id: str
    source_name: str
    source_type: str
    raw_label: str
    raw_parent_label: str
    raw_path: str
    proposed_engine_id: str = ""
    proposed_mega_category_id: str = ""
    proposed_aliases: tuple[str, ...] = field(default_factory=tuple)
    raw_metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TaxonomyMappingResult:
    source_item_id: str
    status: MappingStatus
    confidence: MappingConfidence
    target: MappingTarget | None
    normalized_label: str
    normalized_path: str
    gap_reason: GapReason | None = None
    operator_action_hint: str = ""
    suggested_engine_id: str = ""
    suggested_mega_category_id: str = ""

    def to_dict(self) -> dict:
        payload = {
            "source_item_id": self.source_item_id,
            "status": self.status.value,
            "confidence": self.confidence.value,
            "target": None,
            "normalized_label": self.normalized_label,
            "normalized_path": self.normalized_path,
            "gap_reason": self.gap_reason.value if self.gap_reason else "",
            "operator_action_hint": self.operator_action_hint,
            "suggested_engine_id": self.suggested_engine_id,
            "suggested_mega_category_id": self.suggested_mega_category_id,
        }
        if self.target is not None:
            payload["target"] = {
                "engine_id": self.target.engine_id,
                "mega_category_id": self.target.mega_category_id,
                "department": self.target.department,
                "subcategory": self.target.subcategory,
                "product_family": self.target.product_family,
            }
        return payload
