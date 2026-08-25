"""SC-002: the same project present in several locations produces exactly one Artifact."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from collectors.git import scan  # noqa: E402
from core import store  # noqa: E402
from support.fixtures import FixtureCase  # noqa: E402


class Deduplication(FixtureCase):
    def archive(self) -> Path:
        return self.tmp / "archive"

    def scan_into_store(self, fixture: str, as_name: str, seen: str = "2026-08-25"):
        repository = self.unbundle(fixture, as_name)
        observed = scan.observe(
            repository,
            kind="local",
            locator=str(repository),
            visibility="public",
            seen=seen,
        )
        store.save(observed, self.archive())
        return observed

    def test_the_same_project_on_three_paths_is_one_artifact(self):
        self.scan_into_store("multi-contributor", "disk-one")
        self.scan_into_store("multi-contributor", "disk-two")
        self.scan_into_store("multi-contributor", "disk-three")
        stored = store.load_all(self.archive())
        self.assertEqual(len(stored), 1)
        self.assertEqual(len(stored[0].sources), 3)

    def test_a_fork_does_not_inflate_the_artifact_count(self):
        # Mesma raiz que o upstream, logo o mesmo Artifact (ADR-0003).
        self.scan_into_store("multi-contributor", "upstream")
        self.scan_into_store("barely-touched-fork", "fork")
        self.assertEqual(len(store.load_all(self.archive())), 1)

    def test_a_barely_touched_fork_shows_negligible_authorship(self):
        from collectors.git import authorship

        self.scan_into_store("barely-touched-fork", "fork")
        stored = store.load_all(self.archive())[0]
        carol = authorship.share(stored.authorship, ("carol@example.com",))
        alice = authorship.share(stored.authorship, ("alice@example.com",))
        self.assertLess(carol, 0.1)
        self.assertGreater(alice, 0.5)

    def test_divergent_clones_are_one_artifact_with_both_observations(self):
        self.scan_into_store("divergent-a", "side-a")
        self.scan_into_store("divergent-b", "side-b")
        stored = store.load_all(self.archive())
        self.assertEqual(len(stored), 1)
        # Nenhuma das duas sobrescreveu a outra em silêncio.
        self.assertEqual(stored[0].activity["last"], "2021-05-01")
        self.assertEqual(len(stored[0].sources), 2)

    def test_rewritten_history_is_a_separate_artifact_the_author_can_merge(self):
        from core.config import parse
        from core.identity import apply_overrides

        original = self.scan_into_store("multi-contributor", "original")
        rewritten = self.scan_into_store("rewritten-history", "rewritten")
        self.assertEqual(len(store.load_all(self.archive())), 2)

        config = parse(
            {"identity": {"merge": [{"ids": [original.id, rewritten.id]}]}}
        )
        self.assertEqual(apply_overrides(rewritten.id, config), original.id)

    def test_an_unidentifiable_repository_is_reported_not_stored(self):
        from core.identity import Unidentifiable

        with self.assertRaises(Unidentifiable):
            scan.observe(self.bare_repository(), kind="local", locator="/nowhere")
        self.assertEqual(store.load_all(self.archive()), [])
