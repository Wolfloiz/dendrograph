"""O span de uma Tool é a janela dos commits do próprio Author.

O defeito que originou este arquivo apareceu na validação contra tinygrad:
`gpuocelot`, um fork com commits desde 2009, fazia C++, Docker, Python e Shell
lerem "primeiro uso em 2009" numa conta cujo trabalho começa em 2020. Um fork
carrega a história de quem veio antes, e somá-la à experiência do Author é
superestimar — a única direção que a ADR-0009 proíbe.
"""

import unittest

from core import graph
from core.analysis.spans import compute as compute_spans
from core.config import Config
from core.store import Artifact, Authorship

MINE = "eu@example.com"
THEIRS = "outra@example.com"


def artifact(artifact_id, tools, authorship, activity, **kwargs):
    return Artifact(
        id=artifact_id,
        identity={"method": "root-commit", "value": artifact_id},
        name=kwargs.pop("name", artifact_id),
        tools=[{"name": t} for t in tools],
        authorship=authorship,
        activity=activity,
        **kwargs,
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
        spans = compute_spans([fork], (MINE,))
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
        spans = compute_spans([untouched, own], (MINE,))
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
        spans = compute_spans([untouched, own], (MINE,))
        self.assertEqual(spans["Rust"].artifact_count, 1)
        self.assertEqual(spans["Rust"].untouched_count, 1)

    def test_a_tool_only_in_untouched_forks_claims_no_experience(self):
        untouched = artifact(
            "untouched", ["Fortran"], [entry(THEIRS, "1998-01-01", "1999-01-01")],
            {"first": "1998-01-01", "last": "1999-01-01"},
        )
        spans = compute_spans([untouched], (MINE,))
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
        spans = compute_spans([early, late], (MINE,))
        self.assertEqual(spans["Python"].first, "2018-02-01")
        self.assertEqual(spans["Python"].last, "2026-04-01")
        self.assertEqual(spans["Python"].artifact_count, 2)

    def test_any_configured_email_counts_as_the_author(self):
        other = "eu@trabalho.example"
        art = artifact(
            "a", ["Go"], [entry(other, "2022-01-01", "2022-06-01")],
            {"first": "2022-01-01", "last": "2022-06-01"},
        )
        spans = compute_spans([art], (MINE, other))
        self.assertEqual(spans["Go"].first, "2022-01-01")


class WithoutEmailsTheSpanSaysSo(unittest.TestCase):
    def test_the_window_is_marked_unattributed(self):
        art = artifact(
            "a", ["Python"], [entry(THEIRS, "2009-06-11", "2023-01-01")],
            {"first": "2009-06-11", "last": "2023-01-01"},
        )
        spans = compute_spans([art])
        self.assertFalse(spans["Python"].attributed)
        # A janela observada continua valendo como observação; o que ela não
        # sustenta é a frase "anos de experiência" da SC-007.
        self.assertEqual(spans["Python"].first, "2009-06-11")

    def test_with_emails_the_window_is_attributed(self):
        art = artifact(
            "a", ["Python"], [entry(MINE, "2020-10-17", "2026-08-15")],
            {"first": "2020-10-17", "last": "2026-08-15"},
        )
        spans = compute_spans([art], (MINE,))
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


class ATechniqueIsAskedTheSameQuestion(unittest.TestCase):
    """"Desde quando eu faço teste automatizado" é a pergunta do README.

    Para Rust a ferramenta respondia com uma data. Para uma Technique respondia
    com pertencimento a um conjunto: o nó saía com id, tipo e rótulo e nada
    mais. O módulo de span nunca soube o que é uma Tool — lê `{"name": ...}` —,
    então a resposta já estava escrita, faltava perguntar.
    """

    def _applied(self, artifact_id, techniques, authorship, activity):
        art = artifact(artifact_id, [], authorship, activity)
        art.techniques = [{"name": t, "confidence": "high"} for t in techniques]
        return art

    def test_the_span_reads_techniques_when_asked_for_them(self):
        art = self._applied(
            "a", ["Automated Testing"],
            [entry(MINE, "2020-10-05", "2024-02-01")],
            {"first": "2019-01-01", "last": "2024-02-01"},
        )
        spans = compute_spans([art], (MINE,), of="techniques")
        self.assertEqual(spans["Automated Testing"].first, "2020-10-05")
        self.assertEqual(spans["Automated Testing"].last, "2024-02-01")
        self.assertEqual(spans["Automated Testing"].artifact_count, 1)

    def test_tools_and_techniques_do_not_leak_into_each_other(self):
        art = self._applied(
            "a", ["Static Typing"],
            [entry(MINE, "2020-01-01", "2021-01-01")],
            {"first": "2020-01-01", "last": "2021-01-01"},
        )
        art.tools = [{"name": "Python"}]
        self.assertEqual(list(compute_spans([art], (MINE,))), ["Python"])
        self.assertEqual(
            list(compute_spans([art], (MINE,), of="techniques")), ["Static Typing"]
        )

    def test_a_fork_the_author_never_touched_counts_but_carries_no_dates(self):
        # O mesmo trato da Tool: fica visível, não empresta data. Na varredura
        # real, Automated Testing tinha oito forks intocados.
        untouched = self._applied(
            "fork", ["Automated Testing"],
            [entry(THEIRS, "2009-01-01", "2015-01-01")],
            {"first": "2009-01-01", "last": "2015-01-01"},
        )
        mine = self._applied(
            "mine", ["Automated Testing"],
            [entry(MINE, "2022-03-01", "2023-03-01")],
            {"first": "2022-03-01", "last": "2023-03-01"},
        )
        span = compute_spans([untouched, mine], (MINE,), of="techniques")["Automated Testing"]
        self.assertEqual((span.first, span.last), ("2022-03-01", "2023-03-01"))
        self.assertEqual(span.artifact_count, 1)
        self.assertEqual(span.untouched_count, 1)

    def test_the_graph_node_carries_the_span(self):
        early = self._applied(
            "early", ["Continuous Integration"],
            [entry(MINE, "2021-05-12", "2021-09-01")],
            {"first": "2021-05-12", "last": "2021-09-01"},
        )
        late = self._applied(
            "late", ["Continuous Integration"],
            [entry(MINE, "2024-01-01", "2026-08-19")],
            {"first": "2024-01-01", "last": "2026-08-19"},
        )
        payload = graph.build([early, late], config=Config(emails=(MINE,)),
                              generated_at="2026-08-27T00:00:00Z")
        [node] = [n for n in payload["nodes"] if n["type"] == "Technique"]
        self.assertEqual(node["first"], "2021-05-12")
        self.assertEqual(node["last"], "2026-08-19")
        self.assertEqual(node["artifact_count"], 2)

    def test_an_unattributed_span_says_so(self):
        art = self._applied(
            "a", ["Static Typing"], [entry(THEIRS, "2020-01-01", "2021-01-01")],
            {"first": "2020-01-01", "last": "2021-01-01"},
        )
        payload = graph.build([art], generated_at="2026-08-27T00:00:00Z")
        [node] = [n for n in payload["nodes"] if n["type"] == "Technique"]
        self.assertIs(node["attributed"], False)


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
        spans = compute_spans([art], ("ME@EXAMPLE.COM",))
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


class ASpanNeverOutrunsWhatTheBuildPublishes(unittest.TestCase):
    """T056, a metade de visibilidade: um span é tão largo quanto o build.

    Um span sustentado só por Artifacts privados **não aparece num build
    `public`**. Se aparecesse, a data diria a um visitante que houve trabalho
    naquele intervalo — que é exatamente o que o Princípio IV proíbe, e a
    largura da janela é um vazamento tão real quanto o nome (FR-027, US3 AS2).

    Ele volta quando o Author decide, campo a campo, e está sempre completo na
    visão que só o Author lê.
    """

    MINE = "eu@example.com"
    # O nome que quebra a NDA se aparecer em qualquer lugar da saída.
    CLIENT = "acme-bank-settlement"

    def archive(self):
        from core.store import VISIBILITY_PRIVATE, VISIBILITY_PUBLIC

        return [
            artifact(
                "root-public",
                ["Python"],
                [entry(self.MINE, "2023-01-01", "2024-01-01")],
                {"first": "2023-01-01", "last": "2024-01-01"},
                visibility=VISIBILITY_PUBLIC,
            ),
            artifact(
                "root-private",
                ["Python", "Kafka"],
                [entry(self.MINE, "2018-02-01", "2026-05-01")],
                {"first": "2018-02-01", "last": "2026-05-01"},
                visibility=VISIBILITY_PRIVATE,
                name=self.CLIENT,
                description=f"Internal trading platform for {self.CLIENT}",
            ),
        ]

    def tools(self, *, mode, aliases=()):
        from core import privacy

        config = Config(emails=(self.MINE,), aliases=tuple(aliases))
        selection = privacy.select(self.archive(), config=config, mode=mode)
        payload = graph.build(selection.included, config=config, build_mode=mode)
        return {n["label"]: n for n in payload["nodes"] if n["type"] == "Tool"}

    def test_a_tool_only_private_work_uses_is_absent_from_a_public_build(self):
        self.assertNotIn("Kafka", self.tools(mode="public"))

    def test_a_shared_tools_span_is_narrowed_to_the_public_work(self):
        # Python é usado nos dois. A janela publicada é só a do público: dizer
        # 2018 revelaria que existiu trabalho privado começando ali.
        python = self.tools(mode="public")["Python"]
        self.assertEqual(python["first"], "2023-01-01")
        self.assertEqual(python["last"], "2024-01-01")

    def test_the_authors_own_build_shows_the_true_span(self):
        python = self.tools(mode="full")["Python"]
        self.assertEqual(python["first"], "2018-02-01")
        self.assertEqual(python["last"], "2026-05-01")
        self.assertIn("Kafka", self.tools(mode="full"))

    def test_an_alias_alone_does_not_widen_the_span(self):
        # ADR-0011: divulgação é opt-in campo a campo. O nó aparece; as Tools
        # não, e portanto as datas delas também não.
        from core.config import Alias

        tools = self.tools(mode="public", aliases=(Alias(id="root-private"),))
        self.assertNotIn("Kafka", tools)
        self.assertEqual(tools["Python"]["first"], "2023-01-01")

    def test_revealing_tools_completes_the_span(self):
        from core.config import Alias

        tools = self.tools(
            mode="public", aliases=(Alias(id="root-private", reveal=("tools",)),)
        )
        self.assertIn("Kafka", tools)
        self.assertEqual(tools["Python"]["first"], "2018-02-01")
        self.assertEqual(tools["Python"]["last"], "2026-05-01")

    def test_the_aliased_artifact_is_traceable_from_the_tool_it_revealed(self):
        # SC-006/SC-007: a data tem que apontar para o Artifact que a sustenta,
        # mesmo que esse Artifact esteja sob um nome que não é o dele.
        from core import privacy
        from core.config import Alias

        config = Config(
            emails=(self.MINE,),
            aliases=(Alias(id="root-private", label="Anonymous client", reveal=("tools",)),),
        )
        selection = privacy.select(self.archive(), config=config, mode="public")
        payload = graph.build(selection.included, config=config, build_mode="public")
        index = payload["indexes"]["tool_to_artifacts"]
        kafka = next(n for n in payload["nodes"] if n["label"] == "Kafka")
        self.assertIn("root-private", index[kafka["id"]])
        node = next(n for n in payload["nodes"] if n["id"] == "root-private")
        self.assertEqual(node["label"], "Anonymous client")

    def test_no_real_name_reaches_the_public_build_at_any_reveal_setting(self):
        import json

        from core import privacy
        from core.config import Alias

        for reveal in ((), ("tools",), ("tools", "period", "authorship")):
            config = Config(
                emails=(self.MINE,),
                aliases=(Alias(id="root-private", reveal=reveal),),
            )
            selection = privacy.select(self.archive(), config=config, mode="public")
            payload = graph.build(selection.included, config=config, build_mode="public")
            text = json.dumps(payload)
            self.assertNotIn(self.CLIENT, text, f"leaked at reveal={reveal}")
            self.assertNotIn("Internal trading platform", text)
