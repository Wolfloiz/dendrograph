# Implementation Plan: dendrograph v0.1 — git collector

**Branch**: `001-git-collector` | **Date**: 2026-08-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-git-collector/spec.md`

## Summary

Build the git collector end to end: discover repositories from the GitHub API and from
local folders, scan and analyse each one, resolve a stable identity, accumulate the
result into a committed per-Artifact store, and render a static site plus machine-readable
outputs from that store. The store — not the sources — is the source of truth, so an
Artifact survives the death of the drive it came from.

## Technical Context

**Language/Version**: Python 3.11+ (3.11 for stdlib `tomllib`; 3.12 present locally)

**Primary Dependencies**: None. Standard library only, so a fork installs nothing.
`urllib` for the GitHub API and OAuth device flow; `sqlite3` for the derived database;
`tomllib` for config; `hashlib` for content hashes; `subprocess` for `git`.

**Storage**: `store/artifacts/<id>.json` — one committed JSON file per Artifact, the
source of truth. `graph.json`, `graph.sqlite` and `llms.txt` are derived build outputs.

**Testing**: `unittest` (stdlib). Fixture-based, against small real repositories
committed to `tests/fixtures/`.

**Target Platform**: Linux, macOS, Windows CLI; output is a static site viewable in any
browser offline, from a pen drive, or on GitHub Pages.

**Project Type**: Single project — CLI plus generated static site.

**Performance Goals**: ~500 Artifacts → ~3,000 nodes → under 1 MB of graph data,
rendering without perceptible delay in a browser tab.

**Constraints**: No server. No graph database. No CDN or third-party library on the page;
the force simulation is roughly 90 lines against a 2D canvas. Fully offline-capable output.

**Scale/Scope**: Personal archives — hundreds to low thousands of Artifacts.

## Constitution Check

| Principle | How this plan complies |
|---|---|
| I. Machine proposes, Author disposes | `SUCCEEDS` only via `dendro suggest` + confirmation; `dendro prune` prints config lines and never deletes; identity overridable; Epoch Markers declared |
| II. Store accumulates | Per-Artifact JSON is the source of truth; scans append; `last_seen` recorded; all other outputs derived |
| III. No server / no graph DB / no page deps | Device flow needs only a public `client_id`; SQLite is a derived file, not a graph engine; canvas rendering with zero page dependencies |
| IV. Privacy by default | Visibility stored per Artifact; publish step filters private by default; aliases and redacted mode are per-Artifact and per-mode opt-ins that reveal nothing until asked (ADR-0011); tokens from env only, read-only scope |
| V. Honest inference or none | Techniques limited to manifest/convention markers with confidence + evidence; `DERIVES_FROM` thresholded; no quality, complexity or AI-authorship claims |
| IV. Privacy by default (repo topology) | Tool repo holds no Author data; store lives in the Author's own archive repo, which may be private (ADR-0010) |
| Constraints | Python 3.11+ stdlib only; `unittest`; English public surface, Portuguese comments; MIT |

No violations. No complexity justification required.

### Reviewed against the built system (T092, 2026-08-25)

Each row checked against what exists, not against what was planned. **No principle is
violated, and no deviation needs an ADR.** What the review did turn up was three cases
where the built system was *weaker* than the row claimed, all now closed:

| Row | What the check found |
|---|---|
| I. Machine proposes | `SUCCEEDS` was contracted as Author-confirmed only, but **no config key existed to confirm one with** — the edge was unreachable and the principle held vacuously. `[[succession]]` now closes it. `dendro prune` and `dendro suggest` contain no deletion or write call at all. |
| II. Store accumulates | `store.save` merges into what is already there; no path rebuilds. A source that vanishes is flagged unreachable and its `last_seen` does not advance. |
| III. No server / no graph DB / no page deps | Verified mechanically: **zero non-stdlib imports** across the codebase. The two views reference only their own four sibling files — no CDN, no external font, no fetch. SQLite is written and never queried by v0.1. |
| IV. Privacy by default | `privacy.select` includes private Artifacts only in `full`, which cannot reach `site/` because the output directory is chosen by mode. Tokens are read from the environment and never written to config or store — and never reach `argv` or an error message, which was a real leak until the credential helper replaced the URL. |
| V. Honest inference or none | Eight Technique rules, all manifest or convention markers, each carrying confidence and evidence. `DERIVES_FROM` is thresholded at three shared authored files. `tests/test_no_judgement.py` now sweeps **every generated file**, not just the in-memory payload — it had never looked at what lands on disk, and the first sweep caught the prose in `llms.txt`. |
| IV. Repo topology (ADR-0010) | `examples/` holds no private Artifact. |
| Constraints | Python 3.11+ and stdlib-only confirmed; `unittest` throughout; public surface English with 0 Portuguese identifiers and 0 Portuguese file names against 201 Portuguese comments (ADR-0001). MIT was declared in `pyproject.toml` **with no `LICENSE` file in the repository** — added. |

One deviation is recorded rather than fixed, in `contracts/graph.md`: `DERIVES_FROM` and
`SUCCEEDS` use opposite conventions between the detector and the graph. That is
deliberate — a detector sorts by time, an edge reads as a sentence — but it is a trap for
anyone reading only one layer, so it is written down in both.

## Design

### Identity resolution (ADR-0003)

1. **Primary**: SHA of the repository's root commit — stable across clone, rename,
   re-host and disk.
2. **Fallback**: SHA-256 over a deterministic file set — every tracked file that is not
   in an excluded directory (see *Authored files*, below), sorted by POSIX path, each
   contributing `path\0size\0sha256(content)`. Deterministic across machines and
   filesystems; used for repositories with no commits and for future non-git Artifacts.
3. **Override**: Author declarations in config merge or separate Artifacts; overrides
   always win.

A fork shares upstream's root commit and is therefore the same Artifact — deliberate,
and the source of free fork detection. Authorship is computed separately from per-author
commit and line counts, so a repository count is never inflated by untouched forks.

### Store (ADR-0002)

One JSON file per Artifact under `store/artifacts/`, committed. Per-file layout is
load-bearing: git diffs each run readably, machines merge per Artifact rather than
conflicting on one large file, and corruption costs one entry.

Each file records identity and how it was derived, source provenance, first and last
activity, per-author commit and line counts, visibility, Tools, Techniques with
confidence and evidence, content hashes used for lineage, `last_seen`, and which Author
declarations were applied to it. The declarations themselves live in `dendrograph.toml`:
the store holds what was observed, the config holds what the Author decided, and every
declaration is reversible by deleting a line (see `contracts/README.md`). A source unreachable this run updates nothing but `last_seen`-adjacent
state; it is never treated as deletion.

### Pipeline

```
discover → scan → analyse → resolve identity → write store → build → publish
```

`discover` is source-specific; everything after it is identical whether a repository
arrived via `git clone` or was already on disk. The GitHub path is "discover and clone,
then do the local thing."

### Inference

- **Techniques**: dependency manifests and directory conventions only — where regex is
  genuinely reliable. Small, curated, evidence-backed. AST-based detection is deferred
  to v0.3, so v0.1 must not pretend to read code semantics.
- **`DERIVES_FROM`**: content hashes over authored files only; exclude dependency
  directories, lockfiles, generated output and files under a few hundred bytes; require
  several identical non-trivial files; orient older → newer. Strictness is affordable
  because genuine forks are already collapsed by identity.
- **`SUCCEEDS`**: never inferred into the graph. `dendro suggest` proposes pairs.

### Authentication (ADR-0008)

| Mode | Mechanism | When |
|---|---|---|
| Default | Unauthenticated public API (60 req/h) | Zero setup, demo, public archives |
| `dendro login` | OAuth device flow, public `client_id`, no secret, no redirect URI | Full rate limit, private Artifacts |
| Shortcut | `gh auth token` when `gh` is installed and authenticated | Convenience only, never required |
| CI | PAT as an Actions secret | Scheduled runs — no browser to approve in |

Actions' built-in `GITHUB_TOKEN` is unusable for discovery: scoped to the current
repository, it cannot enumerate the Author's others.

**To verify before implementing**: registering the OAuth App requires device flow to be
explicitly enabled in its settings. Confirm against current GitHub documentation.

### Publishing and privacy (ADR-0005)

The publish step filters the store: private Artifacts excluded unless opted in per
Artifact, aliased per Artifact, or aggregated under redacted mode ("4 private repositories,
Rust, 2019–2021"). README wording must state exactly what the published site contains.

**Aliases (ADR-0011)** are the third treatment and the one that serves the job-search case:
the Artifact is published as a node under a label the Author chose, revealing nothing beyond
its dates until the Author names each further field. Real name, description, URL, source
locators, Technique evidence paths, content hashes and lineage edges never cross, at any
setting — an evidence path such as `clientname/api/deploy.yml` would undo the anonymity
without anyone having looked. Re-identification from dates and Tools alone remains possible;
the README must say so rather than promise anonymity.

### Constraints v0.2 imposes on v0.1

Cheap now, expensive once real data exists in a committed store:

1. **FTS5 table present from day one**, though v0.1 never queries it.
2. **Reverse `tool → artifact` index** in the graph, unrendered in v0.1.
3. **One shared data-loading layer** behind both HTML views, not two standalone pages.
4. **Config schema stable and documented**, since v0.2's README promises a three-step fork.

## Project Structure

### Documentation (this feature)

```
specs/001-git-collector/
├── spec.md
├── plan.md
└── tasks.md        # generated by /speckit-tasks
```

### Source Code

**Tool repository** — code only, no Author data (ADR-0010):

```
dendrograph/
├─ cli.py                         command dispatch, exit codes, --dry-run
├─ collectors/git/                discovery, clone, scan, counting
├─ core/                          identity, store, graph, derived outputs
│  └─ analysis/                   tools, techniques, dependencies, lineage, tool spans
├─ views/                         timeline, graph, shared loader
├─ templates/archive/             the archive repository template
├─ examples/                      demo archive, public repositories only
├─ tests/fixtures/                git bundles, unbundled at setup
├─ docs/adr/                      decision records
├─ pyproject.toml                 Python 3.11+, no runtime dependencies
├─ CONTEXT.md
├─ CONTRIBUTING.md
├─ LICENSE                        MIT
└─ README.md
```

**Archive repository** — created from `templates/archive/`, may be private:

```
<author>-archive/
├─ .github/workflows/update.yml   pins a tool tag; refreshes and auto-commits the store
├─ .gitignore                     ignores .dendro-local/
├─ dendrograph.toml               config
├─ store/artifacts/               source of truth, committed
├─ .dendro-local/                 full builds; never committed, never deployed
└─ site/                          build output, deployed to Pages
```

## Testing Strategy

Test what lies quietly, not what crashes. The heuristics carry the risk:

- **Identity and deduplication** — the same repository on two paths collapses to one
  Artifact; a repository with no commits gets a stable fallback identity; rewritten
  history is recognised as a new Artifact that an override can merge.
- **Authorship counting** — per-author commits and lines are correct on a repository
  with multiple contributors, and a barely-touched fork shows negligible Authorship.
- **Technique precision** — no Technique is claimed without matching evidence; each
  claim points at the file that produced it.
- **Accumulation** — an Artifact whose source disappears survives a rebuild; exclusion
  and un-exclusion are lossless.
- **Privacy** — no private Artifact name reaches any published or public-repository
  output under default settings.

**Fixtures**: real repositories cannot be committed as nested `.git` directories. They
are stored as `git bundle` files under `tests/fixtures/` and unbundled into a temporary
directory at test setup, which keeps them real, small and diffable.

Rendering and the force simulation are not tested.

## Launch Requirements

- Demo archive is the Author's own real archive, public repositories only — honest, real
  data, and automatically safe because it is exactly what the privacy default produces.
- A visualization above the fold; nobody stars a visualization tool without seeing it.
- README states Principle I explicitly, alongside the three-step fork.

## Deferred

- **v0.2** — single screen with view selector; three-step fork README; FTS5 search; Tool
  profile.
- **v0.3** — Barnes-Hut above 3,000 nodes; GitLab and Bitbucket; AST-based detection
  starting with TypeScript and Python.
- **v0.4** — first non-git collector; MCP server over the SQLite; optional LLM layer,
  marking model-derived data at its origin.
