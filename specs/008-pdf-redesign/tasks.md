---
description: "Tasks for 008 PDF Report Redesign"
---

# Tasks: PDF Report Redesign

**Input**: Design documents from `/specs/008-pdf-redesign/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/pdf-reports.md, quickstart.md

**Tests**: Principle VIII applies. No endpoint is new, but two route handlers change (spiritual gifts and generic), so each gets a success test that captures the renderer's inputs. The existing authz tests stay. Render tests cover the kit and every renderer. Each story ends with `pytest` passing.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [x] T001 Copy `Poppins-Regular.ttf`, `Poppins-Medium.ttf`, `Poppins-SemiBold.ttf` and `Poppins-Bold.ttf` from `/Users/tmoney/Developer/trooth_assessment/assets/fonts/` into `assets/fonts/`. Confirm `.dockerignore` does not exclude `assets/`.
- [x] T002 [P] Create the packages `app/services/pdf/__init__.py` and `app/data/__init__.py` (empty or re-exports).

---

## Phase 2: Foundational (shared PDF kit, blocks all stories)

- [x] T003 [P] Create `app/services/pdf/theme.py` with the palette from research R9:
  - `CHARCOAL #1A1A1A`, `SURFACE #222222`, `RULE_DARK #2E2E2E`
  - `GOLD #D4AF37`, `GOLD_DEEP #B8960C`, `GOLD_TINT #FAF4E1`
  - `INK #1A1A1A`, `BODY #333333`, `MUTED #6B6B6B`, `HAIRLINE #E6E6E6`, `TRACK #EFEFEF`
  - `SAGE #6B8F71`, `AMBER #C9A227`, `CLAY #B5654A`

  Also: page constants (US Letter, 0.6 in side margins), a type scale (title 22/26, H2 13/16, H3 11.5/15, body 9.5/14, small 8/11), and `status_color(kind)`.
- [x] T004 [P] Create `app/services/pdf/fonts.py`:
  - `register_fonts() -> FontSet` (idempotent, once per process). It registers Poppins Regular/Medium/SemiBold/Bold from `assets/fonts/` plus `registerFontFamily('Poppins', normal, bold=Bold, italic=Regular, boldItalic=Bold)`.
  - It returns names for `regular`, `medium`, `semibold` and `bold`.
  - If a file is missing, it falls back to Helvetica/Helvetica-Bold and logs once with `logging.getLogger(__name__)`.
- [x] T005 [P] Create `app/services/pdf/text.py`:
  - `strip_unsupported(text)`: removes the emoji ranges U+1F000–1FAFF, U+2600–27BF, U+2B00–2BFF, U+1F1E6–1F1FF, U+FE0F and U+200D, then collapses whitespace.
  - `safe(value) -> str`: `None` → `""`, then `str()`, then `strip_unsupported`, then `xml.sax.saxutils.escape`.
  - `format_date(value) -> str | None`: accepts datetime or ISO string (with a `Z`), returns `"%B %-d, %Y"` (portable: build it from `strftime('%B')` + `day` + `year`), or `None` if it cannot parse.
- [x] T006 Create `app/services/pdf/layout.py` (depends on T003–T005):
  - `NumberedCanvas`: a `canvas.Canvas` subclass that saves page states and draws the footer in `save()`. The footer has a gold 0.75 pt hairline, `"T[root]H Discipleship · {host of settings.app_landing_url}"` on the left and `"Page X of Y"` on the right, both 8 pt `MUTED`.
  - `BrandDoc(BaseDocTemplate)` with `first` and `later` page templates:
    - First page: a charcoal band 96 pt tall across the full width. It holds `assets/email_logo_v2.png`, drawn about 34 pt tall and preserving aspect, with a text wordmark "T[root]H" in gold if the image is missing. The title is 20 pt SemiBold gold and the subtitle (`"{subject} · {date_label}"`) is 9.5 pt `#E6E6E6`. A 2 pt gold line runs under the band.
    - Later pages: a 30 pt charcoal strip with the title in gold at 9 pt.
    - Frames sit below the band and above the footer, so nothing can overlap.
  - `build_pdf(title, subject, date_label, story_fn, fallback_lines, context_id=None) -> bytes`: builds with `canvasmaker=NumberedCanvas`. On any exception it logs `type(e).__name__` + `context_id` (no report text) and returns `fallback_pdf(...)`.
  - `fallback_pdf(title, subject, date_label, lines) -> bytes`: one or more pages drawn on a plain canvas with Helvetica only. It has the charcoal band, the title, the subject and date, and lines wrapped at the frame width.
