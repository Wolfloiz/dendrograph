---

description: "Task list for dendrograph v0.1 — git collector"
---

# Tasks: dendrograph v0.1 — git collector

**Input**: Design documents from `/specs/001-git-collector/`

**Prerequisites**: `plan.md`, `spec.md`, `contracts/`

**Tests**: Included. The constitution requires them — *"test what lies quietly, not what
crashes"* — and `plan.md` names the five heuristics that carry the risk: identity and
deduplication, authorship counting, Technique precision, accumulation, and privacy.
Rendering and the force simulation are deliberately untested.

**Organization**: Tasks are grouped by user story so each story can be implemented,
tested and delivered independently. A separate [three-agent assignment](#three-agent-assignment)
maps the same tasks onto three parallel owners.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel — different files, no dependency on an incomplete task
- **[Story]**: Which user story the task belongs to (US1–US5)
- Paths follow the tool repository layout in `plan.md`: `collectors/git/`, `core/`,
  `views/`, `templates/archive/`, `examples/`, `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Repository skeleton and the fixture harness every test depends on

- [X] T001 Create the tool repository structure — `collectors/git/`, `core/`, `views/`, `templates/archive/`, `examples/`, `tests/` — per plan.md
- [X] T002 [P] Create `pyproject.toml` declaring Python 3.11+, zero runtime dependencies and a `dendro` console entry point
- [X] T003 [P] Implement the fixture harness in `tests/support/fixtures.py` — unbundles `tests/fixtures/*.bundle` into a temp directory at setUp, removes it at tearDown
- [X] T004 [P] Build and commit the fixture repositories as `git bundle` files in `tests/fixtures/`: multi-contributor, no-commits, no-commits-no-files, two-clones-divergent, rewritten-history, barely-touched-fork
- [X] T005 [P] Create `.github/workflows/test.yml` running `python -m unittest discover` on Python 3.11 and 3.12

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The contracts in `contracts/` made real. Every user story reads or writes
through this layer.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete. This is the
serial neck of the project — see [three-agent assignment](#three-agent-assignment).

- [X] T006 Implement `core/config.py` — parse `dendrograph.toml` with `tomllib` per contracts/config.md: every table, absent config valid, unknown key is an error not a warning, no credential ever read from the file
- [X] T007 [P] Unit tests for config in `tests/test_config.py` — absent file works, unknown key rejected, a declaration naming an unknown Artifact id is reported and is not an error
- [X] T008 Implement `core/store.py` read and write per contracts/store-artifact.md — deterministic serialisation: sorted keys, two-space indent, UTF-8, trailing newline
- [X] T009 Implement `schema_version` enforcement in `core/store.py` — refuse an unrecognised version, naming the file and both versions; never partially read, never rewrite (FR-025)
- [X] T010 Implement append-merge semantics in `core/store.py` — a field the run could not observe is left as it was, never overwritten with null (FR-007, ADR-0002)
- [X] T011 [P] Unit tests for the store in `tests/test_store.py` — a run observing nothing produces a byte-identical file, an unknown `schema_version` is refused, a merge preserves prior observations
- [X] T012 [P] Implement `collectors/git/plumbing.py` — `subprocess` wrappers for root-commit enumeration, log, `ls-files`, and clone with full history and `--no-checkout`
- [X] T013 Implement root-commit identity in `core/identity.py` — id `root-<sha>`; on multiple root commits pick the earliest committer date, breaking ties on the smallest SHA (FR-004, contracts/store-artifact.md)
- [X] T014 Implement the authored-files set in `core/identity.py` — exclusions per contracts/store-artifact.md, sorted POSIX paths, each contributing `path\0size\0sha256(content)`
- [X] T015 Implement the content hash in `core/identity.py` — computed for **every** Artifact from the authored-files set, used as the id (`content-<sha>`) when there is no root commit and recorded as `identity.fallback_content_hash` otherwise, so a rewritten history can later be recognised as an existing Artifact; a repository with no commits and no tracked files is reported as unidentifiable and is **not** stored
- [X] T016 Implement identity overrides in `core/identity.py` — `[[identity.merge]]` and `[[identity.separate]]` from config always win (FR-005)
- [X] T017 [P] Unit tests for identity in `tests/test_identity.py` — two clones collapse to one Artifact, multi-root selection is deterministic, no-commits falls back, no-commits-no-files is unidentifiable, both override directions work
- [X] T018 Implement command dispatch in `cli.py` for the six commands in contracts/cli.md — `scan`, `login`, `build`, `publish`, `suggest`, `prune` (FR-020)
- [X] T019 Implement `--dry-run` and exit codes in `cli.py` — `0` success, `1` failure, `2` usage error, `3` partial success (a source was unreachable)
- [X] T020 Implement the run report in `core/report.py` — Artifacts added, Artifacts changed, sources unreachable, Artifacts withheld from output (FR-018, FR-019)
- [X] T021 [P] Unit tests for the CLI in `tests/test_cli.py` — exit code `3` on an unreachable source, `--dry-run` writes nothing
- [X] T022 [P] Verify against current GitHub documentation whether device flow must be explicitly enabled on the OAuth App, and record the finding in `docs/adr/0008-device-flow-auth-no-personal-access-token.md` — plan.md flags this as the one open external unknown

**Checkpoint**: The contracts are executable. The three streams can now fork.

---

## Phase 3: User Story 1 - See my whole archive at once (Priority: P1) 🎯 MVP

**Goal**: Point dendrograph at a GitHub account and get a browsable timeline and graph of
every Artifact it finds.

**Independent Test**: Run against an account with public repositories only, with no
credentials configured, and confirm a browsable timeline and graph are produced.

- [X] T023 [P] [US1] Implement GitHub discovery in `collectors/git/github.py` — `urllib`, pagination, unauthenticated by default and limited to public Artifacts (FR-002)
- [X] T024 [US1] Implement rate-limit degradation in `collectors/git/github.py` — report what could not be reached, never truncate silently (FR-019)
- [X] T025 [P] [US1] Implement the OAuth device flow in `collectors/git/auth.py` — public `client_id`, no secret, no redirect URI, poll until approval; token read from the environment only (ADR-0008)
- [X] T026 [US1] Implement the `gh auth token` shortcut and the CI PAT path in `collectors/git/auth.py` — convenience and CI respectively, never required (FR-003)
- [X] T027 [US1] Implement clone-and-discard in `collectors/git/clone.py` — complete history, `--no-checkout`, temporary directory removed at the end of the run, nothing cached between runs (FR-024)
- [X] T028 [US1] Implement progress reporting in `collectors/git/scan.py` — reported throughout, sized so ~500 public repositories complete unattended within 30 minutes (SC-001b)
- [X] T029 [P] [US1] Implement Tool detection in `core/analysis/tools.py` — manifest and extension markers, each carrying the evidence it was observed from
- [X] T030 [P] [US1] Implement Technique inference in `core/analysis/techniques.py` — dependency manifests and directory conventions only, each claim carrying a confidence and at least one evidence pointer; a Technique with no evidence is invalid (FR-010, SC-006)
- [X] T031 [P] [US1] Implement Dependency extraction in `core/analysis/dependencies.py` — recorded distinctly from Tools (FR-022)
- [X] T032 [US1] Implement authorship counting in `collectors/git/authorship.py` — per-author commits and lines, matched against `[archive].emails`, computed independently of identity (FR-006, FR-009)
- [X] T033 [US1] Wire `dendro scan` end to end in `collectors/git/scan.py` — discover → clone → analyse → resolve identity → write store
- [X] T034 [P] [US1] Implement `core/graph.py` — nodes and edges per contracts/graph.md, node id conventions, and the self-describing `schema` block
- [X] T035 [US1] Implement `indexes.tool_to_artifacts` in `core/graph.py` — present in v0.1 and unrendered by it, because adding it later means every Author rebuilds
- [X] T036 [US1] Implement deterministic ordering in `core/graph.py` — nodes by `(type, id)`, edges by `(type, from, to)`, so only real change dirties the archive repository
- [X] T037 [US1] Implement `core/build.py` emitting `graph.json` and `graph.js` from the same object — the `.js` wraps it in one global assignment, because a browser blocks `fetch()` from a `file://` page (FR-016)
- [X] T038 [P] [US1] Implement the shared data-loading layer in `views/loader.js` — reads `window.DENDROGRAPH_GRAPH`; one layer behind both views, not two standalone pages
- [X] T039 [P] [US1] Implement the timeline view in `views/timeline.html` — Artifacts placed by Period, no page dependencies
- [X] T040 [US1] Implement the graph view in `views/graph.html` — force simulation against a 2D canvas, no CDN and no graph library (Principle III)
- [X] T041 [US1] Make forks distinguishable in `views/graph.html` — a fork reads differently from authored work and does not inflate the Artifact count (US1 AS2, ADR-0003)
- [ ] T042 [US1] Validate SC-005 as soon as the graph view renders, in `views/graph.html` — ~500 Artifacts and ~3,000 nodes reach first render under 2 seconds and sustain at least 30fps while panning, from a page opened with no network access. Barnes-Hut is deferred to v0.3, so a failure here is a redesign and must surface now rather than in polish
  - Partially measured 2026-08-25 with a headless harness (no browser): 500 Artifacts
    produce **554 nodes**, not the ~3,000 assumed — Tool, Technique, Period, Author and
    Dependency nodes are shared across Artifacts. 4,454 edges; `graph.json` 858 KB.
    Parse + eval 13.7 ms; physics 1.57 ms/frame against a 33.3 ms budget at 30fps.
    This excludes canvas rasterisation and is **not** an fps measurement. Real browser
    validation is still outstanding. At the spec's assumed 3,000 nodes the O(n²)
    repulsion is ~30× more work and would exceed the budget — the assumption, not the
    measurement, is what carries the risk.

- [X] T043 [P] [US1] Integration test in `tests/test_dedup.py` — the same project present on two paths produces exactly one Artifact (SC-002, US1 AS3)
- [X] T044 [P] [US1] Guard test in `tests/test_no_judgement.py` — no output in any build mode contains a quality score, a grade, a complexity proof, or an AI-authorship label (FR-015, Principle V)

**Checkpoint**: A public archive renders. This is the MVP and the demo.

---

## Phase 4: User Story 2 - Rescue work that no API can reach (Priority: P1)

**Goal**: Scan local folders once and keep those Artifacts forever, after the drive dies.

**Independent Test**: Scan a local folder, confirm its Artifacts are stored, then rename
or remove the folder and re-run. The Artifacts must still be present in the graph.

- [ ] T045 [P] [US2] Implement local discovery in `collectors/git/local.py` — walk a folder for git repositories, with the same fidelity as the GitHub path (FR-001)
- [ ] T046 [US2] Implement multi-source merging in `core/store.py` — one Artifact carries every source it was seen in; neither overwrites the other (US2 AS3)
- [ ] T047 [US2] Implement `last_seen` and `reachable` semantics in `core/store.py` — a source unreachable this run updates only its `reachable` flag and is never treated as deletion (FR-007, US2 AS2)
- [ ] T048 [US2] Implement divergent-clone merging in `core/store.py` — same root commit, different later commits: observations merge rather than one silently overwriting the other
- [ ] T049 [P] [US2] Integration test in `tests/test_accumulation.py` — scan a folder, remove it, rebuild; every previously seen Artifact remains, with when it was last seen (SC-003)
- [ ] T050 [P] [US2] Integration test in `tests/test_sources.py` — a project present locally and on GitHub resolves to one Artifact carrying two sources (US2 AS3)

**Checkpoint**: The archive now outlives its sources. US1 and US2 both work.

---

## Phase 5: User Story 3 - Answer "how long have I done X?" with a number (Priority: P2)

**Goal**: Read years of experience with a Tool off the timeline instead of estimating.

**Independent Test**: With an archive built, confirm the earliest and latest use of a
given Tool are visible and traceable to specific Artifacts.

- [ ] T051 [P] [US3] Implement Tool span computation in `core/analysis/tool_spans.py` — first use, last use, and the Artifacts each Tool appears in, computed over **the Artifacts present in the build being produced**: public, aliased and opted-in ones under the default; every Artifact in the Author's own `full` build (FR-027, SC-007)
  - Found validating the MVP against tinygrad (2026-08-25): a **fork carries its
    upstream's whole history into the span**. `gpuocelot`, forked with commits back to
    2009-06-11, makes C++, Docker, Python and Shell all read "first used 2009" for an
    account whose own work starts in 2020. That overstates experience, which is the
    direction ADR-0009 rules out, and it puts SC-007 ("state years of experience ... with
    no estimation from memory") on the wrong side of correct. The span must be computed
    over the Author's own commits, not the Artifact's full activity — the views already
    make this distinction with `isBarelyMine` (share < 0.1), but `tool_spans.compute()`
    does not. Needs `[author] emails` to be configured; with no emails there is no "own"
    to measure and the span should say so rather than quietly report the fork's dates.

- [ ] T052 [US3] Render Tool spans in `views/timeline.html` — first and last use, with every contributing Artifact traceable
- [ ] T053 [P] [US3] Implement `graph.sqlite` emission in `core/sqlite.py` — one table per node type plus one `edges` table, mirroring `graph.json` exactly; a derived query surface, never a graph database (Principle III)
- [ ] T054 [US3] Add the FTS5 virtual table over Artifact names and descriptions in `core/sqlite.py` — populated in v0.1 and never queried by it, because v0.2's search needs it and adding it later means every Author rebuilds
- [ ] T055 [P] [US3] Implement `llms.txt` emission in `core/llms.py` — the schema in prose, the archive's shape, and how to read `graph.json` (FR-017)
- [ ] T056 [P] [US3] Unit test in `tests/test_tool_spans.py` — a Tool's first and last use trace to specific Artifacts; a span supported only by private Artifacts is **absent from a `public` build**, complete once those Artifacts are aliased, and complete in the Author's own `full` build (FR-027, US3 AS2, Principle IV)

**Checkpoint**: The résumé question is answerable from output, not memory.

---

## Phase 6: User Story 4 - Publish without leaking a client (Priority: P2)

**Goal**: Publish the archive publicly with nothing private in it, by default.

**Independent Test**: Build an archive containing private Artifacts and confirm no private
name appears anywhere in the published output.

- [ ] T057 [US4] Implement visibility tracking in `core/store.py` — the most recently observed value, keeping its last known value when the source is unreachable and never decaying to `public` (FR-026)
- [ ] T058 [P] [US4] Implement build modes in `core/build.py` — `public` by default, plus `redacted` and `full`; the **output directory follows the mode**: `site/` for `public` and `redacted`, `.dendro-local/` for `full`, so a `full` build cannot reach a published directory (FR-013)
- [ ] T059 [US4] Implement redacted aggregates in `core/build.py` — counts, Tools and a date range under `aggregates.private_withheld`, never a name (ADR-0005)
- [ ] T060 [US4] Implement per-Artifact opt-in from `[publish].opt_in` in `core/build.py` — only the named Artifact appears (US4 AS3)
- [ ] T061 [US4] Implement `[exclude].artifacts` in `core/build.py` — omitted from the graph, retained in the store, restored intact by deleting the line (FR-008)
- [ ] T062 [US4] Implement alias projection in `core/build.py` — from `[[publish.alias]]`, publish the Artifact as a node under its label carrying only the fields named in `reveal`; absent or empty `reveal` publishes the node and its dates and nothing else (FR-028, ADR-0011)
- [ ] T063 [US4] Implement the never-crosses filter in `core/build.py` — for an aliased Artifact strip real name, description, URL, source locators, Technique evidence pointers, content hashes and `DERIVES_FROM`/`SUCCEEDS` edges at **every** setting; a Technique published under an alias ships without its pointer and is no longer verifiable (FR-028, contracts/graph.md)
- [ ] T064 [US4] Implement stable generated labels in `core/build.py` — `Private project N` numbered from the sorted Artifact id and never from discovery order, so a newly scanned private Artifact does not renumber the others (ADR-0011)
- [ ] T065 [US4] Implement `dendro publish` in `cli.py` — publishes from `site/` and never reads `.dendro-local/`; refuses as a second line of defence when `site/graph.json` declares `build_mode: full`; names every Artifact a visibility change removed from the output (FR-026)
- [ ] T066 [P] [US4] Create the archive repository template in `templates/archive/` — `dendrograph.toml`, `store/artifacts/`, `site/`, a `.gitignore` covering `.dendro-local/`, and a README stating exactly what the published site does and does not contain (ADR-0010)
- [ ] T067 [P] [US4] Create `templates/archive/.github/workflows/update.yml` — pins a tool tag, refreshes GitHub-sourced Artifacts and auto-commits the store (ADR-0007)
- [ ] T068 [P] [US4] Support the free-plan split in `templates/archive/.github/workflows/update.yml` and `core/build.py` — when `[publish].target_repository` is set the built site deploys to a second, public repository holding no store, which is how an Author on a free plan keeps a private archive and a public site (ADR-0010)
- [ ] T069 [P] [US4] Privacy test in `tests/test_privacy.py` — zero private Artifact names, descriptions or URLs in any published file under default settings (SC-004)
- [ ] T070 [P] [US4] Test in `tests/test_publish_modes.py` — redacted mode publishes shape without names; `build --mode full` writes nothing into `site/`; `publish` refuses a `full` build
- [ ] T071 [P] [US4] Test in `tests/test_visibility.py` — an Artifact that turns private drops out of the next publish and is named in the run report (FR-026)
- [ ] T072 [P] [US4] Test in `tests/test_repo_topology.py` — no command writes **private** Author data into the tool repository, including into its version history; `examples/` holds public Artifacts only (FR-023, ADR-0010)
- [ ] T073 [P] [US4] Privacy test in `tests/test_alias.py` — an aliased Artifact publishes no real name, description, URL, source locator or Technique evidence path, in any build mode (SC-004, FR-028)
- [ ] T074 [P] [US4] Test in `tests/test_alias_labels.py` — generated labels are unchanged when a new private Artifact is scanned, and an unknown field name in `reveal` is rejected rather than ignored (ADR-0011)

**Checkpoint**: The archive is publishable without an NDA breach.

---

## Phase 7: User Story 5 - Read my own history as a narrative (Priority: P3)

**Goal**: Draw dated markers across the timeline, and let the machine propose
relationships the Author confirms.

**Independent Test**: Declare a marker and confirm it appears on the timeline; run the
suggestion command and confirm no edge is created without confirmation.

- [ ] T075 [US5] Implement Epoch Marker nodes in `core/graph.py` — dated and labelled, read from `[[epoch_markers]]`, declared and never inferred (FR-014)
- [ ] T076 [US5] Render Epoch Markers in `views/timeline.html` — drawn across the axis, with Artifacts reading as before or after each one
- [ ] T077 [P] [US5] Implement content-hash lineage in `core/analysis/lineage.py` — authored files only, excluding dependencies, lockfiles, generated output and files under 512 bytes; several identical non-trivial files required (FR-012)
- [ ] T078 [US5] Emit `DERIVES_FROM` edges in `core/graph.py` — oriented older → newer, each carrying confidence and evidence
- [ ] T079 [P] [US5] Implement `dendro suggest` in `core/suggest.py` — proposes `SUCCEEDS` pairs, candidate Collections, and identity merges where a rewritten history matches an existing Artifact; prints config lines and creates nothing (FR-011, FR-021, Principle I)
- [ ] T080 [US5] Implement confirmed Collection membership in `core/graph.py` — `IN_COLLECTION` edges come only from `[[collections]]`, and an Artifact with an unanswered suggestion stays usable and ungrouped (FR-021)
- [ ] T081 [P] [US5] Implement `dendro prune` in `core/prune.py` — prints candidates and the config lines that would exclude them, and deletes nothing (FR-008, ADR-0002)
- [ ] T082 [P] [US5] Test in `tests/test_suggest.py` — no `SUCCEEDS` edge exists in the graph without a config confirmation (FR-011, SC-008)
- [ ] T083 [P] [US5] Test in `tests/test_lineage.py` — dependencies, lockfiles, generated output and trivial files produce no `DERIVES_FROM`

**Checkpoint**: All five stories are independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T084 [P] Write `README.md` — Principle I stated explicitly, exactly what the published site does and does not contain, and the create-your-archive-from-template steps (ADR-0010)
- [ ] T085 [P] Build the demo archive in `examples/` from the Author's public repositories only — real data, and automatically safe because it is what the privacy default produces
- [ ] T086 Place a visualization above the fold in `README.md` — nobody stars a visualization tool without seeing it
- [ ] T087 [P] Add `LICENSE` (MIT) and `CONTRIBUTING.md` (ADR-0006)
- [ ] T088 Validate SC-001b — a ~500-repository account completes a first full scan unattended within 30 minutes, with progress reported throughout
- [ ] T089 [P] Validate SC-001 — a stranger opens the demo archive and sees a rendered graph in under five minutes without creating any credential
- [ ] T090 [P] Record any vocabulary resolved during implementation in `CONTEXT.md`, not in a backlog
- [ ] T091 [P] Confirm the public surface is English — node and edge identifiers, CLI, file and directory names, docs — and that code comments are Portuguese (ADR-0001)
- [ ] T092 Review the Constitution Check table in `plan.md` against the built system, and record any deviation as a new ADR rather than silently accepting it

---

## Three-Agent Assignment

The user story phases above are the delivery increments. This is the same work cut by
**ownership**, for three agents working in parallel.

**The fork happens after Phase 2, not before.** Phases 1–2 are the serial neck: they turn
`contracts/` into executable code that all three streams read and write through. Splitting
them three ways would mean three agents negotiating the store format while writing it.

| Agent | Territory | Tasks |
|---|---|---|
| **A — collector** | `collectors/git/`, `core/analysis/` | T012, T022–T033, T045, T077, T083 |
| **B — core** | `core/` (identity, store, graph, derived outputs), `cli.py` | T006–T011, T013–T021, T034–T037, T043–T044, T046–T051, T053–T056, T075, T078–T082 |
| **C — views & publish** | `views/`, `templates/archive/`, publish, privacy and aliases | T038–T042, T052, T057–T074, T076 |

Phases 1 and 8 are shared: whoever is free takes them. Every task from T006 to
T083 is assigned to exactly one agent, with no overlap.

**This split is not even, and pretending otherwise would mislead.** Agent B owns most of
Phase 2 alone, and A and C are largely idle until it lands. Two honest ways to handle it:

1. **B runs Phase 2 solo**, while A drafts GitHub discovery against the documented store
   contract (T023–T025 need no store) and C builds the timeline and graph views against a
   hand-written `graph.json` fixture (T038–T040 need no core). Both integrate when Phase 2
   lands.
2. **All three do Phase 2 together** — B on store and identity, A on git plumbing (T012)
   and the device-flow verification (T022), C on config and CLI (T006, T018–T021) — then
   fork cleanly. Faster to the fork, at the cost of three agents in `core/` at once.

Option 1 is safer: the contract files are complete enough that A and C can build against
them without B's code existing.

### Files two agents both touch

- `core/store.py` — B owns it (T008–T011), but T046–T048 (US2) and T057 (US4) extend it.
  **Sequence these; do not run them in parallel.** T057 is C's requirement but B's file:
  either B implements it on C's behalf, or C takes the file for that task.
- `core/graph.py` — B owns it (T034–T036), extended by T075, T078, T080. Same rule.
- `views/timeline.html` — C owns it across T039, T052 and T076, all sequential.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup — **blocks every user story**
- **US1 (Phase 3)**: depends on Phase 2
- **US2 (Phase 4)**: depends on Phase 2. Shares the scan pipeline with US1 but is
  independently testable — its test scans a local folder and removes it
- **US3 (Phase 5)**: depends on Phase 2, and on US1 for a built graph to read Tool spans from
- **US4 (Phase 6)**: depends on Phase 2 and on US1's build step
- **US5 (Phase 7)**: depends on Phase 2 and on US1's graph
- **Polish (Phase 8)**: depends on the stories being shipped

### Within a story

- Models and analysis before services; services before the CLI wiring; core before views
- Tests may be written first where the heuristic is the risk — identity, authorship,
  Technique precision, accumulation, privacy

### Parallel opportunities

- Phase 1: T002–T005 all in parallel
- Phase 2: T007, T011, T012, T017, T021, T022 in parallel; T006/T008–T010, T013–T016 and
  T018–T020 are each same-file sequences
- Phase 3: T023/T025 in parallel, T029–T031 in parallel, T034/T038/T039 in parallel
- Phase 6: T066–T072 all in parallel
- Once Phase 2 lands, US1/US2 (Agent A + B) and the view work (Agent C) proceed together

---

## Parallel Example: Phase 2

```bash
# After T006 and T008 land, launch the independent foundational work together:
Task: "Implement collectors/git/plumbing.py — subprocess wrappers for git"
Task: "Verify device flow enablement against GitHub docs, record in docs/adr/0008"
Task: "Unit tests for config in tests/test_config.py"
Task: "Unit tests for the store in tests/test_store.py"
```

## Parallel Example: User Story 1

```bash
# The three analysis modules touch different files and share no state:
Task: "Implement Tool detection in core/analysis/tools.py"
Task: "Implement Technique inference in core/analysis/techniques.py"
Task: "Implement Dependency extraction in core/analysis/dependencies.py"

# Meanwhile Agent C works against a hand-written graph.json fixture:
Task: "Implement the shared data-loading layer in views/loader.js"
Task: "Implement the timeline view in views/timeline.html"
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1: Setup
2. Phase 2: Foundational — **blocks everything**
3. Phase 3: User Story 1
4. **Stop and validate**: run against a public account with no credentials and confirm a
   browsable timeline and graph
5. This is also the demo and the README's above-the-fold image

### Incremental delivery

1. Setup + Foundational → the contracts are executable
2. + US1 → a public archive renders **(MVP)**
3. + US2 → the archive outlives its sources
4. + US4 → the archive is safe to publish
5. + US3 → the résumé question is answerable
6. + US5 → the archive reads as a narrative

US4 is pulled ahead of US3 deliberately: an NDA breach would be worse than the tool not
existing, so the safe behaviour ships with the first *publishable* version, not after it.

---

## Notes

- **Nothing infers into the graph without confirmation.** `SUCCEEDS` and `IN_COLLECTION`
  come from config only; `APPLIES` and `DERIVES_FROM` carry confidence and evidence. Any
  task that would break this is a constitution violation, not a shortcut (Principle I).
- **The store never loses data.** No task deletes a stored Artifact. Exclusion is a config
  line, and deleting the line restores it (Principle II).
- **Rendering and the force simulation have no tests**, by design. The heuristics carry
  the risk; the canvas does not.
- Commit after each task or logical group; each `git diff` on the store should be readable.
