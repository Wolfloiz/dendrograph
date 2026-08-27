---

description: "Task list for v0.2 — usable by a stranger"
---

# Tasks: Usable by a stranger

**Input**: Design documents from `/specs/002-usable-by-a-stranger/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Not TDD across the board. The constitution exempts rendering and the force
simulation from tests and points them at the heuristics instead. Test tasks appear here only
where the spec or the plan names one: the two privacy guards, the R7 agreement guard, the
address round-trip, the extraction equivalence, and the view-naming guard. Each says what it
would catch.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel — different files, no dependency on an incomplete task
- **[Story]**: US1 single screen, US2 search, US3 Tool profile, US4 fork path

## Path Conventions

Repository root. Views in `views/`, core in `core/`, CLI in `cli.py`, tests in `tests/`.
Structure per [plan.md](./plan.md#project-structure).

---

## Phase 1: Setup

**Purpose**: Put the two guards in place that the rest of the release leans on. Both are
cheap now and expensive to add after something has already gone wrong.

- [ ] T001 [P] Extend `tests/test_view_assets.py` — assert no file in `views/` is named after
      a build output (`graph.js`, `graph.json`, `graph.sqlite`, `llms.txt`). Catches the
      silent overwrite in R3: `emit` writes the data then copies `views/*.js` over it, so
      `views/graph.js` would replace the archive with a renderer and fail as an empty graph
      rather than a build error.
- [ ] T002 Capture the pre-extraction baseline with the jsdom op-counting harness against
      `views/graph.html` and `views/timeline.html` at 3,283 nodes: frames to settle, nodes on
      screen once settled, labels drawn at rest and zoomed, and per-frame `fill` / `drawImage`
      / `arc` / `set font` counts. Record it in the scratchpad and quote it in the T005 commit
      — it is the only thing that can prove the extraction changed nothing.

**Checkpoint**: The naming trap is closed and there is a number to hold the refactor to.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Turn 1,445 lines of two inline `<script>` tags into modules, without changing
one pixel. This blocks every user story, and it is the phase most likely to break something
invisibly — which is exactly why it ships before anything that would mask it.

**⚠️ CRITICAL**: No user story work begins until T005 proves equivalence.

- [ ] T003 Extract the graph renderer from `views/graph.html` into `views/view-graph.js`,
      exposing `DendroViewGraph.create(container, graph, options)` returning
      `{ activate, suspend, select, search }`. `views/graph.html` loads the module and keeps
      working; behaviour is unchanged, `suspend` may be a stub until T009.
- [ ] T004 [P] Extract the timeline renderer from `views/timeline.html` into
      `views/view-timeline.js` with the same factory shape. `views/timeline.html` loads it and
      keeps working.
- [ ] T005 Re-run the T002 harness against the extracted modules and confirm every number is
      identical. A difference here is a behaviour change nobody asked for; fix it rather than
      re-baseline it.

**Checkpoint**: Two working pages, two modules, identical output. Bisectable from here.

---

## Phase 3: User Story 1 — One screen instead of two pages (Priority: P1) 🎯 MVP

**Goal**: Every view of the archive on a single screen, sharing one load, one selection and
one address.

**Independent Test**: Open the archive, switch views, confirm the data was fetched once and
the selected node survived. Then unplug the network and do it again.

### Implementation

- [ ] T006 [US1] Create `views/index.html` — the shell: header, view selector, a slot for the
      search field, and the view container. Loads `graph.js`, `loader.js`, `theme.js` and the
      view modules; carries no rendering logic of its own.
- [ ] T007 [US1] Create `views/screen.js` — the view registry, activation and suspension, and
      the selection that lives in the shell rather than in any view (per
      [contracts/screen.md](./contracts/screen.md)). Views are told what is selected; they do
      not decide it.
- [ ] T008 [US1] Add fragment routing to `views/screen.js` — parse and serialise
      `#graph`, `#graph/<node id>`, `#tool/<node id>`, `#timeline?q=<query>` per the grammar
      in [data-model.md](./data-model.md#address-grammar). Pan, zoom and the layout seed stay
      out on purpose: a shared address lands on the same subject, not the same pixels.
- [ ] T009 [US1] Stop the graph's animation loop in `views/view-graph.js` when the view is
      suspended, keeping the settled layout so returning resumes rather than re-settles. This
      is the SC-007 regression the single screen is most likely to introduce — the loop is
      dirty-gated, which costs nothing on a page with one view and keeps costing behind a
      timeline at ~70 ms a frame while settling.
- [ ] T010 [US1] Carry the selection across a view switch in `views/screen.js` and
      `views/view-timeline.js` — an Artifact selected in the graph is highlighted in the
      timeline. A view that cannot render the current selection shows its normal state, never
      an error.
- [ ] T011 [P] [US1] Extend `views/style.css` with the shell: view selector, layout, and the
      narrow-screen rule where the timeline is the view that survives. Extend, do not rewrite
      — the design tokens and the `.eyebrow` rule are shared with what exists.
- [ ] T012 [US1] Delete `views/graph.html` and `views/timeline.html`. `core/build.py` needs no
      change: the glob added in v0.1 already carries whatever is in `views/`. State the broken
      addresses in the commit rather than adding redirect stubs (R8).
- [ ] T013 [P] [US1] Update `README.md` and `examples/README.md` to name `site/index.html`
      instead of `site/timeline.html`.

### Tests for User Story 1

- [ ] T014 [P] [US1] Add `tests/test_screen.py` — the emitted file set is exactly what
      [contracts/screen.md](./contracts/screen.md) lists, and `graph.html` / `timeline.html`
      are gone. Catches a build that quietly keeps shipping the old pages.
- [ ] T015 [US1] Extend the jsdom harness to prove the graph's loop draws **zero frames** while
      the timeline is active, and that returning to the graph does not re-settle. Catches the
      one regression that would break SC-007 without breaking anything visible.

**Checkpoint**: One screen, both views, offline, with the frame budget held. This is the MVP —
it is worth shipping alone, because it removes the worst thing about the current site.

---

## Phase 4: User Story 2 — Ask the archive a question (Priority: P2)

**Goal**: A visitor searches names and descriptions on the page; the Author searches the whole
store from the command line.

**Independent Test**: Search a word that appears only in a description and nowhere in a name.
The Artifact comes back.

### Implementation

- [ ] T016 [US2] Create `views/search.js` — an index over Artifact, Tool and Technique names
      plus Artifact descriptions, built from the payload already in memory. **46 of the 57
      published Artifacts carry a description today**, so this needs no new build output and no
      rescan (FR-020). Prefix matches rank above substring matches, better-connected first.
- [ ] T017 [US2] Wire search into `views/index.html` and `views/screen.js` — the field, the
      results, and selecting a result moving the current view rather than replacing the screen
      (FR-010). Each result names its kind and why it matched: name or description.
- [ ] T018 [P] [US2] Create `core/search.py` — FTS5 queries over `artifact_search` in
      `graph.sqlite`, ordered by rank then name. Ordering must stay mechanical and explainable
      in one sentence; anything that looks like a judgement about which Artifact matters more
      is an inference the tool does not make (Principle I).
- [ ] T019 [US2] Add the `search` command to `cli.py` per
      [contracts/search.md](./contracts/search.md), and record it in
      `specs/001-git-collector/contracts/cli.md`. With no FTS5 table it refuses with exit `2`
      and says how to get one — it never falls back to a scan that answers a different
      question quietly (R6).

### Tests for User Story 2

- [ ] T020 [P] [US2] Add `tests/test_search.py` — CLI results carry the kind, the subject and
      why each matched; a query matching nothing exits `0` and says so.
- [ ] T021 [US2] **The privacy guard** in `tests/test_search.py` — a term appearing only in a
      withheld Artifact's description is findable from the CLI and appears **nowhere** in the
      published payload, and the page's index returns nothing at all for it. Not "1 result
      hidden": a withheld count discloses that private work matches that word (FR-009,
      Principle IV).
- [ ] T022 [P] [US2] In `tests/test_search.py`, simulate an archive built without FTS5 and
      assert the command refuses rather than degrading. `sqlite.has_search()` exists for this
      and has had no caller until now.

**Checkpoint**: The archive is answerable, from both sides, without either side telling the
other's secrets.

---

## Phase 5: User Story 3 — What one Tool means in this archive (Priority: P3)

**Goal**: One Tool, one screen: the span that can be claimed, the Artifacts behind it, and the
forks that contribute nothing to it.

**Independent Test**: Open a Tool that appears in at least one untouched fork. The claimed
count and the untouched count are both there and cannot be confused for each other.

### Implementation

- [ ] T023 [US3] Create `views/view-tool.js` — the profile, reading `first`, `last`,
      `artifact_count`, `untouched_count` and `attributed` from the Tool node and the member
      list from `indexes.tool_to_artifacts`, which v0.1 shipped unrendered.
- [ ] T024 [US3] Render the three states that are not a normal span: no claimable dates says
      *claims no dates* rather than an empty range (FR-013); `attributed: false` labels the
      window as observed activity, not the Author's (FR-012); and a subject that does not
      exist renders **the same** not-found as one that was withheld, because telling them
      apart is a disclosure.
- [ ] T025 [US3] Make the profile reachable from a search result and from a Tool node in any
      view, via `#tool/<node id>` (FR-014), in `views/screen.js` and `views/view-graph.js`.

### Tests for User Story 3

- [ ] T026 [US3] **The R7 guard** in `tests/test_tool_profile.py` — for every Tool in the real
      archive, the rows marked untouched (from each Artifact's published `authorship.share`)
      agree with the Tool's own `untouched_count`. They are two different measurements that
      should coincide and nothing enforces it. A profile showing four rows under a heading
      saying three is worse than one showing neither.
- [ ] T027 [P] [US3] In `tests/test_tool_profile.py`, assert a Tool whose every use was
      withheld is absent from the published payload entirely, so its profile cannot be reached
      by guessing its address.
- [ ] T028 [US3] **Only if T026 fails**: publish `indexes.tool_to_untouched` from the same pass
      that computes the span in `core/graph.py`, and write it into
      `specs/001-git-collector/contracts/graph.md`. Derived at build time, so no rescan and no
      store change (FR-020) — but a contract addition, and it gets documented rather than
      quietly reconciled.

**Checkpoint**: The résumé question is browsable, and the number that is claimed is
distinguishable from the number that is not.

---

## Phase 6: User Story 4 — From someone else's archive to your own (Priority: P4)

**Goal**: A stranger reaches their own published archive in three steps without reading source.

**Independent Test**: Hand the README to someone who has never seen the repository and time
them. This is the one check that cannot be automated.

**Note**: Depends on nothing else in this release and can move if anything slips. The spec
places it last for that reason, not because it matters least.

- [ ] T029 [US4] Write the three-step path in `README.md` — each step an action, each stating
      what the person will see when it worked, so a failure is visible at the step that caused
      it rather than at the end (FR-017).
- [ ] T030 [US4] At the step that first publishes anything, state exactly what the published
      site does and does not contain — private Artifacts excluded by default, contributor
      addresses never published, local paths never crossing (Principle IV, FR-018).
- [ ] T031 [P] [US4] Verify `templates/archive/` still matches the three steps: a fork of it
      produces a working archive without editing a source file (FR-016), and stopping after
      step one leaves a working thing rather than a broken half.
- [ ] T032 [US4] Time a stranger through it. Under 10 minutes, asking nothing (SC-004). Record
      what they got stuck on, if anything, in this file.

**Checkpoint**: The path from *interesting* to *I want one* exists and has been walked by
someone who did not write it.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T033 Add **View**, **Selection** and **Search result** to `CONTEXT.md` — new vocabulary
      lands there when it is resolved, not in a backlog. All three exist in the interface only
      and none is stored; say so, or the next person will look for the table.
- [ ] T034 Run [quickstart.md](./quickstart.md) end to end against the real archive, including
      the offline check with the network actually off and the frame probe in a real browser.
- [ ] T035 [P] Rebuild `examples/site/` from a fresh publish and sweep the copy again for
      addresses, local paths and absolute URLs. The demo is the thing a stranger opens; it
      must carry the release it advertises.
- [ ] T036 Decide SC-008's disposition and record it here. It arrives from v0.1 owed, not new:
      either an account of ~500 repositories is found and scanned, or the criterion is
      rewritten to state what can be observed. Carrying it a second time without deciding is
      how a validation becomes decoration.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: needs T002's baseline. **Blocks every user story.**
- **US1 (Phase 3)**: needs Phase 2. Blocks US2 and US3 — both need somewhere to live.
- **US2 (Phase 4)** and **US3 (Phase 5)**: need US1. Independent of each other.
- **US4 (Phase 6)**: needs nothing here. Can run at any point, by anyone.
- **Polish (Phase 7)**: needs whichever stories shipped.

```text
T001, T002  →  T003, T004  →  T005  →  US1 (T006–T015)
                                          ├──→ US2 (T016–T022)
                                          └──→ US3 (T023–T028)
US4 (T029–T032)  — independent, any time
```

### Parallel Opportunities

- T001 and T002 together.
- T004 alongside T003 — different files, no shared state.
- T011 and T013 alongside the T006–T010 sequence.
- T018 alongside T016 and T017 — `core/` and `views/` do not touch.
- T020, T022 and T027 alongside their implementation tasks.
- **US2 and US3 in parallel once US1 lands**, and US4 in parallel with everything.

### Within Each Story

The shell before the views that live in it. `core/` before the CLI command that calls it.
Every test that guards a privacy rule before the feature it guards is called done.

---

## Implementation Strategy

### MVP (US1 alone)

Phase 1 → Phase 2 → Phase 3, then stop and validate. One screen, both views, offline, frame
budget held. Worth shipping by itself: it removes the thing v0.1's own validation exposed —
two pages that do not know about each other.

### Incremental

1. Setup + Foundational → two modules, nothing visible changed.
2. **US1** → one screen. Ship.
3. **US2** → the archive answers questions. Ship.
4. **US3** → the résumé question is browsable. Ship.
5. **US4** → strangers can have their own. Ship.

Each step is publishable, and each one leaves the site working.

### If time runs short

Drop from the bottom. US4 first — it depends on nothing and its value is to the project
rather than to any visitor. US3 next. Never drop T021 or T027: they are the two privacy
guards, and Principle IV does not scale down with scope.

---

## Notes

- 36 tasks. US1 has 10, US2 has 7, US3 has 6, US4 has 4; the rest are setup, foundation and
  polish.
- Tests here are guards, not coverage. Each one names the defect it would catch, because a
  test whose failure nobody can interpret gets deleted by the next person in a hurry.
- **T028 is conditional.** It exists so that the answer to R7, whichever way it goes, is
  written down rather than absorbed.
- Commit after each task or logical group. The extraction commits (T003–T005) should be
  reviewable as *nothing changed*, and should say so with the numbers.
