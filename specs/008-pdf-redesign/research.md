# Research: PDF Report Redesign

## R1. Rendering engine
- **Decision**: Keep ReportLab, using platypus (`BaseDocTemplate` + `PageTemplate` + flowables) for every PDF.
- **Rationale**: It is already a dependency, pure Python and runs on Cloud Run with no system libraries. Platypus handles flowing text across pages, which the canvas-drawn gifts PDF does by hand and gets wrong (the overlapping header box).
- **Alternatives**:
  - WeasyPrint (HTML→PDF, reusing email templates): needs Pango/Cairo system libraries in the image, a bigger image and slower cold starts.
  - Headless Chrome: far too heavy.

## R2. Page chrome and "Page X of Y"
- **Decision**: Draw the chrome in `onPage` callbacks:
  - First page: an 88 pt charcoal band with the logo, gold title and subtitle.
  - Later pages: a 28 pt strip with the title.
  - Footer: a gold hairline, the site URL and the page number.
  - Get the total page count from a `NumberedCanvas` subclass that defers `showPage` and writes "Page X of Y" in `save()`.
- **Rationale**: This is the standard ReportLab pattern, done in one build pass, and the chrome can never overlap body frames.
- **Alternatives**: Two `multiBuild` passes cost more and are needed only for TOCs.

## R3. Fonts
- **Decision**:
  - Register Poppins Regular/Medium/SemiBold/Bold from `assets/fonts/` with `registerFontFamily('Poppins', normal=Regular, bold=Bold, italic=Regular, boldItalic=Bold)`. Poppins ships no italic, so `<i>` falls back to upright.
  - Medium is registered as `Poppins-Medium` and SemiBold as `Poppins-SemiBold` for headings.
  - If any file is missing, fall back to Helvetica and Helvetica-Bold.
  - Register once per process.
- **Rationale**: It matches the app's typeface (FR-003). The fonts are SIL OFL licensed, so they can be redistributed.
- **Alternatives**: Helvetica only is less on-brand.

## R4. Escaping and unsupported glyphs
- **Decision**: Run every dynamic string through `safe(text)`:
  1. `str()` and handle `None`.
  2. Strip emoji and pictographs (regex over U+1F000–1FAFF, U+2600–27BF, U+2B00–2BFF, U+FE0F, U+200D, U+1F1E6–1F1FF), then collapse doubled spaces.
  3. Replace `✓✦→↑•` only where the font lacks them. Poppins has `•`, `–`, `—`, curly quotes and `→`, but not `✓` or `✦`, so the kit draws its own markers.
  4. `xml.sax.saxutils.escape`.

  Markup is added only by kit code around already-safe text.
- **Rationale**: This fixes FR-004 and FR-005 at one choke point. Today's failure (an `&` makes `Paragraph` raise, and the caller returns markdown bytes) cannot recur.
- **Alternatives**: An emoji font (Noto Color Emoji) doesn't render color glyphs in ReportLab and is large.

## R5. Failure fallback
- **Decision**: `build_pdf(story_fn, ...)` wraps the build. On any exception it logs the exception type and context id, then returns `fallback_pdf(title, subject, date, lines)`. That is a canvas-drawn one-page branded PDF with the essentials, built with Helvetica only, so it cannot fail on fonts or markup. Renderers never return non-PDF bytes. The `_HAS_REPORTLAB=False` "PSEUDO-PDF" paths are deleted, because ReportLab is a hard dependency in `requirements.txt`.
- **Rationale**: FR-006.

## R6b. Logo on the dark band
- **Decision**: `assets/pdf_logo.png` is derived from `email_logo_v2.png` with its near-black badge background made transparent and cropped, so it sits cleanly on the charcoal band.

## R7. Gift guidance content
- **Decision**:
  - A static dict in `app/data/spiritual_gift_guidance.py`, keyed by the slugs in `app/core/spiritual_gifts_map.MAP`.
  - Each entry: `scriptures` (2–3 references, shown as references only, not quoted text, which avoids translation licensing), `ways_to_serve` (3 short imperative bullets) and `reflection` (one question).
  - The sources are the classic gift passages: Rom 12:6–8, 1 Cor 12:4–11 and 12:28–31, Eph 4:11–12, 1 Pet 4:9–11, plus Old Testament examples for gifts like craftsmanship (Ex 31:1–5) and music (1 Chr 25:1–7).
  - A test asserts complete coverage.
- **Rationale**: No migration, versioned with the code, and easy for the product owner to review in one file.
- **Alternatives**: New DB columns on `spiritual_gift_definitions` would need a migration and seed changes for content that never varies per user.

## R6. Testing without a PDF text extractor
- **Decision**:
  - Each renderer exposes `build_*_story(...) -> list[Flowable]`.
  - Tests walk the story (descending into `Table._cellvalues` and `KeepTogether._content`) and collect `Paragraph.text` to assert on content.
  - Byte-level tests check the `%PDF-` header and the `%%EOF` trailer.
- **Rationale**: No new dependency, and assertions on content are more precise than extracted text (TTF subsetting makes the raw bytes unreadable).
- **Alternatives**: Adding `pypdf` to dev requirements works, but it is a new package for testing only.

## R8. Gift name → slug matching
- **Decision**:
  - Add `display_to_slug(name)` to `spiritual_gifts_scoring.py`. It builds the reverse of `_slug_display` and falls back to normalizing: lowercase, strip, `[\s/&]+` → `-`, then a lookup against MAP slugs, plus the known aliases `pastor-shepherd`, `music-worship` and `tongues-interpretation`.
  - Definitions are keyed by DB slug, which uses underscores (`pastor_shepherd`) where `MAP` uses hyphens (`pastor-shepherd`). `canonical_slug()` normalizes both sides (`[\s/&_-]+` → `-`), so definition lookups also go through it. Found during implementation.
- **Rationale**: FR-014. Today the lookup goes through `display_name`, and "Pastor / Shepherd" ≠ "Pastor/Shepherd".

## R9. Visual system values
- **Palette**:
  - `CHARCOAL #1A1A1A`, `SURFACE #222222`, `RULE_DARK #2E2E2E`
  - `GOLD #D4AF37`, `GOLD_DEEP #B8960C` (for gold text on white, for contrast), `GOLD_TINT #FAF4E1`
  - `INK #1A1A1A`, `BODY #333333`, `MUTED #6B6B6B`, `HAIRLINE #E6E6E6`, `TRACK #EFEFEF`
  - status `SAGE #6B8F71` (strong), `AMBER #C9A227` (developing), `CLAY #B5654A` (needs focus)
- **Type**:
  - Title 22/26 SemiBold gold on charcoal
  - H2 13/16 SemiBold `INK` with a gold 2 pt rule underneath, uppercased with tracking
  - H3 11.5/15 SemiBold
  - Body 9.5/14 Regular `BODY`
  - Small 8/11 `MUTED`
- **Rationale**: It matches `_base.html` and the app (`kPrimaryGold`, `kCharcoal`). Pure gold `#D4AF37` on white fails contrast for small text, so small gold text on white uses `GOLD_DEEP`, and gold fills are used for bars and rules.

## R10. Strength bands and deep-dive cap
- **Decision**:
  - Bands: Strongest 9–12, Developing 5–8, Less evident 0–4.
  - Deep dives: everything in `top_gifts_expanded`, capped at 6. When the cap is hit, a line reads "Also tied: …".
  - If `top_gifts_expanded` is missing, use `top_gifts_truncated`, then the first 3 of `all_scores`.
- **Rationale**: 3 items × 0–4 = 12. The bands split the range into equal-ish thirds that fit how people read them.
