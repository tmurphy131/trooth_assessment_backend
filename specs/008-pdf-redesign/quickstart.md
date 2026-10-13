# Quickstart: Validate the PDF Redesign

## Prerequisites
- Backend repo on `feature/pdf-redesign`, with `.venv` installed (`pip install -r requirements.txt`).
- `assets/fonts/Poppins-*.ttf` present.

## 1. Automated tests
```bash
.venv/bin/pytest tests/test_pdf_reports.py tests/test_spiritual_gifts_email_reports.py \
  tests/test_master_v2_reporting.py tests/test_generic_assessments_endpoints.py \
  tests/test_master_trooth_email.py tests/test_mentor_endpoints_assessments.py -q
```
Expected: all pass. The new tests cover the valid-PDF guarantee, hostile text, guidance coverage, slug matching, ties and the mentor-sent name ([contracts/pdf-reports.md](contracts/pdf-reports.md)).

## 2. Visual review
```bash
.venv/bin/python scripts/render_pdf_samples.py --out /tmp/pdf-samples
```
This writes:
- `gifts_typical.pdf`, `gifts_tie.pdf` and `gifts_all_zero.pdf`
- `mentor_basic.pdf`, `mentor_premium.pdf` and `mentor_hostile.pdf`
- `generic.pdf`

Open each PDF (or `sips -s format png` page 1) and check:
- a charcoal band with the logo, gold title, name and readable date; nothing overlaps
- only brand colors; no black boxes
- "Page X of Y" in the footer, and onlyblv.com as the site
- gifts: top cards with N/12, deep dives with scripture, ways and reflection, 24 ranked rows in bands, next steps
- `mentor_hostile.pdf` shows the `&`/`<` text literally.

## 3. End to end on dev
After `/deploy-dev`:
1. Apprentice: Spiritual Gifts results → **Email PDF**. Open the attachment on iOS Mail.
2. Mentor: an apprentice's Spiritual Gifts → **Email PDF**. The PDF names the apprentice.
3. Apprentice report → **Share PDF**. Opens in Files.
4. A generic assessment → email the report with a PDF.
