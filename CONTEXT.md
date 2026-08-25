# dendrograph

A knowledge graph of what a person has built. It points at an archive — starting
with git — and produces a navigable map of artifacts, tools, techniques and time.
This file is the project's glossary: the words we use and the words we refuse.

**The machine proposes, the Author disposes.** dendrograph is confident about what it
observed and deferential about what it interpreted: anything inferred is offered for
confirmation, never asserted. See `docs/adr/0009`.

Public surface is English: node and edge identifiers, CLI, file names, docs.
Code comments are Portuguese. See `docs/adr/` for that decision.

## Language

**Archive**:
The complete body of work belonging to one Author, across every account, disk and
host it happens to live on.
_Avoid_: Portfolio, collection (means something else here), corpus

**Artifact**:
One unit of work. A git repository under the git collector; a file under a future
Figma collector.
_Avoid_: Project, repo, item

**Collection**:
A grouping of Artifacts — a family, a client, a discipline.
_Avoid_: Group, folder, category

**Tool**:
Something used to build an Artifact: a language, a framework, a plugin.
_Avoid_: Technology, stack, dependency (means something else here)

**Technique**:
How an Artifact was built — a pattern, a method, an approach. Always carries a
confidence and the evidence it was inferred from.
_Avoid_: Skill, practice, pattern

**Period**:
A unit of time an Artifact is placed in: a year or a month.
_Avoid_: Date, era, timeframe

**Author**:
The identity that signs an Artifact.
_Avoid_: User, owner, contributor

**Dependency**:
Third-party work an Artifact reuses. Never authored by the Author.
_Avoid_: Library, package, vendor

**Collector**:
A component that reads one kind of source and fills the generic graph from it.
Collectors know about repositories and commits; the graph does not.
_Avoid_: Scanner, importer, adapter, plugin

**Lineage**:
The relationship between Artifacts that share material — one derives from another.
_Avoid_: Fork, copy, ancestry

**Succession**:
The relationship between Artifacts in time — one began where another stopped.
Distinct from Lineage: successors need share no material.
_Avoid_: Follow-up, next version

**Epoch Marker**:
A dated line the Author draws across their own timeline to give it meaning, such
as the arrival of AI assistants. Declared by the Author, never inferred.
_Avoid_: Era, AI boundary, cutoff

**Authorship**:
How much of an Artifact is the Author's own work, measured independently of the
Artifact's identity. A barely-touched fork and a rewritten one are the same
Artifact; only the second carries meaningful Authorship.
_Avoid_: Ownership, contribution, originality

**Confidence**:
How strongly a Technique is claimed, declared at the point of inference. Never a
quality score — dendrograph does not judge work.
_Avoid_: Score, rating, certainty
