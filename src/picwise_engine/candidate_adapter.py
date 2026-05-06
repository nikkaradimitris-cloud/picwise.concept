from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from picwise_contracts import ContractValidationError, ProductBrain, ProductChoiceRole
from picwise_contracts.validation import (
    validate_choice_role,
    validate_financial_utility_choice_requirements,
    validate_no_commission_ranking_fields,
    validate_no_fake_data,
)


@dataclass(frozen=True)
class AdaptedCandidate:
    payload: dict[str, Any]


class ProductCandidateAdapter:
    _REQUIRED_FIELDS = (
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
    )

    _ALIAS_MAP = {
        "id": "product_id",
        "provider": "merchant_or_provider",
        "merchant": "merchant_or_provider",
        "price": "price_or_cost_display",
        "price_display": "price_or_cost_display",
        "cta_text": "cta_label",
        "redirect_url": "redirect_target",
        "risk_or_limitation": "risks_or_limitations",
    }

    def adapt_candidates(
        self,
        raw_candidates: list[dict[str, Any]],
        selected_brain: ProductBrain,
    ) -> list[AdaptedCandidate]:
        if not isinstance(raw_candidates, list):
            raise ContractValidationError("Candidates must be provided as a list of dictionaries.")

        adapted: list[AdaptedCandidate] = []
        for idx, raw_candidate in enumerate(raw_candidates):
            if not isinstance(raw_candidate, dict):
                raise ContractValidationError(f"Candidate at index {idx} is not a dictionary.")
            validate_no_fake_data(raw_candidate)
            validate_no_commission_ranking_fields(raw_candidate)

            normalized = self._normalize_fields(raw_candidate)
            missing = [field for field in self._REQUIRED_FIELDS if field not in normalized]
            if missing:
                raise ContractValidationError(
                    f"Candidate '{raw_candidate.get('id', idx)}' missing required fields: {missing}"
                )

            role = ProductChoiceRole(str(normalized["role"]))
            validate_choice_role(role, selected_brain)

            key_reasons = normalized["key_reasons"]
            if not isinstance(key_reasons, list):
                raise ContractValidationError(
                    f"Candidate '{normalized['product_id']}' key_reasons must be a list."
                )
            if not key_reasons:
                raise ContractValidationError(
                    f"Candidate '{normalized['product_id']}' requires at least one key reason."
                )

            normalized_risk = self._compose_risk_text(normalized, selected_brain)
            if selected_brain == ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS:
                validate_financial_utility_choice_requirements(normalized_risk)

            tracking_metadata = normalized.get("tracking_metadata", {})
            if not isinstance(tracking_metadata, dict):
                raise ContractValidationError(
                    f"Candidate '{normalized['product_id']}' tracking_metadata must be an object."
                )

            payload = {
                "product_id": str(normalized["product_id"]),
                "title": str(normalized["title"]),
                "merchant_or_provider": str(normalized["merchant_or_provider"]),
                "price_or_cost_display": str(normalized["price_or_cost_display"]),
                "role": role.value,
                "decision_label": str(normalized["decision_label"]),
                "subtitle": str(normalized["subtitle"]),
                "key_reasons": [str(reason) for reason in key_reasons],
                "risks_or_limitations": normalized_risk,
                "cta_label": str(normalized["cta_label"]),
                "redirect_target": str(normalized["redirect_target"]),
                "tracking_metadata": tracking_metadata,
                "is_recommended": False,
            }
            adapted.append(AdaptedCandidate(payload=payload))

        return adapted

    def _normalize_fields(self, raw_candidate: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(raw_candidate)
        for old_name, new_name in self._ALIAS_MAP.items():
            if old_name in normalized and new_name not in normalized:
                normalized[new_name] = normalized[old_name]
        return normalized

    def _compose_risk_text(self, candidate: dict[str, Any], selected_brain: ProductBrain) -> str:
        risk_text = str(candidate["risks_or_limitations"])
        if selected_brain != ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS:
            return risk_text

        appended: list[str] = []
        if candidate.get("terms_summary"):
            appended.append(f"Terms: {candidate['terms_summary']}")
        if candidate.get("unknowns_summary"):
            appended.append(f"Unknowns: {candidate['unknowns_summary']}")
        if appended:
            risk_text = f"{risk_text} {' | '.join(str(item) for item in appended)}"
        return risk_text
