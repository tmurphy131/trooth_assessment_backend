# Implementation Plan: PDF Report Redesign

**Branch**: `feature/pdf-redesign` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-pdf-redesign/spec.md`

## Summary

All PDFs are built from one small ReportLab kit in `app/services/pdf/`. The kit holds:
- the brand palette
- Poppins fonts
- a page template: a charcoal header band with the logo on the first page, a slim strip on later pages, and a footer with "Page X of Y"
- reusable flowables: section heading, stat card, score bar, callout, two-column cards and a safe paragraph that XML-escapes text and strips emoji
- a minimal fallback PDF that is always valid.

The three renderers are rebuilt on the kit:

- **Spiritual Gifts** (`spiritual_gifts_report.generate_pdf`): a new section flow (intro, top-gift cards, deep dives, ranked list in strength bands, next steps). Gifts are matched by slug, and new static per-gift guidance content lives in `app/data/spiritual_gift_guidance.py`.
- **Mentor / Master** (`master_trooth_report.render_pdf_v2`): the same sections and data, restyled on the kit with no emoji glyphs. The legacy `generate_pdf`/`generate_html` there are replaced by the generic branded renderer.
- **Generic** (`generic_assessment_report.generate_pdf`): a branded summary. Routes use `render_pdf_v2` when `mentor_report_v2` exists.

Route fixes in `app/routes/spiritual_gifts.py` pass the apprentice's name and assessment date. No endpoint, schema or filename changes.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, SQLAlchemy, ReportLab ≥ 4.0.7 (existing). **No new packages.** Tests inspect the flowable story instead of extracting PDF text, so `pypdf` is not needed (research R6).

**Assets (new)**: `assets/fonts/Poppins-{Regular,Medium,SemiBold,Bold}.ttf`, copied from the Flutter repo (SIL OFL). The existing `assets/email_logo_v2.png` (760×270, black background) is used on the band. The Dockerfile already runs `COPY . .`, and `.dockerignore` does not exclude `assets/`.

**Storage**: N/A. No migrations. Gift guidance is static code data.

**Testing**: pytest. New `tests/test_pdf_reports.py`:
- every renderer returns bytes starting with `%PDF`
- hostile text (`&`, `<`, emoji, 5k-char strings) renders
- guidance covers every gift slug in `MAP`
- slug matching covers `Pastor/Shepherd` and `Music/Worship`
- tie-at-3rd handling and the 6-deep-dive cap
- the gifts story contains no "Truncated"/"Version"/ISO timestamp
- the mentor-sent gifts PDF names the apprentice (endpoint test with `generate_pdf` patched to capture its args).

Existing tests keep passing: `test_spiritual_gifts_email_reports.py`, `test_master_v2_reporting.py`, `test_generic_assessments_endpoints.py`, `test_master_trooth_email.py` and `test_mentor_endpoints_assessments.py`.

**Target Platform**: Google Cloud Run (dev and prod services)

**Project Type**: web-service (client: Flutter app in `trooth_assessment`; no app change)

**Performance Goals**: each PDF renders in under 1 s for a typical report and under 2 s for a full premium report (two-pass page numbering included).

**Constraints**:
- US Letter
- 0.6 in side margins
- prints well: white pages; dark ink only in the header band and the small top-gift cards
- all text drawn with Poppins or the Helvetica fallback, with no glyphs outside those fonts.

**Scale/Scope**: 3 renderers, 1 shared kit (about 5 small modules), 24 gift guidance entries, and 3 route files touched.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Auth**: ✅ No endpoint or authorization change. The mentor gifts route keeps its active `MentorApprentice` check, and premium content is still included only where it is today.
- [x] **II. Errors**: ✅ Same `HTTPException` paths. Render failures are logged and replaced by a valid fallback PDF, never a trace.
- [x] **III. Migrations**: N/A. No schema change.
- [x] **IV. Config & secrets**: ✅ The footer URL comes from `settings.app_landing_url`. No new config.
- [x] **V. Logging**: ✅ `logging.getLogger(__name__)`. Failure logs carry the exception type and assessment id only, with no report text or emails.
- [x] **VI. Compatibility**: ✅ Purely output changes. Request and response models, endpoints and attachment filenames are unchanged. `generate_pdf` signatures only gain optional kwargs.
- [x] **VII. Layering**: ✅ Rendering stays in `app/services/` (`app/services/pdf/`). Static content goes in `app/data/`. No LLM calls are added.
- [x] **VIII. Tests**: ✅ New render tests, plus a capture test on the mentor gifts route (its existing success and authz tests stay). No external calls.
- [x] **IX. Deploy**: ✅ Verify on dev (email and share from the app on iOS) before prod.
- [x] **X. Contract**: ✅ [contracts/pdf-reports.md](contracts/pdf-reports.md) records that the endpoints and shapes are unchanged and defines the PDF content contract. Frontend: none needed.
- [x] **XI. Formatting**: ✅ Only the touched functions are rewritten. No unrelated reformatting.

**Post-design re-check**: still all ✅ / N/A. Nothing in the design adds endpoints, tables or secrets.

## Project Structure

### Documentation (this feature)

```text
specs/008-pdf-redesign/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/pdf-reports.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
app/
├── services/pdf/
│   ├── __init__.py          # public re-exports
│   ├── theme.py             # palette + type scale + spacing
│   ├── fonts.py             # Poppins registration, Helvetica fallback
│   ├── text.py              # safe(): xml-escape + emoji/unsupported glyph strip
│   ├── layout.py            # BrandDoc (BaseDocTemplate), header band/strip, NumberedCanvas, build_pdf(), fallback_pdf()
│   └── components.py        # section_heading, stat_card, score_bar, score_row, callout, cards_row, two_col_cards, bullets, para
├── data/
│   ├── __init__.py
│   └── spiritual_gift_guidance.py   # GIFT_GUIDANCE[slug] = {scriptures, ways_to_serve, reflection}
├── services/spiritual_gifts_report.py   # rewritten generate_pdf (+ build_gifts_story), generate_html ordering/slug fix
├── services/master_trooth_report.py     # render_pdf_v2 on kit (+ build_mentor_story); legacy generate_pdf → generic renderer
├── services/generic_assessment_report.py # branded generate_pdf (+ build_generic_story)
├── services/spiritual_gifts_scoring.py  # expose display→slug helper (additive)
└── routes/
    ├── spiritual_gifts.py       # pass apprentice_name + assessment_date to generate_pdf (both routes)
    ├── generic_assessments.py   # render_pdf_v2 when mentor_report_v2 exists
    └── master_trooth.py         # legacy fallback → generic branded renderer
assets/fonts/Poppins-*.ttf
tests/test_pdf_reports.py
scripts/render_pdf_samples.py    # dev-only: writes sample PDFs for visual review
```

**Structure Decision**: The kit is a sub-package of `app/services/`, because the PDFs are output integrations, like `email.py`. The guidance content goes in a new `app/data/` package, which mirrors the Flutter repo's `lib/data/` for static content. Each renderer exposes a `build_*_story()` function, so tests can assert on content without parsing PDFs.

## Complexity Tracking

No constitution violations.
