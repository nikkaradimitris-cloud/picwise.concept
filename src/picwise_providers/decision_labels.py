"""Fact-derived decision labels for the four selected provider-feed choices.

`docs/PICWISE_DECISION_CONTRACT.md` requires a `role_label`, `decision_label`,
`key_reasons` and `risk_or_limitation` on every one of the four choices. PROJECT_RULES
section 4 forbids inventing business logic, and the contract leaves the ranking formula
as TODO, so nothing here expresses a judgement about which product is better.

Every string this module produces restates something the feed or the purchasability
verifier already established:

- price rank within the four, which is arithmetic over the prices themselves
- whether purchase availability was verified, or only claimed by the feed
- brand or product type, copied from the row

There is deliberately no "best for", "great value" or "premium" vocabulary: PicWise holds
no reviews, benchmarks or fitness data that could support such a claim, so making one
would be fake data under PROJECT_RULES section 4.

Labels are descriptive only. They never reorder the choices and never influence which
choice is recommended.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .product_condition import non_new_condition as read_non_new_condition
from .product_condition import product_text_for_condition, stated_condition

_PRICE_NUMBER_RE = re.compile(r"\d[\d.,]*\d|\d")

_ORDINAL_PREFIXES = {2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}

UNCOMPARABLE_PRICE_ROLE_LABEL = "Price not comparable with the others"
SAME_PRICE_ROLE_LABEL = "Same price as the other choices"
VERIFIED_RISK = (
    "Purchase availability was verified on the merchant page. "
    "The store can still change price or stock."
)
UNVERIFIED_RISK = (
    "PicWise has not verified that this purchase can be completed. "
    "Availability comes from the provider feed only."
)


@dataclass(frozen=True)
class ChoiceDecisionLabels:
    """Contract label fields for one choice, all derived from feed or verifier facts."""

    choice_id: str
    role_label: str
    decision_label: str
    key_reasons: tuple[str, ...]
    risk_or_limitation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "choice_id": self.choice_id,
            "role_label": self.role_label,
            "decision_label": self.decision_label,
            "key_reasons": list(self.key_reasons),
            "risk_or_limitation": self.risk_or_limitation,
        }


def parse_price_amount(price_text: str) -> float | None:
    """Read a comparable number out of a feed price string, or None.

    Feeds arrive in both conventions: "1,299.50" and "1.299,50" mean the same amount.
    Whichever separator comes last is the decimal separator; the other groups thousands.
    A single separator followed by exactly three digits is read as a thousands separator,
    the usual feed convention. Getting this wrong would invert a price rank and put a
    false "lowest price" label on the dearest product, so it is parsed rather than
    guessed at.
    """
    text = str(price_text or "")
    match = _PRICE_NUMBER_RE.search(text)
    if match is None:
        return None
    if match.start() > 0 and text[match.start() - 1] == "-":
        # A negative price is malformed, not a cheap offer.
        return None
    raw = match.group(0)
    has_dot = "." in raw
    has_comma = "," in raw
    if has_dot and has_comma:
        decimal_sep = "." if raw.rfind(".") > raw.rfind(",") else ","
        thousands_sep = "," if decimal_sep == "." else "."
        raw = raw.replace(thousands_sep, "").replace(decimal_sep, ".")
    elif has_dot or has_comma:
        separator = "." if has_dot else ","
        parts = raw.split(separator)
        if len(parts) == 2 and len(parts[1]) in {1, 2}:
            raw = f"{parts[0]}.{parts[1]}"
        else:
            raw = "".join(parts)
    try:
        value = float(raw)
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


def format_price_display(product: Mapping[str, Any]) -> str:
    """The feed price with its currency, as every price PicWise shows must read."""
    price_text = str(product.get("price_text") or "").strip()
    currency = str(product.get("currency") or "").strip()
    if not price_text:
        return ""
    if currency and currency.lower() not in price_text.lower():
        return f"{price_text} {currency}"
    return price_text


_FEED_LISTS_AS_AVAILABLE_STATES = frozenset({"trusted", "weak"})


def non_new_condition(product: Mapping[str, Any]) -> str:
    """What the feed said to call this choice not new, else "".

    Read through `product_condition`, the same module the selection gate reads, so a
    card cannot stay silent about a condition the selection acted on, or admit one the
    selection did not see. Since the owner decision of 2026-10-10 a non-new choice is
    only ever shown to a buyer who asked for that condition.
    """
    return read_non_new_condition(
        condition=stated_condition(product),
        text=product_text_for_condition(
            (product.get("title"), product.get("product_type"))
        ),
    )


def _is_verified_purchasable(product: Mapping[str, Any]) -> bool:
    if not bool(product.get("verified_purchasable")):
        return False
    state = str(product.get("purchasability_state") or "").strip().lower()
    return state == "purchasable"


def _price_ranks(amounts: Sequence[float | None]) -> dict[int, int]:
    """Competition-rank the comparable prices, cheapest first. Equal prices tie."""
    comparable = sorted(
        (amount, position)
        for position, amount in enumerate(amounts)
        if amount is not None
    )
    ranks: dict[int, int] = {}
    previous_amount: float | None = None
    previous_rank = 0
    for offset, (amount, position) in enumerate(comparable, start=1):
        if previous_amount is not None and amount == previous_amount:
            ranks[position] = previous_rank
            continue
        ranks[position] = offset
        previous_amount = amount
        previous_rank = offset
    return ranks


def _choice_count_phrase(choice_count: int) -> str:
    """The contract always yields four choices, but never hardcode the number."""
    return "these four" if choice_count == 4 else f"these {choice_count}"


def _role_label_for_rank(
    rank: int | None,
    *,
    comparable_count: int,
    choice_count: int,
) -> str:
    if rank is None:
        return UNCOMPARABLE_PRICE_ROLE_LABEL
    if comparable_count <= 1:
        return "Only option with a comparable price"
    scope = _choice_count_phrase(choice_count)
    if rank == 1:
        return f"Lowest price of {scope}"
    if rank >= comparable_count:
        return f"Highest price of {scope}"
    prefix = _ORDINAL_PREFIXES.get(rank)
    if prefix:
        return f"{prefix} lowest price of {scope}"
    return f"Price rank {rank} of {scope}"


def _decision_label(role_label: str, price_display: str, condition: str = "") -> str:
    if not price_display:
        label = role_label
    elif role_label in {UNCOMPARABLE_PRICE_ROLE_LABEL, SAME_PRICE_ROLE_LABEL}:
        label = f"{role_label} (listed at {price_display})"
    else:
        label = f"{role_label}, at {price_display}"
    # A price rank between a refurbished item and new ones compares different things;
    # say so next to the rank, where the buyer reads it.
    if condition:
        label = f"{label} · condition: {condition}"
    return label


def _key_reasons(product: Mapping[str, Any], price_display: str) -> tuple[str, ...]:
    reasons: list[str] = []
    if price_display:
        reasons.append(f"Feed price: {price_display}")
    brand = str(product.get("brand") or "").strip()
    product_type = str(product.get("product_type") or "").strip()
    if brand:
        reasons.append(f"Brand: {brand}")
    elif product_type:
        reasons.append(f"Feed product type: {product_type}")
    if _is_verified_purchasable(product):
        reasons.append("Purchase availability verified on the merchant page")
    elif str(product.get("availability_state") or "").strip().lower() in (
        _FEED_LISTS_AS_AVAILABLE_STATES
    ):
        reasons.append("Listed as available by the provider feed, not verified")
    else:
        # The feed's stock value is absent, unreadable, or a flag that is the same on
        # every row; "listed as available" would claim more than it says.
        reasons.append("Stock status not confirmed by the provider feed")
    return tuple(reasons[:3])


def build_fact_based_choice_labels(
    products: Sequence[Mapping[str, Any]],
) -> tuple[ChoiceDecisionLabels, ...]:
    """Build contract label fields for the selected choices, from facts only.

    Accepts the backend dicts of the selected products in display order and returns
    one entry per product, in the same order.
    """
    rows = list(products or ())
    if not rows:
        return tuple()
    amounts = [parse_price_amount(str(row.get("price_text") or "")) for row in rows]
    # Numbers in different currencies are not comparable: 100 USD against 90 GBP would
    # produce a false "lowest price". Rank only when every priced row agrees on currency.
    currencies = {
        str(row.get("currency") or "").strip().upper()
        for row, amount in zip(rows, amounts)
        if amount is not None
    }
    if len(currencies) > 1:
        amounts = [None] * len(rows)
    ranks = _price_ranks(amounts)
    comparable_count = len(ranks)
    distinct_amounts = {amount for amount in amounts if amount is not None}
    all_prices_equal = comparable_count > 1 and len(distinct_amounts) == 1
    labels: list[ChoiceDecisionLabels] = []
    for position, row in enumerate(rows):
        price_display = format_price_display(row)
        role_label = (
            SAME_PRICE_ROLE_LABEL
            if all_prices_equal and ranks.get(position) is not None
            else _role_label_for_rank(
                ranks.get(position),
                comparable_count=comparable_count,
                choice_count=len(rows),
            )
        )
        condition = non_new_condition(row)
        risk = VERIFIED_RISK if _is_verified_purchasable(row) else UNVERIFIED_RISK
        if condition:
            risk = f"Listed by the feed as {condition}, not new. {risk}"
        labels.append(
            ChoiceDecisionLabels(
                choice_id=str(row.get("provider_product_id") or "").strip(),
                role_label=role_label,
                decision_label=_decision_label(role_label, price_display, condition),
                key_reasons=_key_reasons(row, price_display),
                risk_or_limitation=risk,
            )
        )
    return tuple(labels)
