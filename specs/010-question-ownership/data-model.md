# Data Model: Question Ownership

## Question (`questions`): change
| Field | Type | Rule |
|---|---|---|
| `created_by` *(new)* | `String`, FK → `users.id`, `ON DELETE SET NULL`, nullable, indexed | The mentor who created it. NULL = shared/admin/seed/unattributed |

Backfill (migration `20261014_question_owner`, idempotent, only where `created_by IS NULL`): set it to `t.created_by` when every `assessment_template_questions` link for the question points to a template with the same non-null `created_by`, none of those templates has `is_master_assessment = true`, and `users.role = 'mentor'` for that owner.

## Policy (`app/services/question_access.py`)
| Function | Returns |
|---|---|
| `can_see_answers(user, question)` | `True` if admin or `question.created_by == user.id` |
| `manage_block_reason(db, user, question)` | `None` if allowed. `"not_owner"` if a mentor isn't the creator (or it's a shared question). `"used_elsewhere"` if any linking template's `created_by != user.id` |
| `hide_answers(question_out, as_false)` | a copy with every option's `is_correct` set to `False` (compat) or `None` |

Admins always pass. Apprentices never manage questions (role gate) and never see answers, unless they somehow created a question, which they can't.

## Unchanged
`AssessmentTemplate.created_by`, `AssessmentTemplateQuestion` links, and clone behavior (link the same questions).
