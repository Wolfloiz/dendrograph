# Artifact identity is the root commit SHA, and is separate from authorship

An Artifact is identified by the hash of its repository's first commit, which is
identical across every clone, rename, re-host and drive — so the same project found
on a dead 2019 disk and on GitHub today collapses into one Artifact automatically.
Non-git Artifacts and repositories with no commits fall back to a content hash of a
stable file subset, and the Author can override identity by hand when the machine
gets it wrong.

## Consequences

A fork shares its root commit with upstream, so under this rule a fork **is** the
same Artifact as the original. That is deliberate: it gives fork detection for free.
It also forces identity and Authorship apart — the root commit answers *which*
Artifact this is, while per-author commit and line counts answer *how much of it is
mine*. This is what lets dendrograph report a repository count without inflating it
with untouched forks.
