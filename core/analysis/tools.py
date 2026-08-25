"""Tools an Artifact was built with — a language, a framework.

Manifest and extension markers only. Nothing here reads code semantics; that is
deferred to v0.3, and v0.1 must not pretend otherwise.
"""

from __future__ import annotations

from pathlib import Path

from core.analysis.evidence import KIND_FILE_EXTENSION, KIND_MANIFEST, evidence

# Marcadores de manifesto: presença do arquivo é prova direta da Tool.
BY_MANIFEST = {
    "pyproject.toml": "Python",
    "requirements.txt": "Python",
    "setup.py": "Python",
    "package.json": "JavaScript",
    "tsconfig.json": "TypeScript",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "pom.xml": "Java",
    "build.gradle": "Java",
    "Package.swift": "Swift",
    "mix.exs": "Elixir",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker",
}

BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".rs": "Rust",
    ".go": "Go",
    ".rb": "Ruby",
    ".php": "PHP",
    ".java": "Java",
    ".swift": "Swift",
    ".ex": "Elixir",
    ".c": "C",
    ".cpp": "C++",
    ".sh": "Shell",
    ".sql": "SQL",
}

# Uma Tool só é reivindicada por extensão a partir daqui, para um único arquivo
# solto não virar "sei esta linguagem".
MINIMUM_FILES_FOR_EXTENSION = 2


def detect(paths: list[str]) -> list[dict]:
    """Tools observed in a tracked file list, each carrying its evidence."""
    found: dict[str, dict] = {}

    for path in paths:
        name = Path(path).name
        tool = BY_MANIFEST.get(name)
        if tool:
            found[tool] = {"name": tool, "evidence": evidence(KIND_MANIFEST, path)}

    counts: dict[str, int] = {}
    for path in paths:
        tool = BY_EXTENSION.get(Path(path).suffix)
        if tool:
            counts[tool] = counts.get(tool, 0) + 1
    for tool, count in counts.items():
        if tool in found or count < MINIMUM_FILES_FOR_EXTENSION:
            continue
        found[tool] = {
            "name": tool,
            "evidence": evidence(KIND_FILE_EXTENSION, f"{count} files"),
        }

    return sorted(found.values(), key=lambda item: item["name"])
