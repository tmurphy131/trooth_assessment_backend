# Feature Specification: Question Ownership

**Feature Branch**: `feature/question-ownership` | **Spec Folder**: `specs/010-question-ownership/`

**Created**: 2026-10-14

**Status**: Draft

**Input**: User description: "Give assessment questions an owner, so custom questions belong to the mentor who wrote them and shared/system questions (Master assessment, spiritual gifts, admin-authored) are managed only by admins. A question records its creator. Mentors edit and delete only their own questions. A shared question is never changed in a way that alters someone else's assessment. Correct answers are visible only to admins, the question's creator, and a mentor reviewing a linked apprentice's submitted answers. Nobody sees correct answers while taking an assessment. Cloning keeps working without revealing answers to questions the mentor didn't write. Mentors keep full use of their own custom questions. Existing custom questions are attributed to their mentor where it's unambiguous. Must not break released apps."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mentors fully manage their own custom questions (Priority: P1)

A premium mentor builds a custom assessment. They write their own questions, mark the correct answers, attach them to their template, and come back later to edit or remove them. Everything works as it does today, and the mentor always sees the correct answers they wrote.

**Why this priority**: Custom assessments are a premium feature. Since a temporary safeguard, mentors can no longer edit questions at all. Restoring that for their own questions is the core user value.

**Independent Test**: As a mentor, create a question with a correct answer, attach it to your own template, view the template (the correct answer shows), edit the question, then delete it.

**Acceptance Scenarios**:

1. **Given** a mentor, **When** they create a question, **Then** they are recorded as its creator.
2. **Given** a question the mentor created that is used only in their own templates, **When** they edit or delete it, **Then** the change succeeds.
3. **Given** a mentor viewing their own template, **When** it shows questions they wrote, **Then** the correct answers are shown.
4. **Given** a question the mentor created, **When** they attach it to their own template, **Then** it is attached.

---

### User Story 2 - Shared questions stay protected and their answers stay private (Priority: P1)

Shared questions, such as those behind the Master assessment and the spiritual gifts assessment, are managed only by administrators. A mentor can't change them, can't attach them to a template one by one, and never sees their correct answers. That holds when they view the Master template, when they clone it into their own template, and when they view that clone.

**Why this priority**: The shared assessment is what every apprentice takes. Its integrity, and the privacy of its answers, protects every user's results.

**Independent Test**: As a mentor, view the Master template, clone it, and view the clone. No correct answers appear, edits to shared questions are refused, and attaching a shared question to your own template is refused. An apprentice of that mentor takes the cloned assessment and is still scored correctly.

**Acceptance Scenarios**:

1. **Given** a shared question (no creator), **When** a mentor tries to edit or delete it, **Then** it is refused and nothing changes.
2. **Given** a mentor viewing any template, **When** it includes questions they didn't write, **Then** those questions' correct answers are not revealed.
3. **Given** a mentor, **When** they clone a template they're allowed to clone, **Then** the clone has the same questions and answer choices, their apprentices are scored exactly as on the original, and viewing the clone doesn't reveal correct answers to questions the mentor didn't write.
4. **Given** a mentor, **When** they try to attach a question they didn't write to their template, **Then** it is refused.
5. **Given** an administrator, **When** they view, edit or attach any question, **Then** they can, as today.

---

### User Story 3 - Nobody sees correct answers while taking an assessment (Priority: P1)

Anyone taking an assessment (an apprentice, or a mentor taking one themselves) sees the questions and choices but never which choice is correct. A mentor reviewing a linked apprentice's submitted answers still sees which answers were correct, as part of guiding them.

**Why this priority**: An assessment where the taker can see the answers is meaningless, and its scores feed every report.

**Independent Test**: As a mentor, start an assessment for yourself: no correct answers are included. As a linked mentor, review your apprentice's submitted assessment: correct answers are shown.

**Acceptance Scenarios**:

1. **Given** anyone starting, resuming or viewing their own in-progress assessment, **When** questions are shown, **Then** no correct answers are included.
2. **Given** a mentor actively linked to an apprentice, **When** they review that apprentice's submitted or in-progress answers, **Then** correct answers are shown.
3. **Given** a mentor not linked to an apprentice, **When** they try to view that apprentice's answers, **Then** access is refused, as today.

---

### User Story 4 - Editing never changes someone else's assessment (Priority: P2)

If a question a mentor wrote is also used in a template that isn't theirs, the mentor can't edit or delete it. That would silently change another person's assessment. They're told why.

**Why this priority**: It's rare, but it protects other mentors and their apprentices' results.

**Independent Test**: A mentor-created question is attached to a template owned by someone else. Editing or deleting it as its creator is refused with a clear reason. An admin can still change it.

**Acceptance Scenarios**:

1. **Given** a question the mentor created that is also used in another owner's template, **When** they edit or delete it, **Then** it is refused with a message explaining that other assessments use it.

