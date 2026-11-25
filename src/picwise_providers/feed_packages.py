"""The feed judged in packages (owner, 2026-11-25: «σκέψου ότι θα έχουμε να διαχειριστούμε 10
εκατομμύρια προϊόντα έρχεται ένα ενιαίο αρχείο αυτό πρέπει να χωρίζεται σε κομμάτια πρώτες
500.000 ...», and of the flow put to him: «Το αρχείο κατεβαίνει ολόκληρο και αποθηκεύεται στο
σκληρό δίσκο»; `docs/PICWISE_PACKAGES_PLAN.md`).

The night's preparation judged every row of both Awin links with every row in memory at once
(`state._resolve_provider_feed_pipeline_uncached`): the measure of 25/11 held 11.15 GB once
2,685,295 rows were judged. Here the same rows are judged with one package of them in memory at
a time, and give the same pipeline the preparation goes on from (`state._without_rows_never_shown`'s:
the eligible rows' judgements in the feed's order, the availability context of every row, the
feed's status) and the same notes (the shops' catalogues, the checks, the intake):

1. Both links read row by row (`awin_adapter.read_feed_rows_into`), never held together: each
   row normalized, the second link's kept as `awin_adapter.merge_feeds` keeps them; the steps
   that read a row at a time in the feed's order applied (its shop's catalogue,
   `shop_catalogue.CataloguesRun.row`; the checks' decisions, `checks_applied.ChecksRun.row`);
   what the whole feed decides counted (the barcodes, the availability context); each row
   written, with its place in the feed, to the bucket of its shop on disk. A shop is never in
   two buckets, and its rows stay in the feed's order.
2. A package (whole buckets, about `PACKAGE_ROWS` rows) at a time: each row given the category
   its barcode's rows write (`CataloguesRun.barcode`), its AI category read for the category's
   brake (`ChecksRun.category`), and the first category of each barcode kept for the intake.
   Then the brake is decided over every row (`ChecksRun.settle`).
3. A package at a time again: each row judged against the whole feed's availability context,
   measured for the intake, and kept only when eligible.

The rows kept are put back in the feed's order. The folder's files are removed at the end, and
when anything goes wrong.

`Fallback` says the feed cannot be read so here (a link that cannot be read, a second link whose
text is not UTF-8 or breaks mid-way): the caller reads it whole, as before, and so gives the same
status or the same failure as before.
"""
from __future__ import annotations

import json
import os
import pickle
import shutil
import sys
import tempfile
import zlib
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Collection, Iterator

from . import awin_adapter
from .checks_applied import ChecksRun
from .contracts import ProviderEligibilityResult, ProviderFeedConfig, ProviderParseResult, ProviderProduct
from .feed_intake import IntakeMeasure, _shop_name, barcode_category_of
from .normalization import normalize_feed_row_to_provider_product
from .offer_health import AvailabilityContextBuilder, FeedAvailabilityContext
from .shop_catalogue import CataloguesRun

# The owner's size of a package (25/11: «πρώτες 500.000»).
PACKAGE_ROWS = 500_000
# A shop's rows go to one bucket of these, by its name; a package is whole buckets.
BUCKETS = 128
# Rows written to a bucket at once.
_FLUSH = 256
_SHARED_VALUE_CHARS = awin_adapter._SHARED_VALUE_CHARS
# A folder named here judges the feed in packages whatever the switch says (a trial).
PACKAGES_ENV = "PICWISE_FEED_PACKAGES"
# The server's folder for them (picwise-prepare.service), used when the switch is on.
PACKAGES_DIR_ENV = "PICWISE_FEED_PACKAGES_DIR"
SWITCH_FILE = Path(__file__).resolve().parents[2] / "data" / "feed_packages.json"


class Fallback(Exception):
    """The feed cannot be judged in packages here: the whole feed is read, as before."""


@dataclass
class Packaged:
    """What judging in packages gives the preparation."""

    pipeline: Any  # state.ProviderFeedPipelineResult: the eligible rows, in the feed's order
    intake: dict[str, Any] | None
    intake_error: BaseException | None
    rows: int
    packages: int
    largest_package: int
    disk_bytes: int = 0


