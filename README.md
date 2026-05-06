# Picwise Production

Current status: **local implementation + partial live proof (stage 22 only)**.

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
- Do not claim live feed/affiliate integration without provider proof.

## Local Run

- Run app: `python run_picwise_app.py`
- Local URL: `http://127.0.0.1:8016`
- Demo URL: `http://127.0.0.1:8016/demo?q=power+bank+20000mah+for+iphone`

## Deployment Readiness

- Deployment target domain: `picwise.subby.cloud`
- WSGI entrypoint for deployment: `wsgi.py` (`app`)
- Vercel function entrypoint: `api/index.py` (`app`)
- Vercel routing config: `vercel.json`

## Required Env Variable Names (No Secrets In Repo)

- Feed/source:
  - `PICWISE_FEED_SOURCE_TYPE`
  - `PICWISE_FEED_SOURCE_URL`
  - `PICWISE_FEED_API_KEY`
- Affiliate/redirect:
  - `PICWISE_AFFILIATE_PROVIDER`
  - `PICWISE_AFFILIATE_TRACKING_ID`
  - `PICWISE_AFFILIATE_REDIRECT_TEMPLATE`
- Subby:
  - `PICWISE_SUBBY_ENDPOINT`
  - `PICWISE_SUBBY_PROJECT_ID`
  - `PICWISE_SUBBY_API_KEY`

## Tests

- Command: `python -m unittest discover -s tests`

## Live Status Honesty

- Primary domain plan remains `picwise.subby.cloud`.
- Optional future standalone domain remains `picwise.cloud`.
- Stages 23-25 are currently not live.
- Stage 19 is deployment-ready only unless live deploy proof exists.
- Stage 20 is integration-ready only unless live Subby proof exists.
- Stage 22 is PASSED because operator proof exists for:
  - `https://picwise.subby.cloud/health`
  - `https://picwise.subby.cloud/demo`
- Stage 23 remains non-PASSED until real feed/affiliate config and live proof exist.
- Stage 24 remains non-PASSED until real Subby config and live dashboard proof exist.
- Stage 25 remains `NEEDS_LIVE_PROOF` until stages 23 and 24 have live proof.
