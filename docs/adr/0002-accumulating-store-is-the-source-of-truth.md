# The store accumulates; sources are inputs, not the source of truth

Scans append to a persisted store rather than rebuilding the graph from whatever
the sources currently say. An Artifact seen once stays in the graph forever, even
after the drive dies, the repository is deleted or access is revoked; disappearance
is recorded as state (`last_seen`), never as removal.

## Considered Options

A pure rebuild — regenerate everything from live sources on each run — was the
obvious pipeline shape and is what the original design implied. It was rejected
because it makes the graph exactly as mortal as its sources: scan an external
drive in 2019, lose the drive in 2020, and forty Artifacts vanish on the next run.
That directly contradicts the product's premise, that the record already exists
and merely isn't legible.

## Consequences

- `store/artifacts/<id>.json` — one committed JSON file per Artifact — is the source
  of truth. Per-file diffs make each run reviewable, merges between machines resolve
  per Artifact, and corruption costs one entry rather than the archive. A committed
  SQLite file was rejected for being unmergeable and undiffable.
- `graph.json`, `graph.sqlite` and `llms.txt` become **derived build outputs**,
  regenerated from `store/` on every run.
- Pruning is declarative: an `exclude` list in config omits an Artifact from the
  graph while leaving it in the store, and is reversible by deleting a line.
  `dendro prune` only *lists* candidates to paste. A tool built because human memory
  is unreliable must not offer one-command amnesia.
