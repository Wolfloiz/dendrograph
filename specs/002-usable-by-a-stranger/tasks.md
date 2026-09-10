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

- [X] T001 [P] Extend `tests/test_view_assets.py` — assert no file in `views/` is named after
      a build output (`graph.js`, `graph.json`, `graph.sqlite`, `llms.txt`). Catches the
      silent overwrite in R3: `emit` writes the data then copies `views/*.js` over it, so
      `views/graph.js` would replace the archive with a renderer and fail as an empty graph
      rather than a build error.
- [X] T002 [P] Add a guard in `tests/test_derived_outputs.py` pinning the graph's node
      and edge type sets to a literal list. FR-019 makes *no new node type, edge type or
      inference* a requirement of this release, and the nearest existing test only asserts
      that `llms.txt` mentions each type — it would not notice a new one arriving. This is
      what keeps v0.2 honest about being a reach release rather than a collection one.
- [X] T003 Capture the pre-extraction baseline with the jsdom op-counting harness against
      `views/graph.html` and `views/timeline.html` at 3,283 nodes: frames to settle, nodes on
      screen once settled, labels drawn at rest and zoomed, and per-frame `fill` / `drawImage`
      / `arc` / `set font` counts. Record it in the scratchpad and quote it in the T006 commit
      — it is the only thing that can prove the extraction changed nothing.
  - Measured 2026-08-29 against the full build (3,283 nodes). **Graph**: settles at frame 619,
    3,286 arcs in the last frame, 31 labels at rest and 55 / 200 at eight and sixteen wheel
    steps, canvas trace hash `f16700aaba5c31b9`, DOM hash `d8e474689c0d082a`. **Timeline**:
    709 elements, DOM hash over the same data. Op totals across the settle:
    `fill=1270 stroke=1270 arc=2063728 drawImage=20993 set font=647 clearRect=635`.

**Checkpoint**: The naming trap is closed and there is a number to hold the refactor to.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Turn 1,445 lines of two inline `<script>` tags into modules, without changing
one pixel. This blocks every user story, and it is the phase most likely to break something
invisibly — which is exactly why it ships before anything that would mask it.

**⚠️ CRITICAL**: No user story work begins until T006 proves equivalence.

- [X] T004 Extract the graph renderer from `views/graph.html` into `views/view-graph.js`,
      exposing `DendroViewGraph.create(container, graph, options)` returning
      `{ activate, suspend, select, search }`. `views/graph.html` loads the module and keeps
      working; behaviour is unchanged, `suspend` may be a stub until T010.
- [X] T005 [P] Extract the timeline renderer from `views/timeline.html` into
      `views/view-timeline.js` with the same factory shape. `views/timeline.html` loads it and
      keeps working.
- [X] T006 Re-run the T003 harness against the extracted modules and confirm every number is
      identical. A difference here is a behaviour change nobody asked for; fix it rather than
      re-baseline it.
  - **Every number identical**, including both hashes. Compared the pre-extraction views out
    of git against the post-extraction ones over the *same* data, because a rebuild moves
    `generated_at` and the timeline prints it — the only diff that ever appeared was that
    timestamp, and pinning the data made it vanish.

**Checkpoint**: Two working pages, two modules, identical output. Bisectable from here.

---

## Phase 3: User Story 1 — One screen instead of two pages (Priority: P1) 🎯 MVP

**Goal**: Every view of the archive on a single screen, sharing one load, one selection and
one address.

**Independent Test**: Open the archive, switch views, confirm the data was fetched once and
the selected node survived. Then unplug the network and do it again.

### Implementation

- [X] T007 [US1] Create `views/index.html` — the shell: header, view selector, a slot for the
      search field, and the view container. Loads `graph.js`, `loader.js`, `theme.js` and the
      view modules; carries no rendering logic of its own.
- [X] T008 [US1] Create `views/screen.js` — the view registry, activation and suspension, and
      the selection that lives in the shell rather than in any view (per
      [contracts/screen.md](./contracts/screen.md)). Views are told what is selected; they do
      not decide it.
