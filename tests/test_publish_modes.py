"""Os três modos de build fazem coisas diferentes — e o full nunca chega a site/.

O guarda não é uma checagem no publish: é o diretório de saída, escolhido pelo
modo (contracts/graph.md). Quando `publish` recusa um build full, é segunda
linha de defesa, e segunda linha de defesa se testa.
"""

import contextlib
import io
import json

from cli import EXIT_FAILURE, main
from core import build
from core.config import Config
from tests.support import archives
from tests.support.fixtures import FixtureCase


class RedactedPublishesShapeWithoutNames(FixtureCase):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "archive"
        self.root.mkdir()
        archives.write(self.root, archives.private(), archives.public())
        self.payload = build.build(
            self.root, mode="redacted", config=Config(publish_mode="redacted")
        )

    def test_the_aggregate_counts_what_was_withheld(self):
        withheld = self.payload["aggregates"]["private_withheld"]
        self.assertEqual(withheld["count"], 1)
        self.assertIn("Rust", withheld["tools"])
        self.assertEqual(withheld["first"], "2021")
        self.assertEqual(withheld["last"], "2023")

    def test_the_aggregate_carries_no_name(self):
        blob = json.dumps(self.payload)
        for secret in (archives.CLIENT_NAME, archives.PRIVATE_ID):
            self.assertNotIn(secret, blob)

    def test_public_mode_has_no_aggregate(self):
        # O agregado só existe em redacted: em public ele diria a um visitante
        # que trabalho privado existiu, o que já é mais do que deve saber.
        payload = build.build(self.root, mode="public")
        self.assertNotIn("aggregates", payload)


class FullBuildNeverReachesSite(FixtureCase):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "archive"
        self.root.mkdir()

    def test_a_full_build_writes_elsewhere_and_includes_everything(self):
        archives.write(self.root, archives.private())
        build.build(self.root, mode="full")
        self.assertFalse(build.output_dir(self.root, "public").exists())
        local = build.output_dir(self.root, "full") / "graph.json"
        payload = json.loads(local.read_text(encoding="utf-8"))
        ids = {node["id"] for node in payload["nodes"]}
        self.assertIn(archives.PRIVATE_ID, ids)


class PublishRefusesAFullBuild(FixtureCase):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "archive"
        self.root.mkdir()

    def test_publish_refuses_when_the_site_declares_full(self):
        # Isto não deveria ser possível por construção. A checagem existe
        # porque errar aqui custa uma quebra de NDA, não uma reconstrução.
        site = build.output_dir(self.root, "public")
        site.mkdir(parents=True)
        (site / "graph.json").write_text(
            json.dumps({"build_mode": "full", "nodes": []}), encoding="utf-8"
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["publish", "--root", str(self.root)])
        self.assertEqual(code, EXIT_FAILURE)
        self.assertIn("refusing to publish", stderr.getvalue())
