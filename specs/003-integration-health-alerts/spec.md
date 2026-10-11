# Feature Specification: Integration Health Checks and Alerts

**Feature Branch**: `feature/integration-health-alerts` | **Spec Folder**: `specs/003-integration-health-alerts/`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "Integration health checks and alerts for the T[root]H backend (dev and prod). Why: on 2026-10-10 AI scoring on dev silently failed for about a day (the primary LLM provider returned "model not found" and the fallback provider was out of credits); assessments were marked done with empty reports and nobody was told. There is no monitoring today. What: (1) a protected health check that exercises each external integration — database, primary AI provider, fallback AI provider, transactional email, Firebase (auth and push), RevenueCat, Shopify — cheaply, in parallel, with timeouts, reporting per-integration up/down and latency and logging a machine-readable line per failure; (2) runs every 15 minutes in each environment; (3) email alerts to admin@onlyblv.com when an integration is down, when the API or onlyblv.com stops responding, when real traffic hits AI or email failures, or when server errors spike, re-notifying while it persists and closing on recovery, naming the environment and integration; (4) lock down the public detailed-health and LLM test-generation endpoints and remove the known default for the scheduler secret in production; (5) monitoring setup reproducible from a script in the repo. Out of scope: changing the AI pipeline, a public status page, paging/SMS."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Know when an integration is down (Priority: P1)

The owner gets an email within about half an hour of any integration the app depends on breaking — the database, either AI provider, email delivery, Firebase, RevenueCat or Shopify — in dev or prod. The email says which environment, which integration, and the error, so they can act before users notice.

**Why this priority**: This is the failure that just happened: AI scoring was broken for a day and nobody knew. Detecting a broken integration is the core value.

