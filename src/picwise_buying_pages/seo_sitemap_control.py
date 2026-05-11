from __future__ import annotations

from collections.abc import Iterable
from xml.etree.ElementTree import Element, SubElement, tostring

from .seo_contracts import PageQualityStatus, SEOIndexStatus, SEOBuyingPage

MAX_STAGE37_SITEMAP_ENTRIES = 200


def _is_sitemap_eligible(page: SEOBuyingPage) -> bool:
    return (
        page.index_status == SEOIndexStatus.INDEXABLE
        and page.page_quality_status == PageQualityStatus.QUALITY_PASSED
        and page.sitemap_eligible
        and page.canonical_path.startswith("/best/")
        and page.valid_product_count >= 4
    )


def select_stage37_sitemap_pages(
    pages: Iterable[SEOBuyingPage],
    *,
    max_entries: int = MAX_STAGE37_SITEMAP_ENTRIES,
) -> tuple[SEOBuyingPage, ...]:
    if max_entries <= 0:
        raise ValueError("max_entries must be > 0.")
    materialized = tuple(pages)
    if len(materialized) > max_entries:
        raise ValueError("mass_generation_blocked_for_stage37")
    selected = sorted((page for page in materialized if _is_sitemap_eligible(page)), key=lambda page: page.slug)
    return tuple(selected)


def render_stage37_sitemap_xml(
    pages: Iterable[SEOBuyingPage],
    *,
    base_url: str,
    max_entries: int = MAX_STAGE37_SITEMAP_ENTRIES,
) -> str:
    resolved_base_url = str(base_url or "").strip().rstrip("/")
    if not resolved_base_url:
        raise ValueError("base_url is required.")
    selected = select_stage37_sitemap_pages(pages, max_entries=max_entries)
    urlset = Element(
        "urlset",
        attrib={"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"},
    )
    for page in selected:
        url_el = SubElement(urlset, "url")
        loc = SubElement(url_el, "loc")
        loc.text = f"{resolved_base_url}{page.canonical_path}"
        lastmod = SubElement(url_el, "lastmod")
        lastmod.text = page.last_updated.date().isoformat()
    return tostring(urlset, encoding="utf-8", xml_declaration=True).decode("utf-8")
