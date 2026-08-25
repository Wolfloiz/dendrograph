"""Third-party work an Artifact reuses — never authored by the Author.

Distinct from Tools: `requests` is a Dependency, Python is the Tool it is
written for (FR-022).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from core.analysis.evidence import KIND_MANIFEST, evidence

_REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9._-]+)\s*(?:[=<>!~]=?\s*([^;#\s]+))?")


def _pypi_from_requirements(text: str) -> list[tuple[str, str | None]]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        match = _REQUIREMENT.match(line)
        if match:
            out.append((match.group(1), match.group(2)))
    return out


def _npm_from_package_json(text: str) -> list[tuple[str, str | None]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    out = []
    for section in ("dependencies", "devDependencies"):
        for name, version in (data.get(section) or {}).items():
            out.append((name, version if isinstance(version, str) else None))
    return out


PARSERS = {
    "requirements.txt": ("pypi", _pypi_from_requirements),
    "package.json": ("npm", _npm_from_package_json),
}


def detect(repository: Path | str, paths: list[str]) -> list[dict]:
    """Dependencies read from the manifests present in a repository."""
    repository = Path(repository)
    found: dict[tuple[str, str], dict] = {}
    for path in paths:
        parser = PARSERS.get(Path(path).name)
        if parser is None:
            continue
        ecosystem, parse = parser
        absolute = repository / path
        if not absolute.is_file():
            continue
        try:
            text = absolute.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name, version in parse(text):
            found[(ecosystem, name)] = {
                "name": name,
                "ecosystem": ecosystem,
                "version": version,
                "evidence": evidence(KIND_MANIFEST, path),
            }
    return sorted(found.values(), key=lambda item: (item["ecosystem"], item["name"]))
