"""Um projeto em dois lugares é um Artifact com duas origens.

A identidade vem do commit raiz, não do caminho nem da URL (ADR-0003), então o
mesmo projeto clonado no disco e hospedado no GitHub converge para um registro
só — que carrega as duas origens em vez de uma sobrescrever a outra (US2 AS3).
"""

from collectors.git import scan
from core import store
from tests.support.fixtures import FixtureCase


class OneArtifactCarriesEverySourceItWasSeenIn(FixtureCase):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "archive"
        self.checkout = self.unbundle("multi-contributor")

    def observe_as(self, kind, locator, **kwargs):
        return scan.observe(
            self.checkout, kind=kind, locator=locator, **kwargs
        )

    def test_the_same_project_from_two_sources_is_one_artifact(self):
        store.save(self.observe_as("local", str(self.checkout)), self.root)
        store.save(
            self.observe_as(
                "github",
                "https://github.com/wolfloiz/multi-contributor",
                visibility=store.VISIBILITY_PUBLIC,
            ),
            self.root,
        )
        self.assertEqual(len(store.load_all(self.root)), 1)

    def test_it_carries_both_sources(self):
        store.save(self.observe_as("local", str(self.checkout)), self.root)
        store.save(
            self.observe_as("github", "https://github.com/wolfloiz/multi-contributor"),
            self.root,
        )
        artifact = store.load_all(self.root)[0]
        self.assertEqual(
            sorted(s.kind for s in artifact.sources), ["github", "local"]
        )

    def test_neither_source_overwrites_the_other(self):
        store.save(self.observe_as("local", str(self.checkout)), self.root)
        store.save(
            self.observe_as("github", "https://github.com/wolfloiz/multi-contributor"),
            self.root,
        )
        artifact = store.load_all(self.root)[0]
        locators = {s.locator for s in artifact.sources}
        self.assertIn(str(self.checkout), locators)
        self.assertIn("https://github.com/wolfloiz/multi-contributor", locators)

    def test_the_order_the_sources_arrive_in_does_not_matter(self):
        forward = self.tmp / "forward"
        backward = self.tmp / "backward"
        github = self.observe_as(
            "github", "https://github.com/wolfloiz/multi-contributor"
        )
        localy = self.observe_as("local", str(self.checkout))

        store.save(localy, forward)
        store.save(github, forward)
        store.save(github, backward)
        store.save(localy, backward)

        self.assertEqual(
            store.serialise(store.load_all(forward)[0]),
            store.serialise(store.load_all(backward)[0]),
        )

    def test_losing_the_local_copy_leaves_the_github_source_reachable(self):
        # Metade do ponto de guardar as duas: uma morre, a outra responde.
        store.save(self.observe_as("local", str(self.checkout)), self.root)
        store.save(
            self.observe_as("github", "https://github.com/wolfloiz/multi-contributor"),
            self.root,
        )
        artifact = store.load_all(self.root)[0]
        store.write(artifact.mark_unreachable("local", str(self.checkout)), self.root)

        artifact = store.load_all(self.root)[0]
        by_kind = {s.kind: s for s in artifact.sources}
        self.assertFalse(by_kind["local"].reachable)
        self.assertTrue(by_kind["github"].reachable)

    def test_a_visibility_seen_only_on_github_is_not_erased_by_a_local_scan(self):
        store.save(
            self.observe_as(
                "github",
                "https://github.com/wolfloiz/multi-contributor",
                visibility=store.VISIBILITY_PRIVATE,
                seen="2026-08-20",
            ),
            self.root,
        )
        # Um clone no disco não sabe dizer se o remoto é privado.
        store.save(
            self.observe_as("local", str(self.checkout), seen="2026-08-25"), self.root
        )
        self.assertEqual(store.load_all(self.root)[0].visibility, store.VISIBILITY_PRIVATE)


class TheLocalWalkFindsWhatIsThere(FixtureCase):
    def test_a_folder_of_repositories_is_discovered(self):
        from collectors.git import local

        folder = self.tmp / "drive"
        folder.mkdir()
        self.unbundle("multi-contributor", as_name="drive/alpha")
        self.unbundle("divergent-a", as_name="drive/beta")
        found = local.discover(folder)
        self.assertEqual(
            sorted(p.name for p in found.repositories), ["alpha", "beta"]
        )

    def test_a_repository_inside_a_repository_is_not_a_separate_artifact(self):
        # Código vendorado ou submódulo é trabalho de outra pessoa.
        from collectors.git import local

        outer = self.unbundle("multi-contributor", as_name="outer")
        self.unbundle("divergent-a", as_name="outer/vendor/inner")
        found = local.discover(self.tmp)
        self.assertEqual([p.name for p in found.repositories], [outer.name])

    def test_pointing_straight_at_a_repository_works(self):
        from collectors.git import local

        checkout = self.unbundle("multi-contributor")
        found = local.discover(checkout)
        self.assertEqual(found.repositories, [checkout.resolve()])

    def test_a_bare_repository_is_found(self):
        from collectors.git import local
        from tests.support.fixtures import _git

        folder = self.tmp / "server"
        folder.mkdir()
        source = self.unbundle("multi-contributor")
        _git("clone", "--quiet", "--bare", str(source), str(folder / "alpha.git"))
        found = local.discover(folder)
        self.assertEqual([p.name for p in found.repositories], ["alpha.git"])

    def test_a_missing_path_is_reported_not_raised(self):
        from collectors.git import local

        found = local.discover(self.tmp / "never-existed")
        self.assertEqual(found.repositories, [])
        self.assertTrue(found.unreachable)
        self.assertFalse(found.complete)

    def test_heavy_directories_are_not_walked(self):
        from collectors.git import local

        folder = self.tmp / "drive"
        (folder / "project" / "node_modules" / "dep").mkdir(parents=True)
        self.unbundle("multi-contributor", as_name="drive/project/node_modules/dep/pkg")
        found = local.discover(folder)
        self.assertEqual(found.repositories, [])
