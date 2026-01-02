# Spiritual Gift Assessment — Specification and Implementation Requirements

Note: This document defines requirements only. No code changes are included here.

## 1) Overview & Goals

Purpose: Provide a Spiritual Gifts assessment that identifies each apprentice’s top spiritual gifts and presents a tailored report for apprentices and mentors.

High-level goals:
- Implement this assessment as a new template in the application.
- Use the response scale defined below (Likert 0–4) and compute scores per gift (3 items per gift).
- Generate a custom “Spiritual Gifts Report” (distinct from other assessments):
  - Include a short description of what this assessment measures.
  - Show the Top 3 highest-scoring gifts (with tie handling at the 3rd rank).
  - Show a full list of all 24 gifts with score and the gift definition under each name.
- Surface the report in two places:
  - Apprentice Dashboard → Progress section.
  - Mentor Dashboard → Assessments section (report must include apprentice name).

Template identity and versioning:
- Template key: spiritual_gifts_v1 (proposed)
- Version: 1 (include internal versioning to allow future updates to questions/definitions)
- Official assessment: Admin-managed only (same policy as the Master T[root]H Discipleship). Published versions are read-only for non-admins.

Submission rule:
- All 72 items must be answered (required). If partial submission is allowed in future, treat missing items as 0 and flag report as “Incomplete.”

Report description (display at top of report):
- “This Spiritual Gifts Assessment helps identify the ways God has uniquely equipped you to serve the church and others. Results highlight your strongest gifts and provide definitions to help you understand and apply them.”

## 2) Gift Categories (24)

1. Leadership  
2. Pastor/Shepherd  
3. Discernment  
4. Exhortation  
5. Hospitality  
6. Prophecy  
7. Knowledge  
8. Miracles  
9. Healing  
10. Helps  
11. Mercy  
12. Evangelism  
13. Faith  
14. Teaching  
15. Wisdom  
16. Intercession  
17. Service  
18. Tongues & Interpretation  
19. Giving  
20. Missionary  
21. Apostleship  
22. Craftsmanship  
23. Administration  
24. Music/Worship

## 3) Response Scale (Likert)

- **0 = Never true**  
- **1 = Rarely true**  
- **2 = Sometimes true**  
- **3 = Often true**  
- **4 = Very often true**

## 4) Questionnaire — Scrambled Item Order (72 statements)

> **Format:** `Q##. [Gift] — statement` (the bracketed gift is not shown to the end‑user in production UI)

