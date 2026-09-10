"""Who gets into a published build, and who stays out.

The store holds everything; these outputs are filtered at build time, never at
scan time (ADR-0002, ADR-0005). The rules here are deliberately slanted towards
withholding: an Artifact the Author never declared public stays out, and an
alias can only ever narrow what crosses, never widen it (FR-013, FR-028,
ADR-0011).

See `specs/001-git-collector/contracts/graph.md` (*Build modes*, *Aliased
Artifacts*).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from core import store

MODE_FULL = "full"

# Reexportado de `core.config`, e não redefinido: duas listas dos mesmos campos
# é uma lista que envelhece sozinha, e esta já tinha envelhecido — o valor aqui
# divergiu do que o config validava, sem quebrar teste nenhum, porque ninguém
# a lia. Um campo publicável a mais de um lado é um vazamento do outro.
from core.config import REVEAL_FIELDS  # noqa: F401

GENERATED_LABEL_PREFIX = "Private project"


@dataclass(frozen=True)
class Selection:
    """What one build contains, and what it deliberately leaves out."""

    included: list  # projected Artifacts this build renders
    withheld: list  # Artifacts omitted entirely, with the reason


def select(artifacts, *, config=None, mode: str = "public") -> Selection:
    """Decide which Artifacts a build of *mode* contains.

    - `[exclude].artifacts` wins over everything, in every mode: omission is a
      config line, the store keeps the data, deleting the line restores it
      (FR-008).
    - `full` includes everything else unchanged — it writes to
      `.dendro-local/`, which nothing deploys.
    - Published modes (`public`, `redacted`) include an Artifact when it was
      observed public, when it is named in `[publish].opt_in`, or when it has
      an alias. Everything else is withheld.
    - Visibility `unknown` is **not** public. A local scan that never observed
      a GitHub state must not default into a published site; the Author opts it
      in explicitly or aliases it.
    """
    excluded = set(config.excluded) if config else set()
    opt_in = set(config.opt_in) if config else set()
    aliases = {a.id: a for a in config.aliases} if config else {}

    generated = _generated_labels(
        [
            artifact.id
            for artifact in artifacts
            if artifact.id not in excluded
            and artifact.id not in opt_in
            and artifact.id in aliases
            and aliases[artifact.id].label is None
        ]
    )

    included: list = []
    withheld: list = []
    for artifact in artifacts:
        if artifact.id in excluded:
            continue

        if mode == MODE_FULL:
            included.append(_clear_projection(artifact))
            continue

        alias = aliases.get(artifact.id)
        if alias is not None and artifact.visibility != store.VISIBILITY_PUBLIC:
            included.append(_project(artifact, alias, generated.get(artifact.id)))
            continue

        if artifact.visibility == store.VISIBILITY_PUBLIC or artifact.id in opt_in:
            included.append(_clear_projection(artifact))
            continue

        reason = (
            "visibility unknown"
            if artifact.visibility == store.VISIBILITY_UNKNOWN
            else "private"
        )
        withheld.append((artifact, reason))

    return Selection(included=included, withheld=withheld)


def aggregate(withheld) -> dict | None:
    """Shape without names, for `redacted` mode (FR-013, ADR-0005).

    Counts, Tools and a date range over everything withheld. Never a name,
    never a locator — the aggregate exists to say "there is more" and nothing
    else about it.
    """
    if not withheld:
        return None
    tools: set[str] = set()
    years: list[int] = []
    for artifact, _reason in withheld:
        tools.update(tool["name"] for tool in artifact.tools)
        first = artifact.activity.get("first")
        last = artifact.activity.get("last")
        if first:
            years.append(int(first[:4]))
        if last:
            years.append(int(last[:4]))
    payload = {"count": len(withheld)}
    if tools:
        payload["tools"] = sorted(tools)
    if years:
        payload["first"] = str(min(years))
        payload["last"] = str(max(years))
    return {"private_withheld": payload}


def _project(artifact, alias, generated_label: str | None):
    """An aliased copy: label in, identifying material out (FR-028, ADR-0011).

    The projection sets `aliased` and `reveal` on the copy; the graph layer
    reads them to gate every remaining field. What survives here is the node,
    its dates, and exactly what `reveal` names — the graph strips the rest.
    """
    label = alias.label or generated_label
    projected = replace(
        artifact,
        name=label,
        description=None,
        content_hashes={},
    )
    # Campos de apresentação, não de observação: nunca serializados no store,
    # lidos apenas pela camada de grafo.
    projected.aliased = True
    projected.reveal = tuple(alias.reveal)
    return projected


def _clear_projection(artifact):
    """The same Artifact, guaranteed free of a previous projection."""
    plain = replace(artifact)
    plain.aliased = False
    plain.reveal = ()
    return plain


def _generated_labels(ids: list[str]) -> dict[str, str]:
    """`Private project N`, numbered from the sorted id, never discovery order.

    A newly scanned private Artifact must not renumber the others, or every
    rebuild dirties the published site's diff with renames (ADR-0011).
    """
    return {
        artifact_id: f"{GENERATED_LABEL_PREFIX} {number}"
        for number, artifact_id in enumerate(sorted(ids), start=1)
    }
