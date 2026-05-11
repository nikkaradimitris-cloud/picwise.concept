from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

_NON_SAFE_PATTERN = re.compile(r"[^a-z0-9]+")
_DASH_PATTERN = re.compile(r"-{2,}")
_MIN_SLUG_LENGTH = 3


@dataclass(frozen=True)
class SlugBuildResult:
    valid: bool
    slug: str
    canonical_path: str
    reason_code: str | None


def _normalize_to_ascii(value: str) -> str:
    return (
        unicodedata.normalize("NFKD", str(value))
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )


def build_buying_page_slug(main_keyword: str) -> SlugBuildResult:
    normalized = _normalize_to_ascii(main_keyword)
    slug = _NON_SAFE_PATTERN.sub("-", normalized)
    slug = _DASH_PATTERN.sub("-", slug).strip("-")

    if not slug:
        return SlugBuildResult(
            valid=False,
            slug="",
            canonical_path="",
            reason_code="empty_slug_after_normalization",
        )
    if len(slug) < _MIN_SLUG_LENGTH:
        return SlugBuildResult(
            valid=False,
            slug=slug,
            canonical_path="",
            reason_code="slug_too_short",
        )
    if slug in {"best", "sitemap", "search", "results"}:
        return SlugBuildResult(
            valid=False,
            slug=slug,
            canonical_path="",
            reason_code="reserved_slug",
        )
    return SlugBuildResult(
        valid=True,
        slug=slug,
        canonical_path=f"/best/{slug}",
        reason_code=None,
    )
