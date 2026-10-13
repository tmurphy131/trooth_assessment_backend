# Feature Specification: Invite Codes

**Feature Branch**: `feature/invite-codes` | **Spec Folder**: `specs/006-invite-codes/`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "Let apprentices accept a mentor's invitation with a short code instead of relying on their account email matching the invited email. The app is moving to social-first sign-in (Sign in with Apple on iOS, Google on both platforms, email as a fallback). Apple's 'Hide My Email' gives accounts a relay address that never matches the email a mentor invited, so apprentices can't find their invite today."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Apprentice joins a mentor with a code (Priority: P1)

A mentor invites an apprentice. The apprentice signs in to the app any way they like, including Apple with a hidden email or a different Google account from the one the mentor used. They enter the invite code and are paired with that mentor.

**Why this priority**: This is the problem the feature exists to solve. Without it, apprentices whose account email differs from the invited email can't be paired with their mentor.

**Independent Test**: Create an invite for `invitee@example.com`. Sign in as an apprentice whose account email is different. Redeem the code and confirm both the mentor and the apprentice now see each other as paired.

**Acceptance Scenarios**:

1. **Given** a pending, unexpired invite with code `K7QM-3XPR`, **When** a signed-in apprentice with any email redeems `K7QM-3XPR`, **Then** they are paired with the inviting mentor and the invite is marked accepted.
2. **Given** the same invite, **When** the apprentice enters `k7qm3xpr` or ` K7QM-3XPR ` (lowercase, no dash, extra spaces), **Then** it is accepted exactly as if typed in canonical form.
3. **Given** an invite that has already been accepted, **When** anyone redeems its code, **Then** the request fails with a clear "already used" error and no pairing changes.
4. **Given** an expired invite, **When** its code is redeemed, **Then** the request fails with a clear "expired" error.
5. **Given** a code that doesn't exist (mistyped or revoked), **When** it is redeemed, **Then** the request fails with a "not found" error that doesn't reveal whether the code ever existed.
6. **Given** the apprentice previously had an inactive relationship with this mentor, **When** they redeem a new code from that mentor, **Then** the relationship is reactivated rather than duplicated.

---

### User Story 2 - Mentor gets a code they can share anywhere (Priority: P1)

When a mentor sends an invite, they immediately get the code back and can see it again on their pending-invites list. They can share it by text or any other channel, not only email. The invitation email and its landing page show the code too.

**Why this priority**: Apprentices can only redeem a code they receive. Both stories are needed for the MVP.

**Independent Test**: Send an invite as a mentor. Confirm the response and the pending-invites list both include the code, and the invitation email and landing page show the same code.

**Acceptance Scenarios**:

1. **Given** a mentor, **When** they create an invite, **Then** the response includes a human-readable code.
2. **Given** a mentor with pending invites, **When** they list pending invites, **Then** each invite includes its code.
3. **Given** an invite was created, **When** the apprentice opens the invitation email or its landing page, **Then** they see the code and an instruction to enter it in the app.
4. **Given** invites created before this feature shipped, **When** they are listed or the landing page is opened, **Then** they also have a code.

---

### User Story 3 - Invite acceptance can't be done on someone else's behalf (Priority: P2)

Today the existing accept-by-token call doesn't require sign-in and trusts the apprentice ID in the request body. Anyone holding a token could attach any apprentice to that mentor. Acceptance by token or by code must happen only as the signed-in apprentice.

**Why this priority**: It's a security fix (Principle I). Released apps already send a sign-in token with this call, so the fix doesn't need an app update.

**Independent Test**: Call accept-by-token without signing in (rejected), and signed in as apprentice A with apprentice B's ID in the body (rejected). Then call it as A with A's own ID or no ID (accepted).

**Acceptance Scenarios**:

1. **Given** a valid invite token, **When** accept is called without sign-in, **Then** it fails with 401.
2. **Given** a signed-in apprentice A, **When** accept is called with another user's ID in the body, **Then** it fails with 403 and nothing changes.
3. **Given** a signed-in apprentice A, **When** accept is called with A's own ID (what released apps send), **Then** it succeeds as before.

---

### Edge Cases

