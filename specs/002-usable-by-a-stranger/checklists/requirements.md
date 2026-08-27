# Specification Quality Checklist: Usable by a stranger

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-27
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

Two items were resolved by informed guess rather than by asking, and both are recorded in
*Assumptions* rather than left implicit:

- **Where search runs.** ADR-0004 forbids a library on the page, so the page cannot query
  SQLite. The page searches what it has already loaded; the command line queries the FTS5
  table v0.1 populates. The alternative — shipping descriptions into the page payload and
  making FTS5 purely for external consumers — is viable, and is a planning decision rather
  than a specification one, because both satisfy every requirement here.
- **Single screen replaces, not joins.** Old addresses break on republish. FR-003 exists to
  make the new addresses shareable, and the assumption states the cost plainly instead of
  hiding it.

Three named boundaries carry risk worth restating at planning time:

- **SC-008 is owed, not new.** It arrives from v0.1 unmet, and the criterion itself may be
  the thing that needs rewriting: it names an account size no one here has.
- **The frame budget is already breached in the Author's own full build** — 3,283 nodes,
  roughly 70 ms per frame while the layout settles. SC-007 asks v0.2 not to make it worse.
  A plan that adds per-frame work to the single screen has to say how it stays inside that.
- **Four stories, four surfaces.** The single screen touches the views, search touches the
  views and the CLI, the Tool profile touches the views, and the fork path touches the
  README and the template. Only the single screen blocks the others.

Two requirements are prohibitions rather than capabilities — FR-019 and FR-020 — and are
here deliberately. This release reaches what v0.1 records; a plan that needs a rescan or a
new node type has misread the spec.
