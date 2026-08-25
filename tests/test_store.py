"""The store accumulates. These tests guard the three ways it could quietly lose data:
a rewrite that churns the diff, a schema it should not have read, and a merge that
overwrites what an earlier run saw."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.store import (  # noqa: E402
    SCHEMA_VERSION,
    Artifact,
    Authorship,
    SchemaVersionError,
    Source,
    load_all,
    read,
    save,
    serialise,
    write,
)


def artifact(**overrides) -> Artifact:
    base = dict(
        id="root-aaa",
        identity={"method": "root_commit", "value": "aaa", "fallback_content_hash": None},
        name="thing",
        visibility="public",
        sources=[
            Source(
                kind="github",
                locator="https://github.com/a/thing",
                first_seen="2026-01-01",
                last_seen="2026-01-01",
                visibility="public",
            )
        ],
        activity={"first": "2019-03-11", "last": "2020-01-15"},
        authorship=[Authorship(author="alice@example.com", commits=2, lines_added=10)],
        tools=[{"name": "Python", "evidence": {"kind": "file_extension", "detail": "*.py"}}],
        last_seen="2026-01-01",
    )
    base.update(overrides)
    return Artifact(**base)


class Determinism(unittest.TestCase):
    def test_a_run_that_observed_nothing_rewrites_byte_identically(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(artifact(), tmp)
            first = (Path(tmp) / "store/artifacts/root-aaa.json").read_bytes()
            save(artifact(), tmp)
            second = (Path(tmp) / "store/artifacts/root-aaa.json").read_bytes()
        self.assertEqual(first, second)

    def test_keys_are_sorted_and_the_file_ends_in_a_newline(self):
        text = serialise(artifact())
        self.assertTrue(text.endswith("\n"))
        keys = [line.strip().split('"')[1] for line in text.splitlines() if line.startswith("  \"")]
        self.assertEqual(keys, sorted(keys))


class SchemaVersioning(unittest.TestCase):
    def test_unknown_version_is_refused_not_guessed_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "future.json"
            path.write_text('{"schema_version": 99, "id": "root-aaa"}')
            with self.assertRaises(SchemaVersionError) as caught:
                read(path)
        message = str(caught.exception)
        self.assertIn("99", message)
        self.assertIn(str(SCHEMA_VERSION), message)

    def test_a_refused_file_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "store/artifacts"
            directory.mkdir(parents=True)
            path = directory / "root-aaa.json"
            original = '{"schema_version": 99, "id": "root-aaa"}'
            path.write_text(original)
            with self.assertRaises(SchemaVersionError):
                save(artifact(), tmp)
            self.assertEqual(path.read_text(), original)


class Accumulation(unittest.TestCase):
    def test_merge_keeps_the_earliest_first_seen_and_the_latest_last_seen(self):
        stored = artifact()
        later = artifact(
            sources=[
                Source(
                    kind="github",
                    locator="https://github.com/a/thing",
                    first_seen="2026-06-01",
                    last_seen="2026-06-01",
                    visibility="public",
                )
            ],
            last_seen="2026-06-01",
        )
        merged = stored.merge(later)
        self.assertEqual(merged.sources[0].first_seen, "2026-01-01")
        self.assertEqual(merged.sources[0].last_seen, "2026-06-01")
        self.assertEqual(merged.last_seen, "2026-06-01")

    def test_a_second_source_is_added_not_substituted(self):
        stored = artifact()
        local = artifact(
            sources=[
                Source(
                    kind="local",
                    locator="/media/backup/thing",
                    first_seen="2026-02-01",
                    last_seen="2026-02-01",
                    visibility="private",
                )
            ]
        )
        merged = stored.merge(local)
        self.assertEqual(len(merged.sources), 2)
        self.assertEqual({s.kind for s in merged.sources}, {"github", "local"})

    def test_an_unobserved_field_is_not_blanked(self):
        stored = artifact(description="the real description")
        blind = artifact(description=None)
        self.assertEqual(stored.merge(blind).description, "the real description")

    def test_an_unreachable_source_is_not_a_deletion(self):
        stored = artifact()
        after = stored.mark_unreachable("github", "https://github.com/a/thing")
        self.assertFalse(after.sources[0].reachable)
        self.assertEqual(after.last_seen, "2026-01-01")  # não avança
        self.assertEqual(len(after.sources), 1)

    def test_divergent_clones_merge_rather_than_overwrite(self):
        # Mesma raiz, commits posteriores diferentes: as observações se somam.
        side_a = artifact(activity={"first": "2019-03-11", "last": "2021-04-01"})
        side_b = artifact(
            activity={"first": "2019-03-11", "last": "2021-05-01"},
            authorship=[Authorship(author="bob@example.com", commits=1)],
        )
        merged = side_a.merge(side_b)
        self.assertEqual(merged.activity, {"first": "2019-03-11", "last": "2021-05-01"})
        self.assertEqual({a.author for a in merged.authorship},
                         {"alice@example.com", "bob@example.com"})

    def test_authorship_counts_never_shrink(self):
        stored = artifact(authorship=[Authorship(author="alice@example.com", commits=412)])
        partial = artifact(authorship=[Authorship(author="alice@example.com", commits=3)])
        self.assertEqual(stored.merge(partial).authorship[0].commits, 412)

    def test_visibility_takes_the_most_recent_observation_not_the_most_permissive(self):
        stored = artifact()
        turned_private = artifact(
            sources=[
                Source(
                    kind="github",
                    locator="https://github.com/a/thing",
                    first_seen="2026-01-01",
                    last_seen="2026-09-01",
                    visibility="private",
                )
            ],
            last_seen="2026-09-01",
        )
        self.assertEqual(stored.merge(turned_private).visibility, "private")

    def test_visibility_does_not_decay_to_public_when_nothing_is_observed(self):
        stored = artifact(visibility="private", sources=[])
        self.assertEqual(stored.merge(artifact(sources=[])).visibility, "private")

    def test_an_artifact_survives_its_source_disappearing(self):
        with tempfile.TemporaryDirectory() as tmp:
            save(artifact(), tmp)
            stored = load_all(tmp)[0]
            save(stored.mark_unreachable("github", "https://github.com/a/thing"), tmp)
            survivors = load_all(tmp)
        self.assertEqual(len(survivors), 1)
        self.assertEqual(survivors[0].id, "root-aaa")
        self.assertEqual(survivors[0].last_seen, "2026-01-01")


if __name__ == "__main__":
    unittest.main()
