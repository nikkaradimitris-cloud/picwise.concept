"""Write a synthetic feed about the size of the live catalogue, for speed measures only.

    python tools/bench_make_feed.py <repo checkout> <feed.csv> [copies] [plain rows]

The first of three steps (`docs/PICWISE_AUDIT_FIXES.md`, section 7).

About 40% of its rows are copies of the repository's coverage fixture (products with a
kind), each with its own id, title and price; the rest are products whose title names no
kind, as 59% of the live catalogue are. Local test data (`.invalid` addresses), never a
real listing.
"""
import csv
import random
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
OUT = Path(sys.argv[2])
COPIES = int(sys.argv[3]) if len(sys.argv) > 3 else 700
PLAIN = int(sys.argv[4]) if len(sys.argv) > 4 else 150_000

random.seed(20261110)
rows = list(csv.DictReader(open(REPO / "tests/fixtures/provider_feed_coverage_matrix_fixture.csv", encoding="utf-8")))
columns = list(rows[0].keys())
shops = [f"Bench Shop {number}" for number in range(1, 21)]
plain_words = ["Giftware", "Keepsake", "Ornament", "Novelty", "Trinket", "Bundle", "Assortment", "Selection"]
plain_shelves = ["Home & Garden > Decor", "Arts & Entertainment > Hobbies & Creative Arts", "Apparel & Accessories > Jewelry"]


def ean13(number: int) -> str:
    digits = f"{number:012d}"
    total = sum(int(digit) * (1 if place % 2 == 0 else 3) for place, digit in enumerate(digits))
    return digits + str((10 - total % 10) % 10)


with open(OUT, "w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns)
    writer.writeheader()
    serial = 0
    for copy in range(COPIES):
        for row in rows:
            serial += 1
            new = dict(row)
            new["aw_product_id"] = f"{row['aw_product_id']}-{copy}"
            new["product_name"] = f"{row['product_name']} M{copy:04d}"
            new["search_price"] = f"{float(row['search_price']) * random.uniform(0.6, 2.4):.2f}"
            new["merchant_name"] = random.choice(shops)
            new["ean"] = ean13(500_000_000_000 + serial) if copy % 2 == 0 else ""
            new["aw_deep_link"] = f"https://fixture.example.invalid/products/{new['aw_product_id']}"
            new["merchant_image_url"] = f"https://fixture.example.invalid/images/{new['aw_product_id']}.jpg"
            writer.writerow(new)
    template = rows[0]
    for number in range(PLAIN):
        serial += 1
        word = plain_words[number % len(plain_words)]
        new = dict(template)
        new["aw_product_id"] = f"bench-plain-{number}"
        new["product_name"] = f"{word} piece {number} in {random.choice(['blue', 'green', 'silver', 'oak', 'grey'])}"
        new["brand"] = f"Brand{number % 300}"
        new["merchant_category"] = plain_shelves[number % len(plain_shelves)]
        new["product_type"] = ""
        new["keywords"] = ""
        new["description"] = "Local test data for a speed measure. Not a real listing and not for sale."
        new["search_price"] = f"{random.uniform(3, 400):.2f}"
        new["merchant_name"] = random.choice(shops)
        new["ean"] = ""
        new["aw_deep_link"] = f"https://fixture.example.invalid/products/bench-plain-{number}"
        new["merchant_image_url"] = f"https://fixture.example.invalid/images/bench-plain-{number}.jpg"
        writer.writerow(new)
print(f"rows written: {serial}")