**Independent Test**: Break one integration on dev (for example, point the AI provider at a model name that doesn't exist), wait one check cycle, and confirm an alert email arrives naming dev and that integration; restore it and confirm the alert closes.

**Acceptance Scenarios**:

1. **Given** all integrations are working, **When** the scheduled check runs, **Then** every integration reports up with a latency and no alert is sent.
2. **Given** the fallback AI provider has no remaining credit, **When** the scheduled check runs, **Then** it reports that provider down with the provider's error and an alert email names the environment and "fallback AI provider".
3. **Given** an alert is open for an integration, **When** the integration recovers and the next check passes, **Then** the alert closes automatically and a recovery email is sent.
4. **Given** an integration stays down, **When** 30 minutes pass, **Then** the owner is re-notified until it recovers.

---

### User Story 2 - Know when the service or website stops responding (Priority: P1)

The owner is alerted when the dev or prod API stops answering, or the onlyblv.com website goes down, even if nothing inside the app is running to report it.

**Why this priority**: If the API itself is down, the internal check can't run or report; an outside check is the only signal.

**Independent Test**: Point an uptime check at a URL that returns errors (or briefly use a bad path in a test configuration) and confirm an alert email arrives and then closes when it's restored.

**Acceptance Scenarios**:

1. **Given** the prod API stops responding, **When** checks from outside fail for 5 minutes, **Then** an alert email names prod and the API.
2. **Given** onlyblv.com is unreachable, **When** checks fail for 5 minutes, **Then** an alert email names the website.

---

### User Story 3 - Know when real users hit failures (Priority: P2)

Between scheduled checks, the owner is alerted when real activity fails: AI report generation errors, emails failing to send, scoring falling back to empty reports, or a spike in server errors.

**Why this priority**: Some failures only show under real use (malformed AI responses, quota exhaustion mid-day, a bad deploy). This catches them within minutes instead of waiting for the next scheduled check or a user complaint.

**Independent Test**: Trigger a known failure on dev (for example, an AI call that fails) and confirm an alert email arrives describing the failure type and environment.

**Acceptance Scenarios**:

1. **Given** AI generation fails for real requests, **When** failures occur within a 10-minute window, **Then** an alert email describes "AI generation failures" and the environment.
2. **Given** a report falls back to the empty "safe" result, **When** it happens, **Then** an alert is raised.
3. **Given** the server error rate rises above normal, **When** it stays elevated for 5 minutes, **Then** an alert email is sent.

---

### User Story 4 - Diagnostic endpoints are not public (Priority: P2)

Endpoints that reveal internal details or spend money are only usable by the scheduler or the owner, so nobody on the internet can run up AI costs or read server internals.

**Why this priority**: Today anyone can call the LLM test endpoint (each call costs money) and read detailed health and server metrics. It's a cost and information-exposure risk with a simple fix.

**Independent Test**: Call each diagnostic endpoint without the secret and confirm it's refused; call it with the secret and confirm it works. The basic health check used by the app still works without a secret.

**Acceptance Scenarios**:

1. **Given** no secret, **When** someone calls the detailed health, LLM health/test-generation, metrics, or integrations check, **Then** the request is refused.
2. **Given** the correct secret, **When** the scheduler calls the integrations check, **Then** it runs and returns results.
3. **Given** the basic health check, **When** the app or an uptime monitor calls it without a secret, **Then** it still answers.
4. **Given** production has no scheduler secret configured, **When** the service starts or a protected endpoint is called, **Then** protected endpoints refuse all requests rather than accepting a known default.

---

### User Story 5 - Monitoring can be recreated from the repo (Priority: P3)

The owner (or a future helper) can set up or restore all monitoring for an environment by running one script from the repository, instead of clicking through the cloud console.

**Why this priority**: Makes monitoring reviewable and recoverable, and keeps dev and prod identical, but the alerts work without it once created.

**Independent Test**: Run the script against dev; confirm the alert channel, scheduled check, uptime checks, error metrics and alert policies exist; run it again and confirm nothing is duplicated.

**Acceptance Scenarios**:

1. **Given** an environment with no monitoring, **When** the script runs, **Then** all checks, metrics, alert policies and the email channel are created.
2. **Given** monitoring already exists, **When** the script runs again, **Then** it updates in place and creates no duplicates.

### Edge Cases

- One integration hangs: the check must time it out and still report every other integration, finishing well within the scheduler's limit.
- An integration is not configured in an environment (for example, Shopify on dev): report it as "not configured" rather than down, and don't alert on it.
- A check passes intermittently (flapping): alerts must not fire on a single blip; require the failure to persist for the alert's window.
- The checks themselves must not create user-visible side effects: no emails or push notifications actually delivered, no purchases, no records changed.
- The AI checks cost money: each scheduled run must use the smallest possible request so monthly cost stays negligible.
- The alert email channel itself fails (for example, the address bounces): out of scope to detect; documented as an assumption.
- Both dev and prod alert to the same inbox: every alert must clearly name the environment.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an integrations health check that tests each of: database, primary AI provider, fallback AI provider, transactional email provider, Firebase authentication, Firebase push messaging, RevenueCat, and Shopify.
- **FR-002**: Each integration test MUST make a real but minimal call that proves the integration works with the current credentials (not just that it is configured), with no user-visible side effect.
- **FR-003**: Integration tests MUST run concurrently, each with its own timeout (default 10 seconds), and the whole check MUST return within 30 seconds even if an integration hangs.
- **FR-004**: The check MUST return, per integration, a status of `up`, `down`, or `not_configured`, the latency, and for failures a short error description with secrets removed; plus an overall status.
- **FR-005**: For each `down` integration, the system MUST write one machine-readable log line containing the environment, integration name, and error, suitable for alerting.
- **FR-006**: The integrations check MUST run automatically every 15 minutes in dev and in prod.
- **FR-007**: The system MUST send an email alert to admin@onlyblv.com when any integration is reported `down` by a scheduled check.
- **FR-008**: The system MUST send an email alert when the dev or prod API, or onlyblv.com, fails external availability checks for 5 consecutive minutes.
- **FR-009**: The system MUST send an email alert when real traffic produces AI generation failures, email send failures, or scoring fallbacks to an empty report, within 10 minutes of the failures occurring.
- **FR-010**: The system MUST send an email alert when the server error rate stays above a defined threshold for 5 minutes.
- **FR-011**: Every alert MUST name the environment and the affected integration or signal, MUST re-notify every 30 minutes while open, and MUST close automatically with a notification once the condition clears.
- **FR-012**: The detailed health, LLM health/test-generation, server metrics, and integrations endpoints MUST require the scheduler secret; requests without it MUST be refused.
- **FR-013**: The basic health endpoint used by the app and uptime monitors MUST remain public and unchanged.
- **FR-014**: In production, if the scheduler secret is not configured, protected endpoints (including the existing scheduled-job endpoints) MUST refuse all requests; no built-in default secret may be accepted outside development and test.
- **FR-015**: All monitoring resources (alert channel, scheduled checks, uptime checks, log-based metrics, alert policies) MUST be creatable for an environment by running a script in the repository, and re-running it MUST NOT create duplicates.

### Key Entities

- **Integration check result**: one integration's name, status (`up` / `down` / `not_configured`), latency, error summary, and when it was checked.
- **Health report**: the environment, overall status, check time, and the list of integration check results.
- **Alert**: a condition (integration down, service unavailable, traffic failures, error spike), the environment, open/closed state, and notification history.

### Access, Compatibility & Clients *(mandatory)*

- **Roles**: The integrations check and the detailed health, LLM health and metrics endpoints are callable only with the scheduler secret (cron). The basic health endpoint stays public.
- **Ownership**: No user data involved; results contain no personal data or secrets.
- **Premium**: Not applicable.
- **Compatibility**: Additive for the app. The detailed health, LLM health and metrics endpoints change from public to secret-protected; no released app version, the website, or any script calls them (the app only calls the basic health endpoint), so no minimum app version is affected.
- **Frontend**: None.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When any monitored integration breaks, the owner receives an email naming the environment and integration within 30 minutes, 100% of the time in testing.
- **SC-002**: When the API or website stops responding, the owner receives an email within 10 minutes.
- **SC-003**: A repeat of the 2026-10-10 incident (primary AI provider unavailable, fallback out of credit) produces an alert at the next scheduled check instead of going unnoticed.
- **SC-004**: No diagnostic or cost-incurring endpoint can be used without the secret; verified by calling each without it.
- **SC-005**: Monitoring adds less than $5 per month in combined AI-check and monitoring cost across both environments.
- **SC-006**: Healthy systems produce zero alerts over a 7-day period (no false alarms from single blips).
- **SC-007**: Monitoring for an environment can be recreated from scratch in under 10 minutes by running one script.

## Assumptions

- Alerts go to admin@onlyblv.com for both environments; dev alerts are clearly labeled and can be filtered if they become noisy.
- Delivery of the alert email itself (sent by the cloud provider's monitoring service) is trusted; detecting a broken alert inbox is out of scope.
- Dev has the same integrations as prod; any not configured in an environment are reported `not_configured` and do not alert.
- "Minimal call" means: a tiny AI request, a read-only account or permission lookup for email, RevenueCat and Shopify, a token exchange plus a validate-only (not delivered) push message for Firebase, and a trivial query for the database.
- Uptime and error-spike alerting use the cloud provider's built-in monitoring; the scheduled check reuses the existing scheduler secret header used by current scheduled jobs.
- The fallback AI provider being out of credit today is a known issue that this feature will surface; fixing the credit or provider choice is a separate decision.
- The AI pipeline changes (durable queue, honest failure status) are a separate feature; this feature only alerts on today's failure signals.
