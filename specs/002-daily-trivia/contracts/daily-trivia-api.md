# Contract: Daily Trivia (backend 002)

This is the source of truth for the frontend spec `trooth_assessment/specs/NNN-daily-trivia/` (Principle X).

- Every user endpoint requires `Authorization: Bearer <Firebase ID token>`. A missing or invalid token gets 401.
- Any role (mentor, apprentice, admin) can call them. Nothing here is premium-gated.
- Errors keep the `detail` field, and the global handler adds `correlation_id`.
- Dates are ISO `YYYY-MM-DD` in the user's local timezone. Timestamps are ISO 8601 UTC.
- All changes are additive; no existing endpoint changes.

## Shared shapes

```jsonc
// DailyQuestion: there is deliberately no correct_option field
{
  "date": "2026-10-08",
  "category": "old_testament",       // old_testament | new_testament | theology_doctrine | discipleship_living
  "category_label": "Old Testament",
  "difficulty": "challenger",        // beginner | challenger
  "difficulty_label": "Challenger",
  "question_type": "multiple_choice",// or "true_false"
  "question_text": "Who built the ark?",
  "option_a": "Noah", "option_b": "Moses",
  "option_c": "Abraham", "option_d": "David"   // c/d null for true_false
}

// DailyAnswerResult
{
  "selected_option": "a",
  "correct": true,
  "correct_option": "a",
  "answered_at": "2026-10-08T13:02:11Z"
}

// Reward
{
  "id": 17,
  "tier": 45,                 // 45 | 60 | 90
  "percent": 25,
  "perfect": true,            // the +10% perfect-run bonus applied
  "status": "active",         // pending | active | superseded | expired
  "discount_code": "TROOTH-STREAK45-7KQ2ZD",   // null while pending
  "expires_at": "2026-12-07T13:02:12Z",        // null while pending
  "shop_url": "https://shop.onlyblv.com"
}

// NextMilestone (null once 90 has been earned in this streak)
{
  "tier": 60,
  "days_remaining": 13,
  "percent": 35,
  "percent_if_perfect": 45
}

// CalendarDay
{ "date": "2026-10-07", "status": "correct" }   // correct | wrong | freeze

// StreakState
{
  "current_streak": 47,          // effective: 0 if the streak has lapsed
  "longest_streak": 52,
  "freezes_available": 1,        // after any freezes a lapse would use
  "max_freezes": 2,
  "perfect_run": false,
  "answered_today": true,
  "streak_started_on": "2026-08-20",    // null when current_streak == 0
  "calendar": [CalendarDay],     // the last 62 local days, oldest first, only days with a status
  "next_milestone": NextMilestone | null,
  "active_reward": Reward | null // the single active or pending reward, if any
}
```

## GET `/trivia/daily/today`

Returns today's question for the caller's local date. The first request for a date chooses the question.

**200**
```jsonc
{
  "question": DailyQuestion,
  "answer": DailyAnswerResult | null,   // null until the caller answers
  "streak": StreakState
}
```

| Status | When | `detail` |
|---|---|---|
| 503 | No approved beginner/challenger questions exist | `"daily_question_unavailable"` |

## POST `/trivia/daily/today/answer`

**Body**
```json
{ "question_date": "2026-10-08", "option": "a" }
```

**200**
```jsonc
{
  "question": DailyQuestion,
  "answer": DailyAnswerResult,
  "streak": StreakState,                 // already includes this answer
  "freezes_used": 0,                     // freezes this answer used to bridge missed days
  "streak_reset": false,                 // true if missed days exceeded freezes and the streak restarted
  "freeze_earned": false,                // true if this answer earned a freeze
  "new_reward": Reward | null            // set when this answer reached 45/60/90; usually "pending", the code arrives by push/email and in GET /streak
}
```

| Status | When | `detail` |
|---|---|---|
| 409 | `question_date` isn't the caller's current local date | `"question_expired"` |
| 409 | The caller already answered this date (or a later one) | `"already_answered"` |
| 422 | `option` is a/b/c/d but not on this question (e.g. `c` on true/false) | `"invalid_option"` |
| 422 | Body malformed or `option` not a/b/c/d | FastAPI validation detail |
| 503 | As above | `"daily_question_unavailable"` |

## GET `/trivia/daily/streak`

**200**: `StreakState`. It works before the user has ever answered (all zeros, `calendar: []`, `next_milestone` set to 45).

## PUT `/users/me/timezone`

**Body**
```json
{ "timezone": "America/Chicago" }
```

**200**
```json
{ "timezone": "America/Chicago" }
```

| Status | When | `detail` |
|---|---|---|
| 422 | Not a valid IANA timezone name | `"invalid_timezone"` |

The app should send this after sign-in and whenever the device timezone changes. Until it does, the user is treated as being in `America/New_York`.

## POST `/scheduled/daily-trivia` (cron only)

Header: `X-Cron-Secret: <CRON_SECRET>`. A wrong or missing secret gets **403**. Cloud Scheduler runs it hourly (`0 * * * *`).

Each run sends the 9am reminders, retries unfinished rewards and expires old rewards.

**200**
```json
{ "reminded": 12, "rewards_processed": 1, "rewards_expired": 0, "errors": [] }
```

## Push payloads

| `data.type` | When | Other `data` keys | Suggested tap action |
|---|---|---|---|
| `daily_trivia` | 9am local reminder | `screen: "daily_trivia"`, `date` | Open the daily question modal |
| `daily_trivia_reward` | A reward code became active | `screen: "daily_trivia"`, `tier`, `percent` | Open the streak view showing the code |
