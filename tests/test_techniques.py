"""Onde uma Technique é vista, e como ela se chama.

Duas coisas separadas, no mesmo arquivo porque falham juntas.

A primeira: toda regra começava em `^`. Um repositório com `backend/` e
`frontend/` — que é a forma da maioria — ficava invisível, e `Database
Migrations` estava na tabela sem nunca ter disparado uma vez, porque
`^migrations?/` não vê `backend/migrations/`.

A segunda: nome de Technique é rótulo e id de nó, portanto superfície pública
(ADR-0001). `Static Typing` e `static-typing` seriam dois nós para uma coisa —
o mesmo defeito de identidade que derrubou um build inteiro por `@babel/cli`.
O conjunto é fechado, está no CONTEXT.md, e este arquivo prende um ao outro.
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.analysis import techniques  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def names_of(paths):
    return {found["name"] for found in techniques.detect(paths)}


class AMarkerCountsWhereverItSits(unittest.TestCase):
    """A âncora de raiz não era precisão, era a suposição de um repo raso."""

    def test_a_monorepo_is_not_invisible(self):
        found = names_of([
            "backend/migrations/0001_initial.py",
            "frontend/.eslintrc.json",
            "services/api/tests/test_health.py",
            "apps/web/tsconfig.json",
        ])
        self.assertEqual(
            found,
            {"Database Migrations", "Linting", "Automated Testing", "Static Typing"},
        )

    def test_the_marker_still_needs_a_path_boundary(self):
        # Sem `(^|/)` a busca viraria substring: `mytests/` não é `tests/`, e
        # `notsonic.tf` não é um plano do Terraform.
        self.assertEqual(names_of(["mytests/a.py"]), set())
        self.assertEqual(names_of(["src/refactoring/notes.md"]), set())

    def test_the_three_conventions_that_never_matched(self):
        # Jest põe os testes em `__tests__/`, Jasmine e Angular em `.spec.`,
        # RSpec em `_spec.`. Nenhum casava, e os três são tão inequívocos
        # quanto um diretório `tests/`.
        for path in ("src/__tests__/app.js", "src/app.spec.ts",
                     "spec/models/user_spec.rb"):
            self.assertEqual(names_of([path]), {"Automated Testing"}, path)

    def test_the_root_case_did_not_regress(self):
        self.assertEqual(
            names_of([".github/workflows/ci.yml", "Dockerfile", "tests/test_a.py"]),
            {"Continuous Integration", "Containerisation", "Automated Testing"},
        )


class VendoredWorkIsSomeoneElsesWork(unittest.TestCase):
    """A guarda era efeito colateral do `^`; agora é dita."""

    def test_a_dependencys_own_tests_are_not_the_authors(self):
        self.assertEqual(names_of(["node_modules/left-pad/test/index.js"]), set())

    def test_every_excluded_directory_is_dropped(self):
        for directory in ("node_modules", "vendor", "dist", "build", ".venv", "target"):
            self.assertEqual(
                names_of([f"{directory}/thing/Dockerfile"]), set(), directory
            )

    def test_the_same_marker_outside_a_vendored_tree_still_counts(self):
        self.assertEqual(names_of(["services/worker/Dockerfile"]), {"Containerisation"})


class TheTwoRulesThatWereMissing(unittest.TestCase):
    def test_a_linter_configuration_is_linting(self):
        for path in (".eslintrc.json", "eslint.config.mjs", ".flake8", "ruff.toml",
                     ".rubocop.yml", ".pylintrc", ".golangci.yml"):
            self.assertEqual(names_of([path]), {"Linting"}, path)

    def test_an_environment_declaration_is_reproducible_environments(self):
        for path in ("flake.nix", "shell.nix", ".devcontainer/devcontainer.json",
                     "Vagrantfile"):
            self.assertEqual(names_of([path]), {"Reproducible Environments"}, path)

    def test_a_pinned_version_alone_is_not_one(self):
        # `.nvmrc` e `.tool-versions` fixam versão, que é conveniência tanto
        # quanto reprodutibilidade. Precisão vale mais que cobertura aqui.
        self.assertEqual(names_of([".nvmrc", ".tool-versions"]), set())


class EveryClaimPointsAtTheFileThatMadeIt(unittest.TestCase):
    def test_the_evidence_is_the_matching_path(self):
        [found] = techniques.detect(["backend/migrations/0001_initial.py"])
        self.assertEqual(found["evidence"][0]["kind"], "path")
        self.assertEqual(
            found["evidence"][0]["detail"], "backend/migrations/0001_initial.py"
        )

    def test_a_technique_never_arrives_without_evidence(self):
        for found in techniques.detect(["Dockerfile", "tests/a_test.py", ".flake8"]):
            self.assertTrue(found["evidence"], found["name"])
            self.assertIn(found["confidence"], ("high", "medium"))


class TheNamesAreAClosedSet(unittest.TestCase):
    """CONTEXT.md e `RULES` não podem divergir em silêncio."""

    def documented(self):
        text = (ROOT / "CONTEXT.md").read_text(encoding="utf-8")
        block = text.split("**Technique names**:")[1].split("_Avoid_:")[0]
        return {
            row.split("|")[1].strip()
            for row in block.splitlines()
            if row.startswith("| ") and "---" not in row and "Marker" not in row
        }

    def test_the_table_lists_exactly_what_the_rules_produce(self):
        self.assertEqual({name for name, _, _ in techniques.RULES}, self.documented())

    def test_no_name_is_a_judgement(self):
        # "tem teste" é observável, "bem testado" é julgamento (Princípio V, FR-015).
        forbidden = re.compile(
            r"\b(good|bad|clean|modern|best|proper|quality|advanced|solid)\b",
            re.IGNORECASE,
        )
        for name, _, _ in techniques.RULES:
            self.assertIsNone(forbidden.search(name), name)

    def test_every_name_stands_alone_without_its_pointer(self):
        # Sob alias a Technique viaja sem a evidência (ADR-0011), então o nome
        # tem que significar alguma coisa sozinho.
        for name, _, _ in techniques.RULES:
            self.assertGreaterEqual(len(name.split()), 1)
            self.assertEqual(name, name.strip())
            self.assertTrue(name[0].isupper(), name)


if __name__ == "__main__":
    unittest.main()
