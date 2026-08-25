# dendrograph Constitution

dendrograph builds a knowledge graph of what a person has built, from an archive
spread across accounts, disks and hosts. These principles bind every feature.
The reasoning behind each is recorded in `docs/adr/`; domain vocabulary is defined
in `CONTEXT.md`.

## Core Principles

### I. The Machine Proposes, the Author Disposes (NON-NEGOTIABLE)

dendrograph is confident about what it observed and deferential about what it
interpreted. Anything inferred rather than measured is offered as a suggestion for
the Author to confirm; it is never written into the graph unilaterally. Pruning lists
candidates but never deletes. Identity can be overridden by hand. Epoch Markers are
declared, never inferred. `SUCCEEDS` edges are confirmed, not guessed.

Coverage is traded for trust, deliberately. A sparser graph the Author believes is
worth more than a dense one they must second-guess — this output gets repeated in
interviews and on CVs, where a confident wrong edge is a false claim about a person's
own career. (ADR-0009)

### II. The Store Accumulates; Sources Are Inputs

`store/artifacts/<id>.json` is the source of truth. Scans append; they never rebuild.
An Artifact seen once persists forever — after the drive dies, the repository is
deleted, or access is revoked. Disappearance is recorded as state, never as removal.
Everything else — `graph.json`, `graph.sqlite`, `llms.txt`, the published site — is a
derived build output. No feature may make the graph as mortal as its sources. (ADR-0002)

### III. No Server, No Graph Database, No Page Dependencies

dendrograph runs on the Author's machine and in their own Actions, and publishes to
their own Pages. No third-party server ever receives their data. No graph database:
3,000 nodes fit in a browser tab. No CDN and no graph library on the page, so it works
offline, from a pen drive, and on Pages with no configuration. A feature that requires
hosting, authentication or a data-processor relationship is out of scope by
construction. (ADR-0004, ADR-0007, ADR-0008)

### IV. Privacy Is the Default, Not a Setting

Private Artifacts enter the store and are excluded from the published site unless
opted in one by one. GitHub Pages on a public repository is a world-readable website;
no feature may leak a client, employer or private project name to it by default. Any
claim about privacy in user-facing text must state exactly what the published site
does and does not contain. Tokens are read from the environment, never written to
config or the store, and are read-only.

The tool repository and the Author's archive repository are **separate**: the tool holds
no Author data, and the committed store lives in a repository the Author owns and may
keep private. A feature that writes Author data into the tool repository is a defect.
(ADR-0005, ADR-0008, ADR-0010)

### V. Honest Inference, or None

dendrograph does not judge quality: no scores, no grades, no code review. It does not
prove complexity — it recognises markers of known cost with declared confidence,
because proving O(log n) is undecidable and pretending otherwise would be a lie. It
does not infer AI authorship, which is equally undecidable and whose failure mode is
mislabelling a person's proudest work.

Every inferred edge carries a confidence and a pointer to the evidence it came from.
Precision beats coverage: ten Techniques defensible in an interview beat eighty needing
apology, because one confident error teaches the Author that the whole layer is noise.

## Additional Constraints

- **Python 3.11+, standard library only.** A fork installs nothing. `tomllib` covers
  config, so config needs no parser and no dependency.
- **`unittest`**, not pytest — a consequence of stdlib-only.
- **Public surface is English**: node and edge identifiers, CLI, file and directory
  names, docs and README — including the schema, which ships inside `graph.json` and
  `llms.txt` for others to consume. Code comments are Portuguese. (ADR-0001)
- **MIT licensed.** Chosen knowingly over AGPL, trading protection against a closed
  hosted fork for contributor reach. Do not reopen without new information. (ADR-0006)
- **Collectors know about repositories and commits; the graph does not.** The graph
  speaks only of Artifacts, Tools, Techniques, Periods, Collections, Authors and
  Dependencies. This is what lets a non-git collector arrive without a redesign.

## Development Workflow

- **ADRs are binding.** Work that contradicts one must say so explicitly and argue for
  reopening it — never silently override it. New decisions meeting the bar (hard to
  reverse, surprising without context, a real trade-off) get a new numbered ADR.
- **Test what lies quietly, not what crashes.** The heuristics are the risk: identity
  and deduplication, authorship counting, Technique precision. Assert exact output
  against small real repositories committed as fixtures. Rendering and the force
  simulation need no tests.
- **New vocabulary lands in `CONTEXT.md`** when a term is resolved, not in a backlog.

## Governance

This constitution supersedes other practices. Amendments require an ADR recording what
changed and why, and a version bump below. Any plan or task that violates a principle
must either be redesigned or accompanied by an explicit, documented justification —
"it was easier" is not one.

**Version**: 1.1.0 | **Ratified**: 2026-08-24 | **Last Amended**: 2026-08-24
