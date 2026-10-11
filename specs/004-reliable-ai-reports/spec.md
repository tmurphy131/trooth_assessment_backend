# Feature Specification: Reliable, Fast, Consistent AI Assessment Reports

**Feature Branch**: `feature/ai-scoring-pipeline` | **Spec Folder**: `specs/004-reliable-ai-reports/`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "Reliable, fast, consistent AI assessment reports (backend, with a small app follow-up). Today scoring runs as an in-process background task with no retry; if the instance is recycled or scoring throws, an assessment can sit at 'processing' forever, and when the AI fails the system silently writes default scores and an empty report marked 'done' (users saw Health Score 0% during the 2026-10-10 outage). Scoring takes 2–3 minutes (one AI call per category, sequentially, plus a report call; multiple-choice sent to the AI though correctness is known). The Premium report is generated on first open, raced the background worker and failed with a 500 on malformed AI output. The AI computes numbers itself, so narrative can contradict computed scores. What: durable queued scoring with retries and no concurrent double-scoring; honest 'failed' status instead of empty 'done'; report ready well under a minute; strict structured AI output with retries on malformed responses; AI given computed facts and forbidden to invent numbers, Premium agreeing with free; Premium report generated once during scoring for premium apprentices/mentors with protected on-demand fallback; existing app versions keep working and an app update shows the delayed/failed state. Out of scope: email redesign, questions/templates, Health Score formula."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reports are never lost or silently empty (Priority: P1)

An apprentice submits an assessment. Even if the server restarts mid-scoring or the AI provider has a temporary problem, scoring is retried until it succeeds. If it truly can't complete, the assessment is marked as failed with a reason. The apprentice and mentor see "your report is taking longer than usual" instead of an empty report, and the owner is alerted.

**Why this priority**: Empty or stuck reports are the most damaging failure. They break trust in the core product and happened in production-like conditions on 2026-10-10.

**Independent Test**: On dev, make the AI provider fail (bad model name), submit an assessment, and confirm it's retried, then marked failed with a reason. Restore the provider and confirm a retried or re-queued scoring produces a full report.

**Acceptance Scenarios**:

1. **Given** the AI provider fails temporarily, **When** an assessment is submitted, **Then** scoring is retried automatically and the report completes once the provider recovers, with no user action.
2. **Given** the server instance restarts while scoring is in progress, **When** it comes back, **Then** scoring resumes or restarts and the report completes.
3. **Given** the AI keeps failing for the whole retry period, **When** retries are exhausted, **Then** the assessment's status is "failed" with a reason, no default or empty report is presented as complete, and an alert reaches the owner.
4. **Given** scoring is already running for an assessment, **When** a duplicate request to score the same assessment arrives, **Then** it does not start a second scoring run.
5. **Given** an assessment ended in "failed", **When** the owner re-queues it after the provider is fixed, **Then** it is scored normally.

---

### User Story 2 - Reports arrive in seconds, not minutes (Priority: P1)

After submitting, an apprentice sees their full report quickly, while they're still in the app.

**Why this priority**: A 2–3 minute wait means most users leave before the report exists. Speed directly affects whether people read their results.

**Independent Test**: Submit a typical Master assessment on dev 10 times and measure time from submit to report-ready.

**Acceptance Scenarios**:

1. **Given** normal conditions, **When** an apprentice submits a Master assessment, **Then** the full report is ready within 45 seconds in at least 9 of 10 attempts.
2. **Given** multiple-choice answers, **When** scoring runs, **Then** their correctness is determined exactly from the answer key, not by AI judgment.

---

### User Story 3 - Report content matches the numbers (Priority: P2)

Every narrative statement in the free and Premium reports agrees with the computed Health Score, Biblical Knowledge percentage, per-topic results and previous assessment. Nothing is invented, like "an 11-point improvement from a 70% baseline" when no such baseline exists.

**Why this priority**: Contradictions undermine credibility, especially for mentors using reports to guide conversations, but they don't block anyone from getting a report.

**Independent Test**: Score assessments with and without a previous assessment; check that every number mentioned in the narrative matches the computed facts, and that first-time assessments mention no improvement or decline.

**Acceptance Scenarios**:

1. **Given** a first assessment (no previous one), **When** the report is generated, **Then** it makes no claims about change over time.
2. **Given** a previous assessment exists, **When** the report is generated, **Then** any stated change equals the difference between the two computed Health Scores.
3. **Given** the free and Premium reports for the same assessment, **When** compared, **Then** Health Score, band and Biblical Knowledge percentage are identical.