- [x] T007 Create `app/services/pdf/components.py` (depends on T003–T006). Every function takes plain strings and calls `safe()` internally:
  - `para(text, style="body", markup=False)`. When `markup=True`, the caller passes text that is already safe with kit tags.
  - `section_heading(text)`: uppercased, tracked, 13 pt SemiBold `INK`, with a 2 pt gold rule beneath and space before and after.
  - `subheading(text)`.
  - `score_bar(value, max_value, width, height=6, fill=GOLD)`: a Flowable that draws a `TRACK` rounded rect and a gold fill, with value clamped to 0..max.
  - `score_row(label, value, max_value, note=None, highlight=False)`: a Table row with label, bar, `"N/max"` and an optional note line, tinted `GOLD_TINT` when highlighted.
  - `stat_card(big, label, sub=None)`: a dark `SURFACE` card, big number in gold 30 pt, label in white, sub in `#A3A3A3`.
  - `cards_row(cards)`: equal-width dark cards with a 6 pt gap.
  - `callout(title, body_lines)`: a 3 pt gold left bar on a `GOLD_TINT` fill.
  - `two_col_cards(left_title, left_items, right_title, right_items)`.
  - `bullets(items)`: drawn gold dot markers, not glyphs.
  - `marker(kind)` for check/arrow/star drawn as small vector shapes, used instead of ✓✦↑ glyphs.
- [x] T008 Export the kit API from `app/services/pdf/__init__.py`.
- [x] T009 [P] Add the kit tests to `tests/test_pdf_reports.py`:
  - `safe()` escapes `& < > "` and strips 🎯📖✅.
  - `format_date("2026-10-13T22:36:48Z") == "October 13, 2026"`.
  - `build_pdf` with a story containing hostile text returns bytes starting with `%PDF-` and containing `%%EOF`.
  - `build_pdf` with a `story_fn` that raises still returns a valid PDF (the fallback).
  - `register_fonts()` returns Poppins names when the files exist.
  - Add a story-walker helper `collect_text(story)` that descends `Table._cellvalues`, `KeepTogether._content` and lists, gathering `Paragraph.text`. Other tests reuse it.

**Checkpoint**: `pytest tests/test_pdf_reports.py` passes. The kit is ready.

---

## Phase 3: User Story 1: Apprentice gets a branded, useful Spiritual Gifts PDF (P1) 🎯 MVP

**Goal**: The gifts PDF follows the content contract in `contracts/pdf-reports.md`.

**Independent Test**: Email the gifts report as an apprentice. The PDF has the band, name and readable date, top cards with N/12, deep dives, 24 ranked rows in bands and next steps, and no jargon.

- [x] T010 [P] [US1] Create `app/data/spiritual_gift_guidance.py` with `GIFT_GUIDANCE: dict[str, dict]` for all 24 slugs in `app.core.spiritual_gifts_map.MAP`:
  - leadership, pastor-shepherd, discernment, exhortation, hospitality, prophecy, knowledge, miracles, healing, helps, mercy, evangelism, faith, teaching, wisdom, intercession, service, tongues-interpretation, giving, missionary, apostleship, craftsmanship, administration, music-worship.

  Rules from data-model.md:
  - `scriptures`: "2–3 references, e.g. `\"Romans 12:8\"`. References only, no quoted verse text".
  - `ways_to_serve`: "≥ 3 short imperative sentences, each ≤ 120 chars".
  - `reflection`: "One question ending in `?`".

  Add a module docstring noting the content is pending product-owner review.
