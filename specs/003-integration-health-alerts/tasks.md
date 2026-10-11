---

description: "Task list for Integration Health Checks and Alerts"
---

# Tasks: Integration Health Checks and Alerts

**Input**: Design documents from `/specs/003-integration-health-alerts/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/health-integrations.md, quickstart.md

**Tests**: Per constitution Principle VIII, every new or changed endpoint gets tests for the success path and the authorization failures that apply (here: missing secret, wrong secret, unset `CRON_SECRET`), with every external integration mocked. Each story ends with `pytest` passing.

**Organization**: Tasks are grouped by user story so each can be implemented and verified on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)

---

## Phase 1: Setup

**Purpose**: shared scaffolding

- [x] T001 Create `scripts/monitoring/` with an executable `scripts/monitoring/setup.sh` (thin wrapper around `scripts/monitoring/setup.py`, which holds the idempotent logic) skeleton: `set -euo pipefail`, argument `dev|prod` mapped to `SERVICE` (`trooth-backend-dev` / `trooth-backend`), `API` (`https://trooth-discipleship-api-dev.onlyblv.com` / `https://trooth-discipleship-api.onlyblv.com`), `PREFIX` (`[dev]` / `[prod]`), `PROJECT=trooth-prod`, `REGION=us-east4`, and a `rest()` helper that calls `https://monitoring.googleapis.com/v3/projects/$PROJECT/...` with `gcloud auth print-access-token`
- [x] T002 [P] Add `revenuecat_healthcheck_app_user_id` (env `REVENUECAT_HEALTHCHECK_APP_USER_ID`, default `"healthcheck-probe"`, non-secret) to `app/core/settings.py`

---

## Phase 2: Foundational (blocks US1 and US4)

**Purpose**: response schemas and the shared secret dependency

