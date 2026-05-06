# 22. Live deployment to picwise.subby.cloud

Stage 22 is prepared as **deployment readiness** for the production target and is not marked live until URL proof exists.

## Deployment Target

- domain target: `picwise.subby.cloud`
- GitHub repo: `picwise.concept`
- branch: `main`

## Current Deployment Entrypoints

- local run entrypoint: `run_picwise_app.py`
- deployment WSGI entrypoint: `wsgi.py` (`app`)
- Vercel runtime entrypoint: `api/index.py` (`app`)

## Hosting Setup Steps (Required)

1. Ensure repository root contains:
   - `vercel.json`
   - `api/index.py`
   - `wsgi.py`
2. Confirm deployment app routes return expected responses:
   - `GET /health` -> JSON health payload
   - `GET /demo` -> HTML demo page
3. Confirm demo output still includes explicit fixture markers:
   - `local_test_fixture`
   - `not_production_data`
4. Run tests before deploy:
   - `python -m unittest discover -s tests`

## Vercel and Domain Steps (Required If Vercel Is Used)

1. Import `picwise.concept` into Vercel and set production branch to `main`.
2. Confirm Python runtime build uses `api/index.py` from `vercel.json`.
3. Add custom domain `picwise.subby.cloud` in Vercel project settings.
4. Configure DNS records in the domain provider exactly as instructed by Vercel.
5. Wait for SSL certificate issuance and domain verification.
6. Verify production routes after DNS is active:
   - `https://picwise.subby.cloud/health`
   - `https://picwise.subby.cloud/demo`

## Environment Variable Policy

- No secrets are committed to the repository.
- Keep credentials/API keys only in hosting provider environment settings.
- Template files may only contain placeholders or non-secret status markers.

## Live Proof Checklist

- [ ] `https://picwise.subby.cloud/health` works
- [ ] `https://picwise.subby.cloud/demo` works

## Honest Status Rule

If not live proven, mark `NEEDS_LIVE_PROOF` or `DEPLOYMENT_READY`, not `PASSED`.

Current stage status in this repository remains `DEPLOYMENT_READY` until the two live URLs above are verified.

