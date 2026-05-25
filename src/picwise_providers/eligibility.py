from __future__ import annotations

from .contracts import PROVIDER_ELIGIBILITY_STATUSES, ProviderEligibilityResult, ProviderProduct
from .normalization import derive_stable_provider_product_id, is_valid_http_url


def _category_mapping_state(category_text: str) -> tuple[str, tuple[str, ...]]:
    normalized = " ".join(str(category_text or "").split()).strip()
    if not normalized:
        return "pending", ("missing_category_text",)
    return "available", ("category_text_present",)


def evaluate_provider_product_eligibility(product: ProviderProduct) -> ProviderEligibilityResult:
    reason_codes: list[str] = []
    derived_id = derive_stable_provider_product_id(
        product_url=product.product_url,
        title=product.title,
        raw=product.raw,
    )

    if not str(product.provider_key or "").strip():
        reason_codes.append("missing_provider_key")
    if not str(product.title or "").strip():
        reason_codes.append("missing_title")
    if not str(product.product_url or "").strip():
        reason_codes.append("missing_product_url")
    elif not is_valid_http_url(product.product_url):
        reason_codes.append("invalid_product_url")
    if not str(product.provider_product_id or derived_id).strip():
        reason_codes.append("missing_provider_product_id")

    category_state, category_reasons = _category_mapping_state(product.category_text)
    reason_codes.extend(category_reasons)

    if not str(product.image_url or "").strip():
        reason_codes.append("missing_image_url")
    if not str(product.price_text or "").strip():
        reason_codes.append("missing_price_text")
    if not str(product.availability_text or "").strip():
        reason_codes.append("missing_availability_text")

    blocking_codes = {
        "missing_provider_key",
        "missing_title",
        "missing_product_url",
        "invalid_product_url",
        "missing_provider_product_id",
    }
    if any(code in blocking_codes for code in reason_codes):
        status = "blocked"
    elif category_state == "pending" or any(
        code in reason_codes
        for code in ("missing_image_url", "missing_price_text", "missing_availability_text")
    ):
        status = "needs_review"
    else:
        status = "eligible"

    if status not in PROVIDER_ELIGIBILITY_STATUSES:
        status = "blocked"
        reason_codes.append("invalid_eligibility_resolution")

    return ProviderEligibilityResult(
        product=product,
        status=status,
        reason_codes=tuple(sorted(set(reason_codes))),
        derived_provider_product_id=derived_id,
    )
