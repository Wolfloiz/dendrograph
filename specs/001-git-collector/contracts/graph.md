# Contract: derived outputs — `graph.json`, `graph.sqlite`, `llms.txt`

Build outputs, regenerated from `store/` on every run (ADR-0002). Deleting them costs
nothing. They are the contract between the core stream and everything downstream: the
views, third-party programs, and AI agents (FR-017).

**Privacy applies here, not in the store.** Private Artifacts are in the store and are
filtered out of these outputs when they are built for publication. See *Build modes*.

## `graph.json`

Target: ~500 Artifacts → under 1 MB, first render under 2 seconds (SC-005). Measured,
500 Artifacts produce ~554 nodes, not the ~3,000 first assumed: Tool, Technique, Period,
Author and Dependency nodes are shared rather than one set per Artifact.

```json
{
  "schema_version": 1,
  "generated_at": "2026-08-24T14:02:11Z",
  "generator": "dendrograph 0.1.0",
  "build_mode": "public",
  "schema": {
    "node_types": ["Artifact", "Tool", "Technique", "Period", "Collection", "Author", "Dependency", "EpochMarker"],
    "edge_types": ["USES", "APPLIES", "IN_PERIOD", "IN_COLLECTION", "AUTHORED_BY", "DEPENDS_ON", "DERIVES_FROM", "SUCCEEDS"]
  },
  "nodes": [
    { "id": "root-3f7a1c9e...", "type": "Artifact", "label": "dendrograph",
      "description": "A knowledge graph of what you have built.",
      "first": "2019-03-11", "last": "2026-08-20", "authorship": { "share": 0.87 } },
    { "id": "tool:python", "type": "Tool", "label": "Python",
      "first": "2019-03-11", "last": "2026-08-20", "artifact_count": 12,
      "untouched_count": 2 },
    { "id": "period:2019", "type": "Period", "label": "2019" },
    { "id": "root-8c2d5a1f...", "type": "Artifact", "label": "Anonymous fintech project",
      "aliased": true, "first": "2019-06-02", "last": "2021-11-30" }
  ],
  "edges": [
    { "from": "root-3f7a1c9e...", "to": "tool:python", "type": "USES" },
    { "from": "root-3f7a1c9e...", "to": "period:2019", "type": "IN_PERIOD" }
  ],
  "indexes": {
    "tool_to_artifacts": { "tool:python": ["root-3f7a1c9e..."] }
  },
  "aggregates": {
    "private_withheld": { "count": 4, "tools": ["Rust"], "first": "2019", "last": "2021" }
  },
  "unreachable_sources": [
    { "kind": "local", "last_seen": "2025-11-02" },
    { "kind": "github", "locator": "https://github.com/author/thing", "last_seen": "2026-02-14" }
  ]
}
```

| Field | Notes |
|---|---|
| `schema` | Self-describing, so a consumer needs no companion docs (FR-017). |
| `build_mode` | `public` \| `redacted` \| `full`. See *Build modes*. |
| `nodes` / `edges` | Node ids: Artifacts use their store id; every other type uses `<lowercase type>:<slug>`. |
| `Tool.first` / `.last` / `.artifact_count` | The Tool's span, computed over **the Artifacts present in this build**. Under `public` that is public, aliased and opted-in Artifacts; a span there is deliberately narrower than the Author's own, because a visitor must not learn that private work existed in an interval (FR-027). See *Whose dates a span reports*. |
| `Tool.untouched_count` | Artifacts using the Tool that the Author never committed to. Omitted when zero. They contribute no dates, but they are not hidden — the Author has to be able to explain why the count does not match what they see in the archive. |
| `Tool.attributed` | Present and `false` when no `[archive].emails` are configured. Omitted otherwise. |
| `Technique.first` / `.last` / `.artifact_count` / `.untouched_count` / `.attributed` | The same fields, computed the same way, over the Artifacts that applied the Technique in this build. See *What a Technique span does not say* — `first` is **not** an adoption date. |
| `Artifact.description` | Omitted when absent, and **omitted entirely for an aliased Artifact** — a description names the client as plainly as the real name does (ADR-0011). |
| `Artifact.aliased` | Present and `true` when the node is a private Artifact published under an alias. `label` is the Author's chosen or generated label, never the real name (FR-028, ADR-0011). The **id is not aliased**: it stays the store id, which is the root commit SHA, and is reproducible by anyone holding a clone of the repository. Known and accepted — see ADR-0011. `DEPENDS_ON` edges do **not** cross unless `reveal` names `dependencies`: a manifest identifies without naming. |
| `indexes.tool_to_artifacts` | Reverse index. **Present in v0.1, unrendered** — v0.2 needs it and adding it later means rebuilding every published archive. |
| `indexes.tool_to_untouched` | The Artifacts behind `Tool.untouched_count`, by id. Added in v0.2 for the Tool profile. Omitted for a Tool with none. It exists because deriving the list from `authorship.share` gave a different answer: `share` is how much of the material is the Author's, `untouched` is whether they committed at all, and a repository they committed to without adding lines has a date window and a share of zero. In the Author's own archive that was 13 rows under a heading saying 12. |
| `aggregates.private_withheld` | Only in `redacted` mode; absent otherwise. Counts, Tools and a date range, never names (FR-013, ADR-0005). |
| `unreachable_sources` | Sources the archive knows it cannot reach, reported rather than omitted (FR-019). Derived from the store, not from the run: a rebuild has not scanned anything, and "could not reach it" is a state the store carries between runs. Only sources of Artifacts present in this build appear — a source with no visible Artifact behind it would tell a visitor that private work exists. A `local` locator is withheld from a published build (`kind` and `last_seen` still appear); a `github` locator is already public and already in the graph, so it stays. |

