# Phase 0 — Research: usable by a stranger

Eight questions the spec leaves to the plan. Each is answered from what v0.1 already
built and measured, not from preference; where a question is genuinely open, it says so
and names what would settle it.

---

## R1. Where does search run?

**Decision**: Two mechanisms, one vocabulary. The published page searches the payload it
has already loaded. The command line queries the FTS5 table in `graph.sqlite`.

**Rationale**: ADR-0004 forbids a library on the page, and there is no way to query SQLite
from a `file://` document without one. That closes the question for the page. What made the
answer cheap is that the data is already there: **46 of the 57 published Artifacts carry a
`description`** in `graph.json` today, because the contract publishes it for every
non-aliased Artifact. Searching names and descriptions on the page needs no new field, no
new build output and no rescan — which is what FR-020 demands.

The CLI is what `artifact_search(id, label, description)` was populated for. Its scope is
the whole store, including withheld Artifacts, because it runs on the Author's machine
against their own build.

**Alternatives considered**: *Ship a prebuilt search index into the payload* — rejected as
duplicate state; the payload already contains the strings. *Make FTS5 purely an export for
external consumers and give the CLI a linear scan* — rejected because the table is already
populated and `has_search()` already guards it; a linear scan would be slower and would
leave the v0.1 investment unused.

---

## R2. How does a single screen get built out of 1,445 lines of two pages?

**Decision**: Extract first, merge second. Three steps, each one shippable:

1. Move the graph renderer out of `views/graph.html` into a module the page loads. The page
   keeps working and looks identical.
2. Same for the timeline.
3. Add `views/index.html` — the shell that owns the view selector, the search field and the
   address — and stop emitting the two pages.

**Rationale**: `graph.html` is 1,057 lines and `timeline.html` is 388, almost all of it in
one inline `<script>` each. Merging them in one move means a single commit that touches
every line of the view layer, with no working state in between and nothing to bisect if the
frame budget moves. Steps 1 and 2 are pure extraction — the output is byte-identical and the
existing headless harnesses still apply. Only step 3 changes behaviour.

**Alternatives considered**: *One `index.html` with both scripts inline* — rejected at
1,445 lines in one file. *A build step that concatenates modules* — rejected: it adds a
toolchain to a project whose whole point is that a fork installs nothing.

---

## R3. The renderer cannot be called `views/graph.js`

**Decision**: View modules are prefixed: `view-graph.js`, `view-timeline.js`,
`view-tool.js`, plus `screen.js` for the shell and `search.js` for the index.

**Rationale**: `core/build.emit` writes the data file as `graph.js` and *then* copies
`views/*.js` over the same directory. A file named `views/graph.js` would silently overwrite
the archive with a renderer, and the failure would look like an empty graph rather than a
build error. The glob that copies view assets was added in v0.1 precisely so new view files
ship without a code change; the cost of that convenience is that names collide silently.

**Follow-up**: `tests/test_view_assets.py` should gain a case asserting no file in `views/`
is named after a build output. A comment would not survive the person who does not read it.

---

## R4. What lives in the address, on a `file://` page?

**Decision**: The fragment, and only three things: the view, the selected node, and the
active query — `#graph`, `#graph/root-4f2a…`, `#tool/tool:rust`, `#timeline?q=melissa`.

**Rationale**: A `file://` page has no server to route paths, so the fragment is the only
part of the address that can carry state without a request. It also survives being copied
into a message, which is the whole point of FR-003. Node ids are already opaque and already
public in the payload, so putting one in the address discloses nothing that opening the
archive does not.

**What deliberately does not go in**: pan, zoom and the layout seed. A shared address should
land on the same *subject*, not the same pixels; the layout is not stable across runs anyway,
and a fragment carrying float coordinates would be unreadable.

**Alternatives considered**: *Query string* — a `file://` URL keeps it, but it triggers a
reload on change in some browsers and reads as a server address. *No address state* —
rejected: FR-003, and because replacing two pages with one otherwise makes every existing
link dead with nothing offered in return.

---

## R5. How does the single screen avoid regressing the frame budget?

**Decision**: The graph's animation loop runs only while the graph view is on screen, and
stops entirely when the reader switches away. The simulation's settled state is kept, so
returning to the graph resumes rather than re-settles.

**Rationale**: v0.1's loop is already dirty-gated — it calls `requestAnimationFrame`
continuously but only draws when something changed. On the current pages that costs nothing
because there is only ever one view. On a single screen, an un-gated loop would keep the
graph's canvas alive underneath the timeline, and the layout costs roughly **70 ms per frame
while settling** in the Author's own full build of 3,283 nodes. SC-007 asks v0.2 not to make
this worse, and a loop that runs behind another view is exactly how it would get worse.

**Measured baseline to hold**: first render at 182 ms and 2,432 of 2,432 nodes on screen for
the published archive; 60fps in Chromium while panning at every zoom (T042, T089).

---

## R6. What does the CLI do when FTS5 is not available?

**Decision**: `dendro search` reports that the archive was built without a search index and
says how to get one, exits with the usage code, and never falls back to a scan that would
answer a different question quietly.

**Rationale**: `sqlite.has_search()` already exists for this: a Python compiled without FTS5
still produces a valid archive, it just has no `artifact_search` table. v0.1 made that a
silent, harmless absence because nothing queried it. v0.2 is the first caller, and Principle
I's *the machine is confident about what it observed* applies to the tool's own state as
much as to the data — a search that quietly degrades teaches the Author to distrust the
result they cannot see the basis for.

---

## R7. Which Artifacts in a Tool profile are the untouched ones? *(open)*

**Decision for now**: Show the authoritative `untouched_count` from the Tool node, mark
individual rows from each Artifact's published `authorship.share`, and **assert in a test
that the two agree** on the real archive.

**Why it is open**: they are two different measurements. `untouched_count` counts Artifacts
where `_own_window` found no dates for the Author. `authorship.share` is the proportion of
authored material that is theirs. They should coincide — no commits means no dates and no
share — but nothing enforces it, and a Tool profile that shows four rows marked untouched
under a heading saying three is worse than one that shows neither.

**What would settle it**: the test. If it passes on the real archive it stays as designed
and the test guards it. If it fails, the honest fix is to publish the untouched ids in
`indexes` — a graph schema addition, allowed by FR-020 because it is derived at build time
and needs no rescan, but a contract change that must be written down.

---

## R8. What happens to the addresses of `graph.html` and `timeline.html`?

**Decision**: They stop being emitted. No redirect stubs.

**Rationale**: A static redirect is a `<meta http-equiv="refresh">` file, which means the
build keeps emitting two pages forever to serve links that were shared during a version
almost nobody published. The demo in `examples/` and the README are the only two places that
name them, and both are in this repository and change with the release.

**Stated cost**: an Author who republishes breaks any link they shared to
`…/timeline.html`. FR-003 exists so the new addresses are worth sharing; this is the one
release where that trade is cheap, and it gets more expensive every version.

**Alternatives considered**: *Keep both pages and add a third* — rejected: three surfaces to
keep in step, and the spec's P1 story is that two surfaces already do not know about each
other.
