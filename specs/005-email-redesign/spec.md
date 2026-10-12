# Feature Specification: Email Redesign (consistent layout, report emails, working unsubscribe)

**Feature Branch**: `feature/email-redesign` | **Spec Folder**: `specs/005-email-redesign/`

**Created**: 2026-10-12

**Status**: Draft

**Input**: User description: "Email redesign: reliable, consistent, well-rendered emails across all clients (part 4 of the reports/emails plan)."

## Background

T[root]H sends about 30 kinds of email: reports to mentors, assessment and invitation notices,
agreement signing, gift seats, support replies, engagement campaigns, trivia rewards and internal
reports. They are built three different ways:

- most extend an old shared layout whose styles some mail apps strip;
- the report emails each have their own standalone design;
- a handful are written directly in code.

As a result:

- Layout, colors and footers differ from email to email.
- In some mail apps the dark design can render as white text on white, or lose its styling
  entirely.
- Buttons break in Outlook.
- No email sets the inbox preview line, so inboxes show stray text instead.
- Some emails have no plain-text version.
- Report emails don't lead with the headline numbers the app now shows (one Health Score, band
  and Biblical Knowledge percent).
- **Unsubscribe doesn't work.** Engagement emails (draft reminders, new-assessment
  announcements, re-engagement) say "unsubscribe here", but the link leads to a page that doesn't
  exist in production, and nothing records an email opt-out. People can't stop these emails, and
  major inbox providers expect a working one-click unsubscribe for this kind of mail.
- There's no way to look at an email before it goes out.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recipients can stop engagement emails in one click (Priority: P1)

A user who no longer wants reminder or announcement emails clicks "Unsubscribe" in the email, or
uses the unsubscribe button their mail app shows. They're unsubscribed straight away, without
signing in, and see a short confirmation page. From then on they get no engagement emails, but they
still get the emails that matter to their mentorship: reports, invitations, agreements, account and
support messages, and reward notices.

**Why this priority**: today's unsubscribe link is broken in production and nothing stops these
emails. That frustrates users, risks spam complaints that hurt delivery of *all* T[root]H email
(including reports), and falls short of what inbox providers require for this kind of mail.

**Independent Test**: on dev, send a draft-reminder email to a test account, click its unsubscribe
link, and confirm the page. Trigger the reminder again and see that it isn't sent, while a report
email to the same account still arrives.

**Acceptance Scenarios**:

1. **Given** an engagement email, **When** the recipient clicks its unsubscribe link, **Then** they
   see a confirmation page saying they won't get these emails anymore, without having to sign in.
2. **Given** a mail app that offers its own one-click unsubscribe control for the message,
   **When** the recipient uses it, **Then** they're unsubscribed the same way, with no page visit.
3. **Given** an unsubscribed user, **When** any engagement email would be sent to them, **Then**
   it isn't sent, and that skip is recorded.
4. **Given** an unsubscribed user, **When** a report, invitation, agreement, account, support or
   reward email is sent to them, **Then** it is delivered as normal.
5. **Given** an unsubscribe link that has been altered or belongs to no user, **When** it's
   opened, **Then** nobody's settings change and the page says the link isn't valid.
6. **Given** a user who unsubscribed by mistake, **When** they use the "resubscribe" link on the
   confirmation page, **Then** engagement emails resume.

---

### User Story 2 - Report emails lead with the same numbers as the app (Priority: P1)

A mentor gets the report email for an apprentice's assessment. The top of the email shows the
Health Score and its band. Below that come the priority action, the top strengths and growth areas,
and the Biblical Knowledge percent, all exactly as the app shows them, then one clear "Open in app"
button. A Premium mentor's email also includes the executive summary and highlights of the 12-week
plan.

**Why this priority**: report emails are the most important email T[root]H sends. They used to
show numbers that differed from the app, which undermines trust in the report.

**Independent Test**: on dev, submit an assessment for a test apprentice with a free mentor and a
Premium mentor. Compare each email's Health Score, band, Biblical Knowledge percent, strengths and
priority action with the app's report for the same assessment.

**Acceptance Scenarios**:

1. **Given** a finished assessment, **When** its report email is sent, **Then** the Health
   Score, band and Biblical Knowledge percent in the email equal the ones shown in the app for
   that assessment.
2. **Given** a Premium mentor, **When** they receive the report email, **Then** it includes the
   executive summary and 12-week plan highlights, and its Health Score matches the free email
   and the app.
3. **Given** any report email, **When** the mentor taps "Open in app", **Then** it opens a page with both
   the App Store and Google Play links for the app.
4. **Given** an assessment type without a Health Score (e.g. spiritual gifts), **When** its email
   is sent, **Then** it leads with that assessment's own headline result (e.g. top gifts) in the
   same layout.

---

### User Story 3 - Every email looks right in every major mail app (Priority: P2)

