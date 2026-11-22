"""Say a look's notes as the run's notes, which GitHub's API shows without a login.

    python3 deployment/server/say_notes.py DIR FIRST LAST

`DIR` holds numbered text files (`01.txt`, `02.txt`...: the first line a note's title, the
rest its text), written by a look (`look_itself.Notes`). GitHub keeps ten notes a step, so a
workflow says them ten a step. Nothing but the files' own text is printed.
"""
from __future__ import annotations

import sys
from pathlib import Path


def command(title: str, text: str) -> str:
    """One note as GitHub's workflow command: the title and the text escaped as it asks."""
    body = text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    name = title.replace("%", "%25").replace("\r", " ").replace("\n", " ").replace(":", " ").replace(",", " ")
    return f"::notice title={name}::{body}"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3:
        print(__doc__)
        return 1
    folder, first, last = Path(args[0]), int(args[1]), int(args[2])
    for number in range(first, last + 1):
        path = folder / f"{number:02d}.txt"
        if not path.is_file():
            continue
        title, _, text = path.read_text(encoding="utf-8").partition("\n")
        print(command(title, text.rstrip("\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