---

### User Story 4 - Premium report opens instantly and never errors (Priority: P2)

A premium apprentice, or the premium mentor of an apprentice, opens the full Premium report and it's already there. If it isn't (for example, the user upgraded after the assessment), it's generated once, and opening it twice doesn't start two generations or show an error.

**Why this priority**: Premium is the paid experience. A 500 error or a long spinner on the first open was observed in testing.

**Independent Test**: Submit as a premium apprentice; open the Premium report immediately after the free report is ready and confirm it loads without generation. For a non-premium assessment, upgrade, open the report from two devices at once, and confirm one generation and no error.

**Acceptance Scenarios**:

1. **Given** the apprentice or their active mentor is premium when scoring runs, **When** scoring completes, **Then** the Premium report is already available.
2. **Given** a Premium report doesn't exist yet, **When** two requests for it arrive together, **Then** only one generation happens and both requests get the report or a "being prepared" response, never a server error.
3. **Given** the AI returns malformed output while generating a Premium report, **When** this happens, **Then** it's retried and the user never sees a server error.

---

### User Story 5 - App shows a clear status while a report is pending or delayed (Priority: P3)

In an updated app, a report that is still being prepared shows a "preparing your report" state. A failed one shows "taking longer than usual, we're on it". Neither shows a partial or empty report as if it were final.

**Why this priority**: Improves the experience during rare failures. Existing app versions keep working without it.

**Independent Test**: With the updated app, view an assessment in processing and in failed states and confirm the messages; with the current store app, confirm nothing breaks.

**Acceptance Scenarios**:

1. **Given** an assessment is processing, **When** the apprentice opens it in the updated app, **Then** a preparing state is shown and it updates automatically when ready.
2. **Given** an assessment failed, **When** the apprentice or mentor opens it, **Then** a delayed message is shown instead of a report.
3. **Given** a released app version, **When** it receives the new "failed" status, **Then** it continues to work as it does today (no crash).

### Edge Cases

- Assessment with no open-ended answers: no AI needed for scoring; the report is produced from computed facts alone.
- Assessment with no multiple-choice questions: Health Score uses open-ended maturity only, as the existing formula defines.
- AI succeeds for the report but the Premium generation fails: the free report is complete. Premium is retried separately and doesn't block or fail the free report.
- A mentor relationship changes between submission and scoring: Premium eligibility is evaluated when scoring runs.
- Assessments already stuck in "processing" or marked "done" with an empty fallback from before this feature: they can be found and re-queued.
- The queue itself is unavailable at submission: the submission still succeeds and the scoring request is recovered by a periodic sweep, so no submission is lost.
- Retry storms during a long provider outage: retries back off and stop after the retry window; the owner gets one alert per failure type, not one per assessment.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Submitting an assessment MUST create a scoring request that survives server restarts and is processed even if the instance that accepted the submission stops.
- **FR-002**: Failed scoring attempts MUST be retried automatically with increasing delays, for at least 1 hour, before the assessment is marked failed.
- **FR-003**: The system MUST NOT run two scoring attempts for the same assessment at the same time, and MUST NOT overwrite a completed report with a later duplicate attempt.
- **FR-004**: An assessment MUST NOT be marked done unless its report contains real AI-interpreted content for its open-ended answers (or the assessment has none). Default category scores and the empty fallback report MUST NOT be presented as a completed report.
- **FR-005**: When retries are exhausted, the assessment MUST be marked failed with a short reason, and the failure MUST raise the existing scoring-failure alert.
- **FR-006**: The owner MUST be able to re-queue failed or stuck assessments, individually or all within a time range, and a periodic sweep MUST re-queue assessments stuck in processing longer than the retry window plus a margin.
- **FR-007**: Multiple-choice correctness, Biblical Knowledge percentage, per-topic results and the Health Score MUST be computed exactly by the system, never by the AI.
- **FR-008**: Normal scoring of a Master assessment MUST complete within 45 seconds in at least 90% of attempts.
- **FR-009**: AI responses MUST be requested in a strict structured format. Responses that don't match MUST be retried and MUST NOT surface to users as errors.
- **FR-010**: AI prompts MUST include the computed facts available at that point and instruct the AI not to state other numbers.
  - The free-report prompt gets Biblical Knowledge %, per-category and per-topic results, and the previous assessment's Health Score (if any). It must not state a current Health Score, because the system computes that afterwards from the AI's maturity levels.
  - The Premium-report prompt also gets the final Health Score and band.
  - Statements about change over time MUST only appear when a previous assessment exists.
