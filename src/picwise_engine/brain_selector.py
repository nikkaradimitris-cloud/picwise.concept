from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from picwise_contracts import ProductBrain


@dataclass(frozen=True)
class BrainSelection:
    brain: ProductBrain
    confidence: float
    notes: str


class BrainSelector:
    _HIGH_TRUST_KEYWORDS = {
        "child",
        "baby",
        "infant",
        "safety",
        "safe",
        "sensitive",
        "medical",
        "health",
        "secure",
        "protection",
    }
    _FINANCIAL_KEYWORDS = {
        "insurance",
        "energy",
        "electricity",
        "gas",
        "bank",
        "loan",
        "credit",
        "mortgage",
        "utility",
        "contract",
        "provider",
        "tariff",
        "telecom",
    }
    _SOFTWARE_KEYWORDS = {
        "saas",
        "software",
        "program",
        "subscription",
        "crm",
        "invoicing",
        "billing",
        "tool",
        "platform",
        "api",
        "app",
    }
    _PHYSICAL_HOME_KEYWORDS = {
        "air fryer",
        "fridge",
        "refrigerator",
        "washing machine",
        "vacuum",
        "home",
        "appliance",
        "btu",
        "machine",
        "cleaner",
    }
    _TECH_KEYWORDS = {
        "phone",
        "iphone",
        "android",
        "laptop",
        "monitor",
        "power bank",
        "charger",
        "usb",
        "ssd",
        "ram",
        "cpu",
        "electronics",
    }

    _BRAIN_ORDER = (
        ProductBrain.HIGH_TRUST_RISK_SENSITIVE_DECISIONS,
        ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS,
        ProductBrain.SOFTWARE_PROGRAMS_SAAS,
        ProductBrain.PHYSICAL_PRODUCTS_HOME_MACHINES,
        ProductBrain.TECH_SPECS_ELECTRONICS,
    )

    def select(self, query: str, context: dict[str, Any] | None = None) -> BrainSelection:
        context = context or {}
        normalized_query = query.lower()
        category = str(context.get("category", "")).lower()
        product_type = str(context.get("product_type", "")).lower()
        service_type = str(context.get("service_type", "")).lower()
        risk_flags = self._normalize_string_list(context.get("risk_flags", []))

        score_map = {brain: 0 for brain in ProductBrain}

        self._apply_keyword_scores(normalized_query, score_map)
        self._apply_keyword_scores(category, score_map)
        self._apply_keyword_scores(product_type, score_map)
        self._apply_keyword_scores(service_type, score_map)

        if any(flag in {"high_trust", "safety_critical", "sensitive"} for flag in risk_flags):
            score_map[ProductBrain.HIGH_TRUST_RISK_SENSITIVE_DECISIONS] += 5
        if any(flag in {"financial", "contract_bound", "utility"} for flag in risk_flags):
            score_map[ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS] += 5

        ranked = sorted(
            score_map.items(),
            key=lambda item: (-item[1], self._BRAIN_ORDER.index(item[0])),
        )
        best_brain, best_score = ranked[0]
        second_score = ranked[1][1]

        if best_score <= 0:
            return BrainSelection(
                brain=ProductBrain.PHYSICAL_PRODUCTS_HOME_MACHINES,
                confidence=0.35,
                notes="Unclear classification; deterministic safe fallback applied.",
            )

        confidence = min(0.95, 0.55 + (best_score - second_score) * 0.1)
        return BrainSelection(
            brain=best_brain,
            confidence=round(confidence, 2),
            notes=f"Selected via deterministic keyword/context scoring ({best_score}:{second_score}).",
        )

    def _apply_keyword_scores(self, text: str, score_map: dict[ProductBrain, int]) -> None:
        if not text:
            return
        self._add_matches(text, self._HIGH_TRUST_KEYWORDS, score_map, ProductBrain.HIGH_TRUST_RISK_SENSITIVE_DECISIONS)
        self._add_matches(text, self._FINANCIAL_KEYWORDS, score_map, ProductBrain.FINANCIAL_UTILITY_CONTRACT_PRODUCTS)
        self._add_matches(text, self._SOFTWARE_KEYWORDS, score_map, ProductBrain.SOFTWARE_PROGRAMS_SAAS)
        self._add_matches(text, self._PHYSICAL_HOME_KEYWORDS, score_map, ProductBrain.PHYSICAL_PRODUCTS_HOME_MACHINES)
        self._add_matches(text, self._TECH_KEYWORDS, score_map, ProductBrain.TECH_SPECS_ELECTRONICS)

    @staticmethod
    def _add_matches(
        text: str,
        keywords: set[str],
        score_map: dict[ProductBrain, int],
        brain: ProductBrain,
    ) -> None:
        for keyword in keywords:
            if keyword in text:
                score_map[brain] += 2

    @staticmethod
    def _normalize_string_list(values: Any) -> list[str]:
        if not isinstance(values, list):
            return []
        return [str(value).lower() for value in values]
