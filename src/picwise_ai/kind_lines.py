"""The AI's part in the kinds: each kind of the site its own lines of Google's taxonomy.

Owner, 2026-11-20 (19:00 Athens): «Κάθε είδος του site να έχει τη δική του λίστα κατηγοριών
Google (π.χ. tablet μόνο «Tablet Computers», ρολόι μόνο «Watches»). Τη λίστα να τη φτιάξει
το AI μία φορά (περίπου 0,50 $) και να ελεγχθεί», and «ένα προϊόν εμφανίζεται σε ένα είδος
μόνο αν η κατηγορία που του έδωσε το AI είναι στη λίστα του είδους. Ο ίδιος κανόνας και για
τα δύο feeds». Why: the AI's line of each product was sound, but the kind reader read it
wrong ("Hardware Accessories > Washers" as a washing machine, "Home Fragrances" as perfume).

Claude Haiku 5.5 is given Google's taxonomy as the numbered tree the scan of the products
reads (`picwise_ai.shelves`, cached), and the kinds of `picwise_nlu.product_concepts`, a few
of one department a call: each kind's id, its names, its department, the kinds it is part
of and the narrower kinds it holds. It answers each kind with the lines whose products are
the kind itself, each by its number and its own name, checked as the scan's answers are
(`shelves.checked_lines`: a number and a name that agree, or a name, unique in the list, in
the number's department); a line refused is left out. A line holds the lines under it.

Written once by `deployment/server/write_kind_lines.py` (`.github/workflows/ai-kind-lines.yml`),
checked, and kept in the repository (`KIND_LINES_PATH`), read by `picwise_providers.ai_shelves`.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from .shelves import MODEL, _key, _lines_by_own_name, _names, taxonomy_lines, taxonomy_tree

EFFORT = "medium"
MAX_TOKENS = 16000
# Kinds in one call, all of one department.
PER_CALL = 8
KIND_LINES_PATH = Path(__file__).resolve().parents[2] / "data" / "kind_lines" / "google_lines_by_kind.json"
NAMES_SHOWN = 10

SYSTEM_PROMPT = """\
You map the kinds of product of PicWise, a UK shopping search, to Google's product taxonomy, \
given below as a numbered tree: a line's full name is its own name after the names of the \
lines above it, as "Home & Garden > Kitchen & Dining > Kitchen Appliances > Electric Kettles".
PicWise shows a product under a kind only when the product's line of the taxonomy is on the \
kind's list. A buyer who searches for the kind must see the thing itself: never a part, a \
spare, a refill, a consumable, a case or cover, a cable, a stand or another accessory of it, \
nor a toy, a book, a costume or a decoration of it.
For each kind given, list every line whose products are that kind itself:
- A line counts with every line under it. Choose a line only when every line under it is \
this kind too; otherwise choose the deeper lines that are.
- List every place where the kind is sold, also in other departments: the same thing for \
pets, for camping, for children, for work or for a vehicle is the same kind (a dog bed is a \
bed, a camping chair a chair, a child's backpack a backpack, work boots are boots).
- A kind's narrower kinds, when named, are part of it: list their lines too.
- A kind that is itself an accessory, a part or a consumable (a phone case, drill bits, \
printer ink) gets the lines of that accessory, part or consumable, and not the lines of \
the thing it serves.
- When no line holds the kind, answer an empty list.
Answer each line with its number and its own name, copied exactly from the tree. Every \
kind given is answered exactly once, by its id."""

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kinds": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "lines": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"line": {"type": "integer"}, "name": {"type": "string"}},
                            "required": ["line", "name"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["id", "lines"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["kinds"],
    "additionalProperties": False,
}


def _department_name(mega_category_id: str) -> str:
    return mega_category_id.replace("_", " ")


def kinds_described() -> list[dict[str, Any]]:
    """Each kind of the site as the model reads it, in the lexicon's order."""
    from picwise_nlu.product_concepts import get_product_concepts

    concepts = get_product_concepts()
    by_id = {concept.concept_id: concept for concept in concepts}
    narrower: dict[str, list[str]] = {}
    for concept in concepts:
        for wide in concept.broader:
            narrower.setdefault(wide, []).append(concept.concept_id)

    def named(concept_id: str) -> str:
        concept = by_id.get(concept_id)
        return f"{concept_id} ({concept.english[0]})" if concept is not None and concept.english else concept_id

    found = []
    for concept in concepts:
        found.append(
            {
                "id": concept.concept_id,
                "names": list(concept.english[:NAMES_SHOWN]),
                "department": _department_name(concept.mega_category_id),
                "part_of": [named(wide) for wide in concept.broader],
                "narrower": [named(narrow) for narrow in narrower.get(concept.concept_id, ())],
            }
        )
    return found


def kind_line(number: int, kind: dict[str, Any]) -> str:
    """One kind as the model reads it."""
    parts = [f"{number}. id: {kind['id']}", "names: " + ", ".join(kind.get("names") or ())]
    parts.append(f"department: {kind.get('department') or ''}")
    if kind.get("part_of"):
        parts.append("a kind of: " + ", ".join(kind["part_of"]))
    if kind.get("narrower"):
        parts.append("narrower kinds: " + ", ".join(kind["narrower"]))
    return " | ".join(parts)


def batches(kinds: Sequence[dict[str, Any]], size: int = PER_CALL) -> list[list[dict[str, Any]]]:
    """The kinds in calls of at most `size`, each call of one department, in order."""
    by_department: dict[str, list[dict[str, Any]]] = {}
    for kind in kinds:
        by_department.setdefault(str(kind.get("department") or ""), []).append(kind)
    found = []
    for group in by_department.values():
        for start in range(0, len(group), size):
            found.append(group[start:start + size])
    return found


def user_message(kinds: Sequence[dict[str, Any]]) -> str:
    return "\n".join([f"Kinds ({len(kinds)}):", *(kind_line(n, kind) for n, kind in enumerate(kinds, 1))])


def request_kwargs(kinds: Sequence[dict[str, Any]], lines: Sequence[str] | None = None) -> dict[str, Any]:
    """The Messages API request for one call: the instructions and the tree first, the same
    on every call and cached (the same tree as the scan's); the kinds after."""
    lines = taxonomy_lines() if lines is None else lines
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": [
            {"type": "text", "text": SYSTEM_PROMPT},
            {
                "type": "text",
                "text": "Google's product taxonomy:\n" + taxonomy_tree(lines),
                "cache_control": {"type": "ephemeral"},
            },
        ],
        "messages": [{"role": "user", "content": user_message(kinds)}],
        "output_config": {"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
    }


