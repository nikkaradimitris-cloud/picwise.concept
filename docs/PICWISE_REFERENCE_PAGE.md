# Picwise Reference Page (Stage A)

The `/picwise-reference` route is a locked static visual reference page.

## Asset slots

Place stable local product images at:

- `assets/picwise/product-1.png`
- `assets/picwise/product-2.png`
- `assets/picwise/product-3.png`
- `assets/picwise/product-4.png`

Placeholder files are already present at those exact paths and can be replaced in-place.

## Local view

Start the local app:

`python run_picwise_app.py`

Then open:

`http://127.0.0.1:8016/picwise-reference`

## Manual screenshot capture

Automation is intentionally skipped to avoid adding browser dependencies in this stage.

Use this manual path:

1. Open `http://127.0.0.1:8016/picwise-reference` in a desktop browser.
2. Capture a full-page screenshot.
3. Save as `artifacts/screenshots/picwise-reference.png`.
