# Contract: Assessment scoring API

## GET /assessments/{assessment_id}/status (changed, additive)

Auth: Firebase user who is the apprentice or an active mentor of the apprentice (unchanged).

```json
{
  "id": "…",
  "status": "processing | done | failed",
  "reason": "AI provider unavailable",
  "has_scores": true,
  "overall_score": 7,
  "health_score": 76,
  "updated_at": "2026-10-11T01:00:00Z"
}
```

- `reason`: new, present only when `status = failed` (user-safe text).
- `health_score`: new, null until `done`.
- **403** not the apprentice or mentor; **404** not found. Today both come back as 500; that's
  fixed here.
- Released apps: they read `status` and `has_scores` only, and keep working. With `failed` and
  baseline scores they show baseline content, as today.

## POST /internal/score-assessment/{assessment_id} (new, internal)

Called only by Cloud Tasks. Auth: `Authorization: Bearer <Google OIDC ID token>`, issued for
`trooth-run-sa@trooth-prod.iam.gserviceaccount.com`, audience = `BACKEND_API_URL`; anything
else returns **403**.

| Response | Meaning |
|---|---|
| 200 `{"result": "done"}` | scored now |
| 200 `{"result": "already_done"}` | idempotent no-op |
| 503 `{"detail": "retry: leased"}` | another worker holds a live lease and the assessment isn't `done`. Cloud Tasks backs off and retries, so a task whose worker crashed is picked up once the lease expires (≤ 15 min) instead of being dropped |
| 200 `{"result": "failed", "reason": "…"}` | retry window exhausted; marked failed |
| 503 `{"detail": "retry: …"}` | retryable failure; Cloud Tasks retries with backoff |
| 200 `{"result": "missing"}` | unknown assessment (permanent, so 200 rather than 404, which Cloud Tasks would retry) |

Note: Cloud Tasks retries any non-2xx, so permanent conditions return 200 with a `result`.

## POST /scheduled/scoring-sweep (new)

Auth: `X-Cron-Secret` (403 otherwise). Re-queues stuck `processing` (> 75 min, lease
expired) and retryable `failed` (≥ 6 h since last attempt).
**200** `{"requeued": 3, "ids": ["…"]}`.

## POST /admin/assessments/requeue (new)

Auth: admin user (`require_admin`) **or** `X-Cron-Secret`; 403 otherwise.

Request (at least one selector):

```json
{"ids": ["…"], "since": "2026-10-09T00:00:00Z", "until": "2026-10-11T00:00:00Z",
 "include_done_fallback": true}
```

- `include_done_fallback`: also selects `done` Master assessments whose report is the empty
  fallback (outage backfill).
- **200** `{"requeued": 5, "ids": ["…"], "skipped": [{"id": "…", "why": "already processing"}]}`.
- **422**: no selector given.

## Full report endpoints (behavior change, same shapes)

`GET /assessments/{id}/my-full-report`, `GET /apprentice/my-assessments/{id}/full-report`,
`GET /mentor/submitted-drafts/{id}/full-report`:

- Return the stored report instantly when `full_report_status = ready`.
- Otherwise one caller claims generation; concurrent callers wait (≤ 90 s) for it.
- If it's still generating after the wait: **200** `{"status": "generating", "cached": false}`
  with no `report` key. Clients should retry in a few seconds.
- Never 500 on malformed AI output: generation retries internally, and if it still fails,
  `full_report_status=failed` and **503** `{"detail": "Report is temporarily unavailable"}`.
- Premium gating (403) and access checks are unchanged.
