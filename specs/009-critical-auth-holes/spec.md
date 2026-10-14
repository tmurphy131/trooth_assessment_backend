# Feature Specification: Close Critical Authorization Holes

**Feature Branch**: `fix/critical-auth-holes` | **Spec Folder**: `specs/009-critical-auth-holes/`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "Close three critical authorization holes live in prod (docs/audit-2026-10-13.md findings 1–3). (1) Signup lets any signed-in user change their own role, including to admin, by re-posting signup, and matches existing accounts by request-body email then overwrites the account id (possible account takeover). Identity must come from the verified sign-in, role and id of an existing account must never change, and nobody may make themselves admin. (2) The parent/guardian signature can be submitted with no login and no token by anyone knowing the agreement id. Parents must only sign through the emailed one-time link. (3) A route creates a mentor–apprentice link with no auth, granting a mentor access to any apprentice's data. Remove it; links are created only through invitations, invite codes and agreements. Must not break released app versions."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nobody can change their own role or take over another account (Priority: P1)

A person signs in and completes registration as a mentor or an apprentice. From then on, their role is fixed: re-sending registration, by mistake or on purpose, cannot change it. In particular, nobody can make themselves an administrator. Registration also only ever acts on the signed-in person's own account. It cannot attach the caller to someone else's account by naming that person's email.

**Why this priority**: Today any signed-in user can become an administrator and reach every admin capability, and an account can possibly be taken over by email. This is the most severe hole.

**Independent Test**: As a signed-in apprentice, re-send registration asking for the administrator role and then the mentor role. As a different signed-in person, send registration naming the first person's email. Confirm no role, account or ownership changes in any case.

**Acceptance Scenarios**:

1. **Given** a new person who has signed in but not registered, **When** they register as a mentor or apprentice, **Then** their account is created with that role, their own sign-in identity and their own verified email.
2. **Given** a registered apprentice, **When** they re-send registration asking for the mentor or administrator role, **Then** their role stays apprentice and they get the same result as a normal repeat registration.
3. **Given** a person with no account yet, **When** they register asking for the administrator role, **Then** the request is refused and no account is created. (For an existing account the requested role is ignored, as in scenario 2, so nobody becomes an administrator either way.)
4. **Given** a registered person A, **When** a different signed-in person B sends registration naming A's email, **Then** A's account is unchanged and B gets no access to it. B's request acts only on B's own account: the email in the request is ignored, and B's account (new or existing) uses B's own sign-in email.
5. **Given** a registered person, **When** they re-send registration with a changed display name, **Then** the name may update (as today) but nothing else about the account changes.
6. **Given** an existing account that was created before the person's current sign-in identity existed (legacy re-link), **When** that person signs in with a verified email matching the account, **Then** the account is re-linked to them as today. **When** the email is not verified, **Then** no re-link happens.

---

### User Story 2 - Only a real parent or guardian can give consent for a minor (Priority: P1)

When a minor is invited into a mentorship, the agreement needs a parent or guardian's signature before it activates. That signature can only be given through the one-time link emailed to the parent. Neither the mentor, nor the apprentice, nor anyone else who knows the agreement can submit a parent signature another way.

**Why this priority**: Today anyone who knows an agreement's identifier, including the mentor who created it, can "sign" as the parent and activate the mentorship without guardian consent. This is a child-safety and legal-consent issue.

**Independent Test**: For an agreement awaiting a parent signature, try to submit a parent signature without the emailed link (signed out, as the mentor, and as the apprentice). Confirm it is refused and the agreement stays unsigned. Then sign through the emailed link and confirm the agreement activates.

**Acceptance Scenarios**:

1. **Given** an agreement awaiting a parent signature, **When** anyone submits a parent signature without the emailed one-time link, **Then** it is refused, the agreement stays awaiting the parent, and the mentorship is not activated.
2. **Given** the same agreement, **When** the parent signs through the emailed link, **Then** the agreement becomes fully signed and the mentorship activates, exactly as today.
3. **Given** a used or expired parent link, **When** it is used again, **Then** it is refused, as today.

---

### User Story 3 - Mentor–apprentice links are only created through approved flows (Priority: P1)

A mentor only gains access to an apprentice's data after a real connection: an accepted invitation, an invite code, or a signed agreement. There is no way for anyone, signed in or not, to directly link a mentor to an apprentice.

**Why this priority**: Every mentor permission relies on that link. Today anyone can create one without signing in, which gives a mentor full access to any apprentice's assessments, reports and notes.

**Independent Test**: Try to directly link a mentor to an apprentice (signed out and signed in as a mentor). Confirm it is refused and no link exists. Then connect through an invite code and confirm access works.

**Acceptance Scenarios**:

1. **Given** any caller, **When** they try to directly link a mentor and an apprentice, **Then** the request is refused and no link is created.
2. **Given** a mentor and an apprentice, **When** they connect through an invitation, an invite code or a signed agreement, **Then** the link is created and access works, exactly as today.

---

### Edge Cases

