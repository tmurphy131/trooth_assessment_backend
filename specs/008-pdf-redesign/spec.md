# Feature Specification: PDF Report Redesign

**Feature Branch**: `feature/pdf-redesign` | **Spec Folder**: `specs/008-pdf-redesign/`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "Redesign every PDF report the platform generates so they match the T[root]H brand (charcoal + gold, same as the app and the redesigned emails from spec 005) and read like a finished, useful document. Three PDFs exist: Spiritual Gifts, Mentor/Master T[root]H (incl. premium sections), and Generic assessment. Hybrid style: dark header band with logo, gold accents and dark highlight cards on white pages so it prints well. Fix the listed defects (off-brand colors, overlapping header, raw timestamps, jargon, missing score scale, random definition order, no next steps, lost gift summaries, missing apprentice name, broken emoji glyphs, special characters breaking the file, plain generic PDF, wrong website). Gifts PDF gets new per-gift scripture, ways to serve and reflection content. No API contract changes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Apprentice receives a Spiritual Gifts PDF worth keeping (Priority: P1)

An apprentice finishes the Spiritual Gifts assessment and taps "Email PDF". The attached PDF looks like T[root]H, not a generic printout. It opens with their name and the date they took the assessment. It shows their top three gifts with scores on a clear 0–12 scale. For each top gift it explains what the gift is, where it appears in Scripture, practical ways to use it and a question to reflect on. It ends with all 24 gifts ranked and concrete next steps.

**Why this priority**: The user raised this PDF first. Today it is the least polished, it has visible layout defects, and it is the document apprentices are most likely to share with a mentor or a church leader.

**Independent Test**: Email a gifts report for a test apprentice and open the attachment. Check the branding, the content order, the score scale, the per-gift content and the absence of jargon.

**Acceptance Scenarios**:

1. **Given** a completed gifts assessment, **When** the apprentice emails themselves the report, **Then** the PDF shows a charcoal header band with the T[root]H logo, gold accents, the apprentice's name and a human-readable date (for example "October 13, 2026"), and nothing overlaps.
2. **Given** a result with a clear top three, **When** the PDF is opened, **Then** a "Your top gifts" section shows three highlighted cards in rank order, each with a score shown as "N/12" and a visual bar.
3. **Given** a result where several gifts tie for 3rd place, **When** the PDF is opened, **Then** the tied gifts are shown and labeled "Tied for 3rd", and each tied gift also gets a deep dive.
4. **Given** any top gift, **When** its deep dive is read, **Then** it contains a definition, 2–3 scripture references, at least three ways to use the gift and one reflection question.
5. **Given** any result, **When** the ranked list is read, **Then** all 24 gifts appear once, in score order, each with its one-line summary (including Pastor/Shepherd and Music/Worship), grouped into Strongest (9–12), Developing (5–8) and Less evident (0–4).
6. **Given** any result, **When** the PDF is read, **Then** it contains no "Version", no "Truncated"/"Expanded" labels and no raw machine timestamps, and it ends with a Next steps section.

---

### User Story 2 - Mentor sends an apprentice's gifts PDF (Priority: P1)

A mentor opens an apprentice's Spiritual Gifts results and emails the PDF to themselves. The PDF is the same branded report as in Story 1 and names the apprentice.

**Why this priority**: Today the mentor-sent PDF has no apprentice name, so a mentor with several apprentices cannot tell the reports apart.

**Independent Test**: As a mentor linked to a test apprentice, email the apprentice's gifts report and check that the PDF header and content name that apprentice.

**Acceptance Scenarios**:

1. **Given** a mentor actively linked to an apprentice, **When** the mentor emails the apprentice's gifts report, **Then** the PDF header shows the apprentice's name (not "Apprentice") and the date that apprentice took the assessment.
2. **Given** the same request, **When** compared to the apprentice-sent PDF for the same assessment, **Then** the content is identical.

---

### User Story 3 - Mentor report PDF renders cleanly and on-brand (Priority: P2)

A mentor or apprentice taps "Share PDF" on a T[root]H Mentor Report, or receives it attached to the mentor-report or master-assessment email. The PDF uses the same brand system as the gifts report. Section markers render as clean icons or labels, never as black boxes. The PDF always opens, whatever text the AI or the apprentice wrote.

**Why this priority**: This PDF is already roughly on-brand, but it has broken glyphs and a hard failure mode. When AI text contains "&" or "<", the recipient gets a file that is not a PDF and will not open.

**Independent Test**: Generate the mentor report PDF for an assessment whose report text includes "&", "<", ">", quotes and emoji, both with and without premium content. Confirm it opens, shows no black boxes and follows the brand.

