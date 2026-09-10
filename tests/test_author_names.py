"""Como uma pessoa assina, que não é como ela é identificada.

ADR-0012 tirou o endereço da saída publicada e deixou a parte local no lugar
dele — `octocat` em vez do endereço inteiro. A parte local é o que sobra
quando não se tem coisa melhor. O nome do commit é a coisa melhor: é o que a
pessoa escolheu, é o que o GitHub já mostra em cada commit dela, e `%an` sempre
esteve ali no `git log` — o coletor é que o descartava.
"""

import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from collectors.git import authorship  # noqa: E402
from core.graph import author_label  # noqa: E402
from core.store import Authorship, _merge_authorship  # noqa: E402
from support.fixtures import FixtureCase  # noqa: E402


class TheLabelPrefersTheName(unittest.TestCase):
    def test_the_name_wins_over_the_local_part(self):
        self.assertEqual(
            author_label("1024+octocat@users.noreply.github.com",
                         "Mona Lisa", published=True),
            "Mona Lisa",
        )

    def test_without_a_name_the_local_part_still_answers(self):
        # Registros guardados antes de o coletor ler `%an` não têm nome, e o
        # store acumula em vez de reconstruir (ADR-0002).
        self.assertEqual(author_label("nadia-r@example.com", None, published=True),
                         "nadia-r")

    def test_a_name_that_is_itself_an_address_is_refused(self):
        # `user.name = meu@endereço` é comum, e aí o nome não é melhor que o
        # e-mail: publicá-lo desfaz a ADR inteira.
        self.assertEqual(
            author_label("jane@example.com", "jane@example.com", published=True),
            "jane",
        )

    def test_the_full_build_still_shows_the_address(self):
        self.assertEqual(
            author_label("jane@example.com", "Jane Doe", published=False),
            "jane@example.com",
        )


class TheCollectorRecordsHowEachAddressSigns(FixtureCase):
    def test_the_name_travels_with_the_counts(self):
        repository = self.unbundle("multi-contributor")
        by_author = {a.author: a for a in authorship.counts(repository)}
        self.assertEqual(by_author["alice@example.com"].name, "Alice")
        self.assertEqual(by_author["bob@example.com"].name, "Bob")

    def test_the_most_used_spelling_wins(self):
        repository = self._repository_signed_as(
            [("Ana", "ana@example.com"),
             ("ana", "ana@example.com"),
             ("Ana", "ana@example.com")]
        )
        [entry] = authorship.counts(repository)
        self.assertEqual(entry.name, "Ana")

    def test_two_spellings_of_one_address_are_one_line(self):
        # Antes disto cada caixa virava uma linha, e cada metade ficava com
        # metade dos commits.
        repository = self._repository_signed_as(
            [("Ana", "Ana@Example.com"), ("Ana", "ana@example.com")]
        )
        entries = authorship.counts(repository)
        self.assertEqual(len(entries), 1, entries)
        self.assertEqual(entries[0].author, "ana@example.com")
        self.assertEqual(entries[0].commits, 2)

    def _repository_signed_as(self, signatures):
        target = self.tmp / f"signed-{len(list(self.tmp.iterdir()))}"
        target.mkdir()
        subprocess.run(["git", "init", "--quiet", "-b", "main"], cwd=target, check=True)
        for number, (name, email) in enumerate(signatures):
            (target / "main.py").write_text(f"print({number})\n")
            subprocess.run(["git", "add", "-A"], cwd=target, check=True)
            subprocess.run(
                ["git", "-c", f"user.name={name}", "-c", f"user.email={email}",
                 "commit", "--quiet", "-m", f"commit {number}"],
                cwd=target, check=True,
            )
        return target


class OnePersonSignsDifferentlyInDifferentRepositories(unittest.TestCase):
    """`Luiz` num repositório, `loiz` noutro, um endereço só.

    O primeiro build depois de o nome virar rótulo caiu exatamente aqui:
    `CollidingLabels` entre 'Luiz' e 'loiz' no mesmo id. O guard estava certo —
    dois rótulos num id é o que ele existe para recusar —, e o erro era escolher
    o nome por Artifact quando o id vale para o arquivo inteiro.
    """

    def _artifact(self, artifact_id, name, commits):
        from core.store import Artifact

        return Artifact(
            id=artifact_id,
            identity={"method": "root_commit", "value": artifact_id},
            activity={"first": "2020-01-01", "last": "2021-01-01"},
            authorship=[
                Authorship(author="l@example.com", commits=commits, name=name)
            ],
        )

    def test_the_two_spellings_land_on_one_node(self):
        from core.graph import build

        payload = build(
            [self._artifact("root-a", "Luiz", 40),
             self._artifact("root-b", "loiz", 2)],
            generated_at="2026-08-27T00:00:00Z",
        )
        authors = [n for n in payload["nodes"] if n["type"] == "Author"]
        self.assertEqual(len(authors), 1, authors)

    def test_the_spelling_with_the_most_commits_behind_it_wins(self):
        from core.graph import build

        payload = build(
            [self._artifact("root-a", "Luiz", 40),
             self._artifact("root-b", "loiz", 2)],
            generated_at="2026-08-27T00:00:00Z",
        )
        [author] = [n for n in payload["nodes"] if n["type"] == "Author"]
        self.assertEqual(author["label"], "Luiz")


class AScanWithoutANameDoesNotEraseOne(unittest.TestCase):
    def test_the_prior_name_survives_a_nameless_observation(self):
        prior = [Authorship(author="a@example.com", commits=3, name="Ana")]
        observed = [Authorship(author="a@example.com", commits=5)]
        [merged] = _merge_authorship(prior, observed)
        self.assertEqual(merged.name, "Ana")
        self.assertEqual(merged.commits, 5)

    def test_a_newer_name_replaces_the_older_one(self):
        prior = [Authorship(author="a@example.com", commits=3, name="Ana")]
        observed = [Authorship(author="a@example.com", commits=5, name="Ana Silva")]
        [merged] = _merge_authorship(prior, observed)
        self.assertEqual(merged.name, "Ana Silva")


class TheStoreCarriesTheNameBackAndForth(unittest.TestCase):
    def test_a_record_written_before_the_name_existed_still_loads(self):
        raw = {"author": "a@example.com", "commits": 2, "lines_added": 0,
               "lines_deleted": 0, "first": "2020-01-01", "last": "2020-01-02"}
        self.assertIsNone(Authorship(**raw).name)

    def test_the_name_round_trips(self):
        from core.store import _authorship_to_dict

        entry = Authorship(author="a@example.com", commits=1, name="Ana")
        self.assertEqual(Authorship(**_authorship_to_dict(entry)).name, "Ana")


if __name__ == "__main__":
    unittest.main()
