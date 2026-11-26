"""How much memory the checks' bots take to read what they ask (the checks' rules 23; owner,
2026-11-26: «Όριο μνήμης: 1,8 GB για κάθε bot», «όποιο προϊόν δεν πληροί τις προϋποθέσεις σβήνεται
αμέσως και δεν μένει να πιάνει μνήμη»), and which shops and products each of the eight asks.

    python3 tools/measure_bot_memory.py make DIR [--products 111503] [--shops 105] [--candidates 70331]
        [--cut 47007] [--ledger 261600]
    python3 tools/measure_bot_memory.py measure --catalogue PATH --checks DIR [--clones 8]

`make` writes, in DIR, a catalogue of today's size (fictional shops on `.invalid` hosts, each
product's fields as long as a real feed's), the rows the preparation names for the bot, and a
ledger. `measure` reads them, each way in a process of its own so that one does not stand in the
other's memory: the bot alone as it reads today (on its own process); each bot of its own as it
reads from 26/11 (the catalogue in a process of its own that hands back its shops' rows and ends;
its part of the ledger); the night's recording. It prints each one's peak and what it holds once
it has read, and the table of shops and products per bot. Only counts, never a link or a name of
a real shop; run on the server's own files it reads them and writes nothing.
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT, ROOT / "src", ROOT / "deployment" / "bot", ROOT / "deployment" / "server"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

# Today's catalogue (the preparation of 26/11 04:44 UTC): 111,503 products of 105 shops; the bot's
# night: 70,331 candidates; the cut ones the feed still lists, about 47,000; the ledger 261,600.
PRODUCTS, SHOPS, CANDIDATES, CUT, LEDGER = 111_503, 105, 70_331, 47_007, 261_600
# The four large shops' share of the shown, as on 26/11 (PCHUB.UK 5,707, GamingKit 8,639, Tooled Up
# 16,393, InStock UK 16,916): about 43%.
LARGE = (16_916, 16_393, 8_639, 5_707)
WORDS = ("kettle", "stainless", "steel", "cordless", "rapid", "boil", "litre", "white", "black", "silver",
         "digital", "smart", "compact", "premium", "classic", "edition", "pack", "set", "home", "kitchen")


def _text(rng: random.Random, words: int) -> str:
    return " ".join(rng.choice(WORDS) for _ in range(words))


def _products(count: int, shops: int, rng: random.Random, start: int = 0):
    from picwise_providers.contracts import ProviderProduct

    sizes = list(LARGE) + [max(1, (count - sum(LARGE)) // max(1, shops - len(LARGE)))] * (shops - len(LARGE))
    made = 0
    for shop_number, size in enumerate(sizes):
        name = f"Fixture Shop {shop_number:03d}"
        host = f"shop{shop_number:03d}.invalid"
        for _ in range(size):
            if made >= count:
                return
            number = start + made
            made += 1
            raw = {
                "id": f"S{shop_number:03d}-{number}", "title": _text(rng, 12), "description": _text(rng, 110),
                "link": f"https://{host}/products/{_text(rng, 5).replace(' ', '-')}-{number}?variant={number}",
                "image_link": f"https://cdn.{host}/files/{number}/{_text(rng, 3).replace(' ', '_')}.jpg?v=1700000000",
                "additional_image_link": ",".join(f"https://cdn.{host}/files/{number}/extra{n}.jpg" for n in range(3)),
                "availability": "in stock", "price": f"{rng.randint(5, 900)}.99 GBP", "brand": _text(rng, 1).title(),
                "gtin": f"50{number:011d}", "mpn": f"MPN-{number}", "condition": "new",
                "google_product_category": "Home & Garden > Kitchen & Dining > Kitchen Appliances",
                "product_type": "Home > Kitchen > " + _text(rng, 2).title(), "merchant_name": name,
                "advertiser_id": str(10_000 + shop_number), "item_group_id": f"G{number // 4}",
                "color": rng.choice(("Black", "White", "Silver")), "size": rng.choice(("S", "M", "L", "")),
            }
            yield ProviderProduct(
                provider_key="awin", provider_product_id=raw["id"], title=raw["title"], brand=raw["brand"],
                category_text=raw["google_product_category"], product_url=raw["link"], image_url=raw["image_link"],
                price_text=raw["price"].split()[0], availability_text="in stock", currency="GBP", raw=raw)


def make(folder: Path, *, products: int, shops: int, candidates: int, cut: int, ledger: int) -> None:
    from picwise_checks import ledger as L
    from picwise_checks.rows import row_of, row_record
    from picwise_providers.contracts import ProviderFeedStatus
    from picwise_providers.offer_health import build_feed_availability_context
    from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue

    rng = random.Random(26)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "checks").mkdir(exist_ok=True)
    shown = tuple(_products(products, shops, rng))
    kinds = tuple(frozenset({rng.choice(("kettle", "toaster", "blender", "microwave", "air_fryer", ""))} - {""})
                  for _ in shown)
    prepared = PreparedCatalogue(
        prepared_at=datetime.now(timezone.utc),
        feed_status=ProviderFeedStatus(status="ok", provider_key="awin", product_count=len(shown)),
        availability_context=build_feed_availability_context(shown), products=shown,
        non_new=("",) * len(shown), kinds=kinds, eligible_count=len(shown), shop_count=shops, suggestions=())
    size = write_prepared_catalogue(prepared, folder / "catalogue.json.gz")
    rows = [row_of(product) for product in shown]
    del prepared
    extra = [row_of(product) for product in _products(candidates + cut, shops, rng, start=products)]
    with gzip.open(folder / "checks" / L.CANDIDATES_NAME, "wt", encoding="utf-8") as handle:
        json.dump({"rows": [row_record(row) for row in extra], "candidates": [row.key for row in extra[:candidates]]},
                  handle)
    held = L.Ledger()
    for row in (rows + extra)[:ledger]:
        held.products[row.key] = L.Product(shop=row.shop, state="passed", asked="2026-11-26", passed_on="2026-11-26",
                                           site_price=f"{row.price or 0:.2f}", feed_price=f"{row.price or 0:.2f}",
                                           price_on="2026-11-26", sig=L.row_signature(row))
    number = len(rows) + len(extra)
    while len(held.products) < ledger:
        held.products[f"gone|{number}"] = L.Product(shop=f"Fixture Shop {number % shops:03d}", state="failed",
                                                    reason="gone", fails=2, due="2026-12-20")
        number += 1
    for row in rows:
        held.shop(row.shop)
    L.save(held, folder / "checks" / L.LEDGER_NAME)
    print(f"made: {len(shown):,} products shown of {shops} shops ({size / 1e6:.1f} MB), "
          f"{candidates:,} candidates and {cut:,} cut ones listed, a ledger of {len(held.products):,}")


def _rss_mb() -> float:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024.0
    except OSError:
        pass
    return 0.0


def one(catalogue: Path, checks: Path, way: str, number: int, clones: int) -> dict:
    """One reading, in this process: `alone` as the bot alone reads today, `bot` as bot `number` reads
    from 26/11, `record` as the night's recording reads."""
    from picwise_checks import bot_rows as B
    from picwise_checks import ledger as L

    began = time.perf_counter()
    if way == "alone":
        rows, parts, shared, orders, dearer = B.catalogue_rows(catalogue, order=True)
        extra, named = B.candidate_rows(checks / L.CANDIDATES_NAME)
        for key, row in extra.items():
            rows.setdefault(key, row)
        held = L.load(checks / L.LEDGER_NAME)
        kept = {"rows": len(rows), "ledger": len(held.products)}
        read = 0.0
    elif way == "bot":
        found = B.read_apart(catalogue, checks / L.CANDIDATES_NAME, order=True, clones=clones, chosen=(number,),
                             say=print, ledger=checks / L.LEDGER_NAME)
        kept = {"rows": len(found.rows), "ledger": len(found.ledger.products), "shops": len(found.shops)}
        read = found.read_peak_mb
    else:
        found = B.read_apart(catalogue, checks / L.CANDIDATES_NAME, order=False, clones=0, chosen=(), say=print)
        held = L.load(checks / L.LEDGER_NAME)
        kept = {"rows": len(found.rows), "ledger": len(held.products)}
        read = found.read_peak_mb
    return {"way": way, "bot": number, **kept, "seconds": round(time.perf_counter() - began, 1),
            "peak_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0),
            "holds_mb": round(_rss_mb()), "reading_peak_mb": round(read)}


