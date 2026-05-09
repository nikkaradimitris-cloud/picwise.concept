from __future__ import annotations

from collections.abc import Iterable
from xml.etree.ElementTree import Element, SubElement, tostring

from .google_quality_gate import is_publicly_eligible
from .models import BuyingPage
from .sitemap import normalize_base_url

DEFAULT_SITEMAP_BATCH_SIZE = 5_000


def collect_indexable_entries(pages: Iterable[BuyingPage]) -> tuple[tuple[str, str], ...]:
    entries = [
        (page.slug, page.last_updated.date().isoformat())
        for page in pages
        if is_publicly_eligible(page)
    ]
    entries.sort(key=lambda row: row[0])
    return tuple(entries)


def split_sitemap_entries(
    entries: Iterable[tuple[str, str]],
    *,
    batch_size: int = DEFAULT_SITEMAP_BATCH_SIZE,
) -> tuple[tuple[tuple[str, str], ...], ...]:
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0.")
    materialized = tuple(entries)
    return tuple(
        materialized[offset : offset + batch_size]
        for offset in range(0, len(materialized), batch_size)
    )


def render_sitemap_batch_xml(entries: Iterable[tuple[str, str]], *, base_url: str | None = None) -> str:
    resolved_base = normalize_base_url(base_url)
    urlset = Element(
        "urlset",
        attrib={"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"},
    )
    for slug, lastmod_date in entries:
        url_el = SubElement(urlset, "url")
        loc = SubElement(url_el, "loc")
        loc.text = f"{resolved_base}/best/{slug}"
        lastmod = SubElement(url_el, "lastmod")
        lastmod.text = lastmod_date
    return tostring(urlset, encoding="utf-8", xml_declaration=True).decode("utf-8")


def render_sitemap_index_xml(batch_paths: Iterable[str], *, base_url: str | None = None) -> str:
    resolved_base = normalize_base_url(base_url)
    sitemapindex = Element(
        "sitemapindex",
        attrib={"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"},
    )
    for path in batch_paths:
        cleaned = str(path).strip()
        if not cleaned:
            continue
        location = cleaned if cleaned.startswith("http") else f"{resolved_base}/{cleaned.lstrip('/')}"
        sitemap_el = SubElement(sitemapindex, "sitemap")
        loc = SubElement(sitemap_el, "loc")
        loc.text = location
    return tostring(sitemapindex, encoding="utf-8", xml_declaration=True).decode("utf-8")


def build_sitemap_batches(
    pages: Iterable[BuyingPage],
    *,
    batch_size: int = DEFAULT_SITEMAP_BATCH_SIZE,
    base_url: str | None = None,
) -> tuple[str, ...]:
    entries = collect_indexable_entries(pages)
    batches = split_sitemap_entries(entries, batch_size=batch_size)
    return tuple(render_sitemap_batch_xml(batch, base_url=base_url) for batch in batches)
