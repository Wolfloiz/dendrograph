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


def counts(repository: Path | str) -> list[Authorship]:
    """Per-author commits, lines and date span for one repository."""
    tallies: dict[str, dict] = {}

    for commit in plumbing.log(repository):
        entry = tallies.setdefault(
            commit.author_email,
            {"commits": 0, "added": 0, "deleted": 0, "first": None, "last": None},
        )
        entry["commits"] += 1
        date = commit.date[:10]
        entry["first"] = min(entry["first"] or date, date)
        entry["last"] = max(entry["last"] or date, date)

    for email, added, deleted in plumbing.numstat(repository):
        entry = tallies.setdefault(
            email, {"commits": 0, "added": 0, "deleted": 0, "first": None, "last": None}
        )
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
    weight = {a.author: a.commits + a.lines_added + a.lines_deleted for a in entries}
    total = sum(weight.values())
    if total == 0:
        return 0.0
    mine = sum(value for author, value in weight.items() if author in emails)
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