- [x] T011 [P] [US1] Add `display_to_slug(name: str) -> str | None` to `app/services/spiritual_gifts_scoring.py`. It reverses `_slug_display`, then falls back to normalizing: lowercase, strip, collapse `[\s/&]+` to `-`, then look up against the `CORE_MAP` keys (so "Pastor / Shepherd", "Pastor/Shepherd", "Music/Worship" and "Tongues & Interpretation" all resolve). This is an additive change.
- [x] T012 [US1] Rewrite `app/services/spiritual_gifts_report.py`:
  - Remove the canvas renderer, the `_HAS_REPORTLAB` pseudo-PDF path and `_compose_sections`.
  - Add `_prepare_gifts(scores, definitions)`. It returns ranked rows with `slug, gift, score, rank, band (strongest ≥9 / developing 5–8 / less_evident ≤4), is_top, is_tied_third, summary, definition, guidance`, using `display_to_slug` and `definitions[slug]`. It also returns `deep_dive` (the expanded set, falling back to truncated, then the first 3 of `all_scores`; capped at 6 with an `also_tied` list for the overflow).
  - Add `build_gifts_story(apprentice_name, scores, definitions) -> list`, with sections in contract order:
    1. intro: ≤ 3 sentences citing 1 Corinthians 12:4–7 and 1 Peter 4:10, explaining the 0–12 scale
    2. "Your top gifts": `cards_row` of up to 3 cards with `#rank`, name, `N/12` and a bar, plus a "Tied for 3rd: …" line
    3. deep dives: `KeepTogether` of heading `"#rank Name · N/12"`, definition, `callout("In Scripture", refs)`, "Ways to use this gift" bullets, and `callout("Reflect", [question])`
    4. "All gifts ranked": three band subheadings with `score_row` rows (summary as the note; top rows highlighted)
    5. "Next steps": 3 bullets built from the #1 gift's name and its first `ways_to_serve` item, plus a closing "Romans 12:6" line.
  - Change the signature to `generate_pdf(apprentice_name, version, scores, definitions, *, assessment_date=None) -> bytes`. It calls `build_pdf("Spiritual Gifts Report", name or "Apprentice", format_date(assessment_date) or f"Generated {today}", ...)` with fallback lines listing the top gifts.
  - `version` is accepted but not printed.
- [x] T013 [US1] Update `generate_html` in `app/services/spiritual_gifts_report.py` to use `_prepare_gifts`, for slug-matched summaries and the same ordering. Drop the "Truncated/Expanded" headings ("Top gifts", "All gifts ranked") and escape with `html.escape`.
- [x] T014 [US1] In `app/routes/spiritual_gifts.py` `email_spiritual_gifts_report`, pass `assessment_date=assessment.created_at` to `generate_pdf`.
- [x] T015 [P] [US1] Add the gifts tests to `tests/test_pdf_reports.py`:
  - Every MAP slug has guidance that meets the rules.
  - `display_to_slug` covers the 4 punctuation cases.
  - With the real definitions JSON (`scripts/spiritual_gift_definitions_v1.json`), every ranked row has a summary, including Pastor/Shepherd and Music/Worship.
  - `collect_text(build_gifts_story(...))` contains "Your top gifts", "/12", "In Scripture", "Reflect", "Next steps" and all 24 gift names. It contains no "Truncated", "Expanded" or "Version", and nothing matches `\d{4}-\d{2}-\d{2}T`.
  - A tie case (4 gifts at the 3rd score) shows "Tied for 3rd" and 4 deep dives.
  - An all-zero case caps deep dives at 6 and shows "Also tied".
  - `generate_pdf` returns `%PDF-`.

**Checkpoint**: US1 tests and `tests/test_spiritual_gifts_email_reports.py` pass.

