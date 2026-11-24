"""Variant families the AI decided, and the sets it is asked about.

Owner, 2026-11-19: a shop that lists each variant of a product as a product of its own
(each colour on a page of its own) still shows as one card, «εκεί εμπλέκεται και το
σύστημα ai»; then «Το όριο του ai μπορεί να ανέβει ... δεν θα περιμένω τη νύχτα για να
κάνει το σκανάρισμα θα το κάνουμε τώρα».

The site never calls the AI (`docs/PICWISE_AI_LAYER_SPEC.md`, 4.5): after each preparation
of the catalogue `deployment/server/family_jobs.py` reads it, finds the products of one
shop and brand whose name is the same while a colour, a number or a print differs
(`product_variants.head_key`, `variant_difference`), and writes them as sets to the
folder it shares with `picwise-families`, the AI's service; each product shown by one
card per page first (its page's variants are one product already). The service answers
which of a set are one product (`picwise_ai.families`) and keeps, in one file, each
product's family. The search reads that file (`families_of`) and joins a family's
products into one card (`search_selection._join_variants`). A set the AI has not
answered stays as it is: apart.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .answer_only import answer_only
from .contracts import ProviderProduct
from .decision_labels import parse_price_amount
from .normalization import extract_merchant_name
from .product_variants import DOUBTFUL, head_key, page_key, sizes_apart_key, tail_key, variant_difference

FAMILIES_FILE_ENV = "PICWISE_FAMILIES_FILE"
FAMILIES_NAME = "families.json"
# A set holds at most this many listings, each the cheapest of its page and of those only
# sizes apart: more is a family key too broad to be one product ("Fixturon T-Shirt" for a
# shop's every print).
SET_MOST = 40
# Sets in one job, one call of the AI, and the listings they hold at most: a call's
# answer must fit the answer's room (`picwise_ai.families.MAX_TOKENS`).
SETS_PER_JOB = 25
LISTINGS_PER_JOB = 250
# How often the search looks at the file again.
_RECHECK_SECONDS = 30.0


def product_ref(product: ProviderProduct) -> str:
    """A product as the families file names it: its shop and its id."""
    raw = product.raw if isinstance(product.raw, Mapping) else {}
    shop = (extract_merchant_name(raw) or str(raw.get("merchant_id") or "")).strip().lower()
    return f"{shop}\x1f{str(product.provider_product_id or '').strip()}"


class _Families:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._path = ""
        self._mtime = -1.0
        self._checked = 0.0
        self._families: dict[str, str] = {}

    def get(self) -> dict[str, str]:
        path = os.environ.get(FAMILIES_FILE_ENV, "").strip()
        if not path:
            return {}
        now = time.monotonic()
        with self._lock:
            if path == self._path and now - self._checked < _RECHECK_SECONDS:
                return self._families
            self._checked = now
            try:
                mtime = os.stat(path).st_mtime
            except OSError:
                self._path, self._mtime, self._families = path, -1.0, {}
                return self._families
            if path != self._path or mtime != self._mtime:
                try:
                    payload = json.loads(Path(path).read_text(encoding="utf-8"))
                    families = payload.get("families") if isinstance(payload, dict) else None
                    self._families = (
                        {str(key): str(value) for key, value in families.items()}
                        if isinstance(families, dict)
                        else {}
                    )
                except (OSError, ValueError):
                    self._families = {}
                self._path, self._mtime = path, mtime
            return self._families


_FAMILIES = _Families()


@answer_only
def families_of() -> dict[str, str]:
    """Each product's family as the AI decided it (`product_ref` to a family id); empty
    with no file (`PICWISE_FAMILIES_FILE`) or before the first answer."""
    return _FAMILIES.get()


def _shop(product: ProviderProduct) -> str:
    return product_ref(product).split("\x1f", 1)[0]


@answer_only
def doubtful_sets(products: Iterable[ProviderProduct]) -> list[dict[str, Any]]:
    """The sets the AI is asked about: per shop, brand and the own words of the title's
    head (`head_key`: the name before " - ", " | " or ", "; the whole title without one),
    the products, each the cheapest of its page and of those only sizes apart, when a
    colour, a number or the words after the head tell some of them apart. Each set with
    its id (the same products and titles, the same id, so that it is asked once)."""
    by_key: dict[str, dict[str, tuple[float, ProviderProduct, list[str]]]] = defaultdict(dict)
    for product in products:
        raw = product.raw if isinstance(product.raw, Mapping) else {}
        shop = _shop(product)
        key = head_key(shop=shop, brand=str(product.brand or ""), title=str(product.title or ""))
        if not key:
            continue
        price = parse_price_amount(product.price_text)
        if price is None:
            continue
        unit = page_key(raw) or f"product:{product.provider_product_id}"
        units = by_key[key]
        ref = product_ref(product)
        held = units.get(unit)
        if held is None:
            units[unit] = (price, product, [ref])
        else:
            held[2].append(ref)
            if price < held[0]:
                units[unit] = (price, product, held[2])
    # A product alone under its head key joins the others of its model (`tail_key`): one
    # shop's colours named before the name, in words no list of colours holds (owner,
    # 2026-11-24, Fila UK). Each product stays in one set, so that no two answers split it.
    moves: list[tuple[str, str]] = []
    for key, units in by_key.items():
        if len(units) != 1:
            continue
        product = next(iter(units.values()))[1]
        tail = tail_key(shop=_shop(product), brand=str(product.brand or ""), title=str(product.title or ""))
        if tail and tail != key:
            moves.append((key, tail))
    for key, tail in moves:
        (unit_key, held), = by_key.pop(key).items()
        units = by_key[tail]
        other = units.get(unit_key)
        if other is None:
            units[unit_key] = held
        else:
            units[unit_key] = (min(other[0], held[0]), other[1] if other[0] <= held[0] else held[1], other[2] + held[2])
    sets: list[dict[str, Any]] = []
    for key, units in by_key.items():
        if len(units) < 2:
            continue
        # Listings only sizes apart are one product at search time already
        # (`sizes_apart_key`): one listing here, the cheapest, holding all their products,
        # so that a shirt in ten colours and six sizes is a set of ten, not sixty.
        merged: dict[str, tuple[float, ProviderProduct, list[str]]] = {}
        for unit_key, (price, product, refs) in units.items():
            apart = sizes_apart_key(
                shop=_shop(product), brand=str(product.brand or ""), title=str(product.title or "")
            ) or unit_key
            held = merged.get(apart)
            if held is None:
                merged[apart] = (price, product, list(refs))
            elif price < held[0]:
                merged[apart] = (price, product, held[2] + refs)
            else:
                merged[apart] = (held[0], held[1], held[2] + refs)
        if not 2 <= len(merged) <= SET_MOST:
            continue
        listed = sorted(merged.values(), key=lambda unit: (unit[0], str(unit[1].title)))
        titles = [str(unit[1].title or "") for unit in listed]
        if not any(
            variant_difference(first, second) == DOUBTFUL
            for index, first in enumerate(titles)
            for second in titles[index + 1:]
        ):
            continue
        digest = hashlib.sha256()
        for unit in listed:
            digest.update(f"{unit[1].title}\x1e{','.join(sorted(unit[2]))}\x1d".encode("utf-8"))
        sets.append(
            {
                "id": digest.hexdigest()[:24],
                "brand": str(listed[0][1].brand or ""),
                "listings": [
                    {"title": str(unit[1].title or ""), "price": f"{unit[0]:.2f}", "products": sorted(unit[2])}
                    for unit in listed
                ],
            }
        )
    sets.sort(key=lambda found: found["id"])
    return sets


def answered_set_ids(sets_file: Path) -> set[str]:
    """The sets the AI has answered, as its file of sets keeps them (`sets.json`)."""
    try:
        payload = json.loads(Path(sets_file).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    sets = payload.get("sets") if isinstance(payload, dict) else None
    return set(sets) if isinstance(sets, dict) else set()


def write_jobs(sets: list[dict[str, Any]], jobs_dir: Path, *, answered: set[str]) -> int:
    """Write the sets not answered yet as jobs, `SETS_PER_JOB` sets and `LISTINGS_PER_JOB`
    listings a job at most, after taking away the jobs of the night before that no one
    has claimed; how many jobs were written."""
    jobs_dir = Path(jobs_dir)
    jobs_dir.mkdir(parents=True, exist_ok=True)
    for old in jobs_dir.glob("family-*.json"):
        old.unlink(missing_ok=True)
    chunks: list[list[dict[str, Any]]] = []
    listed = 0
    for found in sets:
        if found["id"] in answered:
            continue
        size = len(found.get("listings") or ())
        if not chunks or len(chunks[-1]) >= SETS_PER_JOB or listed + size > LISTINGS_PER_JOB:
            chunks.append([])
            listed = 0
        chunks[-1].append(found)
        listed += size
    written = 0
    for chunk in chunks:
        name = f"family-{chunk[0]['id']}.json"
        partial = jobs_dir / f".{name}.partial"
        partial.write_text(json.dumps({"sets": chunk}, ensure_ascii=False), encoding="utf-8")
        partial.replace(jobs_dir / name)
        written += 1
    return written
