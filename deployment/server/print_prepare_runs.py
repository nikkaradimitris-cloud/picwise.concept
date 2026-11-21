"""The catalogue preparation's runs, read from the server's journal (owner, 2026-11-20:
«μας ενδιαφέρει γιατί δεν δούλεψε το feed», after two deployments that day whose
preparation failed with no line saying why).

`.github/workflows/prepare-runs.yml` sends this file to the server and runs it there with
sudo (`python3 - < print_prepare_runs.py`), as `print_health.py` is run. It only reads:
the journal of `picwise-prepare.service`, the kernel's lines about memory, systemd's own
view of the unit's last run, the sizes and times of the prepared and cached files, and
the server's memory. A deployment keeps only the run's `prepare_catalogue|Consumed`
lines (`deploy.sh`), so a run that ends without its summary line said nothing of why.

The workflow's log is public, like the repository: every value of the server's secret
files, every link and every long token are masked here, on the server, before a line is
printed; the server's names are masked by the workflow.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path

UNIT = "picwise-prepare.service"
SECRET_FILES = (Path("/etc/picwise/picwise.env"), Path("/etc/picwise/assist.env"))
FOLDERS = (Path("/srv/picwise/shared/prepared"), Path("/srv/picwise/shared/cache"))
LINES_AT_END = 25
LINES_A_RUN = 120
SITE_READINESS = "http://127.0.0.1:8016/private-beta-readiness"

_RUN_STARTS = re.compile(r"Starting (?:picwise-prepare\.service|PicWise: prepare)")
BOT_UNIT = "picwise-shops.service"
# The checks' bot (deployment/bot/shop_checks_bot.py): its lines are counts and shop names
# only, so the last of them are printed as they are.
CHECKS_UNIT = "picwise-checks.service"
CHECKS_LINES = 150
_BOT_RUN_STARTS = re.compile(r"Starting (?:picwise-shops\.service|PicWise: ask the shops)")
_BOT_WORTH_A_LINE = re.compile(r"^(?:the feed's cop|no copy of the feed|in all:|the round failed)|Consumed|Failed|killed")
# A shop's own line, "== <shop>: <how it ended>; <n> requests, ...": a shop's name may hold
# ": " itself, so the end is what follows the last one before its requests.
_BOT_SHOP_LINE = re.compile(r"^== .+: (.+?); [\d,]+ requests")
_WORTH_A_LINE = re.compile(
    r"prepare_catalogue|Traceback|Error|error|fail|Fail|[Kk]illed|oom|OOM|[Mm]emory|Main process|"
    r"Consumed|Suppressed|Deactivated|Finished|exited|status="
)
_LINK = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://\S+")
_TOKEN = re.compile(r"[A-Za-z0-9_\-]{32,}")
_KERNEL_MEMORY = re.compile(r"oom|out of memory|killed process|memory cgroup", re.IGNORECASE)
# A process's line in the kernel's table of an out-of-memory kill:
# [  pid  ]   uid  tgid total_vm      rss rss_anon rss_file rss_shmem pgtables_bytes swapents oom_score_adj name
_TASK_ROW = re.compile(r"\[\s*\d+\]\s+\d+\s+\d+\s+\d+\s+(\d+)\s.*\s(\S+)\s*$")
_OOM_TOTALS = re.compile(r"Mem-Info|active_anon|pages RAM|Free swap|Total swap|Node 0 Normal free", re.IGNORECASE)
TASK_PAGES_SHOWN = 25_000  # 100 MB of 4 kB pages: the processes that matter

Run = Callable[[Sequence[str]], str]


def run(command: Sequence[str]) -> str:
    try:
        done = subprocess.run(list(command), capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.SubprocessError) as error:
        return f"({command[0]} could not be run: {type(error).__name__})"
    return done.stdout


def secrets_in(text: str) -> list[str]:
    """Every value of an environment file, and each long piece of it (a link's key), the
    longest first, so that a value is masked before any piece of it."""
    found: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        value = line.split("=", 1)[1].strip().strip("'\"")
        if len(value) >= 6:
            found.add(value)
        found.update(piece for piece in re.split(r"[/?&=:;,]", value) if len(piece) >= 12)
    return sorted(found, key=len, reverse=True)


def read_secrets(files: Sequence[Path] = SECRET_FILES) -> list[str]:
    found: set[str] = set()
    for path in files:
        try:
            found.update(secrets_in(path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return sorted(found, key=len, reverse=True)


def mask(line: str, secrets: Sequence[str]) -> str:
    for secret in secrets:
        line = line.replace(secret, "<secret>")
    line = _LINK.sub("<link>", line)
    return _TOKEN.sub("<token>", line)


def split_runs(lines: Sequence[str]) -> list[list[str]]:
    """The journal's lines, one list a run: a run begins where systemd starts the unit;
    lines before the first start are a run of their own (one begun before the window)."""
    runs: list[list[str]] = []
    for line in lines:
        if _RUN_STARTS.search(line) or not runs:
            runs.append([])
        runs[-1].append(line)
    return runs


def lines_of_a_run(lines: Sequence[str]) -> list[str]:
    """What a run says: each line worth a look, then its last lines, each once, in order,
    at most `LINES_A_RUN`."""
    keep = {index for index, line in enumerate(lines) if _WORTH_A_LINE.search(line)}
    keep.update(range(max(0, len(lines) - LINES_AT_END), len(lines)))
    chosen = [lines[index] for index in sorted(keep)]
    if len(chosen) > LINES_A_RUN:
        left_out = len(chosen) - LINES_A_RUN
        chosen = chosen[: LINES_A_RUN // 2] + [f"... {left_out} lines left out ..."] + chosen[-LINES_A_RUN // 2 :]
    return chosen


def bot_nights(lines: Sequence[str]) -> list[str]:
    """What the shops' bot said each night (`picwise-shops.service`, 21/11: the second
    opinion of that day read in the night's note that it had read no shop since 19/11):
    its own summary lines, and how many shops ended each way ("read", "no address", ...).
    The bot prints shop names and counts, never an address; only counts are kept here."""
    chosen: list[str] = []
    ends: Counter = Counter()

    def close() -> None:
        if ends:
            chosen.append("   shops: " + "; ".join(f"{end} {count}" for end, count in ends.most_common()))
            ends.clear()

    for line in lines:
        said = line.split(": ", 1)[1] if ": " in line else line
        if _BOT_RUN_STARTS.search(line):
            close()
            chosen.append(line)
        elif _BOT_SHOP_LINE.match(said):
            ends[_BOT_SHOP_LINE.match(said).group(1).split(";", 1)[0].strip()] += 1
        elif _BOT_WORTH_A_LINE.search(said):
            chosen.append(line)
    close()
    return chosen


def kernel_memory_lines(lines: Sequence[str]) -> list[str]:
    """The kernel's lines about memory; within each out-of-memory kill, from "invoked
    oom-killer" to "Killed process", also its totals and each process holding more than
    `TASK_PAGES_SHOWN` pages, with its memory in MB: who held the server's memory then."""
    chosen: list[str] = []
    inside = False
    for line in lines:
        if "invoked oom-killer" in line:
            inside = True
        row = _TASK_ROW.search(line) if inside else None
        if row is not None:
            pages = int(row.group(1))
            if pages > TASK_PAGES_SHOWN:
                chosen.append(f"{line.rstrip()}   <- {pages * 4 / 1024:,.0f} MB")
        elif _KERNEL_MEMORY.search(line) or (inside and _OOM_TOTALS.search(line)):
            chosen.append(line)
        if "Killed process" in line:
            inside = False
    return chosen[-200:]


def main(argv: Sequence[str] | None = None, *, runner: Run = run, secrets: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", default="-30h", help="from when, as journalctl reads it (--since=-30h)")
    args = parser.parse_args(argv)
    hidden = read_secrets() if secrets is None else list(secrets)
    # The server's names and addresses too, besides the workflow's own masks.
    names = runner(["hostname"]) + " " + runner(["hostname", "-f"]) + " " + runner(["hostname", "-I"])
    hidden = sorted(set(hidden) | {name for name in names.split() if len(name) >= 4}, key=len, reverse=True)

    def say(line: str = "") -> None:
        print(mask(line, hidden))

    journal = runner(["journalctl", "-u", UNIT, "-o", "short-iso", "--no-pager", "--since", args.since])
    runs = [lines for lines in split_runs(journal.splitlines()) if lines]
    say(f"== {UNIT}: {len(runs)} runs since {args.since}")
    for number, lines in enumerate(runs, 1):
        say()
        say(f"-- run {number}: {len(lines)} lines, from {lines[0][:25].strip()} to {lines[-1][:25].strip()}")
        for line in lines_of_a_run(lines):
            say(line)

    say()
    say("== systemd's view of the unit's last run")
    say(
        runner(
            [
                "systemctl", "show", UNIT,
                "-p", "Result", "-p", "ExecMainCode", "-p", "ExecMainStatus",
                "-p", "ExecMainStartTimestamp", "-p", "ExecMainExitTimestamp",
                "-p", "MemoryPeak", "-p", "MemoryHigh", "-p", "MemoryMax", "-p", "OOMPolicy",
            ]
        ).strip()
    )

    say()
    say(f"== {BOT_UNIT}, the shops' bot (03:40 UTC): each night's own lines")
    bot = runner(["journalctl", "-u", BOT_UNIT, "-o", "short-iso", "--no-pager", "--since", args.since])
    for line in bot_nights(bot.splitlines()) or ["(none)"]:
        say(line)

    say()
    say(f"== {CHECKS_UNIT}, the checks (20:30 to 03:05 UTC): the last {CHECKS_LINES} lines")
    checks = runner(["journalctl", "-u", CHECKS_UNIT, "-o", "short-iso", "--no-pager", "--since", args.since])
    for line in checks.splitlines()[-CHECKS_LINES:] or ["(none)"]:
        say(line)

    say()
    say("== the kernel's lines about memory")
    for line in kernel_memory_lines(
        runner(["journalctl", "-k", "-o", "short-iso", "--no-pager", "--since", args.since]).splitlines()
    ) or ["(none)"]:
        say(line)
    oomd = runner(["journalctl", "-u", "systemd-oomd.service", "-o", "short-iso", "--no-pager", "--since", args.since]).splitlines()
    say("== systemd-oomd")
    for line in oomd[-10:] or ["(none)"]:
        say(line)

    say()
    say("== the files (size, time)")
    for folder in FOLDERS:
        say(runner(["ls", "-l", "--time-style=+%Y-%m-%d %H:%M:%S", str(folder)]).strip() or f"{folder}: nothing")

    say()
    say("== the server's memory")
    say(runner(["free", "-m"]).strip())

    say()
    say("== the site now: the catalogue each answer came from, and each process's memory")
    seen: list[str] = []
    for _ask in range(6):  # several asks, so that each of the site's workers is likely met
        try:
            page = json.loads(runner(["curl", "-s", "-m", "10", SITE_READINESS]) or "{}")
        except ValueError:
            page = {}
        told = json.dumps(page.get("prepared_feed") if isinstance(page, dict) else None, sort_keys=True)
        if told not in seen:
            seen.append(told)
    for told in seen:
        say(f"prepared_feed: {told}")
    for line in runner(["ps", "-o", "pid=,rss=,comm=", "-u", "picwise"]).splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1].isdigit() and int(parts[1]) > 100 * 1024:
            say(f"  {parts[2]} {parts[0]}: {int(parts[1]) / 1024:,.0f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
