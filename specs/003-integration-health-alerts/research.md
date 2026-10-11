# Research: Integration Health Checks and Alerts

## 1. What each probe calls

| Integration | Probe | Why this call | Side effects |
|---|---|---|---|
| database | `SELECT 1` on a fresh session | proves connection + credentials | none |
| llm_primary | `service.primary_provider.ping()`: Vertex `models.get(model)` | the 2026-10-10 failure ("Publisher model … not found") is exactly what this call returns; a generation was tried first but Gemini 3.5's reasoning tokens truncated a 16-token reply, and raising the cap would break the cost budget and write `[llm] … error` lines that trip the real-traffic alert | none (no tokens) |
| llm_fallback | `fallback_provider.ping()`: OpenAI `models.retrieve(model)` (skipped by default via `HEALTHCHECK_SKIP`) | catches bad key/model; does **not** detect zero credit (needs a paid generation), which real-traffic alerts cover | none |
| email | SendGrid `GET /v3/scopes` | read-only; fails on revoked/invalid key | none |
| firebase_auth | `firebase_admin.get_app().credential.get_access_token()` | proves the service-account credential works | none |
| firebase_messaging | `messaging.send(Message(topic="healthcheck", ...), dry_run=True)` | FCM validates the request and auth without delivering | none (dry run) |
| revenuecat | `GET /v1/subscribers/{settings.revenuecat_healthcheck_app_user_id}`; 200 or 201 = up | read path used by subscription verification | RevenueCat creates an empty customer for an unknown id on first call (201); one fixed id (`healthcheck-probe`) means one inert record, reused |
| shopify | existing `_get_access_token` + `{ shop { name } }` GraphQL | proves client-credentials grant + Admin API | none; `not_configured` when `shopify_admin.is_configured()` is false (dev) |

- **Decision**: real minimal calls, each with its own timeout. **Rationale**: FR-002; the incident
  showed "configured" ≠ "working". **Alternatives**: config-only checks (today's
  `/health/detailed`) — rejected, they'd have stayed green on 2026-10-10.

## 2. Concurrency and timeouts

- **Decision**: `asyncio.gather` over `asyncio.wait_for(asyncio.to_thread(probe), timeout=10)`;
  the endpoint awaits all, so a hung probe costs at most 10 s. Overall budget < 30 s (Cloud
  Scheduler attempt deadline set to 60 s).
- **Rationale**: probes are sync SDK/httpx calls; threads avoid blocking the event loop.
- **Alternatives**: sequential (too slow, one hang delays all); separate scheduler job per
  integration (8× jobs, more config).

## 3. Status semantics

- `up` / `down` / `not_configured`; overall `healthy` if no `down`, else `degraded`.
- HTTP status stays **200** even when degraded, so the scheduler records a successful call and
  the alert comes from the log line, not from scheduler retries. A failure of the endpoint itself
  (5xx, timeout) is caught by the 5xx and uptime alerts.

## 4. Alert signal: structured log line

- **Decision**: one line per down integration:
  `integration_down env=<env> integration=<name> error="<scrubbed, ≤200 chars>"` at WARNING.
- A log-based metric `integration_down` (counter, labels `integration`, `env` extracted by regex
  from `textPayload`) drives the alert.
- **Rationale**: Cloud Run captures stdout as `textPayload`; log-based metrics with label
  extractors give per-integration alert text without new infrastructure.

## 5. Real-traffic signals (log-based metrics)

| Metric | Filter (textPayload) | Source today |
|---|---|---|
| `llm_provider_error` | `"[llm] provider=" AND "error="` | `app/services/llm/base.py` |
| `scoring_fallback` | `"Failed to build mentor_blob"` | `ai_scoring.score_assessment_by_category` |
| `email_send_failed` | `"[email]" AND` one of `"Failed send"`, `"Exception during send"`, `"Skipping send"`, `"No from_email"`, `"Failed to instantiate"` (send failures only, not template-render fallbacks) | `app/services/email.py` |
| 5xx rate | built-in `run.googleapis.com/request_count` with `response_code_class="5xx"` | Cloud Run |

All filtered by `resource.labels.service_name` so dev and prod metrics stay separate.

## 6. Alert policies (per environment)

- Integration down: `integration_down` > 0 in 5 min (aligned per `integration`).
- AI failures: `llm_provider_error` > 0 in 10 min; scoring fallback > 0 in 10 min.
- Email failures: `email_send_failed` > 0 in 10 min.
- 5xx spike: 5xx count > 5 in 5 min.
- Uptime: API `/health` (per env) and `https://onlyblv.com/` fail from ≥ 2 regions for 5 min.
- All: email channel admin@onlyblv.com, `alertStrategy.notificationChannelStrategy.renotifyInterval
  = 1800s`, `autoClose = 1800s`, display names prefixed `[prod]` / `[dev]`, documentation text
  naming the endpoint to check.
- **Rationale**: windows ≥ 5 minutes avoid single-blip alerts (SC-006).

## 7. Monitoring as code

- **Decision**: `scripts/monitoring/setup.sh <dev|prod>`: `gcloud logging metrics create|update`,
  `gcloud monitoring uptime create` (GA), `gcloud scheduler jobs create|update http`, and the
  Monitoring REST API (via `gcloud auth print-access-token`) for the notification channel and
  alert policies, looked up by display name to update instead of duplicating (FR-015).
- **Alternatives**: Terraform (new tool and state to manage for a small team), console clicks
  (not reproducible) — rejected.

## 8. Secret handling

- Scheduler job reads `CRON_SECRET` from Secret Manager at setup time and stores it as the
  `X-Cron-Secret` header (same as existing jobs).
- `campaigns.py` and `scheduled_tasks.py` switch to `require_cron_secret` (fail closed, no
  default) — satisfies FR-014 and removes the grandfathered default.

## 9. Known gap surfaced, not fixed here

- The OpenAI fallback is out of credit. Per the owner (2026-10-10) its check is suppressed:
  `HEALTHCHECK_SKIP` defaults to `llm_fallback`, which reports it as `skipped` (not probed, no
  alert). Set `HEALTHCHECK_SKIP=""` to re-enable once credit is restored or another fallback is
  chosen. Real-traffic fallback errors still raise "AI generation failures" if the primary fails.