---

## Phase 4: User Story 2: Mentor-sent gifts PDF names the apprentice (P1)

**Goal**: The mentor or admin route renders the same PDF with the apprentice's name and date.

**Independent Test**: A mentor linked to an apprentice emails the report, and the captured PDF inputs carry the apprentice's name.

- [x] T016 [US2] In `app/routes/spiritual_gifts.py` `mentor_admin_email_spiritual_gifts_report`, move the `apprentice_user` lookup above the PDF and HTML build. Pass `apprentice_name` (not `None`) and `assessment_date=assessment.created_at` to `generate_pdf` and `generate_html`.
- [x] T017 [P] [US2] Add a test to `tests/test_spiritual_gifts_email_reports.py`. It monkeypatches `app.routes.spiritual_gifts.generate_pdf` to capture its args, has the mentor email the report, and asserts the captured `apprentice_name` equals the apprentice's name and that `assessment_date` is set. It reuses the existing mentor fixtures. The existing unlinked-mentor 403 test stays.

**Checkpoint**: The gifts email tests pass.

---

## Phase 5: User Story 3: Mentor report PDF renders cleanly and on-brand (P2)

**Goal**: `render_pdf_v2` is rebuilt on the kit with the same sections, no emoji glyphs and a guaranteed valid PDF.

**Independent Test**: Render a basic, premium and hostile-text context. Each PDF is valid, has no boxes and uses brand styling.

- [x] T018 [US3] In `app/services/master_trooth_report.py`, add `build_mentor_story(context) -> list`. It reproduces every section and data path of today's `render_pdf_v2` (lines 465–1075), in the same order, using kit components:
  - headline `stat_card` (`{overall_mc_percent}%`, "Biblical Knowledge", `knowledge_band`)
  - `two_col_cards` "Top strengths" / "Growth areas"
  - category `score_row` (/10) with level as the note
  - knowledge topics `score_row` (/100, shown as %)
  - insights as `subheading` + `para` + `bullets` for mentor moves
  - premium: executive summary; strengths and gaps deep dives (biblical perspective in a `callout`); conversation guide (AI sessions and legacy fallback); biblical knowledge analysis (topics as `score_row`, theological check, reading plan `callout`); spiritual formation (markers, development plan, questions)
  - priority action as a `callout` with scripture
  - conversation starters, four-week plan and resources
  - premium progress tracking, mentor prep notes (prayer focus `callout`) and personalized resources.

  Replace every emoji and the `✓ ✦ ↑ 📖 📚 🎯 💬 📅 📈 📝 🙏 ❓ ⚠ ○` glyphs with text labels or `marker()`. Status colors may come only from `status_color()`.
