"""The catalogue's memory: what PicWise has seen of each product, night after night.

The owner, 12/11: «Προχώρα στην υλοποίηση στη μνήμη του καταλόγου ...», then «Ναι,
προχώρα με όλα». Each night's preparation rebuilds the catalogue from nothing, and no
feed sends a date of update or a stock quantity for any product (the night's note of
12/11: 0 of 245,894), so nothing knew how long a product had been listed, when it went
away, or how its price moved. The Google pages spec's 30-day rule, a true `lastmod`,
the lowest price of 30 days, and a shop's broken feed keeping last night's rows all
need this.

One SQLite file, named to the night's preparation (`tools/prepare_catalogue.py
--memory`, or `PICWISE_CATALOGUE_MEMORY_FILE`; on the server
`/srv/picwise/shared/prepared/catalogue_memory.sqlite`), written after the catalogue: of
the products the site answers from (those the cap keeps),

- `products`: per product (a shop and its product id), the first and the last night
  seen, how many nights, its price and currency, the night its price last changed, its
  barcode, its title;
- `prices`: a product's price on the night it was first seen and on each night it
  changed (not every night);
- `shop_nights`: per shop and night, its rows in the feed, shown, kept;
- `nights`: per night, when it was prepared and how many products were kept.

A product the cap leaves out one night and keeps the next is seen on the nights it was
kept. A second preparation in one night (a deployment's, then the night's) counts the
night once. No link is kept: an Awin link carries the account. A failure here never
fails the preparation; it is only noted.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .contracts import ProviderProduct
from .decision_labels import parse_price_amount
from .normalization import extract_merchant_name
from .product_identity import valid_gtin

MEMORY_FILE_ENV = "PICWISE_CATALOGUE_MEMORY_FILE"
NO_SHOP = "(no shop named)"
_TITLE_LENGTH = 300

_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS products (
        key TEXT PRIMARY KEY,
        shop TEXT NOT NULL,
        product_id TEXT NOT NULL,
        gtin TEXT NOT NULL,
        title TEXT NOT NULL,
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL,
        nights_seen INTEGER NOT NULL,
        price_pence INTEGER,
        currency TEXT NOT NULL,
        price_changed_on TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS products_last_seen ON products (last_seen)",
    "CREATE INDEX IF NOT EXISTS products_gtin ON products (gtin)",
    """CREATE TABLE IF NOT EXISTS prices (
        key TEXT NOT NULL,
        night TEXT NOT NULL,
        price_pence INTEGER,
        currency TEXT NOT NULL,
        PRIMARY KEY (key, night)
    )""",
    """CREATE TABLE IF NOT EXISTS shop_nights (
        shop TEXT NOT NULL,
        night TEXT NOT NULL,
        rows INTEGER NOT NULL,
        shown INTEGER NOT NULL,
        kept INTEGER NOT NULL,
        PRIMARY KEY (shop, night)
    )""",
    """CREATE TABLE IF NOT EXISTS nights (
        night TEXT PRIMARY KEY,
        prepared_at TEXT NOT NULL,
        kept INTEGER NOT NULL
    )""",
)


def configured_memory_path() -> Path | None:
    """The memory named by `PICWISE_CATALOGUE_MEMORY_FILE`, or None: without one, a
    preparation (Vercel's build, a test, a speed measure) keeps no memory."""
    configured = str(os.environ.get(MEMORY_FILE_ENV) or "").strip()
    return Path(configured) if configured else None


def product_key(product: ProviderProduct) -> str:
    """A product in the memory: its shop and its id in the feed."""
    return f"{_shop(product)}\x1f{product.provider_product_id}"


def _shop(product: ProviderProduct) -> str:
    raw = product.raw if isinstance(product.raw, Mapping) else {}
    return " ".join(str(extract_merchant_name(raw) or "").split()) or NO_SHOP


def _pence(product: ProviderProduct) -> int | None:
    amount = parse_price_amount(product.price_text)
    return None if amount is None else int(round(amount * 100))


def _row(product: ProviderProduct) -> tuple[str, str, str, str, str, int | None, str]:
    raw = product.raw if isinstance(product.raw, Mapping) else {}
    gtin = valid_gtin(raw)
    title = " ".join(str(product.title or "").split())[:_TITLE_LENGTH]
    return (
        product_key(product),
        _shop(product),
        str(product.provider_product_id),
        gtin.zfill(14) if gtin else "",
        title,
        _pence(product),
        str(product.currency or "").strip().upper(),
    )


def remember_night(
    path: Path,
    products: Sequence[ProviderProduct],
    *,
    prepared_at: datetime,
    intake: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write one night's catalogue into the memory at `path`; what the memory now says,
    for the night's public note (counts only)."""
    night = prepared_at.astimezone(timezone.utc).date().isoformat()
    tonight = {row[0]: row for row in (_row(product) for product in products)}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(str(path), timeout=60)) as db:
        with db:
            for statement in _SCHEMA:
                db.execute(statement)
            before = db.execute("SELECT MAX(night) FROM nights WHERE night < ?", (night,)).fetchone()[0]
            db.execute("CREATE TEMP TABLE tonight (key TEXT PRIMARY KEY, shop TEXT, product_id TEXT, gtin TEXT, title TEXT, price_pence INTEGER, currency TEXT)")
            db.executemany("INSERT INTO tonight VALUES (?, ?, ?, ?, ?, ?, ?)", tonight.values())
            # A price is written the night a product is first seen and each night it changes
            # (a second preparation of the night that reads another price replaces the night's).
            db.execute(
                """INSERT OR REPLACE INTO prices (key, night, price_pence, currency)
                   SELECT t.key, ?, t.price_pence, t.currency FROM tonight t
                   LEFT JOIN products p ON p.key = t.key
                   WHERE p.key IS NULL OR p.price_pence IS NOT t.price_pence OR p.currency != t.currency""",
                (night,),
            )
            db.execute(
                """INSERT INTO products (key, shop, product_id, gtin, title, first_seen, last_seen, nights_seen,
                                         price_pence, currency, price_changed_on)
                   SELECT key, shop, product_id, gtin, title, ?, ?, 1, price_pence, currency, NULL FROM tonight WHERE true
                   ON CONFLICT (key) DO UPDATE SET
                       nights_seen = products.nights_seen + (products.last_seen < excluded.last_seen),
                       price_changed_on = CASE
                           WHEN products.price_pence IS NOT excluded.price_pence OR products.currency != excluded.currency
                           THEN excluded.last_seen ELSE products.price_changed_on END,
                       last_seen = excluded.last_seen,
                       shop = excluded.shop, gtin = excluded.gtin, title = excluded.title,
                       price_pence = excluded.price_pence, currency = excluded.currency""",
                (night, night),
            )
            db.execute(
                "INSERT OR REPLACE INTO nights (night, prepared_at, kept) VALUES (?, ?, ?)",
                (night, prepared_at.astimezone(timezone.utc).isoformat(timespec="seconds"), len(tonight)),
            )
            kept_by_shop: dict[str, int] = {}
            for row in tonight.values():
                kept_by_shop[row[1]] = kept_by_shop.get(row[1], 0) + 1
            shops = {
                str(entry.get("shop") or NO_SHOP): (int(entry.get("rows") or 0), int(entry.get("shown") or 0))
                for entry in ((intake or {}).get("shops") or [])
                if isinstance(entry, Mapping)
            }
            db.executemany(
                "INSERT OR REPLACE INTO shop_nights (shop, night, rows, shown, kept) VALUES (?, ?, ?, ?, ?)",
                [
                    (shop, night, *shops.get(shop, (0, 0)), kept_by_shop.get(shop, 0))
                    for shop in sorted(set(shops) | set(kept_by_shop))
                ],
            )
            db.execute("DROP TABLE tonight")
        one = lambda sql, *args: db.execute(sql, args).fetchone()[0]  # noqa: E731
        summary: dict[str, Any] = {
            "file": path.name,
            "night": night,
            "nights": one("SELECT COUNT(*) FROM nights"),
            "products_known": one("SELECT COUNT(*) FROM products"),
            "seen_tonight": one("SELECT COUNT(*) FROM products WHERE last_seen = ?", night),
            "new_tonight": one("SELECT COUNT(*) FROM products WHERE first_seen = ?", night),
            "price_changed_tonight": one(
                "SELECT COUNT(*) FROM products WHERE price_changed_on = ? AND first_seen < ?", night, night
            ),
            "compared_with": before,
            "gone_since": (
                one("SELECT COUNT(*) FROM products WHERE last_seen = ?", before) if before is not None else None
            ),
        }
    return summary
