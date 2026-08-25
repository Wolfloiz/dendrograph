"""Find git repositories in a folder, with the fidelity the GitHub path has.

This is the half no API can reach: a dead drive, an old laptop backup, a client
handover that never became a remote. Everything after discovery is identical to
the GitHub path — discovery is the only thing that differs (FR-001).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from collectors.git import plumbing

# Não descemos nestes: são grandes, nunca contêm trabalho do Author, e um
# `node_modules` de projeto grande sozinho dobra o tempo da varredura.
SKIPPED_DIRECTORIES = frozenset(
    {
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".gradle",
        "vendor",
        "target",
        "dist",
        "build",
        ".next",
        ".cache",
    }
)

# Um diretório com estes três é um repositório bare — um `git clone --bare`
# ou o backup de um servidor, sem working tree e sem `.git` para reconhecer.
BARE_MARKERS = ("HEAD", "objects", "refs")


@dataclass
class Discovery:
    """What a walk found, and what it could not read."""

    repositories: list[Path] = field(default_factory=list)
    unreachable: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.unreachable


def looks_bare(path: Path) -> bool:
    return all((path / marker).exists() for marker in BARE_MARKERS)


def discover(root: Path | str) -> Discovery:
    """Every git repository under `root`, without descending into any of them.

    A repository inside a repository is vendored code or a submodule, not a
    separate Artifact of the Author's — descending would store someone else's
    work under the Author's name.
    """
    found = Discovery()
    root = Path(root).expanduser()

    if not root.exists():
        found.unreachable.append(f"{root} (no such path)")
        return found
    if root.is_file():
        found.unreachable.append(f"{root} (not a directory)")
        return found

    if plumbing.is_repository(root) or looks_bare(root):
        found.repositories.append(root.resolve())
        return found

    def on_error(error: OSError) -> None:
        # Um diretório ilegível é reportado, nunca omitido em silêncio (FR-019).
        found.unreachable.append(f"{error.filename} ({error.strerror})")

    # followlinks fica falso de propósito: um link para um ancestral faz a
    # caminhada girar para sempre, e um repositório linkado será alcançado
    # pelo seu caminho real de qualquer forma.
    for current, directories, _ in os.walk(root, topdown=True, onerror=on_error):
        here = Path(current)

        if ".git" in directories or looks_bare(here):
            found.repositories.append(here.resolve())
            directories[:] = []
            continue

        directories[:] = sorted(
            d for d in directories
            if d not in SKIPPED_DIRECTORIES and not d.startswith(".git")
        )

    found.repositories = sorted(set(found.repositories))
    return found
