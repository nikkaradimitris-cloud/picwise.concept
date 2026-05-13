from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class TargetMarket(str, Enum):
    US = "US"
    UK = "UK"
    DE = "DE"
    GR = "GR"


class LocaleEligibilityStatus(str, Enum):
    LOCALE_READY = "locale_ready"
    LOCALE_REVIEW_REQUIRED = "locale_review_required"
    LOCALE_BLOCKED = "locale_blocked"


@dataclass(frozen=True)
class ProductLocaleProfile:
    candidate_market: str | None
    candidate_locale: str | None
    candidate_currency: str | None
    delivery_coverage: tuple[str, ...]


@dataclass(frozen=True)
class LocaleEligibilityDecision:
    status: LocaleEligibilityStatus
    target_market: str
    candidate_market: str | None
    candidate_locale: str | None
    candidate_currency: str | None
    delivery_coverage: tuple[str, ...]
    reasons: tuple[str, ...]
    blocker_reasons: tuple[str, ...]
    review_reasons: tuple[str, ...]
    can_show_to_user: bool
    can_continue_to_candidate_page: bool


@dataclass(frozen=True)
class LocaleRuleSet:
    expected_currency_by_market: Mapping[str, str]
    allowed_alternate_currencies_by_market: Mapping[str, tuple[str, ...]]
    review_rate_threshold_for_step4: float


DEFAULT_LOCALE_RULESET = LocaleRuleSet(
    expected_currency_by_market={
        TargetMarket.US.value: "USD",
        TargetMarket.UK.value: "GBP",
        TargetMarket.DE.value: "EUR",
        TargetMarket.GR.value: "EUR",
    },
    allowed_alternate_currencies_by_market={
        TargetMarket.US.value: tuple(),
        TargetMarket.UK.value: tuple(),
        TargetMarket.DE.value: tuple(),
        TargetMarket.GR.value: tuple(),
    },
    review_rate_threshold_for_step4=0.20,
)

_MARKET_REGION = {
    "US": "US",
    "UK": "GB",
    "DE": "DE",
    "GR": "GR",
}

_CURRENCY_REASON_CODES = {
    "currency_missing",
    "currency_mismatch_for_target_market",
    "market_currency_conflict",
}
_DELIVERY_MISSING_REASON_CODES = {"delivery_coverage_missing"}
_MARKET_MISMATCH_REASON_CODES = {
    "candidate_market_unknown",
    "locale_market_conflict",
    "cross_market_delivery_not_explicit_for_target",
    "us_market_rejects_non_us_delivery_profile",
    "uk_market_requires_explicit_uk_delivery",
    "de_market_requires_explicit_de_or_eu_de_coverage",
    "gr_market_requires_explicit_gr_or_eu_gr_coverage",
}


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _normalize_market(value: Any) -> str | None:
    text = _normalize_text(value)
    if text is None:
        return None
    return text.upper().replace("_", "-")


def _normalize_currency(value: Any) -> str | None:
    text = _normalize_text(value)
    if text is None:
        return None
    return text.upper()


def _extract_region_from_locale(locale: str | None) -> str | None:
    if not locale:
        return None
    normalized = locale.replace("_", "-")
    parts = [part for part in normalized.split("-") if part]
    if len(parts) < 2:
        return None
    return parts[-1].upper()


def _extract_mapping(candidate: Any) -> Mapping[str, Any]:
    if isinstance(candidate, Mapping):
        return candidate
    if hasattr(candidate, "__dict__"):
        payload = candidate.__dict__
        if isinstance(payload, Mapping):
            return payload
    return {}


def _coerce_delivery_tokens(value: Any) -> tuple[str, ...]:
    tokens: list[str] = []
    if isinstance(value, (list, tuple, set)):
        for item in value:
            normalized = _normalize_market(item)
            if normalized:
                tokens.append(normalized)
    elif isinstance(value, str):
        for chunk in value.replace(";", ",").split(","):
            normalized = _normalize_market(chunk)
            if normalized:
                tokens.append(normalized)

    deduped = tuple(sorted(dict.fromkeys(tokens)))
    return deduped


def _extract_profile(candidate: Any) -> ProductLocaleProfile:
    payload = _extract_mapping(candidate)
    metadata = payload.get("metadata")
    metadata_map = metadata if isinstance(metadata, Mapping) else {}
    locale_market = metadata_map.get("locale_market")
    locale_market_map = locale_market if isinstance(locale_market, Mapping) else {}

    candidate_market = _normalize_market(
        payload.get("candidate_market")
        or payload.get("market")
        or payload.get("country_market")
        or locale_market_map.get("market")
    )
    candidate_locale = _normalize_text(
        payload.get("candidate_locale")
        or payload.get("locale")
        or locale_market_map.get("locale")
    )
    candidate_currency = _normalize_currency(
        payload.get("candidate_currency")
        or payload.get("currency")
        or locale_market_map.get("currency")
    )
    delivery_coverage = _coerce_delivery_tokens(
        payload.get("delivery_coverage")
        or metadata_map.get("delivery_coverage")
        or payload.get("shipping_coverage")
        or metadata_map.get("shipping_coverage")
    )
    return ProductLocaleProfile(
        candidate_market=candidate_market,
        candidate_locale=candidate_locale,
        candidate_currency=candidate_currency,
        delivery_coverage=delivery_coverage,
    )


