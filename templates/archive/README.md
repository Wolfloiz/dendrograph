What this repository contains, and what it does not
====================================================

This is a dendrograph archive: one Author's body of work as a knowledge graph.

`store/artifacts/` — the source of truth. Every Artifact the scans observed,
private ones included. It stays in this repository and is never published;
only derived outputs filtered for privacy leave it (ADR-0002, ADR-0005).

`site/` — the published output, rebuilt from the store on every run:

- Under the default (`public`) mode it contains **no private Artifact**: no
  name, no description, no URL, no source locator, no Technique evidence path.
- In `redacted` mode an aggregate says how much was withheld — counts, Tools,
  a date range — and never a name.
- A private Artifact appears only if you alias it or opt it in. An aliased one
  publishes under your chosen or generated label, carrying exactly what
  `reveal` names and nothing more.

What an alias does not promise
------------------------------

An alias narrows re-identification; it does not solve it. Exact dates plus a
Tool set plus an authorship share can be enough for a reader who was there.
A Technique published under an alias ships without its evidence pointer and is
therefore not verifiable — that loss is stated, not hidden.

How to use this template
------------------------

1. Create a repository from this template and edit `dendrograph.toml`.
2. Run `dendro scan` locally, or let `.github/workflows/update.yml` refresh
   GitHub-sourced Artifacts on a schedule. CI uses a fine-grained PAT stored
   as the `DENDRO_GITHUB_TOKEN` secret — PATs are supported for CI only
   (ADR-0008); interactively, use `dendro login`.
3. Run `dendro build`. Public and redacted builds write to `site/`, which is
   committed. A full build writes to `.dendro-local/`, which is gitignored and
   never deployed.
4. Run `dendro publish` to push `site/` to `[publish].target_repository` when
   configured — the path for keeping this repository private while the site is
   public (ADR-0010).
5. Serve `site/` with GitHub Pages or open it straight from disk: it works
   with no network and no credential (FR-016).
