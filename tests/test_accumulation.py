"""O arquivo sobrevive à origem que o alimentou.

O teste independente da US2: varrer uma pasta, apagá-la, reconstruir. Todo
Artifact visto antes continua lá, com o registro de quando foi visto pela
última vez (SC-003, FR-007). Sumir de uma origem é um estado observado, nunca
uma exclusão.
"""

import shutil

from collectors.git import scan
from core import graph, store
from core.report import RunReport
from tests.support.fixtures import FixtureCase


class TheArchiveOutlivesItsSources(FixtureCase):
    def setUp(self):
        super().setUp()
        self.folder = self.tmp / "drive"
        self.folder.mkdir()
        self.unbundle("multi-contributor", as_name="drive/alpha")
        self.unbundle("rewritten-history", as_name="drive/beta")
        self.root = self.tmp / "archive"

    def scan(self, dry_run=False) -> RunReport:
        return scan.scan_local(
            self.folder,
            self.root,
            dry_run=dry_run,
            progress=scan.Progress(enabled=False),
        )

    def stored(self):
        return {a.id: a for a in store.load_all(self.root)}

    def test_a_first_scan_stores_what_it_found(self):
        report = self.scan()
        self.assertEqual(len(report.added), 2)
        self.assertEqual(len(self.stored()), 2)

    def test_the_artifacts_survive_the_folder_being_deleted(self):
        self.scan()
        before = set(self.stored())
        shutil.rmtree(self.folder)
        self.scan()
        self.assertEqual(set(self.stored()), before)

    def test_a_deleted_folder_is_reported_unreachable_not_removed(self):
        self.scan()
        shutil.rmtree(self.folder)
        report = self.scan()
        self.assertTrue(report.unreachable)
        self.assertEqual(report.added, [])
        self.assertEqual(len(self.stored()), 2)

    def test_the_sources_are_flagged_unreachable_after_they_vanish(self):
        self.scan()
        shutil.rmtree(self.folder)
        self.scan()
        for artifact in self.stored().values():
            self.assertTrue(artifact.sources)
            self.assertFalse(any(s.reachable for s in artifact.sources))

    def test_when_it_was_last_seen_is_preserved(self):
        self.scan()
        seen = {a.id: a.last_seen for a in self.stored().values()}
        self.assertTrue(all(seen.values()))
        shutil.rmtree(self.folder)
        self.scan()
        # last_seen não avança: nada foi visto nesta execução (FR-007).
        self.assertEqual({a.id: a.last_seen for a in self.stored().values()}, seen)

    def test_the_graph_still_contains_them_after_the_drive_dies(self):
        self.scan()
        shutil.rmtree(self.folder)
        self.scan()
        payload = graph.build(store.load_all(self.root))
        artifacts = [n for n in payload["nodes"] if n["type"] == "Artifact"]
        self.assertEqual(len(artifacts), 2)

    def test_one_folder_disappearing_does_not_touch_another(self):
        # Uma varredura de ~/projects não diz nada sobre o HD externo.
        other = self.tmp / "elsewhere"
        other.mkdir()
        self.unbundle("divergent-a", as_name="elsewhere/gamma")
        scan.scan_local(other, self.root, progress=scan.Progress(enabled=False))
        self.scan()

        shutil.rmtree(self.folder)
        self.scan()

        by_locator = {
            s.locator: s for a in self.stored().values() for s in a.sources
        }
        elsewhere = [s for k, s in by_locator.items() if "elsewhere" in k]
        self.assertTrue(elsewhere)
        self.assertTrue(all(s.reachable for s in elsewhere))

    def test_a_source_that_comes_back_is_reachable_again(self):
        self.scan()
        moved = self.tmp / "moved"
        shutil.move(self.folder, moved)
        self.scan()
        shutil.move(moved, self.folder)
        self.scan()
        for artifact in self.stored().values():
            self.assertTrue(any(s.reachable for s in artifact.sources))

    def test_a_still_missing_source_is_reported_without_rewriting_it(self):
        self.scan()
        shutil.rmtree(self.folder)
        self.scan()
        before = {p.name: p.read_text() for p in (self.root / "store" / "artifacts").glob("*.json")}
        report = self.scan()
        after = {p.name: p.read_text() for p in (self.root / "store" / "artifacts").glob("*.json")}
        self.assertEqual(before, after, "a second miss rewrote the store")
        self.assertTrue(any("still missing" in u for u in report.unreachable))

    def test_a_dry_run_changes_nothing(self):
        self.scan()
        before = {p.name: p.read_text() for p in (self.root / "store" / "artifacts").glob("*.json")}
        shutil.rmtree(self.folder)
        self.scan(dry_run=True)
        after = {p.name: p.read_text() for p in (self.root / "store" / "artifacts").glob("*.json")}
        self.assertEqual(before, after)


class WhatCouldNotBeReachedIsReportedInTheGraph(FixtureCase):
    """FR-019: uma origem inalcançável aparece na saída, não some dela.

    Derivado do store e não da execução: um `build` não varreu nada, e "não
    consegui alcançar" é um estado que o store carrega entre execuções.
    """

    def setUp(self):
        super().setUp()
        self.folder = self.tmp / "drive"
        self.folder.mkdir()
        self.unbundle("multi-contributor", as_name="drive/alpha")
        self.root = self.tmp / "archive"
        scan.scan_local(self.folder, self.root, progress=scan.Progress(enabled=False))
        shutil.rmtree(self.folder)
        scan.scan_local(self.folder, self.root, progress=scan.Progress(enabled=False))
        self.artifacts = store.load_all(self.root)

    def test_a_rebuild_still_reports_it(self):
        payload = graph.build(self.artifacts)
        self.assertEqual(len(payload["unreachable_sources"]), 1)

    def test_a_published_build_withholds_the_local_path(self):
        # O caminho é a máquina do Author, não assunto de quem visita.
        payload = graph.build(self.artifacts, build_mode="public")
        row = payload["unreachable_sources"][0]
        self.assertEqual(row["kind"], "local")
        self.assertNotIn("locator", row)
        self.assertNotIn(str(self.tmp), json_text(payload))

    def test_the_authors_own_build_keeps_it(self):
        payload = graph.build(self.artifacts, build_mode="full")
        self.assertIn("locator", payload["unreachable_sources"][0])

    def test_a_github_locator_is_published_because_it_already_is_public(self):
        artifact = self.artifacts[0]
        artifact.sources.append(
            store.Source(
                kind="github",
                locator="https://github.com/wolfloiz/alpha",
                first_seen="2026-01-01",
                last_seen="2026-01-01",
                reachable=False,
            )
        )
        payload = graph.build([artifact], build_mode="public")
        github = [r for r in payload["unreachable_sources"] if r["kind"] == "github"]
        self.assertEqual(github[0]["locator"], "https://github.com/wolfloiz/alpha")

    def test_a_reachable_source_is_not_listed(self):
        folder = self.tmp / "other"
        folder.mkdir()
        self.unbundle("divergent-a", as_name="other/beta")
        root = self.tmp / "second"
        scan.scan_local(folder, root, progress=scan.Progress(enabled=False))
        payload = graph.build(store.load_all(root))
        self.assertEqual(payload["unreachable_sources"], [])


def json_text(payload) -> str:
    import json

    return json.dumps(payload)
