"""The specifications a provider feed states about a product, and which may rank it.

Owner instruction (2026-10-12): "πάντα πρέπει να ανατρέχουμε στα χαρακτηριστικά του
προϊόντος όταν αυτά είναι διαθέσιμα" -- always read the product's specifications when
the feed carries them -- with the clarification that a number should be cross-checked
against a second source "όπου αυτό είναι εφικτό", where that is feasible.

It is not feasible in the feed PicWise has. Measured on 2026-10-12 over its 11,573
products: of the specification numbers that appear **only** in a description, 0 of 107
for speakers, 0 of 90 for headphones, 0 of 28 for cameras and 0 of 17 for amplifiers
are repeated by any other column. No second source exists to check them against.

So the corroboration this module uses is the only one the data allows: **a number
counts when the feed states it as a property, not when it merely appears.** That
distinction is the whole of the reading:

- The `specifications` column states properties by construction ("Colour: Black,
  Extended Length (mm): 610"), so a labelled number there is read directly. Only three
  shops fill it, two of them on every row, which is also the proof that the column is
  not a feed misconfiguration but a merchant's choice.
- A **title** or **product type** is a declared field: the merchant chose those words
  to name the product, so a number with a unit needs no label ("Gaming Monitor 27
  inch", "XLR Cable 1.5 m"). Requiring a label here would throw away almost
  everything -- cable length drops from 98% of cables to 15%.
- A **description** is marketing copy, so a number there is read only when a word
  naming the property sits just before it ("Driver Diameter 40 mm", "Impedance 32",
  "Battery: 3000mAh") and no hedge or comparison precedes it ("up to 9 hours", "better
  than 32 inch"). Measured, this keeps 70% of the description-only numbers for
  speakers and 81% for amplifiers while dropping the prose.

**Which properties may decide the recommendation** is the owner's call, not this
module's, because a specification is not automatically a measure of quality. The owner
left the choice to PicWise on 2026-10-12 after being shown the coverage, and the rule
taken is: a property ranks only where "more is better" is undisputed for every buyer.
`RANKING_PROPERTIES` is that set -- storage, battery and playtime. Power does not
rank: a louder amplifier is not a better one. Length does not rank, by the owner's
explicit answer the same day: a buyer wants the cable length that fits, not the
longest one, so length is shown on the card and decides nothing. Everything else is
read and shown, never ranked.

Nothing here judges a product. It reports what the feed stated, in the feed's words,
and says where it said it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

# Properties PicWise can read, each with the unit its values are normalised to and
# whether that unit's numbers may decide a recommendation. `scale` converts a stated
# unit into the base unit.
_BASE_UNIT = {
    "storage": "GB",
    "memory": "GB",
    "battery": "mAh",
    "playtime": "h",
    "power": "W",
    "length": "m",
    "screen": "in",
    "frequency": "Hz",
    "impedance": "ohm",
    "weight": "g",
}

# Owner decision, 2026-10-12: only properties whose direction no buyer would dispute.
# Adding one here makes it decide a recommendation, so it is a decision for the owner.
RANKING_PROPERTIES = frozenset({"storage", "battery", "playtime"})

# The units that state each property, and what multiplies a stated value to reach the
# base unit. Order matters inside a property: the longest spelling is tried first so
# "mm" is never read as "m".
_UNITS: tuple[tuple[str, str, float], ...] = (
    ("storage", "tb", 1024.0),
    ("storage", "gb", 1.0),
    ("storage", "mb", 1.0 / 1024.0),
    ("battery", "mah", 1.0),
    ("playtime", "hours", 1.0),
    ("playtime", "hour", 1.0),
    ("playtime", "hrs", 1.0),
    ("playtime", "hr", 1.0),
    ("power", "watts", 1.0),
    ("power", "watt", 1.0),
    ("power", "kw", 1000.0),
    ("power", "w", 1.0),
    ("length", "metres", 1.0),
    ("length", "metre", 1.0),
    ("length", "meters", 1.0),
    ("length", "meter", 1.0),
    ("length", "mm", 0.001),
    ("length", "cm", 0.01),
    ("length", "m", 1.0),
    ("screen", "inches", 1.0),
    ("screen", "inch", 1.0),
    ("frequency", "ghz", 1_000_000_000.0),
    ("frequency", "mhz", 1_000_000.0),
    ("frequency", "khz", 1000.0),
    ("frequency", "hz", 1.0),
    ("impedance", "ohms", 1.0),
    ("impedance", "ohm", 1.0),
    ("weight", "grams", 1.0),
    ("weight", "gram", 1.0),
    ("weight", "kg", 1000.0),
    ("weight", "g", 1.0),
)

_NUMBER = r"\d+(?:[.,]\d+)?"
# One pattern per property, longest unit spelling first, so a scan costs one pass per
# property rather than one per unit. PROJECT_RULES section 9 leaves no room for a scan
# per vocabulary entry on every product of the feed.
_PROPERTY_RE: dict[str, re.Pattern[str]] = {}
_SCALE: dict[tuple[str, str], float] = {}
for _property, _unit, _scale in _UNITS:
    _SCALE[(_property, _unit)] = _scale
for _property in _BASE_UNIT:
    _spellings = [unit for prop, unit, _s in _UNITS if prop == _property]
    _spellings.sort(key=len, reverse=True)
    # A number must start a token, so "USB3.0" and a part code are not read as one --
    # except after "<digit>x", which is how amplifiers and speakers state a per-channel
    # figure ("2x50W"), the commonest spec notation in the real feed's audio titles.
    _PROPERTY_RE[_property] = re.compile(
        r"(?:(?<![\w.])|(?<=\dx)|(?<=\dX)|(?<=\d\u00d7))"
        rf"({_NUMBER})\s*(" + "|".join(re.escape(u) for u in _spellings) + r")(?![\w])",
        flags=re.IGNORECASE,
    )

# The words that name a property in a description, just before its number.
_LABELS: dict[str, str] = {
    "storage": r"storage|rom|internal|capacity|ssd|emmc|hard\s*disk",
    "memory": r"memory|ram",
    "battery": r"battery|cell",
    "playtime": r"play\s*time|playtime|playback|run\s*time|runtime|battery\s*life|standby|talk\s*time",
    "power": r"power|output|rms|wattage|consumption",
    "length": r"length|cable|cord|reach|extended",
    "screen": r"screen|display|panel|size|diagonal",
    "frequency": r"frequency|response|bandwidth|band",
    "impedance": r"impedance",
    "weight": r"weight|weighs|mass",
}
_LABEL_RE = {
    name: re.compile(rf"(?:{pattern})[^.;:\n]{{0,24}}[:\-–—]?\s*$", flags=re.IGNORECASE)
    for name, pattern in _LABELS.items()
}
# A number introduced by one of these is not a statement about the product.
_HEDGE_RE = re.compile(
    r"(?:up\s+to|at\s+least|as\s+(?:much|many)\s+as|better\s+than|more\s+than|less\s+than"
    r"|instead\s+of|compared\s+(?:to|with)|rather\s+than|than|unlike|vs\.?|versus"
    r"|replaces?|fits|suitable\s+for|compatible\s+with|works\s+with|for\s+use\s+with)"
    r"[^.;:\n]{0,16}$",
    flags=re.IGNORECASE,
)

# How far back a label or a hedge may sit from the number it governs.
_LOOKBEHIND = 42

DESCRIPTION_KEYS = ("description", "product_short_description")
SPECIFICATION_KEYS = ("specifications",)
DECLARED_KEYS = ("product_type",)


@dataclass(frozen=True)
class ProductSpec:
    """One specification the feed stated, with where it said it."""

    property_id: str
    value: float
    unit: str
    stated_as: str
    source: str

    @property
    def ranks(self) -> bool:
        """May this property decide which of the four is recommended?"""
        return self.property_id in RANKING_PROPERTIES

    def to_dict(self) -> dict[str, Any]:
        return {
            "property_id": self.property_id,
            "value": self.value,
            "unit": self.unit,
            "stated_as": self.stated_as,
            "source": self.source,
            "ranks": self.ranks,
        }


def _value_of(raw_number: str) -> float | None:
    try:
        return float(raw_number.replace(",", "."))
    except ValueError:
        return None


_RAM_AFTER_RE = re.compile(r"^\W{0,3}(?:ram|ddr\d?|lpddr\d?)\b", flags=re.IGNORECASE)


def _qualified_property(property_id: str, after: str) -> str:
    """The property a number really states, read from the word that follows it.

    A byte figure is storage unless the feed calls it RAM right after it. The titles
    of the one kind whose recommendation storage decides state both: "Android TV Box
    4GB RAM 64GB ROM", where ranking by the 4 would rank the wrong number.
    """
    if property_id == "storage" and _RAM_AFTER_RE.match(str(after or "")):
        return "memory"
    return property_id


def _specs_in_declared_text(text: str, source: str) -> list[ProductSpec]:
    """A declared field: a number with a unit states a property, no label needed."""
    body = " ".join(str(text or "").split())
    if not body:
        return []
    found: list[ProductSpec] = []
    for property_id, pattern in _PROPERTY_RE.items():
        for match in pattern.finditer(body):
            value = _value_of(match.group(1))
            if value is None:
                continue
            scale = _SCALE.get((property_id, match.group(2).lower()))
            if scale is None:
                continue
            named = _qualified_property(property_id, body[match.end() : match.end() + 14])
            found.append(
                ProductSpec(
                    property_id=named,
                    value=value * scale,
                    unit=_BASE_UNIT[named],
                    stated_as=" ".join(match.group(0).split()),
                    source=source,
                )
            )
    return found


def _specs_in_prose(text: str, source: str = "description") -> list[ProductSpec]:
    """Marketing copy: a number counts only where a label names what it measures."""
    body = " ".join(str(text or "").split())
    if not body:
        return []
    found: list[ProductSpec] = []
    for property_id, pattern in _PROPERTY_RE.items():
        label = _LABEL_RE[property_id]
        for match in pattern.finditer(body):
            before = body[max(0, match.start() - _LOOKBEHIND) : match.start()]
            if not label.search(before) or _HEDGE_RE.search(before):
                continue
            value = _value_of(match.group(1))
            if value is None:
                continue
            scale = _SCALE.get((property_id, match.group(2).lower()))
            if scale is None:
                continue
            found.append(
                ProductSpec(
                    property_id=property_id,
                    value=value * scale,
                    unit=_BASE_UNIT[property_id],
                    stated_as=" ".join(match.group(0).split()),
                    source=source,
                )
            )
    return found


_BARE_NUMBER_RE = re.compile(rf"(?<![\w.])({_NUMBER})(?![\w])")


def _spec_from_key_unit(property_id: str, key_text: str, value: str) -> ProductSpec | None:
    """A property whose unit is written in the key and whose number is in the value."""
    number = _BARE_NUMBER_RE.search(" ".join(str(value or "").split()))
    if number is None:
        return None
    amount = _value_of(number.group(1))
    if amount is None:
        return None
    for unit in sorted(
        (unit for prop, unit, _s in _UNITS if prop == property_id), key=len, reverse=True
    ):
        if re.search(rf"(?<![\w]){re.escape(unit)}(?![\w])", key_text, flags=re.IGNORECASE):
            return ProductSpec(
                property_id=property_id,
                value=amount * _SCALE[(property_id, unit)],
                unit=_BASE_UNIT[property_id],
                stated_as=f"{number.group(1)} {unit}",
                source="specifications",
            )
    return None


def _specs_in_specification_column(text: str) -> list[ProductSpec]:
    """"Key: Value, Key: Value" -- the key names the property, so the value is read."""
    body = str(text or "")
    if not body:
        return []
    found: list[ProductSpec] = []
    for part in re.split(r"[,\n;|]", body):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        # The key may itself carry the unit ("Extended Length (mm): 610"), so the
        # property is read from the key and the number from either side of the colon.
        key_text = " ".join(key.split())
        for property_id, label in _LABEL_RE.items():
            if not label.search(key_text + " "):
                continue
            # "Length: 610 mm" -- value carries both number and unit.
            matching = [
                spec
                for spec in _specs_in_declared_text(value, "specifications")
                if spec.property_id == property_id
            ]
            if matching:
                found.append(matching[0])
                break
            # "Extended Length (mm): 610" -- the key carries the unit, the value the
            # number, and neither reads as a specification on its own.
            spec = _spec_from_key_unit(property_id, key_text, value)
            if spec is not None:
                found.append(spec)
            break
    return found


def read_product_specs(
    row: Mapping[str, Any] | None,
    *,
    title: str = "",
) -> tuple[ProductSpec, ...]:
    """Every specification the feed states about this product, best source first.

    One value per property: the first source that states it wins, in the order
    `specifications` (a declared list of properties), then the title and product type
    (declared names), then the description (prose, and only where labelled).
    """
    raw = row if isinstance(row, Mapping) else {}
    found: list[ProductSpec] = []
    for key in SPECIFICATION_KEYS:
        found.extend(_specs_in_specification_column(raw.get(key)))
    found.extend(_specs_in_declared_text(title, "title"))
    for key in DECLARED_KEYS:
        found.extend(_specs_in_declared_text(raw.get(key), key))
    for key in DESCRIPTION_KEYS:
        found.extend(_specs_in_prose(raw.get(key), "description"))

    best: dict[str, ProductSpec] = {}
    for spec in found:
        if spec.property_id not in best:
            best[spec.property_id] = spec
    return tuple(best[property_id] for property_id in _BASE_UNIT if property_id in best)


def ranking_spec(specs: tuple[ProductSpec, ...]) -> ProductSpec | None:
    """The one specification that may decide a recommendation, or None.

    When a product states more than one, the order of `RANKING_PROPERTIES` in
    `_BASE_UNIT` decides, so the same property is compared across the four rather than
    a different one per product.
    """
    for spec in specs:
        if spec.ranks:
            return spec
    return None