1. **Q01. Wisdom** — I offer practical, Christlike solutions from Scripture.  
2. **Q02. Hospitality** — I enjoy creating warm, welcoming spaces for people.  
3. **Q03. Evangelism** — I naturally guide conversations toward the gospel.  
4. **Q04. Leadership** — People look to me for direction when plans are unclear.  
5. **Q05. Faith** — My faith often inspires courage in others.  
6. **Q06. Helps** — I willingly do unnoticed tasks to meet needs.  
7. **Q07. Teaching** — People say I make complex ideas understandable.  
8. **Q08. Prophecy** — I boldly speak Biblical truth to bring clarity.  
9. **Q09. Craftsmanship** — I enjoy building/making things that serve ministry.  
10. **Q10. Pastor/Shepherd** — I check in on people’s well‑being and follow up consistently.  
11. **Q11. Intercession** — I maintain prayer lists and pray with expectancy.  
12. **Q12. Mercy** — I feel deep compassion for those in pain.  
13. **Q13. Knowledge** — I connect Scriptures to explain complex situations.  
14. **Q14. Administration** — I track details so teams deliver reliably.  
15. **Q15. Music/Worship** — I steward musical/creative skills for God’s glory.  
16. **Q16. Healing** — I’m drawn to minister to the sick and hurting.  
17. **Q17. Service** — I prefer doing what’s needed over being noticed.  
18. **Q18. Giving** — I enjoy resourcing ministry beyond the minimum.  
19. **Q19. Discernment** — I often perceive motives behind words or actions.  
20. **Q20. Missionary** — I adapt to new environments for the gospel.  
21. **Q21. Tongues & Interpretation** — I pray in a spiritual language privately.  
22. **Q22. Exhortation** — I encourage others with timely, Scripture‑rooted words.  
23. **Q23. Leadership** — I align tasks and people to keep the big picture in focus.  
24. **Q24. Faith** — I confidently trust God for unseen outcomes.  
25. **Q25. Miracles** — I expect God to act beyond natural limitations.  
26. **Q26. Service** — I organize my time to consistently meet tangible needs.  
27. **Q27. Exhortation** — I help others take practical next steps of faith.  
28. **Q28. Craftsmanship** — I plan and execute hands‑on projects well.  
29. **Q29. Prophecy** — I sense timely messages God wants emphasized.  
30. **Q30. Pastor/Shepherd** — I’m drawn to nurture those working through life issues.  
31. **Q31. Music/Worship** — I lead or support musical worship effectively.  
32. **Q32. Helps** — I feel satisfied when practical work enables the mission.  
33. **Q33. Intercession** — I feel burdened to pray until breakthrough comes.  
34. **Q34. Evangelism** — I explain salvation clearly to non‑Christians.  
35. **Q35. Administration** — I design systems that make work efficient.  
36. **Q36. Giving** — I plan my finances to give generously to God’s work.  
37. **Q37. Discernment** — I can identify truth from error in confusing situations.  
38. **Q38. Wisdom** — I can apply Biblical principles fruitfully in grey areas.  
39. **Q39. Miracles** — I have prayed and seen outcomes shift in remarkable ways.  
40. **Q40. Teaching** — I enjoy studying and communicating Biblical truth.  
41. **Q41. Knowledge** — I often clarify confusion by bringing relevant truth.  
42. **Q42. Hospitality** — I notice newcomers and help them feel at home.  
43. **Q43. Mercy** — I advocate for the vulnerable and overlooked.  
44. **Q44. Leadership** — I naturally motivate groups to move toward a clear vision.  
45. **Q45. Missionary** — I build relationships that cross cultural boundaries.  
46. **Q46. Faith** — I choose obedience even when results aren’t visible.  
47. **Q47. Healing** — I pray for physical/mental healing with persistent faith.  
48. **Q48. Pastor/Shepherd** — I notice and respond to spiritual and emotional needs.  
49. **Q49. Tongues & Interpretation** — Praying in tongues is encouraging and important to me.  
50. **Q50. Service** — I’m quick to volunteer for practical tasks.  
51. **Q51. Miracles** — Others seek my faith when situations appear impossible.  
52. **Q52. Intercession** — I regularly “stand in the gap” for people in prayer.  
53. **Q53. Prophecy** — I feel compelled to confront error with Scripture.  
54. **Q54. Apostleship** — I thrive in breaking new ground for the church.  
55. **Q55. Exhortation** — People say my feedback lifts and directs them.  
56. **Q56. Knowledge** — I retain Biblical facts and contexts that help others.  
57. **Q57. Helps** — I enjoy supporting others so ministry succeeds.  
58. **Q58. Music/Worship** — I help others engage God through music/arts.  
59. **Q59. Discernment** — I sense when something sounds off spiritually or doctrinally.  
60. **Q60. Administration** — I organize people and tasks to hit goals.  
61. **Q61. Apostleship** — I start or pioneer new ministries.  
62. **Q62. Hospitality** — I think about details that make gatherings comfortable.  
63. **Q63. Healing** — People report healing after I intercede for them.  
64. **Q64. Giving** — I notice strategic opportunities to fund Kingdom impact.  
65. **Q65. Evangelism** — I actively look for opportunities to share Jesus.  
66. **Q66. Teaching** — I structure content so others understand Scripture.  
67. **Q67. Apostleship** — I recruit and equip teams to launch new work.  
68. **Q68. Wisdom** — People seek my counsel for next steps.  
69. **Q69. Craftsmanship** — I contribute skilled work (sets, spaces, tools).  
70. **Q70. Tongues & Interpretation** — God uses me to interpret what someone speaking in tongues is saying.  
71. **Q71. Missionary** — I’m drawn to reach people of different cultures.  
72. **Q72. Mercy** — I sit with people in their suffering without rushing them.  

---

## 5) Scoring Specification

- **Per‑gift score** = sum of its 3 items → range **0–12**.  
- **No weighting** and **no reverse scoring**.  
- **Top Gifts (reporting):** sort descending by per‑gift score; show **Top 3** with tie handling (include all ties at the 3rd place boundary).

### Item→Gift MAP (canonical for this scrambled order)

```python
MAP = {
  "Leadership": ['Q04', 'Q23', 'Q44'],
  "Pastor/Shepherd": ['Q10', 'Q30', 'Q48'],
  "Discernment": ['Q19', 'Q37', 'Q59'],
  "Exhortation": ['Q22', 'Q27', 'Q55'],
  "Hospitality": ['Q02', 'Q42', 'Q62'],
  "Prophecy": ['Q08', 'Q29', 'Q53'],
  "Knowledge": ['Q13', 'Q41', 'Q56'],
  "Miracles": ['Q25', 'Q39', 'Q51'],
  "Healing": ['Q16', 'Q47', 'Q63'],
  "Helps": ['Q06', 'Q32', 'Q57'],
  "Mercy": ['Q12', 'Q43', 'Q72'],
  "Evangelism": ['Q03', 'Q34', 'Q65'],
  "Faith": ['Q05', 'Q24', 'Q46'],
  "Teaching": ['Q07', 'Q40', 'Q66'],
  "Wisdom": ['Q01', 'Q38', 'Q68'],
  "Intercession": ['Q11', 'Q33', 'Q52'],
  "Service": ['Q17', 'Q26', 'Q50'],
  "Tongues & Interpretation": ['Q21', 'Q49', 'Q70'],
  "Giving": ['Q18', 'Q36', 'Q64'],
  "Missionary": ['Q20', 'Q45', 'Q71'],
  "Apostleship": ['Q54', 'Q61', 'Q67'],
  "Craftsmanship": ['Q09', 'Q28', 'Q69'],
  "Administration": ['Q14', 'Q35', 'Q60'],
  "Music/Worship": ['Q15', 'Q31', 'Q58'],
}
```

