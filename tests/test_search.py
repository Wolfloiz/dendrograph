"""Search answers the Author fully and the visitor only about what was published.

Three guards live here, and the middle one is the sharp edge of the story: a
word that exists only inside a withheld Artifact's description must be findable
from the Author's own machine and must not survive anywhere in the published
site — not as a row, not as a count, not as a byte.

`0 result(s).` and `1 result, hidden` are different answers to the same
question, and only one of them keeps the promise: a withheld count tells a
visitor that private work matches that word (FR-009, Princípio IV, ADR-0005).
"""

import io
import json
import sqlite3
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cli  # noqa: E402
from core import build, search, sqlite as sqlite_module  # noqa: E402
from core.store import Authorship  # noqa: E402
from core.report import EXIT_FAILURE, EXIT_OK, EXIT_USAGE  # noqa: E402
from core.store import VISIBILITY_PRIVATE  # noqa: E402
from tests.support import archives  # noqa: E402
from tests.support.fixtures import FixtureCase  # noqa: E402

# Uma palavra que não existe em lugar nenhum deste repositório, para que
# encontrá-la num arquivo publicado só possa significar vazamento.
WITHHELD_TERM = "thermoluminescence"
WITHHELD_TOOL = "Zigbee"


def run(*argv) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class SearchCase(FixtureCase):
    """An archive of two Artifacts: one published, one withheld."""

    def setUp(self):
        super().setUp()
        self.root = self.tmp / "archive"
        self.root.mkdir()
        archives.write(
            self.root,
            archives.artifact(
                "root-publico1",
                name="dendrograph",
                description="A knowledge graph of what you have built.",
                tools=("Python",),
            ),
            archives.artifact(
                "root-publico2",
                name="melissa-core",
                description="A lovely virtual assistant.",
                tools=("Python",),
            ),
            archives.artifact(
                "root-privado1",
                # O termo está SÓ na descrição: nenhum nome o carrega, que é
                # o caso que o contrato nomeia.
                name="internal-dating-lab",
                description=f"Sediment {WITHHELD_TERM} dating for a client.",
                visibility=VISIBILITY_PRIVATE,
                tools=(WITHHELD_TOOL,),
            ),
        )

    def build_both(self):
        """The full build the Author searches, and the site a visitor gets."""
        build.build(self.root, mode=build.MODE_FULL)
        build.build(self.root, mode=build.MODE_PUBLIC)

    def site(self) -> Path:
        return build.output_dir(self.root, build.MODE_PUBLIC)

    def published_payload(self) -> dict:
        """What the page itself loads — `graph.js`, not the JSON beside it."""
        raw = (self.site() / "graph.js").read_text(encoding="utf-8")
        return json.loads(raw[raw.index("{") : raw.rindex("}") + 1])


