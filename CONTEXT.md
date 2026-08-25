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

## Resolved while building

Words the implementation forced us to be precise about. Each is here because
being vague about it produced something false.

**Observation**:
What one scan of one repository yields — never written over what is stored, always
merged into it. A field the observation could not see stays as it was; an
unreachable drive must not blank an Artifact.
_Avoid_: Snapshot, sync, import

**Source**:
A place an Artifact was seen: a kind and a locator. One Artifact carries every
source it was ever seen in, and neither overwrites the other. **Distinct from the
Artifact**: losing every source loses nothing, because the store is the record.
_Avoid_: Remote, origin, location

**Reachable**:
Whether a source answered on the last run. Not reaching one is a state that gets
recorded, never a deletion, and it does not advance `last_seen` — nothing was seen.
_Avoid_: Missing, deleted, gone, stale

**Span**:
A Tool's window: the first and last of **the Author's own commits** in Artifacts
using it. Not the Artifacts' whole activity — a fork carries its upstream's past,
and counting it read as seventeen years of a language for an account four years
old. A span states experience, so it must understate rather than overstate.
_Avoid_: Range, usage, experience, years

**Untouched fork**:
An Artifact the Author never committed to. It is the same Artifact as its upstream
(identity is the root commit) and it stays in the archive, but it contributes no
dates to any Span and is counted apart.
_Avoid_: Fork (ambiguous — a rewritten fork is real work), clone, copy

**Alias**:
A name a private Artifact is published under, revealing nothing beyond the node and
its dates until the Author names each field. Disclosure is opt-in per field; there
is no opt-out redaction. See `docs/adr/0011`.
_Avoid_: Pseudonym, anonymised, masked, redacted (means a whole build mode here)

**Build mode**:
`public`, `redacted` or `full`. It chooses the **output directory**, not a filter
applied afterwards — `full` writes to `.dendro-local/` and therefore cannot reach a
published path even by mistake.
_Avoid_: Privacy level, visibility (means an Artifact's own state), profile

**Declaration**:
A line in `dendrograph.toml` where the Author decides something the machine only
proposed. Declarations live in config, never in the store: the store is the
observed record, and mixing the two makes it impossible to say which is which.
_Avoid_: Override (only one kind is), setting, annotation

**Identifying set** / **Authored set**:
Two different file sets, and conflating them breaks identity. The identifying set
is every tracked file outside an excluded directory, and answers *which Artifact is
this*. The authored set is stricter — no lockfiles, nothing under 512 bytes — and
answers *did these two share material*. A repository of small files has an identity
and no lineage; treating one set as both gave it neither.
_Avoid_: Fingerprint, file list, content