**Acceptance Scenarios**:

1. **Given** report text containing "&", "<", ">", quotes or emoji, **When** the PDF is generated, **Then** a valid PDF is produced that shows the text faithfully (emoji are dropped or replaced) and no black boxes appear.
2. **Given** a premium user's report with full premium content, **When** the PDF is generated, **Then** every premium section that exists today still appears, in the same brand styling as the rest of the document.
3. **Given** a report, **When** the PDF is opened, **Then** colors come only from the brand palette (charcoal, gold, neutrals and a muted status set) and the footer shows the correct T[root]H website and "Page X of Y".
4. **Given** rendering fails for an unexpected reason, **When** the PDF is requested, **Then** the recipient still gets a valid, branded PDF with the essentials (name, date, headline scores) instead of a broken file.

---

### User Story 4 - Generic assessment PDF is branded and complete (Priority: P3)

An apprentice or mentor emails the report for any other assessment. The attached PDF is branded. When the assessment has the richer mentor-report data, the PDF uses the full mentor report layout from Story 3. Otherwise it shows a branded summary with the overall score and each category score on its scale.

**Why this priority**: Fewer people use it, but today it is unstyled plain text, and it is less complete than the email it is attached to.

**Independent Test**: Email reports for two generic assessments, one with richer mentor-report data and one without. Check each PDF's layout and branding.

**Acceptance Scenarios**:

1. **Given** a generic assessment with mentor-report data, **When** its report is emailed with a PDF, **Then** the attachment uses the full mentor report layout.
2. **Given** a generic assessment with only basic scores, **When** its report is emailed with a PDF, **Then** the attachment shows the brand header with the assessment's name, the overall score and each category with a visual bar.
3. **Given** a master assessment with no mentor-report data, **When** its report is emailed with a PDF, **Then** the attachment uses the same branded summary layout instead of plain text.

---

### Edge Cases

- An apprentice with no name on file: the header shows "Apprentice" and the file name is unchanged from today.
- Every gift scores 0, or all gifts tie: the ranked list still renders. The top section shows the first three by name order and notes the ties, without an unbounded number of deep dives (at most 6 deep dives; the rest are listed by name as "also tied").
- A gift with no definition record for the assessment's version: the gift still appears, with its summary or definition omitted, and the PDF still renders.
- Very long AI text (several thousand characters in one field): it flows across pages without being clipped or overlapping the header or footer.
- A missing logo or font file on the server: the PDF still renders with fallback fonts and a text wordmark.
- The assessment's submitted date is missing: the date the PDF was generated is used, labeled as such.

## Requirements *(mandatory)*

### Functional Requirements

**Shared brand system (all PDFs)**

- **FR-001**: Every PDF MUST use one shared visual system:
  - a charcoal header band on the first page with the T[root]H logo, the report title in gold and a subtitle with the person's name and a human-readable date
  - a slim branded strip on later pages
  - white body pages
  - gold accents
  - a footer with the correct T[root]H website and "Page X of Y".
- **FR-002**: Colors MUST come only from the brand palette, which matches the app and spec 005 emails: charcoal #1a1a1a/#222222, gold #d4af37, neutral greys, and a muted status set used only for status cues.
- **FR-003**: Text MUST use the app's typeface when it is available, with a clean fallback otherwise.
- **FR-004**: Any user- or AI-supplied text MUST be shown literally. Characters such as "&", "<", ">" and quotes MUST NOT break generation or be read as formatting.
- **FR-005**: Characters the PDF fonts cannot draw (emoji and similar) MUST NOT appear as boxes. They MUST be removed or replaced by drawn icons or text labels.
- **FR-006**: If full rendering fails, the system MUST still return a valid PDF with the essentials. It MUST never send non-PDF content as a PDF attachment or download.
- **FR-007**: Dates MUST be shown in a human-readable form (for example "October 13, 2026"). Internal version numbers and machine timestamps MUST NOT be shown.

**Spiritual Gifts PDF**

- **FR-008**: The gifts PDF MUST contain these sections in order:
  1. header
  2. a short introduction to spiritual gifts and how to read the scores
  3. "Your top gifts"
  4. a deep dive per top gift
  5. all gifts ranked
  6. next steps.
