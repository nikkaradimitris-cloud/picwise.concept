# Picwise Production

Current status (2026-11-09): **live on PicWise's own server with the real Awin feed; the
search is in its big general debugging (owner, 2026-11-07); nothing is given to Google
yet.**

Where the work is now: the first section of `docs/picwise_session_handoff.md` ("START
HERE"). `PROGRESS.md` is the chronological log.

## Mandatory Reading Order

1. `PROJECT_RULES.md` (mandatory first read)
2. `concept.picwise.txt` (product concept source of truth)
3. `docs/` (implementation contracts/specs)
4. `docs/picwise_session_handoff.md`, its first section, and the last entries of `PROGRESS.md`

## What Is Live (2026-11-09)

- `https://picwise.subby.cloud` is served by PicWise's own server since 2026-10-31
  (OVHcloud VPS-4, London; HTTPS by Caddy; `docs/PICWISE_SERVER_ARCHITECTURE.md`).
  Vercel is kept as the backup: deleting the domain's A record puts the site back there.
- The catalogue: Awin's Create-a-Feed link with the Google-format shops (`AWIN_FEED_URL`),
  prepared each night on the server. On 2026-11-09: 597,876 products a card can show,
  242,869 of them kept by the cap of 15% a category (`PROJECT_RULES.md` section 13).
- A search: 4 choices with exactly 1 Recommended, only products in stock, those on a
  current shop offer first and then the cheapest first, commission never a criterion
  (`PROJECT_RULES.md` section 2, `docs/PICWISE_DECISION_CONTRACT.md`). The search reads
  English only. An AI layer marks the products that fit a complex search, since
  2026-11-06, at most one euro a day (`docs/PICWISE_AI_LAYER_SPEC.md`).
- The site's own search pages carry `noindex`. No page is given to Google yet: its pages
  are specified, not built (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`).
- The work goes on every day: a scheduled session at about 12:00 Greek time, a report in
  Greek by email, the site changed only after the owner's «ναι»
  (`docs/PICWISE_DAILY_WORK.md`).

## Branches And Deployment

- **Work:** `ccr-4f47068a-99ikwe`. Each session starts from it and pushes its commits
  there too (`docs/PICWISE_DAILY_WORK.md`).
- **The server:** a push to `ccr-1361f1a7-dcpo60` deploys the pushed commit
  (`.github/workflows/server-deploy.yml`, `deployment/server/deploy.sh`), only on the
  owner's word for that push («ανέβασε»).
- **`main`:** what is live plus its records, moved only on the owner's yes (last on
  2026-11-09), by a fast-forward to the work's branch, so the two stay one line. A push
  to `main` makes Vercel build the backup (`vercel.json`, `api/index.py`), and Vercel
  rebuilds `main` each morning (`/cron/renew-prepared-feed`).
- **Read-only checks:** each workflow in `.github/workflows` runs on a push to the branch
  its file names, never on `main`; some name an older session branch (`server-setup.yml`
  on `ccr-baaad713-r3uvvs`, `live-check.yml` on `ccr-fd5dc1bc-4vgsgl`), which is why
  those branches are kept.
- WSGI entrypoints: `wsgi.py` (`app`) and `api/index.py` (`app`); the server runs them
  through `deployment/server/wsgi_server.py`.

## Build Policy

- Keep recommendation logic revenue-neutral and non-fake.
- Do not commit real credentials or API keys, nor a feed file: the repository is public,
  and a feed file carries every row's Awin tracked link with the owner's publisher ID.
- Do not claim live Subby integration without proof.
- Do not claim click, commission or conversion tracking without proof.

## Secrets (Names Only, Never In The Repository)

- GitHub Actions secrets, passed to the server by the workflows: `SERVER_HOST`,
  `SERVER_USER`, `SERVER_SSH_KEY`, `AWIN_FEED_URL`, `AWIN_FEED_URL_NEW` (only for the
  check before the feed link is replaced), `AWIN_API_TOKEN`, `AWIN_PUBLISHER_ID`,
  `ANTHROPIC_API_KEY`.
- Vercel, for the backup: its own `AWIN_FEED_URL`, `PICWISE_DEPLOY_HOOK_URL` and
  `CRON_SECRET` among others.
- The May design's names (`PICWISE_FEED_SOURCE_*`, `PICWISE_AFFILIATE_*`,
  `PICWISE_SUBBY_*`, in `deployment/app.env.template`) belong to the adapters of stages
  23 and 24; the live site does not use them.

## Local Run

- Run app: `python run_picwise_app.py`
- Local URL: `http://127.0.0.1:8016`
- Demo URL: `http://127.0.0.1:8016/demo?q=power+bank+20000mah+for+iphone`

## Tests

- Command: `python -m unittest discover -s tests`
- Two modules are known to fail, the same test each since before 2026-10-23:
  `test_picwise_canonical_vocabulary_registry_stage2` and
  `test_picwise_search_index_generated_blind_stage4`.

### Search runtime artifact

`src/picwise_search_memory/artifacts/search_runtime_v1.json.gz` is committed and must
match its fingerprint sources. When it does not, the app silently falls back to building
the search index live and the first request misses the render target. Rebuild after
changing vocabulary or taxonomy deep packs:

```bash
python tools/build_picwise_search_artifact.py
```

`tests/test_picwise_mission_decision_delivery.py` fails when the artifact is stale.

### Local provider feed fixture

The real-feed provider pipeline can be run without the operator's private Awin feed:

- Feed: `tests/fixtures/provider_feed_local_test_fixture.csv`
- Coverage: `python -m unittest tests.test_picwise_provider_feed_local_fixture`
- Runtime capture: `python tools/runtime_truth_audit.py`
- Details: `docs/picwise_local_provider_feed_fixture.md`

This fixture is local test data (`local_test_fixture`, `.invalid` URLs only). It is not
real-feed proof and must not be used to close real feed/affiliate stages.

A second fixture, `tests/fixtures/provider_feed_coverage_matrix_fixture.csv`, holds four
products for each of 27 product types across all 18 mega categories and drives the
product-type coverage matrix:

```bash
python -m unittest tests.test_picwise_product_type_coverage_matrix
```

See `docs/picwise_product_type_coverage_matrix.md`.

## Live Status Honesty

- Primary domain: `picwise.subby.cloud`. `picwise.cloud` remains an optional future
  standalone domain.
- Live, with proof recorded in `PROGRESS.md`: the site on PicWise's own server (its
  deployments and checks, the last run `42606594412` on 2026-11-09) and the real Awin
  feed (first live proof 2026-10-11).
- Not live: the Subby dashboard (stages 20 and 24, no live Subby proof); Awin's offers
  since 2026-11-03 (Awin answers 401: a new token is the owner's to make); any page for
  Google; any click, commission or conversion tracking.
- The roadmap table of May 2026 in `PROGRESS.md` keeps its statuses. Stage 22 is PASSED
  because operator proof exists for:
  - `https://picwise.subby.cloud/health`
  - `https://picwise.subby.cloud/demo`
- Stages 19-21 and 23-25 stay as recorded there. 23 is not PASSED: no session ever
  clicks a shop's Awin tracked link (an automated click is a fake click), so no click
  or commission proof is recorded. 24 needs live Subby proof; 25 needs 23 and 24.
