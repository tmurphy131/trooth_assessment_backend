# Data Model: Integration Health Checks and Alerts

No database tables. These are response and log shapes.

## IntegrationResult

| Field | Type | Rules |
|---|---|---|
| `name` | string | one of `database`, `llm_primary`, `llm_fallback`, `email`, `firebase_auth`, `firebase_messaging`, `revenuecat`, `shopify` |
| `status` | enum | `up` \| `down` \| `not_configured` \| `skipped` (listed in `HEALTHCHECK_SKIP`: not probed, never alerted) |
| `latency_ms` | int \| null | wall time of the probe; null when `not_configured` or `skipped` |
| `detail` | string \| null | provider/model for LLM probes (e.g. `gemini`), otherwise null |
| `error` | string \| null | present only when `down`; ≤ 200 chars; key-like substrings (`sk-…`, `SG.…`, `AIza…`, bearer tokens, long hex/base64 runs) replaced with `***` |

## IntegrationsReport

| Field | Type | Rules |
|---|---|---|
| `environment` | string | `settings.environment` (`dev`, `production`, …) |
| `status` | enum | `healthy` if no result is `down`, else `degraded` |
| `checked_at` | ISO-8601 UTC | start of the run |
| `duration_ms` | int | total wall time |
| `integrations` | list[IntegrationResult] | always all eight, fixed order |

## Log line (alert source)

One per `down` result, WARNING level, logger `app.services.integration_health`:

```text
integration_down env=<environment> integration=<name> error="<scrubbed error>"
```

Log-based metric `integration_down` extracts `env` and `integration` labels with
`REGEXP_EXTRACT(textPayload, "env=(\\S+)")` and `"integration=(\\S+)"`.

## Alert (Cloud Monitoring, not stored by the app)

Condition (integration down / service unavailable / traffic failures / 5xx spike), environment
(from the policy name prefix and metric label), open/closed state, notifications every 30
minutes while open, recovery notification on close.