Every T[root]H email looks like the same brand: dark design, logo, readable text, a working
button, and the same footer with app links. It renders correctly in Gmail (web, iPhone, Android),
Apple Mail and Outlook, in both light and dark mode. The inbox preview line shows a helpful summary,
and mail apps that only show text get a readable plain-text version.

**Why this priority**: it affects every email, but it's about quality rather than a broken flow,
so it comes after the unsubscribe and report fixes.

**Independent Test**: send every email type to Gmail, Apple Mail and Outlook test inboxes, in light
and dark mode. Each one shows the logo, readable contrast, a working button and the shared footer.
The inbox preview line is a sentence written for that email, and each has a plain-text version.

**Acceptance Scenarios**:

1. **Given** any email type, **When** it's opened in Gmail, Apple Mail or Outlook, in light or
   dark mode, **Then** text is readable (no white-on-white or black-on-black), the logo shows,
   and the main button is visible and tappable.
2. **Given** any email type, **When** it appears in an inbox list, **Then** the preview line is a
   short summary written for that email, not leftover layout text.
3. **Given** any email type, **When** it's read in a text-only mail app, **Then** a plain-text
   version with the key content and links is shown.
4. **Given** a mail app that strips embedded styles, **When** the email is opened, **Then** the
   design (colors, spacing, button) still appears.

---

### User Story 4 - The team can preview emails before release (Priority: P3)

Before a release, someone on the team runs the email preview to see every email type rendered with
realistic sample data. If needed, they can send a test copy of one or all of them to their own
inbox.

**Why this priority**: it supports quality for every other story, but it isn't user-facing.

**Independent Test**: run the preview and get a rendered copy of every email type in a local
folder. Send one test copy to an inbox and receive it.

**Acceptance Scenarios**:

1. **Given** the preview is run, **When** it finishes, **Then** every email type has a rendered
   HTML file and a plain-text file using sample data, and the run lists any email that failed
   to render.
2. **Given** a test inbox address, **When** the preview is asked to send, **Then** the chosen
   emails arrive there marked as tests, and no real user receives anything.

---

### Edge Cases

- **Missing data in a report email** (no priority action, no strengths, or an older report with no
  Biblical Knowledge percent): the section is left out cleanly. No empty headings, "None" or zeros
  presented as results.
- **Very long names, titles or text** (apprentice names, template names, long AI text): text wraps
  and nothing overflows the layout on phone screens.
- **Images blocked** by the mail app: the email still makes sense. The logo has alt text and no
  essential information is only in an image.
- **The same user unsubscribes twice, or after already being unsubscribed**: the result is the
  same confirmation, with no error.
- **An unsubscribe link from an email sent before this feature**: old emails link to the broken
  page. That page should send people to the new unsubscribe flow, or an explanation, instead of an
  error.
- **The unsubscribe link is opened by a link-scanning security tool** (common in corporate email):
  visiting the page alone mustn't unsubscribe someone. Unsubscribing takes a deliberate action on
  the page, or the mail app's one-click unsubscribe request.
- **A test copy from the preview** must never go to anyone other than the given test address.
- **A user who deletes their account**: their opt-out record goes with the account, like other
  personal data.

## Requirements *(mandatory)*

### Functional Requirements

**Unsubscribe and email preferences**

- **FR-001**: The system MUST store, per user, whether they have opted out of engagement emails.
  The default is opted in, and existing users start opted in.
- **FR-002**: Every engagement email MUST include a visible unsubscribe link and the standard
  one-click unsubscribe information that mail apps use to show their own unsubscribe control.
- **FR-003**: The unsubscribe link MUST work without signing in, and MUST be tied to one user in
  a way that can't be guessed or changed to affect another user.
- **FR-004**: Opening the unsubscribe page MUST NOT by itself unsubscribe anyone. The user
  confirms on the page. A mail app's one-click unsubscribe request MUST unsubscribe immediately.
- **FR-005**: After unsubscribing, the user MUST see a confirmation page with a way to resubscribe.
- **FR-006**: Engagement emails MUST NOT be sent to opted-out users, and each skip MUST be
  recorded alongside the existing email send records.
- **FR-007**: Transactional emails MUST be sent regardless of the opt-out. These are report,
  assessment notices, invitations, agreement, gift seat, account, support, and trivia reward or
  prize emails.
- **FR-008**: The old unsubscribe address used in emails already sent MUST stop returning an
  error and instead lead the person to a working unsubscribe path or a clear explanation.

**Layout and rendering**

- **FR-009**: All emails MUST use one shared layout: the T[root]H dark design, logo (with alt
  text), content area, one primary button style, and a shared footer with the app link, support
  contact and the reason the person is getting the email.
- **FR-010**: The layout MUST stay readable in light and dark mode in Gmail (web, iOS, Android),
  Apple Mail and Outlook, with no low-contrast text and visible buttons. It MUST fit phone screens
  without sideways scrolling.
- **FR-011**: The design MUST still appear in mail apps that strip embedded styles.
- **FR-012**: Every email MUST have an inbox preview line written for that email, and a plain-text
  version containing its key content and links.
