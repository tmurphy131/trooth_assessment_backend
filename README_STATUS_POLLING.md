# Assessment Status & Polling

This backend adds a lightweight status model and endpoint so the client can show immediate "Submitted" and poll until results are ready.

## Schema changes

Table `assessments` has two new columns:
- `status` (string): one of `processing`, `done`, `error`.
- `updated_at` (datetime): auto-updated on changes.

Run the migration:

```bash
alembic upgrade head
```

## Lifecycle

1. On submit: create `assessments` with `status=processing`, `scores=null`.
2. Background worker computes scores by category in a small number of AI calls, then:
   - saves `scores` and `recommendation`
   - sets `status=done`
   - emails mentor
3. On failure, `status=error` and a failure email is sent to the operator.

## Status endpoint

GET `/assessments/{assessment_id}/status`

Response:

```json
{
  "id": "...",
  "status": "processing|done|error",
  "has_scores": true,
  "overall_score": 8,
  "updated_at": "2025-09-17T12:34:56Z"
}
```

- AuthZ: apprentice owner or their mentor.
- `overall_score` is present only when `scores` exist.

## Client polling pattern

- After submit, navigate to a "Submitted" screen with a spinner.
- Poll `/assessments/{id}/status` every 2–4 seconds.
- Stop when `status` is `done` or `error`.
- On `done`, fetch full assessment (`GET /assessments/{id}`) to render details.
- On `error`, show retry guidance and optionally allow resubmission.

## Notes

- The background worker groups Master Trooth questions by category and evaluates them in a single AI call per category. Multiple-choice are graded for correctness, open-ended get qualitative feedback.
- AI calls enforce JSON output and include retry/backoff for rate limits.