### Whose dates a span reports

Within each Artifact the window is the **Author's own commits**, taken from the per-author
`first`/`last` the store already records — not the Artifact's whole activity.

A fork carries its upstream's history. `gpuocelot`, forked with commits back to 2009, made
C++, Docker, Python and Shell all report "first used 2009" for an account whose own work
starts in 2020. Reading that off the page as seventeen years of C++ is exactly the
overstatement ADR-0009 rules out, and it puts SC-007 — *state years of experience with no
estimation from memory* — on the wrong side of correct.

So:

- An Artifact the Author has no commits in contributes **no dates** and does not count
  toward `artifact_count`. It is counted in `untouched_count` instead.
- A Tool that appears **only** in such Artifacts gets `artifact_count: 0` and no dates. The
  archive still shows the Tool and the `USES` edges; the span simply claims nothing.
- With **no `emails` configured** there is no "own" to measure. The span falls back to
  observed activity and is marked `attributed: false`, so a view can say what it is rather
  than pass a fork's dates off as the Author's. `views/timeline.html` renders this in a
  *Basis* column: `yours`, `+N untouched`, `forks only`, or `observed, not yours`.

This is the one place where configuring `[archive].emails` changes what the output *means*
rather than only what it contains.

Technique spans count every Artifact whose `APPLIES` edge was published, aliased ones
included. That is not a leniency: an aliased Artifact's `APPLIES` edge crosses by design —
without its evidence pointer — and a span that counted fewer would give a Technique five
edges and three Artifacts. A Tool span excludes aliased Artifacts for the mirror-image
reason: their `USES` edge does not cross unless `reveal` names `tools`.

### What a Technique span does not say

A Technique is inferred from `tracked_files`, which is the tree at HEAD. So what was
observed is that the marker is there **now**.

- `first` is the earliest the Author worked on an Artifact that shows the marker **today**.
  It is not the date the Technique was adopted, and a project that adopted it last month
  reads as having had it from its first commit.
- A Technique adopted and later abandoned leaves no trace, so it never appears at all.

Both are consequences of observing a tree rather than a history, and neither is a defect to
be fixed by widening the span — reading adoption dates would mean walking commits for the
marker's first appearance, which is a collector change, not a graph one. Until then the
field is what it is, said out loud, in the same spirit as `untouched_count`.

### `authorship.share`

The proportion of an Artifact's authored material that belongs to the Author, between 0
and 1. This is what lets a view size a node and lets an untouched fork (share near 0) read
differently from a rewritten one, which is what ADR-0003 asks for.

**Commits and lines stay in the store**, where the git collector wrote them. The graph does
not know what a commit is — collectors know about repositories and commits; the graph does
not (Principle V). A future non-git collector computes `share` over whatever it measures,
with no redesign.

### Edge types

| Edge | From → To | Origin |
|---|---|---|
| `USES` | Artifact → Tool | Observed |
| `APPLIES` | Artifact → Technique | Inferred, always with confidence + evidence |
| `IN_PERIOD` | Artifact → Period | Observed |
| `IN_COLLECTION` | Artifact → Collection | **Author-confirmed only** (FR-021) |
| `AUTHORED_BY` | Artifact → Author | Observed |
| `DEPENDS_ON` | Artifact → Dependency | Observed |
| `DERIVES_FROM` | Artifact → Artifact | Inferred, thresholded (FR-012). `from` is the **newer** Artifact, `to` the older, so the edge reads as a sentence like every other row: the newer one derives from the older. See *Orientation* |
| `SUCCEEDS` | Artifact → Artifact | **Author-confirmed only. Never inferred into the graph** (FR-011). Same orientation: `from` is the later Artifact, `to` the earlier. Created only by a `[[succession]]` line in config |

Per SC-008, no edge may assert a relationship the Author did not either observe or
confirm. `APPLIES` and `DERIVES_FROM` are the only inferred edges, and both carry
`confidence` and `evidence` on the edge itself.

### Orientation

