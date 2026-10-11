# Implementation Plan: Integration Health Checks and Alerts

**Branch**: `feature/integration-health-alerts` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-integration-health-alerts/spec.md`

## Summary

Add a secret-protected `GET /health/integrations` that runs cheap live probes against every
external dependency (database, primary and fallback LLM, SendGrid, Firebase Auth/FCM,
RevenueCat, Shopify) concurrently with per-probe timeouts, returns per-integration
`up`/`down`/`not_configured` with latency, and logs one `integration_down` line per failure.
Cloud Scheduler calls it every 15 minutes per environment; Cloud Monitoring turns the log line,
real-traffic error lines, uptime checks and 5xx rates into email alerts to admin@onlyblv.com
(30-minute re-notify, auto-close). The public diagnostic endpoints are locked behind the same
secret, all scheduler endpoints use the fail-closed `require_cron_secret` added in the metrics
hotfix (#26), and `scripts/monitoring/setup.sh` recreates all monitoring idempotently.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, SQLAlchemy, Firebase Admin, httpx (already used by
`revenuecat.py`/`shopify_admin.py`), `app/services/llm/` providers. No new packages.

**Storage**: N/A (no tables; results are returned and logged, not stored)

**Testing**: pytest (`tests/`, SQLite in-memory via conftest fixtures); every probe mocked

**Target Platform**: Google Cloud Run (`trooth-backend`, `trooth-backend-dev`, us-east4) plus
Cloud Scheduler, Cloud Logging and Cloud Monitoring in project `trooth-prod`

**Project Type**: web-service (client: Flutter app in `trooth_assessment`, unaffected)

**Performance Goals**: full check returns in < 30 s even if one integration hangs (10 s
per-probe timeout, all concurrent); typical < 5 s

**Constraints**: no user-visible side effects (no delivered email/push, no purchases, no data
writes); AI probes ≤ 16 output tokens with 1 attempt each so monthly cost stays well under $5
(SC-005); results never contain secrets

**Scale/Scope**: 2 environments × 96 runs/day; 8 integrations; ~6 alert policies per env

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Source: `.specify/memory/constitution.md`.

- [x] **I. Auth** ✅: `/health/integrations` and the existing `/health/health/{detailed,llm,metrics}`
  use `require_cron_secret` (`app/services/auth.py`, fail-closed, constant-time). Basic
  `/health` stays public by design (uptime checks, app). No user data → no
  `MentorApprentice`/premium checks apply. No test shortcuts.
- [x] **II. Errors** ✅: 403 via `HTTPException` from `require_cron_secret`; a failing probe is a
  `down` result in a 200 body, not an error response; no traces returned.
- [x] **III. Migrations** N/A: no schema changes.
- [x] **IV. Config & secrets** ✅: reuses `CRON_SECRET` (already in both deploy secret lists);
  removes the `"dev-cron-secret-change-in-prod"` fallbacks in `campaigns.py` and
  `scheduled_tasks.py` (grandfathered debt, fixed because touched). The RevenueCat probe id and
  thresholds are non-secret settings with defaults. No deploy env/secret list changes.
- [x] **V. Logging** ✅: `logging.getLogger(__name__)`; probe errors are truncated and scrubbed of
  key-like substrings before logging/returning.
- [x] **VI. Compatibility** ✅: new endpoint is additive; the three diagnostic endpoints go from
  public to secret-protected, which the spec records (no app version, site or script calls
  them). Scheduler endpoints keep the same header and 403. New route declares a `response_model`.
- [x] **VII. Layering** ✅: probes live in `app/services/integration_health.py`; LLM probes go
  through `app/services/llm/` providers (`primary_provider` / `fallback_provider`), never an SDK
  from a route.
- [x] **VIII. Tests** ✅: endpoint success + 403 (no secret, wrong secret, unset secret) for every
  protected route; probe aggregation, timeout and scrubbing tests with all integrations mocked;
  no live calls. `pytest` must pass.
- [x] **IX. Deploy** ✅: `/deploy-dev`, run the setup script for dev, kill-switch test, then prod
  from `main`.
- [x] **X. Contract** ✅: [contracts/health-integrations.md](contracts/health-integrations.md). No
  frontend spec (no app change).
- [x] **XI. Formatting** ✅: new files only; no reformatting of touched files.

## Project Structure

### Documentation (this feature)

```text
specs/003-integration-health-alerts/
├── spec.md
├── plan.md              # this file
├── research.md          # probe choices, alerting design
├── data-model.md        # result/report shapes, log line format
├── quickstart.md        # dev validation incl. kill-switch test
├── contracts/
│   └── health-integrations.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
app/
├── services/integration_health.py   # NEW: probes, run_all(), scrubbing, integration_down logging
├── services/auth.py                 # require_cron_secret (exists, from #26)
├── schemas/health.py                # NEW: IntegrationResult, IntegrationsReport
├── routes/health.py                 # + GET /integrations; lock detailed/llm/metrics
├── routes/campaigns.py              # use require_cron_secret (drop local verify + default)
├── routes/scheduled_tasks.py        # use require_cron_secret (drop local verify + default)
└── core/settings.py                 # + revenuecat_healthcheck_app_user_id
scripts/monitoring/
├── setup.sh                         # NEW: idempotent channel/scheduler/uptime/metrics/policies
└── README.md
tests/test_integration_health.py     # NEW
```

**Structure Decision**: single FastAPI service; integration logic in `app/services/`, routing in
`app/routes/health.py`; monitoring as code in `scripts/monitoring/` (gcloud + Monitoring REST,
since `gcloud alpha/beta` components aren't installed here).

## Complexity Tracking

No constitution violations.
