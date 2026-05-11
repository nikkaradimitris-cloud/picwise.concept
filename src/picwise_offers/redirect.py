from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re

from .contracts import ExternalOfferStatus
from .ranking import RankedOffer

_SAFE_URL_REGEX = re.compile(r"^https?://[a-z0-9.-]+\.[a-z]{2,}(?:[/?#].*)?$", flags=re.IGNORECASE)


class RedirectStatus(str, Enum):
    REDIRECT_READY = "redirect_ready"
    BLOCKED_INVALID_OFFER = "blocked_invalid_offer"
    BLOCKED_MISSING_URL = "blocked_missing_url"
    BLOCKED_INVALID_AFFILIATE_URL = "blocked_invalid_affiliate_url"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


@dataclass(frozen=True)
class RedirectTrackingPayload:
    decision_id: str
    selected_offer_id: str
    external_store: str
    external_url: str
    affiliate_url_present: bool
    intent_label: str
    timestamp: str
    source: str = "pickwise_external_offer_redirect_proof"
    test_mode: bool = True


@dataclass(frozen=True)
class RedirectProofInput:
    decision_id: str
    intent_label: str
    selected_offer: RankedOffer | None
    timestamp: str = "1970-01-01T00:00:00Z"


@dataclass(frozen=True)
class RedirectProofResult:
    status: RedirectStatus
    redirect_target_url: str | None
    tracking_payload: RedirectTrackingPayload | None
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


def _is_valid_url(value: str) -> bool:
    return bool(_SAFE_URL_REGEX.match((value or "").strip()))


def build_redirect_proof(redirect_input: RedirectProofInput) -> RedirectProofResult:
    ranked_offer = redirect_input.selected_offer
    if ranked_offer is None:
        return RedirectProofResult(
            status=RedirectStatus.BLOCKED_INVALID_OFFER,
            redirect_target_url=None,
            tracking_payload=None,
            reason_codes=("missing_selected_offer",),
        )

    offer = ranked_offer.offer
    if offer.status != ExternalOfferStatus.VALID_EXTERNAL_OFFER:
        return RedirectProofResult(
            status=RedirectStatus.BLOCKED_INVALID_OFFER,
            redirect_target_url=None,
            tracking_payload=None,
            reason_codes=("selected_offer_not_valid_external_offer",),
        )
    if not offer.is_external_temporary_data or offer.pickwise_owned_inventory:
        return RedirectProofResult(
            status=RedirectStatus.BLOCKED_INVALID_OFFER,
            redirect_target_url=None,
            tracking_payload=None,
            reason_codes=("selected_offer_not_temporary_external_data",),
        )

    external_url = (offer.external_url or "").strip()
    if not external_url:
        return RedirectProofResult(
            status=RedirectStatus.BLOCKED_MISSING_URL,
            redirect_target_url=None,
            tracking_payload=None,
            reason_codes=("missing_external_url",),
        )
    if not _is_valid_url(external_url):
        return RedirectProofResult(
            status=RedirectStatus.BLOCKED_INVALID_OFFER,
            redirect_target_url=None,
            tracking_payload=None,
            reason_codes=("invalid_external_url",),
        )

    affiliate_url = (offer.affiliate_url or "").strip()
    if affiliate_url and not _is_valid_url(affiliate_url):
        return RedirectProofResult(
            status=RedirectStatus.BLOCKED_INVALID_AFFILIATE_URL,
            redirect_target_url=None,
            tracking_payload=None,
            reason_codes=("invalid_affiliate_url",),
        )

    redirect_target = affiliate_url or external_url
    payload = RedirectTrackingPayload(
        decision_id=redirect_input.decision_id,
        selected_offer_id=offer.offer_id,
        external_store=offer.external_store,
        external_url=external_url,
        affiliate_url_present=bool(affiliate_url),
        intent_label=redirect_input.intent_label,
        timestamp=redirect_input.timestamp,
    )
    return RedirectProofResult(
        status=RedirectStatus.REDIRECT_READY,
        redirect_target_url=redirect_target,
        tracking_payload=payload,
        reason_codes=("redirect_proof_ready",),
    )
