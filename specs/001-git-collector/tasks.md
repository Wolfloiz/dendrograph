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
- [X] T042 [US1] Validate SC-005 as soon as the graph view renders, in `views/graph.html` — ~500 Artifacts and ~3,000 nodes reach first render under 2 seconds and sustain at least 30fps while panning, from a page opened with no network access. Barnes-Hut is deferred to v0.3, so a failure here is a redesign and must surface now rather than in polish
  - Partially measured 2026-08-25 with a headless harness (no browser): 500 Artifacts
    produce **554 nodes**, not the ~3,000 assumed — Tool, Technique, Period, Author and
    Dependency nodes are shared across Artifacts. 4,454 edges; `graph.json` 858 KB.
    Parse + eval 13.7 ms; physics 1.57 ms/frame against a 33.3 ms budget at 30fps.
    This excludes canvas rasterisation and is **not** an fps measurement. Real browser
    validation is still outstanding. At the spec's assumed 3,000 nodes the O(n²)
    repulsion is ~30× more work and would exceed the budget — the assumption, not the
    measurement, is what carries the risk.
  - Re-measured 2026-08-26 against a real archive — 96 Artifacts, scanned from a local
    folder of 110 repositories and a GitHub account of 68: **2,307 nodes**, 3,158 edges,
    `graph.json` 961 KB. The earlier estimate was low because it assumed node count
    follows Artifact count. It does not: 1,437 of those nodes are Authors and 740 are
    Dependencies, because a fork carries every contributor the upstream ever had. Roughly
    120 real Artifacts reach the 3,000 the spec assumed of 500.
  - **The redesign this task exists to surface was real — and it was not performance.**
    The simulation diverged. `220 / d2` has no floor, so two nodes that touch exchange an
    unbounded force; at 2,307 nodes the layout left the viewport by frame 5 and reached a
    radius of 1e17 by frame 30. Every node was drawn, all of them off-screen: the page
    looks like it renders and then empties. Reproduced in a DOM with a 1900x760 canvas:
    **0 of 2,307 nodes on screen**.
  - Fixed in `views/graph.html`: softening (`d2 + 400`), a 25 px/frame velocity ceiling,
    centre gravity 0.0016 to 0.004, the view auto-fitting the layout's bounding box until
    the reader pans, and the simulation stopping once it settles. Same harness after:
    **2,307 of 2,307 on screen**, settled at frame 591, no ticks afterwards.
  - Headless numbers (Node 22, no browser): parse + eval of a 961 KB `graph.js` 17.5 ms;
    one tick 19.4 ms against the 33.3 ms budget at 30fps, 2.66M pairs per frame. Panning
    after the layout settles costs no tick at all, which is what puts 30fps within reach
    — while settling there is ~14 ms left for rasterisation, and rasterisation is exactly
    what none of this measures.
  - **Measured in a browser 2026-08-27** — Chromium, the 2,307-node archive, an fps probe
    hooked to the one `clearRect` per drawn frame so the count is of frames actually
    painted: **60fps, the vsync ceiling**, while settling and while panning at every zoom.
    SC-005 is met. First render is not at risk either: parse and eval of a 961 KB
    `graph.js` is 17.5 ms against a 2 s budget.
  - The first browser run did not meet it — **20 to 30fps once zoomed in** — and the cause
    was the label redesign, not the simulation. `strokeText` traces every glyph as a path,
    outside the glyph cache, so ~190 haloed labels per frame cost more than all 2,307 nodes
    together; each node was its own `fill` call, and `ctx.font` was reparsed once per
    candidate label. Fixed by rasterising each label once into an offscreen tile and
    blitting it, batching node fills by colour, caching text widths, and resolving the lit
    neighbourhood when focus changes instead of per node per frame. Per frame at 1600x900:
    `fill` 2,307 to under ten, `set font` and `measureText` 96-423 to zero, glyphs traced
    64-376 to zero. The picture is unchanged — the `drawImage` count equals the old
    `fillText` count exactly (32 / 73 / 188 / 95) and the arc count did not move.

- [X] T043 [P] [US1] Integration test in `tests/test_dedup.py` — the same project present on two paths produces exactly one Artifact (SC-002, US1 AS3)
- [X] T044 [P] [US1] Guard test in `tests/test_no_judgement.py` — no output in any build mode contains a quality score, a grade, a complexity proof, or an AI-authorship label (FR-015, Principle V)

