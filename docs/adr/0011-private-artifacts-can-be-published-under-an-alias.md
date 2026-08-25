# Private Artifacts can be published under an alias, revealing nothing by default

An Author may publish a private Artifact as a node carrying a label they chose — "Anonymous
fintech project" — instead of its real name. The aliased Artifact keeps its place in the
graph and on the timeline; it loses its identity. Aliasing is declared per Artifact in
config, which makes it an opt-in of exactly the kind ADR-0005 already requires.

## Considered Options

Before this, publication had two poles: a private Artifact was **excluded** (the default) or
it contributed **aggregate shape** under redacted mode — "4 private repositories, Rust,
2019–2021". Neither serves the job-search case the tool exists for. Exclusion understates
years of experience, sometimes badly for an Author whose work is mostly under NDA.
Aggregation states the years but discards the shape: "four private repositories" is not a
line on a CV, while "anonymous fintech project, Rust and Kafka, 2019–2021, sole author" is.

Letting the Author list what to *hide* was rejected. Anonymisation fails by omission, and a
control shaped as "redact what you remember to redact" makes forgetting the failure mode.
Principle IV requires the safe path to be the lazy one, so an alias reveals nothing until
the Author names what may cross.

## Consequences

- **Disclosure is opt-in, per field.** `reveal` names what may be published — `period`,
  `tools`, `authorship`. Empty, which is the default, publishes the node and its dates and
  nothing else.
- **Some fields never cross, at any setting**: the real name, description and URL; source
  locators; Technique evidence paths; content hashes; and lineage edges to other Artifacts.
  Evidence paths are the sharpest of these — FR-010 requires every Technique to point at the
  file it was inferred from, and a path like `clientname/api/deploy.yml` published under an
  anonymous node destroys the anonymity without anyone having looked. A Technique published
  under an alias therefore ships without its pointer, and stops being verifiable; the
  contract says so rather than implying otherwise.
- **Lineage edges are withheld** because an edge from an anonymous node to a known public
  repository identifies the anonymous one.
- **Re-identification remains possible and is not solved here.** Exact dates, a Tool set and
  an authorship share can be enough for someone who knows the field. The tool narrows the
  surface; it cannot make a project unrecognisable to a reader who was there. Documentation
  must say this plainly rather than promise anonymity.
- **Auto-generated labels are numbered from the sorted Artifact id**, not from discovery
  order, so a newly scanned private Artifact never renumbers the others and the published
  site's diff stays readable.
- Aliasing supersedes redacted mode as the answer to "state my real years of experience
  publicly". Redacted mode stays, because it costs one config line for an Author who wants
  the number without curating anything.
