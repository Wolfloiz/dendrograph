# Feature Specification: dendrograph v0.1 — git collector

**Feature Branch**: `001-git-collector`

**Created**: 2026-08-24

**Status**: Draft

**Input**: Derived from `initial-ideia-project.md` and four rounds of design grilling.
Decisions are recorded in `docs/adr/0001`–`0009`; vocabulary in `CONTEXT.md`;
principles in `.specify/memory/constitution.md`. Technical choices live in `plan.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See my whole archive at once (Priority: P1)

A developer with more than a decade of work points dendrograph at their GitHub account
and, within minutes, sees every repository they have ever authored laid out on a
timeline and as a graph — grouped into Collections, connected to the Tools they used,
placed in the Periods they happened. Today no tool shows the whole; each one shows a
single project at a time.

**Why this priority**: This is the product. Without it nothing else has anything to
attach to, and it is the smallest thing that delivers the core value — knowing what
you have.

**Independent Test**: Run against an account with public repositories only, with no
authentication, and confirm a browsable timeline and graph are produced.

**Acceptance Scenarios**:

1. **Given** an Author with public repositories and no credentials configured,
   **When** they run dendrograph, **Then** a static site is produced showing every
   discovered Artifact on a timeline and in a graph.
2. **Given** an Author whose archive contains forks alongside authored work,
   **When** the graph is built, **Then** forks are distinguishable from authored work
   and do not inflate the Artifact count.
3. **Given** the same project present on two different paths, **When** both are
   scanned, **Then** one Artifact appears, not two.

---

### User Story 2 - Rescue work that no API can reach (Priority: P1)

The same developer has an external drive and an old laptop holding projects that were
never pushed anywhere — much of their pre-AI-age work. They scan those folders once.
The Artifacts enter the archive permanently, and remain there after the drive fails.

**Why this priority**: Equal to P1 above, and the actual differentiator. Every
competing tool reaches only what an API serves. This reaches the work that is otherwise
lost, and it is the reason the store accumulates rather than rebuilds.

**Independent Test**: Scan a local folder, confirm its Artifacts are stored, then rename
or remove the folder and re-run. The Artifacts must still be present in the graph.

**Acceptance Scenarios**:

1. **Given** a local folder of git repositories, **When** the Author scans it,
   **Then** its Artifacts appear in the archive with the same fidelity as
   GitHub-sourced ones.
2. **Given** an Artifact whose source has since disappeared, **When** the archive is
   rebuilt, **Then** the Artifact remains, marked with when it was last seen.
3. **Given** a project that exists both on a local drive and on GitHub, **When** both
   sources are scanned, **Then** they resolve to a single Artifact.

---

### User Story 3 - Answer "how long have I done X?" with a number (Priority: P2)

Filling in a job application, the Author needs "years of experience" with a specific
Tool. Instead of estimating from memory — the least reliable source available — they
read it off their own timeline: since when, how much, in what.

**Why this priority**: The most common concrete job the tool is hired for, but it needs
P1's graph to exist first.

**Independent Test**: With an archive built, confirm the earliest and latest use of a
given Tool are visible and traceable to specific Artifacts.

**Acceptance Scenarios**:

1. **Given** a built archive, **When** the Author looks at a Tool, **Then** they can see
   when they first and last used it and which Artifacts it appears in.
2. **Given** private Artifacts contribute to a Tool's history, **When** the site is
   published publicly, **Then** the Tool's span is still expressible without revealing
   private Artifact names.

---

### User Story 4 - Publish without leaking a client (Priority: P2)

The Author publishes their archive as a public site to share in a job search. Nothing
about their private repositories, clients or employers appears there unless they
explicitly chose to include it.

**Why this priority**: An NDA breach would be worse than the tool not existing, so the
safe behaviour must ship with the first publishable version — not after.

**Independent Test**: Build an archive containing private Artifacts and confirm no
private name appears anywhere in the published output.

**Acceptance Scenarios**:

1. **Given** an archive with private Artifacts, **When** the site is published with
   default settings, **Then** no private Artifact name, description or URL appears in
   any published file.
2. **Given** the Author enables redacted mode, **When** the site is published, **Then**
   private Artifacts contribute aggregate shape only — counts, Tools, date ranges —
   with no identifying names.
3. **Given** the Author opts a specific private Artifact in, **When** the site is
   published, **Then** only that Artifact appears.

---

### User Story 5 - Read my own history as a narrative (Priority: P3)

The Author draws a dated line across their own timeline — "before AI assistants", "went
freelance", "left the agency" — and reads their work in relation to it. Where the tool
cannot know something, it asks rather than guesses: it proposes that one project
succeeded another, and the Author confirms or rejects.

**Why this priority**: Meaning-making rather than inventory. Valuable, but only once the
inventory is trustworthy.

**Independent Test**: Declare a marker and confirm it appears on the timeline; run the
suggestion command and confirm no edge is created without confirmation.

**Acceptance Scenarios**:

1. **Given** the Author declares a dated marker with a label, **When** the timeline
   renders, **Then** the marker is drawn and Artifacts read as before or after it.
2. **Given** dendrograph identifies plausible succession pairs, **When** it reports
   them, **Then** no edge exists in the graph until the Author confirms it.

---

### Edge Cases

- **A repository with no commits.** Root-commit identity is unavailable; the fallback
  must produce a stable identity or the Artifact must be reported as unidentifiable —
  never assigned a random one that changes between runs.
- **Two clones with divergent history.** Same root commit, different later commits: one
  Artifact, with observations merged rather than one silently overwriting the other.
- **A fork the Author rewrote substantially.** Same Artifact as upstream by identity,
  but Authorship must reflect the real contribution.
- **Rewritten history** (squashed import, `filter-branch`): the root commit changes and
  the Artifact appears to be new. The Author needs a way to declare them the same.
- **An Artifact excluded, then un-excluded.** Its data must return intact, since
  exclusion never deleted it.
- **Rate limiting while unauthenticated.** Discovery must degrade gracefully and report
  what it could not reach, never truncate silently.
- **An Artifact that changes visibility** from private to public or back between runs.
  Visibility is re-evaluated at every publish from the most recent observation, so an
  Artifact that turned private drops out of the site without the Author acting, and the
  run report names it as removed.
- **A source unreachable this run** (drive unmounted, access revoked) — indistinguishable
  from deleted, and must not be treated as deletion either way.
- **An Author on a free plan with private Artifacts.** Pages from a private repository
  requires a paid plan, so the archive cannot be both private and directly published.
- **A Collection suggestion the Author never answers.** Artifacts must remain usable and
  ungrouped rather than blocked awaiting confirmation.

## Clarifications

### Session 2026-08-24

- Q: When dendrograph clones a GitHub repository to scan it, is the clone kept on disk between runs or discarded? → A: Full-history clone (no working tree) into a temporary directory, discarded at the end of each run.
- Q: What is the maximum acceptable duration for a first full scan of roughly 500 public repositories? → A: 30 minutes, with progress reported throughout.
- Q: Must every store file carry a schema version so later versions can read or migrate files written by earlier ones? → A: Yes — every store file and every derived output carries a schema version, and unknown versions are refused rather than guessed at.
- Q: When an already-published Artifact turns from public to private between runs, what happens to it in the published site? → A: Publishing re-evaluates visibility every run; the Artifact drops out of the site and the run report says it was removed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST discover Artifacts from a GitHub account and from local folders.
- **FR-002**: System MUST work with no credentials configured, limited to public Artifacts.
- **FR-003**: System MUST offer at least one *interactive* authentication path that does
  not require the Author to manually generate or paste a key. Unattended runs MAY use a
  stored token, since no browser is available to approve one.
- **FR-004**: System MUST assign each Artifact a stable identity that survives cloning,
  renaming, re-hosting and moving between disks.
- **FR-005**: System MUST resolve the same project found in multiple places to a single
  Artifact, and MUST let the Author override identity in both directions.
- **FR-006**: System MUST distinguish *which* Artifact something is from *how much of it*
  the Author wrote.
- **FR-007**: System MUST retain every Artifact it has ever seen, independently of whether
  its source still exists, and MUST record when each was last seen.
- **FR-008**: System MUST NOT delete stored Artifacts as part of any routine operation.
  Exclusion MUST be reversible and MUST NOT discard data.
- **FR-009**: System MUST record for each Artifact: its Author, its Tools, its Period, its
  Collection, and per-author contribution counts.
- **FR-010**: System MUST attach a confidence and a pointer to supporting evidence to every
  inferred Technique.
- **FR-011**: System MUST NOT create a `SUCCEEDS` edge without explicit Author confirmation.
- **FR-012**: System MUST infer `DERIVES_FROM` only from substantial shared authored
  material, excluding dependencies, lockfiles, generated output and trivial files.
- **FR-013**: System MUST exclude private Artifacts from published output by default, and
  MUST support per-Artifact opt-in and an aggregate redacted mode.
- **FR-014**: System MUST let the Author declare any number of dated, labelled markers on
  the timeline, and MUST NOT infer them.
- **FR-015**: System MUST NOT assign quality scores, prove complexity claims, or infer
  whether work was AI-generated.
- **FR-016**: System MUST publish a self-contained static site that functions with no
  network access and no configuration.
- **FR-017**: System MUST emit machine-readable output describing the archive for
  consumption by other programs and by AI agents.
- **FR-018**: System MUST produce a reviewable record of what each run changed.
- **FR-019**: System MUST report sources it could not reach, rather than omitting them
  silently.
- **FR-020**: System MUST expose commands covering: scanning a source, authenticating,
  building outputs, publishing, proposing inferred relationships, and listing prune
  candidates.
- **FR-021**: System MUST propose candidate Collections from observable signals and MUST
  NOT assign an Artifact to a Collection without Author confirmation.
- **FR-022**: System MUST record the third-party Dependencies an Artifact reuses,
  distinguishing them from the Tools it was built with.
- **FR-023**: System MUST NOT write private Author data into the tool's own repository,
  and MUST NOT place private Artifact data in any repository the Author has not designated
  as private — including in version history. The tool repository's `examples/` demo archive
  contains public Artifacts only, which is what the privacy default produces (ADR-0010).

- **FR-024**: System MUST clone remote Artifacts with their complete commit history — root
  commit and per-author counts depend on it — into a temporary working directory that is
  discarded at the end of the run. No cloned source is retained between runs; only the
  store persists.

- **FR-025**: Every stored Artifact and every derived output MUST declare the schema
  version it was written against, and the System MUST refuse to read a version it does not
  recognise rather than interpret it by guesswork.

- **FR-026**: System MUST re-evaluate every Artifact's visibility at each publish, from the
  most recently observed value, and MUST report each Artifact whose change in visibility
  removed it from the published output.
- **FR-027**: System MUST compute Tool spans across every Artifact regardless of
  visibility, and MUST express a span supported by private Artifacts without naming them —
  the span's dates and counts are published; the Artifacts behind it are not.

### Key Entities

- **Archive**: the complete body of work belonging to one Author, across every account,
  disk and host.
- **Artifact**: one unit of work; a git repository under this collector. Carries identity,
  provenance, dates, contribution counts, visibility and last-seen state.
- **Collection**: a grouping of Artifacts — a family, a client, a discipline.
- **Tool**: something used to build an Artifact — a language, a framework.
- **Technique**: how an Artifact was built; always carries confidence and evidence.
- **Period**: a unit of time an Artifact is placed in.
- **Author**: the identity that signs an Artifact.
- **Dependency**: third-party work an Artifact reuses.
- **Epoch Marker**: a dated line the Author draws across their timeline. Declared, never
  inferred.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A stranger who opens the tool's demo archive sees a rendered graph of a real
  archive in under five minutes, without creating any credential.
- **SC-001b**: An Author with roughly 500 public repositories completes a first full scan
  in a single unattended run of at most 30 minutes, with progress reported throughout and
  no manual intervention.
- **SC-002**: The same project present in three locations produces exactly one Artifact.
- **SC-003**: After a source is removed and the archive rebuilt, 100% of previously seen
  Artifacts remain present.
- **SC-004**: Zero private Artifact names appear in published output under default
  settings, and zero appear in any public repository or its version history.
- **SC-005**: An archive of roughly 500 Artifacts (~3,000 nodes) reaches first render in
  under 2 seconds and sustains at least 30fps while panning, from a file opened with no
  network access.
- **SC-006**: Every Technique claim in the output can be traced to the specific evidence it
  was derived from.
- **SC-007**: The Author can state years of experience with a given Tool from the output,
  with no estimation from memory, and the figure is correct even when private Artifacts
  contribute to it.
- **SC-008**: No edge in the graph asserts a relationship the Author did not either observe
  or confirm.

## Assumptions

- The Author has local access to at least one source: a GitHub account or a folder of
  repositories.
- Archives are personal in scale — hundreds to low thousands of Artifacts, not millions.
- The Author is willing to run a command locally; a purely hosted experience is out of
  scope by principle, not by omission.
- Git is the only collector in this feature. The graph vocabulary is deliberately generic
  so later collectors need no redesign, but none ship here.
- The published site is the Author's own; dendrograph never hosts anything.
- The Author's archive lives in a repository separate from the tool's, created from a
  template, and may be private (ADR-0010).
- Non-git sources, search, AST-based detection, other forges, an MCP server and any LLM
  layer are explicitly deferred beyond this feature.
