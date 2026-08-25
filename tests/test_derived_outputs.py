"""`graph.sqlite` e `llms.txt` dizem o mesmo que `graph.json`.

Três formas do mesmo payload: JSON para programas, sqlite para quem prefere
consultar, prosa para um agente que não vai parsear nada (FR-017). Se as três
divergirem, duas delas estão mentindo e ninguém sabe qual.
"""

import json
import sqlite3
import unittest
from collections import Counter
from pathlib import Path

from core import build as build_module
from core import graph, llms
from core import sqlite as sqlite_module
from core.config import Config
from core.store import Artifact, Authorship, Source


def artifact(artifact_id, **kwargs):
    kwargs.setdefault("identity", {"method": "root-commit", "value": artifact_id})
    kwargs.setdefault("name", artifact_id)
    return Artifact(id=artifact_id, **kwargs)


def sample():
    return [
        artifact(
            "root-aaa",
            name="alpha",
            description="A thing that does alpha work.",
            activity={"first": "2020-01-01", "last": "2024-06-01"},
            authorship=[Authorship("me@example.com", 40, 400, 10, "2020-01-01", "2024-06-01")],
            tools=[{"name": "Python"}, {"name": "C++"}],
            techniques=[{"name": "Automated Testing", "confidence": "high", "evidence": []}],
            dependencies=[{"name": "flask", "ecosystem": "pypi", "version": None, "evidence": []}],
            sources=[Source("github", "https://github.com/me/alpha", "2020-01-01", "2026-01-01")],
        ),
        artifact(
            "root-bbb",
            name="beta",
            activity={"first": "2022-03-01", "last": "2023-09-01"},
            authorship=[Authorship("me@example.com", 5, 50, 2, "2022-03-01", "2023-09-01")],
            tools=[{"name": "Python"}],
        ),
    ]


class TheDatabaseMirrorsTheJson(unittest.TestCase):
    def setUp(self):
        self.payload = graph.build(sample(), config=Config(emails=("me@example.com",)))
        self.tmp = Path(__file__).resolve().parent / "_tmp_sqlite"
        self.tmp.mkdir(exist_ok=True)
        self.path = sqlite_module.write(self.payload, self.tmp)
        self.connection = sqlite3.connect(self.path)
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.connection.close()
        for child in self.tmp.iterdir():
            child.unlink()
        self.tmp.rmdir()

    def test_every_node_type_has_a_table_with_the_same_count(self):
        counts = Counter(n["type"] for n in self.payload["nodes"])
        for node_type, expected in counts.items():
            got = self.connection.execute(
                f"SELECT count(*) FROM {node_type.lower()}"
            ).fetchone()[0]
            self.assertEqual(got, expected, node_type)

    def test_every_edge_is_present(self):
        got = self.connection.execute("SELECT count(*) FROM edges").fetchone()[0]
        self.assertEqual(got, len(self.payload["edges"]))

    def test_an_edge_resolves_to_nodes_that_exist(self):
        rows = self.connection.execute('SELECT "from", "to" FROM edges').fetchall()
        ids = {n["id"] for n in self.payload["nodes"]}
        for source, target in rows:
            self.assertIn(source, ids)
            self.assertIn(target, ids)

    def test_a_typed_column_carries_the_value_the_json_carries(self):
        row = self.connection.execute(
            "SELECT label, first, last, authorship_share FROM artifact WHERE id = ?",
            ("root-aaa",),
        ).fetchone()
        node = next(n for n in self.payload["nodes"] if n["id"] == "root-aaa")
        self.assertEqual(row[0], node["label"])
        self.assertEqual(row[1], node["first"])
        self.assertEqual(row[3], node["authorship"]["share"])

    def test_no_field_is_lost_even_where_no_column_names_it(self):
        raw = self.connection.execute(
            "SELECT attributes FROM artifact WHERE id = ?", ("root-aaa",)
        ).fetchone()[0]
        node = next(n for n in self.payload["nodes"] if n["id"] == "root-aaa")
        self.assertEqual(json.loads(raw), node)

    def test_the_build_metadata_travels_with_it(self):
        meta = dict(self.connection.execute("SELECT key, value FROM meta"))
        self.assertEqual(meta["build_mode"], self.payload["build_mode"])
        self.assertEqual(meta["generator"], self.payload["generator"])

    def test_rebuilding_replaces_rather_than_appends(self):
        sqlite_module.write(self.payload, self.tmp)
        again = sqlite3.connect(self.path)
        try:
            count = again.execute("SELECT count(*) FROM artifact").fetchone()[0]
        finally:
            again.close()
        self.assertEqual(count, 2)