def packages_on(path: Path = SWITCH_FILE) -> bool:
    """The switch (`data/feed_packages.json`): true when the night's feed is judged in packages."""
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("on") is True
    except (OSError, ValueError, AttributeError):
        return False


def packages_folder() -> Path | None:
    """The folder the night's packages are written in: `PACKAGES_ENV`'s when set (a trial);
    else, with the switch on, `PACKAGES_DIR_ENV`'s (the server's); None otherwise, and the feed
    is then judged whole, as before."""
    configured = str(os.environ.get(PACKAGES_ENV) or "").strip()
    if configured:
        return Path(configured)
    if not packages_on():
        return None
    folder = str(os.environ.get(PACKAGES_DIR_ENV) or "").strip()
    return Path(folder) if folder else None


def _bucket_of(product: ProviderProduct) -> int:
    raw = product.raw if isinstance(product.raw, dict) else {}
    return zlib.crc32(_shop_name(raw).encode("utf-8", "surrogatepass")) % BUCKETS


def _interned(product: ProviderProduct) -> ProviderProduct:
    """A row read back from disk with its short values shared again, as the reader shares them
    (`awin_adapter._iter_csv_records`): read back, every row holds its own copy."""
    raw = product.raw
    if not isinstance(raw, dict):
        return product
    return replace(product, raw={
        sys.intern(key): (sys.intern(value) if type(value) is str and len(value) <= _SHARED_VALUE_CHARS else value)
        for key, value in raw.items()
    })


