from __future__ import annotations

import re
from dataclasses import dataclass

from picwise_contracts import DecisionOutput

# Tells search engines not to index a page: the site's own search and its demo stay out
# of Google while the pages meant for it are built (owner, 2026-10-23;
# docs/PICWISE_GOOGLE_PAGES_SPEC.md, section 2).
NOINDEX_META = '<meta name="robots" content="noindex">'


@dataclass(frozen=True)
class SeoLandingBundle:
    slug: str
    canonical_candidates: list[str]
    title: str
    description: str


def build_seo_landing_bundle(
    query: str,
    decision_output: DecisionOutput,
    *,
    base_path: str = "/",
) -> SeoLandingBundle:
    slug = generate_safe_slug(query)
    normalized_base = _normalize_base_path(base_path)
    canonical_candidates = [
        f"{normalized_base}q/{slug}/",
        f"{normalized_base}decision/{decision_output.selected_brain.value}/{slug}/",
    ]

    title = f"{decision_output.page_title} | Query match: {query.strip()}"
    recommended = next(choice for choice in decision_output.choices if choice.is_recommended)
    description = (
        f"Decision-ready options for '{query.strip()}': 4 curated choices and 1 recommended "
        f"option for a direct next step. Recommended pick: {recommended.title}."
    )
    return SeoLandingBundle(
        slug=slug,
        canonical_candidates=canonical_candidates,
        title=title,
        description=description,
    )


def generate_safe_slug(query: str) -> str:
    lowered = query.strip().lower()
    lowered = re.sub(r"[^a-z0-9\s-]", "", lowered)
    lowered = re.sub(r"\s+", "-", lowered)
    lowered = re.sub(r"-{2,}", "-", lowered)
    candidate = lowered.strip("-")
    return candidate or "query"


def _normalize_base_path(base_path: str) -> str:
    normalized = base_path.strip() or "/"
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if not normalized.endswith("/"):
        normalized = f"{normalized}/"
    return normalized
