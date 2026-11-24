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
  barcode, its title, and which of the last 62 prepared nights it was seen on
  (`seen_nights`: bit 0 its last night seen, bit 1 the prepared night before, and so
  on; a night with no preparation is not one), so that how long a price held counts
  only the nights it was seen at it (`price_history`, owner, 2026-11-13);
- `prices`: a product's price on the night it was first seen and on each night it
  changed (not every night);
- `shop_nights`: per shop and night, its rows in the feed, shown, kept;
- `nights`: per night, when it was prepared and how many products were kept;
- `meta`: `sale_prices_read_from`, the first night the memory was written with each
  product at its shop's sale price where the shop gives one (owner, 2026-11-19: «Στην
  έκπτωση τραβά στην τιμή της έκπτωσης»). Before it the price written was the shop's usual
  one, sale or not; so on that night a product whose price the sale price changes starts
  its price's history again (its earlier prices and nights forgotten for the history):
  a fall nobody can date is never told as one (`PROJECT_RULES.md` §4: no fake savings).
  From then on a sale beginning or ending is a change like any other.

A product the cap leaves out one night and keeps the next is seen on the nights it was
kept. A second preparation in one night (a deployment's, then the night's) counts the
night once. No link is kept: an Awin link carries the account. A failure here never
fails the preparation; it is only noted.
"""
from __future__ import annotations

import os
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .contracts import ProviderProduct
from .decision_labels import misread_until_mend, parse_price_amount
from .normalization import SALE_USED, extract_merchant_name, sale_price_reading
from .product_identity import valid_gtin

MEMORY_FILE_ENV = "PICWISE_CATALOGUE_MEMORY_FILE"
NO_SHOP = "(no shop named)"
_TITLE_LENGTH = 300
# `seen_nights` keeps this many prepared nights, one bit each: SQLite's integers have 64
# bits, and the sign's is left alone.
SEEN_NIGHTS_KEPT = 62
# The first night written with the shops' sale prices (owner, 2026-11-19).
SALE_PRICES_SINCE = "sale_prices_read_from"
_SEEN_MASK = (1 << SEEN_NIGHTS_KEPT) - 1

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
        price_changed_on TEXT,
        seen_nights INTEGER
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
    # The products whose price is their shop's own page's (`checks_applied`): a price
    # changing its source, feed to site or back, starts its history again (the checks'
    # rules 5.3.5): a change of source is never told as a change of price.
    """CREATE TABLE IF NOT EXISTS price_sources (
        key TEXT PRIMARY KEY,
        source TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS nights (
        night TEXT PRIMARY KEY,
        prepared_at TEXT NOT NULL,
        kept INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS meta (
        name TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""",
)


def configured_memory_path() -> Path | None:
    """The memory named by `PICWISE_CATALOGUE_MEMORY_FILE`, or None: without one, a
    preparation (Vercel's build, a test, a speed measure) keeps no memory."""
    configured = str(os.environ.get(MEMORY_FILE_ENV) or "").strip()
    return Path(configured) if configured else None


def product_key(product: ProviderProduct) -> str:
    """A product in the memory: its shop and its id in the feed."""
    return history_key(_shop(product), product.provider_product_id)


def history_key(shop: object, product_id: object) -> str:
    """The memory's key of the product a shop (as the feed's row names it) lists under
    `product_id`: what a card looks a product's price history up by."""
    return f"{' '.join(str(shop or '').split()) or NO_SHOP}\x1f{str(product_id or '').strip()}"


def _shop(product: ProviderProduct) -> str:
    raw = product.raw if isinstance(product.raw, Mapping) else {}
    return " ".join(str(extract_merchant_name(raw) or "").split()) or NO_SHOP


def _pence(product: ProviderProduct) -> int | None:
    amount = parse_price_amount(product.price_text)
    return None if amount is None else int(round(amount * 100))


def _misread(products: Sequence[ProviderProduct]) -> list[tuple[int, str, int]]:
    """(today's pence, key, the pence read before 2026-11-24) of tonight's products whose
    price the reader misread until then (`decision_labels.misread_until_mend`: "269.448001"
    as 269,448,001): the memory's prices kept under that reading are put right, the same
    price, so the mend tells no change of price (a fall of £269 million would be a fake
    saving, `PROJECT_RULES.md` §4)."""
    found = []
    for product in products:
        before = misread_until_mend(product.price_text)
        now = _pence(product)
        if before is not None and now is not None:
            found.append((now, product_key(product), int(round(before * 100))))
    return found


def _row(product: ProviderProduct, sale_reading: str) -> tuple[str, str, str, str, str, int | None, str, int]:
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
        # At its shop's sale price tonight (`normalization.sale_price_in_force`).
        1 if sale_reading == SALE_USED else 0,
    )


# The shops whose rows give a sale price, named in the night's note.
SALE_SHOPS_LISTED = 8


def _sale_prices(products: Sequence[ProviderProduct], readings: Sequence[str]) -> dict[str, Any]:
    """How many of tonight's products give a sale price, whether it is their price and
    if not why (`normalization.sale_price_reading`), and the shops that give the most:
    counts only, for the night's note (the first night read no sale price at all)."""
    reasons: Counter[str] = Counter()
    filled: Counter[str] = Counter()
    used: Counter[str] = Counter()
    for product, reading in zip(products, readings):
        if not reading:
            continue
        reasons[reading] += 1
        shop = _shop(product)
        filled[shop] += 1
        if reading == SALE_USED:
            used[shop] += 1
    return {
        "given": sum(reasons.values()),
        "readings": dict(sorted(reasons.items(), key=lambda item: (-item[1], item[0]))),
        "shops": [
            {"shop": shop, "given": count, "used": used[shop]}
            for shop, count in sorted(filled.items(), key=lambda item: (-item[1], item[0]))[:SALE_SHOPS_LISTED]
        ],
    }


def _add_seen_nights(db: sqlite3.Connection) -> None:
    """Give a memory written before `seen_nights` existed (12-13/11) its column, each
    product's from what the memory knew: seen on every prepared night from its first to
    its last when its count of nights says so, else only on its last (nothing more is
    claimed than the memory can show)."""
    columns = {row[1] for row in db.execute("PRAGMA table_info(products)")}
    if "seen_nights" in columns:
        return
    db.execute("ALTER TABLE products ADD COLUMN seen_nights INTEGER")
    db.execute(
        """UPDATE products SET seen_nights = CASE
               WHEN nights_seen = (SELECT COUNT(*) FROM nights
                                   WHERE nights.night >= products.first_seen AND nights.night <= products.last_seen)
               THEN (1 << MIN(nights_seen, ?)) - 1
               ELSE 1 END""",
        (SEEN_NIGHTS_KEPT,),
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
    products = products if isinstance(products, (list, tuple)) else list(products)
    readings = [
        sale_price_reading(product.raw if isinstance(product.raw, Mapping) else {}, now=prepared_at)
        for product in products
    ]
    tonight = {row[0]: row for row in (_row(product, reading) for product, reading in zip(products, readings))}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(str(path), timeout=60)) as db:
        with db:
            for statement in _SCHEMA:
                db.execute(statement)
            _add_seen_nights(db)
            # The prices kept under the reader's misreading until 2026-11-24, put right
            # before tonight is compared with them (`_misread`).
            misread = _misread(products)
            db.executemany("UPDATE prices SET price_pence = ? WHERE key = ? AND price_pence = ?", misread)
            db.executemany("UPDATE products SET price_pence = ? WHERE key = ? AND price_pence = ?", misread)
            before = db.execute("SELECT MAX(night) FROM nights WHERE night < ?", (night,)).fetchone()[0]
            db.execute("CREATE TEMP TABLE tonight (key TEXT PRIMARY KEY, shop TEXT, product_id TEXT, gtin TEXT, title TEXT, price_pence INTEGER, currency TEXT, on_sale INTEGER)")
            db.executemany("INSERT INTO tonight VALUES (?, ?, ?, ?, ?, ?, ?, ?)", tonight.values())
            # The first night of the shops' sale prices (owner, 2026-11-19), or a second
            # preparation of that night: a product its sale price gives another price than
            # the one remembered starts its price's history again, since the price written
            # before was the usual one whether or not the sale had begun.
            since = db.execute("SELECT value FROM meta WHERE name = ?", (SALE_PRICES_SINCE,)).fetchone()
            restarted: list[str] = []
            if since is None or since[0] == night:
                restarted = [
                    row[0]
                    for row in db.execute(
                        """SELECT t.key FROM tonight t JOIN products p ON p.key = t.key
                           WHERE t.on_sale AND (p.price_pence IS NOT t.price_pence OR p.currency != t.currency)"""
                    )
                ]
                db.executemany(
                    "DELETE FROM prices WHERE key = ? AND night < ?", [(key, night) for key in restarted]
                )
                db.execute(
                    "INSERT OR IGNORE INTO meta (name, value) VALUES (?, ?)", (SALE_PRICES_SINCE, night)
                )
            # A price whose source changed tonight, its feed's or its shop's own page's (the
            # checks' rules 5.3.5), starts its history again, as a sale price did on its first
            # night.
            db.execute("CREATE TEMP TABLE tonight_sources (key TEXT PRIMARY KEY, site INTEGER)")
            db.executemany(
                "INSERT OR REPLACE INTO tonight_sources VALUES (?, ?)",
                [
                    (product_key(product),
                     1 if (product.raw if isinstance(product.raw, Mapping) else {}).get("price_source") == "shop site"
                     else 0)
                    for product in products
                ],
            )
            switched = [
                row[0]
                for row in db.execute(
                    """SELECT t.key FROM tonight_sources t JOIN products p ON p.key = t.key
                       LEFT JOIN price_sources s ON s.key = t.key
                       WHERE t.site != (s.key IS NOT NULL)"""
                )
            ]
            db.executemany("DELETE FROM prices WHERE key = ? AND night < ?", [(key, night) for key in switched])
            db.execute(
                "INSERT OR IGNORE INTO price_sources (key, source) SELECT key, 'shop site' FROM tonight_sources WHERE site = 1"
            )
            db.execute("DELETE FROM price_sources WHERE key IN (SELECT key FROM tonight_sources WHERE site = 0)")
            already = set(restarted)
            restarted = restarted + [key for key in switched if key not in already]
            # A price is written the night a product is first seen and each night it changes
            # (a second preparation of the night that reads another price replaces the night's).
            db.execute(
                """INSERT OR REPLACE INTO prices (key, night, price_pence, currency)
                   SELECT t.key, ?, t.price_pence, t.currency FROM tonight t
                   LEFT JOIN products p ON p.key = t.key
                   WHERE p.key IS NULL OR p.price_pence IS NOT t.price_pence OR p.currency != t.currency""",
                (night,),
            )
            # Seen tonight: the nights seen move on by the prepared nights since the last
            # one seen (those between it and tonight were not seen), and tonight's is set.
            # Every expression reads the row as it was before this night.
            db.execute(
                """INSERT INTO products (key, shop, product_id, gtin, title, first_seen, last_seen, nights_seen,
                                         price_pence, currency, price_changed_on, seen_nights)
                   SELECT key, shop, product_id, gtin, title, ?, ?, 1, price_pence, currency, NULL, 1 FROM tonight
                   WHERE true
                   ON CONFLICT (key) DO UPDATE SET
                       seen_nights = CASE
                           WHEN products.last_seen < excluded.last_seen
                           THEN ((COALESCE(products.seen_nights, 1)
                                  << (1 + (SELECT COUNT(*) FROM nights
                                           WHERE nights.night > products.last_seen AND nights.night < excluded.last_seen)))
                                 | 1) & ?
                           ELSE COALESCE(products.seen_nights, 1) | 1 END,
                       nights_seen = products.nights_seen + (products.last_seen < excluded.last_seen),
                       price_changed_on = CASE
                           WHEN products.price_pence IS NOT excluded.price_pence OR products.currency != excluded.currency
                           THEN excluded.last_seen ELSE products.price_changed_on END,
                       last_seen = excluded.last_seen,
                       shop = excluded.shop, gtin = excluded.gtin, title = excluded.title,
                       price_pence = excluded.price_pence, currency = excluded.currency""",
                (night, night, _SEEN_MASK),
            )
            # Their history starts tonight: seen tonight only, no change of price told.
            db.executemany(
                "UPDATE products SET seen_nights = 1, price_changed_on = NULL WHERE key = ?",
                [(key,) for key in restarted],
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
            # At the shop's sale price tonight, and, on the first night of sale prices
            # only, how many started their price's history again (owner, 2026-11-19).
            "on_sale_tonight": sum(row[7] for row in tonight.values()),
            "history_restarted_tonight": len(restarted),
            "sale_prices": _sale_prices(products, readings),
            "gone_since": (
                one("SELECT COUNT(*) FROM products WHERE last_seen = ?", before) if before is not None else None
            ),
        }
    return summary
