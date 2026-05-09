from __future__ import annotations

from dataclasses import dataclass

from .index_gate import evaluate_index_gate
from .models import ApprovalStatus, BuyingPage
from .slugging import normalize_keyword_text, slugify_keyword

_BUYING_INTENT_HINTS = (
    "best",
    "for",
    "under",
    "compare",
    "comparison",
    "vs",
    "review",
    "reviews",
    "buy",
    "buyer",
    "price",
)
_FAKE_DATA_MARKERS = (
    "fake",
    "dummy",
    "placeholder",
    "lorem ipsum",
    "test data",
    "sample data",
    "n/a",
)


@dataclass(frozen=True)
class GoogleQualityGateResult:
    quality_passed: bool
    publication_ready: bool
    reasons: tuple[str, ...]


def _normalize_terms(page: BuyingPage) -> tuple[str, ...]:
    terms = [page.main_keyword, *page.keyword_aliases]
    normalized = [normalize_keyword_text(term) for term in terms]
    return tuple(term for term in normalized if term)


def _near_duplicate_keyword(main_keyword: str, existing_keyword: str) -> bool:
    main_normalized = normalize_keyword_text(main_keyword)
    existing_normalized = normalize_keyword_text(existing_keyword)
    if not main_normalized or not existing_normalized or main_normalized == existing_normalized:
        return False
    if main_normalized.startswith(existing_normalized + " "):
        return len(main_normalized.split()) - len(existing_normalized.split()) <= 2
    if existing_normalized.startswith(main_normalized + " "):
        return len(existing_normalized.split()) - len(main_normalized.split()) <= 2
    return False


def _has_clear_buying_intent(page: BuyingPage) -> bool:
    normalized_keyword = normalize_keyword_text(page.main_keyword)
    if not normalized_keyword:
        return False
    tokens = set(normalized_keyword.split())
    if any(hint in tokens for hint in _BUYING_INTENT_HINTS):
        return True
    return len(tokens) >= 4


def _has_unique_comparison_value(page: BuyingPage) -> bool:
    if len(page.products) != 4:
        return False
    titles = {normalize_keyword_text(product.title) for product in page.products}
    reason_count = sum(
        1
        for product in page.products
        if len(normalize_keyword_text(product.reason_summary).split()) >= 3
    )
    buying_reason_count = sum(
        1
        for product in page.products
        if len(normalize_keyword_text(product.buying_reason).split()) >= 3
    )
    distinct_prices = {round(float(product.price), 2) for product in page.products}
    return (
        len([title for title in titles if title]) >= 3
        and reason_count == 4
        and buying_reason_count == 4
        and len(distinct_prices) >= 2
    )


def _has_thin_affiliate_pattern(page: BuyingPage) -> bool:
    has_affiliate_links = any((product.affiliate_url or "").strip() for product in page.products)
    if not has_affiliate_links:
        return False
    useful_reasons = sum(
        1
        for product in page.products
        if len(normalize_keyword_text(product.reason_summary)) >= 6
        and len(normalize_keyword_text(product.buying_reason)) >= 6
    )
    return useful_reasons < 3


def _contains_fake_product_data(page: BuyingPage) -> bool:
    haystack = " ".join(
        (
            page.main_keyword,
            " ".join(page.keyword_aliases),
            " ".join(product.title for product in page.products),
            " ".join(product.reason_summary for product in page.products),
            " ".join(product.buying_reason for product in page.products),
            " ".join(product.availability for product in page.products),
        )
    ).lower()
    if any(marker in haystack for marker in _FAKE_DATA_MARKERS):
        return True
    for product in page.products:
        if product.price <= 0:
            return True
        if product.rating is not None and product.reviews_count in (None, 0):
            return True
    return False


