---
description: "Tasks for Daily Trivia Question & Streak Rewards"
---

# Tasks: Daily Trivia Question & Streak Rewards

**Input**: Design documents from `/specs/002-daily-trivia/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/daily-trivia-api.md

**Tests**: Per constitution Principle VIII, every new endpoint needs tests for its success path and the authorization failures that apply. External services (Shopify, FCM, email) are mocked. Each story ends with `pytest` passing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task belongs to

---

## Phase 1: Setup

- [x] T001 Add `tzdata` to `requirements.txt` (research R1)

---

## Phase 2: Foundational (blocks all stories)

- [x] T002 Create the models in `app/models/daily_trivia.py`, following [data-model.md](data-model.md): `DailyTriviaQuestion`, `DailyTriviaAnswer`, `DailyTriviaStreak`, `DailyTriviaReward`, the `DailyTriviaRewardStatus` enum, and the unique constraints. Register them in `app/models/__init__.py` (and in `alembic/env.py` if models are imported there).
- [x] T003 Write the migration `alembic/versions/20261008_add_daily_trivia.py`:
  - `down_revision = "20261008_trivia_single_sessions"`
  - create the 4 tables and the enum, reusing the existing `triviacategory`, `triviadifficulty` and `triviaquestiontype` types with `create_type=False`
  - full `downgrade()`
- [x] T004 [P] Write the Pydantic schemas in `app/schemas/daily_trivia.py`, one per contract shape: `DailyQuestionOut`, `DailyAnswerResultOut`, `RewardOut`, `NextMilestoneOut`, `CalendarDayOut`, `StreakStateOut`, `DailyTodayOut`, `DailyAnswerIn`, `DailyAnswerOut`, `TimezoneIn`, `TimezoneOut`, `DailyCronOut`.
- [x] T005 Write the service skeleton in `app/services/daily_trivia.py`:
  - constants: milestones `{45: 15, 60: 35, 90: 50}`, `PERFECT_BONUS = 10`, `FREEZE_EVERY = 15`, `MAX_FREEZES = 2`, `NO_REPEAT_DAYS = 180`, `CODE_VALID_DAYS = 60`, `CALENDAR_DAYS = 62`, `DEFAULT_TZ = "America/New_York"`
  - `local_now(user, now)` and `local_today(user, now)`
- [x] T006 Create the router `app/routes/daily_trivia.py` and mount it in `app/main.py` at `/trivia/daily`, before the `/trivia` router.

---

## Phase 3: US1, answer today's question (P1) 🎯 MVP

**Independent test**: two users get the same question with no answer revealed; the first answer is graded; a second answer is refused.

- [x] T007 [US1] `get_or_create_question(db, date)` in `app/services/daily_trivia.py`:
  - pick a (category × level) pair (research R2), excluding questions used in the last 180 days
  - if nothing is eligible, fall back to the question used longest ago
  - fix the shuffle by reusing `_shuffle_options` (R3)
  - insert, and on `IntegrityError` roll back and re-read
  - return `None` when the bank is empty
- [x] T008 [US1] `submit_answer(db, user, question_date, option, now)` in `app/services/daily_trivia.py`:
  - 409 `question_expired` if the date isn't the user's local today
  - 409 `already_answered` if this date or a later one is already answered
  - 422 if the option isn't valid for this question
  - grade the answer and insert it, catching a duplicate-insert `IntegrityError` as `already_answered`
  - call the streak update (US2); until US2 is built, a stub that returns zeros
- [x] T009 [US1] Routes `GET /today` and `POST /today/answer` in `app/routes/daily_trivia.py`, with response models, `get_current_user`, and 503 `daily_question_unavailable`.
- [x] T010 [US1] Tests in `tests/test_daily_trivia.py`:
  - same question and option order for two users
  - no `correct_option` before answering
  - answering returns the correct option
  - 409 `already_answered`
  - 409 `question_expired`
  - 422 for option `c` on true/false
  - 503 on an empty bank
  - 401 without auth
  - only beginner/challenger and never `random`
  - no repeat within 180 days, and the fallback when the bank is exhausted

---

## Phase 4: US2, build and keep a streak (P1)

**Independent test**: consecutive days count up; a freeze bridges a gap; a gap with no freeze resets; a lapsed streak reads as 0.

- [x] T011 [US2] `_advance_streak(db, user_id, date, correct)` in `app/services/daily_trivia.py`:
  - lock the row (create it if missing)
  - apply the gap, freeze and reset rules
  - add one, then update the perfect flag, freezes earned and the longest streak
  - return `(streak, freezes_used, reset, freeze_earned, reached_tier | None)`
- [x] T012 [US2] `get_streak_state(db, user, now)`: effective streak, projected freeze use, a 62-day calendar built from answers plus freeze dates, `next_milestone`, `active_reward`.
- [x] T013 [US2] Route `GET /streak`. Include `streak` in the `/today` and answer responses, and include `freezes_used`, `streak_reset` and `freeze_earned` in the answer response.
- [x] T014 [US2] Tests:
  - 1 → 2 → 3 on consecutive days
  - a freeze earned at 15 and at 30, and none beyond 2
  - a 2-day gap with 2 freezes continues the streak
  - a 2-day gap with 1 freeze resets it and clears freezes
  - a wrong answer keeps the streak and clears the perfect flag
  - a lapsed streak reads as 0 without writing anything
  - the calendar statuses
  - a new user's `/streak` shows zeros and the next milestone at 45

---

## Phase 5: US3, merch discounts (P2)

**Independent test**: day 45 issues a 15% or 25% code; day 60 supersedes and deactivates it; retries never duplicate.

- [x] T015 [P] [US3] `create_percentage_code(tier, percent, title, starts_at, ends_at)`, `build_percentage_input` and `deactivate_code(discount_id)` in `app/services/shopify_admin.py`. Use the same dry-run and production rules as `create_prize_code`.
- [x] T016 [P] [US3] `send_daily_trivia_reward_email(db, user, reward)` in `app/services/email.py`, plus the template `app/templates/email/campaigns/daily_trivia_reward.html` modelled on `trivia_prize.html`. When an earlier code was replaced, the email says so.
- [x] T017 [P] [US3] `notify_daily_trivia_reward(db, user_id, tier, percent)` in `app/services/push_notification.py`, with type `daily_trivia_reward`.
- [x] T018 [US3] In `app/services/daily_trivia.py`:
  - when a tier is reached, create a pending reward with percent = base + bonus, unique on (user, streak start, tier)
  - `process_reward(db, reward_id, now)` runs the steps code → supersede → deactivate → email → push, each under a row lock (research R5)
  - `expire_rewards(db, now)`
- [x] T019 [US3] Return `new_reward` in the answer response, and schedule `process_reward` through FastAPI `BackgroundTasks` in the answer route.
- [x] T020 [US3] Tests, with Shopify, email and push mocked:
  - 15% at 45 when not perfect, 25% when perfect
  - 60 supersedes 45 and calls deactivate exactly once
  - 90 gives 50% or 60%, and nothing is issued beyond 90
  - `process_reward` twice creates one code and sends one email
  - a Shopify failure leaves the answer and streak saved and the reward pending, then a retry succeeds
  - expiry after 60 days
  - after a reset, the 45 reward can be earned again
  - `active_reward` appears in `/streak`

---

## Phase 6: US4, 9am reminder (P2)

**Independent test**: only users at local 9am who haven't answered and have push enabled are reminded, at most once per date.

- [x] T021 [P] [US4] `notify_daily_trivia_reminder(db, user_id, streak, question)` in `app/services/push_notification.py`, with type `daily_trivia`.
- [x] T022 [US4] `run_hourly(db, now)` in `app/services/daily_trivia.py`:
  - send reminders, filtering by timezone (research R7) and setting `last_reminded_date` before sending
  - retry unfinished rewards
  - expire rewards
  - return counts and errors
- [x] T023 [US4] Endpoint `POST /scheduled/daily-trivia` in `app/routes/scheduled_tasks.py`, with `verify_cron_secret` and `response_model`.
- [x] T024 [US4] Tests:
  - 403 without the secret
  - a user at local 9am is reminded and a user at local 8am isn't
  - a user who already answered isn't reminded
  - a user with push disabled isn't reminded
  - a null timezone is treated as New York
  - a second run in the same hour reminds 0

---

## Phase 7: US5, timezone (P2)

- [x] T025 [US5] `PUT /users/me/timezone` in `app/routes/user.py`: validate with `ZoneInfo`, return 422 `invalid_timezone` otherwise, and save to `User.timezone`.
- [x] T026 [US5] Tests:
  - a valid zone is saved and shifts the user's `date`
  - an invalid zone returns 422 and leaves the value unchanged
  - 401 without auth

---

## Phase 8: Polish & cross-cutting

- [x] T027 Delete `DailyTriviaAnswer`, `DailyTriviaStreak` and `DailyTriviaReward` in `app/services/account_deletion.py`, in both the trivia blocks, with a test or an extension of the existing account-deletion test.
- [x] T028 Run the full `pytest` suite and fix any regressions.
- [ ] T029 Validate [quickstart.md](quickstart.md) on dev after `/deploy-dev`, including creating the dev Cloud Scheduler job.

---

## Dependencies

- Setup → Foundational → US1 → US2 → US3.
- US4 needs US1 (the answer check) and US2 (streak data in the push). US5 is independent once Foundational is done.
- T015, T016, T017 and T021 can be done in parallel; they touch different files.

## Implementation strategy

MVP is US1 + US2 (answer and streak). US3, US4 and US5 follow, then Polish. The frontend can start against the contract once US1 and US2 are on dev.
