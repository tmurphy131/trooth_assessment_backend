---
description: "Tasks for 010 Question Ownership"
---

# Tasks: Question Ownership

**Input**: `/specs/010-question-ownership/` (spec, plan, research, data-model, contracts, quickstart)

**Tests**: REQUIRED (Principle VIII). Success and authorization-failure tests for every changed endpoint. `pytest` passes at each checkpoint.

## Phase 1: Setup

- [X] T001 Create `tests/test_question_ownership.py` with fixtures:
  - `act_as`: override `get_current_user`.
  - `make_user(role)`.
  - `make_question(creator=None, correct="A")`: a multiple-choice question with options A (correct) and B.
  - `make_template(owner=None, master=False, published=False, questions=[...])`.

## Phase 2: Foundational

- [X] T002 Add `created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)` to `Question` in `app/models/question.py`.
- [X] T003 Create `alembic/versions/20261014_question_owner.py` (`revision='20261014_question_owner'`, `down_revision='20261013_invite_codes'`):
  - Add the column, the foreign key (`ON DELETE SET NULL`) and an index.
  - Backfill per data-model.md with one `UPDATE questions SET created_by = sub.owner FROM (SELECT atq.question_id, MIN(t.created_by) AS owner FROM assessment_template_questions atq JOIN assessment_templates t ON t.id = atq.template_id GROUP BY atq.question_id HAVING COUNT(*) = COUNT(t.created_by) AND COUNT(DISTINCT t.created_by) = 1 AND SUM(CASE WHEN t.is_master_assessment THEN 1 ELSE 0 END) = 0) sub JOIN users u ON u.id = sub.owner AND u.role = 'mentor' WHERE questions.id = sub.question_id AND questions.created_by IS NULL`.
  - Run the backfill only on Postgres (`op.get_bind().dialect.name == 'postgresql'`).
  - `downgrade()` drops the index, the foreign key and the column.
- [X] T004 Create `app/services/question_access.py`:
  - `can_see_answers(user, question) -> bool`: admin, or `question.created_by == user.id`.
  - `manage_block_reason(db, user, question) -> str | None`:
    - admin → `None`
    - `created_by != user.id` → `"not_owner"`
    - any `AssessmentTemplate` linked to the question with `created_by != user.id` (including NULL/Master) → `"used_elsewhere"`
    - otherwise `None`
  - `hide_answers(q: QuestionOut, as_false: bool) -> QuestionOut`.
  - Add a module docstring citing spec 010.
- [X] T005 In `app/schemas/question.py`, add `created_by: Optional[str] = None` to `QuestionOut` (additive).
- [X] T006 [P] Add unit tests for `can_see_answers` and `manage_block_reason` in `tests/test_question_ownership.py`, covering admin, creator-only-own-templates, creator-used-elsewhere, non-creator and shared (NULL).

## Phase 3: US1, mentors manage their own questions (P1) 🎯 MVP

- [X] T007 [US1] `app/routes/question.py`:
  - **Create:** `create_question` takes `user = Depends(require_mentor_or_admin)` and sets `created_by = user.id if user.role == mentor else None`.
  - **Edit/delete:** `update_question` and `delete_question` go back to `require_mentor_or_admin` (remove the stopgap comment). They call `manage_block_reason`:
    - `"not_owner"` → 403 `"You can only edit questions you created."` (delete: "delete")
    - `"used_elsewhere"` → 409 `"This question is used by other assessments, so it can't be changed."`
    - Log refusals with ids only.
  - **Reads:** list/get show answers per question with `can_see_answers` (replace the admin-only `_out`), keeping `response_model_exclude_none`.
- [X] T008 [US1] `app/routes/admin_template.py` `add_question_to_template` (`POST /{template_id}/questions`): after the template ownership checks, if the caller is a mentor and `question.created_by != caller.id` → 403 `"You can only add questions you created."`
- [X] T009 [P] [US1] Tests:
  - A mentor creates a question, `created_by` is set, and the response includes the answers.
  - Attaching it to their own template → 200.
  - The template view shows the real `is_correct`.
  - Edit → 200. Delete → 200.
  - An admin creates a question → `created_by` is None.

## Phase 4: US2, shared questions protected and private (P1)

- [X] T010 [US2] `app/routes/admin_template.py` `get_template`: replace the template-owner rule with per-question `can_see_answers`. Hidden answers become `is_correct=False` (`hide_answers(as_false=True)`). Keep the existing access checks.
- [X] T011 [P] [US2] Tests:
  - A mentor editing or deleting a shared (NULL) question → 403, unchanged.
  - The Master template view shows every option as `False` for a mentor.
  - Clone the Master, then view the clone as its owner → still `False`.
  - A mentor attaching a shared question to their own template → 403.
  - An admin sees real answers and can edit.
  - Scoring of a cloned template (SC-004): the clone links the same question ids with the same `is_correct` in the database, so server-side scoring inputs are identical.
  - The question list for a mentor omits `is_correct` on shared questions and includes it on their own.

## Phase 5: US3, nobody sees answers while taking (P1)

- [X] T012 [US3] `app/routes/assessment_draft.py`:
  - Replace `include_answers=_sees_answers(current_user)` with `include_answers=False` in every route that returns the caller's own drafts.
  - Use `include_answers=True` only in `get_submitted_by_apprentice`.
  - Remove `_sees_answers` if unused.
- [X] T013 [P] [US3] Tests:
  - A mentor starting a draft for themselves → no `is_correct`.
  - An apprentice → none.
  - An actively linked mentor calling `GET /assessment-drafts/submitted-assessments/{apprentice_id}` → real answers.
  - Update `tests/test_access_hardening.py::test_apprentice_draft_has_no_answers` if needed. It keeps passing.

## Phase 6: US4, editing never changes someone else's assessment (P2)

- [X] T014 [P] [US4] Test: a mentor-created question also linked from another mentor's template (or the Master) → creator's edit is 409 and delete is 409. An admin edit → 200.

## Phase 7: Polish

- [X] T015 `app/services/account_deletion.py`: next to the `assessment_templates.created_by` null-out, add `_safe_update(db, Question, Question.created_by == user_id, {"created_by": None}, "questions")`. Add a test that deleting a mentor clears `created_by` on their questions.
- [X] T016 [P] Create `tests/test_question_ownership_postgres.py` (skip without `TEST_POSTGRES_URL`). Seed the cases, run the backfill SQL, and assert:
  - a mentor-only question is attributed
  - a Master-linked question stays NULL
  - a question split across two owners stays NULL
  - a template owned by an admin-role user stays NULL
- [X] T017 Run the full suite. Run `alembic upgrade head` and `downgrade -1` on a throwaway Postgres. Update `tests/test_access_hardening.py` expectations that changed by design: the stopgap test `test_question_edit_and_delete_are_admin_only` becomes "a mentor can't edit a shared question; an admin can".

## Dependencies
T001 → T002–T005 → T006. US1 (T007–T009) needs T004 and T005. US2 (T010–T011) needs T004. US3 (T012–T013) is independent. US4 (T014) needs T007. T007 and T010 touch different files, but both import T004. Polish runs last.

## Implementation Strategy
Ship all four stories together. They're one coherent rule change, and the migration has to land with the code.

## Phase 8: Found during implementation

- [X] T018 `POST /question/questions` generates `question_code` (`QC` + 12 hex characters). It's NOT NULL + unique on Postgres since migration 20250915, but the model said nullable, so SQLite tests never caught that custom question creation failed (FR-014). Added a Postgres integration test that fails on the old route.