class _Buckets:
    """The rows on disk, each shop's in one bucket, in the order they came."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.pending: list[list[tuple[int, ProviderProduct]]] = [[] for _ in range(BUCKETS)]
        self.sizes = [0] * BUCKETS
        self.written = 0

    def _path(self, bucket: int) -> Path:
        return self.folder / f"bucket-{bucket:03d}.pickle"

    def put(self, bucket: int, index: int, product: ProviderProduct) -> None:
        pending = self.pending[bucket]
        pending.append((index, product))
        self.sizes[bucket] += 1
        if len(pending) >= _FLUSH:
            self._flush(bucket)

    def _flush(self, bucket: int) -> None:
        pending = self.pending[bucket]
        if not pending:
            return
        # Compressed (a row's text is mostly words): about a third of the disk, for little time.
        data = zlib.compress(pickle.dumps(pending, protocol=pickle.HIGHEST_PROTOCOL), 1)
        with self._path(bucket).open("ab") as handle:
            handle.write(len(data).to_bytes(8, "little"))
            handle.write(data)
        self.written += len(data) + 8
        self.pending[bucket] = []

    def close(self) -> None:
        for bucket in range(BUCKETS):
            self._flush(bucket)

    def clear(self) -> None:
        for bucket in range(BUCKETS):
            self._path(bucket).unlink(missing_ok=True)
        self.pending = [[] for _ in range(BUCKETS)]
        self.sizes = [0] * BUCKETS
        self.written = 0

    def read(self, bucket: int) -> Iterator[tuple[int, ProviderProduct]]:
        path = self._path(bucket)
        if not path.exists():
            return
        with path.open("rb") as handle:
            while True:
                size = handle.read(8)
                if not size:
                    return
                yield from pickle.loads(zlib.decompress(handle.read(int.from_bytes(size, "little"))))

    def packages(self, package_rows: int) -> list[list[int]]:
        """Whole buckets, in their order, about `package_rows` rows a package; a bucket larger
        than that is a package of its own."""
        groups: list[list[int]] = []
        current: list[int] = []
        size = 0
        for bucket, count in enumerate(self.sizes):
            if not count:
                continue
            if current and size + count > package_rows:
                groups.append(current)
                current, size = [], 0
            current.append(bucket)
            size += count
        if current:
            groups.append(current)
        return groups

    def read_package(self, buckets: Collection[int]) -> Iterator[tuple[int, ProviderProduct]]:
        for bucket in buckets:
            yield from self.read(bucket)


class _Run:
    """One night's judging in packages (module docstring)."""

    def __init__(self, folder: Path) -> None:
        self.buckets = _Buckets(folder)
        self._fresh()

    def _fresh(self) -> None:
        self.buckets.clear()
        self.catalogues = CataloguesRun()
        self.checks = ChecksRun()
        self.context = AvailabilityContextBuilder()
        self.index = 0
        self.first_shops: set[str] = set()
        self.first_ids: set[str] = set()
        self.second_added = 0
        self.taken: frozenset[int] = frozenset()

    def take(self, product: ProviderProduct) -> None:
        """A row, normalized, through the steps that read one row at a time in the feed's order."""
        product = self.catalogues.row(product)
        self.catalogues.count_barcode(product)
        if self.checks.active:
            product = self.checks.row(self.index, product)
        self.context.add(product)
        self.buckets.put(_bucket_of(product), self.index, product)
        self.index += 1

    def first_pass(self, first: ProviderFeedConfig, second: ProviderFeedConfig | None) -> tuple[str, ...]:
        """Both links read row by row (module docstring, 1); the parse result's reason codes."""
        path, errors = awin_adapter._feed_path(feed_file=first.feed_file, feed_url=first.feed_url)
        if path is None:
            raise Fallback("the first link cannot be read")
        provider_key = first.provider_key

        def take_first(record: dict[str, Any]) -> None:
            product = normalize_feed_row_to_provider_product(record, provider_key=provider_key)
            if product is None:
                return
            self.first_shops.add(awin_adapter.shop_key(product))
            self.first_ids.add(str(product.provider_product_id or "").strip())
            self.take(product)

        errors = awin_adapter.read_feed_rows_into(path, take_first, restart=self._fresh)
        if errors:
            raise Fallback("the first link's rows cannot be read")
        if not self.index:
            raise Fallback("the first link gives no product")
        codes: tuple[str, ...] = ("feed_loaded",)
        if second is None:
            return codes
        second_path, _errors = awin_adapter._feed_path(feed_file=second.feed_file, feed_url=second.feed_url)
        if second_path is None:
            return codes
        shops = set(self.first_shops)
        shops.discard("")
        keep = awin_adapter.second_row_keep_of(shops)
        second_key = second.provider_key
        taken_before = self.index

        def take_second(record: dict[str, Any]) -> None:
            product = normalize_feed_row_to_provider_product(record, provider_key=second_key)
            if product is None:
                return
            if awin_adapter.shop_key(product) in shops or str(product.provider_product_id or "").strip() in self.first_ids:
                return
            self.second_added += 1
            self.take(awin_adapter._with_aisle(product))

        def restart() -> None:
            raise Fallback("the second link is not UTF-8")

        errors = awin_adapter.read_feed_rows_into(second_path, take_second, keep=keep, restart=restart)
        if errors:
            if self.index != taken_before:
                raise Fallback("the second link broke after some of its rows")
            return codes
        return codes + (("second_feed_loaded",) if self.second_added else ())


