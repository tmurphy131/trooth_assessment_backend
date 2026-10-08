# Contract: Trivia Integrity (backend 001)

This is the source of truth for the frontend spec `trooth_assessment/specs/001-trivia-integrity/` (Principle X).

- Base path: `/trivia`.
- Every endpoint requires `Authorization: Bearer <Firebase ID token>`. A missing or invalid token gets 401.
- Errors keep the `detail` field, and the global handler adds `correlation_id`.

## Shared shapes

```jsonc
// SessionQuestion: there is deliberately no correct_option field
{
  "index": 0,                   // 0-based position in this game
  "id": 412,
  "question_text": "Who built the ark?",
  "question_type": "multiple_choice",   // or "true_false"
  "option_a": "Noah", "option_b": "Moses",
  "option_c": "Abraham", "option_d": "David"   // c/d null for true_false
}

// LastAnswer: the grading of the answer just submitted
{
  "question_id": 412,
  "selected": "a",              // null when timed out / not answered
  "correct": true,
  "correct_option": "a",        // revealed only after answering
  "timed_out": false
}

// SingleSessionState: returned by start, answer and grace
{
  "session_id": "uuid",
  "status": "active",           // active | awaiting_grace | finished
  "score": 300,
  "streak": 3,
  "correct_count": 3,
  "grace_tokens": 0,
  "grace_tokens_used": 0,
  "question_number": 4,         // 1-based number of `question`
  "total_questions": 412,     // size of the approved pool for this category + difficulty (the game can run until it is used up)
  "time_limit_ms": 30000,
  "question": SessionQuestion | null,     // null unless status == active
  "last_answer": LastAnswer | null,       // null on start
  "grace_expires_in_ms": 13000 | null,    // set only when awaiting_grace (10 s window + 3 s allowance)
  "result": SingleGameResult | null       // set only when finished
}

// SingleGameResult: unchanged from today's /single/submit response
{
  "score": 1500, "streak_length": 12, "correct_count": 12,
  "is_new_high_score": true, "previous_best": 900,
  "leaderboard_rank": 4, "badges_earned": [BadgeOut, ...]
}
```

## New endpoints

### `POST /trivia/single/start`

Starts a server-run game. First, any unfinished game of the caller's is finished and its score recorded.

Request:
```json
{ "category": "old_testament", "difficulty": "challenger" }
```

Here `category` is one of `old_testament`, `new_testament`, `theology_doctrine`, `discipleship_living` or `random`, and `difficulty` is one of `beginner`, `challenger` or `expert`.

| Status | When |
|---|---|
| 200 | `SingleSessionState` with `status=active`, `question_number=1` and `last_answer=null` |
| 400 | No approved questions for that category and difficulty (`detail: "No questions available"`) |
| 422 | Unknown category or difficulty |

### `POST /trivia/single/{session_id}/answer`

Request:
```json
{ "question_id": 412, "selected": "a" }
```

`selected` is `"a"`–`"d"`, or `null` if the player's timer ran out.

| Status | When |
|---|---|
| 200 | `SingleSessionState`. `last_answer` holds the grading. If correct: `status=active` with the next `question`, or `finished` if none are left. If wrong or late: `awaiting_grace` (with `grace_expires_in_ms`) when a token is available, else `finished` with `result`. |
| 200 (replay) | `question_id` is the **last answered** question (a network retry), whatever the session status, including the answer that ended the game or triggered grace. Returns the current state again without re-grading. Checked before the 409 and 400 rules. |
| 400 | `question_id` is not the current question (`detail: "Answer is not for the current question"`) |
| 404 | No such session, or it belongs to another user (`detail: "Game not found"`) |
| 409 | Session is `awaiting_grace` (`detail: "Grace decision pending"`) or `finished` (`detail: "Game is over"`) |

Timing: the server measures from when the question was sent. More than 33 000 ms (30 s limit + 3 s allowance) is graded wrong with `timed_out=true`, whatever `selected` is.

The clock keeps running when the app is in the background or closed:
- For a late answer, a grace token holder's 10 s (+3 s) grace window starts when the question **expired**, not when the late answer arrived.
- If that window has already passed (answer more than ~43 s after the question was served), the response is `status=finished` with `result`, and no grace is offered.
- An unanswered expired question also makes the game eligible for the server's cleanup jobs, which record the score so far.

### `POST /trivia/single/{session_id}/grace`

Request:
```json
{ "use": true }
```

| Status | When |
|---|---|
| 200 | `use=true` within 13 s of the wrong answer: a token is spent and `status=active` with the next `question` (or `finished` if none are left). `use=false`, or any call after the deadline: `status=finished` with `result`. |
| 404 | No such session, or not the caller's |
| 409 | Session is not `awaiting_grace` (`detail: "No grace decision pending"`) |

### `POST /trivia/single/{session_id}/finish`

There is no body. It ends the game now (the player quit) and records the score. It is idempotent.

| Status | When |
|---|---|
| 200 | `SingleGameResult`. Calling it again on a finished session returns the same stored result. |
| 404 | No such session, or not the caller's |

## Changed endpoints

### `GET /trivia/questions/draw` and `POST /trivia/single/submit` (old flow)

| Setting `TRIVIA_LEGACY_SINGLE_ENABLED` | Behaviour |
|---|---|
| `true` (default) | Same as today. `submit` now records the score as `verified=false`, so it doesn't count toward competitions. Response shapes are unchanged. |
| `false` | **426** `{"detail": "Please update the app to keep playing trivia."}`. Nothing is recorded. |

**Minimum app version that no longer needs these: 2.2.0.** Turn them off only after 2.2.0 is live in the App Store and Google Play. Target date: before 2026-11-01.

### `POST /trivia/challenges` (create)

New response for free users:

| Status | When |
|---|---|
| 403 | Caller is not premium (`is_premium_user` false). `detail: {"error": "premium_required", "message": "Premium subscription required to create challenges", "upgrade_url": "/settings/subscription"}`. No challenge is created and no push is sent. |

All other behaviour is unchanged. Accept, decline, answer, forfeit, nudge, cancel, list and detail have **no** premium check.

### `POST /trivia/challenges/{id}/answer`

| Status | When |
|---|---|
| 400 (new) | `answer.question_id` is not the challenge's current question (`detail: "Answer is not for the current question"`) |

`answer.time_used_ms` is now clamped to 0–30000 before it is stored. The response shape is unchanged.

### `GET /trivia/competition`

There is no shape change. Standings and winners now count only verified scores. A verified score is dated by when its game **started**. Unfinished games are closed before winners are decided.

### `POST /scheduled/trivia-competition-finalize` (cron)

If any single-player game that started before the competition ended is still being played (active within the last hour), the result for that competition is `{"status": "waiting_for_games"}` and the next hourly run tries again. Games idle for over an hour are closed (score recorded) first.

### `POST /scheduled/trivia-expiry` (cron)

The response gains `finished_sessions` (stale single-player games closed). `expired_ids` is now a real list of challenge IDs; previously this endpoint raised an error after expiring challenges.