**Checkpoint**: A public archive renders. This is the MVP and the demo.

---

## Phase 4: User Story 2 - Rescue work that no API can reach (Priority: P1)

**Goal**: Scan local folders once and keep those Artifacts forever, after the drive dies.

**Independent Test**: Scan a local folder, confirm its Artifacts are stored, then rename
or remove the folder and re-run. The Artifacts must still be present in the graph.

- [X] T045 [P] [US2] Implement local discovery in `collectors/git/local.py` — walk a folder for git repositories, with the same fidelity as the GitHub path (FR-001)
- [X] T046 [US2] Implement multi-source merging in `core/store.py` — one Artifact carries every source it was seen in; neither overwrites the other (US2 AS3)
- [X] T047 [US2] Implement `last_seen` and `reachable` semantics in `core/store.py` — a source unreachable this run updates only its `reachable` flag and is never treated as deletion (FR-007, US2 AS2)
- [X] T048 [US2] Implement divergent-clone merging in `core/store.py` — same root commit, different later commits: observations merge rather than one silently overwriting the other
- [X] T049 [P] [US2] Integration test in `tests/test_accumulation.py` — scan a folder, remove it, rebuild; every previously seen Artifact remains, with when it was last seen (SC-003)
- [X] T050 [P] [US2] Integration test in `tests/test_sources.py` — a project present locally and on GitHub resolves to one Artifact carrying two sources (US2 AS3)

**Checkpoint**: The archive now outlives its sources. US1 and US2 both work.

---

## Phase 5: User Story 3 - Answer "how long have I done X?" with a number (Priority: P2)

**Goal**: Read years of experience with a Tool off the timeline instead of estimating.

**Independent Test**: With an archive built, confirm the earliest and latest use of a
given Tool are visible and traceable to specific Artifacts.

- [X] T051 [P] [US3] Implement Tool span computation in `core/analysis/tool_spans.py` — first use, last use, and the Artifacts each Tool appears in, computed over **the Artifacts present in the build being produced**: public, aliased and opted-in ones under the default; every Artifact in the Author's own `full` build (FR-027, SC-007)
  - Found validating the MVP against tinygrad (2026-08-25) and fixed the same day: a fork
    carried its upstream's whole history into the span. `gpuocelot`, forked with commits
    back to 2009-06-11, made C++, Docker, Python and Shell all read "first used 2009" for
    an account whose own work starts in 2020 — the overstatement ADR-0009 rules out, and
    SC-007 on the wrong side of correct. The window is now the Author's own commits, from
    the per-author dates the store already recorded. Untouched Artifacts contribute no
    dates and are counted in `untouched_count`; with no `[archive].emails` configured the
    span is marked `attributed: false` rather than passing a fork's dates off as the
    Author's. On the same 23 repositories Python went from 17.2 years to 3.1. See
    *Whose dates a span reports* in `contracts/graph.md`.

- [X] T052 [US3] Render Tool spans in `views/timeline.html` — first and last use, with every contributing Artifact traceable
- [X] T053 [P] [US3] Implement `graph.sqlite` emission in `core/sqlite.py` — one table per node type plus one `edges` table, mirroring `graph.json` exactly; a derived query surface, never a graph database (Principle III)
- [X] T054 [US3] Add the FTS5 virtual table over Artifact names and descriptions in `core/sqlite.py` — populated in v0.1 and never queried by it, because v0.2's search needs it and adding it later means every Author rebuilds
- [X] T055 [P] [US3] Implement `llms.txt` emission in `core/llms.py` — the schema in prose, the archive's shape, and how to read `graph.json` (FR-017)
- [X] T056 [P] [US3] Unit test in `tests/test_tool_spans.py` — a Tool's first and last use trace to specific Artifacts; a span supported only by private Artifacts is **absent from a `public` build**, complete once those Artifacts are aliased, and complete in the Author's own `full` build (FR-027, US3 AS2, Principle IV)

**Checkpoint**: The résumé question is answerable from output, not memory.

---

## Phase 6: User Story 4 - Publish without leaking a client (Priority: P2)

**Goal**: Publish the archive publicly with nothing private in it, by default.

