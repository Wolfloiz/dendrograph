"""O template do arquivo tem que funcionar sem edição nenhuma.

SC-001 é "zero setup é o caminho da demonstração". Um template que só parseia
depois que a pessoa descomenta a linha certa falha exatamente aí — e falha na
primeira execução, que é a única em que ninguém sabe ainda se a ferramenta é
confiável.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from core import build, config, store

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "archive"


class TheTemplateWorksUntouched(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dendro-template-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        shutil.copytree(TEMPLATE, self.tmp / "archive")
        self.archive = self.tmp / "archive"

    def test_the_shipped_config_parses(self):
        # Um cabeçalho `[[sources]]` com todas as chaves comentadas vira uma
        # tabela vazia e falha na chave obrigatória. O template já saiu assim.
        loaded = config.load(self.archive)
        self.assertEqual(loaded.publish_mode, "public")

    def test_it_declares_nothing_by_itself(self):
        loaded = config.load(self.archive)
        self.assertEqual(loaded.sources, ())
        self.assertEqual(loaded.collections, ())
        self.assertEqual(loaded.successions, ())
        self.assertEqual(loaded.epoch_markers, ())
        self.assertEqual(loaded.declared_ids(), set())

    def test_a_build_on_the_empty_template_produces_a_site(self):
        build.build(self.archive, config=config.load(self.archive))
        for name in ("graph.json", "graph.js", "llms.txt", "index.html"):
            self.assertTrue((self.archive / "site" / name).exists(), name)

    def test_every_commented_example_would_parse_if_uncommented(self):
        """Cada bloco de exemplo, descomentado sozinho, tem que ser válido.

        Um exemplo que não funciona quando copiado é pior que exemplo nenhum:
        a pessoa conclui que a ferramenta está quebrada, não o comentário.
        """
        text = (self.archive / "dendrograph.toml").read_text()
        blocks, current = [], None
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# [") or stripped.startswith("["):
                if current:
                    blocks.append(current)
                current = [stripped.lstrip("# ")]
                continue
            if current is None:
                continue
            if not stripped:
                blocks.append(current)
                current = None
                continue
            # Comentário em prosa entre o cabeçalho e as chaves é ignorado;
            # só linhas `chave = valor` entram no bloco.
            body = stripped[2:] if stripped.startswith("# ") else stripped
            if "=" in body and not body.startswith("#"):
                current.append(body)
        if current:
            blocks.append(current)
        blocks = [b for b in blocks if len(b) > 1]

        self.assertGreater(len(blocks), 4, "no example blocks found to check")
        for block in blocks:
            body = "\n".join(block)
            probe = self.tmp / "probe"
            probe.mkdir(exist_ok=True)
            (probe / "dendrograph.toml").write_text(body + "\n")
            try:
                config.load(probe)
            except config.ConfigError as exc:
                self.fail(f"example block does not parse:\n{body}\n  -> {exc}")


class TheTemplateHoldsNoAuthorData(unittest.TestCase):
    """ADR-0010: a ferramenta não carrega dado de Author, nem de exemplo."""

    def test_the_store_ships_empty(self):
        artifacts = list((TEMPLATE / "store" / "artifacts").glob("*.json"))
        self.assertEqual(artifacts, [])

    def test_no_real_account_is_named(self):
        text = (TEMPLATE / "dendrograph.toml").read_text()
        for placeholder in ("your-account", "you@example.com"):
            self.assertIn(placeholder, text)


if __name__ == "__main__":
    unittest.main()