---

### Edge Cases

- **Questions created before this change:**
  - A question used only in templates created by one mentor (and not in shared templates) is attributed to that mentor.
  - Any other question (shared, unused, or used by several owners) has no creator, so only admins can manage it.
- **Unused question with no creator:** admin-only.
- **Removed creator:** if a creator's account is deleted, their questions become creator-less (admin-only). Templates that use them keep working.
- **Released app versions:** where a released screen expects a yes/no "correct" flag, hidden answers are reported as "not correct" rather than omitted, so the app doesn't fail.
- **Scoring:** always uses the real correct answers on the server, whoever views the template.

## Requirements *(mandatory)*

### Functional Requirements

**Ownership**

- **FR-001**: Each question MUST record its creator. Questions created by admins, seeded system questions, and pre-existing questions that can't be attributed unambiguously have no creator.
- **FR-002**: A question created by a mentor MUST record that mentor as its creator.
- **FR-003**: Existing questions MUST be attributed to a mentor when they are used only in templates created by that one mentor and in no shared (Master or admin-created) template. All others remain creator-less.

**Managing questions**

- **FR-004**: A mentor MUST be able to edit or delete a question only if they are its creator **and** every template using it belongs to them. Admins can edit or delete any question.
- **FR-005**: When an edit or delete is refused because other owners' templates use the question, the response MUST say so clearly.
- **FR-006**: A mentor MUST be able to attach to their own template only questions they created. Admins can attach any question.
- **FR-007**: Cloning a template MUST keep working: the clone uses the same questions, so scoring is identical. It MUST NOT make the mentor the creator of questions they didn't write.

**Answer visibility**

- **FR-008**: Correct answers MUST be shown only to:
  - (a) admins
  - (b) the question's creator
  - (c) a mentor actively linked to the apprentice whose submitted or in-progress answers they are reviewing.
- **FR-009**: Correct answers MUST NOT be included when anyone takes, resumes or views their own assessment, including mentors.
- **FR-010**: Where a released app screen requires a yes/no "correct" flag, hidden answers MUST be reported as "not correct" rather than omitted.
- **FR-011**: Server-side scoring MUST always use the true correct answers.

**Compatibility**

- **FR-012**: Request and response shapes MUST stay compatible with released apps. The only change is in which callers see correct answers, plus clear refusals for disallowed edits and attachments.
- **FR-013**: The temporary admin-only restriction on editing and deleting questions MUST be replaced by these ownership rules.
- **FR-014**: Creating a custom question MUST succeed on the production database. Each new question gets the unique identifier code the database requires. *(Found during implementation: the database requires this code, and the create route never set one, so custom question creation failed on Postgres.)*

### Key Entities

- **Question**: text, type, answer choices (each marked correct or not), and a **creator** (a mentor, or none for shared/admin questions).
- **Template**: a named set of questions with an owner (or shared/Master). A question can be used by several templates.

### Access, Compatibility & Clients *(mandatory)*

- **Roles**:
  - Mentor: creates questions; manages own questions under FR-004; attaches own questions; clones permitted templates.
  - Admin: manages all.
  - Apprentice: takes assessments, never sees answers.
- **Ownership**:
  - Question creator per FR-001–FR-003.
  - Template owner unchanged.
  - Answer visibility per FR-008.
- **Premium**: unchanged. Custom templates remain premium.
- **Compatibility**:
  - Additive data: a creator per question, plus a one-time attribution of existing questions.
  - No endpoint is removed.
  - Hidden answers are reported as "not correct" on screens that need a flag.
  - Edits and attachments that are now disallowed return clear refusals. The released app doesn't edit or delete questions, and only attaches questions it just created, so released apps are unaffected.
- **Frontend**: none required. The app already treats a missing flag as "not correct" (frontend PR #36).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 ways for a non-admin to see correct answers of a question they didn't write, other than reviewing a linked apprentice's answers.
- **SC-002**: 0 ways for a non-admin to change a question that another owner's assessment uses.
- **SC-003**: 100% of mentor custom-question workflows (create, attach, view answers, edit, delete) work for questions the mentor wrote.
- **SC-004**: Apprentices of a cloned template get identical scores to the same answers on the original template.
- **SC-005**: Every acceptance scenario is covered by an automated test.

## Assumptions

- Shared assessments (Master, spiritual gifts, admin templates) are authored by admins or seeds, so their questions have no creator.
- Refusing an edit (FR-004) is preferred over silently copying the question. Copy-on-write isn't needed for current usage.
- Mentors attach their own new questions through template management. Attaching others' questions isn't a real workflow, and cloning covers reuse of the Master assessment.
- A mentor reviewing a linked apprentice's answers seeing which were correct is intended product behavior.
- Account deletion clears or keeps the creator reference without breaking templates. The plan decides how.
