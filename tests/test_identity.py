"""Identity is the heuristic everything else rests on. These assert against small
real repositories, unbundled from tests/fixtures/."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import identity  # noqa: E402
from core.config import Merge, Separate, parse  # noqa: E402
from support.fixtures import REWRITTEN_ROOT, SHARED_ROOT, FixtureCase  # noqa: E402


class RootCommitIdentity(FixtureCase):
    def test_identity_is_the_root_commit(self):
        repo = self.unbundle("multi-contributor")
        found = identity.resolve(repo)
        self.assertEqual(found.method, identity.METHOD_ROOT_COMMIT)
        self.assertEqual(found.value, SHARED_ROOT)
        self.assertEqual(found.artifact_id, f"root-{SHARED_ROOT}")

    def test_two_clones_on_two_paths_are_one_artifact(self):
        # SC-002: o mesmo projeto em três lugares produz exatamente um Artifact.
        first = identity.resolve(self.unbundle("multi-contributor", "here"))
        second = identity.resolve(self.unbundle("multi-contributor", "there"))
        third = identity.resolve(self.unbundle("divergent-a", "elsewhere"))
        self.assertEqual({first.artifact_id, second.artifact_id, third.artifact_id},
                         {f"root-{SHARED_ROOT}"})

    def test_a_fork_is_the_same_artifact_as_upstream(self):
        # Deliberado (ADR-0003): é o que dá detecção de fork de graça.
        upstream = identity.resolve(self.unbundle("multi-contributor"))
        fork = identity.resolve(self.unbundle("barely-touched-fork"))
        self.assertEqual(upstream.artifact_id, fork.artifact_id)

    def test_rewritten_history_looks_like_a_new_artifact(self):
        original = identity.resolve(self.unbundle("multi-contributor"))
        rewritten = identity.resolve(self.unbundle("rewritten-history"))
        self.assertNotEqual(original.artifact_id, rewritten.artifact_id)
        self.assertEqual(rewritten.value, REWRITTEN_ROOT)

    def test_the_content_hash_is_recorded_even_when_a_root_commit_exists(self):
        # É o que permite reconhecer depois um histórico reescrito (contracts).
        found = identity.resolve(self.unbundle("multi-contributor"))
        self.assertIsNotNone(found.fallback_content_hash)
        self.assertEqual(len(found.fallback_content_hash), 64)


class FallbackIdentity(FixtureCase):
    def test_a_repository_with_no_commits_falls_back_to_content(self):
        repo = self.empty_repository()
        # O arquivo precisa ser grande o bastante para contar como autorado.
        (repo / "main.py").write_text("x = 1\n" * 200)
        found = identity.resolve(repo)
        self.assertEqual(found.method, identity.METHOD_CONTENT_HASH)
        self.assertTrue(found.artifact_id.startswith("content-"))

    def test_the_fallback_is_stable_across_copies(self):
        first = self.empty_repository("a")
        (first / "main.py").write_text("x = 1\n" * 200)
        second = self.empty_repository("b")
        (second / "main.py").write_text("x = 1\n" * 200)
        self.assertEqual(identity.resolve(first).value, identity.resolve(second).value)

    def test_no_commits_and_no_files_is_unidentifiable_not_random(self):
        with self.assertRaises(identity.Unidentifiable):
            identity.resolve(self.bare_repository())


class FileSets(FixtureCase):
    def test_dependency_directories_are_out_of_both_sets(self):
        self.assertFalse(identity.is_identifying("node_modules/left-pad/index.js"))
        self.assertFalse(identity.is_identifying("vendor/thing.go"))
        self.assertFalse(identity.is_authored("node_modules/left-pad/index.js", 9999))

    def test_lockfiles_identify_but_do_not_prove_lineage(self):
        # Um lockfile é conteúdo rastreado estável — bom para identidade;
        # comum demais entre projetos — inútil como prova de descendência.
        self.assertTrue(identity.is_identifying("package-lock.json"))
        self.assertFalse(identity.is_authored("package-lock.json", 9999))

    def test_small_files_identify_but_do_not_prove_lineage(self):
        self.assertTrue(identity.is_identifying("main.py"))
        self.assertFalse(identity.is_authored("main.py", 10))
        self.assertTrue(identity.is_authored("main.py", 512))

    def test_a_repository_of_only_small_files_still_has_an_identity(self):
        # O defeito que separar os conjuntos conserta: antes, um repositório
        # de arquivos pequenos saía sem identidade nenhuma.
        repo = self.unbundle("multi-contributor")
        self.assertIsNotNone(identity.content_hash(repo))

    def test_the_lineage_set_is_a_subset_of_the_identity_set(self):
        repo = self.unbundle("multi-contributor")
        identifying = {row[0] for row in identity.identifying_files(repo)}
        authored = {row[0] for row in identity.authored_files(repo)}
        self.assertTrue(authored < identifying)
        self.assertIn("engine.py", authored)
        self.assertIn("main.py", identifying)
        self.assertNotIn("main.py", authored)


class Overrides(unittest.TestCase):
    def test_a_merge_folds_ids_into_the_first_one_listed(self):
        config = parse({"identity": {"merge": [{"ids": ["root-aaa", "root-bbb"]}]}})
        self.assertEqual(identity.apply_overrides("root-bbb", config), "root-aaa")
        self.assertEqual(identity.apply_overrides("root-aaa", config), "root-aaa")

    def test_an_unmentioned_id_is_untouched(self):
        config = parse({"identity": {"merge": [{"ids": ["root-aaa", "root-bbb"]}]}})
        self.assertEqual(identity.apply_overrides("root-ccc", config), "root-ccc")

    def test_a_separation_gives_the_named_locator_its_own_id(self):
        config = parse(
            {
                "identity": {
                    "separate": [{"id": "root-aaa", "locator": "https://x/fork"}]
                }
            }
        )
        split = identity.separated_id("root-aaa", "https://x/fork", config)
        self.assertNotEqual(split, "root-aaa")
        self.assertTrue(split.startswith("root-aaa-"))
        # A origem não declarada continua sendo o Artifact original.
        self.assertEqual(
            identity.separated_id("root-aaa", "https://x/upstream", config), "root-aaa"
        )

    def test_a_separation_is_deterministic(self):
        config = parse(
            {"identity": {"separate": [{"id": "root-a", "locator": "https://x/f"}]}}
        )
        self.assertEqual(
            identity.separated_id("root-a", "https://x/f", config),
            identity.separated_id("root-a", "https://x/f", config),
        )


if __name__ == "__main__":
    unittest.main()
