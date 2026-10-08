# Feature Specification: Trivia Integrity & Premium-Only Challenge Creation

**Feature Branch**: `fix/trivia-integrity` | **Spec Folder**: `specs/001-trivia-integrity/`

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Trivia integrity and premium-only challenge creation. The 60-day launch trivia competition (starts Nov 1 2026) awards real Shopify prize codes ($59/$30/$15) based on single-player best scores, but today the server trusts the client: question draws include the correct answer, single-game submissions accept arbitrary answer lists not tied to any draw, and the 30-second timer and grace tokens exist only in the app. In multiplayer challenges, a player can answer with a question other than the challenge's current one. Creating multiplayer challenges should become a premium feature, while free users can still accept and fully play challenges they receive. Out of scope: gating competition prizes on premium, daily play caps."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single-player scores can't be faked (Priority: P1)

A player starts a single-player game, chooses a category and difficulty, and the server runs it. The server picks the questions, shows them one at a time without the answer, checks each answer as it comes in, applies the 30-second limit, ends the game on the first wrong answer (unless a grace token is used), and records the final score. A score only counts toward the competition if the server ran the whole game.

**Why this priority**: The launch competition pays real prize codes from these scores starting Nov 1 2026. Today anyone who edits the requests can post a perfect score, and an honest player who loses a prize to a faked score is the main harm this feature prevents.

**Independent Test**: Start a game and play it through the new flow. Confirm no question's answer is visible before answering, that wrong, late or out-of-order answers are handled as described, and that the final score matches the answers given. Confirm that only these scores appear in competition standings.

**Acceptance Scenarios**:

1. **Given** a signed-in player, **When** they start a game with a category and difficulty, **Then** they receive the first question and its options, and nothing in the response reveals the correct option.
2. **Given** a game in progress, **When** the player answers the current question correctly within 30 seconds, **Then** they are told it was correct, see their updated score and streak, and receive the next question.
3. **Given** a game in progress, **When** the player answers a question that is not the current question of their game, **Then** the answer is rejected and the game state does not change.
4. **Given** a game in progress, **When** the player answers more than 30 seconds (plus a small network allowance) after the question was shown, **Then** the answer counts as wrong.
5. **Given** a player with no grace tokens, **When** they answer wrong, **Then** they are shown the correct option, the game ends and their score is recorded.
6. **Given** a player who has answered 10 questions correctly in this game, **When** they then answer wrong, **Then** they are offered their grace token and have 10 seconds (plus allowance) to use it. Using it lets them continue without breaking their streak. Declining or letting the time run out ends the game.
7. **Given** a game that has ended, **When** the player tries to answer again, **Then** the answer is rejected.
8. **Given** a player who leaves mid-game, **When** they choose to end it, **Then** their score so far is recorded once, and asking to end it again returns the same result without recording a second score.
9. **Given** the competition is running, **When** standings are calculated, **Then** only scores from server-run games count.
10. **Given** a game run by another player, **When** a player tries to answer, use grace or end it, **Then** they are refused.

---

### User Story 2 - Old app versions are told to update (Priority: P1)

Players on app versions released before this change still use the old flow, where the app gets the answers up front and sends a finished game. Until the updated app is in both stores, that flow keeps working. After that, an operator switches it off, and old-version players are told to update the app.

**Why this priority**: The old flow is the hole being closed. It has to be switched off before the competition starts, and players need a clear message instead of a broken game.

**Independent Test**: With the old flow switched off, call the old question-draw and game-submit requests. Both are refused with an "update the app" message. With it switched on, both behave as today.

**Acceptance Scenarios**:

1. **Given** the old flow is switched on (the default), **When** an old app version draws questions and submits a game, **Then** it behaves exactly as today.
2. **Given** the old flow is switched off, **When** an old app version draws questions or submits a game, **Then** it is refused with an "upgrade required" response whose message asks the player to update the app, and no score is recorded.
3. **Given** the old flow is switched on, **When** an old app version submits a game, **Then** the score is recorded as not server-verified and does not count toward competition standings.

---

### User Story 3 - Multiplayer answers must match the current question (Priority: P1)

In a multiplayer challenge, each answer must be for the question the challenge is currently on.

**Why this priority**: The fix is small, and challenges are another place where answers can be faked today.

**Independent Test**: In an active challenge, send an answer for a question other than the current one and confirm it is rejected. Send one for the current question and confirm it is accepted.

**Acceptance Scenarios**:

1. **Given** an active challenge on question N, **When** a participant answers with a different question, **Then** the answer is rejected and nothing changes.
2. **Given** an active challenge on question N, **When** a participant answers question N, **Then** it is graded as today.
3. **Given** any challenge answer, **When** the reported time is negative or over 30 seconds, **Then** it is stored as 0 or 30 seconds respectively.