- **Mentor redeems their own code, or a non-apprentice account redeems a code:** rejected. Only users with the apprentice role can redeem.
- **Someone guesses codes:** attempts are rate-limited per user (see FR-008). The code space is large enough that guessing is impractical.
- **Two apprentices redeem the same code at the same moment:** exactly one succeeds; the other gets "already used".
- **Mentor revokes an invite and the apprentice then enters its code:** "not found".
- **Mentor invites the same email twice:** the existing "already pending" rule still applies. Each invite has its own code.
- **Code generation collides with an existing code:** a new code is generated. Codes are unique across all invites.
- **Apprentice is already actively paired with this mentor:** redeeming succeeds and does nothing else. The invite is marked accepted and no duplicate pairing is created.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every invite MUST have a code that is unique across all invites. The code is 8 characters long. It uses only uppercase letters and digits, excluding characters that look alike (0, O, 1, I, L).
- **FR-002**: Codes MUST be displayed in the form `XXXX-XXXX`. When matching a code, the system MUST ignore case, dashes and any whitespace (internal or surrounding).
- **FR-003**: Codes MUST be generated with a cryptographically secure random source.
- **FR-004**: Creating an invite MUST return the code. Listing a mentor's pending invites MUST include each invite's code.
- **FR-005**: Invites that exist before this feature ships MUST be given a code.
- **FR-006**: A signed-in apprentice MUST be able to redeem a code. The apprentice is always the signed-in user and is never taken from the request.
- **FR-007**: Redeeming MUST follow the same rules as accepting by token: it must not be expired, must not already be accepted, reactivates an existing relationship, and never ends other mentor relationships. Errors MUST be distinct: not found is 404; expired and already used are both 400 and are told apart by their `detail` text ("This invitation has expired." vs "Invitation has already been accepted"). The app may match on those exact strings.
- **FR-008**: Code redemption MUST be rate-limited to at most 10 failed attempts per user per hour. Further attempts get a 429 until the window passes.
- **FR-009**: The invitation email and the invitation landing page MUST show the code and say to enter it in the app. The landing page MUST stop showing the raw token.
- **FR-010**: Accepting by token MUST require sign-in. It MUST reject a request whose body names a different apprentice than the signed-in user. The body's apprentice ID stays accepted but becomes optional.
- **FR-011**: Existing invite routes, fields and status codes MUST keep working for released app versions. Changes are additive, except that FR-010 adds sign-in to a route the app already calls while signed in.
- **FR-012**: Every successful or failed redemption MUST be logged without the full code. Logs MAY include the invite ID and user ID.

### Key Entities

- **Apprentice Invitation** (existing): gains a code. The existing token, invited email, apprentice name, expiry (7 days) and accepted flag are unchanged. The invited email is still used for the email delivery and for the existing email-matched invite list, but no longer limits who can accept.
- **Mentor–Apprentice relationship** (existing): created or reactivated on redemption, as with token acceptance today.
- **Invite code attempt** (new): one record per redemption attempt. It holds who tried, which invite matched (if any), whether it succeeded, and when. It enforces the FR-008 limit and is the audit trail for FR-012. It's deleted with the user's account.

### Access, Compatibility & Clients *(mandatory)*

- **Roles**: Mentors create invites and see their codes. Signed-in apprentices redeem codes. Accept-by-token now requires a signed-in apprentice. The public invitation landing page is still public and shows only that invite's details and code.
- **Ownership**: A mentor sees only codes for their own invites. Redeeming pairs only the signed-in apprentice.
- **Premium**: Free. This doesn't change any limits on how many apprentices a mentor can have or invite.
- **Compatibility**: Additive (new field, new endpoint). The one behavior change is that accept-by-token now requires sign-in. Released apps already send the sign-in token and the caller's own ID, so no minimum app version is needed.
- **Frontend**: A matching frontend spec in `trooth_assessment` (invite-code entry for apprentices, code display and sharing for mentors, social-first login), linking this spec's contract.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An apprentice whose account email differs from the invited email can be paired with their mentor without help from support.
- **SC-002**: An apprentice can enter a code and be paired in under 30 seconds after signing in.
- **SC-003**: Everyone who tries to pair (the code is valid and unused) succeeds on the first attempt, whatever the case, dashes or spacing.
- **SC-004**: An invite can't be accepted by anyone who isn't signed in, or on behalf of a different user.
- **SC-005**: Invites from before release and released app versions keep working with no errors.

## Assumptions

- Anyone holding a code may redeem it. The code is not tied to the invited email. Mentors choose whom to share it with, and the code is single-use and expires in 7 days.
- Invite expiry stays at 7 days. Revoking still deletes the invite.
- The existing email-matched list of an apprentice's invites stays as a convenience for apprentices whose emails match.
- Agreements and gift seats also match apprentices by email. They have the same hidden-email problem but are out of scope here, and will get a follow-up spec.
- Sign-in method changes (Apple/Google first, email as fallback) are frontend-only and live in the frontend spec.
- The existing rate-limit infrastructure (`RateLimitMiddleware`) or a per-user equivalent can enforce FR-008. The choice belongs in the plan.