def _resolve_target_market(target_market: TargetMarket | str) -> str:
    if isinstance(target_market, TargetMarket):
        return target_market.value
    normalized = _normalize_market(target_market)
    return normalized or ""


def _resolve_ruleset(ruleset: LocaleRuleSet | Mapping[str, Any] | None) -> LocaleRuleSet:
    if ruleset is None:
        return DEFAULT_LOCALE_RULESET
    if isinstance(ruleset, LocaleRuleSet):
        return ruleset

    payload = dict(ruleset)
    expected_market_currency = payload.get("expected_currency_by_market", {})
    alt_currencies = payload.get("allowed_alternate_currencies_by_market", {})

    normalized_expected: dict[str, str] = {}
    if isinstance(expected_market_currency, Mapping):
        for market, currency in expected_market_currency.items():
            normalized_market = _normalize_market(market)
            normalized_currency = _normalize_currency(currency)
            if normalized_market and normalized_currency:
                normalized_expected[normalized_market] = normalized_currency

    normalized_alt: dict[str, tuple[str, ...]] = {}
    if isinstance(alt_currencies, Mapping):
        for market, currencies in alt_currencies.items():
            normalized_market = _normalize_market(market)
            if not normalized_market:
                continue
            if isinstance(currencies, (list, tuple, set)):
                normalized_alt[normalized_market] = tuple(
                    sorted(
                        dict.fromkeys(
                            currency
                            for currency in (_normalize_currency(item) for item in currencies)
                            if currency
                        )
                    )
                )
            elif currencies is None:
                normalized_alt[normalized_market] = tuple()

    return LocaleRuleSet(
        expected_currency_by_market=normalized_expected or DEFAULT_LOCALE_RULESET.expected_currency_by_market,
        allowed_alternate_currencies_by_market=normalized_alt
        or DEFAULT_LOCALE_RULESET.allowed_alternate_currencies_by_market,
        review_rate_threshold_for_step4=float(
            payload.get("review_rate_threshold_for_step4", DEFAULT_LOCALE_RULESET.review_rate_threshold_for_step4)
        ),
    )


def _delivery_has_target(delivery_coverage: tuple[str, ...], target_market: str) -> bool:
    return target_market in delivery_coverage


def _delivery_has_eu_target_combo(delivery_coverage: tuple[str, ...], target_market: str) -> bool:
    return "EU" in delivery_coverage and target_market in delivery_coverage


