"""Fixture repositories for the test suite.

Real repositories cannot be committed as nested `.git` directories, so they live
as `git bundle` files under `tests/fixtures/` and are unbundled into a temporary
directory at setUp. Rebuild them with `tests/fixtures/build.sh`.

Two fixtures are built here instead of unbundled: a bundle requires at least one
ref, so a repository with no commits cannot be one.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"

# Raiz compartilhada por multi-contributor, divergent-* e barely-touched-fork.
# Fixa porque build.sh usa datas e conteúdo fixos.
SHARED_ROOT = "f9c59c8534b791061add8c3983517842a25ff85f"
REWRITTEN_ROOT = "d9967dc229f79b72e246cbf6b0c5168cf5731480"


def _git(*args, cwd=None):
    # Isola de qualquer configuração da máquina, para o teste ser o mesmo em toda parte.
    env = {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": "/nonexistent",
        "PATH": "/usr/bin:/bin",
    }
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


class FixtureCase(unittest.TestCase):
    """Base case giving each test a private temporary directory."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="dendro-fixture-"))
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    @property
    def tmp(self) -> Path:
        return self._tmp

    def unbundle(self, name: str, as_name: str | None = None) -> Path:
        """Clone one committed bundle into the temp directory and return its path."""
        bundle = FIXTURE_DIR / f"{name}.bundle"
        if not bundle.exists():
            raise FileNotFoundError(
                f"{bundle} is missing — run tests/fixtures/build.sh"
            )
        target = self._tmp / (as_name or name)
        _git("clone", "--quiet", str(bundle), str(target))
        return target

    def empty_repository(self, name: str = "no-commits") -> Path:
        """A repository with a tracked file but no commit yet."""
        target = self._tmp / name
        target.mkdir(parents=True)
        _git("init", "--quiet", "-b", "main", cwd=target)
        (target / "main.py").write_text('print("nothing committed yet")\n')
        _git("add", "-A", cwd=target)
        return target

    def bare_repository(self, name: str = "no-commits-no-files") -> Path:
        """A repository with neither commits nor tracked files: unidentifiable."""
        target = self._tmp / name
        target.mkdir(parents=True)
        _git("init", "--quiet", "-b", "main", cwd=target)
        return target