- [x] T019 [US3] Replace the body of `render_pdf_v2(context)` with `build_pdf("Mentor Report", apprentice_name, format_date(submitted_date) or "", lambda: build_mentor_story(context), fallback_lines=[knowledge %, band, strengths, gaps])`. Delete the markdown-bytes fallback for PDFs. Keep `render_markdown_print_v2`, which the print route uses. Change the footer site to the kit's (no more `www.troothapp.com`).
- [x] T020 [P] [US3] Add tests to `tests/test_pdf_reports.py`:
  - basic v2.0 context (from `tests/test_master_v2_reporting.py`'s mock), v2.1 context and premium `full_report` context: each returns `%PDF-`
  - hostile context: strengths `"Prayer & fasting <daily>"`, an insight observation with 🎯 and a 6,000-char `trajectory_note`. It returns `%PDF-`, `collect_text` contains `&amp;` and `&lt;daily&gt;`, and contains no emoji code points
  - every premium section title appears in `collect_text` for the premium context.

**Checkpoint**: `tests/test_master_v2_reporting.py`, `tests/test_master_trooth_email.py` and `tests/test_mentor_endpoints_assessments.py` pass.

---

## Phase 6: User Story 4: Generic assessment PDF is branded and complete (P3)

**Goal**: A branded generic summary, and the v2 layout where v2 data exists.

**Independent Test**: Email a generic report with and without `mentor_report_v2`. Each PDF uses the right layout.

- [x] T021 [US4] Rewrite `app/services/generic_assessment_report.py`:
  - `build_generic_story(title, scores)`: an overall `stat_card` (`overall_score`/10), then a "Category scores" `section_heading` with `score_row` per category (`max` from `cat.get('max_score', 10)`). If `scores.get('summary')` or `scores.get('recommendations')` are present, show them as `para`/`bullets`.
  - `generate_pdf(title, apprentice_name, scores, *, assessment_date=None)` uses `build_pdf`.
  - `generate_html` keeps its behavior but escapes values.
  - Remove the pseudo-PDF path.
- [x] T022 [US4] In `app/routes/generic_assessments.py` (both email handlers, about lines 260 and 426): when `a.mentor_report_v2` is set, build the context with `build_report_context` (as the premium email branch does), add `full_report` when it is cached, and call `render_pdf_v2(context)`. Otherwise call `gen_pdf(..., assessment_date=a.created_at)`. The attachment filename is unchanged.
- [x] T023 [US4] In `app/services/master_trooth_report.py`, replace the legacy `generate_pdf(apprentice_name, scores)` body to delegate to the generic renderer. Map `category_scores` dict → categories list, use title "Master T[root]H Assessment", and keep the name and signature for `app/routes/master_trooth.py:293,414`. Escape values in the legacy `generate_html`.
- [x] T024 [P] [US4] Add tests to `tests/test_pdf_reports.py`: the generic story has the overall and category rows, and `generate_pdf` returns `%PDF-`. Add a test to `tests/test_generic_assessments_endpoints.py` that monkeypatches `app.routes.generic_assessments.render_pdf_v2` and `gen_pdf` to capture calls: with `mentor_report_v2` set, `render_pdf_v2` is called; without it, `gen_pdf` is called.

**Checkpoint**: The generic and master email tests pass.

---

## Phase 7: Polish & Cross-Cutting

- [x] T025 [P] Create `scripts/render_pdf_samples.py` (dev-only, `--out DIR`). It writes `gifts_typical.pdf`, `gifts_tie.pdf`, `gifts_all_zero.pdf`, `mentor_basic.pdf`, `mentor_premium.pdf`, `mentor_hostile.pdf` and `generic.pdf` from fixed sample data.
- [x] T026 Visual review: run the sample script, convert pages to PNG (`sips -s format png`) and check them against the quickstart checklist. Fix spacing, contrast or overflow issues in `app/services/pdf/components.py` and `layout.py`.
- [x] T027 Run the full suite (`.venv/bin/pytest -q`) and fix regressions. Grep `app/` for leftover `troothapp.com`, `PSEUDO-PDF` and `HexColor('#2F4B7C')`.
- [x] T028 [P] Record the gift-guidance review as an open item in `specs/008-pdf-redesign/checklists/requirements.md` notes. Add a "PDF reports" line to `CLAUDE.md` if it documents services.

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 (kit) → the US phases. US1 and US2 touch the same route file, so do US1 first. US3 and US4 depend only on Phase 2. US4's T023 and US3's T018/T019 edit the same file, so run them one after the other.
- Within US1: T010 and T011 [P] → T012 → T013, T014 → T015.
- Polish runs last.

## Parallel Examples

- Phase 2: T003, T004 and T005 together, then T006 → T007 → T008. T009 can start once T006 is done.
- US1: T010 (content) and T011 (slug helper) together.
- After US1: US3 (T018–T020) and US4 T021/T022/T024 in parallel. T023 waits for T019.

## Implementation Strategy

- **MVP**: Phases 1–3 (kit + gifts PDF). That is what the user asked for first.
- Then US2 (a small route fix), US3 (the mentor restyle) and US4 (generic), each a shippable increment.
- Verify on dev (quickstart §3) before prod.