**Independent Test**: Build an archive containing private Artifacts and confirm no private
name appears anywhere in the published output.

  - Closed once agent C delivered US4's filtering. One correction to the task's wording:
    it says the span is "complete once those Artifacts are aliased", but under ADR-0011
    disclosure is opt-in per field, so an alias alone does **not** restore a Tool's dates —
    `reveal = ["tools"]` does. Both are asserted: aliasing leaves the span narrow, and
    revealing tools widens it, with the aliased Artifact still traceable from the Tool it
    contributed to under its generated label.
  - Update 2026-08-25: US4's filtering now exists (`core/privacy.py`); the visibility
    half of T056 is unblocked.

- [X] T057 [US4] Implement visibility tracking in `core/store.py` — the most recently observed value, keeping its last known value when the source is unreachable and never decaying to `public` (FR-026)
- [X] T058 [P] [US4] Implement build modes in `core/build.py` — `public` by default, plus `redacted` and `full`; the **output directory follows the mode**: `site/` for `public` and `redacted`, `.dendro-local/` for `full`, so a `full` build cannot reach a published directory (FR-013)
- [X] T059 [US4] Implement redacted aggregates in `core/build.py` — counts, Tools and a date range under `aggregates.private_withheld`, never a name (ADR-0005)
- [X] T060 [US4] Implement per-Artifact opt-in from `[publish].opt_in` in `core/build.py` — only the named Artifact appears (US4 AS3)
- [X] T061 [US4] Implement `[exclude].artifacts` in `core/build.py` — omitted from the graph, retained in the store, restored intact by deleting the line (FR-008)
- [X] T062 [US4] Implement alias projection in `core/build.py` — from `[[publish.alias]]`, publish the Artifact as a node under its label carrying only the fields named in `reveal`; absent or empty `reveal` publishes the node and its dates and nothing else (FR-028, ADR-0011)
- [X] T063 [US4] Implement the never-crosses filter in `core/build.py` — for an aliased Artifact strip real name, description, URL, source locators, Technique evidence pointers, content hashes and `DERIVES_FROM`/`SUCCEEDS` edges at **every** setting; a Technique published under an alias ships without its pointer and is no longer verifiable (FR-028, contracts/graph.md)
  - Lives in `core/privacy.py` (selection + projection) with the field gates in
    `core/graph.py`. Visibility `unknown` is not public: a locally scanned
    repository stays out of a published build until opted in or aliased.
    Techniques have no `reveal` field, so a bare APPLIES edge always crosses —
    minus its evidence pointer.
- [X] T064 [US4] Implement stable generated labels in `core/build.py` — `Private project N` numbered from the sorted Artifact id and never from discovery order, so a newly scanned private Artifact does not renumber the others (ADR-0011)
  - Nuance: positional numbering over sorted ids is deterministic — same store,
    same labels, never discovery order — but an id sorting **before** existing
    ones shifts later labels visibly and stably in the diff. Stability under
    arbitrary insertion would require persisting labels, contradicting
    ADR-0002 ("everything but the store is derived"); determinism was chosen.
- [X] T065 [US4] Implement `dendro publish` in `cli.py` — publishes from `site/` and never reads `.dendro-local/`; refuses as a second line of defence when `site/graph.json` declares `build_mode: full`; names every Artifact a visibility change removed from the output (FR-026)
  - With `[publish].target_repository`, deployment pushes `site/` to the second
    repository via `core/publish.py`.
