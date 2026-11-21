"""The brakes of the rules' section 7: what stands between a fault of ours and the catalogue.

Owner, 2026-11-21: «μόνο ένα φρένο για λάθη»; a night that cuts unusually many stops the
removal; and, the same evening, «Όχι, κόβει από το πρώτο βράδυ»: no nights of report only.
So the checks cut from their first night, and these are their only safeguard. Their
numbers are Proposed (rules 13.2) and the owner's to change; each is pinned by a test
named after its section (`tests/test_picwise_checks_brakes.py`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

# 7.1: a round in which fewer than half of the shops asked gave any answer is ours.
ROUND_ANSWERED_SHARE = 0.5
# 7.2: a shop's night.
SHOP_MIN_DECIDED = 20
SHOP_NEW_FAILURES_SHARE = 0.25
SHOP_MIN_PASSES = 20
# 7.3: a kind's night.
KIND_MIN_SHOWN = 40
KIND_NEW_CUTS_SHARE = 0.25
# 7.4: the whole night.
NIGHT_MIN_SHOPS = 6
NIGHT_SHOPS_BRAKED_SHARE = 1 / 3
NIGHT_NEW_CUTS_SHARE = 0.10
NIGHTS_STOPPED = 2
# 7.5: a reader proves itself in a shop over its tied readings of the last 7 nights.
PROOF_NIGHTS = 7
PROOF_MIN_READINGS = 20
PROOF_SAME_SHARE = 0.7
# 5.6.3: a reading of Awin that would put out many shops at once waits for the owner.
AWIN_MAX_SHOPS = 3
AWIN_MAX_PRODUCTS_SHARE = 0.05
# 7.6: the checks' own calls to the AI stop for the night here: a stop for a loop gone
# wrong, not a budget (owner: no daily limit of cost).
AI_NIGHT_STOP_DOLLARS = 10.0

# What a shop's brake says (7.2).
NO_BRAKE = ""
HOLD = "hold"
HOLD_FOR_OWNER = "hold for the owner"


def round_is_ours(shops_asked: int, shops_answered: int) -> bool:
    """7.1: fewer than half of the shops asked gave any answer at all: the fault is on
    our side (the server's network); the round records nothing."""
    return shops_asked > 0 and shops_answered < ROUND_ANSWERED_SHARE * shops_asked


def shop_brake(decided: int, new_failures: int, passes_on_record: int) -> str:
    """7.2: of a shop's products decided on a night (at least 20), more than a quarter
    failing that were not failed the night before holds them for a second look; where
    the shop has fewer than 20 passes on record, until a look and the owner's word."""
    if decided < SHOP_MIN_DECIDED or new_failures <= SHOP_NEW_FAILURES_SHARE * decided:
        return NO_BRAKE
    return HOLD if passes_on_record >= SHOP_MIN_PASSES else HOLD_FOR_OWNER


def kind_brake(shown: int, new_cuts: int) -> bool:
    """7.3: a night's new cuts would take more than a quarter of the products a kind
    shows (at least 40 shown)."""
    return shown >= KIND_MIN_SHOWN and new_cuts > KIND_NEW_CUTS_SHARE * shown


def night_brake(shops_decided: int, shops_braked: int, new_cuts: int, shown: int) -> bool:
    """7.4: the shop's brake holds for more than a third of the shops decided that night
    (at least 6 shops), or the night's new cuts pass 10% of the products shown: nothing
    new is cut that night."""
    if shops_decided >= NIGHT_MIN_SHOPS and shops_braked > NIGHT_SHOPS_BRAKED_SHARE * shops_decided:
        return True
    return shown > 0 and new_cuts > NIGHT_NEW_CUTS_SHARE * shown


def cutting_stopped(recent_night_brakes: Iterable[bool]) -> bool:
    """7.4: two whole-night brakes running stop the cutting until a look and the owner's
    word. `recent_night_brakes`: the last nights' brakes, the latest last."""
    last = list(recent_night_brakes)[-NIGHTS_STOPPED:]
    return len(last) == NIGHTS_STOPPED and all(last)


@dataclass(frozen=True)
class Proof:
    tied: int
    same: int

    @property
    def share(self) -> float:
        return self.same / self.tied if self.tied else 0.0


def reader_proof(nights: Iterable[tuple[int, int]]) -> Proof:
    """The tied readings of the last 7 nights and how many said what the feed says."""
    last = list(nights)[-PROOF_NIGHTS:]
    return Proof(tied=sum(tied for tied, _same in last), same=sum(same for _tied, same in last))


def reader_proven(nights: Iterable[tuple[int, int]]) -> bool:
    """7.5: at least 20 tied readings over the last 7 nights, at least 7 in 10 of them
    the same as the feed's: only then may the reader overrule the feed in that shop."""
    proof = reader_proof(nights)
    return proof.tied >= PROOF_MIN_READINGS and proof.same >= PROOF_SAME_SHARE * proof.tied


def awin_waits(shops_out: int, products_out: int, shown: int) -> bool:
    """5.6.3: a reading of Awin that would put out more than 3 shops, or shops holding
    over 5% of the products shown, in one night changes nothing that night."""
    return shops_out > AWIN_MAX_SHOPS or (shown > 0 and products_out > AWIN_MAX_PRODUCTS_SHARE * shown)


def commonest_ratio(pairs: Iterable[tuple[float, float]]) -> float | None:
    """For the report of a shop whose reader is not proven (7.5): the commonest ratio of
    the site's price to the feed's, to two decimals (1.2 is VAT; 100 is pence)."""
    counts: dict[float, int] = {}
    for site, feed in pairs:
        if feed > 0 and site > 0:
            ratio = round(site / feed, 2)
            counts[ratio] = counts.get(ratio, 0) + 1
    if not counts:
        return None
    return max(sorted(counts), key=lambda ratio: counts[ratio])
