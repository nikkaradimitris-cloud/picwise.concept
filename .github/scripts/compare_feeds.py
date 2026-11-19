"""Which shops two Awin feed links hold: the one in use and a new one, compared.

    AWIN_FEED_URL=... AWIN_FEED_URL_NEW=... python3 .github/scripts/compare_feeds.py

Owner, 2026-10-31: the feed in use was made with no category chosen, any language and
every shop that has a Google feed, so they do not know which shops it holds, nor, when
they make a new link with more shops, whether the old ones are in it («πως θα ξέρω οτι
συμπεριλαμβάνονται και τα παλιότερα μέσα στο καινούργιο?»). Each link is downloaded on
GitHub's runner and read row by row, never held whole; its shops are counted by the
advertiser's id (its name when a row has no id). Printed: each feed's shops and rows,
the shops of the one in use that the new one lacks, those it keeps with over a tenth
fewer rows (a category chosen when the link was made leaves the rest of a shop out:
owner's screenshot of Awin's categories, 31/10), and the shops it adds. A new link
replaces the old only with none lacking and none shrunk. The links are secrets and
never printed; nothing on the server or the site changes. Also counted (2026-11-19), for
the feed in use: the rows that carry a sale price, how many the site takes as the shop's
price tonight, and why each other one is left (`normalization.sale_price_reading`,
the site's own rule), with the shapes of the values left as unreadable (digits as 9),
never a row. Exits 1 when the link in use
cannot be read, or the new one cannot, or lacks or shrinks a shop of the one in use.
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
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from picwise_providers.normalization import (  # noqa: E402
    SALE_DATES_UNREAD,
    SALE_PRICE_UNREAD,
    SALE_USED,
    sale_price_reading,
)

# The most a link may send: a feed of every shop is about 1-2 GB (the server takes 2 GB).
LIMIT = 4 * 1024**3
# A shop of the link in use counts as shrunk in the new one below this share of its rows;
# a shop's feed moves by a few rows from day to day.
KEPT = 0.9
_GZIP_MAGIC = b"\x1f\x8b"
csv.field_size_limit(sys.maxsize)


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


# The shop's further photos (owner, 2026-11-15: «εμφανίζουμε έως 4»): Google's column.
EXTRA_PHOTOS = "additional_image_link"


# The shop's sale price and its dates (Google's columns), and the usual price.
SALE_COLUMNS = ("price", "sale_price", "sale_price_effective_date")


def _shape(value: str) -> str:
    """A value's form with its digits as 9 and cut short: "29.99 GBP" is "99.99 GBP"."""
    return "".join("9" if char.isdigit() else char for char in value.strip())[:40] or "(empty)"


def shops_of(path: Path, seen: dict | None = None) -> tuple[Counter, dict[str, str]]:
    """Rows per shop, keyed by the advertiser's id (else its name), and each key's name.
    `seen`, when given, is filled with the feed's columns, its size, and how many rows
    carry further photos and how many."""
    with open(path, "rb") as probe:
        gzipped = probe.read(2) == _GZIP_MAGIC
    binary = gzip.open(path, "rb") if gzipped else open(path, "rb")
    with io.TextIOWrapper(binary, encoding="utf-8-sig", errors="replace", newline="") as text:
        reader = csv.reader(text)
        header = [name.strip().lower() for name in next(reader, None) or []]

        def column(*names: str) -> int | None:
            return next((header.index(name) for name in names if name in header), None)

        sale_at = {name: column(name) for name in SALE_COLUMNS}
        now = datetime.now(timezone.utc)
        sales = Counter()
        sale_shops = Counter()
        in_force_shops = Counter()
        shapes: dict[str, Counter] = {SALE_PRICE_UNREAD: Counter(), SALE_DATES_UNREAD: Counter()}
        extra_at = column(EXTRA_PHOTOS)
        with_extra = 0
        extra_links = Counter()
        id_at = column("advertiser_id", "merchant_id")
        name_at = column("advertiser_name", "merchant_name")
        if id_at is None and name_at is None:
            raise ValueError("no advertiser column")
        rows: Counter = Counter()
        names: dict[str, str] = {}
        for row in reader:
            if not row:
                continue
            ident = row[id_at].strip() if id_at is not None and id_at < len(row) else ""
            name = " ".join(row[name_at].split()) if name_at is not None and name_at < len(row) else ""
            key = ident or name or "(no shop named)"
            rows[key] += 1
            names.setdefault(key, name or key)
            if sale_at["sale_price"] is not None:
                fields = {
                    name: (row[at] if at is not None and at < len(row) else "")
                    for name, at in sale_at.items()
                }
                reason = sale_price_reading(fields, now=now)
                sales[reason] += 1
                if reason:
                    sale_shops[key] += 1
                    if reason == SALE_USED:
                        in_force_shops[key] += 1
                if reason == SALE_PRICE_UNREAD:
                    shapes[reason][_shape(fields["sale_price"])] += 1
                elif reason == SALE_DATES_UNREAD:
                    shapes[reason][_shape(fields["sale_price_effective_date"])] += 1
            if extra_at is not None and extra_at < len(row) and row[extra_at].strip():
                with_extra += 1
                links = [part for part in row[extra_at].replace(",", " ").split() if part.startswith("http")]
                extra_links[min(len(links), 4)] += 1
        if seen is not None:
            seen.update(
                columns=header,
                size=path.stat().st_size,
                with_extra=with_extra,
                extra_links=extra_links,
                sale_column=sale_at["sale_price"] is not None,
                dates_column=sale_at["sale_price_effective_date"] is not None,
                sales=sales,
                sale_shops=sale_shops,
                in_force_shops=in_force_shops,
                shapes=shapes,
            )
        return rows, names


