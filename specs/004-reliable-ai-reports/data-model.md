# Data Model: Reliable, Fast, Consistent AI Assessment Reports

## Assessment (table `assessments`): changes

| Column | Type | Default | Rules |
|---|---|---|---|
| `status` | String (existing) | `processing` | `processing` \| `done` \| `failed` (new value) |
| `scoring_attempts` | Integer | 0 | incremented on every lease claim |
| `scoring_queued_at` | DateTime, nullable | null | set on submit and every re-queue; the 1-hour retry window and the sweep's stuck test are measured from it |
| `scoring_lease_until` | DateTime, nullable | null | set to now+15 min when a worker claims; cleared on finish |
| `scoring_completed_at` | DateTime, nullable | null | set when `status` becomes `done` |
| `failure_reason` | String(300), nullable | null | short, user-safe reason when `failed` (e.g. "AI provider unavailable"); cleared on re-queue |
| `full_report_status` | String(16), nullable | null | null \| `generating` \| `ready` \| `failed` |
| `full_report_claimed_at` | DateTime, nullable | null | when the current `generating` claim started (stale after 5 min) |

Migration: `alembic/versions/20261011_assessment_scoring_state.py`. Adds these columns
(server defaults where shown); `downgrade()` drops them. Existing rows: `scoring_attempts=0`,
others null; `scoring_queued_at` backfilled from `created_at`; `full_report_status='ready'` backfilled
where `scores->'full_report_v1'` exists.

### Status transitions

```text
          submit
            │
            ▼
      ┌──processing──┐  lease claimed → AI ok → persist ─────────────► done
      │      ▲       │  AI error, retry window open → 5xx → Cloud Tasks retry ┘
      │      │       │  AI error, window exhausted ───────────────────► failed
      │   re-queue   │
      └────failed◄───┘
done is terminal for scoring (a duplicate attempt is a no-op).
```

### Invariants

- `status='done'` ⇒ `mentor_report_v2` has real AI content (non-empty `insights` when the
  assessment has open-ended answers) **or** the assessment has no open-ended answers.
- `status='failed'` ⇒ `failure_reason` is set; `scores` holds only baseline values.
- At most one live lease (`scoring_lease_until > now`) per assessment.

## scores JSON (existing column): shape kept

Keys the app reads stay: `overall_score`, `category_scores`, `recommendations`,
`question_feedback`, `summary_recommendation`, `mentor_blob_v2`. New keys:
`scoring_version: "master_v3"`, `computed_facts` (below), `mentor_email_sent_at`.
`full_report_v1` stays here (the draft copy is no longer written).

## ComputedFacts (in `scores.computed_facts` and sent to the AI)

| Field | Type |
|---|---|
| `health_score` | int 0–100 |
| `health_band` | string |
| `biblical_knowledge_percent` | float 0–100 (one decimal) |
| `mc_by_category` | list of `{category, correct, total, percent}` |
| `mc_by_topic` | list of `{topic, correct, total, percent}` |
| `weak_topics` | list[str] (topics < 65%) |
| `previous_health_score` | int \| null |
| `open_ended_count` | int |

`health_score` is computed after the AI returns open-ended levels (the formula needs them), so
the AI receives `biblical_knowledge_percent`, the MC breakdowns and `previous_health_score`, and
is told that the Health Score is computed by the system and must not be stated by it.

## MentorReportV3 (structured AI output; Gemini response schema)

| Field | Type |
|---|---|
| `categories` | list of `{category, level ∈ {Flourishing, Maturing, Stable, Developing, Beginning}, observation, next_step}` |
| `open_feedback` | list of `{question_id, feedback}` |
| `strengths` | list[str] (≤ 5) |
| `gaps` | list[str] (≤ 5) |
| `priority_action` | `{title, steps: list[str], scripture}` |
| `flags` | `{red: list[str], yellow: list[str], green: list[str]}` |
| `four_week_plan` | `{rhythm: list[str], checkpoints: list[str]}` |
| `conversation_starters` | list[str] |
| `recommended_resources` | list of `{title, why, type}` |

No numeric fields: all numbers come from ComputedFacts. Persisted as `mentor_report_v2` in the
existing v2.1 shape (adding `health_score`, `health_band`, `biblical_knowledge`, `insights`
mapped from `categories`) so every reader and `report_summary` keeps working.

## ScoringRequest (Cloud Task, not stored in DB)

`name = projects/trooth-prod/locations/us-east4/queues/assessment-scoring-<env>/tasks/score-<id>[-<ts>]`,
HTTP POST to `/internal/score-assessment/{id}`, OIDC token, retries per queue config.
