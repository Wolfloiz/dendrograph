# Feature Specification: Usable by a stranger

**Feature Branch**: `002-usable-by-a-stranger`

**Created**: 2026-08-27

**Status**: Draft

**Input**: User description: "v0.2 — usable by a stranger. Four things, in the order the roadmap in `specs/001-git-collector/plan.md` sets them: a single screen with a view selector, replacing the two separate pages; a three-step fork README; FTS5 search over Artifact names and descriptions, using the virtual table v0.1 already populates and never queries; a Tool profile using the reverse `tool_to_artifacts` index v0.1 already ships unrendered. Carry forward from v0.1: T088's SC-001b validation is still owed."

## Context

v0.1 answers the Author's question: *what have I built, and since when*. It was validated
against a real archive of 97 Artifacts, and a stranger can open the published demo and see
a rendered graph in under five minutes with no credential (T089).

What v0.1 does **not** do is let that stranger get anywhere afterwards. There are two pages
with no relationship to each other, no way to ask a question of the archive, and no path
from "this is interesting" to "I want one". v0.2 closes those three gaps, for two different
strangers:

- **The visitor** — a recruiter, a collaborator, a person following a link. They arrive with
  a question about someone else's work and leave with an answer or without one.
- **The adopter** — someone who wants their own archive and will not read the source to get
  it.

Nothing about what the archive *contains* changes. No new node type, no new edge type, no
new inference. This release is entirely about reaching what is already there.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One screen instead of two pages (Priority: P1)

A visitor opens the archive and finds a single screen carrying every view of the same data.
Switching from the graph to the timeline is a control on the page, not a navigation to a
different document: the archive loads once, and what the visitor had selected or searched
survives the switch.

**Why this priority**: It is the frame the other three stories hang on. Search and the Tool
profile each need somewhere to live, and on two independent pages each would have to be
built twice and kept in step by hand. Shipping it alone already removes the worst thing
about the current site — that the two halves of the archive do not know about each other.

**Independent Test**: Open the published archive, switch between views, and confirm the
data was fetched once and the selection survived. Deliverable on its own: a visitor stops
losing their place.

**Acceptance Scenarios**:

1. **Given** the archive is open on the graph with a node selected, **When** the visitor
   switches to the timeline, **Then** the same Artifact is highlighted there and no page
   load occurs.
2. **Given** the archive is open on the timeline, **When** the visitor reloads the page or
   shares the address, **Then** the same view is restored.
3. **Given** the network is unplugged and the archive is opened from a file, **When** the
   visitor switches views, **Then** every view works — nothing is fetched on demand.

---

### User Story 2 - Ask the archive a question (Priority: P2)

A visitor types a word and gets back the Artifacts, Tools and Techniques that match it,
searching what an Artifact is *called* and what it is *described as* — not only its label.
The Author gets the same reach from the command line over their whole archive, including
the Artifacts the published site withholds.

**Why this priority**: It is the visitor's first move and the archive's first failure. With
2,432 nodes, "does this person know Rust" is currently answered by panning around a canvas.
Two surfaces are needed because the two questions differ: the visitor searches what was
published, the Author searches everything they own.

**Independent Test**: Search a word that appears only in a description, not in any name, and
confirm the Artifact comes back. Deliverable on its own: the archive becomes answerable.

**Acceptance Scenarios**:

1. **Given** an Artifact whose description mentions a word absent from every name, **When**
   the visitor searches that word, **Then** the Artifact is returned.
2. **Given** a search with no matches, **When** the visitor runs it, **Then** the archive
   says so plainly and offers no guess.
3. **Given** an archive containing withheld Artifacts, **When** the Author searches from the
   command line, **Then** withheld Artifacts appear; **When** a visitor searches the
   published site, **Then** they do not.
4. **Given** a result, **When** the visitor selects it, **Then** the current view moves to it
   rather than replacing the screen.

---

### User Story 3 - What one Tool means in this archive (Priority: P3)

A visitor picks a Tool and sees, on one screen: the span the Author can claim, the Artifacts
that use it, and the forks that use it but contribute no dates. The number that is claimed
and the number that is not are both visible, and it is clear which is which.

**Why this priority**: It is the résumé question — SC-007's *state years of experience with
no estimation from memory* — made browsable instead of computed. It ranks below search
because a visitor who cannot find the Tool cannot reach its profile.

**Independent Test**: Open the profile of a Tool that appears in at least one untouched
fork and confirm the claimed and unclaimed counts are both present and distinguishable.

**Acceptance Scenarios**:

