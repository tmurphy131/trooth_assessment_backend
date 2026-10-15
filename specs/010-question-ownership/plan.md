# Implementation Plan: Question Ownership

**Branch**: `feature/question-ownership` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/010-question-ownership/spec.md`

## Summary

- **Ownership:** add `questions.created_by` (a nullable foreign key to `users.id`) in migration `20261014_question_owner`, with a one-time backfill (FR-003).
- **One policy module** decides everything, `app/services/question_access.py`:
  - `can_see_answers(user, question)`: admin or creator.
  - `manage_block_reason(db, user, question)`: `None` if allowed, otherwise `"not_owner"` or `"used_elsewhere"`.
  - `answers_flag(...)`: hidden answers become `None` (omitted) or `False` (compat), depending on the endpoint.
- **Routes:**
  - `POST /question/questions` records the mentor as creator; admin-created questions get none.
  - `PUT` and `DELETE` go back to mentor-or-admin, checked by the policy: 403 if not the owner, 409 if used elsewhere. This replaces the stopgap.
  - `GET /question/questions[/{id}]` shows answers per question.
  - `GET /admin/templates/{id}` shows answers per question (`False` when hidden, for compat), replacing the template-owner rule.
  - `POST /admin/templates/{id}/questions` lets mentors attach only questions they created.
  - Clone is unchanged: it links the same questions.
- **Drafts:** `include_answers=True` only in `get_submitted_by_apprentice` (a linked mentor reviewing). Never for the caller's own drafts, whatever their role.
- **Account deletion:** clears `questions.created_by`.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (existing). No new packages.

**Storage**: PostgreSQL.
- **New column:** `questions.created_by VARCHAR NULL REFERENCES users(id) ON DELETE SET NULL`, indexed.
- **Migration:** `alembic/versions/20261014_question_owner.py`, with `down_revision = '20261013_invite_codes'` and a `downgrade()` that drops the column.
- **Backfill** (one SQL statement, Postgres): set `created_by` to the template owner for questions whose linking templates all have the same non-null `created_by`, where none is `is_master_assessment` and that owner's role is `mentor`.

**Testing**: pytest (SQLite fixtures; the suite takes about 15 s since #52). New `tests/test_question_ownership.py` covers every acceptance scenario. The backfill SQL is tested against Postgres in `tests/test_question_ownership_postgres.py` (skipped without `TEST_POSTGRES_URL`).

**Target Platform**: Cloud Run (dev → prod). The migration job runs before the deploy.

**Project Type**: web-service (client: Flutter app; no app change, frontend #36 already treats a missing flag as false)

**Performance Goals**: the policy check per question is one indexed lookup of linking templates, done only on edit, delete or attach. Answer visibility on reads is in memory.

**Constraints**:
- Released app template screen: `is_correct` must be a bool on `GET /admin/templates/{id}`, so hidden answers are sent as `False`.
- Other endpoints omit hidden answers or send `None`; the app reads those with `?? false` or `== true`.

**Scale/Scope**: 1 new module, 1 migration, about 5 route files touched, 1 account-deletion line, 2 test files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Auth**: ✅ Question management is gated by role plus ownership. Answer visibility is enforced server-side. Mentor review still requires an active link (#52).
- [x] **II. Errors**: ✅ 403 if not the owner, 409 if other templates use the question, each with a clear `detail`.
- [x] **III. Migrations**: ✅ `20261014_question_owner.py` with `downgrade()`, run through the migrate job before the deploy. The backfill is idempotent (it only fills NULLs).
- [x] **IV. Config & secrets**: N/A.
- [x] **V. Logging**: ✅ Refusals are logged with ids only.
- [x] **VI. Compatibility**: ✅ Additive column. No endpoint is removed or renamed. The `is_correct` bool is preserved where released apps need it. Refusals only hit flows the released app doesn't use (it never edits or deletes questions, and only attaches questions it just created).
- [x] **VII. Layering**: ✅ The policy lives in `app/services/question_access.py`.
- [x] **VIII. Tests**: ✅ Success and authorization-failure tests for create, edit, delete, attach, clone, template view, question list and drafts. No live calls.
- [x] **IX. Deploy**: ✅ Dev, then prod, with migrations first.
- [x] **X. Contract**: ✅ [contracts/question-ownership.md](contracts/question-ownership.md). Frontend: none needed.
- [x] **XI. Formatting**: ✅ Only the touched functions change.

**Post-design re-check**: all ✅ / N/A.

## Project Structure

### Documentation (this feature)

```text
specs/010-question-ownership/
├── plan.md  research.md  data-model.md  quickstart.md
├── contracts/question-ownership.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
alembic/versions/20261014_question_owner.py   # column + FK + index + backfill
app/models/question.py                         # created_by column
app/services/question_access.py                # can_see_answers, manage_block_reason, answers flag helpers
app/routes/question.py                         # create records creator; edit/delete by policy; per-question answers
app/routes/admin_template.py                   # per-question answers on GET; attach only own questions
app/routes/assessment_draft.py                 # include_answers only for linked-mentor review
app/schemas/question.py                        # QuestionOut gains optional created_by (additive)
app/services/account_deletion.py               # clear questions.created_by
tests/test_question_ownership.py
tests/test_question_ownership_postgres.py
```

**Structure Decision**: a single policy module, so every endpoint answers "may this user see or change this question?" the same way. That prevents the drift that caused the template-owner leak.

## Complexity Tracking

No constitution violations.
