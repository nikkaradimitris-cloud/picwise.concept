from __future__ import annotations

from functools import lru_cache
from urllib.parse import unquote

from picwise_buying_pages import BuyingPagesRepository, load_seed_buying_pages, render_buying_pages_sitemap_xml
from picwise_surface.buying_page import render_buying_page_surface


@lru_cache(maxsize=1)
def get_buying_pages_repository() -> BuyingPagesRepository:
    return BuyingPagesRepository(load_seed_buying_pages())


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
