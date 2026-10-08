from __future__ import annotations

from functools import lru_cache
from urllib.parse import unquote

from picwise_buying_pages import (
    BuyingPagesRepository,
    render_buying_pages_sitemap_xml,
)
from picwise_surface.buying_page import render_buying_page_surface


@lru_cache(maxsize=1)
def get_buying_pages_repository() -> BuyingPagesRepository:
    """The buying pages the public `/best/<slug>` routes and sitemap may serve.

    Empty until buying pages are built from real provider data. The only page source
    in the repository, `load_seed_buying_pages()`, is a deterministic test fixture:
    brand "Picwise Demo", prices and ratings computed from the page and slot index
    ("Rating: 4.5 (153 reviews)"), sellers named "PickWise Partner N", and CTAs to
    example.com. Serving it published fabricated products, prices, ratings and review
    counts on indexable URLs, which the Mission Lock forbids outright. The fixture stays
    for offline tests of the page gates; it must never back a public route.
    """
    return BuyingPagesRepository(())


def render_best_slug_html(raw_slug: str) -> tuple[int, str]:
    slug = unquote(raw_slug).strip().strip("/")
    if not slug:
        return 404, "<html><body><h1>404</h1><p>Buying page not found.</p></body></html>"
    page = get_buying_pages_repository().get_by_slug(slug)
    if page is None:
        return 404, "<html><body><h1>404</h1><p>Buying page not found.</p></body></html>"
    return 200, render_buying_page_surface(page)


def render_buying_sitemap_xml(base_url: str | None) -> str:
    repository = get_buying_pages_repository()
    return render_buying_pages_sitemap_xml(repository.list_pages(), base_url=base_url)
