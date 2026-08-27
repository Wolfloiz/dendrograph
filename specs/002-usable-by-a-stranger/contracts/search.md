# Contract: search

Two surfaces, one vocabulary. A visitor and an Author asking the same question get the same
shape of answer over different scopes.

## `dendro search <query>`

```text
usage: dendro search [-h] [--root ROOT] [--limit N] QUERY
```

| | |
|---|---|
| **Reads** | `graph.sqlite` in the archive's build output — the `full` build when present, otherwise the published one |
| **Writes** | Nothing. Prints. |
| **Scope** | Every Artifact in the build, **including those the published site withholds** — it runs on the Author's machine against their own archive |
| **Exit** | `0` with results, `0` with none, `2` when the archive has no search index |

Matching is FTS5 over `artifact_search(id, label, description)`. Ordering is FTS5 rank, then
name — mechanical, and explainable in one sentence, because an ordering that looks like a
judgement about which Artifact matters more would be an inference the tool does not make
(Principle I).

Output names the kind, the subject and why it matched:

```text
melissa-core           Artifact   name
fund-2-tutorials       Artifact   description: "…tutorial series built with Melissa…"
2 result(s).
```

**With no search index**, the command refuses rather than degrading:

```text
dendro: this archive was built without a search index. Rebuild it with a Python
        that has FTS5 (`python3 -c "import sqlite3; sqlite3.connect(':memory:')
        .execute('CREATE VIRTUAL TABLE t USING fts5(x)')"` must succeed), then
        run `dendro build` again.
```

A silent fall back to a linear scan would answer a different question without saying so, and
`sqlite.has_search()` exists precisely so the difference is knowable (R6).

## Search on the page

| | |
|---|---|
| **Scope** | The payload already loaded — nothing is fetched, and the published payload is already privacy-filtered |
| **Fields** | Artifact, Tool and Technique names; Artifact descriptions |
| **Timing** | Results appear while the visitor is still typing. No spinner, no debounce that is perceptible (SC-005) |
| **Ordering** | Prefix matches before substring matches; within each, the better-connected first |

### What the page's search must never do

- **Report matches it is withholding.** "3 results, 1 hidden" tells a visitor that private
  work matches that word. The published payload does not contain withheld Artifacts, so the
  count is naturally correct — the rule is that no code path may add a withheld count back.
- **Return a Tool or Technique with no published Artifacts.** If every Artifact using it was
  withheld, the node is not in the payload and the result cannot exist. A profile addressed
  directly for such a Tool renders the same *not found* as a Tool that never existed.
- **Guess.** A search matching nothing says so and offers nothing (FR-009).

## Shared vocabulary

Both surfaces call the same things by the same names, and both state *why* a row matched —
name or description. A visitor who searches a word that only appears in prose should be able
to tell that is what happened.