class ACommandLineAnswer(SearchCase):
    """T021 — every row names the kind, the subject and why it matched."""

    def setUp(self):
        super().setUp()
        self.build_both()

    def test_a_word_only_in_a_description_finds_the_artifact(self):
        # Cenário 1 da US2: a palavra não está em nome nenhum.
        code, out, _ = run("search", "--root", str(self.root), "assistant")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("melissa-core", out)

    def test_a_row_names_the_kind_the_subject_and_why(self):
        _, out, _ = run("search", "--root", str(self.root), "assistant")
        row = out.splitlines()[0]
        self.assertIn("melissa-core", row)
        self.assertIn("Artifact", row)
        self.assertIn('description: "', row)
        self.assertIn("assistant", row)

    def test_a_name_match_says_name_and_quotes_no_prose(self):
        _, out, _ = run("search", "--root", str(self.root), "dendrograph")
        row = out.splitlines()[0]
        self.assertTrue(row.rstrip().endswith("name"), row)
        self.assertNotIn("description", row)

    def test_a_search_matching_nothing_exits_zero_and_says_so(self):
        code, out, _ = run("search", "--root", str(self.root), "cartography")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out.strip(), "0 result(s).")

    def test_a_search_matching_nothing_offers_no_guess(self):
        # FR-009: dizer que não achou, e não propor outra coisa no lugar.
        _, out, _ = run("search", "--root", str(self.root), "cartography")
        for word in ("did you mean", "similar", "instead", "perhaps"):
            self.assertNotIn(word, out.lower())

    def test_a_query_naming_a_language_is_answered_not_crashed(self):
        # `c++` é erro de sintaxe em FTS5 se entregue cru. Um traceback aqui
        # seria a ferramenta culpando o Author por digitar o nome da linguagem.
        code, out, err = run("search", "--root", str(self.root), "c++")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("result(s).", out)
        self.assertEqual(err, "")

    def test_a_query_of_pure_punctuation_finds_nothing_quietly(self):
        code, out, _ = run("search", "--root", str(self.root), "---")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out.strip(), "0 result(s).")

    def test_the_total_stays_true_when_the_limit_cuts_the_list(self):
        # Cortar a lista não pode encolher a contagem: "1 of 2" é o que
        # distingue um resultado de um resultado escondido.
        code, out, _ = run("search", "--root", str(self.root), "--limit", "1", "a")
        self.assertEqual(code, EXIT_OK)
        last = out.strip().splitlines()[-1]
        self.assertRegex(last, r"^1 of \d+ result\(s\)\.$")

    def test_the_reason_comes_from_fts5_not_from_a_substring_guess(self):
        # Duas palavras, ambas só na prosa: quem decide o porquê comparando a
        # consulta inteira com o rótulo responde "name" para esta linha.
        code, out, _ = run("search", "--root", str(self.root), "knowledge graph")
        self.assertEqual(code, EXIT_OK)
        self.assertIn('description: "', out.splitlines()[0])

    def test_ordering_never_looks_at_who_wrote_more_of_it(self):
        # Princípio I: a ordem é o rank do FTS5 e depois o nome. Nada da
        # autoria, da atividade ou do tamanho do Artifact entra nela.
        _, before, _ = run("search", "--root", str(self.root), "a")

        archives.write(
            self.root,
            archives.artifact(
                "root-publico2",
                name="melissa-core",
                description="A lovely virtual assistant.",
                tools=("Python",),
                authorship=[Authorship(author="a@b.c", commits=40, name="Author")],
                activity={"first": "2005-01-01", "last": "2026-01-01"},
            ),
        )
        build.build(self.root, mode=build.MODE_FULL)
        _, after, _ = run("search", "--root", str(self.root), "a")
        self.assertEqual(before, after)

    def test_searching_writes_nothing(self):
        before = {p: p.stat().st_mtime_ns for p in self.site().rglob("*") if p.is_file()}
        run("search", "--root", str(self.root), "assistant")
        after = {p: p.stat().st_mtime_ns for p in self.site().rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_the_command_reads_only_and_is_declared_read_only(self):
        self.assertIn("search", cli.READ_ONLY_COMMANDS)
        self.assertIn("search", cli.COMMANDS)


class TheGuardOnWithheldWork(SearchCase):
    """T022 — the privacy guard. Never drop this one.

    O Author acha o termo; o site publicado não o contém em byte nenhum; e o
    índice da página não tem nada a devolver por ele — nem uma linha, nem uma
    contagem que confesse que existe algo escondido.
    """

    def setUp(self):
        super().setUp()
        self.build_both()

    # ---- o lado do Author ----

    def test_the_author_finds_a_term_that_lives_only_in_withheld_prose(self):
        code, out, _ = run("search", "--root", str(self.root), WITHHELD_TERM)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("internal-dating-lab", out)
        self.assertIn(WITHHELD_TERM, out)

    def test_the_author_searches_the_full_build_not_the_site(self):
        self.assertEqual(
            search.index_path(self.root),
            self.root / ".dendro-local" / sqlite_module.FILENAME,
        )

    # ---- o lado do visitante ----

    def test_the_term_survives_in_no_published_byte(self):
        for path in sorted(p for p in self.site().rglob("*") if p.is_file()):
            with self.subTest(file=path.name):
                self.assertNotIn(WITHHELD_TERM.encode(), path.read_bytes())

    def test_the_published_index_returns_nothing_and_counts_nothing(self):
        connection = search.connect(self.site() / sqlite_module.FILENAME)
        try:
            results, total = search.search(connection, WITHHELD_TERM)
        finally:
            connection.close()
        self.assertEqual(results, [])
        self.assertEqual(total, 0)
        # A linha inteira, não uma substring: é aqui que "1 result, hidden"
        # apareceria se alguém somasse os retidos de volta.
        self.assertEqual(search.render(results, total), "0 result(s).")

    def test_no_rendering_of_a_withheld_count_exists_at_all(self):
        rendered = search.render([], 0).lower()
        for confession in ("hidden", "withheld", "private", "excluded", "more"):
            self.assertNotIn(confession, rendered)

    def test_the_pages_own_index_has_nothing_to_build_a_result_from(self):
        # `views/search.js` monta suas entradas com exatamente esta regra:
        # nomes de Artifact, Tool e Technique, e descrições de Artifact. Se
        # nenhuma entrada contém o termo, nenhuma busca na página pode
        # devolvê-lo — e o teste acima já provou que o byte não está lá.
        searchable = {"Artifact", "Tool", "Technique"}
        for node in self.published_payload()["nodes"]:
            if node.get("type") not in searchable:
                continue
            haystack = (node.get("label") or "")
            if node.get("type") == "Artifact":
                haystack += " " + (node.get("description") or "")
            self.assertNotIn(WITHHELD_TERM.lower(), haystack.lower())

    def test_a_tool_used_only_by_withheld_work_is_not_in_the_payload(self):
        # O contrato: um Tool sem Artifacts publicados não pode ser um
        # resultado, porque não está no payload para ser um.
        labels = {node.get("label") for node in self.published_payload()["nodes"]}
        self.assertNotIn(WITHHELD_TOOL, labels)

    def test_the_withheld_artifact_is_absent_from_the_published_index(self):
        connection = search.connect(self.site() / sqlite_module.FILENAME)
        try:
            ids = {row[0] for row in connection.execute("SELECT id FROM artifact_search")}
        finally:
            connection.close()
        self.assertNotIn("root-privado1", ids)
        self.assertIn("root-publico1", ids)


class TheRefusalWithoutAnIndex(SearchCase):
    """T023 — no FTS5 table means refuse, never degrade (R6)."""

    def setUp(self):
        super().setUp()
        build.build(self.root, mode=build.MODE_FULL)
        self.index = self.root / ".dendro-local" / sqlite_module.FILENAME

    def drop_the_table(self):
        """What a Python compiled without FTS5 leaves behind: a valid archive
        with no `artifact_search` in it."""
        connection = sqlite3.connect(self.index)
        with connection:
            connection.execute("DROP TABLE artifact_search")
        connection.close()

    def test_has_search_is_what_tells_the_difference(self):
        connection = sqlite3.connect(self.index)
        self.assertTrue(sqlite_module.has_search(connection))
        connection.close()
        self.drop_the_table()
        connection = sqlite3.connect(self.index)
        self.assertFalse(sqlite_module.has_search(connection))
        connection.close()

    def test_the_command_refuses_with_the_usage_code(self):
        self.drop_the_table()
        code, _, _ = run("search", "--root", str(self.root), "assistant")
        self.assertEqual(code, EXIT_USAGE)

    def test_the_refusal_says_how_to_get_an_index(self):
        self.drop_the_table()
        _, _, err = run("search", "--root", str(self.root), "assistant")
        self.assertIn("without a search index", err)
        self.assertIn("fts5", err.lower())
        self.assertIn("dendro build", err)

    def test_the_refusal_prints_no_results_of_any_kind(self):
        # Degradar para uma varredura linear responderia a outra pergunta sem
        # dizer que trocou de pergunta.
        self.drop_the_table()
        _, out, _ = run("search", "--root", str(self.root), "assistant")
        self.assertEqual(out, "")

    def test_an_archive_with_no_build_is_a_different_failure(self):
        empty = self.tmp / "unbuilt"
        empty.mkdir()
        code, _, err = run("search", "--root", str(empty), "assistant")
        self.assertEqual(code, EXIT_FAILURE)
        self.assertIn("dendro build", err)
        self.assertNotIn("without a search index", err)


class SearchLatency(SearchCase):
    """T024 — search stays under 50 ms per keystroke at scale (SC-005)."""

    def setUp(self):
        super().setUp()
        # Gera um archive grande o suficiente para testar latência: 500
        # Artifacts com nomes e descrições variados.
        for i in range(500):
            archives.write(
                self.root,
                archives.artifact(
                    f"root-latency-{i:04d}",
                    name=f"project-{i:04d}",
                    description=f"Description number {i} with various words like "
                    f"python testing and deployment pipeline",
                    tools=("Python",),
                ),
            )
        build.build(self.root, mode=build.MODE_FULL)

    def test_search_completes_under_50_ms(self):
        """Uma busca por keystroke tem que caber em 50 ms (SC-005)."""
        import time

        connection = search.connect(
            self.root / ".dendro-local" / sqlite_module.FILENAME
        )
        try:
            queries = ["python", "project-0", "testing", "pipeline", "a"]
            for query in queries:
                start = time.perf_counter()
                results, total = search.search(connection, query)
                elapsed_ms = (time.perf_counter() - start) * 1000
                with self.subTest(query=query):
                    self.assertLess(
                        elapsed_ms, 50,
                        f"search('{query}') took {elapsed_ms:.1f} ms, limit is 50 ms",
                    )
                    self.assertGreater(total, 0, f"query '{query}' should match something")
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
