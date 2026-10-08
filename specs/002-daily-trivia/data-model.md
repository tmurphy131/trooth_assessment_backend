# Data Model: Daily Trivia (backend 002)

Migration: `alembic/versions/20261008_add_daily_trivia.py`. Its `down_revision` is the current head, `20261008_trivia_single_sessions`. `downgrade()` drops the four tables and the enum type.

## daily_trivia_questions

One row per calendar date, shared by every user.

| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| date | date, **unique**, indexed | the calendar date this question belongs to |
| question_id | int FK → trivia_questions.id | source question, used for the 180-day no-repeat rule |
| category | `triviacategory` enum | never `random` |
| difficulty | `triviadifficulty` enum | `beginner` or `challenger` only |
| question_type | `triviaquestiontype` enum | |
| question_text | string | snapshot |
| options | JSON | `{"a": str, "b": str, "c": str\|null, "d": str\|null}`, already shuffled |
| correct_option | string(1) | letter within `options` |
| created_at | timestamptz | |

## daily_trivia_answers

| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| user_id | string FK → users.id | indexed |
| date | date | the user's local date when they answered |
| daily_question_id | int FK → daily_trivia_questions.id | |
| selected_option | string(1) | must be a non-null key of `options` |
| is_correct | bool | |
| answered_at | timestamptz | |

The table has a unique constraint `uq_daily_trivia_answer_user_date` on (`user_id`, `date`).

## daily_trivia_streaks

One row per user. The row is created on the user's first answer or first reminder.

| Column | Type | Notes |
|---|---|---|
| user_id | string PK, FK → users.id | |
| current_streak | int, default 0 | stored value; reads compute the effective value (research R4) |
| longest_streak | int, default 0 | |
| last_answered_date | date, nullable | |
| streak_started_on | date, nullable | identifies the current streak; part of the reward uniqueness key |
| freezes_available | int, default 0 | 0–2 |
| perfect_run | bool, default true | |
| freeze_dates | JSON list[str ISO date], default [] | freeze-covered dates in the current streak |
| tiers_earned | JSON list[int], default [] | subset of {45, 60, 90} for the current streak |
| last_reminded_date | date, nullable | local date of the last 9am push |
| updated_at | timestamptz | |

**Rules**
- Answering for date D, where `missed = (D − last_answered_date).days − 1`:
  - `missed == 0`: the streak continues.
  - `1 ≤ missed ≤ freezes_available`: use `missed` freezes and append those dates to `freeze_dates`.
  - Otherwise reset: `current_streak = 0`, `freezes_available = 0`, `perfect_run = true`, `freeze_dates = []`, `tiers_earned = []`, `streak_started_on = D`.
  - Then:
    - `current_streak += 1`
    - `perfect_run &= is_correct`
    - if `current_streak % 15 == 0` and `freezes_available < 2`, then `freezes_available += 1`
    - `longest_streak = max(longest_streak, current_streak)`
    - `last_answered_date = D`
  - On a new streak, `streak_started_on` is D.
- Milestones are `{45: 15, 60: 35, 90: 50}`, plus 10 when `perfect_run` is true. Reaching one that isn't in `tiers_earned` appends it and creates a `pending` reward.

## daily_trivia_rewards

| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| user_id | string FK → users.id | indexed |
| streak_started_on | date | the streak that earned it |
| tier | int | 45, 60 or 90 |
| percent | int | 15–60 |
| perfect | bool | whether the +10% bonus applied |
| status | enum `dailytriviarewardstatus` | `pending`, `active`, `superseded` or `expired` |
| discount_code | string, nullable | set when the code is created |
| shopify_discount_id | string, nullable | |
| replaces_reward_id | int FK → daily_trivia_rewards.id, nullable | the active reward this one superseded (used in the email) |
| issued_at | timestamptz, nullable | when the code was created (status became active) |
| expires_at | timestamptz, nullable | `issued_at + 60 days` |
| superseded_at | timestamptz, nullable | |
| deactivated_at | timestamptz, nullable | Shopify `discountCodeDeactivate` done (superseded only) |
| emailed_at | timestamptz, nullable | |
| pushed_at | timestamptz, nullable | |
| created_at | timestamptz | |

The table has a unique constraint `uq_daily_trivia_reward_streak_tier` on (`user_id`, `streak_started_on`, `tier`).

**State transitions**

```
pending ──code created──▶ active ──higher tier becomes active──▶ superseded ──(Shopify deactivated)
                            └──expires_at passed (cron)──▶ expired
```

- A pending reward is finished once its code exists and it has been emailed.
- A superseded reward is finished once it has been deactivated, or when it has no Shopify id (dry run).
- A reward is only created if it is worth more (higher `percent`) than the user's current `active` or `pending` reward. Otherwise the tier is still recorded in `tiers_earned` and the better code is kept. This matters when a new streak reaches 45 while a code from an earlier streak is still active.
- When a pending reward is processed and a newer reward of the same user with a higher percent is already active or pending, it is marked `superseded` without creating a code.
- At most one `active` reward per user. When a code becomes active, any other active reward of that user is superseded in the same transaction.

## Account deletion

Add `DailyTriviaAnswer`, `DailyTriviaStreak` and `DailyTriviaReward` (filtered by `user_id`) to the trivia block in `app/services/account_deletion.py`. `daily_trivia_questions` holds no user data and stays.