- **FR-013**: Every email type MUST move onto the shared layout:
  - the templated emails;
  - the standalone report emails;
  - the emails currently written directly in code (notification, gift seat, gift seat revoked,
    master report, metrics report);
  - the agreement emails.

  Who receives each email and when MUST NOT change.

**Report emails**

- **FR-014**: Report emails (mentor report, Premium report, assessment complete, generic
  assessment, master report) MUST lead with the Health Score and band. Then come the priority
  action, up to 3 strengths and up to 3 growth areas, the Biblical Knowledge percent, and one
  "Open in app" button. Each number MUST equal what the app shows for that assessment.
- **FR-015**: The Premium report email MUST add the executive summary and 12-week plan highlights,
  and its Health Score MUST match the free email and the app.
- **FR-016**: The spiritual gifts email MUST lead with the top gifts in the same layout.
- **FR-017**: Report sections with no data MUST be left out, not shown empty.

**Preview**

- **FR-018**: The team MUST be able to render every email type with realistic sample data, as HTML
  and plain text, without sending anything. The run reports any email that fails to render.
- **FR-019**: The preview MUST be able to send chosen emails to one given test address, marked as
  tests, and MUST NOT be able to send to anyone else.
- **FR-020**: Every email type MUST be covered by automated checks that it renders on the shared
  layout, has a preview line and plain-text version, and (for engagement emails) includes the
  unsubscribe link and one-click information.

### Key Entities

- **Email preference**: per user, opted in or out of engagement emails, with when it last changed
  and how (link, one-click or resubscribe). Deleted with the user.
- **Email category**: each email type is either *engagement* (can be unsubscribed from: draft
  reminder, new assessment announcement, inactive re-engagement, welcome (mentor and apprentice
  versions)) or *transactional*
  (always sent). Internal emails (metrics, admin summaries) go to staff only.
- **Unsubscribe link**: identifies one user for unsubscribing, can't be forged or reused for
  another user, and needs no sign-in.

### Access, Compatibility & Clients *(mandatory)*

- **Roles**:
  - the unsubscribe page, confirmation and one-click endpoints are **public**, authorized only by
    the signed link (Principle I: explicitly public token links);
  - the preview tool is a developer script, not an endpoint;
  - all existing email triggers keep their current access rules.
- **Ownership**: an unsubscribe link changes only the preference of the user it was issued for.
- **Premium**: no change. The Premium report email still goes only to Premium mentors.
- **Compatibility**: additive. One new per-user preference (defaults to opted in), new public
  unsubscribe pages, and the old unsubscribe address now redirects instead of returning 404. No
  existing endpoint changes, and the app needs no update.
- **Frontend**: none. The app's notification settings screen is out of scope. A later app feature
  can expose the same preference.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of engagement email types carry a working unsubscribe link and one-click
  information. On dev, unsubscribing by link and by one-click both stop the next engagement email,
  while a report email to the same account still arrives.
- **SC-002**: An unsubscribe takes at most 2 actions (open the link, confirm), with no sign-in, and
  takes effect for the next email.
- **SC-003**: In a test send of every email type to Gmail (web and iPhone), Apple Mail and Outlook,
  in light and dark mode, 100% render with readable text, the logo and a working button.
- **SC-004**: 100% of email types have a written preview line and a plain-text version.
- **SC-005**: For 5 dev assessments, the report email's Health Score, band and Biblical Knowledge
  percent match the app in 5/5. The Premium email matches the free email in 5/5.
- **SC-006**: The preview renders every email type in one run with zero failures, and a test send
  reaches only the given address.
- **SC-007**: No change in who receives which email or when, confirmed by the existing email tests
  still passing and a review of email triggers.

## Assumptions

- **Which emails can be unsubscribed from:**
  - **Engagement:** draft reminder, new assessment announcement, inactive re-engagement, welcome
    (mentor and apprentice versions).
  - **Always sent (transactional):** reports, assessment notices, invitations, agreements, gift
    seats, account and support messages, and trivia reward or prize emails. Reward emails deliver
    something the user earned, such as a prize code, so they're treated as transactional.
  - **Internal (staff only):** the metrics report and admin summaries keep their current
    recipients. They move onto the shared layout but have no unsubscribe.
- **Branding:** keep the existing dark T[root]H design and gold accent, hardened for mail apps
  (the owner chose "dark brand, hardened" during planning). The logo is the hosted logo already
  configured.
- **"Open in app"** links to the app's existing deep link, falling back to the App Store listing.
  No new deep links.
- **Test inboxes:** rendering is checked by test sends to Gmail, Apple Mail and Outlook accounts
  the team controls. A paid rendering service isn't required.
- **Email provider:** stays SendGrid. Its own unsubscribe groups aren't used, so the preference
  lives with the rest of the user's data.
- **Report numbers** come from the same source the app uses (the canonical report summary from
  spec 004), so no new scoring logic is involved.
