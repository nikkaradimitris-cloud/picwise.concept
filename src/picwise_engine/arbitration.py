from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from picwise_contracts import ContractValidationError, ProductBrain
from picwise_contracts.validation import (
    validate_financial_utility_choice_requirements,
    validate_no_commission_ranking_fields,
    validate_no_fake_data,
)

from .candidate_adapter import AdaptedCandidate


@dataclass(frozen=True)
class ArbitrationResult:
    selected_choices: list[dict[str, Any]]
    recommended_product_id: str
    recommendation_reason: str
    notes: list[str]


class DecisionArbitrator:
    def arbitrate(
        self,
        candidates: list[AdaptedCandidate],
        selected_brain: ProductBrain,
    ) -> ArbitrationResult:
        if len(candidates) < 4:
            raise ContractValidationError("At least 4 valid candidates are required; no fabrication allowed.")

        enriched = []
        for candidate in candidates:
            payload = dict(candidate.payload)
            validate_no_fake_data(payload)
            validate_no_commission_ranking_fields(payload)
            self._validate_brain_specific_requirements(payload, selected_brain)
            score = self._score_candidate(payload, selected_brain)
            enriched.append((payload, score))

        ordered = sorted(enriched, key=lambda item: (-item[1], str(item[0]["product_id"])))
        selected = self._select_with_role_diversity(ordered)
        if len(selected) < 4:
            raise ContractValidationError("Unable to select 4 compliant choices from valid candidates.")

        for choice in selected:
            choice["is_recommended"] = False

        recommended = max(
            selected,
            key=lambda choice: (
                self._score_candidate(choice, selected_brain),
                str(choice["product_id"]),
            ),
        )
        recommendation_reason = self._build_recommendation_reason(recommended)
        if not recommendation_reason:
            raise ContractValidationError("Recommended choice must include a recommendation reason.")

        recommended["is_recommended"] = True
        recommended["tracking_metadata"] = dict(recommended["tracking_metadata"])
        recommended["tracking_metadata"]["recommendation_reason"] = recommendation_reason

        return ArbitrationResult(
            selected_choices=selected,
            recommended_product_id=str(recommended["product_id"]),
            recommendation_reason=recommendation_reason,
            notes=["Deterministic rule-based arbitration applied."],
        )

    def _score_candidate(self, candidate: dict[str, Any], selected_brain: ProductBrain) -> int:
        score = 0
        if len(str(candidate.get("decision_label", "")).strip()) >= 12:
            score += 3
        if len(str(candidate.get("subtitle", "")).strip()) >= 12:
            score += 2
        reasons = candidate.get("key_reasons", [])
        if isinstance(reasons, list):
            score += min(3, len([reason for reason in reasons if str(reason).strip()]))
        if len(str(candidate.get("risks_or_limitations", "")).strip()) >= 18:
            score += 2
        if isinstance(candidate.get("tracking_metadata"), dict):
            score += 1

        if selected_brain == ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS:
            score += self._financial_signal_score(candidate)
        if selected_brain == ProductBrain.HIGH_TRUST_RISK_SENSITIVE_DECISIONS:
            score += self._high_trust_signal_score(candidate)

        return score

    def _select_with_role_diversity(
        self,
        ordered: list[tuple[dict[str, Any], int]],
    ) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        selected_ids: set[str] = set()
        seen_roles: set[str] = set()

        for candidate, _score in ordered:
            if len(selected) == 4:
                break
            role = str(candidate.get("role"))
            product_id = str(candidate["product_id"])
            if role in seen_roles or product_id in selected_ids:
                continue
            selected.append(candidate)
            seen_roles.add(role)
            selected_ids.add(product_id)

        if len(selected) < 4:
            for candidate, _score in ordered:
                if len(selected) == 4:
                    break
                product_id = str(candidate["product_id"])
                if product_id in selected_ids:
                    continue
                selected.append(candidate)
                selected_ids.add(product_id)

        return selected

    def _build_recommendation_reason(self, candidate: dict[str, Any]) -> str:
        reasons = candidate.get("key_reasons", [])
        if isinstance(reasons, list):
            compact = [str(reason).strip() for reason in reasons if str(reason).strip()]
            if compact:
                return f"Recommended for stronger overall fit: {', '.join(compact[:2])}."
        label = str(candidate.get("decision_label", "")).strip()
        if label:
            return f"Recommended because it offers the clearest fit: {label}."
        return ""

    def _validate_brain_specific_requirements(
        self,
        candidate: dict[str, Any],
        selected_brain: ProductBrain,
    ) -> None:
        risk_text = str(candidate.get("risks_or_limitations", ""))
        if selected_brain == ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS:
            validate_financial_utility_choice_requirements(risk_text)
            return
        if selected_brain != ProductBrain.HIGH_TRUST_RISK_SENSITIVE_DECISIONS:
            return

        lowered_risk = risk_text.lower()
        risk_markers = ("risk", "safety", "limit", "caution", "return", "warranty", "cert")
        if not any(marker in lowered_risk for marker in risk_markers):
            raise ContractValidationError(
                "High-trust/risk candidates must include explicit risks_or_limitations."
            )

        reassurance_text = (
            str(candidate.get("subtitle", "")).lower()
            + " "
            + " ".join(str(reason).lower() for reason in candidate.get("key_reasons", []))
        )
        reassurance_markers = ("reliable", "safety", "tested", "warranty", "support", "certified")
        if not any(marker in reassurance_text for marker in reassurance_markers):
            raise ContractValidationError(
                "High-trust/risk candidates must include reassurance signals."
            )

    @staticmethod
    def _financial_signal_score(candidate: dict[str, Any]) -> int:
        text = (
            str(candidate.get("subtitle", "")).lower()
            + " "
            + str(candidate.get("risks_or_limitations", "")).lower()
        )
        markers = ("term", "fee", "charge", "risk", "cancel", "unknown")
        return 2 if any(marker in text for marker in markers) else 0

    @staticmethod
    def _high_trust_signal_score(candidate: dict[str, Any]) -> int:
        text = (
            str(candidate.get("subtitle", "")).lower()
            + " "
            + str(candidate.get("risks_or_limitations", "")).lower()
        )
        markers = ("safety", "cert", "warranty", "return", "support")
        return 2 if any(marker in text for marker in markers) else 0
