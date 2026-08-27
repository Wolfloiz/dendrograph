"""Um `package.json` não pode derrubar o build inteiro.

O defeito apareceu na primeira varredura de um arquivo real: 97 Artifacts, e
`dendro build` morria em todos os modos com `CollidingLabels` entre
`@babel/cli` e `babel-cli`. O guard estava certo — são dois pacotes —, o id é
que apagava o escopo do npm e os empurrava para o mesmo nó. Nove colisões
assim vinham de um Artifact só, e nenhuma delas era do Author.

Restava uma nona, de outra natureza: `LiveScript` e `livescript`, dois pacotes
npm que diferem só na caixa. Foi contornada com um `[exclude]` até a demo de
`examples/` precisar daquele repositório — e uma exclusão que viaja no
repositório da ferramenta não é correção, é a colisão escrita em outro arquivo.
"""

import unittest

from core.graph import (
    CollidingLabels,
    GraphBuilder,
    dependency_id,
    dependency_name,
)


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


class EachRegistryDecidesWhenTwoNamesAreOnePackage(unittest.TestCase):
    """Uma regra só para os dois registros erra para um deles."""

    def test_npm_keeps_two_spellings_of_one_word_apart(self):
        # `LiveScript` foi publicado antes de o npm exigir minúsculas, e segue
        # sendo outro pacote. Foi esta colisão que forçou o `[exclude]`.
        self.assertNotEqual(
            dependency_id("npm", "LiveScript"), dependency_id("npm", "livescript")
        )

    def test_pypi_reads_the_two_spellings_as_one_project(self):
        self.assertEqual(
            dependency_id("pypi", "Django"), dependency_id("pypi", "django")
        )

    def test_pypi_follows_pep_503_on_the_separators_too(self):
        ids = {
            dependency_id("pypi", name)
            for name in ("zope.interface", "zope-interface", "zope_interface")
        }
        self.assertEqual(len(ids), 1, f"split into {ids}")

    def test_npm_does_not_follow_pep_503(self):
        self.assertNotEqual(
            dependency_id("npm", "socket.io"), dependency_id("npm", "socket-io")
        )

    def test_the_label_follows_the_same_rule_as_the_id(self):
        # Sem isto o guard derruba o build ao contrário: um id só, dois
        # rótulos, e a fusão correta acusada de ser uma colisão.
        builder = GraphBuilder()
        for written in ("Django", "django"):
            builder.node(
                dependency_id("pypi", written),
                "Dependency",
                dependency_name("pypi", written),
                ecosystem="pypi",
            )
        self.assertEqual(len(builder._nodes), 1)
        self.assertEqual(builder._nodes["dependency:pypi/django"]["label"], "django")

    def test_the_manifest_that_forced_the_exclude_now_builds(self):
        builder = GraphBuilder()
        for name in ("LiveScript", "livescript"):
            builder.node(
                dependency_id("npm", name),
                "Dependency",
                dependency_name("npm", name),
                ecosystem="npm",
            )
        self.assertEqual(len(builder._nodes), 2)


class TheGuardItselfStaysLoud(unittest.TestCase):
    """A correção é no id, não no guard: fundir em silêncio continua proibido."""

    def test_two_labels_on_one_dependency_id_are_still_refused(self):
        builder = GraphBuilder()
        builder.node("dependency:npm/x", "Dependency", "X")
        with self.assertRaises(CollidingLabels):
            builder.node("dependency:npm/x", "Dependency", "x")


if __name__ == "__main__":
    unittest.main()
