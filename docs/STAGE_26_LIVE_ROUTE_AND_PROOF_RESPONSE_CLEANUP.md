# 26. Live route and proof response cleanup

Stage 26 aligns live routing and proof-response behavior with observed production behavior while keeping safety and honesty constraints intact.

## What changed

- `GET /` now serves the same Picwise landing surface as `GET /demo`.
- `GET /demo` remains available and continues to render the landing surface.
- Landing HTML was polished with lightweight inline CSS and clearer structure while remaining dependency-free.
- `GET /subby-proof` timeout behavior now returns `sent_unconfirmed` with `dashboard_check_required: true` when the outbound request may have been accepted but the response timed out.

## Timeout response model for `/subby-proof`

When a timeout/read-timeout happens after attempting the outbound bridge request, Picwise returns:

- `status: "sent_unconfirmed"`
- `bridge_http_status: null`
- `dashboard_check_required: true`
- `safe_error_type: "TimeoutError"`
- `safe_error_message: <sanitized>`
- `message: "Request may have reached Subby but response timed out. Check Subby dashboard for accepted payload."`
- `secret_values_exposed: false`

For rejected/HTTP error responses, status remains `rejected` or `error` with `bridge_http_status` where available.

## Compliance notes

- This stage does **not** close stage 23.
- This stage does **not** close stage 25.
- No fake data was introduced.
- No secrets are exposed in API responses.