- [x] T003 Create `app/schemas/health.py` with `IntegrationResult` (`name`: one of `database`, `llm_primary`, `llm_fallback`, `email`, `firebase_auth`, `firebase_messaging`, `revenuecat`, `shopify`; `status`: `up` | `down` | `not_configured`; `latency_ms`: int | null, "null when `not_configured`"; `detail`: str | null; `error`: str | null, "present only when `down`; ≤ 200 chars") and `IntegrationsReport` (`environment`, `status`: `healthy` | `degraded`, `checked_at` ISO-8601 UTC, `duration_ms`, `integrations`: "always all eight, fixed order")
- [x] T004 Confirm `require_cron_secret` in `app/services/auth.py` (from #26) is fail-closed and constant-time; no change expected, add a docstring note that health and scheduler routes use it

**Checkpoint**: schemas importable; `pytest` passes.

---

## Phase 3: User Story 1 - Know when an integration is down (Priority: P1) 🎯 MVP

**Goal**: a protected check exercises every integration and an email alert fires when one is down.

**Independent Test**: on dev, call `/health/integrations` with the secret (report lists all eight); with the known `llm_fallback` outage (or a broken `LLM_MODEL`), run the scheduler job and receive "[dev] Integration down" naming the integration; restore and receive the recovery email.

### Tests for User Story 1

- [x] T005 [P] [US1] In `tests/test_integration_health.py`: test `run_all()` with all probes mocked up → `status == "healthy"`, eight results in fixed order, latencies set
- [x] T006 [P] [US1] In `tests/test_integration_health.py`: one probe raises → that result `down` with scrubbed `error` (assert `sk-…`, `SG.…`, `AIza…`, `Bearer …` replaced with `***`, length ≤ 200), overall `degraded`, and exactly one `integration_down env=… integration=… error="…"` WARNING log line (caplog)
- [x] T007 [P] [US1] In `tests/test_integration_health.py`: one probe sleeps past the timeout → `down` with a timeout error while the others still return, total duration < 30 s (use a short timeout override in the test)
- [x] T008 [P] [US1] In `tests/test_integration_health.py`: Shopify not configured and fallback disabled → `not_configured` with `latency_ms` null and no log line
- [x] T009 [P] [US1] In `tests/test_integration_health.py`: `GET /health/integrations` → 200 with the contract shape when `X-Cron-Secret` matches; 403 with no header, a wrong header, and when `CRON_SECRET` is unset (monkeypatch env)

### Implementation for User Story 1

- [x] T010 [US1] Create `app/services/integration_health.py`: `scrub(error) -> str` (mask key-like substrings, truncate to 200), a `Probe` registry in fixed order, and `async run_all(timeout_s=10) -> IntegrationsReport` using `asyncio.gather` over `asyncio.wait_for(asyncio.to_thread(probe), timeout_s)`, logging `integration_down env=<settings.environment> integration=<name> error="<scrubbed>"` at WARNING per down result (logger `__name__`)
- [x] T011 [US1] In `app/services/integration_health.py` implement probes per research §1: `database` (`SELECT 1` via `SessionLocal`), `llm_primary` / `llm_fallback` (`get_llm_service().primary_provider` / `.fallback_provider`, `.generate("Reply with OK.", "OK", LLMConfig(max_tokens=16, max_retries=1, timeout_seconds=8, json_mode=False))`, `detail` = provider name, `not_configured` when fallback disabled, `down` when `response.success` is false), `email` (httpx `GET https://api.sendgrid.com/v3/scopes` with `settings.sendgrid_api_key`; `not_configured` if the key is empty or the placeholder), `firebase_auth` (`firebase_admin.get_app().credential.get_access_token()`), `firebase_messaging` (`messaging.send(Message(topic="healthcheck", data={"probe": "1"}), dry_run=True)`), `revenuecat` (httpx `GET {API_BASE}/subscribers/{settings.revenuecat_healthcheck_app_user_id}` with the secret key; `not_configured` without a key), `shopify` (`shopify_admin.is_configured()` else `not_configured`; token via `_get_access_token` + `{ shop { name } }` through `_graphql`)
- [x] T012 [US1] Add `GET /integrations` (`response_model=IntegrationsReport`, `dependencies=[Depends(require_cron_secret)]`) to `app/routes/health.py`, returning `await run_all()` (path is `/health/integrations` under the router's `/health` prefix)
- [x] T013 [US1] In `scripts/monitoring/setup.sh` add: email notification channel "admin@onlyblv.com" (find by `labels.email_address`, create via REST if missing); log-based metric `integration_down` (`gcloud logging metrics create|update`, filter `resource.type="cloud_run_revision" AND resource.labels.service_name="$SERVICE" AND textPayload:"integration_down"`, labels `integration`/`env` via `REGEXP_EXTRACT`); Cloud Scheduler job `integrations-health-$ENV` (`*/15 * * * *`, GET `$API/health/integrations`, header `X-Cron-Secret` from Secret Manager, attempt deadline 60s; create or update); alert policy "$PREFIX Integration down" (metric > 0 over 300s, grouped by `integration`, renotify 1800s, autoClose 1800s, documentation pointing at `/health/integrations`), all found by display name and patched instead of duplicated

**Checkpoint**: tests pass; on dev the report renders and a down integration produces an alert email.

---

## Phase 4: User Story 2 - Know when the service or website stops responding (Priority: P1)

**Goal**: outside checks alert when an API or onlyblv.com stops answering.

**Independent Test**: uptime checks show green for `$API/health` and `https://onlyblv.com/`; a temporary check on a failing URL opens and closes an alert.

- [x] T014 [US2] In `scripts/monitoring/setup.sh` add uptime checks "$PREFIX API /health" (`$API/health`, 60s period, ≥ 3 regions) and, for `prod` only, "onlyblv.com website" (`https://onlyblv.com/`), created with `gcloud monitoring uptime create` if no check with that display name exists
- [x] T015 [US2] In `scripts/monitoring/setup.sh` add alert policies "$PREFIX API down" and (prod) "onlyblv.com down" on `monitoring.googleapis.com/uptime_check/check_passed` false for 300s from ≥ 2 regions, email channel, renotify 1800s, autoClose 1800s

**Checkpoint**: both uptime checks green in the console; policies exist once.

---

## Phase 5: User Story 3 - Know when real users hit failures (Priority: P2)

**Goal**: alerts on real-traffic AI failures, scoring fallbacks, email failures and 5xx spikes.

**Independent Test**: on dev, trigger an AI failure (e.g. temporary bad `LLM_MODEL` and one assessment submission) and receive "[dev] AI generation failures" and "[dev] Scoring fallback".

- [x] T016 [US3] In `scripts/monitoring/setup.sh` add log-based metrics, each filtered by `resource.labels.service_name="$SERVICE"`: `llm_provider_error` (`textPayload:"[llm] provider=" AND textPayload:"error="`), `scoring_fallback` (`textPayload:"Failed to build mentor_blob"`), `email_send_failed` (`textPayload:"[email]" AND (textPayload:"Failed send" OR textPayload:"Exception during send" OR textPayload:"Skipping send" OR textPayload:"No from_email" OR textPayload:"Failed to instantiate")`)
- [x] T017 [US3] In `scripts/monitoring/setup.sh` add alert policies "$PREFIX AI generation failures", "$PREFIX Scoring fallback", "$PREFIX Email send failures" (each metric > 0 over 600s) and "$PREFIX Server errors" (`run.googleapis.com/request_count` with `response_code_class="5xx"` for `$SERVICE` > 5 over 300s), email channel, renotify 1800s, autoClose 1800s
- [x] T018 [US3] Verify the three log filters match today's log lines by running `gcloud logging read` with each filter against the last 7 days on dev and noting the counts in `scripts/monitoring/README.md`

**Checkpoint**: metrics and policies exist once per environment.

---

## Phase 6: User Story 4 - Diagnostic endpoints are not public (Priority: P2)

**Goal**: detailed health, LLM health/test-generation and server metrics need the secret; scheduler routes fail closed.

**Independent Test**: each endpoint returns 403 without the secret and 200 with it; `/health` stays public.

### Tests for User Story 4

- [x] T019 [P] [US4] In `tests/test_integration_health.py`: `/health/health/detailed`, `/health/health/llm` (with and without `test_generation=true`, LLM mocked) and `/health/health/metrics` → 403 without/with wrong secret and with `CRON_SECRET` unset; 200 with the secret; `/health` → 200 without a secret
- [x] T020 [P] [US4] In `tests/test_integration_health.py`: a `/campaigns/...` and a `/scheduled/...` route → 403 when `CRON_SECRET` is unset even if the caller sends `dev-cron-secret-change-in-prod`; still authorized with the real secret (mock the underlying job functions)

### Implementation for User Story 4

- [x] T021 [US4] In `app/routes/health.py` add `dependencies=[Depends(require_cron_secret)]` to the `/health/detailed`, `/health/llm` and `/health/metrics` route decorators (served at `/health/health/...`), leaving `/health` (basic) untouched
- [x] T022 [P] [US4] In `app/routes/campaigns.py` delete the module-level `CRON_SECRET = os.getenv(..., "dev-cron-secret-change-in-prod")` and local `verify_cron_secret`; use `Depends(require_cron_secret)` from `app/services/auth.py` on every route that used it
- [x] T023 [P] [US4] Same change in `app/routes/scheduled_tasks.py`
- [x] T024 [US4] Update `tests/` that call campaign or scheduled routes so they set `CRON_SECRET` via `monkeypatch.setenv` and send it as `X-Cron-Secret`

**Checkpoint**: `pytest` passes; contract table in `contracts/health-integrations.md` holds.

---

## Phase 7: User Story 5 - Monitoring can be recreated from the repo (Priority: P3)

**Goal**: one idempotent script per environment.

**Independent Test**: run `scripts/monitoring/setup.sh dev` twice; the second run creates nothing new.

- [x] T025 [US5] Make every create in `scripts/monitoring/setup.sh` look up by display name/metric name first and print `created`, `updated` or `exists`; exit non-zero on any API error; never echo the secret
- [x] T026 [P] [US5] Write `scripts/monitoring/README.md`: prerequisites, `setup.sh dev|prod`, what it creates (table), how to silence or delete, where alerts go, and how to rotate `CRON_SECRET` (update secret, redeploy, rerun setup to refresh scheduler headers)

**Checkpoint**: two consecutive dev runs; console shows one of each resource.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [x] T031 Suppress the fallback LLM probe per owner: `HEALTHCHECK_SKIP` setting in `app/core/settings.py` (default `llm_fallback`), `skipped` status in `app/schemas/health.py` and `app/services/integration_health.py`, tests in `tests/test_integration_health.py`, docs updated

- [ ] T027 (Deferred: constitution amendments need their own PR per Governance) Update the constitution's "Technology Constraints & Known Debt" list in `.specify/memory/constitution.md` only if the `CRON_SECRET` default debt is fully removed (it should be after T022/T023); otherwise leave it
- [x] T028 Run `.venv/bin/python -m pytest -q`; all pass
- [ ] T029 Deploy to dev (`/deploy-dev`), run `scripts/monitoring/setup.sh dev`, and walk [quickstart.md](quickstart.md) steps 2–5 including the kill-switch test; record results in the PR
- [ ] T030 After merge: `/deploy-prod` from `main`, `scripts/monitoring/setup.sh prod`, quickstart step 6

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → stories. US1 needs T001–T003. US4 needs T004 only (independent of US1's service). US2 and US3 need only T001 (script skeleton) and the channel from T013; run them after US1's script section. US5 hardens the script after US1–US3 add their sections.
- Order of delivery: US1 (MVP) → US4 (closes exposure, small) → US2 → US3 → US5 → Polish.

## Parallel Opportunities

- T002 with T001. Tests T005–T009 together, then T010→T011→T012 (same file chain), T013 independent of the Python work.
- US4: T019/T020 together; T022 and T023 in parallel (different files).
- US2/US3 script work can proceed while US4 Python work is in review.

## Implementation Strategy

1. MVP: Phases 1–3 (US1) — the check, the log line, the scheduler job and the "Integration down" alert. This alone would have caught the 2026-10-10 incident.
2. Add US4 (lockdown) in the same PR; it's small and reduces exposure.
3. Add US2/US3 alerting and US5 hardening; verify on dev; then prod.
