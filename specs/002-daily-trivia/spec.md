# Feature Specification: Daily Trivia Question & Streak Rewards

**Feature Branch**: `feature/daily-trivia` | **Spec Folder**: `specs/002-daily-trivia/`

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Daily trivia questions. Each user gets a daily trivia notification at 9am, and when they open the app there is a daily trivia modal with a multiple choice question. Everyone sees the same question each day. Questions are random between beginner and challenger level, from a random category, and the category and level are shown. The app tracks daily question streaks and shows them weekly or monthly depending on how long the streak is. A 45-day streak earns 15% off merch, 60 days earns 35%, and 90 days earns 50%. Offers don't stack: an unused lower code is upgraded to the higher one. Answering correctly every day of the streak adds an extra 10%. Missed days can be covered by earned streak freezes. All coupons are automated."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Answer today's question (Priority: P1)

A signed-in user asks for today's question and sees the question, its options, its category and its level, but not the answer. They pick one option. The server tells them whether they were right and shows the correct option. Every user who asks on the same calendar date gets the same question. Each user can answer once per date.

**Why this priority**: Everything else (streaks, pushes, rewards) is built on top of answering. On its own it is already a daily reason to open the app.

**Independent Test**: As two different users on the same date, ask for today's question and confirm both get the same question with no answer revealed. Answer as one user, confirm the result and correct option come back, and confirm a second answer on the same date is refused.

**Acceptance Scenarios**:

1. **Given** a signed-in user who has not answered today, **When** they ask for today's question, **Then** they get the question text, its options, its category and its level, and nothing in the response reveals the correct option.
2. **Given** two users whose local date is the same, **When** each asks for today's question, **Then** both get the same question with the options in the same order.
3. **Given** a user who has not answered today, **When** they submit one of the offered options, **Then** they are told whether it was correct, shown the correct option and their updated streak.
4. **Given** a user who has already answered today, **When** they ask for today's question, **Then** they get the question together with the option they chose, whether it was correct and the correct option.
5. **Given** a user who has already answered today, **When** they submit another answer, **Then** it is refused and their first answer stands.
6. **Given** a user, **When** they submit an option that isn't one of the question's options, **Then** it is refused and nothing is recorded.
7. **Given** today's question was chosen, **When** looking at its category and level, **Then** the category is one of the four real categories (Old Testament, New Testament, Theology & Doctrine, Discipleship & Living) and the level is beginner or challenger.

---

### User Story 2 - Build and keep a streak (Priority: P1)

Each day a user answers, right or wrong, their streak grows by one. If they miss a day and have a streak freeze, the freeze covers that day and the streak survives without growing. If they miss a day with no freeze, the streak resets. Users earn one freeze for every 15 days of streak and can hold at most two. A user can see their current streak, longest streak, freezes, the dates they answered and the dates freezes covered, and how far they are from the next reward.

**Why this priority**: The streak is the habit loop and the basis for rewards.

**Independent Test**: Answer on consecutive dates and confirm the streak counts up. Skip a date with a freeze available and confirm the streak continues and a freeze is used. Skip a date with no freeze and confirm the streak resets.

**Acceptance Scenarios**:

1. **Given** a user with a streak of N who answered yesterday, **When** they answer today, **Then** their streak is N+1.
2. **Given** a user who has never answered, **When** they answer today, **Then** their streak is 1.
3. **Given** a user whose streak reaches 15 or 30 (or any multiple of 15) and who holds fewer than 2 freezes, **When** the streak reaches that number, **Then** they gain one freeze.
4. **Given** a user holding 2 freezes, **When** their streak reaches another multiple of 15, **Then** they still hold 2.
5. **Given** a user who missed K days in a row and holds at least K freezes, **When** they next answer, **Then** K freezes are used, the missed dates are recorded as covered, and the streak continues at its previous count plus one.
6. **Given** a user who missed more days in a row than the freezes they hold, **When** they next answer, **Then** their streak restarts at 1 and their freezes are cleared.
7. **Given** a user whose streak has lapsed (missed days beyond their freezes) but who hasn't answered since, **When** they view their streak, **Then** it shows 0, not the old count.
8. **Given** a user, **When** they view their streak, **Then** they see the current streak, longest streak, freezes held, the answered dates and freeze-covered dates of the current streak, the next reward milestone and what it is worth, and whether the current streak is still perfect.

