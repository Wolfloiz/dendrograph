"""Deployment of the built site to `[publish].target_repository` (ADR-0010).

The archive repository holds the store and can stay private. When a second,
public repository is configured, the filtered contents of `site/` are pushed
there and Pages serves that instead — how an Author on a free plan keeps a
private archive and a public site. The target holds no store, ever: only what
already passed through the privacy filter travels.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class PublishError(Exception):
    """Deployment could not complete. Exits `1`."""


def deploy(site_dir: Path | str, target_repository: str) -> str:
    """Replace the target repository's content with `site/` and push."""
    source = Path(site_dir)
    if not (source / "graph.json").exists():
        raise PublishError(
            f"{source} has no graph.json — run `dendro build` before publishing."
        )
    url = f"https://github.com/{target_repository}.git"
    with tempfile.TemporaryDirectory(prefix="dendro-publish-") as tmp:
        destination = Path(tmp) / "target"
        branch = _checkout(destination, url)
        _replace_contents(destination, source)
        staged = _git(destination, "status", "--porcelain")
        if not staged.strip():
            return f"{target_repository} already matches {source}; nothing to push."
        _git(destination, "add", "-A")
        _git(destination, "-c", "user.name=dendrograph", "-c",
             "user.email=dendrograph@users.noreply.github.com",
             "commit", "-m", "Publish archive site")
        _git(destination, "push", "origin", f"HEAD:{branch}")
    return f"Deployed {source} to {target_repository} ({branch})."


def _checkout(destination: Path, url: str) -> str:
    """Clone the target; a brand-new empty repository is initialised instead."""
    completed = subprocess.run(
        ["git", "clone", "--depth", "1", url, str(destination)],
        capture_output=True, text=True,
    )
    if completed.returncode == 0:
        head = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=destination, capture_output=True, text=True,
        )
        return head.stdout.strip() or "main"
    # Um repositório recém-criado não tem commits para clonar: começa um.
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main", str(destination)], check=True)
    subprocess.run(["git", "remote", "add", "origin", url], cwd=destination, check=True)
    return "main"


def _replace_contents(destination: Path, source: Path) -> None:
    """The target mirrors `site/` exactly — stale files do not survive."""
    for entry in destination.iterdir():
        if entry.name == ".git":
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    for entry in source.iterdir():
        if entry.is_dir():
            shutil.copytree(entry, destination / entry.name)
        else:
            shutil.copy2(entry, destination / entry.name)


def _git(cwd: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=cwd, capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise PublishError(
            f"git {' '.join(arguments)} failed: "
            f"{(completed.stderr or completed.stdout).strip()}"
        )
    return completed.stdout