- [X] T066 [P] [US4] Create the archive repository template in `templates/archive/` — `dendrograph.toml`, `store/artifacts/`, `site/`, a `.gitignore` covering `.dendro-local/`, and a README stating exactly what the published site does and does not contain (ADR-0010)
- [X] T067 [P] [US4] Create `templates/archive/.github/workflows/update.yml` — pins a tool tag, refreshes GitHub-sourced Artifacts and auto-commits the store (ADR-0007)
- [X] T068 [P] [US4] Support the free-plan split in `templates/archive/.github/workflows/update.yml` and `core/build.py` — when `[publish].target_repository` is set the built site deploys to a second, public repository holding no store, which is how an Author on a free plan keeps a private archive and a public site (ADR-0010)
- [X] T069 [P] [US4] Privacy test in `tests/test_privacy.py` — zero private Artifact names, descriptions or URLs in any published file under default settings (SC-004)
- [X] T070 [P] [US4] Test in `tests/test_publish_modes.py` — redacted mode publishes shape without names; `build --mode full` writes nothing into `site/`; `publish` refuses a `full` build
- [X] T071 [P] [US4] Test in `tests/test_visibility.py` — an Artifact that turns private drops out of the next publish and is named in the run report (FR-026)
- [X] T072 [P] [US4] Test in `tests/test_repo_topology.py` — no command writes **private** Author data into the tool repository, including into its version history; `examples/` holds public Artifacts only (FR-023, ADR-0010)
- [X] T073 [P] [US4] Privacy test in `tests/test_alias.py` — an aliased Artifact publishes no real name, description, URL, source locator or Technique evidence path, in any build mode (SC-004, FR-028)
- [X] T074 [P] [US4] Test in `tests/test_alias_labels.py` — generated labels are unchanged when a new private Artifact is scanned, and an unknown field name in `reveal` is rejected rather than ignored (ADR-0011)

**Checkpoint**: The archive is publishable without an NDA breach.

---

## Phase 7: User Story 5 - Read my own history as a narrative (Priority: P3)

**Goal**: Draw dated markers across the timeline, and let the machine propose
relationships the Author confirms.

**Independent Test**: Declare a marker and confirm it appears on the timeline; run the
suggestion command and confirm no edge is created without confirmation.

- [X] T075 [US5] Implement Epoch Marker nodes in `core/graph.py` — dated and labelled, read from `[[epoch_markers]]`, declared and never inferred (FR-014)
- [X] T076 [US5] Render Epoch Markers in `views/timeline.html` — drawn across the axis, with Artifacts reading as before or after each one
- [X] T077 [P] [US5] Implement content-hash lineage in `core/analysis/lineage.py` — authored files only, excluding dependencies, lockfiles, generated output and files under 512 bytes; several identical non-trivial files required (FR-012)
- [X] T078 [US5] Emit `DERIVES_FROM` edges in `core/graph.py` — oriented older → newer, each carrying confidence and evidence
- [X] T079 [P] [US5] Implement `dendro suggest` in `core/suggest.py` — proposes `SUCCEEDS` pairs, candidate Collections, and identity merges where a rewritten history matches an existing Artifact; prints config lines and creates nothing (FR-011, FR-021, Principle I)
- [X] T080 [US5] Implement confirmed Collection membership in `core/graph.py` — `IN_COLLECTION` edges come only from `[[collections]]`, and an Artifact with an unanswered suggestion stays usable and ungrouped (FR-021)
- [X] T081 [P] [US5] Implement `dendro prune` in `core/prune.py` — prints candidates and the config lines that would exclude them, and deletes nothing (FR-008, ADR-0002)
- [X] T082 [P] [US5] Test in `tests/test_suggest.py` — no `SUCCEEDS` edge exists in the graph without a config confirmation (FR-011, SC-008)
- [X] T083 [P] [US5] Test in `tests/test_lineage.py` — dependencies, lockfiles, generated output and trivial files produce no `DERIVES_FROM`
  - Two findings from the first real run against tinygrad (2026-08-25), raised by agent B,
    for agent A to judge. (1) The direction is unsupported at short intervals: `tinyos`
    (first activity 2024-05-02) and `tinyturing` (2024-05-01) are one day apart, and the
    detector still asserts which derives from which. At that distance "older → newer" is
    noise, and SC-008 says no edge may assert what was not observed — a minimum interval,
    or a confidence that degrades as the gap narrows, would settle it. (2) Evidence
    volume: one edge carried 205 paths, and evidence was 7% of a 220 KB `graph.json` for
    two edges alone. Harmless now; worth watching against SC-005's 1 MB target at 500
    Artifacts.
  - **Judged by agent A, 2026-08-27.**
    - **(1) Upheld, and it was live.** The orientation came from `activity.first`, and the
      tie-break was the Artifact id — so at zero days apart the arrow pointed wherever a SHA
      sent it. Not hypothetical: the published demo carried an edge between `selfcheck` and
      `Alluna_air_Eugenio_challenge`, same first-activity date, direction decided by hash.
      `lineage.candidates` now requires the two first activities to be at least
      `MINIMUM_ORIENTING_INTERVAL_DAYS` (7) apart, and a pair the dates cannot separate
      produces no candidate at all rather than a directed one. A pair with no observed date
      on either side is dropped too — it used to sort to the end and get an arrow anyway.
      Real archive: **8 lineage edges became 7**, and every survivor has real separation
      (41 to 632 days). The week is judgement, not measurement, and the comment says so.
      When the collector records a date per shared file the origin becomes observable, and
      the interval stops being needed.
    - **(2) Not upheld — measured, and closed without a change.** In the real public build
      evidence is **24 KB of a 522 KB `graph.json`, 4.6%**, and the heaviest single edge
      carries 145 paths, not 205. What the payload is actually made of: edges 59% (2,702
      records at ~117 bytes, mostly the two long node ids), Dependency nodes 22%, Author
      nodes 15%. Capping evidence would buy about 4% and cost SC-006 — every candidate
      carrying the paths that prove it — which is a bad trade. If the 1 MB target ever
      binds, the lever is the edge records, not the evidence.

