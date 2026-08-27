# Implementation Plan: Usable by a stranger

**Branch**: `002-usable-by-a-stranger` | **Date**: 2026-08-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-usable-by-a-stranger/spec.md`

## Summary

v0.2 reaches what v0.1 already records. One screen carrying every view, a search that reads
names and descriptions, a Tool profile, and a three-step path from someone else's archive to
your own. No new node type, no new inference, no rescan.

The technical shape follows from one measurement and one constraint. The measurement:
**46 of the 57 published Artifacts already carry a description in `graph.json`**, so the
page can search prose without a new build output. The constraint: ADR-0004 forbids a library
on the page, so the page cannot query SQLite — which settles that search is two mechanisms
(page over the loaded payload, CLI over the FTS5 table v0.1 populated) speaking one
vocabulary.

The riskiest part is not any of the four features. It is that the view layer is 1,445 lines
living inside two `<script>` tags, and merging it in one move leaves nothing to bisect if
the frame budget slips. The plan extracts before it merges.

## Technical Context

**Language/Version**: Python 3.11+, standard library only. Browser JavaScript, ES5-compatible
in-page, no build step and no transpiler.

**Primary Dependencies**: None, by constitution. `tomllib` for config, `sqlite3` for the
archive, both stdlib.

**Storage**: `store/artifacts/<id>.json` accumulates and is untouched by this release.
Derived: `graph.json`, `graph.js`, `graph.sqlite` (with the `artifact_search` FTS5 table),
`llms.txt`.

**Testing**: `unittest`, stdlib. View behaviour is verified headlessly with a jsdom harness
and an instrumented canvas that counts operations; it is a scratch tool, never a repository
dependency.

**Target Platform**: A folder of static files opened from `file://` or GitHub Pages, with
the network unplugged. Plus a local CLI.

**Project Type**: Local CLI producing a self-contained static site.

