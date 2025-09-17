# Apprentice Progress Page — Requirements

> Scope: Requirements only (no code). This page consolidates assessment outcomes for an apprentice. Focus on two official admin‑managed assessments first (Master T[root]H Assessment & Spiritual Gifts Assessment), then other assessments chronologically.

## 1. Objectives
- Give apprentices a single, clear snapshot of their key formation metrics.
- Highlight the two canonical (admin‑managed) assessments at the top for quick recognition.
- Provide access to historical and other assessment reports below.
- Enable exporting/emailing PDF versions of individual reports (per earlier specs).

## 2. Layout Overview (High Level)
```
[ Page Title: Progress ]

[Row of Featured Cards]
  ├─ Card A: Master T[root]H Assessment (latest overall score)
  └─ Card B: Spiritual Gifts Assessment (Top 3 gifts from latest attempt)

[Section: All Assessment Reports]
  ├─ Report Entry (Newest First)
  ├─ Report Entry
  ├─ ... (pagination / lazy load)
```

## 3. Featured Cards (Hero Row)
### 3.1 Master T[root]H Assessment Card
- Title: "Master T[root]H Assessment"
- Data shown (from latest completed attempt):
  - Overall aggregate score (integer badge) plus top 3 category scores (chips) provided directly by backend.
  - Date of latest completion (small text).
  - If fewer than 3 categories exist (edge), show available categories and note: "Fewer categories assessed".
- Ordering / tie policy:
  - Categories pre-ordered server‑side by (score DESC, category_name ASC) and truncated to three (no tie expansion on the card).
  - Client MUST NOT recompute ordering—treat array as authoritative.
- Actions:
  - Tap → Opens full Master assessment report view.
  - Overflow (optional/future): View history, Retake.
- Empty state: If no submission yet → CTA button: "Take Assessment".
- Cross‑reference: See Section 13 (Verified Decisions) for backend contract & prerequisites.

Source data contract (featured card endpoint expected JSON):
```
{
  "overall_score": 8.2,              // float raw (optional)
  "overall_score_display": 8,        // int for prominent badge
  "top3": [                          // length 1–3; already ranked & truncated
    { "category": "Prayer", "score": 9 },
    { "category": "Scripture", "score": 8 },
    { "category": "Community", "score": 8 }
  ],
  "completed_at": "2025-09-12T14:04:09Z",
  "version": "master_v1"
}
```
Display rules:
- Show `overall_score_display` as primary number.
- Render category chips horizontally (wrap if needed). Ellipsis chip text if > 14 chars.
- Announce via accessibility label: "Master assessment score 8 of 10. Top categories: Prayer 9, Scripture 8, Community 8.".

### 3.2 Spiritual Gifts Assessment Card
- Title: "Spiritual Gifts Assessment"
- Data shown (latest completed attempt):
  - Top 3 gifts (exactly three chips; ties at 3rd place are NOT expanded here even if full report expands them).
  - Each gift: Gift Name + Score badge (0–12).
  - Date of latest completion.
  - If fewer than three gifts (incomplete): show available gifts and note: "Incomplete – retake".
- Tie truncation consistency: Mirrors Master card truncation policy; full Gifts report may show expanded ties.
- Actions:
  - Tap → Opens Spiritual Gifts full report view.
  - Overflow (optional/future): View history, Retake.
- Empty state: If no submission yet → CTA: "Take Spiritual Gifts Assessment".

## 4. All Assessment Reports Section
### 4.1 Purpose
Provide chronological access to every assessment report the apprentice has generated (including the two featured ones and any future/new assessment types).

### 4.2 Ordering & Grouping
- Default ordering: Newest first by completion timestamp.
- Each entry is independent; featured cards simply surface the latest of their respective types.
- Optional future filter tabs: [All] [Master] [Spiritual Gifts] [Other]. (Not required for v1.)

### 4.3 Report Entry Structure
For each report entry:
- Title: Assessment Display Name (e.g., "Master T[root]H Assessment", "Spiritual Gifts Assessment").
- Subtitle/meta line: Completed <relative time> (e.g., "3d ago") + exact date (YYYY-MM-DD).
- Summary snippet (truncated metrics):
  - Master: `Overall <score> • <Cat1>, <Cat2>, <Cat3>` (top3 truncated; no tie expansion). If <3 categories: list available.
  - Spiritual Gifts: `<Gift1>, <Gift2>, <Gift3>` (truncated top 3 only).
  - Other assessments: Implementation-defined summary field or first key metric.
