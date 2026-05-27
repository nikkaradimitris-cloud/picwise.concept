# PicWise Stage 8A Patch — Awin gzip feed support

## Problem

Real Awin merchant feeds are often distributed as `.csv.gz` files. The Stage 8A adapter loaded feed bytes and decoded them as plain text, which caused CSV parsing to fail on valid gzip payloads.

## Change

`src/picwise_providers/awin_adapter.py` now:

1. Detects gzip payloads before decode/parse:
   - file path ending in `.gz`
   - gzip magic bytes `1f 8b`
2. Decompresses gzip bytes with `gzip.decompress` for both `AWIN_FEED_FILE` and `AWIN_FEED_URL`.
3. Returns `provider_feed_parse_failed` for gzip, decode, and CSV/JSON parse failures instead of raising uncaught exceptions.

No UI, resolver wiring, Amazon manual affiliate, or search artifact changes were made.

## Safe statuses

| Status | Meaning |
| --- | --- |
| `provider_feed_not_configured` | No `AWIN_FEED_FILE` or `AWIN_FEED_URL` set |
| `provider_feed_parse_failed` | Feed load, gzip decompress, decode, or parse failed |
| `provider_feed_loaded` | Feed parsed and normalized products are present |

## Tests

- `tests/test_picwise_providers_stage8a.py`
  - gzip CSV fixture parses successfully
  - invalid gzip returns `provider_feed_parse_failed`
  - gzip magic bytes without `.gz` extension still decompress
  - missing fields are not faked
- `tests/test_picwise_provider_real_feed_gzip_stage8a_patch.py`
  - optional real Geekbuying `.csv.gz` proof when `AWIN_FEED_FILE` is set

## Local proof

```powershell
$env:AWIN_FEED_FILE="C:\Users\User\Desktop\picwise-private-feeds\geekbuying_feed.csv.gz"
python -m unittest tests.test_picwise_provider_real_feed_gzip_stage8a_patch
```
