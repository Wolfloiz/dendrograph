## Agent skills

### Issue tracker

Specs, plans and tasks live under `specs/NNN-<slug>/`, managed by Spec Kit; `.scratch/` holds exploratory work. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, each label string equal to its name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` at the repo root plus `docs/adr/`. See `docs/agents/domain.md`.

### Project principles

`.specify/memory/constitution.md` is binding, and `docs/adr/` records why each decision was made. Work that contradicts either must say so explicitly rather than silently override it.

**The decisions already taken.** Read the full ADR before working in its area; this index exists so you always know one is there.

| ADR | Decides |
|---|---|
| 0001 | Public surface English (identifiers, CLI, file names, the graph schema), code comments Portuguese |
| 0002 | The store accumulates: `store/artifacts/<id>.json` is the source of truth; everything else is derived; scans append, never rebuild |
| 0003 | Artifact identity is the root commit SHA, separate from Authorship; a fork *is* the same Artifact |
| 0004 | No server, no graph database, no CDN or library on the page; ~3,000 nodes fit in a browser tab |
| 0005 | Private Artifacts are excluded from the published site by default; redacted mode publishes shape without names |
| 0006 | MIT, chosen over AGPL knowingly. Do not reopen without new information |
| 0007 | Local CLI first; a scheduled Actions run is one caller, not the product's home |
| 0008 | GitHub access via OAuth device flow, not a PAT; `gh auth token` is a shortcut; PAT for CI only |
| 0009 | The machine proposes, the Author disposes — coverage traded for trust, deliberately |
| 0010 | The tool repository and the Author's archive repository are separate; the tool holds no private Author data |

Feature-level interface contracts live in `specs/NNN-<slug>/contracts/`. Where a contract and an ADR disagree, the ADR wins.