- **FR-009**: Every score MUST be shown against its 0–12 scale, both as "N/12" and as a visual bar.
- **FR-010**: Ties at 3rd place MUST be shown and labeled "Tied for 3rd", and tied gifts MUST get deep dives, up to 6 deep dives in total.
- **FR-011**: Each deep dive MUST include the gift's definition, 2–3 scripture references, at least three practical ways to use the gift and one reflection question.
- **FR-012**: The system MUST hold the scripture, ways-to-serve and reflection content for all 24 gifts. Content for every gift in the assessment MUST be present. The product owner reviews the wording before release.
- **FR-013**: The ranked list MUST show all 24 gifts in score order (ties broken by name), each with its one-line summary. It MUST group them into Strongest (9–12), Developing (5–8) and Less evident (0–4), and visually highlight the top gifts.
- **FR-014**: Gift summaries and content MUST match every gift reliably, whatever the spacing or punctuation of its name (for example "Pastor/Shepherd" vs "Pastor / Shepherd").
- **FR-015**: The gifts PDF MUST NOT print the full definitions of all 24 gifts. Full definitions stay in the app.
- **FR-016**: Mentor- or admin-sent gifts PDFs MUST name the apprentice and show the apprentice's assessment date.
- **FR-017**: The gifts PDF MUST end with next steps that refer to the person's top gift (for example, talking with a mentor and trying a specific way to serve).

**Mentor / Master report PDF**

- **FR-018**: The mentor report PDF MUST keep every section and data point it shows today, including all premium sections when premium content exists, restyled in the shared system.
- **FR-019**: Headline scores MUST be shown in a highlighted card, and category and knowledge scores MUST show their scale with a visual bar.
- **FR-020**: Strengths and growth areas MUST appear side by side in brand-styled cards.

**Generic assessment PDF**

- **FR-021**: When an assessment has mentor-report data, its emailed PDF MUST use the mentor report layout (FR-018 to FR-020).
- **FR-022**: Otherwise, the PDF MUST show a branded summary: the assessment's name as the title, the overall score in a highlighted card, and each category score with its scale and a bar. Master assessments with no mentor-report data MUST use this same layout.

**Compatibility**

- **FR-023**: Endpoints, request bodies, response bodies, attachment file names and authorization rules MUST stay unchanged.
- **FR-024**: The HTML report (sent when `include_html` is requested) MUST use the same gift ordering and summary matching as the PDF.

### Key Entities

- **Gift guidance**: per-gift reference content, keyed by gift: scripture references (2–3), ways to use the gift (3+), and a reflection question. It covers all 24 gifts and is shipped with the product, not edited by users.
- **Report document**: a generated PDF for a person and an assessment, with a title, subject name, assessment date and a sequence of branded sections.

### Access, Compatibility & Clients *(mandatory)*

- **Roles**: unchanged.
  - Gifts PDF: the apprentice (self) and a mentor linked to the apprentice or an admin.
  - Mentor report PDF: the apprentice owner or their mentor.
  - Generic PDF: unchanged existing rules.
- **Ownership**: unchanged. A mentor sees only actively linked apprentices.
- **Premium**: unchanged. Premium sections appear only when premium content exists and the requester is entitled to it today.
- **Compatibility**: purely a change to the output's appearance and content. Nothing is added, removed or renamed in the API, so no minimum app version is needed.
- **Frontend**: none. The existing "Email PDF" and "Share PDF" actions keep working unchanged.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of generated PDFs open as valid PDFs in standard viewers (iOS Files, Mail and Preview), including reports whose text contains "&", "<", ">", quotes or emoji.
- **SC-002**: 0 missing-glyph boxes and 0 off-palette colors across sample renders of all three PDF types.
- **SC-003**: All 24 gifts show a one-line summary in the ranked list for 100% of gifts reports (today 2 of 24 can be missing).
- **SC-004**: 100% of mentor-sent gifts PDFs name the apprentice (today 0%).
- **SC-005**: Every top gift in a gifts report has a definition, scripture, ways to serve and a reflection question.
- **SC-006**: A reader can name their top three gifts and one next step within 30 seconds of opening the gifts PDF. The product owner checks this with a review of the sample renders.
- **SC-007**: Generating a PDF does not noticeably slow the email or share actions (it stays within a couple of seconds, as today).

## Assumptions

- The brand palette and logo are the ones already used by the spec 005 email templates and the app. The black-background "T[root]H Discipleship" logo is used on the charcoal band.
- The correct public website for the footer is the configured app landing site (onlyblv.com), not "troothapp.com".
- Gift guidance content is written by the implementer, drawing on widely used biblical gift passages (Romans 12, 1 Corinthians 12–14, Ephesians 4, 1 Peter 4). The product owner reviews it before release, and a content change is a code change.
- Strength band thresholds (9–12 / 5–8 / 0–4) are a reasonable default for 3 questions per gift scored 0–4.
- Only the visual layout and the content of the PDFs change. Email bodies (spec 005) and the in-app screens are out of scope.
- PDFs are rendered on US Letter pages, as today.