def evaluate_locale_product_eligibility(
    candidate: Any,
    target_market: TargetMarket | str,
    ruleset: LocaleRuleSet | Mapping[str, Any] | None = None,
) -> LocaleEligibilityDecision:
    resolved_target_market = _resolve_target_market(target_market)
    resolved_ruleset = _resolve_ruleset(ruleset)
    profile = _extract_profile(candidate)

    blocker_reasons: list[str] = []
    review_reasons: list[str] = []

    if resolved_target_market not in resolved_ruleset.expected_currency_by_market:
        blocker_reasons.append("unsupported_target_market")

    candidate_market = profile.candidate_market
    if candidate_market is None:
        blocker_reasons.append("candidate_market_unknown")
    elif candidate_market not in {"US", "UK", "DE", "GR", "EU"}:
        blocker_reasons.append("candidate_market_unknown")

    expected_currency = resolved_ruleset.expected_currency_by_market.get(resolved_target_market)
    allowed_currency_set = {
        currency
        for currency in (
            [expected_currency]
            + list(resolved_ruleset.allowed_alternate_currencies_by_market.get(resolved_target_market, tuple()))
        )
        if currency
    }

    if profile.candidate_currency is None:
        review_reasons.append("currency_missing")
    elif allowed_currency_set and profile.candidate_currency not in allowed_currency_set:
        blocker_reasons.append("currency_mismatch_for_target_market")

    if candidate_market and profile.candidate_currency and expected_currency:
        candidate_expected_currency = resolved_ruleset.expected_currency_by_market.get(candidate_market)
        if candidate_expected_currency and profile.candidate_currency != candidate_expected_currency:
            blocker_reasons.append("market_currency_conflict")

    locale_region = _extract_region_from_locale(profile.candidate_locale)
    if candidate_market in _MARKET_REGION and locale_region:
        expected_region = _MARKET_REGION[candidate_market]
        if locale_region != expected_region:
            blocker_reasons.append("locale_market_conflict")

    if not profile.delivery_coverage:
        review_reasons.append("delivery_coverage_missing")
    else:
        has_target_delivery = _delivery_has_target(profile.delivery_coverage, resolved_target_market)
        has_eu_combo = _delivery_has_eu_target_combo(profile.delivery_coverage, resolved_target_market)

        if resolved_target_market == TargetMarket.US.value:
            if not has_target_delivery:
                blocker_reasons.append("us_market_rejects_non_us_delivery_profile")
        elif resolved_target_market == TargetMarket.UK.value:
            if not has_target_delivery:
                blocker_reasons.append("uk_market_requires_explicit_uk_delivery")
        elif resolved_target_market == TargetMarket.DE.value:
            if not (has_target_delivery or has_eu_combo):
                blocker_reasons.append("de_market_requires_explicit_de_or_eu_de_coverage")
        elif resolved_target_market == TargetMarket.GR.value:
            if not (has_target_delivery or has_eu_combo):
                blocker_reasons.append("gr_market_requires_explicit_gr_or_eu_gr_coverage")

        if candidate_market and candidate_market != resolved_target_market:
            cross_market_explicit = False
            if resolved_target_market in {TargetMarket.DE.value, TargetMarket.GR.value} and candidate_market == "EU":
                cross_market_explicit = has_eu_combo
            else:
                cross_market_explicit = has_target_delivery
            if not cross_market_explicit:
                blocker_reasons.append("cross_market_delivery_not_explicit_for_target")

    deduped_blockers = tuple(sorted(dict.fromkeys(blocker_reasons)))
    deduped_reviews = tuple(sorted(dict.fromkeys(review_reasons)))
    deduped_reasons = tuple(sorted(dict.fromkeys([*deduped_blockers, *deduped_reviews])))

    if deduped_blockers:
        status = LocaleEligibilityStatus.LOCALE_BLOCKED
    elif deduped_reviews:
        status = LocaleEligibilityStatus.LOCALE_REVIEW_REQUIRED
    else:
        status = LocaleEligibilityStatus.LOCALE_READY

    can_show = status == LocaleEligibilityStatus.LOCALE_READY
    return LocaleEligibilityDecision(
        status=status,
        target_market=resolved_target_market,
        candidate_market=profile.candidate_market,
        candidate_locale=profile.candidate_locale,
        candidate_currency=profile.candidate_currency,
        delivery_coverage=profile.delivery_coverage,
        reasons=deduped_reasons,
        blocker_reasons=deduped_blockers,
        review_reasons=deduped_reviews,
        can_show_to_user=can_show,
        can_continue_to_candidate_page=can_show,
    )


def evaluate_locale_batch_eligibility(
    candidates: Iterable[Any],
    target_market: TargetMarket | str,
    ruleset: LocaleRuleSet | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_ruleset = _resolve_ruleset(ruleset)
    decisions = [
        evaluate_locale_product_eligibility(
            candidate=candidate,
            target_market=target_market,
            ruleset=resolved_ruleset,
        )
        for candidate in candidates
    ]

    total_candidates = len(decisions)
    status_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    for decision in decisions:
        status_key = decision.status.value
        status_counts[status_key] = status_counts.get(status_key, 0) + 1
        for reason in decision.reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    ready_count = status_counts.get(LocaleEligibilityStatus.LOCALE_READY.value, 0)
    review_required_count = status_counts.get(LocaleEligibilityStatus.LOCALE_REVIEW_REQUIRED.value, 0)
    blocked_count = status_counts.get(LocaleEligibilityStatus.LOCALE_BLOCKED.value, 0)

    currency_mismatch_count = sum(
        1
        for decision in decisions
        if any(reason in _CURRENCY_REASON_CODES for reason in decision.reasons)
    )
    delivery_missing_count = sum(
        1
        for decision in decisions
        if any(reason in _DELIVERY_MISSING_REASON_CODES for reason in decision.reasons)
    )
    market_mismatch_count = sum(
        1
        for decision in decisions
        if any(reason in _MARKET_MISMATCH_REASON_CODES for reason in decision.reasons)
    )

    review_rate = (review_required_count / total_candidates) if total_candidates else 0.0
    can_continue_to_step4 = bool(
        total_candidates > 0
        and blocked_count == 0
        and review_rate <= resolved_ruleset.review_rate_threshold_for_step4
    )

    return {
        "total_candidates": total_candidates,
        "ready_count": ready_count,
        "review_required_count": review_required_count,
        "blocked_count": blocked_count,
        "currency_mismatch_count": currency_mismatch_count,
        "delivery_missing_count": delivery_missing_count,
        "market_mismatch_count": market_mismatch_count,
        "status_counts": dict(sorted(status_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "can_continue_to_step4": can_continue_to_step4,
    }
