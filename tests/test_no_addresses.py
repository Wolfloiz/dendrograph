"""Um endereço publicado é um endereço colhido.

O id de Author já era um digest para manter o endereço fora dele. O rótulo não
era: numa varredura real de 97 Artifacts, o site público saía com o e-mail
legível de 1.165 contribuintes — gente que nunca ouviu falar desta ferramenta,
cujo endereço o próprio GitHub esconde atrás de `noreply`. ADR-0012.
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from collectors.git import scan  # noqa: E402
from core import build as build_module  # noqa: E402
from core import store  # noqa: E402
from core.graph import author_label  # noqa: E402
from support.fixtures import FixtureCase  # noqa: E402

ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class TheLabelIsNotTheIdentity(unittest.TestCase):
    def test_a_published_label_drops_the_domain(self):
        self.assertEqual(
            author_label("nadia-r@example.com", published=True), "nadia-r"
        )

    def test_the_github_numeric_prefix_goes_with_it(self):
        # O que sobra é o nome de usuário, que já é público.
        self.assertEqual(
            author_label("1024+octocat@users.noreply.github.com", published=True),
            "octocat",
        )

    def test_the_full_build_keeps_the_address(self):
        # `full` nunca sai da máquina do Author, e lá distinguir dois `john`
        # é problema de quem está olhando o próprio arquivo.
        self.assertEqual(
            author_label("john@work.example", published=False), "john@work.example"
        )

    def test_an_address_with_no_local_part_still_yields_a_label(self):
        label = author_label("@example.com", published=True)
        self.assertNotIn("@", label)
        self.assertTrue(label)

    def test_two_addresses_with_one_local_part_are_not_merged(self):
        # Rótulos iguais são aceitáveis: são duas pessoas chamadas `john`. Ids
        # iguais não seriam, e é o id que responde por identidade.
        from core.graph import node_id

        self.assertEqual(
            author_label("john@a.example", published=True),
            author_label("john@b.example", published=True),
        )
        self.assertNotEqual(
            node_id("Author", "john@a.example"), node_id("Author", "john@b.example")
        )


class NoPublishedFileCarriesAnAddress(FixtureCase):
    """O grafo em memória passar não basta: o sqlite e o llms.txt são o mesmo
    payload noutra forma, e é o disco que é lido."""

    def setUp(self):
        super().setUp()
        repository = self.unbundle("multi-contributor")
        self.archive = self.tmp / "archive"
        store.save(
            scan.observe(repository, kind="local", locator=str(repository),
                         visibility="public", seen="2026-08-25"),
            self.archive,
        )

    def written_files(self, mode):
        build_module.build(
            self.archive, mode=mode, generated_at="2026-08-25T00:00:00Z"
        )
        directory = build_module.output_dir(self.archive, mode)
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                yield path

    def test_no_public_or_redacted_output_contains_an_address(self):
        checked = 0
        for mode in ("public", "redacted"):
            for path in self.written_files(mode):
                text = path.read_bytes().decode("utf-8", errors="ignore")
                found = ADDRESS.search(text)
                self.assertIsNone(
                    found,
                    f"{mode}/{path.name} publishes "
                    f"{found.group(0) if found else ''}",
                )
                checked += 1
        self.assertGreater(checked, 6, "the sweep did not reach the built site")

    def test_the_fixture_does_have_addresses_to_leak(self):
        # Sem isto a varredura acima passa por não ter o que encontrar.
        text = "".join(
            path.read_bytes().decode("utf-8", errors="ignore")
            for path in self.written_files("full")
            if path.name == "graph.json"
        )
        self.assertRegex(text, ADDRESS)


if __name__ == "__main__":
    unittest.main()