**Checkpoint**: All five stories are independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T084 [P] Write `README.md` — Principle I stated explicitly, exactly what the published site does and does not contain, and the create-your-archive-from-template steps (ADR-0010)
- [X] T085 [P] Build the demo archive in `examples/` from the Author's public repositories only — real data, and automatically safe because it is what the privacy default produces
  - `examples/site/` — 57 Artifacts, 2,432 nodes, 2,703 edges, 3.2 MB, published 2026-08-27
    from the Author's own archive with nothing configured but `[archive].emails`. The store
    stays out: it holds the 40 withheld Artifacts, and the tool repository holds no private
    Author data (ADR-0010).
  - **"Automatically safe" turned out to be a claim worth testing, and it failed twice.**
    Building the demo from real public data is what surfaced both:
    - `LiveScript` and `livescript` are two npm packages differing only in case, and the
      Dependency id lowercased both into one. It had been worked around with an `[exclude]`
      on the repository that carried them — a workaround that would have shipped in this
      repository. Fixed properly: identity now follows each registry's own rule. PyPI
      normalises (PEP 503), so `Django` and `django` are one project; npm does not, so they
      are two packages. `tests/test_dependency_ids.py`.
    - The published site carried the readable email address of **1,165 contributors**,
      harvested from the history of public repositories and forks. The Author node id was
      already a digest to keep the address out of it; the label was not. ADR-0012, and
      `tests/test_no_addresses.py` sweeps every written file so it cannot come back.
  - Verified on the copy: no address, no local path, and none of the 40 withheld Artifacts
    named anywhere in `examples/site/`.
  - Refreshed 2026-08-27 after the lineage and Author-label work: 2,432 nodes, 2,702 edges,
    7 lineage edges instead of 8 — the dropped one was oriented by a hash tie-break — and
    Author nodes labelled `Anant Prasad` and `Sean Wei` instead of `anantprsd5` and `me`.
    Swept again on the copy: still no address, no local path, no withheld Artifact named.
- [X] T086 Place a visualization above the fold in `README.md` — nobody stars a visualization tool without seeing it
- [X] T087 [P] Add `LICENSE` (MIT) and `CONTRIBUTING.md` (ADR-0006)
- [ ] T088 Validate SC-001b — a ~500-repository account completes a first full scan unattended within 30 minutes, with progress reported throughout
  - **Progress and unattendedness: validated outright.** A cold scan of `github:Wolfloiz`
    printed one line per repository — `[64/68]  204s  Wolfloiz/...` — with the elapsed
    seconds running, then `scanned 68 in 210s`. No prompt, exit 0, and the one repository
    that could not be identified was reported as unidentifiable rather than taken as fatal.
    That is the difference between a run that finished and a run that hung, which is the
    whole point of the criterion.
  - **The 30 minutes: measured in parts, because no ~500-repository account is available.**
    - Real scan, 68 repositories cloned from scratch: **210 s**, mean **3.06 s/repo**,
      median **1 s**, p90 **7 s**, worst **24 s**.
    - 500 synthetic local repositories, which skip the clone and isolate analysis and store:
      **58 s**, peak RSS **40 MB**. Cost per repository across the run: 0.111 s over the
      first hundred, 0.130 s over the middle hundred, 0.110 s over the last. **Flat — there
      is no super-linear term**, which is the only thing that would make the extrapolation
      dishonest.
    - Derived outputs at 500 Artifacts: full build **0.71 s**, publish **0.38 s**, 507 nodes
      and 2,660 edges. Not a factor.
    - So ~96% of a GitHub scan is the clone, and it is network-bound. 500 × 3.06 s =
      **25.5 min** — inside the budget, with about 15% of headroom.
  - **What carries the risk is the size distribution, not the count.** This account's median
    repository costs 1 s and its worst costs 24. An account of 500 with a heavier tail, or a
    slower link, exceeds 30 minutes without anything in the code being wrong. A token is also
    assumed: unauthenticated discovery is capped at 60 requests an hour, which cannot reach
    500 repositories at all (ADR-0008, and `discover` says so in its docstring).
  - **Still open**: an account of that size to run it against. Everything measurable without
    one has been measured, and the projection rests on measured linearity rather than on
    assumption.