---

### User Story 4 - Only premium users can create challenges (Priority: P2)

Creating a challenge becomes a premium feature. Anyone who is challenged, free or premium, can still accept, decline, play, forfeit and nudge.

**Why this priority**: It's an upgrade incentive, not a fix, so it ranks below the integrity work. It can ship on its own.

**Independent Test**: A free user tries to create a challenge and is refused with a premium-required response. A premium user creates one against a free user, and the free user accepts and plays it to the end.

**Acceptance Scenarios**:

1. **Given** a free user, **When** they try to create a challenge, **Then** they are refused with a premium-required response and no challenge or notification is created.
2. **Given** a user on any premium tier (mentor premium, apprentice premium, mentor-gifted), or an admin, **When** they create a challenge, **Then** it is created as today.
3. **Given** a free user who has been challenged, **When** they accept, answer every question, nudge or forfeit, **Then** each works as today.
4. **Given** a user whose premium has expired, **When** they try to create a challenge, **Then** they are refused as a free user. Challenges they already created continue normally.

### Edge Cases

- **Grace token use:** a player who earns more than one grace token (at 10, 20, … correct) can use them one at a time. Each wrong answer is a separate grace decision.
- **Running out of questions:** if a game uses every approved question for its category and difficulty, the game ends and the score is recorded.
- **Starting a new game with one unfinished:** the unfinished game ends with the score earned so far, and that score is recorded.
- **Leaving mid-question** (app backgrounded or closed): the clock keeps running. If the player returns within 30 seconds (plus allowance) they can still answer. Up to 10 seconds after that, a player with a grace token is offered it. After that the game is over, and the score earned so far is recorded.
- **Abandoned games** with no activity for over an hour end with the score earned so far (a safety net; the expired-question rule above normally closes them sooner). A wrong answer that triggered a grace offer which was never used counts as wrong.
- **Timeout while awaiting grace:** a grace decision sent after the deadline ends the game, the same as declining.
- **Retries:** a repeated request (network retry) for the most recently graded answer must return the same outcome without grading it twice. This includes an answer that ended the game or triggered a grace offer.
- **No questions available:** if the chosen category and difficulty has no approved questions, the game can't start and the player is told so.
- **Shuffled options:** the correct option is judged by the option order the player actually saw, not the stored order.
- **Old scores:** scores recorded before this change stay on personal bests and the general leaderboard. They are outside the competition window, which starts Nov 1 2026.
- **Premium and accepting:** a free user who loses premium while a challenge they created is pending or active keeps playing it. The premium check applies only when a challenge is created.

## Requirements *(mandatory)*

### Functional Requirements

**Server-run single-player games**

- **FR-001**: The system MUST let a signed-in player start a single-player game for a category (including "random") and a difficulty. The server picks and orders the questions and records the game as belonging to that player.
- **FR-002**: The system MUST NOT reveal any question's correct option before that question has been answered in the game.
- **FR-003**: The system MUST give the player only the current question. The next one is revealed only after the current one has been graded.
- **FR-004**: The system MUST accept an answer only for the current question of an active game owned by the caller, and MUST reject anything else without changing the game.
- **FR-005**: The system MUST measure the time to answer from when the server sent the question. An answer arriving more than 30 seconds after that, plus a fixed network allowance, MUST count as wrong.
- **FR-006**: After each answer the system MUST tell the player whether they were right, which option was correct, and their current score, streak and grace tokens.
- **FR-007**: The system MUST award one grace token for every 10 correct answers in a game.
- **FR-008**: On a wrong answer, if the player has a grace token, the system MUST wait up to 10 seconds plus the allowance for them to use or decline it. If they have none, the game MUST end. For a late or missing answer, the grace window starts when the question's 30 seconds ran out, not when the late answer arrives. So a player who leaves the app can't come back after the window and still be offered grace.
- **FR-009**: Using a grace token MUST consume it and let the game continue as though the wrong answer did not break the streak. Declining or missing the deadline MUST end the game.
- **FR-009a**: The clock MUST keep running whether or not the player is in the app. Once the current question's time (plus any grace window the player was entitled to) has run out with no answer, the game MUST be treated as over. Any later request finds it finished, and the background sweeps record its score without waiting for the one-hour idle rule.
- **FR-010**: The score and streak MUST be computed only from the server's own grading, using the existing scoring rules (100 points × streak multiplier).
- **FR-011**: Ending a game MUST record the score once, award badges, and report personal best and leaderboard rank as today. Ending it again MUST return the same result without recording again.
- **FR-012**: Every recorded single-player score MUST say whether a server-run game produced it.
- **FR-013**: Competition standings and prize decisions MUST count only server-verified scores. A verified score belongs to the moment its game **started**, so a game started inside the competition window counts even if it finishes (or is auto-closed) after the window ends. Before winners are decided, any unfinished games MUST be closed so their scores are included.

