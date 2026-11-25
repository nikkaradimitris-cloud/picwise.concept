"""Where the night's preparation spends its memory, step by step (read-only).

    PICWISE_MEMORY_STEPS=1 python tools/measure_prepare_memory.py --feed-file feed.bin --out /tmp/x/catalogue.json.gz

Runs `tools/prepare_catalogue.py` as the night runs it, with each of its large steps
wrapped so that after the step it prints the process's memory now (after a full
collection) and its peak so far, and how many rows or products the step returned. Nothing
the preparation decides changes: the wrappers call the same functions with the same
arguments and hand back what they return.

Written on 2026-11-25 for the owner's «Να χειρίζονται σε πακέτα τα προϊόντα»: before the
preparation is cut into packages of shops, which step holds the memory. It prints counts
and step names only, never the feed's link nor a row's text (the repository and its
workflow logs are public).
"""
from __future__ import annotations

import functools
import gc
import importlib.util
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (str(ROOT), str(SRC)):
    if path not in sys.path:
        sys.path.insert(0, path)

_START = time.monotonic()


def _status_kb(name: str) -> int:
    try:
        with open("/proc/self/status", encoding="ascii") as status:
            for line in status:
                if line.startswith(name + ":"):
                    return int(line.split()[1])
    except OSError:
        pass
    return 0


def _size(value: object) -> str:
    """How many rows or products a step returned, when it says so; else nothing."""
    for candidate in (value, getattr(value, "products", None), getattr(value, "eligibility_results", None)):
        if isinstance(candidate, tuple) and len(candidate) == 2 and isinstance(candidate[0], list):
            candidate = candidate[0]
        try:
            return f", {len(candidate):,} items"  # type: ignore[arg-type]
        except TypeError:
            continue
    return ""


def report(step: str, value: object = None) -> None:
    gc.collect()
    now = _status_kb("VmRSS") / 1048576
    peak = _status_kb("VmHWM") / 1048576
    print(
        f"memory step: {step}: now {now:.2f} GB, peak {peak:.2f} GB, "
        f"{time.monotonic() - _START:.0f} s{_size(value)}",
        flush=True,
    )


def _wrap(module: object, name: str, step: str) -> None:
    original = getattr(module, name)

    @functools.wraps(original)
    def wrapped(*args, **kwargs):
        value = original(*args, **kwargs)
        report(step, value)
        return value

    setattr(module, name, wrapped)


def install() -> None:
    from picwise_providers import awin_adapter, category_scope, kind_itself, prepared_catalogue, state

    _wrap(awin_adapter, "_read_feed_rows", "a link's rows read")
    _wrap(awin_adapter, "_load_awin_provider_feed_uncached", "a link's rows made products")
    _wrap(awin_adapter, "merge_feeds", "the two links merged")
    _wrap(state, "load_awin_provider_feed", "the feed loaded")
    _wrap(state, "apply_shop_catalogues", "the shops' own catalogues applied")
    _wrap(state, "apply_checks", "the checks applied")
    _wrap(state, "build_feed_availability_context", "the availability context")
    _wrap(state, "_resolve_provider_feed_pipeline_uncached", "the pipeline (every row judged)")
    _wrap(state, "_search_catalogue", "the search catalogue of every eligible product")
    _wrap(category_scope, "settle_or_keep", "the categories' list read")
    _wrap(state, "build_search_catalogue", "a search catalogue rebuilt")
    _wrap(kind_itself, "settle_catalogue", "the kinds read")
    _wrap(state, "_catalogue_kind_choices", "the kinds' choices")
    _wrap(state, "build_brand_list", "the brands")
    _wrap(state, "build_search_suggestions", "the suggestions")
    _wrap(state, "_prepare_feed_catalogue", "the catalogue prepared")
    _wrap(prepared_catalogue, "write_prepared_catalogue", "the file written")


def main(argv: list[str] | None = None) -> int:
    install()
    report("started")
    spec = importlib.util.spec_from_file_location("prepare_catalogue", ROOT / "tools" / "prepare_catalogue.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    original_cap = module._Cap.__call__

    def cap_call(self, products, kinds, feed_ctx):
        report("before the cap", products)
        keep = original_cap(self, products, kinds, feed_ctx)
        report("the cap decided", keep)
        return keep

    module._Cap.__call__ = cap_call
    code = module.main(argv)
    report("done")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
