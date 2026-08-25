"""Artifact identity — which Artifact this is, never how much of it is yours.

Primary identity is the SHA of the repository's root commit, which is identical
across every clone, rename, re-host and drive. A fork shares upstream's root
commit and is therefore the same Artifact: deliberate, and the source of free
fork detection (ADR-0003). Authorship answers the other question, separately.

See `specs/001-git-collector/contracts/store-artifact.md`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from collectors.git import plumbing

METHOD_ROOT_COMMIT = "root_commit"
METHOD_CONTENT_HASH = "content_hash"
METHOD_OVERRIDE = "override"

MINIMUM_AUTHORED_BYTES = 512

EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        "node_modules",
        "vendor",
        ".venv",
        "venv",
        "target",
        "dist",
        "build",
        "__pycache__",
    }
)

EXCLUDED_FILENAMES = frozenset(
    {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "Cargo.lock",
        "Gemfile.lock",
        "composer.lock",
        "go.sum",
    }
)


class Unidentifiable(Exception):
    """No stable identity is derivable.

    Raised for a repository with neither commits nor tracked files. Such an
    Artifact is reported and NOT stored: a generated id would change between
    runs and accumulate junk in a store that never deletes.
    """


@dataclass(frozen=True)
class Identity:
    method: str
    value: str
    fallback_content_hash: str | None = None

    @property
    def artifact_id(self) -> str:
        prefix = "root" if self.method == METHOD_ROOT_COMMIT else "content"
        return f"{prefix}-{self.value}"

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "value": self.value,
            "fallback_content_hash": self.fallback_content_hash,
        }


def is_identifying(relative_path: str) -> bool:
    """Does this file contribute to the Artifact's identity?

    Every tracked file outside an excluded directory, with no size floor: a
    repository of small files is perfectly identifiable, it simply has nothing
    substantial in it. This set determines identity, so changing it changes the
    ids of already-stored Artifacts — treat additions as a schema version bump.
    """
    return not any(part in EXCLUDED_DIRECTORIES for part in Path(relative_path).parts)


def is_authored(relative_path: str, size: int) -> bool:
    """Is this file substantial material of the Author's own, for lineage?

    Stricter than `is_identifying`: lockfiles and anything under 512 bytes are
    excluded because they are too common to be evidence of shared descent
    (FR-012). Identity must not use this set — a repository whose files are all
    small would come out with no identity at all.
    """
    if not is_identifying(relative_path):
        return False
    if Path(relative_path).name in EXCLUDED_FILENAMES:
        return False
    return size >= MINIMUM_AUTHORED_BYTES


def _hashed_files(repository: Path, keep) -> list[tuple[str, int, str]]:
    rows: list[tuple[str, int, str]] = []
    for relative in plumbing.tracked_files(repository):
        absolute = repository / relative
        if not absolute.is_file():
            continue
        size = absolute.stat().st_size
        if not keep(relative, size):
            continue
        digest = hashlib.sha256(absolute.read_bytes()).hexdigest()
        rows.append((relative, size, digest))
    return sorted(rows, key=lambda row: row[0])


def identifying_files(repository: Path | str) -> list[tuple[str, int, str]]:
    """(path, size, sha256) for the identity set, sorted by POSIX path."""
    return _hashed_files(Path(repository), lambda path, size: is_identifying(path))


def authored_files(repository: Path | str) -> list[tuple[str, int, str]]:
    """(path, size, sha256) for the lineage set, sorted by POSIX path."""
    return _hashed_files(Path(repository), is_authored)


def _roll_up(rows: list[tuple[str, int, str]]) -> str | None:
    if not rows:
        return None
    digest = hashlib.sha256()
    for path, size, file_hash in rows:
        digest.update(f"{path}\0{size}\0{file_hash}".encode("utf-8"))
    return digest.hexdigest()


def content_hash(repository: Path | str) -> str | None:
    """SHA-256 over the identity set. Deterministic across machines and filesystems."""
    return _roll_up(identifying_files(repository))


def lineage_hash(repository: Path | str) -> str | None:
    """SHA-256 over the lineage set, or None when nothing substantial is tracked."""
    return _roll_up(authored_files(repository))


def _earliest_root(repository: Path | str, roots: list[str]) -> str:
    """The root commit with the earliest committer date; ties break on the SHA.

    A repository with merged histories has more than one root, and picking by
    order of appearance would make identity depend on how git happened to walk
    the graph.
    """
    if len(roots) == 1:
        return roots[0]
    dated = [(plumbing.commit_date(repository, sha), sha) for sha in roots]
    return min(dated)[1]


def resolve(repository: Path | str) -> Identity:
    """Identity for one repository on disk.

    The content hash is computed for *every* Artifact, not only as a fallback:
    it is what lets a squashed import or a `filter-branch` be recognised later
    as an existing Artifact whose root commit changed.
    """
    repository = Path(repository)
    hashed = content_hash(repository)
    roots = plumbing.root_commits(repository)
    if roots:
        return Identity(
            method=METHOD_ROOT_COMMIT,
            value=_earliest_root(repository, roots),
            fallback_content_hash=hashed,
        )
    if hashed is None:
        raise Unidentifiable(
            f"{repository}: no commits and no authored files — "
            "no stable identity is derivable, so this Artifact is reported, not stored"
        )
    return Identity(method=METHOD_CONTENT_HASH, value=hashed)


def apply_overrides(artifact_id: str, config) -> str:
    """Author declarations always win (FR-005).

    A merge folds several ids into the first one listed; a separation is applied
    by the caller, which knows which source it is looking at.
    """
    for merge in config.merges:
        if artifact_id in merge.ids:
            return merge.ids[0]
    return artifact_id


def separated_id(artifact_id: str, locator: str, config) -> str:
    """Split one Artifact into two when the Author says the machine got it wrong.

    The declared locator keeps a derived id of its own, so a fork the Author
    rewrote can be counted separately from the upstream it shares a root with.
    """
    for separation in config.separations:
        if separation.id == artifact_id and separation.locator == locator:
            suffix = hashlib.sha256(locator.encode("utf-8")).hexdigest()[:12]
            return f"{artifact_id}-{suffix}"
    return artifact_id
