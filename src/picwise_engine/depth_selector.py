from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from picwise_contracts import DecisionDepth, ProductBrain


@dataclass(frozen=True)
class DepthSelection:
    depth: DecisionDepth
    confidence: float
    notes: str


class DecisionDepthSelector:
    _FAST_KEYWORDS = {"quick", "simple", "cheap", "basic", "fast", "budget", "under"}
    _HIGH_STAKES_KEYWORDS = {
        "contract",
        "insurance",
        "loan",
        "mortgage",
        "child",
        "safety",
        "sensitive",
        "expensive",
        "long term",
    }

    def select(
        self,
        query: str,
        context: dict[str, Any] | None,
        selected_brain: ProductBrain,
    ) -> DepthSelection:
        context = context or {}
        query_text = query.lower()
        risk_level = str(context.get("risk_level", "")).lower()
        product_type = str(context.get("product_type", "")).lower()
        service_type = str(context.get("service_type", "")).lower()
        price_band = str(context.get("price_band", "")).lower()
        estimated_price = context.get("estimated_price")

        high_score = 0
        medium_score = 0
        fast_score = 0

        if selected_brain in {
            ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS,
            ProductBrain.HIGH_TRUST_RISK_SENSITIVE_DECISIONS,
        }:
            high_score += 3
        elif selected_brain in {
            ProductBrain.SOFTWARE_PROGRAMS_SAAS,
            ProductBrain.PHYSICAL_PRODUCTS_HOME_MACHINES,
        }:
            medium_score += 2
        else:
            fast_score += 1

        if risk_level in {"high", "critical", "sensitive"}:
            high_score += 3
        elif risk_level in {"medium", "moderate"}:
            medium_score += 2
        elif risk_level in {"low", "minimal"}:
            fast_score += 2

        if price_band in {"premium", "high", "enterprise"}:
            high_score += 2
        elif price_band in {"mid", "standard"}:
            medium_score += 1
        elif price_band in {"low", "budget"}:
            fast_score += 1

        if isinstance(estimated_price, (int, float)):
            if estimated_price >= 1000:
                high_score += 2
            elif estimated_price >= 150:
                medium_score += 1
            else:
                fast_score += 1

        if any(keyword in query_text for keyword in self._HIGH_STAKES_KEYWORDS):
            high_score += 2
        if any(keyword in query_text for keyword in self._FAST_KEYWORDS):
            fast_score += 1

        if "subscription" in service_type or "saas" in product_type:
            medium_score += 1
        if "contract" in service_type:
            high_score += 2

        scored_depths = [
            (DecisionDepth.HIGH_STAKES_HIGH_TRUST, high_score),
            (DecisionDepth.CONSIDERED_PURCHASE, medium_score),
            (DecisionDepth.FAST_DECISION, fast_score),
        ]
        scored_depths.sort(key=lambda item: (-item[1], item[0].value))
        chosen_depth, top_score = scored_depths[0]
        second_score = scored_depths[1][1]

        confidence = 0.5 if top_score == 0 else min(0.95, 0.6 + (top_score - second_score) * 0.1)
        return DepthSelection(
            depth=chosen_depth,
            confidence=round(confidence, 2),
            notes=f"Depth scored deterministically (high={high_score}, medium={medium_score}, fast={fast_score}).",
        )
