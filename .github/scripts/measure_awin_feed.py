"""What the second Awin link, in Awin's own feed format, brings: measured before PicWise reads it.

    AWIN_FEED_URL=... AWIN_FEED_URL_AWIN=... python3 .github/scripts/measure_awin_feed.py

Owner, 2026-11-19: the Awin-format feeds come back («εφόσον το σετ μπορεί να υποστηρίξει την
υποδομή της awin προχωράμε»). Awin keeps the two formats apart, so these shops come in a
second link, the secret AWIN_FEED_URL_AWIN, made with 187 of the 213 Awin-format feeds
offered (adult, non-pound, services and software left out). Downloaded on GitHub's runner
and read row by row, never held whole. Printed, for the owner and for the server's room:
the file's size and columns; its shops and rows; the rows priced in pounds, with a price,
with a category, in stock, with a barcode, and the rows PicWise could show (all of those
together); each shop with its rows and the rows it could show; and the shops already in
the feed in use (AWIN_FEED_URL, Google's format), by Awin's advertiser id. The links are
secrets and never printed; nothing on the server or the site changes.
"""
from __future__ import annotations

import csv
import gzip
import io
import os
import sys
import tempfile
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

LIMIT = 4 * 1024**3
_GZIP_MAGIC = b"\x1f\x8b"
csv.field_size_limit(sys.maxsize)

ID_COLUMNS = ("merchant_id", "advertiser_id")
NAME_COLUMNS = ("merchant_name", "advertiser_name")
PRICE_COLUMNS = ("search_price", "store_price", "price")
CATEGORY_COLUMNS = ("merchant_category", "category_name", "merchant_product_category_path", "google_product_category")
STOCK_COLUMNS = ("in_stock", "stock_status", "is_for_sale", "availability")
BARCODE_COLUMNS = ("ean", "product_gtin", "upc", "isbn", "mpn")
_IN_STOCK = {"1", "yes", "y", "true", "in stock", "in_stock", "instock", "available"}


def download(url: str, path: Path) -> None:
    written = 0
    with urllib.request.urlopen(url, timeout=120) as response, open(path, "wb") as handle:
        while chunk := response.read(1024 * 1024):
            written += len(chunk)
            if written > LIMIT:
                raise ValueError("larger than 4 GB")
            handle.write(chunk)
    if not written:
        raise ValueError("empty")


def why(error: Exception) -> str:
    # Only the kind of failure: a message could carry the link.
    if isinstance(error, urllib.error.HTTPError):
        return f"HTTP {error.code}"
    if isinstance(error, ValueError) and str(error) in ("larger than 4 GB", "empty", "no advertiser column"):
        return str(error)
    return type(error).__name__


def _rows(path: Path):
    with open(path, "rb") as probe:
        gzipped = probe.read(2) == _GZIP_MAGIC
    binary = gzip.open(path, "rb") if gzipped else open(path, "rb")
    with io.TextIOWrapper(binary, encoding="utf-8-sig", errors="replace", newline="") as text:
        reader = csv.reader(text)
        header = [name.strip().lower() for name in next(reader, None) or []]
        yield header
        yield from reader


def _price(text: str) -> float:
    try:
        return float(text.replace(",", "").split()[0])
    except (ValueError, IndexError):
        return 0.0


