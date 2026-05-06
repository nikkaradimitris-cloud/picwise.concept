# Picwise Production

Current status: **local app implementation + production-path readiness (not live)**.

## Mandatory Reading Order

1. `PROJECT_RULES.md` (mandatory first read)
2. `concept.picwise.txt` (product concept source of truth)
3. `docs/` (implementation contracts/specs)

## Repository Scope (Current Phase)

- This repository now includes contracts, engine, surface, and local app implementation layers.
- Docs in `docs/` define implementation contracts and readiness notes.
- Local app endpoints exist: `GET /health` and `GET /demo`.
- Demo data is explicitly marked `local_test_fixture` and `not_production_data`.
- No fake revenue/conversion metrics are introduced.

## Build Policy

- Keep recommendation logic revenue-neutral and non-fake.
- Do not commit real credentials or API keys.
- Do not claim live deployment or live Subby integration without proof.

## Local Run

- Run app: `python run_picwise_app.py`
- Local URL: `http://127.0.0.1:8016`
- Demo URL: `http://127.0.0.1:8016/demo?q=power+bank+20000mah+for+iphone`

## Tests

- Command: `python -m unittest discover -s tests`

## Live Status Honesty

- Primary domain plan remains `picwise.subby.cloud`.
- Optional future standalone domain remains `picwise.cloud`.
- Stage 19 is deployment-ready only unless live deploy proof exists.
- Stage 20 is integration-ready only unless live Subby proof exists.
