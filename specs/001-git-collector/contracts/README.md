# Contracts — dendrograph v0.1

The interfaces the three implementation streams share. Everything here is a **contract**:
once an implementation stream depends on it, changing it means changing the other streams
too. Freeze these before parallel work begins.

| Contract | Written by | Read by |
|---|---|---|
| [`store-artifact.md`](./store-artifact.md) | core | collector (fills), core (owns), publish (filters) |
| [`graph.md`](./graph.md) | core | views, and any third party or agent consuming the archive |
| [`cli.md`](./cli.md) | all three | the Author, the archive repository's workflow |
| [`config.md`](./config.md) | core | all three |

## Scope

Public surface is English — field names, node and edge identifiers, command names, file
names (ADR-0001). These names ship inside `graph.json` and `llms.txt` for others to
consume, so they are part of the product, not an implementation detail.

The graph vocabulary is generic on purpose. Collectors know about repositories and
commits; the graph knows only Artifacts, Tools, Techniques, Periods, Collections,
Authors, Dependencies and Epoch Markers. A future non-git collector must be able to fill
this graph without a redesign.

## Schema versioning

Per FR-025, every store file and every derived output declares `schema_version`, and the
tool refuses a version it does not recognise rather than interpreting it by guesswork.

- `schema_version` is a single integer, incremented on any change that an older reader
  could misread. Adding an optional field does not increment it; renaming, removing or
  changing the meaning of a field does.
- The store and the derived outputs version **independently**. Derived outputs are
  rebuilt from the store on every run, so their version tracks the consumer contract;
  the store's version tracks the durable one and is the one that will ever need a
  migration.
- On reading a `schema_version` higher than it knows, the tool stops with an error
  naming the file and both versions. It never partially reads and never rewrites.

v0.1 ships `schema_version: 1` for both.

## Design decisions taken here

These are not settled by the spec or by an ADR. They are decided here so the streams can
proceed; each is cheap to revisit **before** implementation and expensive after, because
the store is committed and accumulates (Principle II).

1. **Artifact ids are prefixed by their derivation method** — `root-<sha>` or
   `content-<sha>` — so a file name says how its identity was obtained. Without the
   prefix, a root-commit SHA-1 and a content SHA-256 are indistinguishable strings, and
   an override that changes the method would be invisible in `git diff`.
2. **Author declarations live in config, not in the store.** The store holds what was
   *observed*; `dendrograph.toml` holds what the Author *decided*. This keeps the store
   machine-written and the config human-written, makes every declaration reversible by
   deleting a line (ADR-0002), and means a declaration can be made about an Artifact
   before it has ever been scanned. Store files record which declarations were applied
   to them, for traceability only.
3. **`graph.json` carries its own schema description**, so a consumer needs no companion
   documentation. This is what FR-017 means by output "for consumption by other programs
   and by AI agents".
