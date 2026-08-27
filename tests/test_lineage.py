"""`DERIVES_FROM` only from substantial shared authored material (FR-012).

Dependencies, lockfiles, generated output and files under 512 bytes never
enter the lineage set, so no amount of sharing them produces a candidate. And
one or two identical files never do either: the threshold exists because a
false edge is a false claim about the Author's work, not a styling choice.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import identity  # noqa: E402
from core.analysis import lineage  # noqa: E402
from core.store import Artifact  # noqa: E402
from support.fixtures import FixtureCase  # noqa: E402


def artifact(artifact_id, files, first="2020-01-01"):
    hashes = {
        f"{digest:064x}": f"file{digest}.py" for digest in files
    }
    return Artifact(
        id=artifact_id,
        identity={"method": "root_commit", "value": artifact_id},
        content_hashes={
            "algorithm": "sha256",
            "authored_files": [
                {"path": path, "size": 1024, "hash": digest}
                for digest, path in hashes.items()
            ],
        },
        activity={"first": first, "last": first},
    )


class Threshold(FixtureCase):
    SHARED = lineage.MINIMUM_SHARED_FILES

    def test_below_the_threshold_produces_nothing(self):
        older = artifact("root-older", range(self.SHARED - 1), first="2020-01-01")
        newer = artifact("root-newer", range(self.SHARED - 1), first="2021-01-01")
        self.assertEqual(lineage.candidates([older, newer]), [])

    def test_at_the_threshold_a_candidate_appears(self):
        older = artifact("root-older", range(self.SHARED), first="2020-01-01")
        newer = artifact("root-newer", range(self.SHARED), first="2021-01-01")
        [candidate] = lineage.candidates([older, newer])
        self.assertEqual(candidate["from"], "root-older")
        self.assertEqual(candidate["to"], "root-newer")
        self.assertEqual(candidate["confidence"], "medium")

    def test_double_the_threshold_reads_as_high_confidence(self):
        many = lineage.HIGH_CONFIDENCE_AT
        older = artifact("root-older", range(many), first="2020-01-01")
        newer = artifact("root-newer", range(many), first="2021-01-01")
        [candidate] = lineage.candidates([older, newer])
        self.assertEqual(candidate["confidence"], "high")

    def test_every_candidate_carries_the_paths_that_prove_it(self):
        # Uma aresta sem evidência seria um palpite, e o grafo não aceita
        # palpite (Principle I).
        older = artifact("root-older", range(self.SHARED), first="2020-01-01")
        newer = artifact("root-newer", range(self.SHARED), first="2021-01-01")
        [candidate] = lineage.candidates([older, newer])
        self.assertEqual(len(candidate["evidence"]), self.SHARED)
        for pointer in candidate["evidence"]:
            self.assertEqual(pointer["kind"], "path")
            self.assertTrue(pointer["detail"].startswith("file"))

    def test_same_content_under_a_different_path_still_counts(self):
        # A evidência é o conteúdo, não o nome: um arquivo renomeado continua
        # sendo o mesmo material.
        older = Artifact(
            id="root-older",
            identity={"method": "root_commit", "value": "root-older"},
            content_hashes={
                "algorithm": "sha256",
                "authored_files": [
                    {"path": f"old/{n}.py", "size": 1024, "hash": f"{n:064x}"}
                    for n in range(self.SHARED)
                ],
            },
            activity={"first": "2020-01-01", "last": "2020-01-01"},
        )
        newer = Artifact(
            id="root-newer",
            identity={"method": "root_commit", "value": "root-newer"},
            content_hashes={
                "algorithm": "sha256",
                "authored_files": [
                    {"path": f"new/{n}.py", "size": 1024, "hash": f"{n:064x}"}
                    for n in range(self.SHARED)
                ],
            },
            activity={"first": "2021-01-01", "last": "2021-01-01"},
        )
        [candidate] = lineage.candidates([older, newer])
        # O ponteiro registrado é o caminho do Artifact mais antigo.
        self.assertTrue(
            all(p["detail"].startswith("old/") for p in candidate["evidence"])
        )


class Orientation(FixtureCase):
    def test_the_edge_runs_older_to_newer_never_back(self):
        older = artifact("root-older", range(4), first="2019-01-01")
        newer = artifact("root-newer", range(4), first="2022-01-01")
        # A ordem da entrada não importa: a orientação vem das datas.
        [candidate] = lineage.candidates([newer, older])
        self.assertEqual((candidate["from"], candidate["to"]),
                         ("root-older", "root-newer"))

    def test_equal_dates_produce_no_edge_at_all(self):
        # Isto já foi o contrário: o desempate caía no id, e a seta apontava
        # para onde um SHA mandou. Uma direção decidida por hash é uma
        # afirmação que ninguém observou (SC-008).
        first = artifact("root-aaa", range(4), first="2021-01-01")
        second = artifact("root-zzz", range(4), first="2021-01-01")
        self.assertEqual(lineage.candidates([second, first]), [])

    def test_a_gap_shorter_than_the_interval_produces_no_edge(self):
        # `tinyos` e `tinyturing`, um dia de diferença: a essa distância a
        # primeira atividade é fuso horário, não história.
        older = artifact("root-older", range(4), first="2024-05-01")
        newer = artifact("root-newer", range(4), first="2024-05-02")
        self.assertEqual(lineage.candidates([older, newer]), [])

    def test_the_interval_itself_is_enough(self):
        older = artifact("root-older", range(4), first="2024-05-01")
        newer = artifact(
            "root-newer", range(4),
            first=f"2024-05-{1 + lineage.MINIMUM_ORIENTING_INTERVAL_DAYS:02d}",
        )
        [candidate] = lineage.candidates([older, newer])
        self.assertEqual((candidate["from"], candidate["to"]),
                         ("root-older", "root-newer"))

    def test_an_artifact_with_no_observed_date_is_never_oriented(self):
        # Sem data não há "mais antigo", e o par ia para o fim da ordenação e
        # ganhava uma seta assim mesmo.
        dated = artifact("root-dated", range(4), first="2020-01-01")
        undated = artifact("root-undated", range(4))
        undated.activity = {}
        self.assertEqual(lineage.candidates([dated, undated]), [])

    def test_an_artifact_without_stored_hashes_never_produces_an_edge(self):
        plain = artifact("root-plain", range(8), first="2020-01-01")
        empty = artifact("root-empty", range(8), first="2021-01-01")
        empty.content_hashes = {}
        self.assertEqual(lineage.candidates([plain, empty]), [])


class WhatNeverCounts(FixtureCase):
    """Dependencies, lockfiles, generated output and trivial files (FR-012)."""

    def _scanned(self, repo):
        return {
            "algorithm": "sha256",
            "authored_files": [
                {"path": path, "size": size, "hash": digest}
                for path, size, digest in identity.authored_files(repo)
            ],
        }

    def test_shared_trivial_and_vendored_files_produce_no_candidate(self):
        # Dois projetos distintos que só compartilham lockfile, arquivo pequeno
        # e diretório de dependência: nada disso é prova de descendência.
        junk = {
            "package-lock.json": "l" * 9000,
            "node_modules/left-pad/index.js": "p" * 5000,
            "vendor/thing.go": "v" * 5000,
            "dist/bundle.min.js": "m" * 9000,
            "main.py": "s = 1\n",
        }
        first = self.empty_repository("first")
        for path, content in junk.items():
            target = first / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        second = self.empty_repository("second")
        for path, content in junk.items():
            target = second / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        # Datas bem separadas de propósito: sem elas o par cairia pelo
        # intervalo de orientação, e o teste passaria sem testar o filtro.
        a = Artifact(id="root-a", identity={"method": "root_commit", "value": "a"},
                     content_hashes=self._scanned(first),
                     activity={"first": "2020-01-01", "last": "2020-01-01"})
        b = Artifact(id="root-b", identity={"method": "root_commit", "value": "b"},
                     content_hashes=self._scanned(second),
                     activity={"first": "2022-01-01", "last": "2022-01-01"})
        self.assertEqual(lineage.candidates([a, b]), [])


if __name__ == "__main__":
    unittest.main()