**Old single-player flow**

- **FR-014**: The old question-draw and game-submit requests MUST keep working with unchanged responses while an operator setting allows them. That setting MUST be on by default.
- **FR-015**: With the setting off, both old requests MUST be refused with an "upgrade required" status and a message asking the player to update the app, and MUST NOT record anything.
- **FR-016**: Scores sent through the old submit request MUST be recorded as not server-verified.

**Multiplayer**

- **FR-017**: A challenge answer MUST be rejected unless it is for the challenge's current question.
- **FR-018**: The reported time for a challenge answer MUST be clamped to between 0 and 30 seconds.
- **FR-019**: Only premium users (any active premium tier, or admins) MUST be able to create a challenge. Others MUST receive the standard premium-required refusal. No challenge or notification is created.
- **FR-020**: Accepting, declining, answering, forfeiting, nudging, cancelling and viewing challenges MUST stay open to participants regardless of premium.

### Key Entities

- **Single-player game session**: one game run by the server. It has:
  - the owner, category and difficulty;
  - the ordered questions and the correct option for each as shown;
  - the current position and when the current question was sent;
  - answers given so far, score, streak and correct count;
  - grace tokens earned and used, and any pending grace deadline;
  - its state (in progress, awaiting a grace decision, finished) and its timestamps.
- **Single-player score** (existing): gains a "server-verified" marker and a link to the game session that produced it.
- **Challenge** (existing): no new data. Answer checks are stricter.

### Access, Compatibility & Clients *(mandatory)*

- **Roles**: any signed-in user (mentor, apprentice or admin) can play single player and take part in challenges. Creating a challenge requires premium or admin.
- **Ownership**: a player can only answer, use grace on, or end their own game sessions. Challenge actions stay limited to the two participants, as today.
- **Premium**: creating a challenge is premium-gated (403 when not premium). Everything else in trivia stays free.
- **Compatibility**:
  - New single-player game requests are additive.
  - The old question-draw and game-submit requests will be **switched off** (refused with "upgrade required") once the minimum app version below is live in both the App Store and Google Play.
  - **Minimum app version that no longer needs them: 2.2.0** (the first release with the frontend changes; confirm at release time).
  - The challenge-create 403 and the challenge-answer rejection are new error responses on existing requests. App versions before 2.2.0 will show their generic error for them.
- **Frontend**: `trooth_assessment/specs/001-trivia-integrity/` (to be written), linking this spec's `contracts/`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No response a player receives during a single-player game, before they answer, contains the correct option for that question. This is verified across a full game of at least 50 questions.
- **SC-002**: Once the old flow is switched off, every single-player score recorded is server-verified. Before then, unverified scores count toward the competition 0% of the time.
- **SC-003**: Each of the known cheats is refused:
  - submitting the same question twice;
  - answering a question from outside the game;
  - claiming a different difficulty;
  - answering after the game has ended;
  - claiming unearned grace tokens;
  - answering after the time limit (graded wrong).
- **SC-004**: On the dev environment, a player's answer feedback and next question come back in under 1 second under normal conditions.
- **SC-005**: The old flow is switched off in production before the competition starts on Nov 1 2026.
- **SC-006**: 100% of free users trying to create a challenge are refused with the premium-required response. 100% of challenges sent to free users can be accepted and played to completion.

## Assumptions

- **Network allowance:** about 3 seconds on top of the 30-second answer limit and the 10-second grace decision. This absorbs mobile latency without meaningfully extending play time.
- **Game length:** a game has no fixed question count. It continues until the player's run ends or every approved question for that category and difficulty has been used once. This matches today's app, which fetches more questions mid-game, so long runs and the 60–100 streak badges stay reachable.
- **Old scores:** scores recorded before this change stay as they are. They are marked not server-verified, but the competition window starts after this ships, so nothing currently counted is affected.
- **Grace and scoring:** a wrong answer saved by a grace token does not break the streak and scores no points, matching today's app.
- **Premium:** "premium" means whatever the existing premium check says, which includes admins, every premium tier, and the global premium switch.
- **Rejection codes:** the "upgrade required" refusal uses a status distinct from premium-required (426), so the app can tell them apart.
- **Turning off the old flow:** the operator setting is changed by deploying with it switched off. It is not changed from inside the app.
- **Out of scope:**
  - gating competition prizes on premium;
  - daily or per-game play caps;
  - multiplayer tie-breaks by time;
  - server-side timing for multiplayer answers.
