"""Clone remote Artifacts, then throw the clone away.

Complete history because root-commit identity and per-author counts depend on
it; no working tree because nothing reads the checkout; discarded at the end of
the run because the store is the source of truth and the source is an input
(FR-024, ADR-0002).
"""

from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from collectors.git import plumbing


@contextmanager
def working_directory(prefix: str = "dendro-scan-"):
    """A temporary directory removed when the run ends, however it ends."""
    path = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def clone_into(url: str, workdir: Path, name: str) -> Path:
    """Clone one repository with its whole history and no working tree."""
    target = workdir / name
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    return plumbing.clone(url, target)
