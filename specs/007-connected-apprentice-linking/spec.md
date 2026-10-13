# Feature Specification: Link Agreements and Gift Seats to Apprentice Accounts

**Feature Branch**: `feature/connected-apprentice-linking` | **Spec Folder**: `specs/007-connected-apprentice-linking/`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "Agreements and gift seats still find the apprentice by email, so they break for apprentices who sign in with Apple's Hide My Email or a different Google account, the same problem spec 006 fixed for invitations. Fix both together."

**Follow-up to**: spec 006 (invite codes), whose assumptions named agreements and gift seats as the next step.

## Background (current behavior)

- **Agreements.**
  - A mentor creates an agreement by typing the apprentice's email, and `apprentice_id` stays empty even if the mentor is already connected to that apprentice.
  - Apprentices see their agreements by matching the agreement email against their account email.
  - Signing in the app is refused (403) unless the account email equals the agreement email.
  - Signing through the emailed link fills in the apprentice by looking up that email. If no account has it, the agreement never connects the apprentice to the mentor.
  - So an apprentice whose account email differs (an Apple relay address, another Google account) can't see, sign or be connected by an agreement in the app.
- **Gift seats.** These are mostly account-based already:
  - Mentors pick a connected apprentice (sent by ID), and the backend checks the connection.
  - Every seat has a redemption code, which apprentices redeem with `POST /apprentice/redeem-code`.

  Remaining gaps:
  - The connection check accepts an *ended* mentorship.
  - Any role, including mentors, can redeem a gift code.
  - The redeem log line includes the user's email.
  - The app has no screen where an apprentice enters a gift code. That's frontend work, covered by the matching frontend spec.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mentor sends an agreement to a connected apprentice (Priority: P1)

A mentor already connected to an apprentice (by invite code or any other way) creates an agreement by picking that apprentice, not by typing an email. The agreement belongs to the apprentice's account from the start. The apprentice sees it in the app, signs it there, and every agreement action works, whatever email their account uses.

**Why this priority**: This is the common path. Most agreements go to apprentices the mentor has already connected with, and today every one sent to a hidden-email apprentice is unusable in the app.

**Independent Test**: Connect mentor M and apprentice A, where A's account email differs from any email M knows. M creates an agreement by choosing A. A lists their agreements and sees it. A signs it in the app and gets 200. Status moves on as it does today.

**Acceptance Scenarios**:

