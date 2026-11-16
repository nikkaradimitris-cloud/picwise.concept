"""How many searches visitors made, and how many found no product: counted on the server,
printed as numbers only (owner, 2026-11-16, the daily work's Sunday summary: «αναζητήσεις
επισκεπτών (συχνές και χωρίς αποτέλεσμα)»).

`.github/workflows/server-health.yml` sends this file to the server every morning and runs
it there (`python3 - < count_searches.py`), so this commit's code runs, not the release's.
It reads the day files `picwise_app.search_log` keeps (`/srv/picwise/shared/searches`,
`<UTC day>.jsonl`, one `{"q": "the words"}` a line). The workflow's log is public, like the
repository: no search's words are printed, nor anything made from them; a search is only
counted.

- Every day: yesterday's searches (the last whole UTC day), the searches of the last
  `DAYS` whole days, how many different ones (the same words whatever their capitals and
  spaces), and how many times the most searched one was searched.
- With `--check` (the workflow: on Sundays, or by hand): every different search of those
  days is asked of the site on the server itself (`SITE`, where `picwise-web` listens, never
  the internet) and counted when its page shows no product card. Such a request is no
  visitor's search: the site keeps only what a page's own script reports
  (`picwise_app.search_log`) and asks the AI only when a page's script asks for its answer
  (`picwise_ai.store`), so it is not kept and costs nothing. At most `MAX_CHECKED`
  searches, the most searched first, within `MAX_CHECK_SECONDS`; the rest are counted as
  not checked.

The standard library only: the server's own python3 runs it, outside the site's packages.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable

SEARCHES_DIR = Path("/srv/picwise/shared/searches")
SITE = "http://127.0.0.1:8016"
SITE_HOST = "picwise.subby.cloud"
DAYS = 7
MAX_CHECKED = 200
MAX_CHECK_SECONDS = 180.0
REQUEST_SECONDS = 15.0
# Each product card of a search's page opens with this (`picwise_surface.reference`).
CARD_MARK = '<article class="pw-card'

# A search's words -> the page the site shows for it, or None when it did not answer.
Fetch = Callable[[str], "str | None"]


def read_day(folder: Path, day: date) -> list[str]:
    """The searches kept on one day; a line that is not one is left out."""
    try:
        text = (folder / f"{day.isoformat()}.jsonl").read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return []
    searches = []
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        words = " ".join(str(record.get("q") or "").split()) if isinstance(record, dict) else ""
        if words:
            searches.append(words)
    return searches


def same_search(words: str) -> str:
    """What makes two searches the same one: their words, whatever capitals and spaces."""
    return " ".join(words.split()).casefold()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """The check stays on the server: a page that sends elsewhere is not followed."""

    def redirect_request(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None


def fetch_page(words: str) -> str | None:
    """The site's page for a search, asked on the server itself."""
    request = urllib.request.Request(
        f"{SITE}/search?{urllib.parse.urlencode({'q': words})}",
        headers={"Host": SITE_HOST, "User-Agent": "picwise-server-health"},
    )
    try:
        with urllib.request.build_opener(_NoRedirect).open(request, timeout=REQUEST_SECONDS) as response:
            if response.status != 200:
                return None
            return response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError):
        return None


def found_nothing(page: str) -> bool:
    return CARD_MARK not in page


def check(
    searches: Counter,
    first_words: dict[str, str],
    fetch: Fetch,
    *,
    max_checked: int = MAX_CHECKED,
    max_seconds: float = MAX_CHECK_SECONDS,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[int, int, int]:
    """The different searches that found no product, the searches they were, and how many
    different ones were not checked."""
    started = clock()
    nothing = nothing_times = unchecked = 0
    for checked, (key, times) in enumerate(searches.most_common()):
        if checked >= max_checked or clock() - started > max_seconds:
            unchecked += 1
            continue
        page = fetch(first_words[key])
        if page is None:
            unchecked += 1
        elif found_nothing(page):
            nothing += 1
            nothing_times += times
    return nothing, nothing_times, unchecked


def _days(today: date, count: int) -> list[date]:
    return [today - timedelta(days=back) for back in range(count, 0, -1)]


def _count(days_searches: Iterable[list[str]]) -> tuple[int, Counter, dict[str, str]]:
    total = 0
    counted: Counter = Counter()
    first_words: dict[str, str] = {}
    for searches in days_searches:
        for words in searches:
            total += 1
            key = same_search(words)
            counted[key] += 1
            first_words.setdefault(key, words)
    return total, counted, first_words


def summary(folder: Path, today: date, *, do_check: bool, fetch: Fetch = fetch_page, days: int = DAYS) -> list[str]:
    """The lines to print: numbers only."""
    if not folder.is_dir():
        return ["searches by visitors: none kept (the server has no folder for them)"]
    span = _days(today, days)
    try:
        by_day = [read_day(folder, day) for day in span]
    except OSError as error:
        return [f"searches by visitors: not read ({type(error).__name__})"]
    total, counted, first_words = _count(by_day)
    most = counted.most_common(1)[0][1] if counted else 0
    lines = [
        f"searches by visitors: {len(by_day[-1])} yesterday ({span[-1].isoformat()}); "
        f"{total} in the {days} days {span[0].isoformat()} to {span[-1].isoformat()}, "
        f"{len(counted)} different, the most searched one {most} times"
    ]
    if do_check:
        if not counted:
            lines.append("searches that found no product: none to check")
        else:
            nothing, nothing_times, unchecked = check(counted, first_words, fetch)
            lines.append(
                f"searches that found no product, asked again on the server: {nothing} of the "
                f"{len(counted)} different ({nothing_times} of the {total} searches); not checked: {unchecked}"
            )
    return lines


def main(argv: list[str] | None = None, *, fetch: Fetch = fetch_page, now: datetime | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, default=SEARCHES_DIR)
    parser.add_argument("--check", action="store_true", help="ask the site again which searches find no product")
    args = parser.parse_args(argv)
    today = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date()
    for line in summary(args.dir, today, do_check=args.check, fetch=fetch):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
