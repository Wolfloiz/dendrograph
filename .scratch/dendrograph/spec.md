> **Superseded.** This was the grilling output. It has been split into the Spec Kit
> artifacts and is kept only as the record of how the design was reached:
>
> - `specs/001-git-collector/spec.md` — what and why
> - `specs/001-git-collector/plan.md` — how
> - `.specify/memory/constitution.md` — the principles
>
> Edit those, not this file.

# dendrograph — v0.1 specification

Status: agreed, not yet implemented. No code exists; this specifies it from zero.

A knowledge graph of what a person has built. Point it at an archive — starting with
git — and get a navigable map of Artifacts, Tools, Techniques and time, generated
locally and published as a static site with no server.

Vocabulary in this document is defined in [`CONTEXT.md`](../../CONTEXT.md). Decisions
are recorded in [`docs/adr/`](../../docs/adr/) and are referenced inline as ADR-NNNN
rather than re-argued here.

---

## 1. The principle

**The machine proposes, the Author disposes** (ADR-0009). dendrograph is confident
about what it observed and deferential about what it interpreted. Every inference is a
suggestion the Author confirms; nothing interpreted is written into the graph
unilaterally. Coverage is traded for trust, deliberately: this output gets repeated in
interviews and on CVs, where a confident wrong edge is a false claim about a person's
own career.

## 2. Scope

**In scope for v0.1:**

- Discovery of git repositories from two sources: the GitHub API, and local folders.
- Scanning, analysis, identity resolution, graph assembly, and an accumulating store.
- Two HTML views — timeline and graph — plus `graph.json`, `graph.sqlite`, `llms.txt`.
- A GitHub Actions workflow that refreshes GitHub-sourced Artifacts and commits.

**Explicitly not in scope — decisions, not omissions:**

- **Hosts nothing.** Runs on the Author's machine and in their Actions; publishes to
  their Pages. No third-party server sees any data (ADR-0004).
- **Judges no quality.** Not code review. No scores, no grades.
- **Proves no complexity.** Recognises markers of known cost with declared confidence.
  Proving O(log n) is undecidable; pretending otherwise would be a lie.
- **Infers no AI authorship.** Undecidable, and a wrong "AI-generated" label on a
  person's proudest work is the worst failure this tool could produce. The pre-AI-age
  reading comes from Epoch Markers the Author declares, not from detection.
- **Requires no LLM key.** Any AI layer is optional, off by default, and deferred.

## 3. Domain model

Nodes: `artifact`, `collection`, `tool`, `technique`, `period`, `author`, `dependency`.

| Edge | Direction | Origin |
|---|---|---|
| `BELONGS_TO` | artifact → author | measured |
| `USES_TOOL` | artifact → tool | measured |
| `APPLIES_TECHNIQUE` | artifact → technique | inferred, with confidence + evidence |
| `IN_COLLECTION` | artifact → collection | declared or measured |
| `IN_PERIOD` | artifact → period | measured |
| `DERIVES_FROM` | artifact → artifact | inferred, with confidence |
| `SUCCEEDS` | artifact → artifact | **Author-declared only** in v0.1 |

The graph speaks of Artifacts, Tools and Periods — never of repositories, languages or
commits. That vocabulary lives in the collectors, and it is what lets a Figma or Drive
collector arrive later without a redesign.

Identifiers are English throughout, including in `graph.json`, `graph.sqlite` and
`llms.txt`, because those exist to be read by other people and machines (ADR-0001).
Code comments are Portuguese.

## 4. Identity and deduplication

An Artifact is identified by the **SHA of its repository's root commit** (ADR-0003),
which is stable across every clone, rename, re-host and drive. The same project found
on a dead 2019 disk and on GitHub today collapses into one Artifact automatically.

- **Fallback**: content hash over a stable subset of authored files, for non-git
  Artifacts and repositories with no commits.
- **Override**: the Author may declare two Artifacts the same, or force them apart,
  in config. Overrides always win.
- **Forks**: a fork shares the upstream root commit and is therefore the *same*
  Artifact. This is deliberate — it gives fork detection for free.
- **Identity is not Authorship**: the root commit says *which* Artifact; per-author
  commit and line counts say *how much of it is the Author's*. This is what lets
  dendrograph state a repository count without inflating it with untouched forks.

## 5. The store

`store/artifacts/<id>.json` — one committed JSON file per Artifact — is the **source of
truth** (ADR-0002). Scans append; they never rebuild.

