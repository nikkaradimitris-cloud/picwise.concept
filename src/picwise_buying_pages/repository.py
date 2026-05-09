from __future__ import annotations

from collections.abc import Iterable

from .models import BuyingPage
from .slugging import normalize_keyword_text


class BuyingPagesRepositoryError(ValueError):
    """Raised when repository fixtures violate uniqueness constraints."""


class BuyingPagesRepository:
    def __init__(self, pages: Iterable[BuyingPage]) -> None:
        self._pages_by_slug: dict[str, BuyingPage] = {}
        self._keyword_to_slug: dict[str, str] = {}

        for page in pages:
            if page.slug in self._pages_by_slug:
                raise BuyingPagesRepositoryError(f"Duplicate slug detected: {page.slug}")
            self._pages_by_slug[page.slug] = page

            lookup_terms = (page.main_keyword, *page.keyword_aliases)
            for term in lookup_terms:
                normalized = normalize_keyword_text(term)
                if not normalized:
                    continue
                if normalized in self._keyword_to_slug:
                    existing_slug = self._keyword_to_slug[normalized]
                    if existing_slug != page.slug:
                        raise BuyingPagesRepositoryError(
                            "Alias mapping conflict for "
                            f"'{term}' between '{existing_slug}' and '{page.slug}'."
                        )
                self._keyword_to_slug[normalized] = page.slug

    def list_pages(self) -> tuple[BuyingPage, ...]:
        slugs = sorted(self._pages_by_slug.keys())
        return tuple(self._pages_by_slug[slug] for slug in slugs)

    def get_by_slug(self, slug: str) -> BuyingPage | None:
        return self._pages_by_slug.get(slug)

    def get_by_keyword(self, keyword_or_alias: str) -> BuyingPage | None:
        normalized = normalize_keyword_text(keyword_or_alias)
        if not normalized:
            return None
        slug = self._keyword_to_slug.get(normalized)
        if slug is None:
            return None
        return self._pages_by_slug.get(slug)
