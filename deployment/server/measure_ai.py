"""The AI layer's offline measure: complex searches on a copy of the server's catalogue.

The AI layer's spec (`docs/PICWISE_AI_LAYER_SPEC.md`, 4.8; owner, 2026-11-05: «ΝΑΙ» to
building it first, measured first on about 150 searches). Each search of the list runs
on the copy with this checkout's code, as the site runs it; when the page would say
"PicWise could not match" some words of a search for a kind (`picwise_ai.complex_search`),
Claude Haiku 5.5 reads up to 30 products of the answer and answers, and the code's checks
read the answer (`picwise_ai.checks`). Printed for each search: what the engine read, what
the AI answered for each product, the sentence that would be shown or why it is withheld,
the time and the cost; then the totals. Nothing on the server or the site changes.

    python3 deployment/server/measure_ai.py CATALOGUE.json.gz deployment/server/ai_measure_searches.txt \
        [--gone GONE.json] [--offers OFFERS.json] [--budget 1.00] [--limit N] [--dry-run]

The AI is asked only with `ANTHROPIC_API_KEY` set and without `--dry-run`; otherwise the
run says which searches it would be asked about. It stops asking once the calls have
cost `--budget` dollars. The repository and its logs are public: titles, brands, prices
and shops are printed, never a link, and never the key.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path

# The tags a search of the list carries: the signal it is meant to exercise, or a
# control the AI must not be asked about.
TAGS = ("words", "broader", "plain", "judgement")
EXPECT_ASKED = {"words": True, "broader": True, "plain": False, "judgement": False}
TITLE = 90
UNCLEAR_LISTED = 3


@dataclass
class Measured:
    tag: str
    search: str
    asked: bool = False
    why_not: str = ""
    kind: str = ""
    words: tuple[str, ...] = ()
    total: int = 0
    read: int = 0
    sentence: str = ""
    buttons: tuple[str, ...] = ()
    proposed: tuple[str, ...] = ()
    failure: str = ""
    error: str = ""
    yes: int = 0
    no: int = 0
    unclear: int = 0
    unproved: int = 0
    seconds: float = 0.0
    search_seconds: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    lines: list[str] = field(default_factory=list)


def read_searches(path: Path) -> list[tuple[str, str]]:
    """`tag | search` per line; `#` starts a comment."""
    searches = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        tag, separator, search = (part.strip() for part in line.partition("|"))
        if not separator or tag not in TAGS or not search:
            raise ValueError(f"{path.name}, line {number}: expected 'tag | search' with a tag of {TAGS}: {raw!r}")
        searches.append((tag, search))
    return searches


def _short(text: str, width: int = TITLE) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 1] + "…"


def measure_one(tag: str, search: str, *, resolve, ask, client, dry_run: bool, descriptions=None) -> Measured:
    """One search: the engine's answer, then the AI's when the search is complex: a
    sentence when some products fit, else the shops' words as searches the catalogue
    counts, else nothing."""
    from picwise_ai.checks import check_answer
    from picwise_ai.complex_search import SHOWN_FOR_CANDIDATES, complex_search_of, why_not_asked
    from picwise_ai.request import request_kwargs, user_message
    from picwise_ai.shop_words import verified_shop_words

    measured = Measured(tag=tag, search=search)
    began = time.monotonic()
    resolution = resolve(search, shown=SHOWN_FOR_CANDIDATES)
    measured.search_seconds = time.monotonic() - began
    measured.total = int(getattr(resolution, "provider_feed_total_count", 0) or 0)
    measured.kind = str(getattr(resolution, "understood_concept_name", "") or getattr(resolution, "understood_concept_id", "") or "")
    measured.why_not = why_not_asked(search, resolution)
    complex_search = complex_search_of(search, resolution, descriptions=descriptions)
    if complex_search is None:
        return measured
    measured.kind = complex_search.kind_name + (" (the broader kind)" if complex_search.fell_back else "")
    measured.words = complex_search.words
    measured.read = len(complex_search.candidates)
    if dry_run or client is None:
        described = sum(1 for candidate in complex_search.candidates if candidate.description)
        measured.lines.append(f"    the request: {len(user_message(complex_search)):,} characters of products,"
                              f" {described} with a description")
        return measured
    measured.asked = True
    asked = ask(request_kwargs(complex_search), client=client)
    measured.seconds = asked.seconds
    measured.tokens_in = asked.input_tokens + asked.cache_write_tokens + asked.cache_read_tokens
    measured.tokens_out = asked.output_tokens
    measured.cost = asked.cost_usd
    measured.error = asked.error
    checked = check_answer(asked.answer, complex_search, stop_reason=asked.stop_reason)
    measured.yes, measured.no, measured.unclear = len(checked.yes), len(checked.no), len(checked.unclear)
    measured.unproved = len(checked.unproved)
    measured.sentence = checked.sentence
    measured.failure = asked.error or checked.failure
    measured.proposed = tuple(str(word) for word in (asked.answer or {}).get("shop_words") or () if str(word).strip())
    if not measured.failure and not measured.sentence and checked.shop_words:
        measured.buttons = tuple(
            f"{word.word} ({word.count:,})" for word in verified_shop_words(checked.shop_words, complex_search, resolve)
        )
    if measured.proposed:
        measured.lines.append(
            f"    the shops' words proposed: {', '.join(measured.proposed)}; passed the checks:"
            f" {', '.join(checked.shop_words) or 'none'}; answered by the catalogue: {len(measured.buttons)}"
        )
    sentence = str((asked.answer or {}).get("sentence") or "")
    if not checked.shown and sentence:
        measured.lines.append(f"    the sentence written: {sentence}")
    by_number = {candidate.number: candidate for candidate in complex_search.candidates}
    proof = dict(checked.proof)
    given = {
        verdict.get("n"): " ".join(str(verdict.get("words") or "").split())
        for verdict in (asked.answer or {}).get("verdicts") or ()
        if isinstance(verdict, dict)
    }
    still_unclear = tuple(number for number in checked.unclear if number not in checked.unproved)
    for verdict, numbers, limit in (
        ("yes", checked.yes, None), ("unproved", checked.unproved, None), ("no", checked.no, None),
        ("unclear", still_unclear, UNCLEAR_LISTED),
    ):
        for number in numbers[:limit]:
            candidate = by_number[number]
            measured.lines.append(
                f"    {verdict:7} {number:2}. {_short(candidate.title)} | {candidate.price_text} | {_short(candidate.shop, 30)}"
            )
            if verdict == "yes":
                measured.lines.append(f"               its words: {proof.get(number, '')}")
            elif verdict == "unproved":
                measured.lines.append(f"               its words, not in the product: {given.get(number, '') or '(none)'}")
        if limit is not None and len(numbers) > limit:
            measured.lines.append(f"    {verdict:7} … and {len(numbers) - limit} more")
    return measured


def print_measured(index: int, measured: Measured) -> None:
    print()
    print(f"[{index}] {measured.tag} | {measured.search}")
    if not measured.words:
        print(f"    not asked: {measured.why_not or 'not complex'}; read as {measured.kind or 'no kind'};"
              f" {measured.total:,} products ({measured.search_seconds:.1f} s)")
        return
    print(f"    read as {measured.kind}; {measured.total:,} products, {measured.read} read;"
          f" asked about: {', '.join(measured.words)}")
    if measured.asked:
        if measured.sentence:
            print(f"    SHOWN: {measured.sentence}")
        elif measured.failure:
            print(f"    WITHHELD: {measured.failure}")
        elif measured.buttons:
            print(f"    BUTTONS: {' · '.join(measured.buttons)}")
        else:
            print("    NOTHING: no product fits and no word of the shops to offer")
        print(f"    yes {measured.yes}, no {measured.no}, unclear {measured.unclear}"
              + (f" ({measured.unproved} a yes without its words in the product)" if measured.unproved else "") + ";"
              f" {measured.seconds:.1f} s; {measured.tokens_in:,} tokens in, {measured.tokens_out:,} out;"
              f" ${measured.cost:.5f}")
    for line in measured.lines:
        print(line)


def print_totals(results: list[Measured], budget_reached: bool) -> None:
    asked = [m for m in results if m.asked]
    shown = [m for m in asked if m.sentence]
    buttons = [m for m in asked if not m.sentence and not m.failure and m.buttons]
    nothing = [m for m in asked if not m.sentence and not m.failure and not m.buttons]
    withheld_count = sum(1 for m in asked if m.failure)
    print()
    print("IN SHORT")
    print(f"  searches: {len(results)}; the AI asked about {len(asked)}: a sentence shown for {len(shown)},"
          f" the shops' words offered for {len(buttons)}, nothing for {len(nothing)}, withheld for {withheld_count}")
    if buttons:
        print(f"  words offered: {sum(len(m.buttons) for m in buttons)} in all;"
              f" proposed {sum(len(m.proposed) for m in asked)}")
    for tag in TAGS:
        of_tag = [m for m in results if m.tag == tag]
        if not of_tag:
            continue
        complex_ = sum(1 for m in of_tag if m.words)
        expected = "complex" if EXPECT_ASKED[tag] else "not complex"
        print(f"  {tag}: {len(of_tag)} searches, {complex_} complex for the engine (expected: {expected})")
    not_asked = Counter(m.why_not for m in results if not m.words)
    if not_asked:
        print("  not complex, why: " + "; ".join(f"{why} {n}" for why, n in not_asked.most_common()))
    withheld = Counter(m.failure.split(":")[0] for m in asked if m.failure)
    if withheld:
        print("  withheld, why: " + "; ".join(f"{why} {n}" for why, n in withheld.most_common()))
    if asked:
        cost = sum(m.cost for m in asked)
        seconds = sorted(m.seconds for m in asked)
        print(f"  the AI's answers: yes {sum(m.yes for m in asked)}, no {sum(m.no for m in asked)},"
              f" unclear {sum(m.unclear for m in asked)}, of which {sum(m.unproved for m in asked)} a yes whose"
              f" words do not stand in the product")
        print(f"  cost: ${cost:.4f} in all, ${cost / len(asked):.5f} a search;"
              f" tokens {sum(m.tokens_in for m in asked):,} in, {sum(m.tokens_out for m in asked):,} out")
        print(f"  time of an answer: {seconds[len(seconds) // 2]:.1f} s in the middle, {seconds[-1]:.1f} s at most")
    searched = sorted(m.search_seconds for m in results)
    if searched:
        print(f"  time of a search on the copy: {searched[len(searched) // 2]:.1f} s in the middle")
    if budget_reached:
        print("  the budget was reached: the searches after it were not asked about")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("catalogue")
    parser.add_argument("searches")
    parser.add_argument("--gone", default="")
    parser.add_argument("--offers", default="")
    parser.add_argument("--budget", type=float, default=1.00)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    searches = read_searches(Path(args.searches))
    if args.limit:
        searches = searches[: args.limit]
    path = Path(args.catalogue).resolve()
    # The copies stand in for the server's files, as for the audit (print_confusions.py).
    for name in ("AWIN_FEED_URL", "AWIN_FEED_FILE", "PICWISE_PURCHASABILITY_CACHE_FILE",
                 "PICWISE_GONE_PHOTOS_FILE", "PICWISE_OFFERS_FILE"):
        os.environ.pop(name, None)
    os.environ["PICWISE_PREPARED_CATALOGUE_FILE"] = str(path)
    os.environ["PICWISE_PREPARED_MAX_AGE_HOURS"] = "100000"
    for option, name in ((args.gone, "PICWISE_GONE_PHOTOS_FILE"), (args.offers, "PICWISE_OFFERS_FILE")):
        if option and Path(option).is_file() and Path(option).stat().st_size:
            os.environ[name] = str(Path(option).resolve())

    from picwise_ai.client import ask, make_client
    from picwise_ai.request import EFFORT, MODEL
    from picwise_providers import state
    from picwise_providers.awin_adapter import feed_file_cache_key
    from picwise_providers.prepared_catalogue import PreparedFileCheck, read_prepared_catalogue_to_measure
    from picwise_providers.search_selection import _product_search_fields
    from picwise_search.live_search_resolver import resolve_live_search

    began = time.monotonic()
    prepared = read_prepared_catalogue_to_measure(path)
    if prepared is None:
        print("no prepared catalogue could be read")
        return 1
    if not prepared.search_fields or "category" not in prepared.search_fields[0]:
        prepared = replace(prepared, search_fields=tuple(_product_search_fields(p) for p in prepared.products))
    state._PREPARED_STATE.clear()
    state._PREPARED_STATE.update(
        file_key=feed_file_cache_key(str(path)),
        prepared=prepared,
        check=PreparedFileCheck("fresh", prepared, prepared.prepared_at),
    )
    state.remember_product_kinds({})
    from picwise_ai.complex_search import description_of

    by_id = {str(product.provider_product_id or "").strip(): product for product in prepared.products}

    class _Descriptions:
        """Each product's description by its id, read only when asked for."""

        def get(self, product_id, default=""):
            product = by_id.get(str(product_id or "").strip())
            return description_of(product) if product is not None else default

    descriptions = _Descriptions()
    dry_run = args.dry_run or not os.environ.get("ANTHROPIC_API_KEY")
    # The measure waits longer than the site will, to see how long an answer takes.
    client = None if dry_run else make_client(timeout=30.0)
    print(f"the prepared catalogue of {prepared.prepared_at.isoformat()}: {len(prepared.products):,} products,"
          f" read in {time.monotonic() - began:.0f} s; {len(searches)} searches; the AI: "
          + ("not asked (a dry run)" if dry_run else f"{MODEL}, effort {EFFORT}, a budget of ${args.budget:.2f}"))

    results: list[Measured] = []
    spent = 0.0
    budget_reached = False
    for index, (tag, search) in enumerate(searches, start=1):
        over = not dry_run and spent >= args.budget
        budget_reached = budget_reached or over
        try:
            measured = measure_one(tag, search, resolve=resolve_live_search, ask=ask,
                                   client=None if over else client, dry_run=dry_run or over,
                                   descriptions=descriptions)
        except Exception as error:  # a measure only: the next search goes on
            measured = Measured(tag=tag, search=search, why_not=f"the search failed: {type(error).__name__}: {error}")
        spent += measured.cost
        results.append(measured)
        print_measured(index, measured)
    print_totals(results, budget_reached)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