- An Artifact seen once persists forever. Disappearance of its source is recorded as
  state (`last_seen`, `source_gone`), never as deletion.
- `graph.json`, `graph.sqlite`, `llms.txt` and the published site are **derived build
  outputs**, regenerated from `store/` on every run.
- Per-file layout is load-bearing: git diffs each run readably, machines merge per
  Artifact instead of conflicting on one large file, and corruption costs one entry.
- **Pruning is declarative**: an `exclude` list in config omits an Artifact from the
  graph while leaving it in the store; removing the line restores it. `dendro prune`
  only *lists* candidates and prints config lines to paste. Nothing deletes.

Each stored Artifact records: identity and how it was derived, source provenance,
first/last activity dates, per-author commit and line counts, visibility, detected
Tools, detected Techniques with confidence and evidence, content hashes used for
lineage, `last_seen`, and any Author declarations.

## 6. Execution model

`dendro` is a local CLI (ADR-0007). Actions is one caller, not the product's home —
an Actions runner cannot see the Author's drives, and those drives hold the work no
API can reach.

```
discover → scan → analyse → resolve identity → write store → build → publish
```

1. **Discover** — GitHub API (public, and private when authenticated), or a local path.
2. **Scan** — structure, manifests, dependencies, conventions, content hashes.
3. **Analyse** — separate authored from fork, deduplicate copies, count commits and
   lines per author, detect Tools and Techniques.
4. **Resolve identity** — root commit, fallback hash, Author overrides.
5. **Write store** — append and update `store/artifacts/<id>.json`.
6. **Build** — assemble the graph, emit `graph.json`, `graph.sqlite`, `llms.txt`.
7. **Publish** — render the static site into `docs/`.

## 7. Collectors

Both ship in v0.1, and local scanning is not the lesser half — it reaches the drives
no API can. Once a repository is on disk the downstream path is identical; the API
path is "discover and clone, then do the local thing".

| | git collector (v0.1) | figma collector (deferred) |
|---|---|---|
| `artifact` | repository | file |
| `collection` | project family | project or client |
| `tool` | language, framework | plugin, component library |
| `technique` | project pattern, complexity marker | grid, design token, auto-layout |
| `period` | commit date | version date |
| `author` | git identity | account |
| `DERIVES_FROM` | identical source files | reused component |

**Honest note on expansion.** Git is a universal substrate: every commit has an author,
a date and a diff. Design and architecture have no equivalent — a Figma version has no
granular authorship, a `.psd` on a drive has no history. Future collectors will fill
fewer fields with less precision. The architecture accommodates this; the UI must show
the varying data quality rather than hide it.

## 8. Inference rules

**Techniques — small, high-precision, evidence-backed.** Ten markers defensible in an
interview beat eighty needing apology. One confidently wrong "applies CQRS" on a CRUD
app teaches the Author that the whole layer is noise. Since v0.3 replaces regex with
AST parsing, v0.1's regex set is restricted to where regex is genuinely reliable:
dependency manifests and directory conventions, not code semantics. Every
`APPLIES_TECHNIQUE` edge carries a confidence and a pointer to its evidence.

**`DERIVES_FROM` — strict, directional.** Content hashes over *authored* files only:
exclude dependency directories, lockfiles, generated output and files under a few
hundred bytes; require several identical non-trivial files, not one; orient by time,
older as source. Confidence scales with how much material is shared. The threshold can
afford to be strict because genuine forks are already collapsed by root-commit identity
— this edge only needs to catch copy-paste lineage.

**`SUCCEEDS` — declared, never guessed.** Temporal adjacency is everywhere: in any
active archive dozens of unrelated projects start as another goes quiet. `dendro
suggest` lists plausible pairs; only the Author's confirmation writes the edge.

**Epoch Markers — declared, plural, generic.** Config holds a list of `{date, label}`.
"Before AI assistants" is one suggested label; "went freelance" and "left the agency"
are equally valid. The schema never learns the concept "AI" — the pitch ages, the
mechanism does not.

## 9. Privacy and publishing

Private Artifacts enter the store and are **excluded from the published site by
default** (ADR-0005), opt-in per Artifact. **Redacted mode** publishes them as
aggregate shape with no names — "4 private repositories, Rust, 2019–2021" — which
rescues the résumé case: "four years of Rust" is the number an interview needs, and it
is provable without naming a client.