- **FR-011**: The free and Premium reports for one assessment MUST show identical Health Score, band and Biblical Knowledge %.
- **FR-012**: When the apprentice or an active mentor is premium at scoring time, the Premium report MUST be generated as part of scoring and stored for instant retrieval. Its failure MUST NOT fail or delay the free report.
- **FR-013**: On-demand Premium generation MUST remain available as a fallback and MUST generate at most once per assessment even with concurrent requests. Waiting callers receive the result or a "being prepared" response, not a server error.
- **FR-014**: The mentor's report notification email MUST be sent once, after the report is actually complete, not when scoring fails.
- **FR-015**: Assessment status MUST expose `processing`, `done` and the new `failed`, with an optional reason. Existing fields and their meanings MUST stay unchanged for released app versions.
- **FR-016**: An updated app MUST show a preparing state for `processing` and a delayed message for `failed`, and refresh automatically when the status becomes `done`.

### Key Entities

- **Assessment scoring state**: per assessment — status (`processing` / `done` / `failed`), failure reason, attempt count, timestamps (queued, started, completed), and whether the Premium report exists.
- **Scoring request**: a durable request to score one assessment, with retry schedule and attempt history; at most one active per assessment.
- **Computed facts**: Health Score, band, Biblical Knowledge %, per-topic results, previous Health Score. Calculated by the system, then given to the AI and shown in every report.
- **Premium report**: stored per assessment, generated once, with a generating/ready marker to prevent duplicates.

### Access, Compatibility & Clients *(mandatory)*

- **Roles**: Apprentices submit and read their own assessments. Mentors read their actively linked apprentices' assessments. Re-queue and sweep are restricted to the owner/admin or the scheduler (secret). The internal scoring endpoint is callable only by the queue's authenticated identity.
- **Ownership**: Unchanged. Mentor access requires an active link; premium gating is unchanged (403 when not premium).
- **Premium**: The Premium report stays premium-gated; pre-generation happens only when the apprentice or an active mentor is premium.
- **Compatibility**: Additive. The status field gains the value `failed` and an optional `reason`; existing fields are unchanged. Released apps treat a non-`processing` status with scores as done, so they'll show the baseline scores for a failed assessment, as today, without crashing. No endpoint is removed or renamed.
- **Frontend**: Matching app spec to be created in `trooth_assessment` for User Story 5, linking this spec's contract.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% of Master assessment reports are ready within 45 seconds of submission (down from 2–3 minutes).
- **SC-002**: Zero assessments presented as complete with default or empty AI content. Measured as 0 "done" assessments containing the fallback report, over 30 days.
- **SC-003**: Zero assessments stuck in processing for more than 2 hours. Every one completes or is marked failed with a reason.
- **SC-004**: Simulated restarts and temporary AI outages of up to 30 minutes during scoring produce complete reports with no user action, in 100% of test runs.
- **SC-005**: Zero server errors shown to users when opening a Premium report, over 30 days.
- **SC-006**: In a review of 20 generated reports, 100% of numbers stated in the narrative match the computed facts, and first assessments contain no change-over-time claims.
- **SC-007**: AI cost per scored assessment does not increase (target: decrease) compared to today.

## Assumptions

- The Health Score formula (60% multiple choice, 40% open-ended maturity) and question templates are unchanged; consistency work builds on the canonical scores shipped in the report-consistency fix (#25).
- The existing monitoring from feature 003 provides the alerting (scoring-fallback and AI-failure alerts). This feature makes "failed" visible to it rather than adding a new alert channel.
- "Owner" re-queue tools can be an admin- or scheduler-secret-protected endpoint plus a script; no admin UI is required.
- The primary AI provider supports a strict structured-output mode; the fallback provider is used only when the primary fails.
- Only the Master assessment uses the AI pipeline today; other assessment types (spiritual gifts, generic templates) keep their current scoring, but should not regress.
- The legacy synchronous route `POST /assessments/master-trooth/submit`, which the app doesn't call, is out of scope and left as is. Its scorer (`score_assessment_by_category`, via `ai_scoring_master`) stays in place while anything references it.
- Email redesign, question/template changes and the Health Score formula are out of scope.