class SearchShipsUnusedSoNobodyRebuildsLater(unittest.TestCase):
    """A busca é da v0.2. A tabela é da v0.1, senão todo Author reconstrói."""

    def setUp(self):
        self.payload = graph.build(sample())
        self.tmp = Path(__file__).resolve().parent / "_tmp_fts"
        self.tmp.mkdir(exist_ok=True)
        self.connection = sqlite3.connect(sqlite_module.write(self.payload, self.tmp))
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.connection.close()
        for child in self.tmp.iterdir():
            child.unlink()
        self.tmp.rmdir()

    def test_the_table_exists(self):
        self.assertTrue(sqlite_module.has_search(self.connection))

    def test_every_artifact_is_indexed(self):
        count = self.connection.execute("SELECT count(*) FROM artifact_search").fetchone()[0]
        self.assertEqual(count, 2)

    def test_a_name_is_findable(self):
        rows = self.connection.execute(
            "SELECT id FROM artifact_search WHERE artifact_search MATCH 'alpha'"
        ).fetchall()
        self.assertEqual([r[0] for r in rows], ["root-aaa"])

    def test_a_description_is_findable_and_not_only_the_name(self):
        rows = self.connection.execute(
            "SELECT id FROM artifact_search WHERE artifact_search MATCH 'work'"
        ).fetchall()
        self.assertEqual([r[0] for r in rows], ["root-aaa"])


class TheProseSaysWhatTheJsonSays(unittest.TestCase):
    def setUp(self):
        self.payload = graph.build(sample(), config=Config(emails=("me@example.com",)))
        self.text = llms.render(self.payload)

    def test_it_states_the_artifact_count(self):
        self.assertIn("2 Artifact(s)", self.text)

    def test_it_states_the_schema_so_no_companion_docs_are_needed(self):
        for node_type in self.payload["schema"]["node_types"]:
            self.assertIn(node_type, self.text)
        for edge_type in self.payload["schema"]["edge_types"]:
            self.assertIn(edge_type, self.text)

    def test_it_explains_that_a_fork_shares_an_identity(self):
        self.assertIn("fork", self.text.lower())
        self.assertIn("authorship.share", self.text)

    def test_it_warns_that_a_published_build_is_narrower(self):
        self.assertIn("narrower", self.text)

    def test_the_authors_own_build_makes_no_such_claim(self):
        payload = graph.build(sample(), build_mode="full")
        self.assertNotIn("narrower", llms.render(payload))

    def test_it_refuses_to_invite_a_quality_judgement(self):
        self.assertIn("does not rank, score or judge", self.text)
        self.assertIn("refused by design", self.text)

    def test_a_tool_span_carries_its_basis(self):
        self.assertIn("Author's own commits", self.text)

    def test_an_unattributed_span_says_so(self):
        text = llms.render(graph.build(sample()))
        self.assertIn("NOT attributed", text)

    def test_an_attributed_span_makes_no_such_disclaimer(self):
        self.assertNotIn("NOT attributed", self.text)


class EveryOutputIsWritten(unittest.TestCase):
    def test_a_build_emits_all_of_them(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            from core import store

            for a in sample():
                store.save(a, tmp)
            build_module.build(tmp)
            site = Path(tmp) / "site"
            for name in ("graph.json", "graph.js", "graph.sqlite", "llms.txt"):
                self.assertTrue((site / name).exists(), name)

    def test_the_authors_own_build_keeps_them_out_of_the_published_directory(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            from core import store

            for a in sample():
                store.save(a, tmp)
            build_module.build(tmp, mode=build_module.MODE_FULL)
            self.assertTrue((Path(tmp) / ".dendro-local" / "graph.sqlite").exists())
            self.assertFalse((Path(tmp) / "site").exists())


if __name__ == "__main__":
    unittest.main()
