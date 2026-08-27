# Phase 1 — Data model

The short version: **nothing is added to the store, and almost nothing to the graph.** This
page exists to say exactly which fields v0.2 finally reads, and to record the one addition
that would be allowed if R7 resolves against us.

## What v0.2 reads that v0.1 wrote and never used

| Field | Where | Written by v0.1 | Read by |
|---|---|---|---|
| `artifact_search(id, label, description)` | `graph.sqlite`, FTS5 virtual table | Populated on every build; `has_search()` guards a Python compiled without FTS5 | `core/search.py`, `dendro search` |
| `indexes.tool_to_artifacts` | `graph.json` | Emitted, documented as *present in v0.1, unrendered* | The Tool profile |
| `Artifact.description` | `graph.json` | Published for every non-aliased Artifact — **46 of 57** in the demo | The page's search |

That table is the whole reason this release needs no rescan. Each of those three was put
there in v0.1 with a note saying adding it later would force every Author to rebuild.

## Fields the Tool profile reads

All already published on the `Tool` node, all computed by `core/analysis/spans.py`:

| Field | Meaning | What the profile must do with it |
|---|---|---|
| `first` / `last` | The window of the Author's **own** commits in Artifacts using the Tool | Show as the claimed span. Absent means no claim — render *claims no dates*, never an empty range (FR-013) |
| `artifact_count` | Artifacts contributing dates | The claimed count |
| `untouched_count` | Artifacts using the Tool the Author never committed to | Show beside the claimed count, marked as contributing no dates. Omitted when zero |
| `attributed` | `false` when no `[archive].emails` are configured | Label the span as observed activity, not the Author's (FR-012) |

The same five fields now exist on `Technique` nodes as of v0.1's closing work. A Technique
profile is out of scope, and the spec says why: it is the same view with a different
subject, and the shape should be proven once first.

## Entities that exist only in the interface

Neither is stored, neither is published, and both are named here so the code does not invent
three words for each.

**View** — one way of reading the same archive: `graph`, `timeline`, `tool`. A view owns
rendering and nothing else. It does not own data, does not fetch, and does not hold the
selection. Views are told what is selected; they do not decide it.

**Selection** — the subject the reader is looking at: a node id, or nothing. It lives in the
shell, survives a view switch (FR-005), and is what the address carries (FR-003). A view
that cannot show the current selection — a Tool selected while the timeline is open — shows
its normal state rather than an error; the selection is not lost, just not rendered.

**Search result** — a subject, its kind, and why it matched: the name or the description.
Never a copy of the record. Selecting one moves the current view (FR-010), which is why a
result carries a node id and not a rendering.

## Address grammar

The fragment is the only part of a `file://` address that can carry state without a request.

```text
#graph                          the graph, nothing selected
#graph/root-4f2a…               the graph, that Artifact selected
#timeline                       the timeline
#timeline/root-4f2a…            the timeline, that Artifact highlighted
#tool/tool:rust                 the Tool profile for that Tool
#graph?q=melissa                the graph, with that search active
```

Deliberately **not** in the address: pan, zoom, layout seed. A shared address should land on
the same subject, not the same pixels — the layout is not stable across runs, and a fragment
carrying float coordinates would be unreadable (R4).

## The one addition that might become necessary

If the test guarding R7 fails — if marking untouched rows from `authorship.share` disagrees
with the Tool's own `untouched_count` on the real archive — the honest fix is to publish the
ids rather than reconcile the numbers quietly:

```json
"indexes": {
  "tool_to_artifacts":  { "tool:rust": ["root-…", "root-…"] },
  "tool_to_untouched":  { "tool:rust": ["root-…"] }
}
```

Derived at build time from the same pass that computes the span, so no rescan and no store
change — allowed by FR-020. It is a graph contract addition and would have to be written
into `contracts/graph.md`, not left to be discovered.

## What does not change

No new node type. No new edge type. No new inference. The graph vocabulary stays exactly as
the constitution closes it: Artifacts, Tools, Techniques, Periods, Collections, Authors,
Dependencies, Epoch Markers.
