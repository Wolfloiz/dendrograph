"""Nenhum comando escreve dado privado do Author no repositório da ferramenta.

FR-023, ADR-0010: a ferramenta e o arquivo do Author são repositórios
separados. O teste roda os comandos enraizados num diretório temporário e
exige que a árvore de trabalho da ferramenta — incluindo o que viraria
histórico — não mude um byte. E `examples/` só pode conter Artifacts públicos,
porque é o que viaja com o código.
"""

import json
import subprocess
from pathlib import Path

from core import build, store
from tests.support import archives
from tests.support.fixtures import FixtureCase

TOOL_REPO = Path(__file__).resolve().parent.parent


def git_status() -> str:
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=TOOL_REPO, capture_output=True, text=True, check=True,
    )
    return completed.stdout


class NoCommandDirtiesTheToolRepository(FixtureCase):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "archive"
        self.root.mkdir()
        archives.write(self.root, archives.private(), archives.public())
        self.before = git_status()

    def test_a_build_rooted_elsewhere_leaves_the_tool_repo_untouched(self):
        build.build(self.root)
        build.build(self.root, mode="redacted")
        build.build(self.root, mode="full")
        self.assertEqual(git_status(), self.before)

    def test_the_store_never_lands_inside_the_tool_repo(self):
        # O root é onde store/ e site/ nascem; nenhum caminho dentro da
        # ferramenta pode ser criado por um build apontado para fora dela.
        for path in (
            TOOL_REPO / "store",
            TOOL_REPO / "site",
            TOOL_REPO / ".dendro-local",
        ):
            self.assertFalse(path.exists(), f"{path} não deveria existir")

    def test_examples_hold_public_artifacts_only(self):
        examples = TOOL_REPO / "examples"
        if not examples.exists():
            return
        for path in sorted(examples.rglob("*.json")):
            with self.subTest(file=path):
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and "visibility" in raw:
                    self.assertNotEqual(raw["visibility"], "private")
