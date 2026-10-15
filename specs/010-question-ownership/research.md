# Research: Question Ownership

## R1. Where ownership lives
- **Decision**: A nullable `created_by` on `questions`. NULL means shared/admin.
- **Rationale**: Answer visibility and edit rights belong to the question, not the template. Questions are shared across templates (clones link the same rows), so template ownership can't decide them.
- **Alternatives**:
  - Copy questions on clone, so the mentor owns the copies. That would hand the mentor the answer key through their own copies, and break the link to central fixes.
  - A separate ownership table. Unnecessary for a single creator.

## R2. Edit rules when a question is shared
- **Decision**: A mentor may edit or delete only if they're the creator **and** every linking template has `created_by == mentor`. Otherwise 403 (not the owner) or 409 (used elsewhere). Admins are unrestricted.
- **Rationale**: FR-004. It never changes another owner's assessment.
- **Alternatives**: Copy-on-write (fork the question for the editing template). More complex, and no current workflow needs it (spec assumption).

## R3. Backfill
- **Decision**: One idempotent `UPDATE … FROM (subquery)` in the migration. Attribute a question to the single non-null template owner when all of its links point to templates by that owner, none is the Master, and the owner's role is mentor. Unlinked questions stay NULL.
- **Rationale**: FR-003, "where unambiguous". Clones of the Master share Master questions, so those are excluded by the Master check.
- **Alternatives**: Attribute by earliest link. That's ambiguous and could wrongly hand shared answers to a mentor.

## R4. Answers in responses
- **Decision**: One helper decides visibility. Per endpoint:
  - `GET /question/questions[/{id}]`: hidden answers are omitted (`response_model_exclude_none`), as #52 already does.
  - `GET /admin/templates/{id}`: hidden answers are `False`. The released template screen reads it as a non-null bool.
  - Drafts: `None` (the app reads `?? false`).
- **Rationale**: FR-010, FR-012.

## R5. Drafts
- **Decision**: `include_answers=True` only in `get_submitted_by_apprentice`, which is already scoped to an actively linked mentor or admin. All other draft routes return the caller's own drafts, so they never include answers, whatever the role.
- **Rationale**: FR-008(c) and FR-009. Mentors taking assessments themselves no longer get answers. The #52 rule was "mentor or admin".

## R6. Attach
- **Decision**: `POST /admin/templates/{id}/questions`: mentors may attach only questions with `created_by == mentor`. Admins may attach any. Clone keeps linking all source questions; it's already restricted to the Master or the mentor's own templates.
- **Rationale**: FR-006 and FR-007. The released app attaches only questions it just created, so they're owned.

## R7. Account deletion
- **Decision**: The foreign key uses `ON DELETE SET NULL`, and `account_deletion.py` also explicitly nulls `questions.created_by` alongside `assessment_templates.created_by`, for SQLite and order safety.
- **Rationale**: The edge case "creator removed" leaves the question admin-only and keeps templates working.