- Optional future phrase (growth trend) withheld until delta support added.
- Icon or badge: Unique per assessment type for quick scanning.
- Action affordances:
  - Tap entire row to open full report detail view.
  - Secondary action icon: "Email PDF" (optional/future). v1: email action only in detail view.

### 4.4 Empty State
If NO assessments at all:
- Show illustration + text: "No assessments yet".
- Provide buttons: "Take Master Assessment" and "Take Spiritual Gifts Assessment".

### 4.5 Pagination / Loading
- If > N (e.g., 10–20) reports, implement lazy load / endless scroll.
- Show skeleton placeholders while loading additional pages.

## 5. Report Detail View (Interaction Requirements)
(Reference existing assessment report specs; key additions for progress context.)
- Contains full structured report (already defined for Master & Spiritual Gifts).
- Action: "Email me this report (PDF)" (see Spiritual Gifts spec for PDF style; Master uses analogous styling).
- Back navigation returns to Progress list preserving scroll position.

## 6. Data Requirements
### 6.1 API / Data Sources
Featured Card Endpoints (fast path):
- `GET /assessments/master/latest` → `{ overall_score, overall_score_display, top3[], completed_at, version }`
- `GET /assessments/spiritual-gifts/latest` → `{ top_gifts_truncated[], completed_at, version }`

Reports List Endpoint (paginated):
- `GET /assessments/reports?limit=20&cursor=...` →
```
{
  "items": [
    {
      "id": "...",
      "assessment_type": "master" | "spiritual_gifts" | "other",
      "display_name": "Master T[root]H Assessment",
      "completed_at": "2025-09-12T14:04:09Z",
      "version": "master_v1",
      "summary": {
        "overall_score": 8,
        "top3": [ {"category": "Prayer", "score": 9}, {"category": "Scripture", "score": 8}, {"category": "Community", "score": 8} ]
      }
    },
    {
      "id": "...",
      "assessment_type": "spiritual_gifts",
      "completed_at": "2025-09-12T13:03:11Z",
      "version": "spiritual_gifts_v1",
      "summary": {
        "top_gifts": [ {"gift": "Wisdom", "score": 11}, {"gift": "Faith", "score": 10}, {"gift": "Teaching", "score": 10} ]
      }
    }
  ],
  "next_cursor": "opaque-token-or-null"
}
```
Pagination: cursor-based; client stops when `next_cursor` null.

Failure / fallback: If a card endpoint returns 404, treat as "not taken" state. If response missing expected key (e.g. `top3`), show error placeholder with retry affordance (do NOT derive locally).

### 6.2 Caching / Performance
- Cache featured card responses independently (stale-while-revalidate window: 300s suggested).
- Background refresh when page regains focus or user pull-to-refresh invoked.
- Target p95 latency: featured endpoints <120ms server time; reports list <200ms for page 1.

### 6.3 Edge Cases
- Partial / in-progress attempt should NOT appear as a completed report.
- If latest attempt incomplete: show CTA to continue (future) or retake; omit summary.
- Deleted / deprecated assessment types remain visible (label with "(Archived)").
- Master card with <3 categories: show available + helper text.
- Gifts card with <3 gifts: show available + helper text.
- Missing `top3` or `top_gifts_truncated` key → treat as transient error (retry button) instead of silently hiding.