## Appendix A — Gift Definitions with Scripture References

## 6) Report Requirements (Output Format)

Audience: Apprentice (primary), Mentor (secondary).

Sections:
1. Header
   - Title: “Spiritual Gifts Report”
   - Apprentice name (mentor view must include apprentice name)
   - Assessment date/time
   - Template version (e.g., v1)
   - Short description (see Overview)
2. Top Gifts
   - Display Top 3 gifts by score (0–12)
   - Tie handling: include all gifts that tie at the 3rd rank
   - For each gift: show Gift Name, Score, one-sentence summary from its definition
3. Full Results
   - List all 24 gifts, sorted by score (desc)
   - For each gift: Gift Name, Score, Full Definition (from Appendix A)
4. Footer (optional)
   - Suggest next steps (e.g., discuss with mentor, opportunities to serve)

Accessibility and responsiveness:
- Ensure headings and structure for screen readers.
- Mobile-friendly layout; definitions collapse/expand on small screens.

Export and email delivery (required):
- Generate a printable PDF of the Spiritual Gifts Report that includes the full content (header, Top 3, full results with definitions).
- From Apprentice Dashboard → Progress → Report view: provide an action “Email me this report (PDF)” that sends the PDF to the signed-in apprentice’s email.
- From Mentor Dashboard → Assessments → Report view: provide an action “Email me this report (PDF)” that sends the PDF to the signed-in mentor’s email. (Emailing to others is out of scope for v1.)
- Email details:
  - Subject: “Spiritual Gifts Report — <Apprentice Name> — <YYYY-MM-DD>”
  - Body: brief explanation and link back to the app (if applicable).
  - Attachment filename: spiritual_gifts_report_<apprentice_name>_<yyyyMMdd>.pdf
  - PDF content must match the on-screen report exactly (including template version and date).
  - Delivery via backend mail service (existing email infra), respecting rate limits and error handling.

  ### PDF Design — Header and Footer Style

  Header:
  - Left: App logo (monochrome or full-color, 24–28px height), aligned with page margin.
  - Center: Title “Spiritual Gifts Report” (H1, 18–20pt, bold).
  - Right: Apprentice Name (mentor view), Assessment Date (YYYY‑MM‑DD), and Template Version (v1) stacked in small caps (9–10pt). On apprentice self-view, show just Date and Version.
  - Below header: a thin divider line (#E0E0E0) across full width.

  Footer:
  - Left: “Generated by T[root]H Discipleship” (8–9pt, muted #666).
  - Center: Page X of Y.
  - Right: Report ID (or short hash) for reference, e.g., RPT‑SG‑20250912‑AB12 (8–9pt).

  Typography & spacing:
  - Body font: Inter, Roboto, or system sans (10–11pt); Headings: 1.2× scaling.
  - Color palette: primarily black (#000) and dark gray (#333); use accent (#FFB300 / similar amber) for gift name headers and Top 3 badges.
  - Section spacing: 12–16pt margins between major sections; 6–8pt between items.
  - Tables or lists should avoid splitting a single gift’s name/score/definition across pages when possible (keep with next rule).

  Top 3 visual treatment:
  - Each Top Gift displayed as a card-like block with subtle border or background tint (#FFF8E1) with Gift Name (bold), Score (badge), and 1‑line summary.

  Full list formatting:
  - Sorted by score (desc). Each gift entry includes: Name (bold), Score (badge), Definition paragraph(s).
  - Use a small divider or ample whitespace between gift entries for readability.

  Page setup:
  - Margins: 0.75in (top/bottom), 0.6in (left/right). Header/Footer within margin.
  - Avoid orphan/widow lines for definition paragraphs where supported.

## 7) Placement in App (UX Integration)

Apprentice dashboard → Progress section:
- Show latest Spiritual Gifts Report card with: title, date, and top 3 gifts preview.
- Tap opens full report view.
 - In the report view, include an “Email me PDF” action.

Mentor dashboard → Assessments section:
- For each apprentice with a completed Spiritual Gifts Report, list an entry with apprentice name, date, and top 3 gifts preview.
- Tap opens full report for that apprentice.
 - In the report view, include an “Email me PDF” action for the mentor.

Empty states:
- If not yet completed: show a call-to-action to start the Spiritual Gifts Assessment.

## 8) Data Model & API Requirements (Conceptual)

Template:
- template_key: spiritual_gifts_v1
- item_ids: Q01–Q72

Submission payload (conceptual JSON):
```json
{
  "template_key": "spiritual_gifts_v1",
  "answers": {
    "Q01": 0, "Q02": 3, "Q03": 2, 
    "...": 1
  }
}
```

Server-side compute requirements:
- Validate all 72 items present (0–4 integer values).
- Compute per-gift sums (range 0–12) using the MAP above.
- Identify top 3 gifts (with tie handling) and produce sorted full list.
- Store result with apprentice_id, computed scores, and template version.

Result shape (conceptual JSON):
```json
{
  "id": "result-uuid",
  "apprentice_id": "uid",
  "template_key": "spiritual_gifts_v1",
  "version": 1,
  "created_at": "2025-09-12T10:15:00Z",
  "top_gifts": [
    {"gift": "Wisdom", "score": 11},
    {"gift": "Faith", "score": 10},
    {"gift": "Teaching", "score": 10}
  ],
  "scores": [
    {"gift": "Wisdom", "score": 11, "definition": "..."},
    {"gift": "Faith", "score": 10, "definition": "..."},
    {"gift": "Teaching", "score": 10, "definition": "..."},
    {"gift": "Leadership", "score": 9, "definition": "..."}
    // all 24 gifts
  ]
}
```

Security & auth:
- Apprentice can view their own report(s).
- Mentor can view reports for their assigned apprentices.
- Admin-only editing of this template: Only Admins can create/update/delete the Spiritual Gifts template (including questions, definitions, and the item→gift MAP) and publish new versions. Non-admin attempts must be rejected with 403 Forbidden.
- Version governance: Once a version is published, it is immutable for all roles except Admin creating a new version; prior versions remain view-only.
 - Emailing PDF: Only the currently signed-in viewer may email themselves a copy. No cross-user email in v1. Requests must be authorized.

Caching (optional):
- Cache computed report for fast repeat viewing; invalidate on any re-submission.

## 9) Acceptance Criteria

Functional:
- Given a fully answered submission, the system produces per-gift scores that match the MAP and 0–4 scale.
- Top 3 section includes ties correctly.
- Full list includes all 24 gifts with correct scores and definitions.
- Apprentice sees the report in Progress; Mentor sees it in Assessments with apprentice name.
- Only Admin users can modify template content or publish a new version; non-admin attempts result in 403 Forbidden.
- “Email me PDF” is available and functional for both apprentices (in Progress report view) and mentors (in Assessments report view), sending to the signed-in user’s email with correct attachment and subject.

Validation:
- Reject out-of-range answers; explain 0–4 allowed.
- If answers missing and partial submissions are blocked: return a clear validation error.

UX:
- Definitions readable on mobile; long text truncates with expand.
- Title, date, and name visible at the top (mentor view shows apprentice name).

Non-functional:
- Compute on server within < 500ms p95 for typical loads (excluding network latency).
- Handle concurrent submissions safely.

## 10) Edge Cases & Rules

- Tie handling at rank 3: include all gifts that share the 3rd-place score.
- If multiple submissions exist, surfaces the most recent in dashboards; provide a way to view history (optional/future).
- If definitions update in future versions, store and show definition matching the version used.

## 11) Internationalization (Future)

- All user-facing strings should be localizable.
- Keep gift names/definitions in a structure that supports multiple languages.

## 12) Open Questions

1. Should apprentices be able to re-take and replace the prior report, or keep history? (Default: keep history.)
2. PDF export needed in v1? (Default: not required.)
3. Any admin review tools required (e.g., export CSV of scores)?


- **Leadership** — divine strength to influence people while focusing on vision/big picture. **Refs:** Romans 12:8; 1 Timothy 3:1‑13, 5:17; Hebrews 13:17.  
- **Pastor/Shepherd** — divine strength to care for personal needs by nurturing and mending life issues. **Refs:** John 10:1‑18; Ephesians 4:11‑14; 1 Timothy 3:1‑7; 1 Peter 5:1‑3.  
- **Discernment** — divine strength to identify falsehood and distinguish between right/wrong motives and situations. **Refs:** Matthew 16:21‑23; Acts 5:1‑11, 16:16‑18; 1 Corinthians 12:10; 1 John 4:1‑6.  
- **Exhortation** — divine strength to encourage others through written/spoken word rooted in Biblical truth. **Refs:** Acts 14:22; Romans 12:8; 1 Timothy 4:13; Hebrews 10:24‑25.  
- **Hospitality** — divine strength to create warm, welcoming environments (home/office/church). **Refs:** Acts 16:14‑15; Romans 12:13, 16:23; Hebrews 13:1‑2; 1 Peter 4:9.  
- **Prophecy** — divine strength to boldly speak/clarify Scriptural and doctrinal truth; sometimes foretelling God’s plan. **Refs:** Acts 2:37‑40, 7:51‑53, 26:24‑29; 1 Corinthians 14:1‑4; 1 Thessalonians 1:5.  
- **Knowledge** — divine strength to understand and bring clarity to situations, often by sharing Biblical truth. **Refs:** Acts 5:1‑11; 1 Corinthians 12:8; Colossians 2:2‑3.  
- **Miracles** — divine strength to alter natural outcomes supernaturally through prayer, faith, and divine direction. **Refs:** Acts 9:36‑42, 19:11‑12, 20:7‑12; Romans 15:18‑19; 1 Corinthians 12:10, 28.  
- **Healing** — divine strength to act in faith/prayer (often with laying on of hands) for healing of physical/mental illnesses. **Refs:** Acts 3:1‑10, 9:32‑35, 28:7‑10; 1 Corinthians 12:9, 28.  
- **Helps** — divine strength to work in supportive roles for accomplishing ministry tasks. **Refs:** Mark 15:40‑41; Acts 9:36; Romans 16:1‑2; 1 Corinthians 12:28.  
- **Mercy** — divine strength to feel empathy and care for the hurting in any way. **Refs:** Matthew 9:35‑36; Mark 9:41; Romans 12:8; 1 Thessalonians 5:14.  
- **Evangelism** — divine strength to help non‑Christians take steps toward becoming Christ followers. **Refs:** Acts 8:5‑6, 8:26‑40, 14:21, 21:8; Ephesians 4:11‑14.  
- **Faith** — divine strength to believe God for unseen, supernatural results in every arena of life. **Refs:** Acts 11:22‑24; Romans 4:18‑21; 1 Corinthians 12:9; Hebrews 11.  
- **Teaching** — divine strength to study/learn Scripture and bring understanding and growth to Christians. **Refs:** Acts 18:24‑28, 20:20‑21; 1 Corinthians 12:28; Ephesians 4:11‑14.  
- **Wisdom** — divine strength to apply scriptural truths practically, producing fruitful outcomes and Christlike character. **Refs:** Acts 6:3,10; 1 Corinthians 2:6‑13, 12:8.  
- **Intercession** — divine strength to stand in the gap for people/places by praying and believing for profound results. **Refs:** Hebrews 7:25; Colossians 1:9‑12, 4:12‑13; James 5:14‑16.  
- **Service** — divine strength to do small or great tasks for the overall good of the body of Christ. **Refs:** Acts 6:1‑7; Romans 12:7; Galatians 6:10; 1 Timothy 1:16‑18; Titus 3:14.  
- **Tongues & Interpretation** — divine strength to pray in a heavenly language to encourage the spirit and commune with God; often accompanied by interpretation and used appropriately. **Refs:** Acts 2:1‑13; 1 Corinthians 12:10, 14:1‑14.  
- **Giving** — divine strength to produce wealth and give tithes/offerings to advance God’s Kingdom on earth. **Refs:** Mark 12:41‑44; Romans 12:8; 2 Corinthians 8:1‑7, 9:2‑7.  
- **Missionary** — divine strength to reach those outside one’s culture/nationality, often while living among them. **Refs:** Acts 8:4, 13:2‑3, 22:21; Romans 10:15.  
- **Apostleship** — divine strength to pioneer churches/ministries through planting, overseeing, and training. **Refs:** Acts 15:22‑35; 1 Corinthians 12:28; 2 Corinthians 12:12; Galatians 2:7‑10; Ephesians 4:11‑14.  
- **Craftsmanship** — divine strength to plan, build, and work with hands to serve multiple ministry applications. **Refs:** Exodus 30:22, 31:3‑11; 2 Chronicles 34:9‑13; Acts 18:2‑3.  
- **Administration** — divine strength to organize multiple tasks and groups of people to accomplish them. **Refs:** Luke 14:28‑30; Acts 6:1‑7; 1 Corinthians 12:28.  
- **Music/Worship** — divine strength to sing/dance/play instruments to help others worship God. **Refs:** Deuteronomy 31:22; 1 Samuel 16:16; 1 Chronicles 16:41‑42; 2 Chronicles 5:12‑13, 34:12; Psalm 150.

---

## 13) Implementation Readiness & Gaps (Audit 2025‑09‑13)

Status: No backend implementation for this assessment currently exists (no template, endpoints, scoring code, or persistence artifacts referencing spiritual gifts). This section enumerates what must be added or clarified before coding.

### 13.1 Current Gaps vs Spec
| Area | Gap | Action |
|------|-----|--------|
| Template registration | `spiritual_gifts_v1` not present in DB | Create template record & version metadata |
| Questions storage | 72 items not persisted | Insert as template questions with stable ids (Q01–Q72) |
| MAP validation | No server validation for 24 gifts × 3 items | Add publish-time validator ensuring bijective coverage (all 72 used exactly once) |
| Gift definitions | Not version-bound | Store definitions with version or embed snapshot in template JSON |
| Submission endpoint | Missing | Add POST `/assessments/spiritual-gifts/submit` |
| Retrieval endpoints | Missing | Add latest, history, mentor-access endpoints (see 13.3) |
| Scoring logic | Not implemented | Add pure function to compute per-gift sums & top sets |
| Tie handling contract | Only implied | Formalize truncated vs expanded top lists |
| PDF generation | Not implemented | Reuse PDF service; add gift-specific layout adapter |
| Email rate limiting | Unspecified in spec | Define constraints & errors |
| History retention | Open question (#1) | Decision: keep history (each submission immutable) |
| Open question (#2) | PDF export asked if needed while earlier section mandates it | Resolve: PDF REQUIRED in v1 (question removed) |
| Security scoping | Mentor/apprentice checks not spelled out in endpoints | Document authorization matrix |
| Audit logging | Not specified | Add events for submit, view, email, publish |
| Internationalization | Future only | Define structure to allow locale expansion |
| Response shape | Single list only | Add both truncated & expanded top gifts arrays |
| Performance target | Generic (<500ms) | Refine: server scoring p95 <150ms (no AI) |
| Error codes | Not enumerated | Standardize set (400/403/404/409/429/500) |

### 13.2 Data Model Additions / Clarifications
Option A (Reuse existing `assessment_templates` & `assessments`):
- Store `template_key='spiritual_gifts_v1'` in `assessment_templates` with: version, question bank (ordered), MAP, gift definitions, published_at, is_active.
- `assessments` row: `template_id` referencing gifts template, `answers` (dict of Qxx->0–4), `scores` JSON containing computed structures.

Scores JSON recommended structure:
```jsonc
{
  "version": 1,
  "template_key": "spiritual_gifts_v1",
  "scoring_algorithm": "simple_sum_v1",
  "top_gifts_truncated": [ {"gift": "Wisdom", "score": 11}, {"gift": "Faith", "score": 10}, {"gift": "Teaching", "score": 10} ],
  "top_gifts_expanded": [ /* includes ties at rank 3 */ ],
  "all_scores": [ {"gift": "Wisdom", "score": 11}, ... 24 items ... ],
  "rank_meta": { "third_place_score": 10 },
  "definition_version": 1
}
```

Gift definition storage:
- Table or embedded JSON; if table: `gift_slug`, `display_name`, `definition`, `version`, `locale` (default `en`).
- Use slugs (e.g., `music-worship`, `tongues-interpretation`) for stable keys.

### 13.3 Required Endpoints (Proposed)
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /assessments/spiritual-gifts/submit | Apprentice | Submit answers (creates new assessment) |
| GET | /assessments/spiritual-gifts/latest | Apprentice | Latest own report (scores JSON) |
| GET | /assessments/spiritual-gifts/history?limit=N&cursor=... | Apprentice | Paginated history |
| GET | /assessments/spiritual-gifts/{apprentice_id}/latest | Mentor | Latest for assigned apprentice |
| GET | /assessments/spiritual-gifts/{apprentice_id}/history | Mentor | History (authorization check) |
| GET | /admin/assessments/spiritual-gifts/template | Admin | Fetch active template/version |
| POST | /admin/assessments/spiritual-gifts/template | Admin | Create draft/new version (unpublished) |
| POST | /admin/assessments/spiritual-gifts/template/publish | Admin | Validate + publish version |
| POST | /assessments/spiritual-gifts/{assessment_id}/email-pdf | Apprentice/Mentor | Email own copy (rate-limited) |

### 13.4 Scoring & Ordering Contract
- Validation: All 72 distinct question keys present; each value integer 0–4. Reject otherwise (400 `INVALID_ANSWERS`).
- Per-gift sum: Sum three mapped items (no weighting). Range 0–12.
- Expanded Top Gifts: Include all gifts whose score ≥ score_of_rank_3.
- Truncated Top Gifts: First three after sorting by (score DESC, gift_slug ASC) — used for dashboard card previews.
- Sorting rule globally: (score DESC, gift_slug ASC) for deterministic display.

### 13.5 Tie Handling Clarification
- Report detail uses `top_gifts_expanded` (may exceed 3 if ties at rank 3).
- Featured progress card uses `top_gifts_truncated` (exactly 3 max; no tie expansion).

### 13.6 Security & Authorization Matrix
| Role | Submit | View Own | View Apprentice | Publish Template | Email Self | Email Apprentice |
|------|--------|----------|-----------------|------------------|-----------|------------------|
| Apprentice | Yes | Yes | No | No | Yes | N/A |
| Mentor | No | N/A | Yes (assigned only) | No | Yes (mentor gets their copy of apprentice report) | No (no direct send-to-apprentice) |
| Admin | (Optional) | Any | Any | Yes | Yes | No |

### 13.7 Email & Rate Limiting
- Limit: 5 emails per user (role perspective) per hour for this assessment type.
- Error: 429 with JSON `{ "error":"RATE_LIMIT", "retry_after_seconds": 900 }`.
- Subject pattern already defined; ensure consistent with Master assessment format.

### 13.8 Logging / Audit Events
- `spiritual_gifts_submit` (apprentice_id, assessment_id, version)
- `spiritual_gifts_view` (viewer_id, assessment_id)
- `spiritual_gifts_email_request` (requestor_id, assessment_id)
- `spiritual_gifts_template_publish` (admin_id, new_version)

### 13.9 Performance Targets
- Scoring computation: p95 < 150ms (in-memory arithmetic only).
- Latest retrieval (warm cache): < 50ms server processing.

### 13.10 Error Codes & Responses
| Code | Scenario | Notes |
|------|----------|-------|
| 400 | Missing/invalid answers | Include list of offending question keys |
| 403 | Unauthorized role/action | Mentor viewing non‑assigned apprentice |
| 404 | Report/template not found | Distinguish `REPORT_NOT_FOUND` vs `TEMPLATE_NOT_FOUND` |
| 409 | Publish conflict | A published active version already exists (requires explicit retire or version bump) |
| 429 | Rate limit | See section 13.7 |
| 500 | Unexpected | Log correlation id |

### 13.11 History & Versioning
- Each submission creates immutable record; history endpoints paginate by `created_at DESC`.
- Definitions and MAP resolved at scoring time; store `definition_version` with scores JSON to guarantee replay fidelity.

### 13.12 Internationalization Preparation
- Gift definitions data model should allow multiple locales: future endpoint filter `?locale=en` (fallback to default).

### 13.13 Sample Deterministic Test Vector
Add Appendix B (future) with: (a) canonical answer set, (b) expected per-gift scores, (c) expected ordering — used for automated regression tests.

### 13.14 Implementation Checklist (Pre‑Code)
- [ ] Insert template & 72 questions.
- [ ] Implement MAP validator.
- [ ] Implement scoring function + unit tests.
- [ ] Implement submission + retrieval endpoints.
- [ ] Add PDF generation adapter (reuse styling guidelines).
- [ ] Add rate limiting middleware rule.
- [ ] Add audit logging hooks.
- [ ] Add history pagination logic.
- [ ] Add deterministic ordering tests (ties scenario).
- [ ] Add email integration test (subject, attachment naming).
- [ ] Add migration/backfill script if needed for gift slugs.

### 13.15 Resolved / Updated Open Questions
| Original Question | Resolution |
|-------------------|------------|
| #1 Retake vs replace | Keep history (immutable; latest surfaced) |
| #2 PDF export needed? | Yes, required in v1 (sections 6 & 13). Remove from open list |
| #3 Admin review tools (CSV)? | Still open (future) |

*End Section 13.*

### 14 Frontend: pre‑assessment disclaimer dialog before entering the spiritual gifts flow
This assessment works best when you respond based on your current reality, not your aspirations. If asked about prayer, answer how you actually pray now, not how you wish you prayed. Choose responses that reflect what comes naturally to you, not what you think sounds more spiritual. Avoid "should" thinking—focus on your genuine patterns and experiences. There are no right or wrong answers, only an opportunity to discover how God has uniquely gifted you.

*End Section 14*

### 15 Operational: Migration & Seeding Runbook (v1)

This section captures the concrete operational steps required to provision and maintain the Spiritual Gifts assessment (version 1) using the new `question_code` approach.

#### 15.1 Prerequisites
- Alembic migration `20250915_add_question_code` applied (adds `question_code` to `questions`).
- Python env with dependencies installed (`requirements.txt`).
- `DATABASE_URL` exported or passed via `--url`.
- Definitions JSON: `scripts/spiritual_gift_definitions_v1.json` present and validated.

#### 15.2 Environment Setup
```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/yourdb
alembic upgrade head
```

Verify schema:
```bash
psql "$DATABASE_URL" -c "\d+ questions" | grep question_code
```

#### 15.3 First-Time Seed (Definitions + Questions, Unpublished)
```bash
python scripts/seed_spiritual_gifts.py \
  --version 1 \
  --file scripts/spiritual_gift_definitions_v1.json \
  --seed-questions
```

Expected log highlights:
- Inserted gift definitions
- Inserted question Q01..Q72
- Template has all 72 questions linked ✅

#### 15.4 Publish Template
```bash
python scripts/seed_spiritual_gifts.py \
  --version 1 \
  --file scripts/spiritual_gift_definitions_v1.json \
  --seed-questions --publish
```

#### 15.5 Idempotency / Verification (No Writes)
```bash
python scripts/seed_spiritual_gifts.py \
  --version 1 \
  --file scripts/spiritual_gift_definitions_v1.json \
  --seed-questions --verify-only
```

#### 15.6 Dry Run (Preview Changes Only)
```bash
python scripts/seed_spiritual_gifts.py \
  --version 1 \
  --file scripts/spiritual_gift_definitions_v1.json \
  --seed-questions --dry-run
```

#### 15.7 Force Re-link (If Ordering/Links Corrupted)
```bash
python scripts/seed_spiritual_gifts.py \
  --version 1 \
  --file scripts/spiritual_gift_definitions_v1.json \
  --seed-questions --force-relink
```

#### 15.8 Text Update Workflow
1. Modify wording in `app/core/spiritual_gifts_map.py`.
2. Run without flag to see warnings:
   ```bash
   python scripts/seed_spiritual_gifts.py --version 1 --file scripts/spiritual_gift_definitions_v1.json --seed-questions
   ```
3. Apply updates intentionally:
   ```bash
   python scripts/seed_spiritual_gifts.py --version 1 --file scripts/spiritual_gift_definitions_v1.json --seed-questions --allow-text-update
   ```

#### 15.9 Replace Definitions (Rare)
```bash
python scripts/seed_spiritual_gifts.py \
  --version 1 \
  --file scripts/spiritual_gift_definitions_v1.json \
  --replace
```
(Add `--seed-questions` if you also want a linkage verification in the same run.)

#### 15.10 Full One-Liner (Fresh Env, Publish Immediately)
```bash
python scripts/seed_spiritual_gifts.py --version 1 --file scripts/spiritual_gift_definitions_v1.json --seed-questions --publish
```

#### 15.11 Post-Seed Verification SQL (Optional)
```sql
-- Count coded questions
SELECT COUNT(*) FROM questions WHERE question_code IS NOT NULL;

-- Ensure 72 distinct codes
SELECT COUNT(DISTINCT question_code) FROM questions;

-- Linkage count for template v1
SELECT COUNT(*)
FROM assessment_template_questions tq
JOIN assessment_templates t ON t.id = tq.template_id
WHERE t.name = 'Spiritual Gifts Assessment' AND t.version = 1;

-- Detect missing codes
WITH expected AS (
  SELECT unnest(ARRAY[
    'Q01','Q02','Q03','Q04','Q05','Q06','Q07','Q08','Q09','Q10','Q11','Q12','Q13','Q14','Q15','Q16','Q17','Q18','Q19','Q20','Q21','Q22','Q23','Q24','Q25','Q26','Q27','Q28','Q29','Q30','Q31','Q32','Q33','Q34','Q35','Q36','Q37','Q38','Q39','Q40','Q41','Q42','Q43','Q44','Q45','Q46','Q47','Q48','Q49','Q50','Q51','Q52','Q53','Q54','Q55','Q56','Q57','Q58','Q59','Q60','Q61','Q62','Q63','Q64','Q65','Q66','Q67','Q68','Q69','Q70','Q71','Q72'
  ]) AS code
)
SELECT code FROM expected e LEFT JOIN questions q ON q.question_code = e.code WHERE q.id IS NULL;
```

#### 15.12 Integrity Contract
- Exactly 72 `question_code` values exist; all unique.
- Each code appears exactly once in the template linkage for version 1.
- `MAP` (in `app/core/spiritual_gifts_map.py`) covers every code exactly once (validated on import).

#### 15.13 Troubleshooting
| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| Missing template warning on `--verify-only` | Template not yet created | Run without `--verify-only` first to create | 
| Duplicate code constraint error | Manual insert bypassed script | Delete offending row or adjust code; re-run seed |
| Drift warning (text) | Wording changed in constants | Re-run with `--allow-text-update` if intentional |
| Link count != 72 | Partial deletion/manual edits | Use `--force-relink` |
| Missing codes in SQL check | Migration/seed aborted mid-run | Re-run seed with `--seed-questions` |

#### 15.14 Future Versioning (v2+ Outline)
- Create new constants file segment (or new list) with `Q73+` or reuse codes only if semantics unchanged.
- Add new migration only if schema changes (not required for content-only version bump).
- Publish v2 template; keep v1 active for historical reports.

*End Section 15*