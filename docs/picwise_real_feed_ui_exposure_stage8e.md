# Stage 8E — Safe UI Exposure for Real Feed 4+1

## Scope

UI-only exposure of Stage 8D backend real-feed 4+1 results in the PicWise reference/search surface.

## Active renderer

- File: `src/picwise_surface/reference.py`
- Entry: `render_picwise_reference_surface()`
- Card builders:
  - Manual Amazon: `_build_result_cards()`
  - Real feed 4+1: `_build_provider_feed_result_cards()` (guarded by `_provider_feed_ui_display_allowed()`)

## Display gate

Feed cards render only when all are true:

- `provider_feed_selection_status == "selected"`
- `provider_feed_decision_status == "recommended"`
- exactly 4 selected products with complete real fields
- recommended product ID is one of the selected four
- non-empty recommendation reason codes
- provider key is a real feed provider (`awin`), not demo/fake

Otherwise the existing safe empty/disclaimer states are preserved.

## Honest copy

- Query line: `Showing 4 selected real products for: …`
- Disclaimer: selected real products from connected feed; one recommended from four based on search fit
- Recommended note: `Recommended from these 4.`
- Provider label example: `Geekbuying via Awin`

## Unchanged

- Manual Amazon `power_banks` path
- Layout, colors, animations, header, footer, search bar
- Broad-query, blocked, provider-not-connected safe states
- Search artifact and provider ranking logic

## Tests

```powershell
$env:AWIN_FEED_FILE="C:\Users\User\Desktop\picwise-private-feeds\geekbuying_feed.csv.gz"
python -m unittest tests.test_picwise_real_feed_ui_exposure_stage8e
```