---

### User Story 3 - Earn merch discounts automatically (Priority: P2)

When a user's streak reaches 45, 60 or 90 days, the system creates a single-use merch discount code for them and sends it by push and email. The discount is 15%, 35% or 50%, plus 10% if every answer in the current streak was correct. A user holds at most one active reward code: when they reach a higher tier, the earlier unused code is switched off and replaced by the higher one. Codes expire 60 days after they are issued.

**Why this priority**: The rewards drive long streaks, but answering and streaks work and have value without them.

**Independent Test**: Bring a test user to 44 days and answer once more. Confirm a 15% code (25% if perfect) is issued, recorded and sent. Then bring them to 59 days and answer. Confirm the 45-day code is switched off and a 35% code (45% if perfect) replaces it.

**Acceptance Scenarios**:

1. **Given** a user at 44 days whose streak has at least one wrong answer, **When** they answer on day 45, **Then** a 15% single-use code is created, recorded as their active reward, and sent to them by push and email.
2. **Given** a user at 44 days whose every answer in the streak was correct, **When** they answer correctly on day 45, **Then** the code is 25%.
3. **Given** a user with an active 45-day code, **When** they reach 60 days, **Then** the 45-day code is switched off in the store, marked superseded, and a 35% (or 45% if perfect) code becomes their active reward.
4. **Given** a user reaches 90 days, **Then** they get 50% (or 60% if perfect) on the same terms, and no further codes are issued in that streak.
5. **Given** a reward was already issued for a tier in the current streak, **When** the tier check runs again (retries, duplicate requests), **Then** no second code is created and the user is not notified twice.
6. **Given** creating the code in the store fails, **When** the user answers, **Then** their answer and streak are still saved, and the code is created on a later retry without a duplicate.
7. **Given** a reward code was issued more than 60 days ago, **When** the daily expiry runs, **Then** it is marked expired and no longer shown as active.
8. **Given** a user whose streak reset after earning the 45-day reward, **When** they build a new streak to 45, **Then** they can earn the 45-day reward again.
9. **Given** a user with an active code, **When** they view their streak, **Then** they see the code, its percentage and its expiry date.

---

### User Story 4 - Daily 9am reminder (Priority: P2)

At 9am in each user's local time, users who have push enabled and haven't answered today's question get a push notification inviting them to answer it. Users who already answered don't get it.

**Why this priority**: The reminder keeps streaks alive, but users can still answer without it.

**Independent Test**: With users in two timezones, run the hourly reminder job at a time when it is 9am for one of them. Confirm only that user is notified, and not if they already answered.

**Acceptance Scenarios**:

1. **Given** a user with push enabled whose local time is in the 9am hour and who hasn't answered today, **When** the hourly reminder runs, **Then** they receive one push about today's question.
2. **Given** that user already answered today, **When** the reminder runs, **Then** they receive nothing.
3. **Given** a user with push disabled, **When** the reminder runs, **Then** they receive nothing.
4. **Given** a user with no timezone saved, **When** the reminder runs, **Then** they are treated as being in America/New_York.
5. **Given** the reminder job is called twice in the same hour, **When** it runs, **Then** no user is notified twice for the same date.
6. **Given** a caller without the scheduler secret, **When** they call the reminder job, **Then** they are refused.

---

### User Story 5 - App reports the user's timezone (Priority: P2)

The app tells the server the user's timezone, so "today" and "9am" match the user's own clock.