GitHub Pages on a public repository is a world-readable website. The README must not
claim private repositories "never leave your account" without stating exactly what the
published site does and does not contain.

## 10. Authentication

No key generation (ADR-0008):

- **Default, zero setup**: unauthenticated public API. A stranger sees a graph within a
  minute of forking. Rate-limited to 60 req/hour versus 5,000 authenticated — fine for
  a demo, poor for a 500-repository archive.
- **`dendro login`**: OAuth device flow — a short code approved in the browser. Public
  `client_id` only, no client secret, no redirect URI, therefore no server. Stdlib
  `urllib`: one request for the code, then poll until approved.
- **Shortcut**: if `gh` is installed and authenticated, borrow `gh auth token`. Never a
  requirement, since `gh` is an external dependency.
- **CI only**: a stored PAT as an Actions secret, because a scheduled run has no browser
  to approve in. Actions' built-in `GITHUB_TOKEN` is unusable for discovery — it is
  scoped to the current repository and cannot enumerate the Author's others.

Tokens are read from the environment and never written to config or the store.
Read-only scope.

**To verify before implementing**: registering the OAuth App requires device flow to be
explicitly enabled in its settings. Confirm against current GitHub documentation.

## 11. Outputs

- `docs/` — the static site: **timeline** and **graph** views. No CDN, no graph
  library; the force simulation is ~90 lines against a 2D canvas, so the page works
  offline, from a pen drive, and on Pages with no configuration (ADR-0004).
- `graph.json` — the whole graph; also the migration path if this ever needs Neo4j.
- `graph.sqlite` — including an FTS5 table (see §12).
- `llms.txt` — machine-readable summary for AI agents, which gain context about a
  specific person that no model has from training.

Roughly 3,000 nodes for a 500-repository archive: under 1 MB, drawn in the tab without
effort. No graph database.

## 12. Constraints v0.2 imposes on v0.1

Cheap now, expensive after real data exists in a committed store. Each is a shape
constraint, not a feature:

1. **FTS5 table present from day one**, even though v0.1 never queries it — v0.2 search
   depends on it.
2. **Reverse `tool → artifact` index in the graph**, unrendered in v0.1 — v0.2's Tool
   profile ("click Rust, see since when, how much, in what") needs it.
3. **One shared data-loading layer behind both HTML views**, not two standalone pages —
   v0.2 puts a view selector on a single screen.
4. **Config schema stable and documented**, because v0.2's README promises a
   three-step fork.

## 13. Repository structure

```
dendrograph/
├─ .github/workflows/update.yml
├─ collectors/git/         discovery, clone, scan, counting
├─ core/                   analysis, graph, generic schema
├─ views/                  timeline, graph, profile
├─ store/artifacts/        source of truth, committed
├─ docs/                   published site (Pages) + adr/
├─ examples/               demonstration archive
├─ CONTEXT.md
├─ CONTRIBUTING.md
├─ LICENSE                 MIT
└─ README.md
```

## 14. Implementation constraints

- **Python 3.11+, standard library only.** A fork installs nothing. 3.11 gives
  `tomllib`, so config needs no parser and no dependency.
- **`unittest`**, not pytest — stdlib-only.
- **Test what lies quietly, not what crashes**: identity and dedup (does the same repo
  on two paths collapse?), authorship counting, Technique precision. Assert exact
  output against a handful of small real repositories committed as fixtures. Rendering
  and the force simulation need no tests; the heuristics absolutely do.
- **MIT licensed** (ADR-0006).
- Project name is **dendrograph**, one word.

## 15. Launch requirements

- **The demo archive is the Author's own real archive, public repositories only** —
  honest, real data, and automatically safe because it is exactly what the privacy
  default produces, which doubles as proof that the default works. Consequence accepted
  knowingly: the Author's own work becomes the project's landing page.
- **A visualization above the fold.** Nobody stars a visualization tool without seeing
  the visualization.
- **README states the principle** of §1 explicitly, alongside the three-step fork.

## 16. Deliberately deferred

- **v0.2** — single screen with view selector; three-step fork README; FTS5 search;
  Tool profile.
- **v0.3** — Barnes-Hut above 3,000 nodes; GitLab and Bitbucket; AST-based pattern
  detection starting with TypeScript and Python.
- **v0.4** — first non-git collector; MCP server over the SQLite; optional LLM layer for
  what heuristics cannot reach, marking model-derived data at its origin.