Every edge reads as a sentence from `from` to `to`: *Artifact* `USES` *Tool*, *newer*
`DERIVES_FROM` *older*, *later* `SUCCEEDS` *earlier*. Time therefore runs `to` → `from`
on both Artifact-to-Artifact edges.

This was got wrong once, and the wrongness was not cosmetic. `DERIVES_FROM` was specified
"oriented older → newer", and on a real scan that emitted `tinygrad DERIVES_FROM tinyos`
— tinygrad is from 2020, tinyos from 2024, and it is tinyos that is built on tinygrad.
The graph asserted the reverse of the truth, in an edge type SC-008 says must never
assert what was not observed. A direction that only reads oddly is a style question; one
that inverts a claim is a defect.

### What lineage detection returns

`core.analysis.lineage.candidates(artifacts)` returns dicts of
`{"from", "to", "confidence", "evidence"}` ordered **older → newer**: `from` is the older
Artifact. `core/graph.py` reverses that when emitting, per *Orientation* above. The two
conventions are deliberately different and each is right for its layer — a detector sorts
by time, an edge reads as a sentence — so neither may be assumed from the other.

Until that module exists the graph emits no such edge: an inferred relationship with no
detector behind it would be a claim nobody made.

`EpochMarker` nodes have a date and a label and no edges; the timeline draws them across
the axis. Declared, never inferred (FR-014).

## `graph.sqlite`

A derived query surface, **not a graph database** (Principle III). One table per node
type plus one `edges` table, mirroring `graph.json` exactly — anything true of one is
true of the other.

An **FTS5 virtual table over Artifact names and descriptions ships in v0.1 and is never
queried by it.** v0.2's search needs it, and adding it later means every Author rebuilds.
Populating it now costs one `INSERT` per Artifact.

## `llms.txt`

Plain text, for an agent reading the archive without parsing JSON: the schema in prose,
the archive's shape (counts, date range, Tools), and how to read `graph.json`. Subject to
the same privacy filtering as every other output.

## Loading from `file://`

The published site must work opened from disk, from a pen drive, with no network
(FR-016). A browser blocks `fetch('graph.json')` from a `file://` page under CORS, so
**`graph.json` is delivered to the page as a script that assigns a global**, not fetched:

```html
<script src="graph.js"></script>   <!-- window.DENDROGRAPH_GRAPH = { ... } -->
```

`graph.js` is `graph.json` wrapped in one assignment, emitted by the same build step.
Both ship: the `.json` for programs and agents (FR-017), the `.js` for the page. They are
generated from the same object in the same run and can never disagree.

This is why the views stream must go through one shared data-loading layer rather than
two standalone pages — the layer is what hides this from the timeline and the graph view.

## Aliased Artifacts

A private Artifact the Author has aliased is published as a node under a chosen or generated
label. What it carries beyond the node and its dates is exactly what `[[publish.alias]].reveal`
names — `period`, `tools`, `authorship` — and nothing else.

**These never appear in published output for an aliased Artifact, at any setting:**

| Withheld | Why |
|---|---|
| Real name, description, URL | The point of the alias |
| `sources[].locator` | A path or URL names the owner |
| Technique evidence pointers | Evidence is a file path, and `clientname/api/deploy.yml` undoes the anonymity without anyone having looked. A Technique published under an alias ships **without** its pointer, and is therefore not verifiable — say so, do not imply otherwise |
| `content_hashes` | Feeds lineage, and lineage identifies |
| `DERIVES_FROM` / `SUCCEEDS` edges | An edge from an anonymous node to a known public Artifact identifies the anonymous one |

Generated labels are `Private project N`, numbered from the **sorted Artifact id** rather
than from discovery order, so a newly scanned private Artifact never renumbers the others and
the published site's diff stays readable.

Re-identification is narrowed, not solved: exact dates plus a Tool set plus an authorship
share can be enough for a reader who was there. User-facing text must say that rather than
promise anonymity.

## Build modes

| Mode | Private Artifacts | Where |
|---|---|---|
| `public` | Excluded entirely. **Default** (FR-013). | Published site |
| `redacted` | Aggregate shape only — counts, Tools, date ranges, no names | Published site, opt-in |
| any mode | An **aliased** private Artifact appears as a node under its label, per *Aliased Artifacts* above | Published site, per-Artifact opt-in |
| `full` | Included | `.dendro-local/` only — gitignored by the archive template, never read by `publish` |

`full` is a local-inspection mode, and the guard is the **output directory**, not a check
at publish time: `build --mode full` writes to `.dendro-local/` and never to `site/`. A
check at publish time would run after the private data had already been written into the
directory that gets deployed. `publish` still refuses a `full` build as a second line of
defence.

## Determinism

Two builds from the same store produce byte-identical outputs apart from
`generated_at`. Nodes sorted by `(type, id)`, edges by `(type, from, to)`. Without this,
every build dirties the archive repository's git history and FR-018's reviewable record
becomes noise.
