"""Where an Artifact came from — substantial shared material, never a guess.

`DERIVES_FROM` is one of only two inferred edges, and a false one is a false
claim about the Author's work: the lineage set is deliberately strict, and only
*several* identical authored files count as evidence (FR-012). Lockfiles,
generated output, dependencies and anything under 512 bytes never reach the
stored `content_hashes.authored_files`, so they can never produce an edge here.

Every candidate carries its confidence and the paths that prove it (SC-006).
"""

from __future__ import annotations

from core.analysis.evidence import (
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    KIND_PATH,
    evidence,
)

# Uma correspondência pode ser acidente; várias, de arquivos substanciais,
# praticamente não. Abaixo do mínimo nem candidato existe.
MINIMUM_SHARED_FILES = 3

# A partir do dobro do mínimo a sobreposição é grande demais para coincidência.
HIGH_CONFIDENCE_AT = MINIMUM_SHARED_FILES * 2


def _authored_index(artifact) -> dict[str, str] | None:
    files = artifact.content_hashes.get("authored_files")
    if not files:
        return None
    return {entry["hash"]: entry["path"] for entry in files}


def _older_first(artifact):
    """Order for the older → newer orientation, stable when dates tie or vanish."""
    first = artifact.activity.get("first")
    # Sem data observada o Artifact vai para o fim: descendência é sobre tempo,
    # e quem não tem tempo observado não pode ser o mais antigo com segurança.
    return (first is None, first or "", artifact.id)


def candidates(artifacts) -> list[dict]:
    """Candidate `DERIVES_FROM` edges over the Artifacts of one archive.

    Each is `{"from", "to", "confidence", "evidence"}`, oriented older → newer
    by first observed activity, ties broken on the id so two runs agree. These
    are proposals for the graph (T078), not Author-confirmed relationships:
    `SUCCEEDS` is declared in config and never appears here (FR-011).
    """
    indexed = []
    for artifact in artifacts:
        index = _authored_index(artifact)
        if index:
            indexed.append((artifact, index))

    proposed = []
    ordered = sorted(indexed, key=lambda pair: _older_first(pair[0]))
    for position, (older, older_files) in enumerate(ordered):
        for newer, newer_files in ordered[position + 1:]:
            if older.id == newer.id:
                continue
            shared_hashes = set(older_files) & set(newer_files)
            if len(shared_hashes) < MINIMUM_SHARED_FILES:
                continue
            paths = sorted(older_files[digest] for digest in shared_hashes)
            confidence = (
                CONFIDENCE_HIGH
                if len(shared_hashes) >= HIGH_CONFIDENCE_AT
                else CONFIDENCE_MEDIUM
            )
            proposed.append(
                {
                    "from": older.id,
                    "to": newer.id,
                    "confidence": confidence,
                    "evidence": [evidence(KIND_PATH, path) for path in paths],
                }
            )
    # Ordem determinística como o resto do grafo: só mudança real suja diffs.
    return sorted(proposed, key=lambda c: (c["from"], c["to"]))
