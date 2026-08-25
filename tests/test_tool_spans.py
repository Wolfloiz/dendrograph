"""O span de uma Tool é a janela dos commits do próprio Author.

O defeito que originou este arquivo apareceu na validação contra tinygrad:
`gpuocelot`, um fork com commits desde 2009, fazia C++, Docker, Python e Shell
lerem "primeiro uso em 2009" numa conta cujo trabalho começa em 2020. Um fork
carrega a história de quem veio antes, e somá-la à experiência do Author é
superestimar — a única direção que a ADR-0009 proíbe.
"""

import unittest

from core.analysis import tool_spans
from core.config import Config
from core.store import Artifact, Authorship

MINE = "eu@example.com"
THEIRS = "outra@example.com"


def artifact(artifact_id, tools, authorship, activity):
    return Artifact(
        id=artifact_id,
        identity={"method": "root-commit", "value": artifact_id},
        name=artifact_id,
        tools=[{"name": t} for t in tools],
        authorship=authorship,
        activity=activity,
    )


def entry(email, first, last, commits=10):
    return Authorship(
        author=email,
        commits=commits,
        lines_added=commits * 10,
        lines_deleted=0,
        first=first,
        last=last,
    )


class TheSpanFollowsTheAuthorsOwnCommits(unittest.TestCase):
    def test_an_upstreams_history_does_not_become_the_authors(self):
        # O caso gpuocelot: o repositório existe desde 2009, o Author chegou
        # em 2024. "Python desde 2009" é uma frase que ninguém observou.
        fork = artifact(
            "fork",
            ["Python"],
            [entry(THEIRS, "2009-06-11", "2023-01-01", commits=900),
             entry(MINE, "2024-03-01", "2024-05-02", commits=3)],
            {"first": "2009-06-11", "last": "2024-05-02"},
        )
        spans = tool_spans.compute([fork], (MINE,))
        self.assertEqual(spans["Python"].first, "2024-03-01")
        self.assertEqual(spans["Python"].last, "2024-05-02")

    def test_a_fork_the_author_never_touched_contributes_no_dates(self):
        untouched = artifact(
            "untouched",
            ["Python"],
            [entry(THEIRS, "2009-06-11", "2023-01-01")],
            {"first": "2009-06-11", "last": "2023-01-01"},
        )
        own = artifact(
            "own",
            ["Python"],
            [entry(MINE, "2020-10-17", "2026-08-15")],
            {"first": "2020-10-17", "last": "2026-08-15"},
        )
        spans = tool_spans.compute([untouched, own], (MINE,))
        self.assertEqual(spans["Python"].first, "2020-10-17")
        self.assertEqual(spans["Python"].artifact_count, 1)

    def test_an_untouched_fork_is_counted_but_not_hidden(self):
        # Some do span, não do relatório: o Author precisa poder explicar por
        # que a contagem de Artifacts não bate com o que ele vê no arquivo.
        untouched = artifact(
            "untouched", ["Rust"], [entry(THEIRS, "2015-01-01", "2016-01-01")],
            {"first": "2015-01-01", "last": "2016-01-01"},
        )
        own = artifact(
            "own", ["Rust"], [entry(MINE, "2023-12-24", "2026-08-15")],
            {"first": "2023-12-24", "last": "2026-08-15"},
        )
        spans = tool_spans.compute([untouched, own], (MINE,))
        self.assertEqual(spans["Rust"].artifact_count, 1)
        self.assertEqual(spans["Rust"].untouched_count, 1)

    def test_a_tool_only_in_untouched_forks_claims_no_experience(self):
        untouched = artifact(
            "untouched", ["Fortran"], [entry(THEIRS, "1998-01-01", "1999-01-01")],
            {"first": "1998-01-01", "last": "1999-01-01"},
        )
        spans = tool_spans.compute([untouched], (MINE,))
        self.assertEqual(spans["Fortran"].artifact_count, 0)
        self.assertIsNone(spans["Fortran"].first)
        self.assertEqual(spans["Fortran"].untouched_count, 1)

    def test_several_artifacts_widen_the_window_to_the_authors_own_extremes(self):
        early = artifact(
            "early", ["Python"], [entry(MINE, "2018-02-01", "2018-09-01")],
            {"first": "2018-02-01", "last": "2018-09-01"},
        )
        late = artifact(
            "late", ["Python"], [entry(MINE, "2025-01-01", "2026-04-01")],
            {"first": "2025-01-01", "last": "2026-04-01"},
        )
        spans = tool_spans.compute([early, late], (MINE,))
        self.assertEqual(spans["Python"].first, "2018-02-01")
        self.assertEqual(spans["Python"].last, "2026-04-01")
        self.assertEqual(spans["Python"].artifact_count, 2)

    def test_any_configured_email_counts_as_the_author(self):
        other = "eu@trabalho.example"
        art = artifact(
            "a", ["Go"], [entry(other, "2022-01-01", "2022-06-01")],
            {"first": "2022-01-01", "last": "2022-06-01"},
        )
        spans = tool_spans.compute([art], (MINE, other))
        self.assertEqual(spans["Go"].first, "2022-01-01")