- [X] T009 [US1] Add fragment routing to `views/screen.js` — parse and serialise
      `#graph`, `#graph/<node id>`, `#tool/<node id>`, `#timeline?q=<query>` per the grammar
      in [data-model.md](./data-model.md#address-grammar). Pan, zoom and the layout seed stay
      out on purpose: a shared address lands on the same subject, not the same pixels.
- [X] T010 [US1] Stop the graph's animation loop in `views/view-graph.js` when the view is
      suspended, keeping the settled layout so returning resumes rather than re-settles. This
      is the SC-007 regression the single screen is most likely to introduce — the loop is
      dirty-gated, which costs nothing on a page with one view and keeps costing behind a
      timeline at ~70 ms a frame while settling.
- [X] T011 [US1] Carry the selection across a view switch in `views/screen.js` and
      `views/view-timeline.js` — an Artifact selected in the graph is highlighted in the
      timeline. A view that cannot render the current selection shows its normal state, never
      an error.
- [X] T012 [P] [US1] Extend `views/style.css` with the shell: view selector, layout, and the
      narrow-screen rule where the timeline is the view that survives. Extend, do not rewrite
      — the design tokens and the `.eyebrow` rule are shared with what exists.
- [X] T013 [US1] Delete `views/graph.html` and `views/timeline.html`. `core/build.py` needs no
      change: the glob added in v0.1 already carries whatever is in `views/`. State the broken
      addresses in the commit rather than adding redirect stubs (R8).
- [X] T014 [US1] Update `README.md` and `examples/README.md` to name `site/index.html`
      instead of `site/timeline.html`. **Not parallel**: T031 rewrites `README.md` too, and
      US4 is invited to run at any time — the two must not be open at once.

### Tests for User Story 1

- [X] T015 [P] [US1] Add `tests/test_screen.py` — the emitted file set is exactly what
      [contracts/screen.md](./contracts/screen.md) lists, and `graph.html` / `timeline.html`
      are gone. Catches a build that quietly keeps shipping the old pages.
- [X] T016 [US1] Extend the jsdom harness to prove the graph's loop draws **zero frames** while
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

- [X] T017 [US2] Create `views/search.js` — an index over Artifact, Tool and Technique names
      plus Artifact descriptions, built from the payload already in memory. **46 of the 57
      published Artifacts carry a description today**, so this needs no new build output and no
      rescan (FR-020). Prefix matches rank above substring matches, better-connected first.
- [X] T018 [US2] Wire search into `views/index.html` and `views/screen.js` — the field, the
      results, and selecting a result moving the current view rather than replacing the screen
      (FR-010). Each result names its kind and why it matched: name or description.
- [X] T019 [P] [US2] Create `core/search.py` — FTS5 queries over `artifact_search` in
      `graph.sqlite`, ordered by rank then name. Ordering must stay mechanical and explainable
      in one sentence; anything that looks like a judgement about which Artifact matters more
      is an inference the tool does not make (Principle I).
- [X] T020 [US2] Add the `search` command to `cli.py` per
      [contracts/search.md](./contracts/search.md), and record it in
      `specs/001-git-collector/contracts/cli.md`. With no FTS5 table it refuses with exit `2`
      and says how to get one — it never falls back to a scan that answers a different
      question quietly (R6).

### Tests for User Story 2

- [X] T021 [P] [US2] Add `tests/test_search.py` — CLI results carry the kind, the subject and
      why each matched; a query matching nothing exits `0` and says so.
- [X] T022 [US2] **The privacy guard** in `tests/test_search.py` — a term appearing only in a
      withheld Artifact's description is findable from the CLI and appears **nowhere** in the
      published payload, and the page's index returns nothing at all for it. Not "1 result
      hidden": a withheld count discloses that private work matches that word (FR-009,
      Principle IV).
- [X] T023 [P] [US2] In `tests/test_search.py`, simulate an archive built without FTS5 and
      assert the command refuses rather than degrading. `sqlite.has_search()` exists for this
      and has had no caller until now.
- [X] T024 [US2] Measure search latency against the real archive at 3,283 nodes with the
      jsdom harness and hold it under the 50 ms per keystroke SC-005 asks for. The index is
      bigger than it looks — 46 of the 57 published Artifacts carry prose — and a scan per
      keystroke across all of it is exactly the cost that is invisible in a demo and felt in
      a real archive.
  - Measured 2026-08-29 against the full build, 3,286 nodes, 50 of 97 Artifacts carrying
    prose: index built in **2.3 ms**, mean **0.13 ms** per keystroke over 42 queries typed
    letter by letter, worst **2.96 ms** on `m` with 56 results. SC-005 asks for under 50 ms;
    the margin is seventeen-fold. The scan is linear over a payload that is already in
    memory, and at this size linear is simply cheap.

