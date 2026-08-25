"""Zero nomes privados em qualquer arquivo publicado, nas configurações padrão.

O teste independente da US4 (SC-004): um arquivo com um Artifact privado,
nenhuma configuração, um `dendro build`. Se qualquer byte do site souber o
nome do cliente — num nó, num índice, no sqlite, na prosa para agentes —
o padrão falha, e é no padrão que a promessa tem de valer.
"""

from core import build
from core.config import Config
from core.store import VISIBILITY_PRIVATE
from tests.support import archives
from tests.support.fixtures import FixtureCase

# Tudo pelo que um vazamento seria reconhecível.
SECRETS = (
    archives.CLIENT_NAME,
    "acme",  # o locator nomeia a organização
    archives.EVIDENCE_PATH,
    archives.CONTENT_HASH,
    "Internal tooling",  # a descrição
)


class TheDefaultBuildPublishesNothingPrivate(FixtureCase):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "archive"
        self.root.mkdir()
        archives.write(self.root, archives.private(), archives.public())

    def published_files(self):
        site = build.output_dir(self.root, "public")
        return sorted(p for p in site.iterdir() if p.is_file())

    def test_no_private_name_appears_in_any_published_file(self):
        build.build(self.root)
        for path in self.published_files():
            with self.subTest(file=path.name):
                blob = path.read_bytes()
                for secret in SECRETS:
                    self.assertNotIn(secret.encode(), blob)

    def test_the_private_artifact_is_not_in_the_graph_at_all(self):
        payload = build.build(self.root)
        ids = {node["id"] for node in payload["nodes"]}
        self.assertNotIn(archives.PRIVATE_ID, ids)

    def test_withholding_is_reported_never_silent(self):
        from core.report import RunReport

        report = RunReport()
        build.build(self.root, report=report)
        self.assertTrue(any(archives.CLIENT_NAME in line for line in report.withheld))

    def test_an_explicit_opt_in_publishes_by_name(self):
        # opt_in é a exceção declarada: o Author publicou AQUELE Artifact de
        # nome, um por vez. Não é o padrão, e precisa de uma linha no config.
        config = Config(opt_in=(archives.PRIVATE_ID,))
        payload = build.build(self.root, config=config)
        ids = {node["id"] for node in payload["nodes"]}
        self.assertIn(archives.PRIVATE_ID, ids)
