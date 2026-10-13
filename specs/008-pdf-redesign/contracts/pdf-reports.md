# Contract: PDF Reports

## HTTP surface: unchanged

None of these endpoints change their method, path, request body, response body, status codes, authorization or attachment filename. Only the bytes of the PDF change.

| Endpoint | PDF source | Attachment / filename |
|---|---|---|
| `POST /assessments/spiritual-gifts/email-report` | Spiritual Gifts | `spiritual_gifts_report_{name}_{YYYYMMDD}.pdf` |
| `POST /assessments/spiritual-gifts/{apprentice_id}/email-report` | Spiritual Gifts | same |
| `GET /assessments/{assessment_id}/mentor-report-v2.pdf` | Mentor report | `mentor_report_{name}_{id8}.pdf` (download) |
| `POST /assessments/{assessment_id}/email-report` | Mentor report | `mentor_report_{name}_{YYYYMMDD}.pdf` |
| `POST /assessments/master-trooth/email-report` | Mentor report (v2 data), else Generic summary | unchanged |
| `POST /assessments/master-trooth/{apprentice_id}/email-report` | same | unchanged |
| `POST /templates/{template_id}/email-report` | Mentor report (v2 data), else Generic summary | unchanged |
| `POST /templates/{template_id}/{apprentice_id}/email-report` | same | unchanged |

`EmailReportResponse.pdf_bytes` still reports the byte length.

## Output guarantee (all PDFs)

- The body starts with `%PDF-` and ends with `%%EOF`, even when rendering fails (FR-006).
- Content type is `application/pdf`. Page size is US Letter.

## Renderer interfaces (internal, used by routes and tests)

```text
spiritual_gifts_report.generate_pdf(apprentice_name, version, scores, definitions, *, assessment_date=None) -> bytes
spiritual_gifts_report.build_gifts_story(apprentice_name, scores, definitions) -> list[Flowable]
master_trooth_report.render_pdf_v2(context) -> bytes            # unchanged signature
master_trooth_report.build_mentor_story(context) -> list[Flowable]
master_trooth_report.generate_pdf(apprentice_name, scores) -> bytes   # kept name; delegates to generic summary
generic_assessment_report.generate_pdf(title, apprentice_name, scores, *, assessment_date=None) -> bytes
generic_assessment_report.build_generic_story(title, scores) -> list[Flowable]
```

## Content contract: Spiritual Gifts PDF

Sections in order:
1. **Band**: logo, "Spiritual Gifts Report", "{name} · {Month D, YYYY}".
2. **Intro** (≤ 3 sentences): what gifts are, with 1 Cor 12:4–7 and 1 Pet 4:10, and how to read the 0–12 scores.
3. **Your top gifts**: up to 3 dark cards with rank, name, `N/12` and a bar. "Tied for 3rd: …" when the expanded set is larger than the truncated one.
4. **Deep dives**: one per expanded top gift (cap 6). Each has a heading (`#rank Name · N/12`), the definition, an "In Scripture" callout, a "Ways to use this gift" list (≥ 3) and a "Reflect" callout.
5. **All gifts ranked**: 24 rows in three bands (Strongest 9–12 / Developing 5–8 / Less evident 0–4). Each row has rank, name, a bar, `N/12` and the summary. Top rows are tinted.
6. **Next steps**: 3 bullets, built from the #1 gift. A closing reference: Romans 12:6.

Must not contain: "Truncated", "Expanded", "Version", ISO-8601 timestamps, or full definitions for non-top gifts.

## Content contract: Mentor report PDF

The section set is the same as today's `render_pdf_v2`, and all of it uses kit components with no emoji. The order:
1. Headline card: Health Score + band + Biblical Knowledge %, the same numbers as the spec 005 emails and the app.
2. Strengths / growth areas.
3. **Priority action**. It sits right after the headline, as it does in the report emails.
4. Category scores, then biblical knowledge. Scored topics show a bar. v2.1 weak topics with no scores appear as a "Topics to study" callout, not 0% bars.
5. Insights.
6. Premium sections: executive summary, strengths and gaps deep dives, conversation guide, biblical knowledge analysis, spiritual formation.
7. Conversation starters, four-week plan, resources.
8. Premium progress tracking, mentor prep notes, personalized resources.

## Content contract: Generic summary PDF

Band with the template name, an overall stat card, category rows with a bar and `N/10` (scale taken from the data: 10 by default), and the footer.
