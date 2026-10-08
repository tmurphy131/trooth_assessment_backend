# Research: Trivia Integrity & Premium-Only Challenge Creation

No open questions came out of Technical Context. These are the design decisions behind the plan.

## R1. Where game state lives

- **Decision**: in a database row (`trivia_single_sessions`), one per game.
- **Rationale**:
  - Cloud Run runs several instances, so in-memory state can't be used.
  - The server must record when each question was sent (timer), what was answered (no duplicates, retries), and grace deadlines.
  - The finished score must be written exactly once.
  - A row gives all of that, plus row locking (`with_for_update`) against double-taps.
- **Alternatives considered**:
  - A signed token returned to the client: stateless, but it can't stop the same token being replayed or record server time per answer without growing into a session anyway.
  - Redis: not in the stack.

## R2. How a session stores its questions

- **Decision**:
  - At start, store the **whole approved pool** for the category and difficulty as a shuffled list of IDs (`question_ids`). There is no fixed game length.
  - When a question is served, shuffle its options (`_shuffle_options`) and store a snapshot of it in `current_question`: `{id, question_text, question_type, options{a..d}, correct}`.
  - Grading uses that snapshot.
- **Rationale**:
  - Today's app fetches more questions mid-game (`trivia_game_screen.dart:91-110`), so games run until the pool is used up. A fixed cap would end long runs and make the 60–100-streak badges impossible to earn.
  - Storing IDs only (a few KB even for large pools) keeps the row small.
  - The one live snapshot means answers are judged against the option order the player saw, and a question edit mid-game can't change the grading.
  - The old draw never shuffled options, so this also stops "the answer is always B" memorisation.
- **Alternatives considered**:
  - Snapshot every question at start: the row grows with the pool size for no benefit.
  - A 50-question cap with top-ups: more state and more requests for the same result.

## R3. Timer enforcement

- **Decision**:
  - Store `current_served_at` when a question is put in a response.
  - On answer, `elapsed = now − current_served_at`. Over `30 s + 3 s` allowance counts as wrong, with `timed_out=true`.
  - The client may send `selected: null` when its own timer expires.
- **Rationale**: server time is the only clock the player can't change. 3 s covers a slow mobile round trip.
- **Clock keeps running while away** (added after product review): the player found that backgrounding the old app paused its countdown.
  - When an answer is late, the grace window is anchored to the question's expiry (`served_at + 30 s`) instead of to when the late answer arrived: `deadline = min(now, served_at + 30 s) + 10 s + 3 s`. If that has already passed, the game finishes immediately with no grace offer.
  - A session whose current question expired (`served_at + 33 s`, or `+ 46 s` when the player holds a grace token) with no answer is treated as stale, so `finish_stale` and the competition finalize close it without waiting for the 1 h idle rule.
- **Note**: SQLite (tests) returns naive datetimes. Every stored timestamp is normalized with an `_aware()` helper (same as `trivia_competition._aware`) before comparing with `_now()`.
- **Alternatives considered**:
  - Trusting the client's `time_used_ms`: that's the current hole.
  - A tighter 1 s allowance: risks marking honest answers on slow connections as wrong.

## R4. Grace token semantics (match today's app)

- **Decision**:
  - A token is earned whenever `correct_count % 10 == 0` after a correct answer.
  - A wrong answer (including a timeout) with tokens > 0 sets `status=awaiting_grace` and `grace_deadline = now + 10 s + 3 s`.
  - `use=true` before the deadline consumes the token, marks that answer `graced`, and serves the next question.
  - `use=false`, a late call, or any lazy check after the deadline finishes the game.
  - Graced answers are left out of scoring, which is what the app does today by dropping them before submitting. So the streak carries on and the graced question scores 0.
- **Rationale**: scores stay comparable with games played before this change.

## R5. Retries and double submits

- **Decision**:
  - All mutations lock the session row.
  - The **first** check on `answer` (after ownership): if `question_id` equals the **last answered** question's ID, return the current state again (200) without re-grading, whatever the status. That covers the answer that ended the game or triggered a grace offer.
  - Otherwise `awaiting_grace` or `finished` gets 409, and a non-current `question_id` gets 400.
  - `finish` on a finished session returns the stored result.
- **Rationale**: mobile retries after a timeout must not cost the player a game, show a spurious error, or double-record a score.

## R6. Abandoned and overlapping games

- **Decision**:
  - When a game is touched or a new one started, any of the user's sessions that are `active` or `awaiting_grace` and past their limits are finished.
  - Starting a new game finishes any unfinished one first.
  - The existing daily `/scheduled/trivia-expiry` job also finishes sessions idle for over 1 h.
  - Before recording winners, `finalize_competition` closes stale games (`trivia_session.games_in_progress_before`). If a game that started before the end is still being played, it returns `waiting_for_games` and the next hourly run tries again. This keeps a player who is mid-game at midnight from being cut off or left out.
  - In all of these, a pending graced answer counts as wrong.
- **Rationale**: the score earned is never lost, and a player can't keep several games open to scout questions.
- **Alternative considered**: a separate cron only. The lazy finish already covers the common case, and the existing job covers the rest.

## R7. Old endpoints

- **Decision**:
  - A new setting `trivia_legacy_single_enabled` (env `TRIVIA_LEGACY_SINGLE_ENABLED`, default `true`).
  - When false, `GET /questions/draw` and `POST /single/submit` raise `HTTPException(426, detail="Please update the app to keep playing trivia.")`.
  - When true, they behave as today, except that submit writes `verified=false`.
  - `detail` is a plain string so old app versions that show `detail` display a readable message.
- **Rationale**: Principle VI (removal specified, minimum version named) and Principle IV (config through settings).
- **Alternative considered**: a hard-coded cutover date. You can't schedule a store approval, so a flag is safer.

## R8. Premium gate response shape

- **Decision**: `403` with `detail={"error": "premium_required", "message": "Premium subscription required to create challenges", "upgrade_url": "/settings/subscription"}`. This is the object shape used at `app/routes/mentor.py:496`.
- **Rationale**:
  - The app maps any 403 on this endpoint to `PremiumRequiredException`, so the status code is what matters (Principle XII).
  - Of the two known debt shapes, this one is machine-readable. No new shape is added.

## R9. Competition counting

- **Decision**: add `TriviaSingleScore.verified == True` to the filter in `compute_standings`. Personal bests, the general leaderboard and badges keep counting all scores.
- **Rationale**: the spec limits the competition change to "only verified counts". Once the old flow is off, every new score is verified anyway.

## R10. When a verified score counts

- **Decision**: a session's score row gets `created_at = session.created_at` (when the game **started**), not when it finished.
- **Rationale**:
  - Games can be closed late: by the player, by the next game start, or by the daily or finalize sweeps.
  - Dating the score by game start means a game begun inside the competition window counts, even if it is closed after the window ends.
  - It also stops a game started before the window opens from being counted.
- **Alternative considered**: dating by finish time. That makes the outcome depend on when cleanup happens to run.

