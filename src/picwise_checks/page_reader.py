"""A product page read as text: what its schema.org data and its product tags say.

The rules' section 4.5, reader 2: read in this order, the first that gives a product
winning: the page's JSON-LD (a Product, or a ProductGroup with its variants, in a @graph
or not), then its microdata (`itemprop`), then the `product:` and `og:` tags. Nothing
else (rules 4.5.4): no page drawn in a browser, no guess from words such as "Add to
basket". A page that gives none of these has no product a machine reads.

Each offer keeps its price as the page writes it (a number, in the offer's own
currency), its availability as schema.org's word ("instock", "outofstock",
"preorder"...), and the codes that tie it to a feed row: its SKU, its GTIN (padded to 14
digits, so the UPC-12 and EAN-13 forms of one code agree, as `product_identity` pads
them), its MPN, and in a Shopify shop its variant's id. Reader 1, Shopify's own product
JSON, is read by `read_shopify_product`.

Only the first product of a page counts, with its own variants: products a page lists
beside it (related, recently viewed) are not its product.
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Iterator, Mapping

# The schema.org words of availability (the last part of their address, lower case).
# Owner, 2026-11-12 and the rules' section 5.2: in stock is a state that lets the buyer
# order now for delivery; pre-order, back-order and "in store only" are not (Proposed).
IN_STOCK_WORDS = frozenset({"instock", "limitedavailability", "onlineonly"})
NOT_IN_STOCK_WORDS = frozenset(
    {"outofstock", "soldout", "discontinued", "preorder", "presale", "backorder", "instoreonly", "oos"}
)
IN_STOCK = "in stock"
SOLD_OUT = "sold out"

_GTIN_KEYS = ("gtin14", "gtin13", "gtin12", "gtin8", "gtin")
_JSON_LD = re.compile(
    r"<script\b[^>]*\btype\s*=\s*[\"']?application/ld\+json[\"']?[^>]*>(.*?)</script\s*>", re.I | re.S
)
_TAG = re.compile(r"<(meta|link)\b[^>]*>", re.I)
_ATTR = re.compile(r"([a-zA-Z_:.-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))")
_ITEMPROP = re.compile(r"<([a-zA-Z0-9]+)\b([^>]*\bitemprop\s*=\s*[^>]*)>([^<]*)", re.I)
_PRODUCT_ITEMTYPE = re.compile(r"itemtype\s*=\s*[\"']?https?://schema\.org/Product\b", re.I)
_NUMBER = re.compile(r"\d[\d.,]*")


@dataclass(frozen=True)
class Offer:
    price: float | None
    currency: str = ""
    availability: str = ""
    sku: str = ""
    gtin: str = ""
    mpn: str = ""
    variant: str = ""


@dataclass(frozen=True)
class PageRead:
    """What a page says of its product; `how` is "" when no product was read on it."""

    how: str = ""
    name: str = ""
    offers: tuple[Offer, ...] = ()
    gtins: frozenset[str] = field(default_factory=frozenset)
    skus: frozenset[str] = field(default_factory=frozenset)
    mpns: frozenset[str] = field(default_factory=frozenset)
    canonical: str = ""

    @property
    def found(self) -> bool:
        return bool(self.how)


NOTHING = PageRead()


def gtin14(value: Any) -> str:
    """A GTIN-8/12/13/14 as 14 digits, or "" when the value is no such code."""
    digits = re.sub(r"\D", "", str(value if value is not None else ""))
    return digits.zfill(14) if len(digits) in (8, 12, 13, 14) and digits.strip("0") else ""


def _code(value: Any) -> str:
    return " ".join(str(value if value is not None else "").split())


def availability_word(value: Any) -> str:
    """schema.org's availability word ("instock") out of an address, a word or words."""
    text = str(value if value is not None else "").strip().rsplit("/", 1)[-1].lower()
    return re.sub(r"[^a-z]", "", text)


def stock_of(word: str) -> str:
    """"in stock", "sold out", or "" for an availability word that says neither."""
    if word in IN_STOCK_WORDS:
        return IN_STOCK
    if word in NOT_IN_STOCK_WORDS:
        return SOLD_OUT
    return ""


