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
import re
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

UNIT = "picwise-prepare.service"
SECRET_FILES = (Path("/etc/picwise/picwise.env"), Path("/etc/picwise/assist.env"))
FOLDERS = (Path("/srv/picwise/shared/prepared"), Path("/srv/picwise/shared/cache"))
LINES_AT_END = 25
LINES_A_RUN = 120

_RUN_STARTS = re.compile(r"Starting (?:picwise-prepare\.service|PicWise: prepare)")
_WORTH_A_LINE = re.compile(
    r"prepare_catalogue|Traceback|Error|error|fail|Fail|[Kk]illed|oom|OOM|[Mm]emory|Main process|"
    r"Consumed|Suppressed|Deactivated|Finished|exited|status="
)
_LINK = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://\S+")
_TOKEN = re.compile(r"[A-Za-z0-9_\-]{32,}")
_KERNEL_MEMORY = re.compile(r"oom|out of memory|killed process|memory cgroup", re.IGNORECASE)

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
    say("== the kernel's lines about memory")
    kernel = [line for line in runner(["journalctl", "-k", "-o", "short-iso", "--no-pager", "--since", args.since]).splitlines() if _KERNEL_MEMORY.search(line)]
    for line in kernel[-40:] or ["(none)"]:
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