## 7. Visual & UX Guidelines
- Cards: Elevated or outlined container with 16px padding. Title bold 16–18px; primary metric 20–24px.
- Category / gift chips: pill shape, accent background (#FFF8E1) with contrasting text (#5A4200); max width 120px, text overflow ellipsis.
- Skeleton states: For each featured card show (1) rectangular title bar placeholder, (2) circular badge placeholder for score, (3) three chip placeholders (or count of available).
- Loading animation: subtle shimmer (<= 1.5s loop).
- Spacing scale: 4 / 8 / 16 / 24.
- Accessibility: Minimum 4.5:1 contrast; each chip has aria-label: "<Category> score <value>".
- Voice order: Announce overall score before categories.
- Error placeholder: bordered box with retry icon + message (do not collapse layout height).

## 8. Permissions / Security
- Apprentice can only retrieve their own scores/reports.
- Mentor tokens MUST be rejected (403) if calling progress page endpoints (they have distinct mentor endpoints).
- No cross-user querying by arbitrary apprentice_id parameter is allowed in progress endpoints.
- API must enforce identity via bearer token (Firebase → backend validation).

## 9. PDF Emailing Constraints
- Email action only available inside detail view (v1) to prevent accidental taps.
- Rate limiting: Max 5 report emails per assessment type per user per hour (shared policy with Gifts spec). Overflow → 429 JSON `{ "error":"RATE_LIMIT", "retry_after_seconds": <int> }`.
- Email subject patterns:
  - Master: "Master Assessment Report — <YYYY-MM-DD>"
  - Spiritual Gifts: "Spiritual Gifts Report — <YYYY-MM-DD>"
- Attachment filenames: `master_report_<yyyyMMdd>.pdf`, `spiritual_gifts_report_<yyyyMMdd>.pdf`
- Future: unify naming with apprentice name when emailing self? (Deferred.)

## 10. Logging & Analytics (Optional/Future)
- Track events: progress_page_view, report_open, email_pdf_request, assessment_card_click.
- Funnel metric: Percentage of apprentices who open at least one report weekly.

## 11. Acceptance Criteria
- Master card shows overall score + exactly 3 (or fewer with note) category chips sourced from backend `top3` (no client reordering).
- Gifts card shows exactly 3 truncated gifts (or fewer w/ note) regardless of tie expansion in full report.
- Reports list entries display truncated top3 / top_gifts consistent with cards.
- Detail view provides working "Email me PDF" action with rate limit enforcement.
- Attempts in progress never appear in list or cards.
- Empty states show correct CTAs when no assessments taken.
- Error in one featured card does not block rendering of the other or the list.
- Accessibility: Screen reader announces card summary (score + categories/gifts) in one continuous phrase.
- Latency: Initial featured card + first page list fetch completes within performance targets (Section 6.2).

## 12. Open Questions
1. Sparkline trend for Master future? (Deferred.)
2. Pin additional assessment types to featured row? (Future.)
3. Filter tabs (All/Master/Gifts/Other) in v1? (Answer: No, confirmed.)
4. Drill-down interaction on category/gift chips (tap to open breakdown)? (Future consideration.)
5. Include apprentice self-reflection notes panel beneath featured cards? (Future.)

---
## 14. Error & Loading States
- States per featured card: loading, loaded, error, empty, partial (<3 categories/gifts).
- Error JSON from backend should include `error` code; UI maps generic to friendly copy.
- Retry strategy: exponential backoff (1s, 3s, 8s) with manual retry button.
- Offline: show cached data (if <24h old) with "Offline" badge.

## 15. Test Cases (Minimum)
| Case | Setup | Expected |
|------|-------|----------|
| Master standard | >=3 categories | 3 chips rendered |
| Master two categories | Only 2 categories scored | 2 chips + note |
| Master tie across rank 3 | 4 categories tie at score for ranks 2–4 | Backend still returns truncated 3; UI renders 3 |
| Gifts standard | 3+ gifts | 3 gift chips |
| Gifts incomplete | Only 2 answered groups | 2 chips + "Incomplete – retake" |
| Missing key | Backend omits `top3` | Error placeholder with retry |
| Rate limit email | Exceed threshold | Toast + no send, 429 handled |
| Accessibility | VoiceOver enabled | Announces combined summary string |

Deterministic ordering test: Provide fixed dataset where alphabetical tiebreak is verifiable.


---
*End of PROGRESS_PAGE requirements.*

---

## 13. Verified Decisions & Implementation Impact (Post‑Review)
User Decisions Provided:
1. Display Strategy (Q1 = option b): Master Assessment featured card must show BOTH overall aggregate score AND (new) Top 3 category scores from the latest attempt.
2. Tie Handling (Q2 = option a): Deterministic ordering for ties (no special tie grouping) — stable sort by (score DESC, category_name ASC) then take first 3.
3. Future Deltas Placeholder (Q3 = Yes): Reserve structure now to enable future “change since previous attempt” without rendering any delta UI in v1.

### 13.1 Current Backend Capability Assessment
| Capability | Present Now | Gap / Note |
|------------|-------------|------------|
| Per-question category linkage (Question.category_id -> Category) | Yes (`question.category_id`) | OK |
| Category name resolution when submitting draft | Yes (joins in `submit_draft`) | OK |
| AI scoring returns per-category scores | Yes (`score_assessment_by_category` yields `category_scores`) | OK |
| AI scoring stores scores JSON in Assessment.scores | Yes (`scores=detailed_scores`) | OK |
| Overall score calculation | Integer floor of average of category scores (`sum // len`) | Might want precise mean (float) before formatting UI |
| Top 3 categories derivable | Implicit (available in `scores['category_scores']`) | Need explicit backend helper or contract for client |
| Attempt history for deltas | Partial: `assessments` table has timestamp; separate `assessment_score_history` model exists but submission does NOT currently persist a historical snapshot per submission beyond the Assessment record itself | Need consistent history writing on each submission for reliable delta computation |
| Endpoint returning latest Master assessment with category breakdown | Not explicitly defined (submission returns full object; listing endpoint unspecified here) | Need dedicated read endpoint or augment list to include summary_fields |
| Spiritual Gifts handling of top 3 w/ tie suppression at card level | Gifts spec already defines top 3 (ties truncated) | Align Master logic to mirror gifts card behavior |
| Delta (previous vs current) computation | Not implemented | Placeholder only (structure & data capturing) |

### 13.2 Required Pre‑Requisite Changes (Before Implementing UI Showing Top 3 Categories for Master)
1. Backend: Ensure every new assessment submission writes a row to `assessment_score_history` containing the full `scores` JSON (if not already automatically populated). This guarantees previous attempt retrieval for future delta.
2. Backend: Introduce endpoint (proposed) `GET /assessments/master/latest` → returns: `{ id, completed_at, overall_score, category_scores: {<category>: int}, top3: [ { category, score } ], version }`.
3. Backend: Define deterministic ordering algorithm for category ranking (score DESC, category_name ASC) and include server‑computed `top3` array so all clients stay consistent.
4. Backend: Adjust overall score calculation to use precise arithmetic mean (float, one decimal) before rounding for display; maintain stored integer field for backward compatibility OR store both `overall_score_raw` (float) and `overall_score` (int) in `scores` JSON.
5. Backend: When scoring, persist category names exactly as canonical Category.name (avoid drift) — consider normalizing to slug for internal keys while returning display names.
6. Backend: If an assessment has fewer than 3 categories (edge case), still return `top3` array with whatever is available; client renders note if < 3.
7. Backend: Add version tag (e.g., `"master_v1"`) inside `scores` JSON to future‑proof changes in scoring algorithm.

### 13.3 Optional (Future Delta Enablement)
These are not required for v1 display but should be recorded now so future delta UI is low friction:
- Write a history row into `assessment_score_history` on every submission (see #1) with fields: `{ overall_score_raw, overall_score, category_scores, computed_at }`.
- Provide endpoint `GET /assessments/master/history?limit=N` returning compact chronological array for delta computations.
- Standardize numeric types (store all category scores as integers 0–10, overall float) to avoid client inference.

### 13.4 Frontend Contract Additions (Documentation Only)
Master Featured Card now expects response shape:
```
{
  "overall_score": 8.3,              // float (one decimal recommended)
  "overall_score_display": 8,        // integer for prominent badge
  "top3": [                          // already ordered & truncated
     { "category": "Prayer", "score": 9 },
     { "category": "Scripture", "score": 8 },
     { "category": "Community", "score": 8 }
  ],
  "completed_at": "2025-09-12T14:04:09Z",
  "version": "master_v1"
}
```
Client display rules:
- Show integer `overall_score_display` large.
- Show category list horizontal / stacked (truncate labels if overflow) using returned ordering.
- If < 3 categories: render available; append subtle text "Fewer categories assessed".

### 13.5 Acceptance Criteria Addendum
- Master featured card displays both overall aggregate and exactly three category chips (or fewer with note) using backend `top3` array.
- Ties resolved deterministically on backend using (score DESC, category_name ASC) prior to truncation.
- No client-side tie resolution logic beyond rendering order given.
- Response includes `version`; unsupported versions gracefully fallback (client may display badge "Updated Scoring").

### 13.6 Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Missing history rows for earlier attempts | Future deltas inaccurate | Backfill script creates history entries from existing `assessments` table at deployment of this change |
| Floating vs integer mismatch | UI rounding inconsistencies | Define rounding rule: `overall_score_display = round(overall_score_raw)` (half up) |
| Category rename drift | Inconsistent historical labels | Store both `category_key` (immutable slug) and `display_name`; use slug for comparisons |

### 13.7 Deployment / Migration Notes
1. Data Migration: Backfill `assessment_score_history` for existing rows (INSERT one history record per assessment with `triggered_by='system_migration'`).
2. No schema change required unless adding slugs: if so add columns `categories.slug` and populate from name (lowercase, hyphenated) before exposing new endpoints.
3. Release Order: (a) Deploy backend changes + endpoint, (b) Update frontend to consume new endpoint/shape, (c) Remove any temporary client derivation of top 3.

---
*Addendum complete.*