**Performance Goals**: First render under 2 s and at least 30fps while panning at 3,000
nodes (SC-007, carried from v0.1's SC-005, measured there at 182 ms and 60fps). Search
results appear while the visitor is still typing (SC-005).

**Constraints**: No server, no graph database, no CDN, no library on the page. Offline from
a file. Private Artifacts excluded by default. Public surface English, comments Portuguese.

**Scale/Scope**: 2,432 nodes in the published demo; 3,283 in the Author's own full build,
which is already past the point v0.1 named as where Barnes-Hut becomes necessary.

## Constitution Check

*GATE: passed before Phase 0. Re-checked after Phase 1 design — see below.*

| Principle | Bearing on v0.2 | Verdict |
|---|---|---|
| **I — machine proposes, Author disposes** | v0.2 adds no inference. The one place it could slip is search *ranking*: an ordering that looks like a judgement about which Artifact matters more. Ranking is by match position and then by name, both mechanical and both explainable in one sentence. `dendro search` with no FTS5 table refuses rather than degrading quietly (R6). | **Pass** |
| **II — the store accumulates** | FR-020 forbids requiring a rescan. Nothing here writes to the store. The Tool profile and search read fields already published. | **Pass** |
| **III — no server, no database, no page dependencies** | The single screen is one more static file, not fewer. Search on the page runs over the payload already in memory; the CLI's SQLite runs on the Author's machine. Every view must work from `file://` with the network unplugged (FR-004), which the quickstart tests literally. | **Pass** |
| **IV — privacy is the default** | The sharpest edge in this release. Search must not report the existence of matches it withholds (FR-009), and a Tool used only in withheld Artifacts must not appear at all — including as an address someone can guess. Both are spec edge cases and both get tests. | **Pass, with the two tests named** |
| **V — honest inference, or none** | No new inference. The Tool profile's obligation is the opposite: to state what it *cannot* claim — an unattributed span, a Tool with no claimable dates (FR-012, FR-013). | **Pass** |

**Additional constraints**: Python 3.11+ stdlib only — unchanged. `unittest` — unchanged.
English public surface, Portuguese comments — the new view modules and the CLI command
follow it. MIT — unchanged. Collectors know about repositories, the graph does not — v0.2
touches neither.

**Re-check after Phase 1**: no violation introduced. One item to carry into tasks: R7 is
open, and the decision it defers (publishing untouched Artifact ids in `indexes`) would be a
graph contract addition. It is allowed by FR-020 — derived at build time, no rescan — but it
must be written into `contracts/graph.md` if the guarding test fails on the real archive.

## Project Structure

### Documentation (this feature)

```text
specs/002-usable-by-a-stranger/
├── plan.md              # This file
├── spec.md              # The specification
├── research.md          # Phase 0 — eight decisions
├── data-model.md        # Phase 1 — what exists, what is derived, what is new
├── quickstart.md        # Phase 1 — how to prove it works
├── contracts/
│   ├── screen.md        # The single screen: views, address, selection
│   └── search.md        # `dendro search` and the page's search
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 — created by /speckit-tasks, not here
```

### Source Code (repository root)

```text
views/
├── index.html           # NEW — the shell: view selector, search field, address
├── screen.js            # NEW — view switching, selection, fragment routing
├── search.js            # NEW — the page's index over names and descriptions
├── view-graph.js        # NEW — extracted from graph.html, unchanged behaviour
├── view-timeline.js     # NEW — extracted from timeline.html, unchanged behaviour
├── view-tool.js         # NEW — the Tool profile
├── loader.js            # unchanged
├── theme.js             # unchanged
├── style.css            # extended, not rewritten
├── graph.html           # REMOVED at the end of the extraction
├── timeline.html        # REMOVED at the end of the extraction
└── fonts/               # unchanged

core/
├── search.py            # NEW — FTS5 queries over graph.sqlite
├── sqlite.py            # unchanged; `has_search` finally has a caller
├── build.py             # emit: no code change needed, the glob already carries new files
└── graph.py             # unchanged unless R7 resolves against us

cli.py                   # NEW `search` command

tests/
├── test_search.py       # NEW — CLI and page search, including what search must not say
├── test_screen.py       # NEW — the address, view switching, selection survival
├── test_tool_profile.py # NEW — claimed vs untouched, unattributed spans
└── test_view_assets.py  # extended — no view file may be named after a build output
```

**Structure Decision**: The view layer stops being two documents with inline scripts and
becomes one document with view modules. `core/` gains exactly one file. `cli.py` gains
exactly one command. Nothing in `collectors/` or `store/` moves, which is the point: v0.2 is
a reach problem, not a collection problem.

The naming prefix on view modules is not cosmetic. `core/build.emit` writes the data as
`graph.js` and then copies `views/*.js` into the same directory, so a file named
`views/graph.js` would overwrite the archive with a renderer and fail as an empty graph
rather than as a build error (R3).

## Sequencing

Four stories, but the dependency graph is narrower than it looks: only the shell blocks
anything.

```text
1. Extract view-graph.js and view-timeline.js       ← pure refactor, byte-identical output
        │
2. index.html + screen.js  (US1, P1)                ← the shell; drops the two pages
        │
        ├── 3. search.js + core/search.py + CLI (US2, P2)
        ├── 4. view-tool.js (US3, P3)
        └──   (independent) 5. three-step README (US4, P4)
```

Step 1 ships without changing what anyone sees, which is what makes step 2 bisectable. Step
5 depends on nothing here and can move if anything slips — the spec says so deliberately.

## Risks

| Risk | Why it is real | What holds it |
|---|---|---|
| **The frame budget slips on the single screen** | The graph's loop is dirty-gated but always running. Behind another view it would keep costing, and the Author's full build already runs ~70 ms per frame while settling at 3,283 nodes. | R5: the loop stops when the view is not on screen, and resumes settled. The op-counting harness measures before and after, as it did for T042. |
| **Privacy leaks through search** | "No results" and "results you may not see" are one line of code apart, and the second one discloses that private work matches a word. | FR-009, and a test that searches a term present only in a withheld Artifact's description and asserts the published site returns nothing at all. |
| **A Tool profile reachable by address for a Tool that was withheld** | The fragment is guessable — `#tool/tool:rust` — and a view that renders "not found" differently from "does not exist" leaks the difference. | One rendering for both, tested. |
| **The extraction changes behaviour by accident** | 1,445 lines moving between files, in a layer the constitution exempts from tests. | The extraction commits must produce identical headless output — same node count on screen, same label count, same op counts per frame. That harness exists. |
| **R7 resolves against us** | Row marking and the authoritative count could disagree on real data. | The guarding test runs on the real archive, not a fixture. If it fails, the fix is a documented `indexes` addition, not a quiet reconciliation. |

## Carried debt

**SC-008 arrives owed.** A ~500-repository account completing a first full scan unattended
within 30 minutes was projected from measured linearity — 68 real repositories at 3.06 s
each, 500 synthetic ones flat at 0.111 / 0.130 / 0.110 s across the run — and never
observed. v0.2 inherits it unchanged. It closes when such an account is scanned, or the
criterion is rewritten to state what can actually be observed. This plan does not schedule
work against it; it refuses to let it disappear.

## Complexity Tracking

No constitution violations. Nothing to justify.