**Checkpoint**: The archive is answerable, from both sides, without either side telling the
other's secrets.

---

## Phase 5: User Story 3 — What one Tool means in this archive (Priority: P3)

**Goal**: One Tool, one screen: the span that can be claimed, the Artifacts behind it, and the
forks that contribute nothing to it.

**Independent Test**: Open a Tool that appears in at least one untouched fork. The claimed
count and the untouched count are both there and cannot be confused for each other.

### Implementation

- [X] T025 [US3] Create `views/view-tool.js` — the profile, reading `first`, `last`,
      `artifact_count`, `untouched_count` and `attributed` from the Tool node and the member
      list from `indexes.tool_to_artifacts`, which v0.1 shipped unrendered.
- [X] T026 [US3] Render the three states that are not a normal span: no claimable dates says
      *claims no dates* rather than an empty range (FR-013); `attributed: false` labels the
      window as observed activity, not the Author's (FR-012); and a subject that does not
      exist renders **the same** not-found as one that was withheld, because telling them
      apart is a disclosure.
- [X] T027 [US3] Make the profile reachable from a search result and from a Tool node in any
      view, via `#tool/<node id>` (FR-014), in `views/screen.js` and `views/view-graph.js`.

### Tests for User Story 3

- [X] T028 [US3] **The R7 guard** in `tests/test_tool_profile.py` — for every Tool in the real
      archive, the rows marked untouched (from each Artifact's published `authorship.share`)
      agree with the Tool's own `untouched_count`. They are two different measurements that
      should coincide and nothing enforces it. A profile showing four rows under a heading
      saying three is worse than one showing neither.
- [X] T029 [P] [US3] In `tests/test_tool_profile.py`, assert a Tool whose every use was
      withheld is absent from the published payload entirely, so its profile cannot be reached
      by guessing its address.
- [X] T030 [US3] **Only if T028 fails**: publish `indexes.tool_to_untouched` from the same pass
      that computes the span in `core/graph.py`, and write it into
      `specs/001-git-collector/contracts/graph.md`. Derived at build time, so no rescan and no
      store change (FR-020) — but a contract addition, and it gets documented rather than
      quietly reconciled.
  - **R7 resolved against the derivation, on the real archive.** JavaScript listed 13 rows
    against its own `untouched_count` of 12. The two are different questions and one
    Artifact answers them differently: the Author committed to it without adding lines, so
    it has a date window and a `share` that rounds to nothing. `indexes.tool_to_untouched`
    is published from the same pass that computes the span, documented in
    `contracts/graph.md`, and `tests/test_tool_profile.py` holds the count to the list.

**Checkpoint**: The résumé question is browsable, and the number that is claimed is
distinguishable from the number that is not.

---

## Phase 6: User Story 4 — From someone else's archive to your own (Priority: P4)

**Goal**: A stranger reaches their own published archive in three steps without reading source.

**Independent Test**: Hand the README to someone who has never seen the repository and time
them. This is the one check that cannot be automated.

**Note**: Depends on nothing else in this release and can move if anything slips. The spec
places it last for that reason, not because it matters least.

- [X] T031 [US4] Write the three-step path in `README.md` — each step an action, each stating
      what the person will see when it worked, so a failure is visible at the step that caused
      it rather than at the end (FR-017).
- [X] T032 [US4] At the step that first publishes anything, state exactly what the published
      site does and does not contain — private Artifacts excluded by default, contributor
      addresses never published, local paths never crossing (Principle IV, FR-018).
- [X] T033 [P] [US4] Verify `templates/archive/` still matches the three steps: a fork of it
      produces a working archive without editing a source file (FR-016), and stopping after
      step one leaves a working thing rather than a broken half.
- [X] T034 [US4] Build an archive from `templates/archive/` holding a single Artifact and
      confirm every view renders it: a graph of one node, a one-row timeline, a search with
      nothing to find, and a Tool profile if any Tool exists. This is the first thing every
      adopter sees, and US4's third acceptance scenario — stopping after step one leaves a
      working thing rather than a broken half — is not true until something checks it.
- [ ] T035 [US4] **Partly done; still needs a stranger.** Walk a stranger through it against
      SC-004 as rewritten: asking nothing, opening no source file, every command running as
      pasted, each *You should see* matching, and under 10 minutes of their own time with the
      waiting removed. Record what they got stuck on, if anything, here.
  - **Walked by the Author, 2026-09-10: about twelve minutes, and most of it was the
    clones, not the commands.** This does not close SC-004 — the criterion says *a stranger
    with no prior knowledge*, and the Author wrote the thing. What it does establish is
    where the twelve minutes went, which no stranger's stopwatch would have told us any
    better: downloading repositories dominated, and the reading and typing did not.
  - Two defects surfaced on the way and are fixed: `scan github:<your-account>` could not be
    pasted, because `<word` is an input redirect in zsh and bash; and `login` printed
    "0 Artifact(s) added, 0 changed" directly under "Already authenticated", which reads as
    the authentication having failed. Both were found by running the text rather than
    reading it, which is the whole argument for this task existing.
  - **`--filter=blob:none` was measured and rejected — do not retry it.** The collector
    clones full history with `--no-checkout` (FR-024 needs the root commit and the per-author
    counts), and full history means every version of every file. A partial clone looks like
    the obvious fix and is not. On `tinygrad/tinygrad` (14,753 commits):

    | | clone | then `ls-tree -r --long HEAD` | on disk |
    |---|---|---|---|
    | `--no-checkout` (today) | 8.78 s | **0.00 s** | 127 MB |
    | `+ --filter=blob:none` | 2.24 s | **280 s, unfinished** | 21 MB |

    Same commit count and the same root SHA both ways, so identity survives — but `--long`
    needs each blob's size, and a partial clone fetches the missing blobs one at a time.
    The clone gets 4x faster and the command after it becomes unusable. Anything in this
    direction has to deal with `--long` first.
  - **This put a question to SC-004, and T040 answered it.** The old criterion timed a
    stranger to their published archive, but the measurement was dominated by how many
    repositories they own and how fast their connection is — neither of which the README can
    change. SC-004 is now split: the interface conditions here, the cost of the waiting under
    SC-008, which already governs it.

**Checkpoint**: The path from *interesting* to *I want one* exists and has been walked by
someone who did not write it.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T036 Add **View**, **Selection** and **Search result** to `CONTEXT.md` — new vocabulary
      lands there when it is resolved, not in a backlog. All three exist in the interface only
      and none is stored; say so, or the next person will look for the table.
- [X] T037 Run [quickstart.md](./quickstart.md) end to end against the real archive, including
      the offline check and the frame probe in a real browser.
  - **Done headlessly, 2026-08-29.** No absolute URL in any published file, so nothing is
    fetched. The 40 withheld Artifacts leak neither name nor description into `graph.json`,
    `graph.js` or `graph.sqlite` — the one apparent hit was the tool naming itself in
    `generator`, not an Artifact. `dendro search` answers from the whole archive, the page
    index answers in 2.96 ms worst-case, the screen passes 15 interaction checks, and the
    Tool profile's count matches its list on every Tool.
  - **Done in a browser, 2026-09-10.** Chrome 152, 1920x993, `examples/site/` — the real
    published archive, 2,433 nodes and 2,714 edges. Three runs: two over `http://127.0.0.1`
    and one from `file://` with no server behind the site's own files. **SC-007 passes on
    both halves.**

    | | file:// | http | http |
    |---|---|---|---|
    | first render | **381.8 ms** | 688.3 ms | 835.9 ms |
    | pan at fit | 59.6fps *(ceiling 59.7)* | 58.8 *(58.9)* | 59.5 *(59.6)* |
    | pan at min zoom `k=0.05` | 58.3 *(58.7)* | 53.7 *(60.0)* | 58.6 *(58.9)* |
    | pan at max zoom `k=6` | 59.6 *(60.0)* | 59.7 *(60.0)* | 59.0 *(59.4)* |
    | frames behind the timeline | **0** | **0** | **0** |

  - **Nothing is fetched, proven twice.** From `file://` the only network requests in the
    whole run were the probe's own reports to the harness; the site asked for nothing. Over
    http the page made 16 requests, every one same-origin. The three absolute URLs that do
    exist in the files are not fetches: `scripts.sil.org` is prose in the OFL licence,
    `packtpub.com` is an Artifact's locator inside `graph.json`, and `w3.org/2000/svg` is
    the XML namespace in `logo.svg`. The network was not physically unplugged — cutting it
    would have cut the session doing the measuring — but with zero requests leaving the
    page there is nothing left for an unplugged cable to change.
  - **The regression the single screen was most likely to introduce did not happen.** Zero
    frames drawn behind the timeline, in all three runs. `suspend()` genuinely stops the
    loop rather than leaving it dirty-gated and running.
  - **Panning is vsync-bound, not compute-bound.** Painted frames equal the display's
    ceiling at every zoom — the probe counted both, and the graph draws every frame the
    browser offers. Median gap 16.7 ms throughout. The one exception is the first http run
    at minimum zoom, 53.7fps against a 60.0 ceiling with a single 303 ms stall; it did not
    reproduce in either later run at the same zoom, so it reads as a one-off collection
    pause rather than a cost that scales with zoom.
  - **First render is 2.1x v0.1's 182 ms, and under SC-007's 2 s ceiling by 5x.** The
    comparable number is `file://`'s 381.8 ms; http's 688–836 ms carries 723 KB of
    `graph.js` over the wire. Run 2's breakdown puts 547.7 ms of that *after* `graph.js`
    was already available, so it is work and not transport. v0.1 measured a page that
    loaded one view; the single screen loads eight scripts before it can paint, which is
    what US1 bought. Worth knowing, not worth blocking on.
  - **Not a criterion, but measured and worth recording**: the force simulation runs 17–24
    seconds before it settles, drawing every frame while it converges.
  - Instrumented by hooking `clearRect` — `draw()` is its only caller in the whole site
    (`view-graph.js:353`), so the count is painted frames and not `frame()` calls, which
    fire every rAF even when `dirty` is false. The harness lived entirely outside the
    repository. Two traps worth writing down for whoever repeats this: Chrome suspends
    `requestAnimationFrame` **and** `setTimeout` in a background tab, so a probe driven
    from a tab that never comes to the front measures the freeze and not the product — the
    first numbers this task produced were exactly that, and were thrown away; and the
    browser extension cannot drive `file://` at all, so that half has to be opened by hand.
- [X] T038 [P] Rebuild `examples/site/` from a fresh publish and sweep the copy again for
      addresses, local paths and absolute URLs. The demo is the thing a stranger opens; it
      must carry the release it advertises.
  - Replaced rather than copied over: `cp -r` into an existing directory leaves whatever it
    does not overwrite, and the first attempt shipped `graph.html` and `timeline.html`
    alongside the new screen — the same defect the build had, in the copy step. Swept
    clean: no address, no local path, no absolute URL.
- [X] T039 Decide SC-008's disposition and record it here. It arrives from v0.1 owed, not new:
      either an account of ~500 repositories is found and scanned, or the criterion is
      rewritten to state what can be observed. Carrying it a second time without deciding is
      how a validation becomes decoration.
  - **Decided: rewritten.** No ~500-repository account exists to point it at, and none is
    coming. SC-008 now states the thing that can be observed — progress throughout, an
    unattended finish, and a per-repository cost that stays linear under 4 seconds — which
    is what the original was protecting. The 500 in the old wording was never about the
    software; it was a stand-in for "big enough that a hang would matter", and linearity
    measured across 500 synthetic repositories says more about that than one account ever
    would.
- [X] T040 Decide SC-004's disposition and record it here. T035's walk showed the criterion
      measures the network as much as the interface; either it says which it means, or the
      next person passes it by owning fewer repositories.
  - **Decided: rewritten, split rather than relaxed.** The old sentence bundled two things
    that fail for unrelated reasons — a README that confuses someone, and a link that is
    slow. T035 took about twelve minutes and the clones were the larger part, so under the
    old wording it fails; and yet the same walk found two genuine interface defects, which
    is the criterion working. Scoring both on one stopwatch hides each behind the other.
  - SC-004 now carries four observable interface conditions — asks nothing, opens no source
    file, every command runs as pasted, every *You should see* matches — plus a ten-minute
    bound on the walker's **own** time, with the clock stopped while anything downloads.
    The cost of the waiting moves to SC-008, which already states it as a per-repository
    number and is the criterion that can actually be failed by the software.
  - Same shape as T039, and for the same reason: keep what the original was protecting,
    drop the part that was never about the software. The pattern is worth naming, because
    it has now happened twice — a criterion phrased as one number over a whole journey
    measures whatever dominates the journey, which is rarely the thing under test.
- [ ] T041 **Close the fixture blind spot structurally, not case by case.** Two privacy
      leaks shipped for the same reason and were found the same way — by building against a
      real account, never by a test. `DEPENDS_ON` published a private Artifact's whole
      manifest, and `IN_COLLECTION` published the Author's own name for the work. Both were
      invisible because `archives.private()` did not carry the field, so the sweep in
      `tests/test_alias.py` had nothing to sweep.
  - The audit that found them, run 2026-09-10, and what it still says:

    | `store.Artifact` field | private fixture carries it | shielded under alias |
    |---|---|---|
    | tools, techniques, sources, content_hashes, description | yes | yes |
    | dependencies | yes *(added T041's first fix)* | yes *(fixed)* |
    | **authorship** | **no — gate exists, never exercised** | yes |
    | **declarations_applied** | **no** | unknown, never tested |

    Eight edge types exist. `USES`, `APPLIES`, `IN_PERIOD`, `AUTHORED_BY`, `DEPENDS_ON`,
    `DERIVES_FROM`, `SUCCEEDS` and `IN_COLLECTION` are now all accounted for — but three of
    them are accounted for only by reading the code, because no fixture drives them.
  - **The work**: give `archives.private()` every field an Artifact can hold, each carrying
    the client's name the way `DEPENDENCY_NAME` does, so the existing `SECRETS` sweep
    exercises all of them. Then add the test that makes this class of defect impossible to
    reopen: enumerate `dataclasses.fields(store.Artifact)` and fail when the private fixture
    leaves one empty. A field added in v0.3 then fails a test the day it is added, instead of
    shipping and being found by someone building a demo.
  - **Why the shield moved to the builder** (done, recorded here because it is the shape the
    rest should follow): a per-loop `if aliased` cannot protect an edge emitted outside that
    loop, which is exactly how `IN_COLLECTION` escaped — it is written in the `if config:`
    block. `GraphBuilder.shield(node, *edge_types)` declares once what may not touch an
    anonymous node, and `edge()` enforces it wherever the edge is emitted. New edge types
    should be added there, not guarded again at each call site.
  - Also unresolved and worth a look in the same pass: a node that exists **only** to be
    connected leaks through its label alone. A Collection whose every member was anonymous
    published `Acme client work` with no edges at all until this was fixed by not creating
    the node. Check whether Tool, Technique, Period or Dependency can reach that state.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: needs T003's baseline. **Blocks every user story.**
- **US1 (Phase 3)**: needs Phase 2. Blocks US2 and US3 — both need somewhere to live.
- **US2 (Phase 4)** and **US3 (Phase 5)**: need US1. Independent of each other.
- **US4 (Phase 6)**: needs nothing here. Can run at any point, by anyone — with one
  exception: T014 and T031 both edit `README.md` and must not be open at once.
- **Polish (Phase 7)**: needs whichever stories shipped.

```text
T001, T003  →  T004, T005  →  T006  →  US1 (T007–T016)
                                          ├──→ US2 (T017–T023)
                                          └──→ US3 (T025–T030)
US4 (T031–T035)  — independent, any time
```

### Parallel Opportunities

- T001 and T003 together.
- T005 alongside T004 — different files, no shared state.
- T012 alongside the T007–T011 sequence. **Not T014**: it edits `README.md`, which
  T031 rewrites.
- T019 alongside T017 and T018 — `core/` and `views/` do not touch.
- T021, T023 and T029 alongside their implementation tasks.
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
rather than to any visitor. US3 next. Never drop T022 or T029: they are the two privacy
guards, and Principle IV does not scale down with scope.

---

## Notes

- 39 tasks. US1 has 10, US2 has 8, US3 has 6, US4 has 5; the rest are setup, foundation
  and polish.
- Tests here are guards, not coverage. Each one names the defect it would catch, because a
  test whose failure nobody can interpret gets deleted by the next person in a hurry.
- **T030 is conditional.** It exists so that the answer to R7, whichever way it goes, is
  written down rather than absorbed.
- Commit after each task or logical group. The extraction commits (T004–T006) should be
  reviewable as *nothing changed*, and should say so with the numbers.