def amount(value: Any) -> float | None:
    """A price written as a number, "1,299.00", "1.299,00", "£12.99" or "12,99"; None
    when it is none of these. A price is never worked out: this reads what is written."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if value >= 0 else None
    match = _NUMBER.search(str(value if value is not None else ""))
    if not match:
        return None
    text = match.group(0).rstrip(".,")
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", text):
        text = text.replace(",", "")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", text):
        text = text.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d+,\d{1,2}", text):
        text = text.replace(",", ".")
    elif not re.fullmatch(r"\d+(\.\d+)?", text):
        return None
    try:
        return float(text)
    except ValueError:
        return None


# ---- JSON-LD ----------------------------------------------------------------------


def _types(node: Mapping[str, Any]) -> set[str]:
    kind = node.get("@type")
    kinds = kind if isinstance(kind, list) else [kind]
    return {str(item).rsplit("/", 1)[-1] for item in kinds if item}


def _products_in(node: Any) -> Iterator[Mapping[str, Any]]:
    if isinstance(node, list):
        for item in node:
            yield from _products_in(item)
    elif isinstance(node, dict):
        if _types(node) & {"Product", "ProductGroup", "IndividualProduct", "ProductModel"}:
            yield node
            return
        for key in ("@graph", "mainEntity", "mainEntityOfPage"):
            if key in node:
                yield from _products_in(node[key])


def _json_blocks(text: str) -> Iterator[Any]:
    for block in _JSON_LD.findall(text):
        stripped = block.strip()
        for candidate in (stripped, html.unescape(stripped)):
            try:
                yield json.loads(candidate, strict=False)
                break
            except ValueError:
                continue


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return [] if value is None else [value]


def _offers_of(product: Mapping[str, Any]) -> list[Offer]:
    sku = _code(product.get("sku"))
    gtin = next((gtin14(product.get(key)) for key in _GTIN_KEYS if gtin14(product.get(key))), "")
    mpn = _code(product.get("mpn"))
    offers: list[Offer] = []
    for node in _as_list(product.get("offers")):
        if not isinstance(node, dict):
            continue
        kinds = _types(node)
        price: Any = node.get("price")
        if price in (None, "") and isinstance(node.get("priceSpecification"), (dict, list)):
            spec = next((item for item in _as_list(node["priceSpecification"]) if isinstance(item, dict)), {})
            price = spec.get("price")
            node = {**node, "priceCurrency": node.get("priceCurrency") or spec.get("priceCurrency")}
        if "AggregateOffer" in kinds and price in (None, ""):
            low, high = amount(node.get("lowPrice")), amount(node.get("highPrice"))
            # Several prices are no one price: the offer says its stock, not a price.
            price = low if low is not None and (high is None or high == low) else None
        if "AggregateOffer" in kinds and isinstance(node.get("offers"), list):
            offers.extend(_offers_of({"sku": sku, "gtin": gtin, "mpn": mpn, "offers": node["offers"]}))
            continue
        offers.append(
            Offer(
                price=amount(price),
                currency=_code(node.get("priceCurrency")).upper(),
                availability=availability_word(node.get("availability")),
                sku=_code(node.get("sku")) or sku,
                gtin=next((gtin14(node.get(key)) for key in _GTIN_KEYS if gtin14(node.get(key))), "") or gtin,
                mpn=_code(node.get("mpn")) or mpn,
            )
        )
    return offers


def _read_json_ld(text: str) -> PageRead:
    for data in _json_blocks(text):
        for product in _products_in(data):
            parts = [product]
            parts.extend(item for item in _as_list(product.get("hasVariant")) if isinstance(item, dict))
            offers: list[Offer] = []
            for part in parts:
                offers.extend(_offers_of(part))
            codes = [
                (
                    _code(part.get("sku")),
                    next((gtin14(part.get(key)) for key in _GTIN_KEYS if gtin14(part.get(key))), ""),
                    _code(part.get("mpn")),
                )
                for part in parts
            ]
            if not offers and not any(any(code) for code in codes):
                continue
            return PageRead(
                how="json-ld",
                name=_code(product.get("name")),
                offers=tuple(offers),
                gtins=frozenset({code[1] for code in codes} | {offer.gtin for offer in offers}) - {""},
                skus=frozenset({code[0] for code in codes} | {offer.sku for offer in offers}) - {""},
                mpns=frozenset({code[2] for code in codes} | {offer.mpn for offer in offers}) - {""},
            )
    return NOTHING


# ---- microdata and tags ---------------------------------------------------------


def _attrs(tag: str) -> dict[str, str]:
    return {
        match.group(1).lower(): html.unescape(next(group for group in match.groups()[1:] if group is not None))
        for match in _ATTR.finditer(tag)
    }


def _read_microdata(text: str) -> PageRead:
    if not _PRODUCT_ITEMTYPE.search(text):
        return NOTHING
    seen: dict[str, str] = {}
    for match in _ITEMPROP.finditer(text):
        attrs = _attrs(match.group(2))
        name = attrs.get("itemprop", "").lower()
        if not name or name in seen:
            continue
        value = attrs.get("content") or attrs.get("href") or attrs.get("value") or html.unescape(match.group(3))
        seen[name] = " ".join(str(value).split())
    price = amount(seen.get("price") or seen.get("lowprice"))
    gtin = next((gtin14(seen.get(key)) for key in _GTIN_KEYS if gtin14(seen.get(key))), "")
    if price is None and not (gtin or seen.get("sku") or seen.get("mpn")):
        return NOTHING
    offer = Offer(
        price=price,
        currency=(seen.get("pricecurrency") or "").upper(),
        availability=availability_word(seen.get("availability")),
        sku=seen.get("sku", ""),
        gtin=gtin,
        mpn=seen.get("mpn", ""),
    )
    return PageRead(
        how="microdata",
        name=seen.get("name", ""),
        offers=(offer,),
        gtins=frozenset({gtin}) - {""},
        skus=frozenset({offer.sku}) - {""},
        mpns=frozenset({offer.mpn}) - {""},
    )


def _tags(text: str) -> tuple[dict[str, str], str]:
    meta: dict[str, str] = {}
    canonical = ""
    for match in _TAG.finditer(text):
        attrs = _attrs(match.group(0))
        if match.group(1).lower() == "link":
            if not canonical and "canonical" in attrs.get("rel", "").lower().split():
                canonical = attrs.get("href", "")
            continue
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and key not in meta and "content" in attrs:
            meta[key] = " ".join(attrs["content"].split())
    return meta, canonical


def _read_tags(meta: Mapping[str, str]) -> PageRead:
    price = amount(meta.get("product:price:amount") or meta.get("og:price:amount"))
    sku = meta.get("product:retailer_item_id", "")
    if price is None and not sku:
        return NOTHING
    offer = Offer(
        price=price,
        currency=(meta.get("product:price:currency") or meta.get("og:price:currency") or "").upper(),
        availability=availability_word(meta.get("product:availability") or meta.get("og:availability")),
        sku=sku,
    )
    return PageRead(how="tags", name=meta.get("og:title", ""), offers=(offer,), skus=frozenset({sku}) - {""})


# ---- a platform's own data ---------------------------------------------------------

_MAGENTO_INIT = re.compile(r"<script\b[^>]*\btype\s*=\s*[\"']?text/x-magento-init[\"']?[^>]*>(.*?)</script\s*>", re.I | re.S)


def _price_configs(node: Any) -> Iterator[Mapping[str, Any]]:
    if isinstance(node, dict):
        config = node.get("priceConfig")
        if isinstance(config, dict):
            yield config
        for value in node.values():
            yield from _price_configs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _price_configs(item)


def _read_magento(text: str) -> PageRead:
    """Magento's own price box (`text/x-magento-init`, its `priceConfig`): the price it
    shows, of one product only (a page listing several has several). Its stock is not
    read: Magento writes it as words, which are never guessed from (4.5.4)."""
    products: dict[str, float] = {}
    for block in _MAGENTO_INIT.findall(text):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for config in _price_configs(data):
            prices = config.get("prices") if isinstance(config.get("prices"), dict) else {}
            final = prices.get("finalPrice") if isinstance(prices.get("finalPrice"), dict) else {}
            price = amount(final.get("amount"))
            if price is not None:
                products[str(config.get("productId") or "")] = price
    if len(products) != 1:
        return NOTHING
    return PageRead(how="magento", offers=(Offer(price=next(iter(products.values()))),))


def read_page(text: str) -> PageRead:
    """What a product page's own HTML says of its product (module docstring); last, a
    platform's own structured data (Magento's price box: like Shopify's own JSON, data the
    page gives as data, never words)."""
    body = str(text or "")
    meta, canonical = _tags(body)
    for reader in (_read_json_ld, _read_microdata):
        found = reader(body)
        if found.found:
            return replace(found, canonical=canonical)
    found = _read_tags(meta)
    if not found.found:
        found = _read_magento(body)
    return replace(found, canonical=canonical)


# ---- Shopify ----------------------------------------------------------------------


def read_shopify_product(data: Mapping[str, Any], *, pence: bool) -> PageRead:
    """A Shopify product as its own JSON gives it: `/products/<name>.js` (`pence`: prices
    in pence) or a product of `/products.json` (prices as "12.99"). Its variants are its
    offers; a variant's `available` says whether it can be bought now."""
    if not isinstance(data, Mapping):
        return NOTHING
    offers = []
    for variant in data.get("variants") or ():
        if not isinstance(variant, Mapping):
            continue
        price = amount(variant.get("price"))
        if pence and price is not None:
            price = round(price / 100, 2)
        available = variant.get("available")
        offers.append(
            Offer(
                price=price,
                availability="" if available is None else ("instock" if available else "outofstock"),
                sku=_code(variant.get("sku")),
                gtin=gtin14(variant.get("barcode")),
                variant=_code(variant.get("id")),
            )
        )
    if not offers:
        return NOTHING
    return PageRead(
        how="shopify",
        name=_code(data.get("title")),
        offers=tuple(offers),
        gtins=frozenset(offer.gtin for offer in offers) - {""},
        skus=frozenset(offer.sku for offer in offers) - {""},
    )


def words(text: str) -> set[str]:
    """The words of a title, for `title_alike`."""
    return set(re.findall(r"[a-z0-9]+", html.unescape(str(text or "")).lower()))


def title_alike(feed_title: str, page_title: str, *, share: float = 0.6) -> bool:
    """Whether at least `share` of the feed title's words are on the page's (the look of
    21/11 measured 60%: six of 95 cards fell under it and were the same product, which
    is why a title alone never fails a product at its own address, rules 5.1)."""
    mine = words(feed_title)
    return bool(mine) and len(mine & words(page_title)) / len(mine) >= share


def offers_in_pounds(offers: Iterable[Offer]) -> list[Offer]:
    """The offers whose currency is pounds or not written (rules 5.3.1: pounds only)."""
    return [offer for offer in offers if offer.currency in ("", "GBP")]