- [X] T089 [P] Validate SC-001 — a stranger opens the demo archive and sees a rendered graph in under five minutes without creating any credential
  - Measured 2026-08-27 from a clean clone of this repository. **Nothing on the path asks
    for an account**: a clone or a zip download, then a double-click. No server, no install,
    no Python — the demo is HTML.
  - What has to arrive: **4.2 MB** packed (9.7 MB checked out). Local clone 0.4 s; over a
    10 Mbit link the download is a handful of seconds, and the five-minute budget is not
    close to being the constraint.
  - What happens on open, measured on the cloned copy: parse and eval of the 716 KB
    `graph.js` **18 ms**, first frame at **182 ms**, layout settled at frame 563 — about
    nine seconds of visible convergence at 60fps — with **2,432 of 2,432 nodes on screen**.
    Rasterisation is not in these numbers; T042 covers it in a real browser at 60fps on the
    same page.
  - **No file in `examples/site/` names an absolute URL**, so the page renders with the
    network unplugged (FR-016, ADR-0004). `tests/test_view_assets.py` holds that for the
    views the build copies.
  - The remaining risk is not technical: a stranger has to find the thing. `README.md` names
    `examples/site/` immediately after the quickstart, which is the only reason the five
    minutes is spent looking at a graph instead of looking for one.
- [X] T090 [P] Record any vocabulary resolved during implementation in `CONTEXT.md`, not in a backlog
- [X] T091 [P] Confirm the public surface is English — node and edge identifiers, CLI, file and directory names, docs — and that code comments are Portuguese (ADR-0001)
- [X] T092 Review the Constitution Check table in `plan.md` against the built system, and record any deviation as a new ADR rather than silently accepting it

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

## v0.1 closed — 2026-08-27

91 of 92 tasks done. **T088 ships with a named gap rather than a claim**: SC-001b asks
for a ~500-repository account and none exists to point at. Everything measurable without
one was measured — a cold scan of 68 real repositories at 3.06 s each, 500 synthetic local
ones showing the per-repository cost flat across the run (0.111 / 0.130 / 0.110 s over the
first, middle and last hundred), derived outputs at 500 Artifacts under a second. That puts
500 repositories at 25.5 minutes against a 30-minute budget, and the projection rests on
measured linearity rather than assumption. Progress reporting and unattendedness needed no
extrapolation and are validated outright.

Checking the box would be deciding that a projection counts as the validation. It does not,
so the box stays open and **the item carries into v0.2** as a validation still owed.

Three defects surfaced late and are worth naming, because each was found by using the tool
on real data rather than by reading the code:

- **The graph diverged and then went blank** (T042). Fixed, and the browser measurement
  that closed it also caught a 20–30fps regression introduced by the fix's own label pass.
- **Identity collapsed three different things into one node** — an npm scope, an npm
  package's own capitalisation, and one contributor who signed two ways. The label guard
  caught all three; the ids were wrong, not the guard.
- **The published site carried 1,165 contributors' email addresses** (ADR-0012). The id was
  already a digest to keep the address out; the label had never been given the same thought.

The line those three share: the store, the ids and the privacy default were all correct in
the abstract and wrong against a real archive. Nothing in the plan would have caught them.

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