def checked_kind_lines(
    answer: dict[str, Any] | None, ids: Sequence[str], lines: Sequence[str]
) -> tuple[dict[str, list[str]], int]:
    """Each kind's lines, for the kinds of the call answered exactly once; and how many
    lines were refused. A line: its number and its own name agree, or the name names a
    line (each own name is unique) in the same department as the number's line, or the
    number is past the list's ends. A kind answered with no line keeps an empty list (the
    model found none); a kind not answered, or answered twice, is left out."""
    if not isinstance(answer, dict) or not isinstance(answer.get("kinds"), list):
        return {}, 0
    wanted = set(ids)
    by_name = _lines_by_own_name(tuple(lines))
    seen: dict[str, int] = {}
    found: dict[str, list[str]] = {}
    refused = 0
    for item in answer["kinds"]:
        if not isinstance(item, dict) or item.get("id") not in wanted:
            continue
        kind = str(item["id"])
        seen[kind] = seen.get(kind, 0) + 1
        chosen: list[str] = []
        for given in item.get("lines") or ():
            if not isinstance(given, dict):
                refused += 1
                continue
            number, name = given.get("line"), given.get("name")
            if not isinstance(number, int) or isinstance(number, bool) or not isinstance(name, str):
                refused += 1
                continue
            numbered = lines[number - 1] if 1 <= number <= len(lines) else ""
            line = ""
            if numbered and _key(_names(numbered)[-1]) == _key(name):
                line = numbered
            else:
                named = by_name.get(_key(name), "")
                if named and (not numbered or _names(named)[0] == _names(numbered)[0]):
                    line = named
            if not line:
                refused += 1
                continue
            if line not in chosen:
                chosen.append(line)
        found[kind] = chosen
    return {kind: chosen for kind, chosen in found.items() if seen.get(kind) == 1}, refused


def line_numbers(lines: Sequence[str]) -> dict[str, int]:
    return {line: number for number, line in enumerate(lines, 1)}


def compact(found: dict[str, list[str]], lines: Sequence[str]) -> str:
    """The lists in few characters, one kind a row: `id=number,number` (`id=` for none),
    to be read back by `from_compact` against the same taxonomy."""
    numbers = line_numbers(lines)
    return "\n".join(f"{kind}=" + ",".join(str(numbers[line]) for line in chosen) for kind, chosen in found.items())


def from_compact(text: str, lines: Sequence[str]) -> dict[str, list[str]]:
    """The lists `compact` wrote; a row that is not one is skipped."""
    found: dict[str, list[str]] = {}
    for row in str(text or "").splitlines():
        kind, sign, numbers = row.strip().partition("=")
        if not sign or not kind:
            continue
        chosen = []
        for part in numbers.split(","):
            part = part.strip()
            if part.isdigit() and 1 <= int(part) <= len(lines):
                chosen.append(lines[int(part) - 1])
        found[kind] = chosen
    return found


def chunks(text: str, width: int = 3500) -> list[str]:
    """Rows kept whole, in pieces of at most `width` characters (GitHub keeps about 4,000
    of a note)."""
    pieces: list[str] = []
    current: list[str] = []
    size = 0
    for row in text.splitlines():
        if current and size + len(row) + 1 > width:
            pieces.append("\n".join(current))
            current, size = [], 0
        current.append(row)
        size += len(row) + 1
    if current:
        pieces.append("\n".join(current))
    return pieces


def write(found: dict[str, list[str]], path: Path, *, note: dict[str, Any]) -> None:
    """The lists as the repository keeps them: the kinds in the lexicon's order."""
    data = {**note, "kinds": found}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def read(path: Path = KIND_LINES_PATH) -> dict[str, list[str]]:
    """Each kind's lines as kept; empty when the file is not there or not readable."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    kinds = data.get("kinds") if isinstance(data, dict) else None
    if not isinstance(kinds, dict):
        return {}
    return {
        str(kind): [str(line) for line in chosen if isinstance(line, str)]
        for kind, chosen in kinds.items()
        if isinstance(chosen, list)
    }


def all_ids(kinds: Iterable[dict[str, Any]]) -> list[str]:
    return [str(kind["id"]) for kind in kinds]
