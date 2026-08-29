"""O perfil de uma Tool não pode contar de um jeito e listar de outro.

O plano da v0.2 deixou isto em aberto (research.md, R7) com uma aposta: marcar
as linhas intocadas por `authorship.share` e contá-las pelo `untouched_count`
do nó deveriam coincidir, e nada garantia. Não coincidiram. No arquivo real,
JavaScript dava **13 linhas derivadas sob um título dizendo 12**.

São duas perguntas diferentes. `share` é quanto do material é do Author;
`untouched` é se ele commitou. Um repositório onde ele commitou sem somar
linhas tem janela de datas e `share` zero. A resposta foi publicar a lista que
o span usou — `indexes.tool_to_untouched` — em vez de conciliar as duas contas
em silêncio.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import graph  # noqa: E402
from core.analysis.spans import compute as compute_spans  # noqa: E402
from core.config import Config  # noqa: E402
from core.store import Artifact, Authorship  # noqa: E402

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


def entry(email, first, last, commits=10, added=100):
    return Authorship(author=email, commits=commits, lines_added=added,
                      lines_deleted=0, first=first, last=last)


class TheCountAndTheListAreTheSameMeasurement(unittest.TestCase):
    def payload(self, artifacts):
        return graph.build(artifacts, config=Config(emails=(MINE,)),
                           generated_at="2026-08-29T00:00:00Z")

    def test_the_published_list_matches_the_published_count(self):
        mine = artifact("root-mine", ["Python"], [entry(MINE, "2020-01-01", "2021-01-01")],
                        {"first": "2020-01-01", "last": "2021-01-01"})
        fork = artifact("root-fork", ["Python"], [entry(THEIRS, "2009-01-01", "2015-01-01")],
                        {"first": "2009-01-01", "last": "2015-01-01"})
        payload = self.payload([mine, fork])
        [tool] = [n for n in payload["nodes"] if n["type"] == "Tool"]
        listed = payload["indexes"]["tool_to_untouched"].get(tool["id"], [])
        self.assertEqual(len(listed), tool["untouched_count"])
        self.assertEqual(listed, ["root-fork"])

    def test_a_commit_that_added_no_lines_is_not_an_untouched_fork(self):
        # O caso que derrubou a derivação por `share`: o Author commitou, então
        # há janela de datas, mas não somou material, então `share` é zero.
        # Contar pelo `share` chamaria isto de fork intocado; o span não chama.
        touched = artifact(
            "root-touched", ["Python"],
            [entry(MINE, "2022-01-01", "2022-06-01", commits=4, added=0),
             entry(THEIRS, "2020-01-01", "2022-06-01", commits=90, added=9000)],
            {"first": "2020-01-01", "last": "2022-06-01"},
        )
        payload = self.payload([touched])
        [tool] = [n for n in payload["nodes"] if n["type"] == "Tool"]
        [node] = [n for n in payload["nodes"] if n["type"] == "Artifact"]
        # Praticamente nada — e "praticamente nada" é o que uma derivação por
        # `share` teria lido como "nada".
        self.assertLess(node["authorship"]["share"], 0.01)
        self.assertEqual(tool.get("untouched_count", 0), 0)
        self.assertEqual(payload["indexes"]["tool_to_untouched"], {})
        self.assertEqual(tool["artifact_count"], 1)

    def test_the_index_omits_tools_with_nothing_untouched(self):
        mine = artifact("root-mine", ["Rust"], [entry(MINE, "2020-01-01", "2021-01-01")],
                        {"first": "2020-01-01", "last": "2021-01-01"})
        payload = self.payload([mine])
        self.assertEqual(payload["indexes"]["tool_to_untouched"], {})

    def test_the_span_carries_the_ids_it_counted(self):
        mine = artifact("root-mine", ["Go"], [entry(MINE, "2020-01-01", "2021-01-01")],
                        {"first": "2020-01-01", "last": "2021-01-01"})
        fork = artifact("root-fork", ["Go"], [entry(THEIRS, "2009-01-01", "2015-01-01")],
                        {"first": "2009-01-01", "last": "2015-01-01"})
        span = compute_spans([mine, fork], (MINE,))["Go"]
        self.assertEqual(span.untouched_count, len(span.untouched_ids))
        self.assertEqual(span.untouched_ids, ("root-fork",))


class AWithheldToolIsNotReachable(unittest.TestCase):
    """Um perfil endereçável por chute não pode confirmar o que foi retido."""

    def test_a_tool_used_only_by_withheld_artifacts_is_absent(self):
        # O build recebe só os Artifacts publicáveis; uma Tool cujo único uso
        # ficou de fora não tem nó, não tem índice e não tem perfil.
        payload = graph.build([], config=Config(emails=(MINE,)),
                              generated_at="2026-08-29T00:00:00Z")
        self.assertEqual([n for n in payload["nodes"] if n["type"] == "Tool"], [])
        self.assertEqual(payload["indexes"]["tool_to_artifacts"], {})
        self.assertEqual(payload["indexes"]["tool_to_untouched"], {})


if __name__ == "__main__":
    unittest.main()
