from __future__ import annotations

from collections.abc import Iterable
from xml.etree.ElementTree import Element, SubElement, tostring

from .index_gate import evaluate_index_gate
from .models import BuyingPage

DEFAULT_PUBLIC_BASE_URL = "https://picwise.subby.cloud"


def normalize_base_url(base_url: str | None) -> str:
    candidate = (base_url or DEFAULT_PUBLIC_BASE_URL).strip()
    if not candidate:
        return DEFAULT_PUBLIC_BASE_URL
    return candidate.rstrip("/")


def render_buying_pages_sitemap_xml(pages: Iterable[BuyingPage], base_url: str | None = None) -> str:
    resolved_base = normalize_base_url(base_url)
    urlset = Element(
        "urlset",
        attrib={"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"},
    )

    indexable_pages = sorted(
        (
            page
            for page in pages
            if evaluate_index_gate(page).indexable
        ),
        key=lambda page: page.slug,
    )
    for page in indexable_pages:
        url_el = SubElement(urlset, "url")
        loc = SubElement(url_el, "loc")
        loc.text = f"{resolved_base}/best/{page.slug}"
        lastmod = SubElement(url_el, "lastmod")
        lastmod.text = page.last_updated.date().isoformat()

    xml_bytes = tostring(urlset, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")
