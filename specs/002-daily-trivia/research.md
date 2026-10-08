# Research: Daily Trivia Question & Streak Rewards

## R1. Which date is "today"

- **Decision**: Use each user's local date. It is computed as `datetime.now(ZoneInfo(user.timezone or "America/New_York")).date()`. `User.timezone` already exists but nothing writes it, so `PUT /users/me/timezone` is added. Add the `tzdata` pip package: the `python:3.11-slim` image has no system zoneinfo database, so `ZoneInfo` would fail at runtime.
- **Rationale**: The spec puts "today" and "9am" on the user's own clock. The stdlib `zoneinfo` plus `tzdata` is the smallest dependency that gives a correct IANA database on Cloud Run.
- **Alternatives considered**:
  - One global date (America/New_York). Wrong for users far from Eastern time.
  - `pytz`. Older API and still an extra dependency.
  - Installing `tzdata` with apt in the Dockerfile. Works in production but not in local virtualenvs on every OS. The pip package works everywhere.

## R2. Choosing a question per date without races

- **Decision**: `daily_trivia_questions.date` is a unique column, and the question is chosen lazily on the first request for a date.
  - The chooser shuffles the (category × level) pairs for the four real categories and the two levels, and takes the first pair that has an eligible question.
  - Eligible means approved and not used as a daily question in the last 180 days.
  - If no question is eligible, it falls back to the approved beginner/challenger question used longest ago.
  - When two requests insert at once, the unique constraint makes one of them fail; that one rolls back and re-reads the row.
- **Rationale**: Nothing needs scheduling and nothing can be missed. Picking the pair first gives categories and levels an equal chance regardless of how many questions each has. The unique constraint is the only race guard that works the same on PostgreSQL and on the SQLite test database.
- **Alternatives considered**:
  - A nightly cron that pre-creates the row. One more job to fail. Timezones ahead of UTC would need the row before midnight UTC anyway.
  - A deterministic hash of the date into the question list. The pick shifts whenever questions are added.

## R3. Fixing the option order

- **Decision**: Shuffle once when the date's row is created. Store the shuffled options (`{"a": .., "b": .., "c": .., "d": ..}`), the shuffled correct letter, the question text, the type, the category and the level on the row.
  - True/false questions keep a = True and b = False, the same rule as `_shuffle_options` in `app/services/trivia.py`.
  - This reuses `_shuffle_options` rather than duplicating it.
- **Rationale**: Everyone sees the same order (FR-004). Editing the bank later doesn't change a day that has already happened.

## R4. Streak math

- **Decision**: Freezes are used lazily, when the user next answers. Reads compute the effective state without writing anything.
  - On answer for date D, with L the last answered date and `missed = (D − L).days − 1`:
    - If D ≤ L, refuse with 409.
    - If `missed == 0`, the streak continues.
    - If `0 < missed ≤ freezes`, use `missed` freezes and record those dates as freeze-covered.
    - Otherwise reset: freezes = 0, the perfect flag is cleared, the earned-tier list is cleared, and the streak start becomes D.
  - Then:
    - `current += 1`
    - `perfect = perfect and correct` (or just `correct` for a new streak)
    - if `current % 15 == 0 and freezes < 2`, then `freezes += 1`
    - `longest = max(longest, current)`
    - `L = D`
  - If `current` is 45, 60 or 90 and that tier isn't in the earned-tier list, add it and create a pending reward.
  - Reads use the same `missed` calculation against today: if it exceeds the freezes, the displayed streak is 0. Otherwise the freezes that would be used are shown as already used, and their dates as freeze-covered.
  - The streak row is locked (`SELECT … FOR UPDATE`) while an answer is processed.
- **Rationale**: Nothing has to run daily to keep streaks correct, and an unread streak costs nothing. The lock and the unique (user, date) answer constraint make double-taps safe.
- **Alternatives considered**: A nightly job that breaks streaks and uses freezes. It runs over every user, every timezone has a different midnight, and the job can fail.

## R5. Issuing reward codes

- **Decision**: The answer transaction creates a `daily_trivia_rewards` row with status `pending`. It is unique on (user, streak start, tier). After the response is sent, a FastAPI `BackgroundTasks` job runs `process_reward(reward_id)`, and the hourly cron re-runs it for any reward that isn't finished. `process_reward` copies the per-step, row-locked pattern of `trivia_competition._ensure_code` / `_ensure_notified`:
  1. **Code**: lock the reward. If it has no code, create one in Shopify, set it `active` with an expiry 60 days out, and mark every other `active` reward of this user `superseded`.
  2. **Deactivate**: for each superseded reward with a Shopify id that isn't deactivated, call `discountCodeDeactivate` and set `deactivated_at`.
  3. **Email**: send if `emailed_at` is unset. The email is the delivery of record.
  4. **Push**: best-effort; set `pushed_at` either way.
- **Rationale**: Shopify can't slow down or break the answer (FR-018), every step can be retried without repeating (FR-017), and the code mirrors a flow that already works in production.
- **Alternatives considered**:
  - Calling Shopify inline during the answer. It adds 1–2 seconds and couples the answer to Shopify's uptime.
  - Retrying only in the cron. Users would wait up to an hour for the code.

## R6. The Shopify discount

- **Decision**: Add `create_percentage_code(percent, title, starts_at, ends_at)` and `deactivate_code(discount_id)` to `app/services/shopify_admin.py`.
  - Code format: `TROOTH-STREAK{tier}-XXXXXX`.
  - Discount: `customerGets.value.percentage = percent/100` on `items: {all: true}`, `usageLimit: 1`, `appliesOncePerCustomer: true`, and `endsAt` 60 days out.
  - Uses the same dry-run behaviour (`DRYRUN-` codes outside prod; an error in prod when the store isn't configured) and the same client-credentials token.
- **Rationale**: "X% off merch" maps directly onto a store-wide percentage code. Deactivating, rather than deleting, keeps the record visible in the Shopify admin.
- **Open product risk**: a percentage off the whole order has no dollar cap, so a 60% code on a large order costs more than a 60% code on one item. Shopify basic codes can't cap the discount amount. A minimum or maximum order rule, or limiting the code to a collection, can be added in `build_percentage_input` later if needed.

## R7. Reminders

- **Decision**: `POST /scheduled/daily-trivia` runs hourly (`0 * * * *`, any zone) and is protected by `verify_cron_secret`. It does three things:
  1. Reminders. Take the distinct `User.timezone` values (null counts as America/New_York) and keep the zones where the current local hour is 9. For users in those zones who have push enabled, haven't answered for their local date, and have `last_reminded_date` different from their local date, set `last_reminded_date` and send a personalised push through `PushNotificationService.send_to_user` with data `{type: "daily_trivia", screen: "daily_trivia"}`.
  2. Re-run `process_reward` for unfinished rewards.
  3. Expire `active` rewards whose `expires_at` has passed.
- **Rationale**: One job is one scheduler entry. Filtering by timezone keeps the query small. `last_reminded_date` makes running twice in an hour harmless (SC-005).
- **Alternatives considered**:
  - FCM topics per timezone. The topic can't skip users who already answered.
  - One send at 9am Eastern. Wrong for users in other timezones.

## R8. Answers that cross midnight

- **Decision**: `POST /trivia/daily/today/answer` takes `{question_date, option}`. If `question_date` isn't the user's current local date, the server returns 409 with `detail` set to `"question_expired"`, and the app reloads.
- **Rationale**: Otherwise a user who opens the modal at 11:59pm and taps at 12:01am would be graded against a question they never saw.
