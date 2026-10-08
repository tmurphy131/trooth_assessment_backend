# Implementation Plan: Daily Trivia Question & Streak Rewards

**Branch**: `feature/daily-trivia` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-daily-trivia/spec.md`

## Summary

The feature has four parts:
- **Daily question**: one question per calendar date. It is chosen lazily from the approved beginner/challenger bank, with a random category and level and no repeats for 180 days, and its shuffle is fixed on the date's row.
- **Answering and streaks**: each user answers once per local date. The streak is updated under a row lock, using freezes that are applied lazily.
- **Rewards**: reaching 45, 60 or 90 days creates a pending reward. A background task (retried hourly by cron) turns it into a single-use Shopify percentage code, deactivates the code it replaces, then sends it by email and push. This reuses the step-by-step idempotent pattern from `trivia_competition.py`.
- **Reminders**: an hourly cron sends the 9am push in each user's local timezone. Timezone comes from a new `PUT /users/me/timezone`.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, Firebase Admin, httpx (Shopify Admin). **New**: `tzdata`, the IANA timezone database for `zoneinfo`, which `python:3.11-slim` lacks (research R1).

**Storage**: PostgreSQL. Four new tables (`daily_trivia_questions`, `daily_trivia_answers`, `daily_trivia_streaks`, `daily_trivia_rewards`) and one new enum, added in migration `20261008_add_daily_trivia.py`.

**Testing**: pytest (`tests/test_daily_trivia.py`, SQLite in-memory via conftest fixtures; Shopify, FCM and email mocked; `now` injected)

**Target Platform**: Google Cloud Run (dev and prod services) plus one new Cloud Scheduler job (hourly)

**Project Type**: web-service (client: Flutter app in `trooth_assessment`)

**Performance Goals**:
- `GET /today` and the answer request each make a handful of indexed queries.
- Shopify calls happen after the response, never inside it.
- The hourly cron finishes well inside Cloud Run's request timeout for the current user base: one indexed query per eligible timezone, then one push per user.

**Constraints**: correct options are never in a pre-answer response; at most one answer per user per date; no duplicate codes or notifications under retries.

**Scale/Scope**: current user base (thousands); 3 user endpoints, 1 user-settings endpoint, 1 cron endpoint.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Source: `.specify/memory/constitution.md`.

- [x] ✅ **I. Auth**: the daily endpoints and `PUT /users/me/timezone` depend on `get_current_user` and only touch the caller's own rows. Not premium. The cron endpoint uses `verify_cron_secret`. No test shortcuts.
- [x] ✅ **II. Errors**: `HTTPException` with string `detail` codes (`question_expired`, `already_answered`, `daily_question_unavailable`, `invalid_timezone`).
- [x] ✅ **III. Migrations**: `20261008_add_daily_trivia.py` with a full `downgrade()`, run by the migrate job before deploy. No seed script.
- [x] ✅ **IV. Config & secrets**: no new secrets. The existing Shopify client credentials and `CRON_SECRET` are reused. Reward constants live in the service; `settings.shop_url` is reused.
- [x] ✅ **V. Logging**: `logging.getLogger(__name__)`. Logs carry user IDs and reward IDs, never codes in full, tokens or email addresses.
- [x] ✅ **VI. Compatibility**: additive only (new routes, tables, optional data). Every new handler declares `response_model`.
- [x] ✅ **VII. Layering**: logic in `app/services/daily_trivia.py`; Shopify in `shopify_admin.py`; email in `email.py`; push in `push_notification.py`. Routes stay thin. No LLM.
- [x] ✅ **VIII. Tests**: `tests/test_daily_trivia.py` covers the success paths, 401/403 for cron, the 409/422 cases, streak math, rewards and idempotency. Nothing live.
- [x] ✅ **IX. Deploy**: dev first (`/deploy-dev` plus the dev Scheduler job), prod from `main`.
- [x] ✅ **X. Contract**: [contracts/daily-trivia-api.md](contracts/daily-trivia-api.md). The frontend spec will link it.
- [x] ✅ **XI. Formatting**: new files only. Existing files get targeted edits, no reformatting.

Re-checked after Phase 1 design: still passes. Grandfathered debt touched: the `CRON_SECRET` default in `scheduled_tasks.py` is reused, not added to or changed.

## Project Structure

### Documentation (this feature)

```text
specs/002-daily-trivia/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/daily-trivia-api.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
app/
├── models/daily_trivia.py           # NEW: DailyTriviaQuestion, DailyTriviaAnswer, DailyTriviaStreak, DailyTriviaReward
├── models/__init__.py               # register new models
├── schemas/daily_trivia.py          # NEW: response/request models per contract
├── services/daily_trivia.py         # NEW: local_today, get_or_create_question, submit_answer, streak math,
│                                    #      get_streak_state, process_reward, run_hourly
├── services/shopify_admin.py        # + create_percentage_code, deactivate_code
├── services/email.py                # + send_daily_trivia_reward_email
├── services/push_notification.py    # + notify_daily_trivia_reminder, notify_daily_trivia_reward
├── services/account_deletion.py     # + delete daily answers/streak/rewards
├── routes/daily_trivia.py           # NEW: GET /today, POST /today/answer, GET /streak
├── routes/user.py                   # + PUT /me/timezone
├── routes/scheduled_tasks.py        # + POST /daily-trivia
├── main.py                          # mount daily_trivia router at /trivia/daily (before /trivia)
└── templates/email/campaigns/daily_trivia_reward.html   # NEW
alembic/versions/20261008_add_daily_trivia.py            # NEW
requirements.txt                     # + tzdata
tests/test_daily_trivia.py           # NEW
```

**Structure Decision**: this follows the existing trivia layout: a model file, a schema file, a service, and a route module mounted in `app/main.py`. Cron work goes in `scheduled_tasks.py`, next to `/trivia-competition-finalize`.

## Complexity Tracking

No violations.