1. **Given** M has an active connection with A, **When** M creates an agreement with A's account ID, **Then** the agreement is tied to A's account, and its email is A's account email (so notification emails reach A, including through an Apple relay).
2. **Given** that agreement, **When** A lists their agreements, opens it, or lists pending agreements, **Then** it appears and opens normally.
3. **Given** that agreement awaiting A's signature, **When** A signs it in the app, **Then** it is accepted even though A's account email never matched an address M typed.
4. **Given** M has **no active** connection with apprentice B, **When** M creates an agreement naming B's account ID, **Then** it is refused (403) and nothing is created.
5. **Given** a mentor creates an agreement by email only (today's path), **Then** behavior is unchanged.
6. **Given** an agreement tied to A's account, **When** A asks for a parent-link resend or a meeting reschedule, or tries to end the mentorship while it's pending, **Then** each works or blocks as it does today for email-matched agreements.

---

### User Story 2 - Agreement sent by email attaches once the apprentice joins (Priority: P2)

A mentor sends an agreement by email to someone who isn't connected yet, usually together with an invitation to the same address. That person signs up with a hidden or different email and joins with the invite code. The agreement now attaches to their account, so they see and can sign it in the app. If they already signed it through the emailed link, it's linked to them.

**Why this priority**: This covers the "invite and agreement sent together" flow for new apprentices. It's less common than Story 1, and the emailed signing link already works without an account.

**Independent Test**: M invites `jordan@example.com` and creates an agreement for `jordan@example.com`. Jordan signs up with a relay address and redeems the invite code. Jordan's agreement list now contains that agreement, tied to Jordan's account.

**Acceptance Scenarios**:

1. **Given** mentor M has agreements for email E that aren't tied to any account, **When** an apprentice accepts M's invitation addressed to E (by code or token), **Then** those agreements become tied to that apprentice's account.
2. **Given** such an agreement was already signed through the emailed link before the apprentice existed, **When** it attaches, **Then** it shows as signed, and the mentorship is active through the invite acceptance.
3. **Given** agreements for email E from a **different** mentor, **When** the apprentice accepts M's invite, **Then** those other agreements are **not** attached.
4. **Given** an agreement already tied to some account, **When** any invite is accepted, **Then** it is never re-tied to another account.

---

### User Story 3 - Gift seats only go to current apprentices, and only apprentices redeem codes (Priority: P3)

Gifting by picking a connected apprentice works only while that mentorship is active. Gift codes can be redeemed only by apprentice accounts. Redeem logs no longer contain email addresses. The app-side gift-code entry screen comes from the frontend spec.

**Why this priority**: Small hardening. Existing gifts already work through account IDs and codes.

**Independent Test**: A mentor whose mentorship with B has ended tries to gift B by ID and is refused. A mentor account tries to redeem a gift code and is refused. Neither leaves a gift attached to the wrong account.

**Acceptance Scenarios**:

1. **Given** a mentor whose connection with B has ended (inactive), **When** they gift a seat to B by ID (create, purchase or assign), **Then** B is treated as not connected, the same as today for never-connected apprentices.
2. **Given** a mentor or admin account, **When** it redeems a gift code, **Then** it is refused (403) and the seat stays unredeemed.
3. **Given** any gift-code redemption, **Then** the logs record user and seat IDs only, never an email.

---

### Edge Cases

- **Both an account ID and an email are sent when creating an agreement:** the account ID wins, and the agreement email comes from that account.
- **The connected apprentice later ends the mentorship:** existing agreements stay tied to their account. Ending is still blocked while one is pending, as today.
- **The apprentice changes their account email after an agreement was created by ID:** the agreement keeps the email it was created with, so notification emails go there (Apple relay addresses keep forwarding). Access, signing and listing don't change, because they match the account ID first.
- **The apprentice deletes their account:** account deletion already removes agreements by account ID *or* email. Nothing changes.
- **An invite is accepted but the agreement email differs only in letter case or surrounding spaces:** emails are compared trimmed and lowercased, as stored.
- **An unlinked agreement for E exists from mentor M, but the apprentice joined M by an invite addressed to a different email:** it isn't attached. Story 1 (pick the connected apprentice) is the path for that case.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Creating an agreement MUST accept an optional apprentice account ID. When it's given, the mentor MUST have an **active** connection with that apprentice, or the request fails with 403. The agreement is then tied to that account, and its email (and name, if none was given) comes from the account.
- **FR-002**: When an apprentice account ID is given, the email in the request MUST become optional. With no ID, the email stays required (today's behavior).
- **FR-003**: In-app signing by the apprentice MUST be allowed when the agreement is tied to the signer's account, **or** when the signer's email matches the agreement email (today's rule). Signing by anyone else stays refused (403).
- **FR-004**: When an apprentice accepts a mentor's invitation (by code or by token), every agreement from **that mentor** with the **same email as the invitation** that isn't tied to an account yet MUST become tied to the accepting apprentice. Already-tied agreements MUST NOT change.
- **FR-005**: Every place that finds an apprentice's agreements MUST keep matching by account ID **or** email: listing, viewing, pending list, resend and reschedule requests, the ending-mentorship check, and account deletion. Account ID comes first; email stays as a fallback for agreements not tied to an account yet.
- **FR-006**: Gifting a seat by apprentice account ID (create, purchase, assign) MUST require an **active** connection between the mentor and that apprentice.
- **FR-007**: Redeeming a gift code MUST be limited to apprentice accounts (403 for other roles).
- **FR-008**: Gift-code redemption logs MUST NOT include email addresses. User and seat IDs are enough.
- **FR-009**: Every change MUST be additive for released app versions. Requests and responses that work today keep working.

### Key Entities

- **Agreement** (existing): already has an optional apprentice account ID, which this feature fills in at creation (Story 1) or when the apprentice joins (Story 2). No new fields.
- **Apprentice invitation** (existing, spec 006): its email links invitations and agreements in Story 2.
- **Mentor premium seat** (existing): no data changes.

### Access, Compatibility & Clients *(mandatory)*

- **Roles**: Mentors create agreements and gift seats, and may only target apprentices they have an active connection with when using an account ID. Apprentices sign their own agreements and redeem gift codes.
- **Ownership**: An apprentice sees and signs only agreements tied to their account or addressed to their email. A mentor targets only actively connected apprentices by ID.
- **Premium**: Unchanged. Gift seats are already gated by the mentor's subscription.
- **Compatibility**: Additive: a new optional field on agreement creation, and wider (never narrower) matching for apprentices. The stricter checks (an active connection to gift by ID; only apprentices redeem gift codes) only refuse requests that shouldn't have worked. No minimum app version is needed.
- **Frontend**: The matching frontend spec in `trooth_assessment`:
  - the mentor's agreement screen picks from connected apprentices (sending the account ID), with email entry kept for apprentices who aren't connected yet;
  - an apprentice screen to enter a gift code;
  - it links this spec's contract.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An apprentice whose account email differs from anything the mentor typed can see, open and sign, in the app, every agreement their mentor sends after connecting.
- **SC-002**: An apprentice who joins through an invite code sees, in the app, the agreements that mentor sent to the invited address, with no support help.
- **SC-003**: No agreement or gift seat can be tied to an apprentice the mentor isn't actively connected with, when an account ID is used.
- **SC-004**: Released app versions keep working with no errors (agreement creation by email, signing, gift codes).

## Assumptions

- Apple's private relay addresses forward email, so storing the account's (relay) email on an agreement still delivers notification emails.
- Attaching agreements on invite acceptance (FR-004) is limited to the same mentor and the same invited email. That's precise enough not to attach the wrong person's agreement.
- Gift-code guessing isn't rate-limited here. Codes have about 8.5 × 10¹¹ possibilities (`TROOTH-XXXX-XXXX`), and that's unchanged by this feature. A rate limit can follow the spec 006 pattern later if needed.
- The test-only signing shortcut in `apprentice_sign` (active only when `ENV=test`) is out of scope.
