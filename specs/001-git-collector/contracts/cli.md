# Contract: the `dendro` command surface

Six commands, covering exactly the capabilities FR-020 requires: scanning a source,
authenticating, building outputs, publishing, proposing inferred relationships, and
listing prune candidates.

`dendro` is a local CLI first; a scheduled Actions run is one caller of it, not the
product's home (ADR-0007). Every command runs from the archive repository's root, where
`dendrograph.toml` and `store/` live.

| Command | Does | Writes |
|---|---|---|
| `dendro scan [SOURCE]` | Discovers and scans a source, merging observations into the store | `store/artifacts/*.json` |
| `dendro login` | Authenticates against GitHub via OAuth device flow | Nothing — token goes to the environment |
| `dendro build` | Rebuilds derived outputs from the store | `site/` for `public` and `redacted`; `.dendro-local/` for `full` |
| `dendro publish` | Produces the publishable site | `site/` |
| `dendro suggest` | Proposes relationships and Collections for confirmation | Nothing — prints |
| `dendro prune` | Lists Artifacts that look prunable | Nothing — prints |

## `dendro scan [SOURCE]`

`SOURCE` is a local path, a GitHub account (`github:author`), or omitted to scan every
source in config.

- Clones remote Artifacts with **complete history, no working tree**, into a temporary
  directory discarded at the end of the run (FR-024). Nothing is cached between runs.
- Reports progress throughout; ~500 public repositories complete unattended within 30
  minutes (SC-001b).
- Sources it cannot reach are **reported, never silently omitted** (FR-019), and are not
  treated as deletions (FR-007).
- Unauthenticated by default, limited to public Artifacts (FR-002).

## `dendro login`

OAuth device flow: prints a short code, the Author approves it in a browser, a token
comes back (ADR-0008). Satisfies FR-003's requirement of an interactive path that never
asks the Author to generate or paste a key.

- Borrows `gh auth token` when `gh` is installed and authenticated — a convenience,
  never a requirement.
- A stored PAT is supported **for CI only**, where no browser exists to approve in.
- Tokens are read from the environment, never written to config or the store, and are
  read-only (Principle IV).

**Open verification**: registering the OAuth App requires device flow to be explicitly
enabled in its settings. Confirm against current GitHub documentation before implementing.

## `dendro build`

Rebuilds `graph.json`, `graph.sqlite` and `llms.txt` from the store. Takes
`--mode public|redacted|full`, defaulting to `public`. Never touches the store.

**The output directory is chosen by the mode, not by a flag.** `public` and `redacted`
write to `site/`. `full` writes to `.dendro-local/`, which the archive template gitignores
and which no deployment reads. A `full` build therefore cannot reach `site/` even by
mistake, and there is nothing left for `publish` to catch.

## `dendro publish`

Produces the site for deployment from `site/`. It never reads `.dendro-local/`, so a
`full` build is out of reach by construction. As a second line of defence it also
**refuses to publish when `site/graph.json` declares `build_mode: full`** — which should
be unreachable, and is checked anyway because the cost of being wrong here is an NDA
breach.

Re-evaluates every Artifact's visibility from the most recent observation and names each
Artifact that a visibility change removed from the output (FR-026). Private Artifacts the
Author has aliased are published under their labels, revealing only what `reveal` names
(FR-028, ADR-0011).

When `[publish].target_repository` is set, the built site is deployed to that second,
public repository, which holds no store. This is the path for an Author whose archive
repository is private: GitHub Pages from a private repository requires a paid plan, so the
store stays private and only the filtered site becomes public (ADR-0010).

## `dendro suggest`

Prints candidate `SUCCEEDS` pairs, candidate Collections, and candidate identity merges
where a rewritten history looks like an existing Artifact. **Creates nothing.** The
Author confirms by pasting a line into config (FR-011, FR-021, Principle I).

Artifacts with unanswered Collection suggestions remain usable and ungrouped; nothing
blocks awaiting confirmation.

## `dendro prune`

Prints Artifacts that look prunable and the config lines that would exclude them.
**Deletes nothing** (FR-008). Exclusion omits an Artifact from the graph while leaving it
in the store, and is reversed by deleting the line — its data returns intact.

A tool built because human memory is unreliable must not offer one-command amnesia
(ADR-0002).

## Common behaviour

- `--dry-run` on every command that writes: report what would change, change nothing.
- Every run ends with a **run report** — Artifacts added, Artifacts changed, sources
  unreachable, Artifacts withheld from output (FR-018, FR-019).
- Exit codes: `0` success; `1` command failure; `2` usage error; `3` partial success —
  the run completed but a source was unreachable. `3` exists so a scheduled Actions run
  can distinguish "nothing to see" from "half your archive was silently skipped".
- No command writes Author data into the tool's repository (FR-023, ADR-0010).
