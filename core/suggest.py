"""Proposals the Author confirms, or does not. Nothing here creates anything.

The machine proposes, the Author disposes (ADR-0009, Principle I). Every
suggestion is printed as the exact config line that would confirm it, so
accepting one is a copy and a paste and rejecting one is doing nothing. An
Artifact with an unanswered suggestion stays usable and ungrouped — nothing in
the archive blocks awaiting an answer (FR-021).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# Uma Collection candidata precisa de mais de uma coincidência para ser dita em
# voz alta; abaixo disso a sugestão é ruído que o Author aprende a ignorar, e um
# fluxo de confirmação que as pessoas ignoram é pior que não existir.
MINIMUM_COLLECTION_SIZE = 3

# Uma sucessão só é proposta quando o mais novo começa depois de o mais velho
# parar. Projetos sobrepostos no tempo são trabalho paralelo, não uma sequência.
MAXIMUM_SUCCESSION_GAP_DAYS = 730


@dataclass(frozen=True)
class Suggestion:
    kind: str          # "succeeds" | "collection" | "identity-merge"
    summary: str       # o que se está afirmando, em prosa
    because: str       # a evidência, para o Author poder discordar
    config_line: str   # exatamente o que confirma isto

    def render(self) -> str:
        return f"{self.summary}\n    because: {self.because}\n    {self.config_line}"


@dataclass
class Proposals:
    succeeds: list[Suggestion] = field(default_factory=list)
    collections: list[Suggestion] = field(default_factory=list)
    identity_merges: list[Suggestion] = field(default_factory=list)

    @property
    def all(self) -> list[Suggestion]:
        return self.succeeds + self.collections + self.identity_merges

    def render(self) -> str:
        if not self.all:
            return (
                "Nothing to propose. Every relationship the archive can see is either "
                "already confirmed or too weak to be worth your attention."
            )
        out = []
        for heading, items in (
            ("Candidate successions (SUCCEEDS)", self.succeeds),
            ("Candidate Collections", self.collections),
            ("Candidate identity merges", self.identity_merges),
        ):
            if not items:
                continue
            out.append(f"{heading}: {len(items)}")
            out.append("")
            for item in items:
                out.append(f"  {item.render()}")
                out.append("")
        out.append(
            "Nothing above has been created. Paste a line into dendrograph.toml to "
            "confirm it; leave it and the Artifacts stay usable and ungrouped."
        )
        return "\n".join(out)


def _days_between(earlier: str, later: str) -> int:
    return (date.fromisoformat(later) - date.fromisoformat(earlier)).days


def _confirmed_pairs(config) -> set[tuple[str, str]]:
    if not config:
        return set()
    pairs = set()
    for collection in config.collections:
        for a in collection.artifacts:
            for b in collection.artifacts:
                if a != b:
                    pairs.add((a, b))
    return pairs


def successions(artifacts, config=None) -> list[Suggestion]:
    """Pairs where one project stopped and a same-named-ish one started.

    Deliberately narrow. A `SUCCEEDS` edge asserts a narrative about the
    Author's own history, and a wrong one is worse than a missing one.
    """
    confirmed = _confirmed_pairs(config)
    if config:
        confirmed |= {(s.earlier, s.later) for s in config.successions}
    candidates = [
        a for a in artifacts
        if a.activity.get("first") and a.activity.get("last") and a.name
    ]
    out = []
    for older in candidates:
        for newer in candidates:
            if older.id == newer.id or (older.id, newer.id) in confirmed:
                continue
            gap_start, gap_end = older.activity["last"], newer.activity["first"]
            if gap_end <= gap_start:
                continue
            gap = _days_between(gap_start, gap_end)
            if gap > MAXIMUM_SUCCESSION_GAP_DAYS:
                continue
            if not _names_rhyme(older.name, newer.name):
                continue
            shared = _shared_tools(older, newer)
            if not shared:
                continue
            out.append(
                Suggestion(
                    kind="succeeds",
                    summary=f"{newer.name!r} may succeed {older.name!r}",
                    because=(
                        f"{older.name} ended {gap_start}, {newer.name} began {gap_end} "
                        f"({gap} days later); the names share a stem and both use "
                        f"{', '.join(sorted(shared))}"
                    ),
                    config_line=(
                        "[[succession]]\n"
                        f'    earlier = "{older.id}"\n'
                        f'    later = "{newer.id}"\n'
                        f'    note = "{older.name} became {newer.name}"'
                    ),
                )
            )
    return sorted(out, key=lambda s: s.summary)


def _names_rhyme(a: str, b: str) -> bool:
    """A shared stem of at least four characters, in either direction."""
    a, b = a.lower(), b.lower()
    if a == b:
        return True
    stem = min(len(a), len(b))
    for size in range(stem, 3, -1):
        if a[:size] == b[:size]:
            return True
    return False


def _shared_tools(a, b) -> set[str]:
    return {t["name"] for t in a.tools} & {t["name"] for t in b.tools}


def collections(artifacts, config=None) -> list[Suggestion]:
    """Groups of Artifacts that share a Tool set narrow enough to mean something."""
    already = set()
    if config:
        for collection in config.collections:
            already |= set(collection.artifacts)

    by_signature: dict[tuple, list] = {}
    for artifact in artifacts:
        if artifact.id in already:
            continue
        signature = tuple(sorted(t["name"] for t in artifact.tools))
        if not signature:
            continue
        by_signature.setdefault(signature, []).append(artifact)

    out = []
    for signature, members in sorted(by_signature.items()):
        if len(members) < MINIMUM_COLLECTION_SIZE:
            continue
        # Uma assinatura de uma Tool só agrupa "tudo que é Python", o que não
        # é uma Collection, é um filtro que a pessoa já tem.
        if len(signature) < 2:
            continue
        ids = sorted(a.id for a in members)
        names = ", ".join(sorted(a.name or a.id for a in members)[:4])
        out.append(
            Suggestion(
                kind="collection",
                summary=f"{len(members)} Artifacts share exactly {', '.join(signature)}",
                because=f"{names}" + (" and others" if len(members) > 4 else ""),
                config_line=(
                    "[[collections]]\n"
                    f'    name = "{" + ".join(signature)}"  # rename this\n'
                    f"    artifacts = {ids!r}".replace("'", '"')
                ),
            )
        )
    return out


def identity_merges(artifacts, config=None) -> list[Suggestion]:
    """Artifacts whose authored files match though their root commits do not.

    A rewritten history — `filter-branch`, a squashed re-import — produces a new
    root commit for work that is not new. The content hash catches it; only the
    Author can say whether it is the same Artifact (FR-005).
    """
    declared = set()
    if config:
        for merge in config.merges:
            declared |= set(merge.ids)

    by_hash: dict[str, list] = {}
    for artifact in artifacts:
        digest = _lineage_digest(artifact)
        if not digest:
            continue
        by_hash.setdefault(digest, []).append(artifact)

    out = []
    for digest, members in sorted(by_hash.items()):
        if len(members) < 2:
            continue
        ids = sorted(a.id for a in members)
        if set(ids) <= declared:
            continue
        names = " and ".join(sorted(a.name or a.id for a in members))
        out.append(
            Suggestion(
                kind="identity-merge",
                summary=f"{names} may be one Artifact with a rewritten history",
                because=(
                    "different root commits, but their authored files hash identically "
                    f"({digest[:12]}…)"
                ),
                config_line=(
                    "[[identity.merge]]\n"
                    f"    ids = {ids!r}\n".replace("'", '"')
                    + '    reason = "history rewritten"  # say why, for the next reader'
                ),
            )
        )
    return out


def _lineage_digest(artifact) -> str | None:
    files = (artifact.content_hashes or {}).get("authored_files") or []
    if not files:
        return None
    import hashlib

    digest = hashlib.sha256()
    for entry in sorted(files, key=lambda f: f["path"]):
        digest.update(f"{entry['path']}\0{entry['size']}\0{entry['hash']}".encode())
    return digest.hexdigest()


def propose(artifacts, config=None) -> Proposals:
    """Everything worth asking the Author about. Creates nothing."""
    return Proposals(
        succeeds=successions(artifacts, config),
        collections=collections(artifacts, config),
        identity_merges=identity_merges(artifacts, config),
    )