- A person who registered with one role, abandoned setup, and comes back to choose a different role: the first role stands (consistent with the app's rule that a role is chosen once). Changing it is an admin/support action.
- A legacy account whose stored role was wrong from older code: it is no longer fixed by re-registering. Support corrects it. The number of affected accounts is expected to be zero or near zero.
- Repeat registration from the app after a network retry: it returns the existing account normally, with no error, so released apps keep working.
- Registration naming an email different from the signed-in person's verified email: the account is created or matched using the signed-in identity's email, not the one in the request.
- A signed-in identity with no email (unusual provider setups): registration is refused with a clear message rather than creating a nameless account.
- A legacy account whose owner now signs in with a new identity and an **unverified** email: registration and sign-in are refused with the generic "verify your email" message, and nothing is re-linked. They verify their email, or support re-links them. Released apps treat this refusal like "account already exists", so the person may land on "complete registration" until they verify.
- Old app versions, or anyone still sending the removed parent-sign or direct-link requests: they get a clear refusal. The app never calls these, so no user sees it.

## Requirements *(mandatory)*

### Functional Requirements

**Registration and identity**

- **FR-001**: Registration MUST identify the account only by the signed-in person's verified identity. Any account identifier or email in the request MUST NOT select, create or modify a different account.
- **FR-002**: The email stored for a newly registered account MUST be the signed-in identity's email.
- **FR-003**: Registration MUST NOT change the role of an existing account.
- **FR-004**: Registration MUST NOT change the identifier of an existing account.
- **FR-005**: No one MUST be able to become an administrator through registration. A new account requesting the administrator role MUST be refused. For an existing account the requested role is ignored (FR-003). Administrator accounts are granted only by an operator outside the app.
- **FR-006**: A repeat registration for an existing account MUST succeed and return that account, so released apps that retry or re-register keep working. Only the display name may update.
- **FR-007**: Re-linking an existing account to a new sign-in identity by email (legacy re-link, at registration or at any signed-in request) MUST only happen when the signed-in identity's email is verified, and MUST only use that verified email.

**Parent/guardian consent**

- **FR-008**: A parent or guardian signature MUST only be accepted through the emailed one-time parent link.
- **FR-009**: The way to submit a parent signature by agreement identifier, without the one-time link, MUST be removed. Any such request MUST be refused with no change to the agreement.

**Mentor–apprentice links**

- **FR-010**: The way to directly link a mentor and an apprentice MUST be removed. Any such request MUST be refused with no link created.
- **FR-011**: Links MUST continue to be created by invitations, invite codes and signed agreements, unchanged.

**Safety and verification**

- **FR-012**: Each fix MUST have tests: the success path still works, and the abuse cases in the acceptance scenarios are refused.
- **FR-013**: Refusals MUST NOT reveal whether another person's account or agreement exists. In particular, the refusal for an unverified email MUST use a generic message that doesn't confirm an account exists for that email.

### Key Entities

- **Account**: a registered person with a sign-in identity, an email, a display name and a role (apprentice, mentor or administrator). Role and identity are fixed after registration.
- **Agreement**: a mentorship agreement that may need an apprentice signature and, for minors, a parent signature given through a one-time emailed link.
- **Mentor–apprentice link**: the relationship that grants a mentor access to an apprentice's data. It is created only by invitations, invite codes or signed agreements.

### Access, Compatibility & Clients *(mandatory)*

- **Roles**:
  - Registration: any signed-in person, acting only on their own account.
  - Parent signature: only the holder of the emailed one-time link.
  - Direct linking: nobody (removed).
- **Ownership**: a person can only create or read their own account through registration. Mentors only see apprentices they are actively linked to (unchanged).
- **Premium**: no change.
- **Compatibility**: two routes are removed: parent signature by agreement identifier, and direct mentor–apprentice linking. No released app version uses either. The frontend has unused, already-broken client functions for both, so no minimum app version is needed. Registration keeps its request and response shape. Repeat registration still succeeds.
- **Frontend**: no spec needed. Optional cleanup: remove the unused `parentSignAgreement` and `assignApprentice` client functions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 ways remain for a person to raise their own role or become an administrator through the app or its public interface.
- **SC-002**: 0 ways remain to submit a parent signature without the emailed one-time link.
- **SC-003**: 0 ways remain to create a mentor–apprentice link outside invitations, invite codes and signed agreements.
- **SC-004**: 100% of new registrations and repeat registrations from released app versions keep succeeding (no new errors in sign-up or sign-in after release).
- **SC-005**: Every abuse case in the acceptance scenarios is covered by an automated test that fails if the hole reopens.
- **SC-006**: After release, a review finds no unexpected administrators, and every repeat registration that may have changed an existing account's role within the available request-log history is listed for follow-up. (Older role changes can't be detected: role history isn't stored.)

## Assumptions

- Administrators are created by an operator directly (for example a one-off database or console change), never through the app. No in-app "become admin" flow is needed.
- Sign-in providers keep one account per email, so a verified email reliably identifies one person.
- The app's role-selection and sign-up screens only ever request mentor or apprentice.
- Legacy accounts with a wrong stored role are rare. Support handles them instead of re-registration.
- The two removed routes have no callers in released app versions (verified in the frontend source: the client functions exist but are never invoked, and the direct-link call uses the wrong parameter format).
- A follow-up audit query for unexpected administrators and recent role changes is part of rollout, not of the code change.
