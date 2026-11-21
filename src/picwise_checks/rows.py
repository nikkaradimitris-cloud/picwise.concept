"""A product of the catalogue as the checks know it (`verdicts.Row`), and as the
preparation writes it for the bot (`candidates.json.gz`)."""
from __future__ import annotations

from typing import Any, Mapping

from .page_reader import amount, gtin14
from .verdicts import Row


def _feed_stock(text: str) -> str:
    word = " ".join(str(text or "").lower().replace("_", " ").split())
    if word in ("in stock", "instock", "available", "1", "yes", "true"):
        return "in stock"
    if word in ("out of stock", "outofstock", "sold out", "0", "no", "false"):
        return "sold out"
    return ""


def row_of(product: Any) -> Row:
    """What the checks know of one product of the catalogue (`picwise_providers`)."""
    from picwise_providers.catalogue_cap import shop_of
    from picwise_providers.catalogue_memory import product_key
    from picwise_providers.product_identity import MPN_KEYS, valid_gtin
    from picwise_providers.shop_catalogue import own_address, product_address_name

    raw = product.raw if isinstance(product.raw, Mapping) else {}
    address = own_address(product.product_url, raw)
    handle, variant = product_address_name(address) if address else ("", "")
    skus = {str(raw.get(name) or "").strip() for name in ("merchant_product_id", "sku", "id")}
    skus.add(str(product.provider_product_id or "").strip())
    return Row(
        key=product_key(product),
        shop=shop_of(product),
        product_id=str(product.provider_product_id or ""),
        address=address,
        title=" ".join(str(product.title or "").split()),
        price=amount(product.price_text),
        currency=str(product.currency or "").upper(),
        gtin=gtin14(valid_gtin(raw)),
        mpn=next((" ".join(str(raw.get(name)).split()) for name in MPN_KEYS if str(raw.get(name) or "").strip()), ""),
        skus=frozenset(skus - {""}),
        handle=handle,
        variant=variant,
        photo=" ".join(str(product.image_url or "").split()),
        feed_stock=_feed_stock(product.availability_text),
    )


def row_record(row: Row) -> list[Any]:
    """A row as the preparation writes it for the bot (`candidates.json.gz`)."""
    return [row.key, row.shop, row.product_id, row.address, row.title, row.price, row.currency, row.gtin, row.mpn,
            sorted(row.skus), row.handle, row.variant, row.photo, row.feed_stock]


def row_from_record(values: list[Any]) -> Row:
    (key, shop, product_id, address, title, price, currency, gtin, mpn, skus, handle, variant, photo,
     feed_stock) = values
    return Row(key=key, shop=shop, product_id=product_id, address=address, title=title, price=price,
               currency=currency, gtin=gtin, mpn=mpn, skus=frozenset(skus), handle=handle, variant=variant,
               photo=photo, feed_stock=feed_stock)