def _has_structured_data_mismatch(page: BuyingPage, structured_data: dict[str, object] | None) -> bool:
    if not structured_data:
        return False
    if bool(structured_data.get("hidden_only")):
        return True
    items = structured_data.get("products")
    if not isinstance(items, list):
        return False
    visible = {
        product.product_id: (
            round(float(product.price), 2),
            normalize_keyword_text(product.availability),
            round(float(product.rating), 2) if product.rating is not None else None,
            int(product.reviews_count) if product.reviews_count is not None else None,
        )
        for product in page.products
    }
    for item in items:
        if not isinstance(item, dict):
            return True
        product_id = str(item.get("product_id", "")).strip()
        if product_id not in visible:
            return True
        expected_price, expected_availability, expected_rating, expected_reviews = visible[product_id]
        seen_price = round(float(item.get("price", expected_price)), 2)
        seen_availability = normalize_keyword_text(str(item.get("availability", expected_availability)))
        seen_rating = item.get("rating")
        seen_reviews = item.get("reviews_count")
        if expected_price != seen_price or expected_availability != seen_availability:
            return True
        if seen_rating is not None and expected_rating is not None and round(float(seen_rating), 2) != expected_rating:
            return True
        if seen_reviews is not None and expected_reviews is not None and int(seen_reviews) != expected_reviews:
            return True
    return False


def evaluate_google_quality_gate(
    page: BuyingPage,
    *,
    existing_pages: tuple[BuyingPage, ...] = (),
    structured_data: dict[str, object] | None = None,
    economic_score_passed: bool = True,
) -> GoogleQualityGateResult:
    reasons: list[str] = []
    normalized_terms = _normalize_terms(page)
    if not normalized_terms:
        reasons.append("keyword_only_page")

    normalized_keyword = normalize_keyword_text(page.main_keyword)
    seen_terms = set()
    for existing in existing_pages:
        seen_terms.update(_normalize_terms(existing))
    if normalized_keyword and normalized_keyword in seen_terms:
        reasons.append("duplicate_keyword")
    for existing in existing_pages:
        if _near_duplicate_keyword(page.main_keyword, existing.main_keyword):
            reasons.append("near_duplicate_keyword")
            break
    if any(normalized_keyword and normalize_keyword_text(alias) == normalized_keyword for alias in page.keyword_aliases):
        reasons.append("keyword_alias_duplicate")

    if page.slug != slugify_keyword(page.main_keyword):
        reasons.append("canonical_slug_mismatch")
    if "--" in page.slug or not page.slug.strip():
        reasons.append("doorway_style_slug")

    if not _has_clear_buying_intent(page):
        reasons.append("missing_buying_intent")
    if not _has_unique_comparison_value(page):
        reasons.append("weak_unique_user_value")
    if _has_thin_affiliate_pattern(page):
        reasons.append("thin_affiliate_page")
    if _contains_fake_product_data(page):
        reasons.append("fake_product_data")

    if not page.faq_items:
        reasons.append("missing_required_faq")
    if not page.related_searches:
        reasons.append("missing_required_related_searches")

    if _has_structured_data_mismatch(page, structured_data):
        reasons.append("structured_data_mismatch")

    if not economic_score_passed:
        reasons.append("economic_scoring_not_passed")

    index_result = evaluate_index_gate(page)
    if not index_result.indexable:
        reasons.append("index_gate_not_passed")

    if page.approval_status != ApprovalStatus.APPROVED:
        reasons.append("approval_status_not_approved")

    quality_blockers = {
        "keyword_only_page",
        "duplicate_keyword",
        "keyword_alias_duplicate",
        "near_duplicate_keyword",
        "doorway_style_slug",
        "missing_buying_intent",
        "weak_unique_user_value",
        "thin_affiliate_page",
        "fake_product_data",
        "missing_required_faq",
        "missing_required_related_searches",
        "structured_data_mismatch",
    }
    quality_passed = not any(reason in quality_blockers for reason in reasons)
    publication_ready = quality_passed and all(
        reason not in {"economic_scoring_not_passed", "index_gate_not_passed", "approval_status_not_approved"}
        for reason in reasons
    )

    return GoogleQualityGateResult(
        quality_passed=quality_passed,
        publication_ready=publication_ready,
        reasons=tuple(sorted(set(reasons))),
    )


def is_publicly_eligible(page: BuyingPage, *, economic_score_passed: bool = True) -> bool:
    return evaluate_google_quality_gate(
        page,
        economic_score_passed=economic_score_passed,
    ).publication_ready
