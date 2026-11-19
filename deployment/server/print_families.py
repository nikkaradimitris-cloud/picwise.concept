"""What the AI decided about the shops' listings (owner, 2026-11-19: one card per product):
how many sets it answered, how many it joined, and a sample of both, to be read and
checked by a person.

    ssh picwise 'sudo cat /srv/picwise/assist/families/answers/sets.json' \
        | python3 deployment/server/print_families.py [--sample 40]

Printed: counts, and for a sample of sets the titles it joined and those it kept apart,
with no link and no shop's address. Exits 0, also without a file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Any


def print_families(payload: Any, *, sample: int = 40) -> None:
    sets = payload.get("sets") if isinstance(payload, dict) else None
    if not isinstance(sets, dict) or not sets:
        print("families: no set answered yet")
        return
    answered = {key: value for key, value in sets.items() if isinstance(value, dict)}
    joined = {key: value for key, value in answered.items() if any(len(group) > 1 for group in value.get("groups") or ())}
    count = payload.get("families_count")
    print(
        f"families: sets answered: {len(answered):,}; with listings joined: {len(joined):,}; "
        f"kept all apart: {len(answered) - len(joined):,}; products given a family: "
        f"{count if isinstance(count, int) else '?':,}; last answer {payload.get('updated_at', '?')}"
    )

    def order(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    for key in sorted(answered, key=order)[:sample]:
        value = answered[key]
        # A shop's title may hold a line break: one line a set.
        titles = [" ".join(str(title).split()) for title in value.get("titles") or ()]
        parts = []
        for group in value.get("groups") or ():
            names = [titles[number - 1] for number in group if 0 < number <= len(titles)]
            parts.append("  +  ".join(names))
        joined_any = any(len(group) > 1 for group in value.get("groups") or ())
        print(("joined: " if joined_any else "apart: ") + "  |  ".join(parts))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print what the AI decided about the shops' listings.")
    parser.add_argument("--sample", type=int, default=40)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    text = sys.stdin.read()
    try:
        payload = json.loads(text) if text.strip() else {}
    except ValueError:
        print("families: the file cannot be read")
        return 0
    print_families(payload, sample=args.sample)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
