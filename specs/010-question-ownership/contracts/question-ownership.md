# Contract: Question Ownership

No endpoint is added, removed or renamed. Changes are in who may act, and in answer visibility.

| Endpoint | Who | Change |
|---|---|---|
| `POST /question/questions` | mentor, admin | Records `created_by`: the mentor, or none for admins. The response gains optional `created_by` (additive). Generates the required unique `question_code` (`QC…`). Before this, creation failed on Postgres (FR-014) |
| `PUT /question/questions/{id}` | mentor (own, see below), admin | Replaces the admin-only stopgap. **403** `"You can only edit questions you created."` **409** `"This question is used by other assessments, so it can't be changed."` |
| `DELETE /question/questions/{id}` | same as PUT | Same 403/409, with "deleted" wording |
| `GET /question/questions`, `GET /question/questions/{id}` | any signed-in user | `is_correct` is included only for questions the caller may see (admin or creator). Otherwise the key is omitted |
| `GET /admin/templates/{id}` | mentor (own or Master), admin | `is_correct` is **real** for questions the caller may see, and **`false`** otherwise. A bool, as the released template screen requires |
| `POST /admin/templates/{id}/questions` | mentor (own template), admin | Mentors may attach only questions they created. Otherwise **403** `"You can only add questions you created."` |
| `POST /admin/templates/{id}/clone` | unchanged | Links the same questions. Answers stay governed by the question rules above |
| Draft routes (`/assessment-drafts/...`) | unchanged access | `is_correct` is `null` on the caller's own drafts, for **every** role. Real only in `GET /assessment-drafts/submitted-assessments/{apprentice_id}` (a linked mentor or admin reviewing) |

"Own" for PUT and DELETE means `created_by == caller` **and** every template using the question has `created_by == caller`.

**Released apps**: the app never calls PUT or DELETE on questions, attaches only questions it just created (owned), and reads `is_correct` with `?? false` or `== true` (frontend #36). The template screen gets a bool. No minimum version is needed.
