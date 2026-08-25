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

# (Technique, confidence, regex sobre o caminho POSIX rastreado).
# Cada regra existe porque o marcador é convenção estabelecida, não palpite.
RULES: list[tuple[str, str, re.Pattern]] = [
    ("Continuous Integration", CONFIDENCE_HIGH,
     re.compile(r"^\.github/workflows/.+\.ya?ml$|^\.gitlab-ci\.yml$|^\.circleci/")),
    ("Containerisation", CONFIDENCE_HIGH,
     re.compile(r"^Dockerfile$|^docker-compose\.ya?ml$")),
    ("Infrastructure as Code", CONFIDENCE_HIGH,
     re.compile(r"\.tf$|^ansible/|^helm/|^k8s/|^kubernetes/")),
    ("Automated Testing", CONFIDENCE_HIGH,
     re.compile(r"^tests?/|^spec/|_test\.[a-z]+$|\.test\.[a-z]+$|^test_[^/]+\.py$")),
    ("Database Migrations", CONFIDENCE_MEDIUM,
     re.compile(r"^migrations?/|^db/migrate/|^alembic/")),
    ("Documented Decisions", CONFIDENCE_HIGH,
     re.compile(r"^docs?/adr/|^docs?/decisions/")),
    ("Static Typing", CONFIDENCE_MEDIUM,
     re.compile(r"^tsconfig\.json$|^mypy\.ini$|^py\.typed$")),
    ("Pre-commit Hooks", CONFIDENCE_HIGH,
     re.compile(r"^\.pre-commit-config\.ya?ml$|^\.husky/")),
]


def detect(paths: list[str]) -> list[dict]:
    """Techniques inferred from a tracked file list.

    A Technique with no evidence is invalid and is never produced here: the
    first matching path becomes the pointer, so every claim can be traced back
    to the file that made it (SC-006).
    """
    found: dict[str, dict] = {}
    for path in paths:
        for name, confidence, pattern in RULES:
            if name in found or not pattern.search(path):
                continue
            found[name] = {
                "name": name,
                "confidence": confidence,
                "evidence": [evidence(KIND_PATH, path)],
            }
    return sorted(found.values(), key=lambda item: item["name"])
