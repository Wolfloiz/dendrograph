"""Um `package.json` não pode derrubar o build inteiro.

O defeito apareceu na primeira varredura de um arquivo real: 97 Artifacts, e
`dendro build` morria em todos os modos com `CollidingLabels` entre
`@babel/cli` e `babel-cli`. O guard estava certo — são dois pacotes —, o id é
que apagava o escopo do npm e os empurrava para o mesmo nó. Nove colisões
assim vinham de um Artifact só, e nenhuma delas era do Author.
"""

import unittest

from core.graph import CollidingLabels, GraphBuilder, dependency_id


class AScopedPackageIsNotItsUnscopedNamesake(unittest.TestCase):
    def test_the_scope_survives_the_id(self):
        self.assertNotEqual(
            dependency_id("npm", "@babel/cli"), dependency_id("npm", "babel-cli")
        )

    def test_two_packages_under_one_scope_stay_apart(self):
        self.assertNotEqual(
            dependency_id("npm", "@babel/cli"), dependency_id("npm", "@babel/core")
        )

    def test_the_same_name_under_two_scopes_stays_apart(self):
        self.assertNotEqual(
            dependency_id("npm", "@babel/core"), dependency_id("npm", "@types/core")
        )

    def test_an_ordinary_name_keeps_a_readable_id(self):
        self.assertEqual(dependency_id("pypi", "flask"), "dependency:pypi/flask")
        self.assertEqual(dependency_id("npm", "@babel/cli"), "dependency:npm/@babel/cli")

    def test_the_ecosystem_still_separates_two_registries(self):
        self.assertNotEqual(
            dependency_id("npm", "requests"), dependency_id("pypi", "requests")
        )

    def test_a_name_the_slug_empties_is_derived_rather_than_collapsed(self):
        # Sem isto, todo nome sem letra latina cai em `dependency:npm/` e a
        # segunda ocorrência derruba o build — o mesmo defeito, outra porta.
        ids = {dependency_id("npm", name) for name in ("中文包", "日本語", "!!!")}
        self.assertEqual(len(ids), 3, f"collapsed into {ids}")

    def test_the_manifest_that_broke_the_build_now_builds(self):
        builder = GraphBuilder()
        for name in ("@babel/cli", "babel-cli", "@babel/core", "babel-core"):
            builder.node(dependency_id("npm", name), "Dependency", name, ecosystem="npm")
        self.assertEqual(len(builder._nodes), 4)


class TheGuardItselfStaysLoud(unittest.TestCase):
    """A correção é no id, não no guard: fundir em silêncio continua proibido."""

    def test_two_labels_on_one_dependency_id_are_still_refused(self):
        builder = GraphBuilder()
        builder.node("dependency:npm/x", "Dependency", "X")
        with self.assertRaises(CollidingLabels):
            builder.node("dependency:npm/x", "Dependency", "x")


if __name__ == "__main__":
    unittest.main()
