# dendrograph

A knowledge graph of what a person has built. It points at an archive — starting
with git — and produces a navigable map of artifacts, tools, techniques and time.
This file is the project's glossary: the words we use and the words we refuse.

**The machine proposes, the Author disposes.** dendrograph is confident about what it
observed and deferential about what it interpreted: anything inferred is offered for
confirmation, never asserted. See `docs/adr/0009`.

Public surface is English: node and edge identifiers, CLI, file names, docs. Code
comments are Portuguese. Prose documentation also exists in Portuguese — the seam is
that prose translates and the CLI does not, so `README.pt-br.md` carries the same
commands as `README.md`, byte for byte. See `docs/adr/0001`.

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
confidence and the evidence it was inferred from. **The names are a closed set**,
listed under *Technique names* below.
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
The window of **the Author's own commits** in the Artifacts that use a Tool or apply
a Technique. Not the Artifacts' whole activity — a fork carries its upstream's past,
and counting it read as seventeen years of a language for an account four years
old. A span states experience, so it must understate rather than overstate.

A Technique span carries one caveat a Tool span does not: Techniques are inferred
from the file tree as it stands, so `first` is the earliest the Author worked on an
Artifact that shows the marker **today**, never the date it was adopted.
_Avoid_: Range, usage, experience, years

**Technique names**:
A closed set, not free text. A Technique name is a node label and a node id, which
makes it public surface (ADR-0001) — and `Static Typing` alongside `static-typing`
would be two nodes for one thing. That is the same identity defect that cost a
build over `@babel/cli`, an npm package over its own capitalisation, and one
contributor over signing two ways; a free-text name is the fourth door into it.

The set, and what each one is inferred from:

| Name | Marker |
|---|---|
| Continuous Integration | a workflow or pipeline definition |
| Containerisation | a Dockerfile or compose file |
| Infrastructure as Code | Terraform, Ansible, Helm, Kubernetes manifests |
| Automated Testing | a test directory or test-named file |
| Database Migrations | a migrations directory |
| Documented Decisions | an ADR or decisions directory |
| Static Typing | a type-checker configuration |
| Pre-commit Hooks | a pre-commit or husky configuration |
| Linting | a linter configuration |
| Reproducible Environments | a Nix flake, devcontainer, or Vagrantfile |

Adding one is a deliberate act: it must name something observable from a marker that
means nothing else, it must read as a phrase a person would put on a CV, and it must
not be a judgement — "has tests" is observable, "well tested" is not (Principle V).
`tests/test_techniques.py` holds the table and this list to each other, so the
documentation cannot drift from the code without a test failing.
_Avoid_: Tag, label, category

**View**:
One way of reading the same archive — the graph, the timeline, a Tool profile. A
view renders and nothing else: it does not fetch, does not own the selection, and
does not know the other views exist. It is told what is selected. Exists in the
interface only; nothing about it is stored or published.
_Avoid_: Page, tab, screen (the screen is the one thing that holds the views)

**Selection**:
The subject the reader is looking at — a node id, or nothing. It lives in the
screen, survives a change of view, and is what the address carries. A view that
cannot render the current selection shows its normal state; the selection is not
lost by failing to fit in one.
_Avoid_: Focus (means the node under the cursor), highlight, active node

**Search result**:
A subject, its kind, and **why** it matched — the name or the description. Never a
copy of the record: a result carries a node id, so choosing one moves the view
that is open rather than replacing the screen. Two searches answer over different
scopes — the page over what was published, the command line over the whole store —
and say the same things by the same names.
_Avoid_: Hit, match (used for the reason, not the row), suggestion

**Untouched fork**:
An Artifact the Author never committed to. It is the same Artifact as its upstream
(identity is the root commit) and it stays in the archive, but it contributes no
dates to any Span and is counted apart.
_Avoid_: Fork (ambiguous — a rewritten fork is real work), clone, copy

**Alias**:
A name a private Artifact is published under, revealing nothing beyond the node, its
**id** and its dates until the Author names each field. Disclosure is opt-in per
field; there is no opt-out redaction.

The id is in that sentence because leaving it out made the sentence false. An
Artifact's id is the SHA of its root commit, and an aliased node publishes it
unchanged — so anyone holding a clone of the repository reproduces it with
`git rev-list --max-parents=0 HEAD` and confirms the match, and a private fork of
something public has a public root SHA already. Known, accepted and documented
rather than fixed. An alias is for the reader who does not have the repository, not
for one who does. See `docs/adr/0011`.
_Avoid_: Pseudonym, anonymised, masked, redacted (means a whole build mode here),
anonymity (it is not one)

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
