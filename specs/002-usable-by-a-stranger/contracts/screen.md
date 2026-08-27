# Contract: the single screen

One document, several views, one selection, one address.

## Files the build emits

| Emitted | Was |
|---|---|
| `index.html` | new — the shell |
| `screen.js`, `search.js`, `view-graph.js`, `view-timeline.js`, `view-tool.js` | new — view modules |
| `loader.js`, `theme.js`, `style.css`, `fonts/` | unchanged |
| `graph.js`, `graph.json`, `graph.sqlite`, `llms.txt` | unchanged |
| ~~`graph.html`~~, ~~`timeline.html`~~ | **no longer emitted** |

An Author who republishes breaks links they shared to `…/timeline.html`. That cost is
stated rather than mitigated (R8): a redirect stub means emitting two pages forever, and the
addresses being replaced were shared during a version almost nobody published.

**No view module may be named after a build output.** `core/build.emit` writes `graph.js`
and then copies `views/*.js` over the same directory, so `views/graph.js` would overwrite
the archive with a renderer and fail as an empty graph rather than a build error.
`tests/test_view_assets.py` asserts this.

## The shell owns three things

**The view.** Which one is showing. Switching is a control on the page — no document load,
no refetch (FR-001, FR-002). The archive is parsed once per visit.

**The selection.** A node id or nothing. It survives a view switch when the subject exists
in both (FR-005). A view that cannot render the current selection shows its normal state,
not an error — the selection is not lost, only not drawn.

**The address.** See the grammar in [data-model.md](../data-model.md#address-grammar).
Reloading or sharing restores the view, the selection and the query (FR-003).

Views own rendering and nothing else. They are told what is selected; they do not decide it,
do not fetch, and do not talk to each other.

## Lifecycle, and why it matters

A view is **activated** when it becomes visible and **suspended** when another takes over.

The graph's animation loop runs only while the graph is active. It is dirty-gated already —
it draws only when something changed — but on a single screen an always-running loop would
keep costing behind the timeline, and the Author's own full build costs roughly 70 ms per
frame while the layout settles at 3,283 nodes. Suspending keeps the settled layout, so
returning resumes rather than re-settles.

**The budget this must not exceed** (v0.1 measured, SC-007 carries it):

| | |
|---|---|
| First render | 182 ms at 2,432 nodes — must stay under 2 s at 3,000 |
| Panning | 60fps in Chromium, at every zoom |
| Nodes on screen once settled | all of them |

## Behaviour every view owes

- Works from `file://` with the network unplugged. Nothing is fetched on demand (FR-004).
- Renders an archive of one Artifact without looking broken. An empty graph, a one-row
  timeline and a search with nothing to find are normal states, not errors.
- Has a way to say *this claims nothing* that is distinguishable from *this has not loaded*.
- Lands somewhere sensible when addressed with a subject that no longer exists, and says
  what happened — with **one rendering for both** "withheld" and "never existed", because
  telling them apart is a disclosure.

## The Tool profile

A view like the others, addressed `#tool/<node id>`, showing:

- the claimed span, or *claims no dates* when there is none (FR-013);
- the Artifacts that use it, from `indexes.tool_to_artifacts`;
- the untouched forks, marked as contributing no dates, counted by the Tool node's own
  `untouched_count`;
- a span labelled as observed activity rather than the Author's when `attributed` is `false`
  (FR-012).

Reachable from a search result and from the Tool's node in any view (FR-014).
