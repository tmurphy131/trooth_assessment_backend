# Data Model: Trivia Integrity

Migration: `alembic/versions/20261008_add_trivia_single_sessions.py`

- **Enum types:** the `category` and `difficulty` columns MUST reuse the existing Postgres enum types via `postgresql.ENUM(..., name='triviacategory' / 'triviadifficulty', create_type=False)`, as in `a1b2c3d4e5f6_add_trivia_tables.py`. Only `triviasessionstatus` is created and dropped by this migration.

- revision `20261008_trivia_single_sessions`, down_revision `20261003_trivia_competitions`
- `downgrade()` drops the new columns and table.

## New: `TriviaSingleSession` (`trivia_single_sessions`, in `app/models/trivia.py`)

| Column | Type | Notes |
|---|---|---|
| `id` | String (uuid4) PK | Returned to the client as `session_id` |
| `user_id` | String FK `users.id`, indexed, not null | Owner; every call checks it |
| `category` | Enum `TriviaCategory` | Includes `random` |
| `difficulty` | Enum `TriviaDifficulty` | |
| `question_ids` | JSON, not null | `[int, …]`: the whole approved pool for category + difficulty, shuffled at start. No fixed game length. |
| `current_index` | Integer, default 0 | Index into `question_ids` |
| `current_question` | JSON, nullable | Snapshot of the question being served: `{id, question_text, question_type, options: {a,b,c?,d?}, correct}`, with options shuffled when served. **Never serialised to clients as-is.** |
| `current_served_at` | DateTime tz, nullable | When the current question was last sent |
| `answers` | JSON, default `[]` | `[{index, question_id, selected, correct, timed_out, graced, elapsed_ms}]` |
| `score` | Integer, default 0 | Recomputed from non-graced `answers` |
| `streak` | Integer, default 0 | Current streak |
| `max_streak` | Integer, default 0 | Becomes the score's `streak_length` |
| `correct_count` | Integer, default 0 | |
| `grace_tokens` | Integer, default 0 | Available now |
| `grace_tokens_used` | Integer, default 0 | |
| `grace_deadline` | DateTime tz, nullable | Set only while `awaiting_grace` |
| `status` | Enum `TriviaSessionStatus` (`active`, `awaiting_grace`, `finished`), indexed | |
| `result` | JSON, nullable | The stored `SingleGameResult` once finished (idempotent `finish`) |
| `created_at` | DateTime tz | |
| `last_activity_at` | DateTime tz | Updated on every call; used for the 1 h abandonment rule |
| `finished_at` | DateTime tz, nullable | |

### State transitions

```text
start ──► active ──answer correct──► active (next question; finished when the pool is used up)
             │
             └─answer wrong / timed out──┬─ tokens > 0 ──► awaiting_grace ──use (before deadline)──► active (next question)
                                         │                       │
                                         │                       └─decline / past deadline──► finished
                                         └─ tokens = 0 ──► finished
active | awaiting_grace ──finish / new start / idle > 1 h──► finished
```

`finished` is terminal. Entering it writes exactly one `TriviaSingleScore` (with `verified=true`), awards badges and stores `result`.

### Validation rules

- Order of checks on answer:
  1. owner (else 404);
  2. `question_id` == last answered ID → replay current state (research R5);
  3. `status == active` (else 409);
  4. `question_id == question_ids[current_index]` (else 400).
- All stored timestamps are compared via `_aware()` (SQLite returns naive datetimes).
- `selected` is one of the letters present for that question, or `null` (timeout). Anything else is graded wrong.
- Grace is only accepted while `status == awaiting_grace`. A call after `grace_deadline` counts as a decline.

## Changed: `TriviaSingleScore` (`trivia_single_scores`)

| Column | Type | Notes |
|---|---|---|
| `verified` | Boolean, not null, `server_default=false` | `true` only when written by a session finish. Existing rows and old-flow submits are `false`. |
| `created_at` (existing) | | For session scores, set to the **session's** `created_at` (game start, research R10). Old-flow scores keep "now". |
| `session_id` | String FK `trivia_single_sessions.id`, nullable | Set for verified scores |

## Unchanged: `TriviaChallenge`

There is no schema change. Answer validation is stricter: `question_id` must equal `question_ids[current_question_index]`, and the stored `time_used_ms` is clamped to 0–30000.
