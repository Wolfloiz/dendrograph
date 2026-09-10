"""Um Artifact sob alias publica o rótulo, e nada além do que `reveal` nomeia.

FR-028, ADR-0011, SC-004. A lista do que nunca cruza é curta e absoluta:
nome real, descrição, URL, locator de origem, caminho de evidência de
Technique, hash de conteúdo, arestas DERIVES_FROM/SUCCEEDS. O teste varre os
arquivos publicados por todos eles, em cada modo publicado — e confirma que
o que sobrou é exatamente o que `reveal` liberou.
"""

import json
from pathlib import Path

from core import build, graph as graph_module
from core.config import Alias, Config
from tests.support import archives
from tests.support.fixtures import FixtureCase

SECRETS = (
    archives.CLIENT_NAME,
    "acme",
    archives.EVIDENCE_PATH,
    archives.CONTENT_HASH,
    "Internal tooling",
    "/media/backup/work",  # o locator
)


def published_text(root) -> str:
    site = build.output_dir(root, "public")
    return "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(site.iterdir()) if path.is_file() and path.suffix != ".sqlite"
    )


class AnAliasPublishesTheLabelAndNothingElse(FixtureCase):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "archive"
        self.root.mkdir()
        archives.write(self.root, archives.private(), archives.public())
        self.config = Config(aliases=(
            Alias(id=archives.PRIVATE_ID, label="Anonymous fintech project"),
        ))
        self.payload = build.build(self.root, config=self.config)
        self.text = published_text(self.root)

    def test_the_label_is_published_and_the_real_name_never(self):
        self.assertIn("Anonymous fintech project", self.text)
        for secret in SECRETS:
            self.assertNotIn(secret, self.text)

    def test_the_node_marks_itself_as_aliased(self):
        node = next(n for n in self.payload["nodes"] if n["id"] == archives.PRIVATE_ID)
        self.assertTrue(node.get("aliased"))
        # Datas ficam: o lugar no timeline é o que sobra quando a identidade sai.
        self.assertEqual(node["first"], "2021-03-01")
        self.assertNotIn("description", node)

    def test_no_edge_reveals_what_was_not_revealed(self):
        # Só a Technique nua (sem evidência) cruza; nada de USES, IN_PERIOD,
        # AUTHORED_BY, DEPENDS_ON ou linhagem sem reveal.
        edges = [e for e in self.payload["edges"] if e["from"] == archives.PRIVATE_ID]
        self.assertEqual([e["type"] for e in edges], ["APPLIES"])
        self.assertTrue(all(not e.get("evidence") for e in edges))

    def test_techniques_ship_without_evidence_pointers(self):
        # Sem reveal nenhum, nem a Technique cruza; com ela revelada, viaja
        # sem o ponteiro — e portanto sem verificação. Isso se diz, não se
        # esconde (contracts/graph.md).
        config = Config(aliases=(
            Alias(id=archives.PRIVATE_ID, label="Anon", reveal=("tools",)),
        ))
        payload = build.build(self.root, mode="public", config=config)
        applies = [
            e for e in payload["edges"]
            if e["from"] == archives.PRIVATE_ID and e["type"] == "APPLIES"
        ]
        self.assertTrue(applies)
        self.assertTrue(all(not e.get("evidence") for e in applies))
        blob = json.dumps(payload)
        self.assertNotIn(archives.EVIDENCE_PATH, blob)