def judge_in_packages(
    config: ProviderFeedConfig,
    *,
    folder: Path,
    second: ProviderFeedConfig | None,
    judge: Callable[..., ProviderEligibilityResult],
    status_of: Callable[..., Any],
    pipeline_of: Callable[..., Any],
    measure_intake: bool = False,
    read_kinds: Callable[[ProviderProduct], Collection[str]] | None = None,
    not_new: Callable[[ProviderProduct], bool] | None = None,
    package_rows: int | None = None,
) -> Packaged:
    """The feed judged one package at a time (module docstring). `judge` judges a row against
    the availability context (`state._enrich_provider_eligibility_result`); `status_of` gives
    the feed's status from its counts (`state.feed_status_from_counts`); `pipeline_of` makes
    the pipeline (`state.ProviderFeedPipelineResult`); `read_kinds` and `not_new`, the
    intake's (`state._pipeline_intake`'s). Raises `Fallback` when the whole feed must be read."""
    folder.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="packages-", dir=folder))
    try:
        return _judge(config, work, second=second, judge=judge, status_of=status_of, pipeline_of=pipeline_of,
                      measure_intake=measure_intake, read_kinds=read_kinds, not_new=not_new,
                      package_rows=package_rows or PACKAGE_ROWS)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _judge(config, work, *, second, judge, status_of, pipeline_of, measure_intake, read_kinds, not_new, package_rows):
    run = _Run(work)
    codes = run.first_pass(config, second)
    run.buckets.close()
    context: FeedAvailabilityContext = run.context.context()
    packages = run.buckets.packages(package_rows)
    first_category = categories_pass(run, packages, measure_intake=measure_intake)
    kept, counts, intake, intake_error = judging_pass(
        run, packages, context, first_category, judge=judge, measure_intake=measure_intake, read_kinds=read_kinds,
        not_new=not_new)
    parse_result = ProviderParseResult(status="provider_feed_loaded", products=(), reason_codes=codes)
    provider_key = str(config.provider_key or "").strip() or "unknown_provider"
    feed_status = status_of(
        provider_key=provider_key, parse_result=parse_result, product_count=sum(counts.values()),
        eligible_count=counts["eligible"], review_count=counts["needs_review"], blocked_count=counts["blocked"],
    )
    pipeline = pipeline_of(feed_status=feed_status, parse_result=parse_result, eligibility_results=kept,
                           availability_context=context)
    return Packaged(
        pipeline=pipeline,
        intake=intake,
        intake_error=intake_error,
        rows=run.index,
        packages=len(packages),
        largest_package=max((sum(run.buckets.sizes[bucket] for bucket in package) for package in packages), default=0),
        disk_bytes=run.buckets.written,
    )


def categories_pass(run: _Run, packages: list[list[int]], *, measure_intake: bool) -> dict[str, tuple[int, str]]:
    """2 (module docstring): a package at a time, the barcodes' categories given, the AI's
    category read, the first category of each barcode kept; then the category's brake over
    every row and the shops' catalogues' note. Returns each barcode's first category, with
    the place of its row."""
    catalogues, checks = run.catalogues, run.checks
    first_category: dict[str, tuple[int, str]] = {}
    for package in packages:
        for index, product in run.buckets.read_package(package):
            product = catalogues.barcode(product)
            if checks.active:
                checks.remark(index, product)
                if checks.needs_category(product):
                    checks.category(index, product)
            if measure_intake:
                found = barcode_category_of(product)
                if found is not None:
                    barcode, category = found
                    seen = first_category.get(barcode)
                    if seen is None or index < seen[0]:
                        first_category[barcode] = (index, category)
    run.taken = frozenset(checks.settle()) if checks.active else frozenset()
    catalogues.settle()
    return first_category


def judging_pass(run: _Run, packages: list[list[int]], context: FeedAvailabilityContext,
                 first_category: dict[str, tuple[int, str]], *, judge, measure_intake: bool, read_kinds, not_new):
    """3 (module docstring): a package at a time, each row judged against the whole feed's
    availability context, measured for the intake, kept only when eligible. Returns the kept
    rows' judgements in the feed's order, the counts by status, the intake and its error."""
    catalogues = run.catalogues
    taken = run.taken
    intake = IntakeMeasure({barcode: category for barcode, (_index, category) in first_category.items()},
                           read_kinds=read_kinds) if measure_intake else None
    intake_error: BaseException | None = None
    counts: Counter = Counter()
    kept: list[tuple[int, ProviderEligibilityResult]] = []
    for package in packages:
        for index, product in run.buckets.read_package(package):
            product = _interned(catalogues.barcode(product, count=False))
            if index in taken:
                product = ChecksRun.cut_for_category(product)
            row = judge(product, feed_ctx=context)
            counts[row.status] += 1
            if intake is not None:
                try:
                    intake.add(row, not_new=bool(not_new and row.status == "eligible" and row.product_eligibility is not None
                                                 and row.product_eligibility.card_eligible and not_new(row.product)))
                except Exception as error:  # noted by the tool; the catalogue is prepared as before
                    intake, intake_error = None, error
            if row.status == "eligible":
                kept.append((index, row))
    kept.sort(key=lambda item: item[0])
    return tuple(row for _index, row in kept), counts, (intake.note() if intake is not None else None), intake_error
