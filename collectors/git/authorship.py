"""How much of an Artifact is the Author's own work.

Computed independently of identity: the root commit answers *which* Artifact
this is, these counts answer *how much of it is mine*. That separation is what
lets a repository count stay honest when it contains untouched forks
(FR-006, ADR-0003).
"""

from __future__ import annotations

from pathlib import Path

from collectors.git import plumbing
from core.store import Authorship


def _key(email: str) -> str:
    """A mesma normalização que `Authorship` aplica ao guardar.

    Contar por e-mail cru parte uma pessoa em duas linhas quando ela escreve a
    caixa diferente entre dois commits — `Marta9@example.com` e
    `marta9@example.com` —, e cada metade fica com metade das contagens. Numa
    varredura real as duas grafias saíram do mesmo arquivo.
    """
    return email.strip().lower()


def _chosen_name(spellings: dict[str, int] | None) -> str | None:
    """O nome que aquele endereço mais usou para assinar.

    Uma pessoa troca de nome ao longo dos anos e escreve o mesmo nome de dois
    jeitos. O mais frequente é estável entre varreduras, e o desempate é
    alfabético para que duas execuções nunca discordem.
    """
    if not spellings:
        return None
    return sorted(spellings.items(), key=lambda item: (-item[1], item[0]))[0][0]


def counts(repository: Path | str) -> list[Authorship]:
    """Per-author commits, lines and date span for one repository."""
    tallies: dict[str, dict] = {}
    # O nome vem junto porque é ele que o grafo publica: o endereço identifica,
    # mas publicar endereço é entregar endereço (ADR-0012). `plumbing.log` já
    # lia `%an` e o jogava fora.
    spellings: dict[str, dict[str, int]] = {}

    def blank() -> dict:
        return {"commits": 0, "added": 0, "deleted": 0, "first": None, "last": None}

    for commit in plumbing.log(repository):
        key = _key(commit.author_email)
        entry = tallies.setdefault(key, blank())
        entry["commits"] += 1
        date = commit.date[:10]
        entry["first"] = min(entry["first"] or date, date)
        entry["last"] = max(entry["last"] or date, date)
        written = (commit.author_name or "").strip()
        if written:
            seen = spellings.setdefault(key, {})
            seen[written] = seen.get(written, 0) + 1

    for email, added, deleted in plumbing.numstat(repository):
        entry = tallies.setdefault(_key(email), blank())
        entry["added"] += added
        entry["deleted"] += deleted

    return sorted(
        (
            Authorship(
                author=email,
                commits=entry["commits"],
                lines_added=entry["added"],
                lines_deleted=entry["deleted"],
                first=entry["first"],
                last=entry["last"],
                name=_chosen_name(spellings.get(email)),
            )
            for email, entry in tallies.items()
        ),
        key=lambda a: a.author,
    )


def share(entries: list[Authorship], emails: tuple[str, ...]) -> float:
    """The Author's proportion of an Artifact's authored material, 0 to 1.

    This is what reaches the graph. Commits and lines stay in the store, where
    the git collector wrote them — the graph does not know what a commit is
    (Principle V, contracts/graph.md).
    """
    if not entries:
        return 0.0
    weight: dict[str, int] = {}
    for a in entries:
        weight[a.author] = weight.get(a.author, 0) + a.commits + a.lines_added + a.lines_deleted
    total = sum(weight.values())
    if total == 0:
        return 0.0
    # `Authorship` normaliza o e-mail gravado; o configurado tem que combinar.
    configured = {e.strip().lower() for e in emails}
    mine = sum(value for author, value in weight.items() if author in configured)
    return round(mine / total, 4)


def activity(entries: list[Authorship]) -> dict:
    """Earliest and latest activity across every contributor."""
    firsts = [a.first for a in entries if a.first]
    lasts = [a.last for a in entries if a.last]
    span = {}
    if firsts:
        span["first"] = min(firsts)
    if lasts:
        span["last"] = max(lasts)
    return span
