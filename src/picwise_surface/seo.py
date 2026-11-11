from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from html import escape

from picwise_contracts import DecisionOutput

# Tells search engines not to index a page: the site's own search and its demo stay out
# of Google while the pages meant for it are built (owner, 2026-10-23;
# docs/PICWISE_GOOGLE_PAGES_SPEC.md, section 2).
NOINDEX_META = '<meta name="robots" content="noindex">'

# What every page Google may index says of itself (the audit, 2026-11-10; owner, the same
# day: «Ζητώ διόρθωση και βελτίωση ... τις προδιαγραφές google»). The audit found, on the
# live site: no canonical address on any page, while the same pages also answer on the
# Vercel backup's hostname; no sitemap, and none named in robots.txt; no icon
# (`/favicon.ico` answered 404), so a result in Google would carry none; no structured
# data; one title for every search. These add no page to Google: the pages it may index
# are the same seven (`INDEXABLE_PATHS`), the site's own search still carries `noindex`.
#
# The one address the site is known by: its primary domain (`PROJECT_RULES.md` section
# 8). Another origin, should the site ever move, is named here without changing code.
CANONICAL_ORIGIN_ENV = "PICWISE_CANONICAL_ORIGIN"
DEFAULT_CANONICAL_ORIGIN = "https://picwise.subby.cloud"
SITE_NAME = "PicWise"
# English as written for the United Kingdom: the site's market (`_HOME_HEADING`).
SITE_LANGUAGE = "en-GB"
THEME_COLOUR = "#2f6fe4"
ICON_SVG_PATH = "/assets/picwise/favicon.svg"
ICON_PNG_PATH = "/assets/picwise/favicon-48.png"
TOUCH_ICON_PATH = "/assets/picwise/apple-touch-icon.png"
LARGE_ICON_PATH = "/assets/picwise/icon-512.png"
MANIFEST_PATH = "/assets/picwise/site.webmanifest"
SITEMAP_PATH = "/sitemap.xml"
# The pages Google may index today: the home page without a search and the pages that say
# who runs PicWise and how (`legal.FOOTER_LINKS`). The pages meant for Google's results
# (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`) join their own sitemaps when the owner opens them.
INDEXABLE_PATHS = ("/", "/about", "/terms", "/privacy", "/cookies", "/affiliate-disclosure", "/contact")
# Crawlers stay off the redirect to the shops, which records a click, and off the two
# routes that act when called. The search is not blocked: its pages carry `noindex`,
# which Google reads only on a page it may fetch (the spec, section 2).
_ROBOTS_RULES = ("User-agent: *", "Disallow: /out/", "Disallow: /subby-proof", "Disallow: /cron/")


def canonical_origin() -> str:
    """The scheme and host the site is known by, without a trailing slash."""
    configured = str(os.environ.get(CANONICAL_ORIGIN_ENV) or "").strip().rstrip("/")
    if re.fullmatch(r"https://[a-z0-9.-]+", configured):
        return configured
    return DEFAULT_CANONICAL_ORIGIN


def canonical_url(path: str) -> str:
    """The one address of a page of the site: `path` on the canonical origin."""
    return canonical_origin() + "/" + str(path or "/").lstrip("/")


def icon_links_html() -> str:
    """The site's icon, for a browser's tab, a phone's home screen and a search result."""
    return (
        f'<link rel="icon" href="{ICON_SVG_PATH}" type="image/svg+xml">'
        f'<link rel="icon" href="{ICON_PNG_PATH}" type="image/png" sizes="48x48">'
        f'<link rel="apple-touch-icon" href="{TOUCH_ICON_PATH}">'
        f'<link rel="manifest" href="{MANIFEST_PATH}">'
        f'<meta name="theme-color" content="{THEME_COLOUR}">'
    )


def indexable_head_html(path: str, *, title: str, description: str) -> str:
    """What a page Google may index adds to its head: its one address, and how a link to
    it is shown where it is shared. `title` and `description` are the page's own."""
    address = escape(canonical_url(path), quote=True)
    return (
        f'<link rel="canonical" href="{address}">'
        '<meta property="og:type" content="website">'
        f'<meta property="og:site_name" content="{SITE_NAME}">'
        f'<meta property="og:locale" content="{SITE_LANGUAGE.replace("-", "_")}">'
        f'<meta property="og:title" content="{escape(title, quote=True)}">'
        f'<meta property="og:description" content="{escape(description, quote=True)}">'
        f'<meta property="og:url" content="{address}">'
        f'<meta property="og:image" content="{escape(canonical_url(LARGE_ICON_PATH), quote=True)}">'
        '<meta name="twitter:card" content="summary">'
    )


def home_structured_data_html() -> str:
    """Who publishes the site and what the site is, as schema.org data on the home page:
    only what the page itself says (the name, the address, the icon). No rating, no
    review, no search box of Google's: PicWise invents none and asks for none."""
    home = canonical_url("/")
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": f"{home}#organization",
                "name": SITE_NAME,
                "url": home,
                "logo": canonical_url(LARGE_ICON_PATH),
            },
            {
                "@type": "WebSite",
                "@id": f"{home}#website",
                "name": SITE_NAME,
                "url": home,
                "inLanguage": SITE_LANGUAGE,
                "publisher": {"@id": f"{home}#organization"},
            },
        ],
    }
    # "<" never ends the script early: written as its escape inside the data.
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return f'<script type="application/ld+json">{text}</script>'


def robots_txt() -> str:
    """`/robots.txt`: what crawlers stay off, and where the sitemap is."""
    return "\n".join(_ROBOTS_RULES) + f"\nSitemap: {canonical_url(SITEMAP_PATH)}\n"


def sitemap_xml() -> str:
    """`/sitemap.xml`: the canonical address of each page Google may index, and nothing
    else (the spec, section 2: only canonical, indexable addresses; no `lastmod` where
    the day a page's content changed is not known)."""
    rows = "".join(f"<url><loc>{escape(canonical_url(path))}</loc></url>" for path in INDEXABLE_PATHS)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{rows}</urlset>'
    )


def search_page_title(query: str) -> str:
    """The title of a search's page: the search itself, so that a visitor with several
    of them open can tell them apart. The home page keeps its own."""
    words = " ".join(str(query or "").split())
    if not words:
        return ""
    if len(words) > 70:
        words = words[:69].rstrip() + "…"
    return f"{words} — {SITE_NAME}"


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