class WithoutEmailsTheSpanSaysSo(unittest.TestCase):
    def test_the_window_is_marked_unattributed(self):
        art = artifact(
            "a", ["Python"], [entry(THEIRS, "2009-06-11", "2023-01-01")],
            {"first": "2009-06-11", "last": "2023-01-01"},
        )
        spans = tool_spans.compute([art])
        self.assertFalse(spans["Python"].attributed)
        # A janela observada continua valendo como observação; o que ela não
        # sustenta é a frase "anos de experiência" da SC-007.
        self.assertEqual(spans["Python"].first, "2009-06-11")

    def test_with_emails_the_window_is_attributed(self):
        art = artifact(
            "a", ["Python"], [entry(MINE, "2020-10-17", "2026-08-15")],
            {"first": "2020-10-17", "last": "2026-08-15"},
        )
        spans = tool_spans.compute([art], (MINE,))
        self.assertTrue(spans["Python"].attributed)


class TheGraphCarriesTheDistinction(unittest.TestCase):
    def _tool_node(self, artifacts, config=None):
        from core import graph

        payload = graph.build(artifacts, config=config)
        return next(n for n in payload["nodes"] if n["type"] == "Tool")

    def test_an_unattributed_span_is_flagged_in_the_graph(self):
        art = artifact(
            "a", ["Python"], [entry(THEIRS, "2009-06-11", "2023-01-01")],
            {"first": "2009-06-11", "last": "2023-01-01"},
        )
        self.assertIs(self._tool_node([art])["attributed"], False)

    def test_an_attributed_span_does_not_carry_the_flag(self):
        art = artifact(
            "a", ["Python"], [entry(MINE, "2020-10-17", "2026-08-15")],
            {"first": "2020-10-17", "last": "2026-08-15"},
        )
        node = self._tool_node([art], config=Config(emails=(MINE,)))
        self.assertNotIn("attributed", node)
        self.assertEqual(node["first"], "2020-10-17")

    def test_untouched_forks_reach_the_graph_when_there_are_any(self):
        untouched = artifact(
            "untouched", ["Python"], [entry(THEIRS, "2009-06-11", "2023-01-01")],
            {"first": "2009-06-11", "last": "2023-01-01"},
        )
        own = artifact(
            "own", ["Python"], [entry(MINE, "2020-10-17", "2026-08-15")],
            {"first": "2020-10-17", "last": "2026-08-15"},
        )
        node = self._tool_node([untouched, own], config=Config(emails=(MINE,)))
        self.assertEqual(node["untouched_count"], 1)
        self.assertEqual(node["first"], "2020-10-17")


if __name__ == "__main__":
    unittest.main()


