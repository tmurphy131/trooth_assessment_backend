# AI Scoring: Architecture, Flow, and Improvements

This document describes how assessment scoring works today for both the Master T[root]H Discipleship and generic assessments, and proposes concrete improvements to address report quality issues (e.g., low-quality or mismatched feedback for Mini Trooth / smaller assessments).

## At-a-glance

- Primary scorer: Category-based AI scoring using OpenAI (model: gpt-4o-mini)
- Fallback scorer: Deterministic mock based on answer length if no API key
- Master wrapper: Adds version tag and “Top 3” categories over the category-based result
- Generic scorer: Numerical averaging per rubric (no AI calls)
- Transport/storage: Scores are stored on `Assessment.scores` as JSON and surfaced via routes

---

## End-to-end flow (apprentice submit → mentor notification)

1) Apprentice completes assessment and submits (backend creates an `Assessment`):
- In draft route, a background worker `_process_assessment_background(assessment_id)` is kicked off after submission. Source: `app/routes/assessment_draft.py`.

2) Background worker prepares scoring inputs:
- Loads the `Assessment` by `assessment_id` and its `answers` (dict[str(question_id) → str(answer)]).
- Builds `questions: List[dict]` from `AssessmentTemplateQuestion` → `Question` including:
  - `id`: str
  - `text`: str
  - `category`: str (resolved from `Category.name`, default: "General Assessment")
  - `question_type`: str (e.g., `multiple_choice` if available)
  - `options`: for MC questions: `[ { text, is_correct } ]` if available
- If the template is missing, falls back to synthesizing questions from answer keys.

3) Category-based scoring:
- Calls `score_assessment_by_category(answers, questions)` (in `app/services/ai_scoring.py`).
- If `OPENAI_API_KEY` is missing or invalid → uses `generate_mock_detailed_scores()` fallback.
- Else, groups `answers` by `question.category` and does one OpenAI call per category via `score_category_with_feedback(...)`.

4) Persist and notify:
- Saves returned `scores` JSON to `Assessment.scores`, sets `Assessment.status = "done"`, commits.
- Sends mentor email with overall and category scores, plus a summary recommendation. (Legacy email format expects simple details; feedback text is not yet deeply formatted for email.)

5) Consumption:
- Frontend polls `/assessments/{id}/status` for `status` and `overall_score`.
- Full details available via `/assessments/{id}`.
- Master reports (PDF/HTML) can be produced via `app/services/master_trooth_report.py` (optional PDF).

---

## What the AI sees (per category)

Function: `score_category_with_feedback(client, category, qa_pairs)`

- Input shape:
  - `category`: string
  - `qa_pairs`: `[ { question, answer, question_id, question_type?, options? } ]`
    - For MC, options (with `is_correct`) are included to enable correctness checking.

- Prompt highlights:
  - “Score this category once from 1-10 based on the set of answers as a whole.”
  - “Treat multiple-choice questions as FACT: mark correct/incorrect using provided options.”
  - “Treat open-ended as OPINION/EXPERIENCE: don’t mark correct/incorrect; give brief qualitative feedback.”
  - Output must be JSON ONLY with keys:
    - `score: int(1-10)`
    - `recommendation: str`
    - `question_feedback: [ { question, answer, correct (bool|null), explanation } ]`

- API call:
  - Model: `gpt-4o-mini`
  - `response_format={"type":"json_object"}` to encourage pure JSON
  - `temperature=0.3` (first implementation) with retries and lenient JSON parsing

- Parsing and return:
  - Returns `(score: int, recommendation: str, question_feedback: list)`
  - Adds `question_id` to feedback items by index (assumes same order as input)

- Aggregation into final result (per assessment):
  - `overall_score`: integer average of category scores (current integer division)
  - `category_scores`: map of category name → int score
  - `recommendations`: per-category recommendation text
  - `question_feedback`: concatenated list from all categories
  - `summary_recommendation`: “strongest vs weakest” style summary

---

## Master assessment wrapper

Function: `app/services/ai_scoring_master.py::score_master_assessment(answers, questions)`

- Calls `score_assessment_by_category` and enriches the result with:
  - `version: "master_v1"`
  - `top3`: top three categories by score
  - Normalized `overall_score` and integer `category_scores`

This is the path used by Master T[root]H reports.

---

## Generic assessment scorer (no AI)

Function: `app/services/ai_scoring_generic.py::score_generic_assessment(answers, rubric)`

- If a rubric is provided (with categories, question_ids, and optional weights):
  - Computes per-category averages and an overall (average or weighted sum)
- If no rubric: averages all numeric answers into a single “General” category
- Returns:
  - `{ overall_score: float, categories: [ { name, score } ], scoring_version: "generic_v1", model: "none" }`

This powers non-AI numeric/rubric-based assessments.

---

## Data contracts (inputs/outputs)

- Input `answers` (all flows): `{ question_id: string → answer: string }`
  - For MC, the answer is typically the selected option text (string)
- Input `questions` (AI flows):
  ```json
  {
    "id": "<str>",
    "text": "<str>",
    "category": "<str> | default 'General Assessment'",
    "question_type": "<str?> (e.g., 'multiple_choice')",
    "options": [ { "text": "<str>", "is_correct": <bool> } ]
  }
  ```
- Output (AI category-based):
  ```json
  {
    "overall_score": <int>,
    "category_scores": { "<CategoryName>": <int> },
    "recommendations": { "<CategoryName>": "<str>" },
    "question_feedback": [
      {
        "question": "<str>",
        "answer": "<str>",
        "correct": true | false | null,
        "explanation": "<str>",
        "question_id": "<str>"
      }, ...
    ],
    "summary_recommendation": "<str>"
  }
  ```
