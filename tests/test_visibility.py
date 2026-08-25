"""A visibilidade é reavaliada da observação mais recente, e nunca decai para public.

FR-026 tem duas metades: a mudança remove o Artifact do output publicado E
tem nome no relatório. A outra direção importa tanto: uma origem que não
respondeu nesta execução preserva a última visibilidade conhecida — decair
para public é como o nome de um cliente sai.
"""

import contextlib
import io
import json

from cli import main
from core import build, privacy, store
from tests.support import archives
from tests.support.fixtures import FixtureCase


class TheMostRecentObservationWins(FixtureCase):
    def test_a_later_private_observation_overrides_an_earlier_public_one(self):
        observed = store.Artifact(
            id="root-x",
            identity={},
            sources=[store.Source(
                kind="github", locator="https://github.com/acme/client",
                first_seen="2026-01-01", last_seen="2026-01-01",
                visibility=store.VISIBILITY_PUBLIC,
            )],
        )
        fresh = store.Artifact(
            id="root-x",
            identity={},
            sources=[store.Source(
                kind="github", locator="https://github.com/acme/client",
                first_seen="2026-01-01", last_seen="2026-06-01",
                visibility=store.VISIBILITY_PRIVATE,
            )],
        )
        merged = observed.merge(fresh)
        self.assertEqual(merged.visibility, store.VISIBILITY_PRIVATE)

    def test_an_unreachable_source_keeps_its_last_known_visibility(self):
        known = store.Artifact(
            id="root-y",
            identity={},
            visibility=store.VISIBILITY_PRIVATE,
            sources=[store.Source(
                kind="local", locator="/media/backup/client",
                first_seen="2025-01-01", last_seen="2025-12-01",
                visibility=store.VISIBILITY_PRIVATE,
            )],
        )
        unreachable = known.mark_unreachable("local", "/media/backup/client")
        self.assertEqual(unreachable.visibility, store.VISIBILITY_PRIVATE)

    def test_unknown_never_becomes_public_by_default(self):
        # Um scan local que nunca observou estado nenhum não é público: é
        # desconhecido, e desconhecido fica de fora até o Author declarar.
        artifact = archives.artifact("root-z", visibility=store.VISIBILITY_UNKNOWN)
        selection = privacy.select([artifact])
        self.assertEqual([a.id for a in selection.included], [])


class TurningPrivateRemovesItFromTheNextPublish(FixtureCase):
    """O teste independente da US4, de ponta a ponta (FR-026)."""

    def setUp(self):
        super().setUp()
        self.root = self.tmp / "archive"
        self.root.mkdir()

    def _publish(self) -> str:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["publish", "--root", str(self.root)])
        self.assertEqual(code, 0)
        return stdout.getvalue()

    def _published_ids(self) -> set:
        payload = json.loads(
            (build.output_dir(self.root, "public") / "graph.json").read_text(encoding="utf-8")
        )
        return {node["id"] for node in payload["nodes"] if node["type"] == "Artifact"}

    def test_it_drops_out_and_is_named_in_the_report(self):
        artifact = archives.artifact("root-v1", name="once-public")
        archives.write(self.root, artifact)
        self._publish()
        self.assertIn("root-v1", self._published_ids())

        stored = store.load_all(self.root)[0]
        store.write(store.replace(stored, visibility=store.VISIBILITY_PRIVATE), self.root)

        output = self._publish()
        self.assertIn("once-public", output)
        self.assertIn("removed by a visibility change", output)
        self.assertNotIn("root-v1", self._published_ids())