class DistinctToolsGetDistinctNodes(unittest.TestCase):
    """C, C++ e C# colapsavam todos em `tool:c`.

    Um nó só, com o rótulo de quem escreveu por último, as arestas USES das três
    somadas e o span de uma linguagem pendurado na identidade de outra. O índice
    `tool_to_artifacts` dizia 7 Artifacts para C++ enquanto o span contava 3.
    """

    def test_c_family_names_do_not_share_a_node_id(self):
        from core.graph import node_id

        ids = {node_id("Tool", name) for name in ("C", "C++", "C#")}
        self.assertEqual(len(ids), 3, f"collapsed into {ids}")

    def test_the_sharp_languages_stay_apart(self):
        from core.graph import node_id

        self.assertNotEqual(node_id("Tool", "F"), node_id("Tool", "F#"))

    def test_ordinary_names_keep_a_readable_id(self):
        from core.graph import node_id

        self.assertEqual(node_id("Tool", "Python"), "tool:python")
        self.assertEqual(node_id("Tool", "C++"), "tool:c-plus-plus")

    def test_two_labels_on_one_id_are_refused_rather_than_merged(self):
        from core.graph import CollidingLabels, GraphBuilder

        builder = GraphBuilder()
        builder.node("tool:x", "Tool", "One")
        with self.assertRaises(CollidingLabels) as caught:
            builder.node("tool:x", "Tool", "Another")
        self.assertIn("One", str(caught.exception))
        self.assertIn("Another", str(caught.exception))

    def test_the_same_label_twice_is_still_deduplicated(self):
        from core.graph import GraphBuilder

        builder = GraphBuilder()
        builder.node("tool:x", "Tool", "One")
        builder.node("tool:x", "Tool", "One", first="2020-01-01")
        self.assertEqual(len(builder._nodes), 1)

    def test_the_index_and_the_span_agree_on_how_many_artifacts_use_a_tool(self):
        # A divergência que expôs a colisão: índice 7, span 3.
        from core import graph

        arts = [
            artifact("a", ["C"], [entry(MINE, "2021-01-01", "2021-06-01")],
                     {"first": "2021-01-01", "last": "2021-06-01"}),
            artifact("b", ["C++"], [entry(MINE, "2022-01-01", "2022-06-01")],
                     {"first": "2022-01-01", "last": "2022-06-01"}),
            artifact("c", ["C++"], [entry(MINE, "2023-01-01", "2023-06-01")],
                     {"first": "2023-01-01", "last": "2023-06-01"}),
        ]
        payload = graph.build(arts, config=Config(emails=(MINE,)))
        index = payload["indexes"]["tool_to_artifacts"]
        for node in payload["nodes"]:
            if node["type"] != "Tool":
                continue
            self.assertEqual(
                len(index[node["id"]]),
                node["artifact_count"] + node.get("untouched_count", 0),
                f'{node["label"]} disagrees with its index entry',
            )


class TheSameAuthorTypedTwoWaysIsOnePerson(unittest.TestCase):
    """git grava o que a pessoa digitou, e ela não digita igual toda vez.

    `Cloud11665@gmail.com` e `cloud11665@gmail.com` apareceram no mesmo arquivo
    real. Sem normalizar viram dois autores: duas contagens, dois nós Author, e
    um `share` que não fecha.
    """

    def test_the_stored_email_is_normalised(self):
        self.assertEqual(entry("Cloud11665@Gmail.COM", None, None).author,
                         "cloud11665@gmail.com")

    def test_two_spellings_weigh_as_one_author(self):
        from collectors.git.authorship import share

        entries = [entry("Me@Example.com", None, None, commits=5),
                   entry("me@example.com", None, None, commits=5)]
        self.assertEqual(share(entries, ("me@example.com",)), 1.0)

    def test_a_configured_email_matches_whatever_case_it_was_written_in(self):
        art = artifact(
            "a", ["Python"], [entry("Me@Example.com", "2020-01-01", "2021-01-01")],
            {"first": "2020-01-01", "last": "2021-01-01"},
        )
        spans = tool_spans.compute([art], ("ME@EXAMPLE.COM",))
        self.assertEqual(spans["Python"].first, "2020-01-01")

    def test_one_author_node_per_person(self):
        from core import graph

        art = artifact(
            "a", ["Python"],
            [entry("Me@Example.com", "2020-01-01", "2021-01-01"),
             entry("me@example.com", "2021-02-01", "2022-01-01")],
            {"first": "2020-01-01", "last": "2022-01-01"},
        )
        payload = graph.build([art], config=Config(emails=(MINE,)))
        authors = [n for n in payload["nodes"] if n["type"] == "Author"]
        self.assertEqual(len(authors), 1)