**Why this priority**: Without it, everyone runs on the default timezone. That still works, but feels wrong outside the Eastern time zone.

**Independent Test**: Save a timezone for a user, then confirm their "today" and reminder hour follow it. Confirm an invalid timezone is refused.

**Acceptance Scenarios**:

1. **Given** a signed-in user, **When** they save a valid timezone name (e.g. "America/Chicago"), **Then** it is stored and used for their daily date and reminder hour.
2. **Given** a signed-in user, **When** they save something that isn't a valid timezone name, **Then** it is refused and the stored value doesn't change.

### Edge Cases

- **Choosing the question**: the first request for a date chooses that date's question. If two requests arrive at once, both get the same question.
- **No repeats**: a question used as the daily question in the last 180 days isn't chosen again. If every eligible question was used in that window, the one used longest ago is chosen.
- **Empty bank**: if there are no approved beginner or challenger questions at all, asking for today's question returns a clear "not available" error instead of failing.
- **Different dates**: users in different timezones can be on different dates at the same moment. Each user gets the question for their own local date.
- **Changing timezone**: a user can only answer for their current local date, and each date only once. A timezone change can't add more than one answered day per date.
- **True/false questions**: these have two options. They are allowed and shown with two options.
- **Freeze-covered days**: these don't count toward the streak or toward the 45/60/90 milestones, and they don't break a perfect run.
- **Wrong answers**: a wrong answer keeps the streak alive but ends the perfect run for the rest of that streak.
- **Upgrading a used code**: if the earlier code was already used, switching it off is harmless and the new code is still issued.
- **Store not configured**: outside production, placeholder (dry-run) codes are issued so the flow can be tested. In production, the code stays pending and is retried.
- **Account deleted**: the user's daily answers, streak and rewards are deleted with the account.
- **Code from an earlier streak**: if a user still holds an unused code from an earlier streak and a new streak reaches a tier worth the same or less, no new code is issued and the better code is kept. A higher tier replaces it as usual.
- **After 90 days**: the streak keeps counting, with no new rewards until the streak resets.

## Requirements *(mandatory)*

### Functional Requirements

**Daily question**

- **FR-001**: The system MUST assign exactly one question to each calendar date and give it to every user whose local date is that date.
- **FR-002**: The question MUST be chosen at random from approved questions at the beginner or challenger level in one of the four real categories, choosing the category at random first.
- **FR-003**: The system MUST NOT reuse a question that was a daily question in the previous 180 days, unless no other question is eligible, in which case it MUST choose the one used longest ago.
- **FR-004**: The option order for a date MUST be fixed when the question is chosen and MUST be the same for every user.
- **FR-005**: The question MUST NOT reveal the correct option to a user until that user has answered it.

**Answering**

- **FR-006**: Each user MUST be able to answer the question for their current local date exactly once. Later answers for the same date MUST be refused, and answers for any other date MUST be refused.
- **FR-007**: After answering, the user MUST be told whether they were correct and which option was correct.

**Streaks and freezes**

- **FR-008**: The system MUST keep, per user: current streak, longest streak, last answered date, freezes held, whether the current streak is perfect, the start date of the current streak, the dates freezes covered in the current streak, and the reward tiers earned in the current streak.
- **FR-009**: Answering on the day after the last answered date MUST add one to the streak.
- **FR-010**: Missed days MUST each use one freeze. If there are more missed days than freezes, the streak MUST restart at 1 and freezes MUST reset to 0.
- **FR-011**: A user MUST gain one freeze whenever the current streak reaches a multiple of 15, up to a maximum of 2 held.
- **FR-012**: The perfect flag MUST become false after the first wrong answer in a streak, and MUST be true again when a new streak starts with a correct answer.
- **FR-013**: When showing a streak whose last answered date is too far in the past for the freezes held, the system MUST show the streak as 0.

**Rewards**

