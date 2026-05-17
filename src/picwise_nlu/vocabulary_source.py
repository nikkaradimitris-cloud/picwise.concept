from __future__ import annotations

import re
from pathlib import Path


_PACK_FILES = (
    "home_living_appliances.py",
    "tech_electronics_office.py",
    "auto_moto_mobility.py",
    "tools_diy_garden_repair.py",
    "health_beauty_family_lifestyle.py",
    "fashion_footwear_jewelry_accessories.py",
)
_ASCII_STRING_RE = re.compile(r'"([a-z0-9][a-z0-9/\-\s]{1,80})"')
_RECORD_BLOCK_RE = re.compile(
    r"def\s+_[a-z0-9_]+_record\(\)\s*->\s*dict:\s*(?P<body>.*?)(?=^def\s+_[a-z0-9_]+_record\(\)\s*->\s*dict:|\Z)",
    flags=re.DOTALL | re.MULTILINE,
)
_MEGA_CATEGORY_RE = re.compile(r'mega_category_id\s*=\s*"([^"]+)"')


def _canonicalize(term: str) -> str:
    return " ".join(term.split()).strip().lower()


def load_clean_vocab_by_mega_category() -> dict[str, set[str]]:
    base_dir = Path(__file__).resolve().parents[1] / "picwise_taxonomy" / "deep_packs"
    vocab: dict[str, set[str]] = {}
    for file_name in _PACK_FILES:
        path = base_dir / file_name
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for block_match in _RECORD_BLOCK_RE.finditer(content):
            block = block_match.group("body")
            category_match = _MEGA_CATEGORY_RE.search(block)
            if not category_match:
                continue
            category = category_match.group(1)
            bucket = vocab.setdefault(category, set())
            for raw in _ASCII_STRING_RE.findall(block):
                term = _canonicalize(raw)
                if len(term) < 3:
                    continue
                token_count = len(term.split())
                if token_count > 4:
                    continue
                if any(token.endswith("'s") for token in term.split()):
                    continue
                bucket.add(term)
    return vocab

