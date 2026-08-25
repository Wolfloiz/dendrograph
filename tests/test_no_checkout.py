"""Um clone sem working tree tem que render a mesma análise que um com.

Toda varredura do GitHub clona com `--no-checkout`. Enquanto a análise lia o
disco, ela via zero arquivos e devolvia zero Tools, zero Techniques e zero
Dependencies — em silêncio, com saída bem-formada. Os fixtures têm working
tree, então nenhum teste percebia.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from collectors.git import plumbing
from core import identity
from core.analysis import dependencies, tools


def build_repository(path: Path) -> None:
    def run(*args):
        subprocess.run(
            ["git", *args],
            cwd=path,
            check=True,
            capture_output=True,
            env={
                **plumbing._env(),
                "GIT_AUTHOR_NAME": "A",
                "GIT_AUTHOR_EMAIL": "a@example.com",
                "GIT_COMMITTER_NAME": "A",
                "GIT_COMMITTER_EMAIL": "a@example.com",
                "GIT_AUTHOR_DATE": "2021-01-01T00:00:00Z",
                "GIT_COMMITTER_DATE": "2021-01-01T00:00:00Z",
            },
        )

    path.mkdir(parents=True, exist_ok=True)
    run("init", "--quiet", "-b", "main")
    (path / "pyproject.toml").write_text("[project]\nname = 'thing'\n")
    (path / "requirements.txt").write_text("requests==2.31.0\nflask\n")
    (path / "engine.py").write_text("# engine\n" + "x = 1\n" * 400)
    (path / "helper.py").write_text("# helper\n" + "y = 2\n" * 400)
    run("add", "-A")
    run("commit", "--quiet", "-m", "first")


class AnalysisSurvivesWithoutAWorkingTree(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.origin = root / "origin"
        build_repository(self.origin)
        self.bare = root / "clone"
        plumbing.clone(str(self.origin), self.bare)
        self.addCleanup(self.tmp.cleanup)

    def test_the_clone_really_has_no_working_tree(self):
        # Se isto falhar, o teste parou de exercitar o que dizia exercitar.
        self.assertFalse((self.bare / "engine.py").exists())

    def test_the_files_are_still_visible(self):
        self.assertEqual(
            sorted(plumbing.tracked_files(self.bare)),
            ["engine.py", "helper.py", "pyproject.toml", "requirements.txt"],
        )

    def test_tools_are_still_detected(self):
        paths = plumbing.tracked_files(self.bare)
        self.assertTrue(tools.detect(paths), "no Tool detected without a checkout")

    def test_dependencies_are_still_extracted(self):
        paths = plumbing.tracked_files(self.bare)
        names = {d["name"] for d in dependencies.detect(self.bare, paths)}
        self.assertIn("requests", names)
        self.assertIn("flask", names)

    def test_the_content_hash_matches_the_checked_out_original(self):
        self.assertIsNotNone(identity.content_hash(self.bare))
        self.assertEqual(
            identity.content_hash(self.bare), identity.content_hash(self.origin)
        )

    def test_the_lineage_hash_matches_the_checked_out_original(self):
        self.assertIsNotNone(identity.lineage_hash(self.bare))
        self.assertEqual(
            identity.lineage_hash(self.bare), identity.lineage_hash(self.origin)
        )

    def test_the_same_identity_is_resolved_either_way(self):
        self.assertEqual(
            identity.resolve(self.bare).value, identity.resolve(self.origin).value
        )


if __name__ == "__main__":
    unittest.main()
