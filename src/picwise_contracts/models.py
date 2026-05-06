from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from .enums import (
    DecisionDepth,
    MissingDataState,
    ProductBrain,
    ProductChoiceRole,
    TrackingEventType,
)
from .validation import (
    ContractValidationError,
    ValidationWarning,
    validate_choice_role,
    validate_cta_label,
    validate_financial_utility_choice_requirements,
    validate_missing_data_states,
    validate_no_commission_ranking_fields,
    validate_no_fake_data,
    validate_primary_choice_count,
    validate_recommended_count,
)


def _parse_iso_timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractValidationError(f"Invalid ISO timestamp: {value}") from exc


def _validate_uuid(value: str, field_name: str) -> None:
    try:
        UUID(str(value))
    except ValueError as exc:
        raise ContractValidationError(f"{field_name} must be a valid UUID.") from exc


@dataclass(frozen=True)
class ProductChoice:
    product_id: str
    title: str
    merchant_or_provider: str
    price_or_cost_display: str
    role: ProductChoiceRole
    decision_label: str
    subtitle: str
    key_reasons: list[str]
    risks_or_limitations: str
    cta_label: str
    redirect_target: str
    tracking_metadata: dict[str, Any]
    is_recommended: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any], brain: ProductBrain) -> tuple["ProductChoice", list[ValidationWarning]]:
        required = (
            "product_id",
            "title",
            "merchant_or_provider",
            "price_or_cost_display",
            "role",
            "decision_label",
            "subtitle",
            "key_reasons",
            "risks_or_limitations",
            "cta_label",
            "redirect_target",
            "tracking_metadata",
            "is_recommended",
        )
        missing_fields = [field_name for field_name in required if field_name not in data]
        if missing_fields:
            raise ContractValidationError(
                f"ProductChoice missing required fields: {missing_fields}"
            )

        validate_no_fake_data(data)
        validate_no_commission_ranking_fields(data)

        role = ProductChoiceRole(data["role"])
        validate_choice_role(role, brain)

        if not isinstance(data["key_reasons"], list) or not data["key_reasons"]:
            raise ContractValidationError("ProductChoice.key_reasons must be a non-empty list.")

        if not isinstance(data["tracking_metadata"], dict):
            raise ContractValidationError(
                "ProductChoice.tracking_metadata must be an object/dict."
            )

        if brain == ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS:
            validate_financial_utility_choice_requirements(data["risks_or_limitations"])

        warnings = validate_cta_label(str(data["cta_label"]), brain)

        return (
            cls(
                product_id=str(data["product_id"]),
                title=str(data["title"]),
                merchant_or_provider=str(data["merchant_or_provider"]),
                price_or_cost_display=str(data["price_or_cost_display"]),
                role=role,
                decision_label=str(data["decision_label"]),
                subtitle=str(data["subtitle"]),
                key_reasons=[str(reason) for reason in data["key_reasons"]],
                risks_or_limitations=str(data["risks_or_limitations"]),
                cta_label=str(data["cta_label"]),
                redirect_target=str(data["redirect_target"]),
                tracking_metadata=data["tracking_metadata"],
                is_recommended=bool(data["is_recommended"]),
            ),
            warnings,
        )


