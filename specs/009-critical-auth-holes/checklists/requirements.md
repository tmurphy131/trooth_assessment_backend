# Specification Quality Checklist: Close Critical Authorization Holes

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-13
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Validation passed on the first iteration.
- The Compatibility section names the two unused frontend client functions (`parentSignAgreement`, `assignApprentice`) on purpose. This repo's spec template requires stating client impact, and they are why no minimum app version is needed.
- Scope decision (no clarification needed): FR-007 (verified email for legacy re-link) extends finding 1 to the matching path in signed-in requests, because it is the same account-takeover class.
- Behavior change to confirm in review: re-registering can no longer correct a wrong stored role (edge cases). This is intentional and matches the app's "role chosen once" rule.
- `/speckit-analyze` (2026-10-14) found 0 critical issues; all 7 findings were fixed at the source:
  - **I1:** US1 scenario 4 now ignores the body email.
  - **I2:** FR-005 and scenario 3 are limited to new accounts.
  - **C1:** SC-006 reworded to what can be detected, with R8 and task T014 added (log query).
  - **C2:** added T008, a Postgres test for the blocked re-link.
  - **U1:** FR-013 now requires a generic 409 message, with a test case.
  - **U2:** the tests now patch `firebase_admin.auth` directly.
  - **F1:** documented that `assign-apprentice` now returns 405.

  Tasks were renumbered T001–T016 in execution order.
