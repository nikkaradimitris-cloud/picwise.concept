# Landing Page Specification

## Purpose

Landing pages must terminate search intent quickly by presenting decision-ready outputs.

## Above-the-Fold Requirements

Must include, immediately visible:
- query confirmation text
- 4 primary choice cards
- 1 visually emphasized recommended card
- the counter ("4 of 45")
- clear CTA on each card

Must not include:
- heavy hero that pushes choices below fold
- empty search-like first state
- an infinite scroll that loads on its own ("More" is a button the buyer presses)

## Card Structure Requirements

Each choice card must show:
- role badge
- decision label (decision-focused, not raw spec dump)
- subtitle (cost + key benefit + reassurance)
- 2-3 key reasons
- risk/limitation note
- CTA

Recommended card must additionally show:
- "Recommended" marker
- stronger visual emphasis
- concise recommendation reason

## More Options Behavior

Changed on 2026-10-16 by the owner: "price first" (`docs/picwise_price_first_plan_2026-10-15.md`).

- "More" is below the first 4 choices, on every search.
- Each press opens the next 4 cheapest, as often as the buyer asks, until the list ends.
- A counter shows how many are shown: "4 of 45", "8 of 45".
- Nothing opened by "More" is recommended.
- It is a button the buyer presses, not an infinite scroll that loads on its own.

## Accessibility and Clarity

- Decision text must remain scannable and concise.
- UI must reduce decision time, not increase browsing effort.
- Accessibility standards baseline: TODO

## Non-Compliance Conditions

Any of the following is non-compliant:
- missing 4+1 structure
- missing recommended rationale
- missing CTA or redirect mapping
- fake data or fake urgency
- commission-first recommendation behavior