1. **Given** a Tool used in Artifacts the Author committed to and in forks they did not,
   **When** the visitor opens its profile, **Then** the span, the claimed Artifact count and
   the untouched count all appear, and the untouched ones are marked as contributing no
   dates.
2. **Given** a Tool that appears only in untouched forks, **When** the visitor opens its
   profile, **Then** it claims no dates and says so, rather than showing an empty range.
3. **Given** no `[archive].emails` are configured, **When** the visitor opens any Tool
   profile, **Then** the span is labelled as observed activity, not as the Author's.

---

### User Story 4 - From someone else's archive to your own (Priority: P4)

A stranger who liked what they saw follows a README and has their own published archive
without reading any source. Three steps, each one a thing they do rather than a thing they
understand.

**Why this priority**: The highest value for the project and the lowest for any single
visitor, which is why it ships last rather than first. It also depends on nothing else here,
so it can move if the others slip.

**Independent Test**: Hand the README to someone who has never seen the repository and time
them to a published archive without answering questions.

**Acceptance Scenarios**:

1. **Given** a stranger with a GitHub account and no other setup, **When** they follow the
   three steps, **Then** they have a published archive of their own public repositories.
2. **Given** a stranger at any step, **When** they read it, **Then** it names what to do and
   what they will see, and never requires opening a source file.
3. **Given** a stranger who stops after step one, **When** they look at what they have,
   **Then** it is a working thing, not a broken half.

---

### Edge Cases

- **An archive with one Artifact.** A fresh fork of the template publishes an archive of
  almost nothing. Every view must render it without looking broken — an empty graph, a
  one-row timeline and a search with nothing to find are all normal states, not errors.
- **A Tool whose every use is withheld.** It must not appear in the published site at all,
  including in search results and as a profile reachable by address. Absence is the point
  (ADR-0005).
- **A search term that matches a withheld Artifact's description.** The published site must
  return nothing rather than a redacted row: a row that says "1 result, hidden" tells the
  visitor that private work matching that word exists.
- **A Technique or Tool with no dates at all.** Every view that shows a span must have a way
  to say *this claims nothing* that is distinguishable from *this has not loaded*.
- **The screen is a phone.** A view selector and a graph canvas compete for the same space;
  the archive must remain readable, and the timeline is the view that survives narrow.
- **A deep link into a view that no longer exists** — a Tool that was excluded, or an
  Artifact withheld since the address was shared. The screen must land somewhere sensible
  and say what happened.
- **An archive above 3,000 nodes.** The Author's own archive already holds 3,283 in the full
  build, and the layout's settling phase costs roughly 70 ms per frame there — above the
  33 ms that 30fps allows. This is the point the v0.1 spec named as where Barnes-Hut
  becomes necessary, and it is deferred to v0.3. v0.2 must not make it worse and must not
  pretend it is solved.

## Requirements *(mandatory)*

### Functional Requirements

**One screen**

- **FR-001**: The published archive MUST present every view of the data on a single screen,
  with a control that switches between them without loading another document.
- **FR-002**: The archive data MUST be loaded once per visit, regardless of how many views
  the visitor opens.
- **FR-003**: The current view, the selected node and the active search MUST be recoverable
  from the page address, so a visitor can share or reload what they are looking at.
- **FR-004**: Every view MUST work from a local file with no network access, as v0.1's do
  (ADR-0004).
- **FR-005**: A selection made in one view MUST survive the switch to another view when the
  same subject exists in both.

**Search**

- **FR-006**: The published archive MUST let a visitor search over what Artifacts, Tools and
  Techniques are named, and over what Artifacts are described as.
- **FR-007**: The command line MUST offer the Author the same search over the whole store,
  including Artifacts the published site withholds.
- **FR-008**: Search results MUST distinguish what kind of thing each result is.
- **FR-009**: A search that matches nothing MUST say so, and MUST NOT report the existence
  of matches it is withholding.
- **FR-010**: Selecting a result MUST move the current view to that subject rather than
  replacing the screen.

**Tool profile**

- **FR-011**: A visitor MUST be able to open one Tool and see its span, the Artifacts that
  use it, and the untouched forks that use it without contributing dates.
- **FR-012**: A Tool profile MUST distinguish a span the Author can claim from observed
  activity that is not attributed to them, using the `attributed` flag the graph already
  carries.
- **FR-013**: A Tool with no claimable dates MUST state that it claims none, rather than
  render an empty or zero range.
- **FR-014**: A Tool profile MUST be reachable from a search result and from the Tool's node
  in any view.

**The fork path**

- **FR-015**: The README MUST carry a path from an empty GitHub account to a published
  archive in three steps, each one an action rather than an explanation.
