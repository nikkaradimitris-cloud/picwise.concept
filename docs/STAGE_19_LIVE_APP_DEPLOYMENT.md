# 19. Live app deployment

Stage 19 is implemented as **deployment readiness** only.

## What is included

- local app launch command: `python run_picwise_app.py`
- deployment planning baseline for primary domain `picwise.subby.cloud`
- environment variable templates with names only (no secrets)
- non-live operational checklist for moving from local to real deployment

## What is intentionally not included

- no live host provisioning performed
- no DNS changes executed
- no platform credentials committed
- no claim that production is live

## Readiness Checklist

- [x] app exposes `GET /health`
- [x] app exposes `GET /demo`
- [x] app runtime uses feed adapter -> engine -> surface flow
- [x] deployment config templates created without secrets
- [ ] live deployment proof (URL + deployment record)
- [ ] post-deploy runtime verification on `picwise.subby.cloud`

## Status

Deployment status: `DEPLOYMENT_READY`  
Not live deployed yet: live proof is still required before marking PASSED.
