"""How an Artifact was built — always with a confidence and the evidence behind it.

Dependency manifests and directory conventions only, where a match is genuinely
reliable. Precision beats coverage: ten Techniques defensible in an interview
beat eighty needing apology (Principle V).

Never asserted: quality, complexity, or whether a person or a model wrote it.
Those are refused outright, not merely unimplemented (FR-015).
"""

from __future__ import annotations

import re

from core.analysis.evidence import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, KIND_PATH, evidence
from core.identity import is_identifying

# `(^|/)` e não `^`: um repositório com `backend/` e `frontend/` é invisível
# para uma âncora de raiz, e essa é a forma da maioria. Medido em 104
# repositórios reais: `Database Migrations` existia na tabela e nunca disparou
# uma vez, porque `^migrations?/` não vê `backend/migrations/`.
#
# A âncora também protegia por acidente contra `node_modules/x/test/`. Essa
# guarda agora é explícita, em `detect`, e não um efeito colateral do `^`.
ROOTED = "(^|/)"

# (Technique, confidence, regex sobre o caminho POSIX rastreado).
# Cada regra existe porque o marcador é convenção estabelecida, não palpite.
RULES: list[tuple[str, str, re.Pattern]] = [
    ("Continuous Integration", CONFIDENCE_HIGH,
     re.compile(rf"{ROOTED}\.github/workflows/[^/]+\.ya?ml$"
                rf"|{ROOTED}\.gitlab-ci\.yml$|{ROOTED}\.circleci/")),
    ("Containerisation", CONFIDENCE_HIGH,
     re.compile(rf"{ROOTED}Dockerfile(\.[A-Za-z0-9_-]+)?$"
                rf"|{ROOTED}(docker-)?compose\.ya?ml$")),
    ("Infrastructure as Code", CONFIDENCE_HIGH,
     re.compile(rf"\.tf$|{ROOTED}ansible/|{ROOTED}helm/|{ROOTED}k8s/|{ROOTED}kubernetes/")),
    # `__tests__/` é a convenção do Jest, `.spec.` a do Jasmine e do Angular,
    # `_spec.` a do RSpec. Nenhuma delas casava, e todas são tão inequívocas
    # quanto um diretório `tests/`.
    ("Automated Testing", CONFIDENCE_HIGH,
     re.compile(rf"{ROOTED}tests?/|{ROOTED}__tests__/|{ROOTED}spec/"
                rf"|_test\.[a-z]+$|\.test\.[a-z]+$"
                rf"|_spec\.[a-z]+$|\.spec\.[a-z]+$"
                rf"|{ROOTED}test_[^/]+\.py$")),
    ("Database Migrations", CONFIDENCE_MEDIUM,
     re.compile(rf"{ROOTED}migrations?/|{ROOTED}db/migrate/|{ROOTED}alembic/")),
    ("Documented Decisions", CONFIDENCE_HIGH,
     re.compile(rf"{ROOTED}docs?/adr/|{ROOTED}docs?/decisions/")),
    ("Static Typing", CONFIDENCE_MEDIUM,
     re.compile(rf"{ROOTED}tsconfig\.json$|{ROOTED}mypy\.ini$|{ROOTED}py\.typed$")),
    ("Pre-commit Hooks", CONFIDENCE_HIGH,
     re.compile(rf"{ROOTED}\.pre-commit-config\.ya?ml$|{ROOTED}\.husky/")),
    # A tabela nomeava sete técnicas e nenhuma delas era esta, embora um
    # arquivo de configuração de linter não signifique outra coisa.
    ("Linting", CONFIDENCE_HIGH,
     re.compile(rf"{ROOTED}\.eslintrc(\.[a-z]+)?$|{ROOTED}eslint\.config\.[a-z]+$"
                rf"|{ROOTED}\.flake8$|{ROOTED}\.?ruff\.toml$|{ROOTED}\.pylintrc$"
                rf"|{ROOTED}\.rubocop\.yml$|{ROOTED}\.golangci\.ya?ml$"
                rf"|{ROOTED}\.stylelintrc(\.[a-z]+)?$")),
    # Só marcadores que não significam outra coisa. `.nvmrc` e `.tool-versions`
    # ficaram de fora de propósito: fixam uma versão, que é conveniência tanto
    # quanto reprodutibilidade, e precisão vale mais que cobertura aqui.
    ("Reproducible Environments", CONFIDENCE_HIGH,
     re.compile(rf"{ROOTED}flake\.nix$|{ROOTED}shell\.nix$|{ROOTED}\.devcontainer/"
                rf"|{ROOTED}Vagrantfile$")),
]


def detect(paths: list[str]) -> list[dict]:
    """Techniques inferred from a tracked file list.

    A Technique with no evidence is invalid and is never produced here: the
    first matching path becomes the pointer, so every claim can be traced back
    to the file that made it (SC-006).

    Vendored trees are dropped first: a dependency's own test directory says
    what its author did, not what this Artifact's did.
    """
    found: dict[str, dict] = {}
    for path in paths:
        # `node_modules/left-pad/test/` não é teste do Author, é teste de
        # outra pessoa que veio junto. Enquanto as regras começavam em `^` a
        # âncora escondia isso; sem ela, a guarda tem que ser dita.
        if not is_identifying(path):
            continue
        for name, confidence, pattern in RULES:
            if name in found or not pattern.search(path):
                continue
            found[name] = {
                "name": name,
                "confidence": confidence,
                "evidence": [evidence(KIND_PATH, path)],
            }
    return sorted(found.values(), key=lambda item: item["name"])
