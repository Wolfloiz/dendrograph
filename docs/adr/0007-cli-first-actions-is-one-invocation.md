# dendrograph is a local CLI first; Actions is one place to invoke it

`dendro` is a command run on any machine that can reach some sources; a scheduled
GitHub Actions workflow is simply one caller of it, not the product's home.

## Considered Options

Running only in Actions was the original design, but it is incompatible with the
project's own promise to scan local folders: an Actions runner is an ephemeral
container in a datacentre with no access to the author's disks, old laptops or
external drives — which is precisely where the unrecoverable, pre-AI-age work lives.
Actions-only would amputate the half of an archive that most needs rescuing.

## Consequences

Because the committed store is the source of truth (ADR 0002), where a scan ran stops
mattering: any machine scans what it can reach and commits what it saw. A drive can be
scanned once, in 2026, and die in 2027 with its Artifacts preserved. Scheduled Actions
runs refresh GitHub-sourced Artifacts and auto-commit the store.
