# Contract: Health endpoints

Base: `https://trooth-discipleship-api.onlyblv.com` (prod), `https://trooth-discipleship-api-dev.onlyblv.com` (dev).

## GET /health/integrations — NEW

**Auth**: header `X-Cron-Secret: <CRON_SECRET>`.

**200** (always, even when an integration is down):

```json
{
  "environment": "dev",
  "status": "healthy",
  "checked_at": "2026-10-11T01:00:00Z",
  "duration_ms": 2140,
  "integrations": [
    {"name": "database", "status": "up", "latency_ms": 12, "detail": null, "error": null},
    {"name": "llm_primary", "status": "up", "latency_ms": 1420, "detail": "gemini", "error": null},
    {"name": "llm_fallback", "status": "skipped", "latency_ms": null, "detail": null, "error": null},
    {"name": "email", "status": "up", "latency_ms": 180, "detail": null, "error": null},
    {"name": "firebase_auth", "status": "up", "latency_ms": 95, "detail": null, "error": null},
    {"name": "firebase_messaging", "status": "up", "latency_ms": 240, "detail": null, "error": null},
    {"name": "revenuecat", "status": "up", "latency_ms": 160, "detail": null, "error": null},
    {"name": "shopify", "status": "not_configured", "latency_ms": null, "detail": null, "error": null}
  ]
}
```

`status` per integration is `up`, `down`, `not_configured`, or `skipped` (named in the
`HEALTHCHECK_SKIP` setting, default `llm_fallback` while the OpenAI fallback has no credit).

**403** `{"detail": "Invalid or missing cron secret"}`: header missing or wrong, or
`CRON_SECRET` not configured on the service.

Schema: [data-model.md](../data-model.md) (`IntegrationsReport`).

## Existing endpoints whose access changes

| Endpoint | Before | After |
|---|---|---|
| `GET /health` | public | **unchanged** (public; app + uptime checks) |
| `GET /health/health` | public | **unchanged** (public basic check) |
| `GET /health/health/detailed` | public | `X-Cron-Secret` required, else 403 |
| `GET /health/health/llm` (incl. `?test_generation=true`) | public | `X-Cron-Secret` required, else 403 |
| `GET /health/health/metrics` | public | `X-Cron-Secret` required, else 403 |
| `/campaigns/*`, `/scheduled/*` | `X-Cron-Secret`, fell back to a known default if unset | `X-Cron-Secret`; **403 for everything if `CRON_SECRET` is unset** |

Response bodies of the existing endpoints are unchanged. No released app version calls the
changed endpoints (the app only calls `GET /health`).