@dataclass(frozen=True)
class DecisionOutput:
    query: str
    selected_brain: ProductBrain
    decision_depth: DecisionDepth
    page_title: str
    choices: list[ProductChoice]
    recommended_product_id: str
    missing_data_states: list[MissingDataState]
    tracking_context: dict[str, Any]
    more_choices: list[ProductChoice] | None = None
    warnings: list[ValidationWarning] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DecisionOutput":
        required = (
            "query",
            "selected_brain",
            "decision_depth",
            "page_title",
            "choices",
            "recommended_product_id",
            "missing_data_states",
            "tracking_context",
        )
        missing_fields = [field_name for field_name in required if field_name not in data]
        if missing_fields:
            raise ContractValidationError(
                f"DecisionOutput missing required fields: {missing_fields}"
            )

        validate_no_fake_data(data)
        validate_no_commission_ranking_fields(data)

        brain = ProductBrain(data["selected_brain"])
        depth = DecisionDepth(data["decision_depth"])

        if not isinstance(data["choices"], list):
            raise ContractValidationError("DecisionOutput.choices must be a list.")

        validate_primary_choice_count(len(data["choices"]))

        choices: list[ProductChoice] = []
        warnings: list[ValidationWarning] = []
        for raw_choice in data["choices"]:
            parsed_choice, choice_warnings = ProductChoice.from_dict(raw_choice, brain)
            choices.append(parsed_choice)
            warnings.extend(choice_warnings)

        recommended_count = sum(1 for choice in choices if choice.is_recommended)
        validate_recommended_count(recommended_count)

        recommended_id = str(data["recommended_product_id"])
        primary_ids = {choice.product_id for choice in choices}
        if recommended_id not in primary_ids:
            raise ContractValidationError(
                "recommended_product_id must belong to one of the 4 primary choices."
            )

        recommended_choice = next(choice for choice in choices if choice.is_recommended)
        if recommended_choice.product_id != recommended_id:
            raise ContractValidationError(
                "recommended_product_id must match the single recommended primary choice."
            )

        if "more_choices" in data and data["more_choices"] is not None:
            if not isinstance(data["more_choices"], list):
                raise ContractValidationError("DecisionOutput.more_choices must be a list.")
            if len(data["more_choices"]) > 4:
                raise ContractValidationError(
                    "more_choices cannot exceed 4 entries (no infinite list behavior)."
                )
            more_choices: list[ProductChoice] = []
            for raw_choice in data["more_choices"]:
                parsed_choice, choice_warnings = ProductChoice.from_dict(raw_choice, brain)
                more_choices.append(parsed_choice)
                warnings.extend(choice_warnings)
        else:
            more_choices = None

        if not isinstance(data["tracking_context"], dict):
            raise ContractValidationError("DecisionOutput.tracking_context must be a dict.")

        missing_states_raw = data["missing_data_states"]
        if not isinstance(missing_states_raw, list):
            raise ContractValidationError("missing_data_states must be a list.")
        validate_missing_data_states([str(state) for state in missing_states_raw])
        missing_states = [MissingDataState(state) for state in missing_states_raw]

        # Depth enum is validated and retained for downstream enforcement.
        if depth == DecisionDepth.HIGH_STAKES_HIGH_TRUST and not choices:
            raise ContractValidationError("High-stakes output requires validated choices.")

        return cls(
            query=str(data["query"]),
            selected_brain=brain,
            decision_depth=depth,
            page_title=str(data["page_title"]),
            choices=choices,
            recommended_product_id=recommended_id,
            missing_data_states=missing_states,
            tracking_context=data["tracking_context"],
            more_choices=more_choices,
            warnings=warnings,
        )