- **FR-016**: The path MUST NOT require reading, editing or understanding any source file.
- **FR-017**: Each step MUST state what the person will see when it worked, so a failure is
  visible at the step that caused it rather than at the end.
- **FR-018**: The path MUST state, at the point where it first publishes anything, exactly
  what the published site does and does not contain (Principle IV).

**What does not change**

- **FR-019**: No new node type, edge type or inference enters the graph. v0.2 reaches what
  v0.1 records.
- **FR-020**: The store format MUST NOT require a rescan to take advantage of anything in
  this release. Everything needed is already recorded (ADR-0002).

### Key Entities

No new graph entities. The graph vocabulary stays exactly as the constitution closes it:
Artifacts, Tools, Techniques, Periods, Collections, Authors, Dependencies, Epoch Markers.

Two entities exist in the interface only, and neither is stored:

- **View**: one way of reading the same archive — the graph, the timeline, a Tool profile.
  Views share a selection and a search; they do not own data.
- **Search result**: a subject, its kind, and why it matched — the name or the description.
  A result is a pointer into a view, never a copy of the record.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A visitor who knows a name finds it and lands on it in under 15 seconds from
  opening the archive, without scrolling any list.
- **SC-002**: A visitor moves between any two views without a page load, and without losing
  the node they had selected.
- **SC-003**: Asked *how long has this person used X, and on what*, a visitor answers from
  one screen without opening a second document or a file.
- **SC-004**: **Rewritten, not timed against the wrong clock a second time.** A stranger
  with a GitHub account and no prior knowledge reaches their own published archive following
  the README alone. Four conditions, all observable, none of them a stopwatch on the
  network:
  1. They **ask nothing** and **open no source file**.
  2. Every command **runs as pasted**, with no editing beyond the account name and the
     platform note the README already gives.
  3. Each step's *You should see* matches what they actually see, so a failure surfaces
     where it happened.
  4. Their **own time — reading, deciding and typing — stays under 10 minutes**, measured
     with the waiting removed: clock stops while a scan or clone runs.

  What the waiting costs is **SC-008's line, not this one**. A criterion that measures how
  many repositories someone owns and how fast their link is cannot be passed or failed by
  changing the README, which is the only thing this criterion is about.

  *Why it changed*: the walk happened on 2026-09-10 and took about twelve minutes, of which
  the clones were the larger part — the reading and the typing were not close. Under the old
  wording that is a failure, and the fix would have been to own fewer repositories. Two real
  defects surfaced on the same walk and were fixed: a command that could not be pasted
  (`<your-account>` is an input redirect in zsh and bash) and a `login` that printed
  "0 Artifact(s) added" under "Already authenticated", which reads as having failed. Both
  are interface defects, both are what this criterion exists to catch, and the old sentence
  scored them the same as a slow connection. The split keeps what the original protected —
  a newcomer who is never blocked, confused, or sent to read source — and hands the network
  to the criterion that already governs it.
- **SC-005**: A search over an archive of 3,000 nodes returns its results in under 50 ms per
  keystroke — fast enough that they appear while the visitor is still typing, with no spinner
  and no delay they can feel. The number is here because *no perceptible wait* cannot fail a
  test, and a criterion that cannot fail is not a criterion.
- **SC-006**: The published archive still opens from a file with the network unplugged, with
  no account and no install, and every view works. *(v0.1's SC-001, non-negotiable.)*
- **SC-007**: First render of the single screen stays within 2 seconds at 3,000 nodes, and
  panning holds at least 30fps — no worse than v0.1 measured. *(Carried from v0.1's SC-005.)*
- **SC-008**: **Rewritten, not inherited a second time.** A first full scan reports progress
  throughout and completes unattended, at a cost that stays linear in the number of
  repositories: **under 4 seconds per repository on a warm link**, with no super-linear term
  as the count grows. At that rate 500 repositories land inside 30 minutes, and the sentence
  is one that can be observed instead of one that waits for an account nobody here has.

  *Why it changed*: v0.1 wrote SC-001b as "a ~500-repository account completes a first full
  scan within 30 minutes" and could not test it — the largest account available holds 68.
  Everything else was measured: 68 real repositories at 3.06 s each, 500 synthetic ones flat
  at 0.111 / 0.130 / 0.110 s per repository across the run, and derived outputs at 500
  Artifacts under a second. Carrying the criterion unchanged into v0.3 would make it
  decoration — a line nobody can pass or fail. The rewritten one keeps what the original was
  protecting (an unattended run that does not silently hang or degrade) and drops the part
  that was never about the software.
