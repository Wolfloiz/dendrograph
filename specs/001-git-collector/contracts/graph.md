# Contract: derived outputs — `graph.json`, `graph.sqlite`, `llms.txt`

Build outputs, regenerated from `store/` on every run (ADR-0002). Deleting them costs
nothing. They are the contract between the core stream and everything downstream: the
views, third-party programs, and AI agents (FR-017).

**Privacy applies here, not in the store.** Private Artifacts are in the store and are
filtered out of these outputs when they are built for publication. See *Build modes*.

## `graph.json`

Target: ~500 Artifacts → ~3,000 nodes → under 1 MB, first render under 2 seconds
(SC-005).

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
      "first": "2019-03-11", "last": "2026-08-20", "authorship": { "share": 0.87 } },
    { "id": "tool:python", "type": "Tool", "label": "Python" },
    { "id": "period:2019", "type": "Period", "label": "2019" }
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
    { "kind": "local", "locator": "/media/backup", "last_seen": "2025-11-02" }
  ]
}
```

| Field | Notes |
|---|---|
| `schema` | Self-describing, so a consumer needs no companion docs (FR-017). |
| `build_mode` | `public` \| `redacted` \| `full`. See *Build modes*. |
| `nodes` / `edges` | Node ids: Artifacts use their store id; every other type uses `<lowercase type>:<slug>`. |
| `indexes.tool_to_artifacts` | Reverse index. **Present in v0.1, unrendered** — v0.2 needs it and adding it later means rebuilding every published archive. |
| `aggregates.private_withheld` | Only in `redacted` mode; absent otherwise. Counts, Tools and a date range, never names (FR-013, ADR-0005). |
| `unreachable_sources` | Sources this run could not reach, reported rather than omitted (FR-019). |

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
| `DERIVES_FROM` | Artifact → Artifact | Inferred, thresholded (FR-012), oriented older → newer |
| `SUCCEEDS` | Artifact → Artifact | **Author-confirmed only. Never inferred into the graph** (FR-011) |

Per SC-008, no edge may assert a relationship the Author did not either observe or
confirm. `APPLIES` and `DERIVES_FROM` are the only inferred edges, and both carry
`confidence` and `evidence` on the edge itself.

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

## Build modes

| Mode | Private Artifacts | Where |
|---|---|---|
| `public` | Excluded entirely. **Default** (FR-013). | Published site |
| `redacted` | Aggregate shape only — counts, Tools, date ranges, no names | Published site, opt-in |
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