@dataclass(frozen=True)
class TrackingEvent:
    event_type: TrackingEventType
    event_id: str
    timestamp: datetime
    query: str
    selected_brain: ProductBrain
    decision_depth: DecisionDepth
    session_id: str
    source: str
    metadata: dict[str, Any]
    missing_data_states: list[MissingDataState]
    product_id: str | None = None
    recommended: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrackingEvent":
        required = (
            "event_type",
            "event_id",
            "timestamp",
            "query",
            "selected_brain",
            "decision_depth",
            "session_id",
            "source",
            "metadata",
            "missing_data_states",
        )
        missing_fields = [field_name for field_name in required if field_name not in data]
        if missing_fields:
            raise ContractValidationError(
                f"TrackingEvent missing required fields: {missing_fields}"
            )

        validate_no_fake_data(data)
        validate_no_commission_ranking_fields(data)

        event_type = TrackingEventType(data["event_type"])
        _validate_uuid(str(data["event_id"]), "event_id")
        _validate_uuid(str(data["session_id"]), "session_id")

        if not isinstance(data["metadata"], dict):
            raise ContractValidationError("TrackingEvent.metadata must be a dict.")

        missing_states_raw = data["missing_data_states"]
        if not isinstance(missing_states_raw, list):
            raise ContractValidationError("TrackingEvent.missing_data_states must be a list.")
        validate_missing_data_states([str(state) for state in missing_states_raw])

        product_required = {
            TrackingEventType.RECOMMENDED_SHOWN,
            TrackingEventType.CTA_CLICK,
            TrackingEventType.RECOMMENDED_CLICK,
            TrackingEventType.NON_RECOMMENDED_CLICK,
            TrackingEventType.REDIRECT_ATTEMPT,
            TrackingEventType.REDIRECT_SUCCESS,
            TrackingEventType.REDIRECT_FAILURE,
        }
        if event_type in product_required and not data.get("product_id"):
            raise ContractValidationError(f"{event_type.value} requires product_id.")

        if event_type == TrackingEventType.RECOMMENDED_CLICK and data.get("recommended") is not True:
            raise ContractValidationError("recommended_click requires recommended=true.")
        if event_type == TrackingEventType.NON_RECOMMENDED_CLICK and data.get("recommended") is not False:
            raise ContractValidationError("non_recommended_click requires recommended=false.")
        if event_type == TrackingEventType.RECOMMENDED_SHOWN and data.get("recommended") is not True:
            raise ContractValidationError("recommended_shown requires recommended=true.")

        return cls(
            event_type=event_type,
            event_id=str(data["event_id"]),
            timestamp=_parse_iso_timestamp(str(data["timestamp"])),
            query=str(data["query"]),
            selected_brain=ProductBrain(data["selected_brain"]),
            decision_depth=DecisionDepth(data["decision_depth"]),
            session_id=str(data["session_id"]),
            source=str(data["source"]),
            metadata=data["metadata"],
            missing_data_states=[MissingDataState(state) for state in missing_states_raw],
            product_id=str(data["product_id"]) if data.get("product_id") is not None else None,
            recommended=data.get("recommended"),
        )


@dataclass(frozen=True)
class RedirectEvent:
    event_id: str
    timestamp: datetime
    query: str
    product_id: str
    merchant_or_provider: str
    redirect_target: str
    recommended: bool
    click_to_redirect_budget_ms: int
    tracking_metadata: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RedirectEvent":
        required = (
            "event_id",
            "timestamp",
            "query",
            "product_id",
            "merchant_or_provider",
            "redirect_target",
            "recommended",
            "click_to_redirect_budget_ms",
            "tracking_metadata",
        )
        missing_fields = [field_name for field_name in required if field_name not in data]
        if missing_fields:
            raise ContractValidationError(
                f"RedirectEvent missing required fields: {missing_fields}"
            )

        validate_no_fake_data(data)
        validate_no_commission_ranking_fields(data)
        _validate_uuid(str(data["event_id"]), "event_id")

        budget_ms = int(data["click_to_redirect_budget_ms"])
        if budget_ms >= 300:
            raise ContractValidationError(
                "click_to_redirect_budget_ms must be < 300ms per performance target."
            )

        if not isinstance(data["tracking_metadata"], dict):
            raise ContractValidationError("tracking_metadata must be a dict.")

        return cls(
            event_id=str(data["event_id"]),
            timestamp=_parse_iso_timestamp(str(data["timestamp"])),
            query=str(data["query"]),
            product_id=str(data["product_id"]),
            merchant_or_provider=str(data["merchant_or_provider"]),
            redirect_target=str(data["redirect_target"]),
            recommended=bool(data["recommended"]),
            click_to_redirect_budget_ms=budget_ms,
            tracking_metadata=data["tracking_metadata"],
        )
