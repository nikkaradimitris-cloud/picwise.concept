from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from enum import Enum

from .index_gate import is_product_slot_publicly_valid
from .models import BuyingPage, ProductSlot, RefreshMetadata, RefreshStatus


class RefreshTransition(str, Enum):
    SUCCESS = "success"
    DUE = "due"
    FAILED = "failed"
    MANUAL = "manual"


def choose_recommended_product_id(page: BuyingPage, products: tuple[ProductSlot, ...]) -> str:
    """Select the best product deterministically from the 4 slots."""

    def _availability_rank(value: str) -> int:
        normalized = str(value).strip().lower()
        if normalized == "in_stock":
            return 3
        if normalized == "preorder":
            return 2
        if normalized == "limited":
            return 1
        return 0

    def _price_fit(product: ProductSlot) -> float:
        if not page.price_band_applicable:
            return 0.5
        lower = float(page.target_price_min_eur or 80.0)
        upper = float(page.target_price_max_eur or 250.0)
        if lower <= float(product.price) <= upper:
            return 1.0
        distance = min(abs(float(product.price) - lower), abs(float(product.price) - upper))
        return max(0.0, 1.0 - (distance / max(upper - lower, 1.0)))

    valid_products = tuple(product for product in products if is_product_slot_publicly_valid(page, product))
    pool = valid_products or products
    ranked = sorted(
        pool,
        key=lambda product: (
            _availability_rank(product.availability),
            _price_fit(product),
            float(product.rating or 0.0),
            int(product.reviews_count or 0),
            product.product_id,
        ),
        reverse=True,
    )
    return ranked[0].product_id


def determine_refresh_status(page: BuyingPage, now: datetime) -> RefreshStatus:
    metadata = page.refresh_metadata
    if metadata.refresh_status in {RefreshStatus.REFRESH_FAILED, RefreshStatus.MANUAL_REQUIRED}:
        return metadata.refresh_status
    if metadata.next_refresh_at is not None and now >= metadata.next_refresh_at:
        return RefreshStatus.REFRESH_DUE
    return RefreshStatus.FRESH


def transition_refresh_status(
    page: BuyingPage,
    transition: RefreshTransition,
    now: datetime,
    refresh_reason: str,
) -> BuyingPage:
    interval_hours = int(page.refresh_metadata.refresh_interval_hours)
    if transition == RefreshTransition.SUCCESS:
        status = RefreshStatus.FRESH
        next_refresh_at = now + timedelta(hours=interval_hours)
    elif transition == RefreshTransition.DUE:
        status = RefreshStatus.REFRESH_DUE
        next_refresh_at = now
    elif transition == RefreshTransition.FAILED:
        status = RefreshStatus.REFRESH_FAILED
        next_refresh_at = now + timedelta(hours=min(interval_hours, 6))
    else:
        status = RefreshStatus.MANUAL_REQUIRED
        next_refresh_at = None

    metadata = RefreshMetadata(
        refresh_status=status,
        refresh_interval_hours=interval_hours,
        next_refresh_at=next_refresh_at,
        last_refresh_at=now,
        refresh_reason=refresh_reason.strip() or "refresh_transition",
    )
    return replace(page, refresh_metadata=metadata, last_updated=now)


def refresh_page_products(
    page: BuyingPage,
    refreshed_products: tuple[ProductSlot, ...],
    now: datetime,
    refresh_reason: str = "deterministic_product_refresh",
) -> BuyingPage:
    """Refresh 4 product slots while keeping URL/slug unchanged."""
    if len(refreshed_products) != 4:
        raise ValueError("refreshed_products must contain exactly 4 product slots.")
    invalid_slots = [
        idx
        for idx, product in enumerate(refreshed_products, start=1)
        if not is_product_slot_publicly_valid(page, product)
    ]
    if invalid_slots:
        joined = ",".join(str(idx) for idx in invalid_slots)
        raise ValueError(
            f"refreshed_products contain public-ineligible slots: {joined}."
        )

    recommended_product_id = choose_recommended_product_id(page, refreshed_products)
    refreshed_page = replace(
        page,
        products=refreshed_products,
        recommended_product_id=recommended_product_id,
    )
    return transition_refresh_status(
        refreshed_page,
        transition=RefreshTransition.SUCCESS,
        now=now,
        refresh_reason=refresh_reason,
    )