def print_sales(info: dict, names: dict[str, str]) -> None:
    """The feed's sale prices: how many rows carry one, how many are the shop's price
    tonight by the site's rule, and why the rest are left."""
    if not info.get("sale_column"):
        print("  sale_price: not among its columns")
        return
    sales: Counter = info["sales"]
    carried = sum(count for reason, count in sales.items() if reason)
    print(
        f"  sale_price: in its columns (its dates column {'too' if info['dates_column'] else 'not'}); "
        f"rows with a sale price: {carried:,}; the shop's price tonight by the site's rule: {sales[SALE_USED]:,}"
    )
    for reason, count in sales.most_common():
        if reason and reason != SALE_USED:
            print(f"    left, {reason}: {count:,}")
    for reason, shapes in info["shapes"].items():
        for shape, count in shapes.most_common(5):
            print(f"    {reason}, written as {shape!r}: {count:,}")
    if info["sale_shops"]:
        print("  the shops with the most sale prices (rows with one; of them, the shop's price tonight):")
        for key, count in info["sale_shops"].most_common(15):
            shown = names[key] if names[key] == key else f"{names[key]} ({key})"
            print(f"    {count:>9,}  {info['in_force_shops'][key]:>9,}  {shown}")


def why(error: Exception) -> str:
    # Only the kind of failure: a message could carry the link.
    if isinstance(error, urllib.error.HTTPError):
        return f"HTTP {error.code}"
    if isinstance(error, ValueError) and str(error) in ("larger than 4 GB", "empty", "no advertiser column"):
        return str(error)
    return type(error).__name__


def listed(keys: list[str], rows: Counter, names: dict[str, str]) -> None:
    for key in sorted(keys, key=lambda key: (-rows[key], names[key].lower())):
        shown = names[key] if names[key] == key else f"{names[key]} ({key})"
        print(f"  {rows[key]:>9,}  {shown}")


def main() -> int:
    links = (
        ("in use", os.environ.get("AWIN_FEED_URL", "").strip()),
        ("new", os.environ.get("AWIN_FEED_URL_NEW", "").strip()),
    )
    read: dict[str, tuple[Counter, dict[str, str]]] = {}
    seen: dict[str, dict] = {}
    with tempfile.TemporaryDirectory() as folder:
        for label, url in links:
            if not url:
                print(f"no {label} feed link in GitHub's secrets")
                if label == "in use":
                    return 1
                continue
            path = Path(folder) / "feed.bin"
            try:
                download(url, path)
                seen[label] = {}
                read[label] = shops_of(path, seen[label])
            except Exception as error:  # reported by its kind only
                print(f"the {label} feed could not be read: {why(error)}")
                return 1
            finally:
                path.unlink(missing_ok=True)
    for label, (rows, names) in read.items():
        print(f"the {label} feed: {len(rows):,} shops, {sum(rows.values()):,} rows")
        info = seen[label]
        print(f"  its file: {info['size'] / 1024**2:,.1f} MB as downloaded; {len(info['columns'])} columns")
        if EXTRA_PHOTOS in info["columns"]:
            total = sum(rows.values()) or 1
            counts = ", ".join(
                f"{number}{'+' if number == 4 else ''} links: {info['extra_links'][number]:,}"
                for number in sorted(info["extra_links"])
            )
            print(
                f"  {EXTRA_PHOTOS}: in its columns; rows with further photos: {info['with_extra']:,} "
                f"({info['with_extra'] / total:.1%})" + (f"; {counts}" if counts else "")
            )
        else:
            print(f"  {EXTRA_PHOTOS}: not among its columns")
        print_sales(info, names)
    if "new" in seen and "in use" in seen:
        only_new = [name for name in seen["new"]["columns"] if name not in seen["in use"]["columns"]]
        only_old = [name for name in seen["in use"]["columns"] if name not in seen["new"]["columns"]]
        print(f"columns the new feed adds: {', '.join(only_new) or 'none'}")
        print(f"columns the new feed lacks: {', '.join(only_old) or 'none'}")
    old_rows, old_names = read["in use"]
    if "new" not in read:
        print("the shops of the feed in use, the most rows first:")
        listed(list(old_rows), old_rows, old_names)
        return 0
    new_rows, new_names = read["new"]
    missing = [key for key in old_rows if key not in new_rows]
    shrunk = [key for key in old_rows if key in new_rows and new_rows[key] < KEPT * old_rows[key]]
    added = [key for key in new_rows if key not in old_rows]
    print(f"shops of the feed in use that the new one lacks: {len(missing):,}")
    listed(missing, old_rows, old_names)
    print(f"shops of the feed in use that the new one keeps with over a tenth fewer rows: {len(shrunk):,}")
    for key in sorted(shrunk, key=lambda key: (-old_rows[key], old_names[key].lower())):
        shown = old_names[key] if old_names[key] == key else f"{old_names[key]} ({key})"
        print(f"  {old_rows[key]:>9,} -> {new_rows[key]:>9,}  {shown}")
    print(f"shops the new feed adds: {len(added):,}")
    listed(added, new_rows, new_names)
    print(
        "the new feed holds every shop of the one in use, with its rows" if not missing and not shrunk
        else "the new feed lacks or shrinks shops of the one in use: keep the link in use"
    )
    return 1 if missing or shrunk else 0


if __name__ == "__main__":
    sys.exit(main())
