from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Any

from .contracts import OfferCandidate


_CANDIDATE_KEYS = (
    "candidate_id",
    "source_id",
    "source_type",
    "title",
    "brand",
    "model",
    "image_url",
    "price",
    "currency",
    "seller_name",
    "seller_url",
    "availability_status",
    "outbound_url",
    "affiliate_url",
    "category",
    "vertical",
    "engine",
    "category_bucket",
    "google_taxonomy_path",
    "saas_erp_contract_ref",
    "finance_insurance_contract_ref",
    "source_updated_at",
    "metadata",
)


def _to_float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_candidate(raw: dict[str, Any]) -> OfferCandidate:
    metadata = raw.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {"import_payload": str(metadata or "")}
    return OfferCandidate(
        candidate_id=str(raw.get("candidate_id") or "").strip(),
        source_id=str(raw.get("source_id") or "").strip(),
        source_type=str(raw.get("source_type") or "").strip(),
        title=(str(raw.get("title")).strip() if raw.get("title") not in (None, "") else None),
        brand=(str(raw.get("brand")).strip() if raw.get("brand") not in (None, "") else None),
        model=(str(raw.get("model")).strip() if raw.get("model") not in (None, "") else None),
        image_url=(str(raw.get("image_url")).strip() if raw.get("image_url") not in (None, "") else None),
        price=_to_float_or_none(raw.get("price")),
        currency=(str(raw.get("currency")).strip() if raw.get("currency") not in (None, "") else None),
        seller_name=(str(raw.get("seller_name")).strip() if raw.get("seller_name") not in (None, "") else None),
        seller_url=(str(raw.get("seller_url")).strip() if raw.get("seller_url") not in (None, "") else None),
        availability_status=(
            str(raw.get("availability_status")).strip() if raw.get("availability_status") not in (None, "") else None
        ),
        outbound_url=(str(raw.get("outbound_url")).strip() if raw.get("outbound_url") not in (None, "") else None),
        affiliate_url=(str(raw.get("affiliate_url")).strip() if raw.get("affiliate_url") not in (None, "") else None),
        category=(str(raw.get("category")).strip() if raw.get("category") not in (None, "") else None),
        vertical=(str(raw.get("vertical")).strip() if raw.get("vertical") not in (None, "") else None),
        engine=(str(raw.get("engine")).strip() if raw.get("engine") not in (None, "") else None),
        category_bucket=(
            str(raw.get("category_bucket")).strip() if raw.get("category_bucket") not in (None, "") else None
        ),
        google_taxonomy_path=(
            str(raw.get("google_taxonomy_path")).strip() if raw.get("google_taxonomy_path") not in (None, "") else None
        ),
        saas_erp_contract_ref=(
            str(raw.get("saas_erp_contract_ref")).strip() if raw.get("saas_erp_contract_ref") not in (None, "") else None
        ),
        finance_insurance_contract_ref=(
            str(raw.get("finance_insurance_contract_ref")).strip()
            if raw.get("finance_insurance_contract_ref") not in (None, "")
            else None
        ),
        source_updated_at=(
            str(raw.get("source_updated_at")).strip() if raw.get("source_updated_at") not in (None, "") else None
        ),
        metadata=metadata,
    )


def import_offer_candidates_from_json_text(text: str) -> tuple[OfferCandidate, ...]:
    payload = json.loads(text or "[]")
    if not isinstance(payload, list):
        return tuple()
    candidates: list[OfferCandidate] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        candidates.append(_normalize_candidate(row))
    return tuple(candidates)


def import_offer_candidates_from_csv_text(text: str) -> tuple[OfferCandidate, ...]:
    handle = StringIO(text or "")
    reader = csv.DictReader(handle)
    candidates: list[OfferCandidate] = []
    for row in reader:
        filtered = {key: row.get(key) for key in _CANDIDATE_KEYS}
        filtered["metadata"] = {"import_format": "csv"}
        candidates.append(_normalize_candidate(filtered))
    return tuple(candidates)
