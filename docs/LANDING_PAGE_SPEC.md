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

## Search Box

Added on 2026-10-16 by the owner.

- As the buyer types, the likely word is completed in faint letters; a tap fills it in.
- Word suggestions appear below from the first letter and narrow with each letter
  ("l" -> laptop, lamp).
- A microphone: the buyer speaks and the words are written.
- Below the box: trends; a tap puts the word in the box and shows the products.
- Trends state only what is known (ANTI_FAKE): seasonal picks labelled as such at first,
  then the most frequent searches on PicWise. "What people buy" only once real
  purchase data exists.
- While a search runs, a scanning screen shows what is happening: searching N shops
  and M products, found these, cross-checking, sending. It appears within 1.5 s, and
  the results may follow within about 4 s. Only true facts; never a deliberate delay.
- PicWise will also install on phones as an app, and later go to the Play Store. Links
  to shops open in the phone's browser, so the shop's cookie is set where the buyer
  buys.

### Built in step 4 (2026-10-17)

Wording, chosen by the owner on 2026-10-17:
- The box reads "What are you looking for?" (placeholder and label). The owner chose
  it over "Search any product, cheapest first" because it promises nothing a shop
  reviewing PicWise for its affiliate programme could object to.
- "What is PicWise?" reads: "PicWise finds the product you want in the shops it is
  connected to, shows what the shops list as in stock, cheapest first, and marks one mid-priced
  Recommended."

Everything below needs JavaScript and adds to the page; without it the box is a plain
form and the search works as before.

- **Scanning screen.** On a search (the box, a suggestion, the microphone) or on
  "More", the page shows at once: "Searching 39,815 products from 2 shops for
  "laptop"…". The numbers are the products PicWise can show and the shops they come
  from, as the server last loaded them; a page that has not loaded the feed yet says
  "Searching the shops connected to PicWise for "laptop"…". It names no step the
  browser cannot see: finding, checking and sending happen on the server within the one
  request, so the screen does not narrate them. It goes as soon as the results page
  arrives; nothing waits for it.
- **Suggestions.** From the first letter, up to 8 suggestions under the box, and the
  first one completed in faint letters inside it: Tab or the right arrow, or a tap on
  the faint letters, fills it in; a tap on a suggestion searches it. They are the
  names of the kinds PicWise knows, in English and Greek, and a brand with a kind
  ("samsung smartphone"), each offered only when the search returns products from
  the connected shops, the larger first. Accents and case do not matter. The list is
  fetched once (`/suggest.json`, kept by the browser for an hour), so a keystroke
  costs no request to the server.
- **Microphone.** A button in the box, shown only where the browser can turn speech
  into text (Chrome, Edge, Safari; not Firefox). The words appear in the box as they
  are spoken, and the search starts when the buyer stops (owner, 2026-10-17), through
  the same understanding as typed words. The browser's own speech service does the
  listening: in Chrome the audio goes to Google. The privacy page says so.

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