- Output (Master wrapper adds):
  ```json
  {
    "version": "master_v1",
    "top3": [ { "category": "<str>", "score": <int> }, ... ]
  }
  ```
- Output (Generic scorer): see section above.

---

## Known issues and gaps

1) Feedback alignment by index
- Today, we append `question_id` to each returned `question_feedback` item by matching list positions to the input `qa_pairs`. This assumes the model returns the same order and the same count, which may not always hold.
- Impact: Feedback could be attached to the wrong question if the model reorders, merges, or omits items.

2) Overall score integer division
- `overall_score` currently uses integer division (`//` like behavior) after rounding per-category. This floors results and reduces fidelity.

3) Mixed prompt variants and dead code
- `score_category_with_feedback` contains a second, unreachable prompt block (legacy) within the same function, which is confusing and easy to regress. Cleanup recommended.

4) MC correctness depends on option text matching
- The model is told the list of options with `is_correct` and sees the user’s free-form answer text. If the app sends the selected option’s text, that usually works. If anything else (e.g., indices or partial text) is sent, correctness may be misjudged.

5) Default category fallbacks
- When a question has no category, we use a default like “Spiritual Assessment” or “General Assessment,” which can pool unrelated questions and dilute relevance.

6) Error handling and resiliency
- While retries and lenient JSON parsing exist, hard failures still surface as category-level defaults. There’s a commented-out `@cache_result` that could help rate-limits if re-enabled with safe keys.

7) Email/report formatting depth
- The mentor email path currently maps category scores but doesn’t leverage `question_feedback` details. The PDF/HTML master report is minimal; more structured summaries could improve clarity.

---

## Recommendations (prioritized)

Short-term (1–2 days):
- Stabilize feedback mapping
  - Include `question_id` explicitly in the prompt and REQUIRE the model to echo `question_id` in each `question_feedback` item. Avoid index-based alignment.
- Clean up scorer code
  - Remove the unreachable legacy prompt block inside `score_category_with_feedback` and keep a single prompt implementation.
- Improve overall score calculation
  - Compute `overall_score = round(mean(category_scores))` to avoid flooring. Keep integer for display, but preserve a float internally if needed.
- Tighten JSON schema
  - Continue using `response_format={"type":"json_object"}` and provide a JSON “schema-like” example with explicit types. Optionally, add a pre-parse validator to coerce types reliably.

Medium-term (3–7 days):
- Function-calling / JSON schema enforcement
  - If available, migrate to function/tool calling or stricter JSON schema to harden structure (key presence, types). This eliminates lenient parsing quirks.
- MC correctness fidelity
  - For MC questions, pass both the options list and the selected option’s index/id alongside the text; instruct the model to compare by index/id, not free-text.
- Category calibration
  - Standardize categories for each template and ensure questions are accurately tagged. Consider per-template category weights.
- Better recommendations
  - Synthesize a more actionable cross-category summary (e.g., top strengths, two targeted next steps, one scripture-based encouragement) to increase usefulness.
- Observability
  - Add structured logs with `assessment_id`, `category`, token usage, and timing per call. Consider adding a throttled “debug dump” endpoint for admins in non-prod.

Long-term (1–2 sprints):
- Test harness and fixtures
  - Add golden tests with fixed prompts and mock responses. Validate mapping from inputs → `question_feedback` (esp. `question_id`), and stability of `overall_score` rollup.
- Caching & idempotency
  - Re-enable the cache decorator with keys derived from `(template_id, normalized_answers, scorer_version)` to avoid repeat calls during retries or re-submissions.
- Versioned scorer pipeline
  - Introduce `scoring_version` tags for the AI path (e.g., `cat_ai_v2`), and store alongside outputs to simplify migrations and A/B.

---

## Quick reference: Key functions

- `app/services/ai_scoring.py`
  - `score_assessment_by_category(answers, questions) -> dict`
  - `score_category_with_feedback(client, category, qa_pairs) -> (score, recommendation, question_feedback)`
  - `generate_mock_detailed_scores(answers, questions) -> dict`
  - `generate_summary_recommendation(category_scores, recommendations) -> str`
  - `score_assessment(answers) -> dict` (legacy adapter)
  - `score_assessment_with_questions(answers, questions) -> (overall_score, summary)`
- `app/services/ai_scoring_master.py`
  - `score_master_assessment(answers, questions) -> dict` (adds `version`, `top3`)
- `app/services/ai_scoring_generic.py`
  - `score_generic_assessment(answers, rubric) -> dict` (no AI)
- `app/services/master_trooth_report.py`
  - `generate_pdf(apprentice_name, scores) -> bytes`
  - `generate_html(apprentice_name, scores) -> str`

---

## Acceptance criteria for improvements

- Feedback mapping is reliable: each `question_feedback` item contains the correct `question_id` echoed by the model.
- Overall score matches rounded average, not floored.
- No unreachable/dead code in `score_category_with_feedback`.
- MC correctness uses option indices/ids when available and matches user selections.
- Structured tests cover master and generic flows; mock path validated when `OPENAI_API_KEY` is absent.

---

## Appendix: Edge cases to consider

- Empty answers or missing questions → deterministic benign default
- Mixed templates with missing category tags → explicit default category per template to avoid cross-contamination
- Large answer sets or long free-text responses → token budgeting in prompts (truncate contextually if needed)
- Rate limits / transient errors → retries, backoff, cache, and graceful degradation per category

---

If you'd like, I can implement the short-term fixes (feedback `question_id` echo, overall score rounding, dead code cleanup) in a small PR with targeted tests.