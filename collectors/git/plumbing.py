"""Thin wrappers over the `git` binary.

Collectors know about repositories and commits; the graph does not (Principle V).
Everything git-shaped lives behind this module.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(Exception):
    pass


def _env() -> dict:
    # Isola de config da máquina e nunca deixa o git pedir credencial numa
    # execução desatendida.
    env = dict(os.environ)
    env.update(
        {
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "",
        }
    )
    return env


def git(*args: str, cwd: Path | str | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        env=_env(),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def is_repository(path: Path | str) -> bool:
    try:
        git("rev-parse", "--git-dir", cwd=path)
        return True
    except (GitError, FileNotFoundError, NotADirectoryError):
        return False


def has_commits(path: Path | str) -> bool:
    try:
        git("rev-parse", "--verify", "HEAD", cwd=path)
        return True
    except GitError:
        return False


def root_commits(path: Path | str) -> list[str]:
    """Every commit with no parent, newest first as git reports them."""
    if not has_commits(path):
        return []
    out = git("rev-list", "--max-parents=0", "HEAD", cwd=path)
    return [line.strip() for line in out.split("\n") if line.strip()]


def commit_date(path: Path | str, sha: str) -> str:
    """Committer date of one commit, as an ISO-8601 instant."""
    return git("show", "-s", "--format=%cI", sha, cwd=path).strip()


def tracked_files(path: Path | str) -> list[str]:
    """Every tracked file, as POSIX paths. Works with or without commits."""
    out = git("ls-files", "-z", cwd=path)
    return [p for p in out.split("\0") if p]


@dataclass(frozen=True)
class Commit:
    sha: str
    author_name: str
    author_email: str
    date: str  # ISO-8601


def log(path: Path | str) -> list[Commit]:
    if not has_commits(path):
        return []
    out = git("log", "--format=%H%x1f%an%x1f%ae%x1f%aI", cwd=path)
    commits = []
    # split("\n") e não splitlines(): splitlines() também quebra em \x1c-\x1e,
    # o que engoliria qualquer separador de registro que usássemos.
    for line in out.split("\n"):
        if not line.strip():
            continue
        sha, name, email, date = line.split("\x1f")
        commits.append(Commit(sha=sha, author_name=name, author_email=email, date=date))
    return commits


def numstat(path: Path | str) -> list[tuple[str, int, int]]:
    """Per-commit line counts as (author_email, added, deleted).

    Binary files report `-` for both counts; they contribute zero rather than
    crashing the scan.
    """
    if not has_commits(path):
        return []
    out = git("log", "--format=%x1e%ae", "--numstat", cwd=path)
    rows: list[tuple[str, int, int]] = []
    email = None
    for line in out.split("\n"):
        if line.startswith("\x1e"):
            email = line[1:].strip()
            continue
        if not line.strip() or email is None:
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added = 0 if parts[0] == "-" else int(parts[0])
        deleted = 0 if parts[1] == "-" else int(parts[1])
        rows.append((email, added, deleted))
    return rows


def clone(url: str, target: Path | str) -> Path:
    """Clone with complete history and no working tree.

    Complete because root-commit identity and per-author counts depend on it
    (FR-024); no working tree because nothing here ever reads the checkout, and
    a bare-ish clone of 500 repositories is the difference between fitting in a
    temp directory and not.
    """
    target = Path(target)
    git("clone", "--quiet", "--no-checkout", url, str(target))
    return target