class RevealNamesExactlyWhatCrosses(FixtureCase):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "archive"
        self.root.mkdir()
        archives.write(self.root, archives.private())

    def edges_for(self, config):
        payload = build.build(self.root, config=config)
        return {
            e["type"] for e in payload["edges"] if e["from"] == archives.PRIVATE_ID
        }

    def test_empty_reveal_publishes_node_dates_and_bare_techniques(self):
        # Techniques não têm campo em `reveal`: publicam-se sempre, sem o
        # ponteiro de evidência — e portanto sem verificação, o que se diz
        # abertamente (contracts/graph.md). Nada mais cruza.
        config = Config(aliases=(Alias(id=archives.PRIVATE_ID),))
        self.assertEqual(self.edges_for(config), {"APPLIES"})
        node = next(n for n in build.build(self.root, config=config)["nodes"]
                    if n["id"] == archives.PRIVATE_ID)
        self.assertIn("first", node)

    def test_each_named_field_crosses_alone(self):
        cases = {
            "tools": {"USES"},
            "period": {"IN_PERIOD"},
            "authorship": {"AUTHORED_BY"},
        }
        from core.store import Authorship

        artifact = archives.private()
        stored = type(artifact)(
            id=artifact.id, identity=artifact.identity, name=artifact.name,
            description=None, visibility=artifact.visibility,
            sources=artifact.sources, activity=artifact.activity,
            authorship=[Authorship(author="eu@example.com", commits=5)],
            tools=artifact.tools, techniques=artifact.techniques,
            dependencies=artifact.dependencies, content_hashes={},
        )
        archives.write(self.root, stored)
        for field, expected in cases.items():
            with self.subTest(reveal=field):
                config = Config(emails=("eu@example.com",), aliases=(
                    Alias(id=archives.PRIVATE_ID, label="Anon", reveal=(field,)),
                ))
                self.assertEqual(self.edges_for(config), expected | {"APPLIES"})


class LineageEdgesNeverCrossAnAlias(FixtureCase):
    def test_derives_from_to_a_known_artifact_is_dropped(self):
        builder = graph_module.GraphBuilder()
        aliased = builder.node("root-anon", "Artifact", "Private project 1")
        known = builder.node("root-known", "Artifact", "dendrograph")
        builder.shield(aliased)
        builder.edge(aliased, known, "DERIVES_FROM")
        builder.edge(known, aliased, "SUCCEEDS")
        types = {e["type"] for e in builder.to_dict(build_mode="full")["edges"]}
        self.assertNotIn("DERIVES_FROM", types)
        self.assertNotIn("SUCCEEDS", types)


class TheAliasedNodeKeepsTheIdThatIdentifiesTheRepository(FixtureCase):
    """O id de um Artifact sob alias é o SHA do commit raiz, e é publicado.

    Não é descuido: a identidade de Artifact é o commit raiz (ADR-0003) e o
    grafo publica ids de Artifact como ids do store (contracts/graph.md). Quem
    tem um clone reproduz o valor com `git rev-list --max-parents=0 HEAD` e
    confirma a correspondência — e um repositório privado que seja fork de algo
    público já tem o SHA raiz público, porque um fork *é* o mesmo Artifact.

    Foi decidido em 2026-09-10 documentar em vez de corrigir. Este teste é
    onde a decisão fica executável: se alguém passar a derivar o id sob alias,
    ele falha e obriga a mexer na ADR-0011 junto, em vez de o comportamento
    mudar em silêncio nos dois sentidos.
    """

    def setUp(self):
        super().setUp()
        self.root = self.tmp / "archive"
        self.root.mkdir()
        archives.write(self.root, archives.private(), archives.public())
        self.payload = build.build(self.root, config=Config(aliases=(
            Alias(id=archives.PRIVATE_ID, label="Anonymous fintech project"),
        )))

    def test_the_published_id_is_the_store_id_unchanged(self):
        node = next(n for n in self.payload["nodes"] if n.get("aliased"))
        self.assertEqual(node["id"], archives.PRIVATE_ID)

    def test_the_id_reaches_the_published_files(self):
        # O rótulo é falso e o id é verdadeiro, no mesmo arquivo. É exatamente
        # isso que a ADR-0011 registra como divulgação conhecida.
        text = published_text(self.root)
        self.assertIn("Anonymous fintech project", text)
        self.assertIn(archives.PRIVATE_ID, text)

    def test_the_disclosure_is_written_down_where_it_is_decided(self):
        # Um teste que trava o comportamento sem a ADR que o explica deixaria a
        # próxima pessoa achando que é acidente.
        adr = (Path(__file__).resolve().parent.parent
               / "docs/adr/0011-private-artifacts-can-be-published-under-an-alias.md")
        self.assertIn("root commit SHA", adr.read_text(encoding="utf-8"))