- **FR-014**: When the streak reaches 45, 60 or 90, the system MUST issue a reward for that tier once per streak: 15%, 35% or 50% respectively, plus 10 if the streak is perfect at that moment.
- **FR-015**: Each reward MUST be a single-use merch discount code that expires 60 days after it is issued.
- **FR-016**: A user MUST have at most one active reward. Issuing a higher tier MUST switch off the previous active code in the store and mark it superseded. A tier worth the same or less than the user's current reward MUST NOT replace it.
- **FR-017**: Issuing and notifying MUST be safe to retry: no duplicate codes, no duplicate notifications.
- **FR-018**: A failure to create a code MUST NOT block or undo the answer or the streak update.
- **FR-019**: The user MUST be told about a new reward by push and by email, including the code, the percentage, the expiry date and where to shop.
- **FR-020**: Rewards past their expiry MUST be marked expired by a daily job.

**Reminders and timezone**

- **FR-021**: An hourly scheduled job MUST send one daily-question push to each user who has push enabled, whose local time is in the 9am hour, and who hasn't answered or already been reminded for their local date.
- **FR-022**: The scheduled job MUST require the scheduler secret.
- **FR-023**: Users MUST be able to save their timezone. Invalid timezone names MUST be refused. Users with no saved timezone MUST be treated as America/New_York.

### Key Entities

- **Daily Question**: the question chosen for one calendar date: the date, the question, its category and level, and the fixed option order.
- **Daily Answer**: one user's answer for one date: the option chosen, whether it was correct and when it was given. At most one per user per date.
- **Daily Streak**: one per user: current and longest streak, last answered date, freezes held, perfect flag, streak start, freeze-covered dates, tiers earned this streak, last reminder date.
- **Streak Reward**: a discount earned at a milestone: user, tier, percentage, code, store reference, status (pending, active, superseded, expired), issue and expiry dates, and when it was emailed and pushed.

### Access, Compatibility & Clients *(mandatory)*

- **Roles**: any signed-in user (mentor, apprentice or admin) can get, answer and view their own daily question and streak, and save their own timezone. The reminder and expiry jobs are cron-only, using the scheduler secret.
- **Ownership**: users only see and change their own answers, streak, rewards and timezone.
- **Premium**: free; this feature is not premium-gated.
- **Compatibility**: additive only. New endpoints and tables; no existing route or field changes.
- **Frontend**: `trooth_assessment/specs/NNN-daily-trivia/` (to be written), linking this spec's `contracts/`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of users on the same local date see the same question, and no response before answering contains the correct option.
- **SC-002**: A user can open the question, answer and see their result and streak in under 15 seconds.
- **SC-003**: 0 duplicate reward codes and 0 duplicate reward notifications for any user and tier in a streak, including under retries.
- **SC-004**: 100% of users who reach 45, 60 or 90 days with notifications reachable receive their code within 5 minutes of answering (or within one retry cycle if the store was unavailable).
- **SC-005**: Each eligible user gets at most one daily reminder per local date, sent during their local 9am hour.
- **SC-006**: Within 60 days of launch, at least 25% of weekly active users answer the daily question at least 4 days a week.

## Assumptions

- The existing approved trivia question bank is reused. Before launch it will hold well over 180 eligible beginner and challenger questions. Expert questions are excluded.
- The existing merch store and discount-code mechanism used for trivia competition prizes is reused. Codes are not tied to a store customer account; anyone holding the code can use it once.
- Streak counting uses the user's saved timezone at the time of each request. Users who travel may see their day shift by the time difference.
- A user with no saved timezone is in America/New_York, matching the app's main audience.
- Daily answers don't affect single-player scores, leaderboards, badges or the trivia competition.
- Rewards cap at 60% (90 days with a perfect run). There is no reward beyond 90 days in this version.
- Reward percentages, milestones, freeze rules and code expiry are fixed product rules for this version; changing them requires a deploy.
