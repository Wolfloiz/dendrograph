# Contract: `dendrograph.toml`

The Author's declarations. Lives in the archive repository, parsed with stdlib `tomllib`
(Principle: stdlib only).

**This file is where the Author disposes.** The store holds what the machine observed;
this holds what the Author decided. Every declaration is reversible by deleting a line
(Principle I, ADR-0002).

The schema is stable and documented from v0.1, because v0.2's README promises a
three-step setup against it.

```toml
[archive]
author = "Luiz"
emails = ["luiz@example.com", "luiz@work.example.com"]

[[sources]]
kind = "github"
account = "author"

[[sources]]
kind = "local"
path = "/media/backup/old-projects"

[publish]
mode = "public"                 # public | redacted
opt_in = ["root-a1b2c3..."]     # private Artifacts published by name, one by one
target_repository = "author/archive-site"   # optional: deploy the site to a second, public repo

[[publish.alias]]
id = "root-a1b2c3..."
label = "Anonymous fintech project"   # omit for a stable generated "Private project N"
reveal = ["period", "tools", "authorship"]   # empty by default: the node and its dates only

[exclude]
artifacts = ["root-d4e5f6..."]  # omitted from the graph; NOT deleted from the store

[[identity.merge]]
ids = ["root-a1b2c3...", "root-9f8e7d..."]
reason = "history rewritten by filter-branch in 2021"

[[identity.separate]]
id = "root-3f7a1c..."
locator = "https://github.com/author/fork-i-rewrote"

[[collections]]
name = "Client work"
artifacts = ["root-a1b2c3..."]

[[succession]]
earlier = "root-a1b2c3..."
later = "root-9f8e7d..."
note = "the rewrite that replaced it"

[[epoch_markers]]
date = "2023-03-14"
label = "AI assistants arrive"
```

| Table | Purpose | Requirement |
|---|---|---|
| `[archive].emails` | Which commit authors count as the Author, for Authorship | FR-006, FR-009 |
| `[[sources]]` | What `dendro scan` scans when given no argument | FR-001 |
| `[publish].mode` | `public` (default) or `redacted` | FR-013 |
| `[publish].opt_in` | Private Artifacts published by name, one at a time | FR-013 |
| `[publish].target_repository` | Optional. Deploys the built site to a second, public repository holding no store — the free-plan path, since Pages from a private repository requires a paid plan | ADR-0010 |
| `[[publish.alias]]` | Publishes one private Artifact under a label, revealing only the fields named in `reveal` | FR-028, ADR-0011 |
| `[exclude].artifacts` | Omitted from the graph, retained in the store, reversible | FR-008 |
| `[[identity.merge]]` | Declares two ids to be one Artifact. Overrides always win | FR-005 |
| `[[identity.separate]]` | Declares one id to be two Artifacts — the escape hatch for a fork the Author wants counted separately | FR-005 |
| `[[collections]]` | **Confirmed** Collection membership. `dendro suggest` proposes; only this file assigns | FR-021 |
| `[[succession]]` | The only way a `SUCCEEDS` edge comes into being. `dendro suggest` proposes pairs; the edge exists because this line does, never because the tool found a resemblance. `note` is optional and travels onto the edge | FR-011 |
| `[[epoch_markers]]` | Dated, labelled lines across the timeline. Declared, never inferred | FR-014 |

## Rules

- **Absent config is valid.** With no `dendrograph.toml`, `dendro scan <path>` works and
  publishing defaults to `public`. Zero setup is the demo path (SC-001).
- **No tokens.** Credentials come from the environment only, never from this file
  (Principle IV).
- **An unknown key is an error, not a warning.** A typo in `opt_in` that silently does
  nothing is a privacy failure, and this file is where privacy is decided. The same applies
  to an unknown value in `reveal`: it is rejected, never ignored.
- **`reveal` is a disclosure list, not a redaction list.** It names what may be published.
  Absent or empty, an alias publishes the node and its dates and nothing else. There is no
  way to express "publish everything except X", because a control shaped that way makes
  forgetting the failure mode (ADR-0011).
- **Declarations may name Artifacts that do not exist yet.** An id in `exclude` or
  `opt_in` with no matching store file is reported in the run report and is not an error
  — the Artifact may be on a drive that is currently unplugged.