def measure(catalogue: Path, checks: Path, clones: int) -> None:
    from picwise_checks import bot_rows as B
    from picwise_checks import ledger as L

    def apart(*arguments: str) -> dict:
        done = subprocess.run([sys.executable, __file__, "one", "--catalogue", str(catalogue), "--checks", str(checks),
                               *arguments], capture_output=True, text=True, check=True)
        return json.loads(done.stdout.strip().splitlines()[-1])

    print("== each way read in a process of its own (MB: the process's peak, what it holds once it has read, "
          "the peak of the process the catalogue was read in)")
    lines = [apart("--way", "alone"), apart("--way", "record")]
    lines += [apart("--way", "bot", "--bot", str(number), "--clones", str(clones)) for number in range(1, clones + 1)]
    for line in lines:
        name = {"alone": "the bot alone, as today", "record": "the night's recording"}.get(line["way"], f"bot {line['bot']}")
        print(f"{name}: {line['rows']:,} rows, ledger {line['ledger']:,}"
              + (f", {line['shops']} shops" if "shops" in line else "")
              + f"; peak {line['peak_mb']:,} MB, holds {line['holds_mb']:,} MB, its reading's peak "
              f"{line['reading_peak_mb']:,} MB; {line['seconds']} s")
    bots = [line for line in lines if line["way"] == "bot"]
    if bots:
        print(f"the {len(bots)} bots: the most one holds {max(line['holds_mb'] for line in bots):,} MB, together "
              f"{sum(line['holds_mb'] for line in bots):,} MB; the largest reading {max(line['reading_peak_mb'] for line in bots):,} MB "
              "(one at a time: each bot starts its reading 75 s after the one before it)")
    found = B.read_bot_rows(catalogue, checks / L.CANDIDATES_NAME, clones=clones)
    table = B.table(found.rows, found.shown, found.candidates, found.bot_of, clones)
    print("== the shops and products per bot (shown, candidates; by their number at Awin or by name; the largest shop)")
    mean = sum(entry["shown"] for entry in table) / max(1, len(table))
    for entry in table:
        print(f"bot {entry['bot']}: {entry['shops']} shops ({entry['by_number']} by number, {entry['by_name']} by name), "
              f"shown {entry['shown']:,}, candidates {entry['candidates']:,}; the largest: "
              f"{entry['largest'][0] or '-'} {entry['largest'][1]:,}"
              + ("; OVER TWICE THE MEAN" if entry["shown"] > 2 * mean else ""))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="what", required=True)
    made = sub.add_parser("make")
    made.add_argument("folder", type=Path)
    made.add_argument("--products", type=int, default=PRODUCTS)
    made.add_argument("--shops", type=int, default=SHOPS)
    made.add_argument("--candidates", type=int, default=CANDIDATES)
    made.add_argument("--cut", type=int, default=CUT)
    made.add_argument("--ledger", type=int, default=LEDGER)
    measured = sub.add_parser("measure")
    measured.add_argument("--catalogue", type=Path, required=True)
    measured.add_argument("--checks", type=Path, required=True)
    measured.add_argument("--clones", type=int, default=8)
    single = sub.add_parser("one")
    single.add_argument("--catalogue", type=Path, required=True)
    single.add_argument("--checks", type=Path, required=True)
    single.add_argument("--way", choices=("alone", "bot", "record"), required=True)
    single.add_argument("--bot", type=int, default=0)
    single.add_argument("--clones", type=int, default=8)
    args = parser.parse_args(argv)
    if args.what == "make":
        make(args.folder, products=args.products, shops=args.shops, candidates=args.candidates, cut=args.cut,
             ledger=args.ledger)
    elif args.what == "measure":
        measure(args.catalogue, args.checks, args.clones)
    else:
        print(json.dumps(one(args.catalogue, args.checks, args.way, args.bot, args.clones)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