def measure(path: Path) -> dict:
    rows = _rows(path)
    header = next(rows)

    def at(names: tuple[str, ...]) -> list[int]:
        return [header.index(name) for name in names if name in header]

    def first(row: list[str], places: list[int]) -> str:
        for place in places:
            if place < len(row) and row[place].strip():
                return row[place].strip()
        return ""

    id_at, name_at = at(ID_COLUMNS), at(NAME_COLUMNS)
    if not id_at and not name_at:
        raise ValueError("no advertiser column")
    price_at, category_at = at(PRICE_COLUMNS), at(CATEGORY_COLUMNS)
    stock_at, barcode_at = at(STOCK_COLUMNS), at(BARCODE_COLUMNS)
    currency_at = at(("currency",))
    counts = Counter()
    currencies = Counter()
    shop_rows, shop_shown = Counter(), Counter()
    names: dict[str, str] = {}
    for row in rows:
        if not row:
            continue
        ident = first(row, id_at)
        name = " ".join(first(row, name_at).split())
        key = ident or name or "(no shop named)"
        names.setdefault(key, name or key)
        shop_rows[key] += 1
        counts["rows"] += 1
        currency = first(row, currency_at).upper() or "(none)"
        currencies[currency] += 1
        pounds = currency == "GBP"
        priced = _price(first(row, price_at)) > 0
        categorised = bool(first(row, category_at))
        stock = first(row, stock_at).lower()
        in_stock = stock in _IN_STOCK if stock else True
        counts["pounds"] += pounds
        counts["priced"] += priced
        counts["category"] += categorised
        counts["in_stock"] += in_stock
        counts["barcode"] += bool(first(row, barcode_at))
        if pounds and priced and categorised and in_stock:
            counts["could_show"] += 1
            shop_shown[key] += 1
    return {
        "size": path.stat().st_size,
        "columns": header,
        "counts": counts,
        "currencies": currencies,
        "shop_rows": shop_rows,
        "shop_shown": shop_shown,
        "names": names,
    }


def ids_of(path: Path) -> set[str]:
    rows = _rows(path)
    header = next(rows)
    places = [header.index(name) for name in ID_COLUMNS if name in header]
    found = set()
    for row in rows:
        for place in places:
            if place < len(row) and row[place].strip():
                found.add(row[place].strip())
                break
    return found


def main() -> int:
    url = os.environ.get("AWIN_FEED_URL_AWIN", "").strip()
    in_use = os.environ.get("AWIN_FEED_URL", "").strip()
    if not url:
        print("no Awin-format feed link (AWIN_FEED_URL_AWIN) in GitHub's secrets")
        return 1
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "feed.bin"
        try:
            download(url, path)
            info = measure(path)
        except Exception as error:  # reported by its kind only
            print(f"the Awin-format feed could not be read: {why(error)}")
            return 1
        finally:
            path.unlink(missing_ok=True)
        known: set[str] | None = None
        if in_use:
            try:
                download(in_use, path)
                known = ids_of(path)
            except Exception as error:  # reported by its kind only
                print(f"the feed in use could not be read: {why(error)}")
            finally:
                path.unlink(missing_ok=True)
    counts, total = info["counts"], info["counts"]["rows"] or 1
    print(f"the Awin-format feed: {len(info['shop_rows']):,} shops, {counts['rows']:,} rows")
    print(f"  its file: {info['size'] / 1024**2:,.1f} MB as downloaded; {len(info['columns'])} columns")
    for label, key in (
        ("priced in pounds", "pounds"), ("with a price", "priced"), ("with a category", "category"),
        ("in stock (or saying nothing)", "in_stock"), ("with a barcode", "barcode"),
    ):
        print(f"  rows {label}: {counts[key]:,} ({counts[key] / total:.1%})")
    print(f"  rows PicWise could show (pounds, a price, a category, in stock): {counts['could_show']:,} "
          f"({counts['could_show'] / total:.1%})")
    print("  currencies: " + ", ".join(f"{code} {rows:,}" for code, rows in info["currencies"].most_common()))
    shops = info["shop_rows"]
    if known is not None:
        both = [key for key in shops if key in known]
        print(f"shops already in the feed in use: {len(both):,}")
        for key in sorted(both, key=lambda key: (-shops[key], info["names"][key].lower())):
            print(f"  {shops[key]:>9,}  {info['names'][key]} ({key})")
    print("each shop of the Awin-format feed: rows, and rows it could show")
    for key in sorted(shops, key=lambda key: (-shops[key], info["names"][key].lower())):
        print(f"  {shops[key]:>9,}  {info['shop_shown'][key]:>9,}  {info['names'][key]} ({key})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
