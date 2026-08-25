"""Artifacts that look prunable, and the config lines that would exclude them.

**Deletes nothing** (FR-008). Exclusion omits an Artifact from the graph while
leaving it in the store, and is reversed by deleting the line — its data returns
intact (ADR-0002).

A tool built because human memory is unreliable must not offer one-command
amnesia. So this command is a reading, not an action: it says what looks like
clutter and hands over the exact line that would hide it, and the Author decides.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Um fork em que o Author quase não tocou: presente no arquivo, mas não é
# trabalho dele em nenhum sentido que uma entrevista aceitaria.
BARELY_MINE = 0.1

# Um repositório com pouquíssimos commits e nenhuma Tool reconhecida costuma ser
# um teste, um tutorial seguido até a metade, um `git init` esquecido.
FEW_COMMITS = 3


@dataclass(frozen=True)
class Candidate:
    artifact_id: str
    name: str
    reason: str

    def render(self) -> str:
        return f"{self.name}  ({self.artifact_id})\n    {self.reason}"


@dataclass
class Report:
    candidates: list[Candidate] = field(default_factory=list)
    already_excluded: list[str] = field(default_factory=list)

    def config_block(self) -> str:
        ids = ", ".join(f'"{c.artifact_id}"' for c in self.candidates)
        return f"[exclude]\nartifacts = [{ids}]"

    def render(self) -> str:
        out: list[str] = []
        if self.already_excluded:
            out.append(
                f"{len(self.already_excluded)} Artifact(s) are already excluded. They "
                "are still in the store, and deleting their config line brings them "
                "back intact."
            )
            out.append("")
        if not self.candidates:
            out.append("Nothing looks prunable.")
            return "\n".join(out)

        out.append(f"{len(self.candidates)} Artifact(s) look prunable:")
        out.append("")
        for candidate in self.candidates:
            out.append(f"  {candidate.render()}")
            out.append("")
        out.append("To exclude them, put this in dendrograph.toml:")
        out.append("")
        for line in self.config_block().splitlines():
            out.append(f"  {line}")
        out.append("")
        out.append(
            "Nothing was deleted, and nothing will be. Excluding an Artifact omits it "
            "from the graph and leaves it in the store; delete the line and it returns "
            "with its history intact."
        )
        return "\n".join(out)


def _share(artifact, emails: frozenset) -> float | None:
    if not artifact.authorship or not emails:
        return None
    weight = {
        a.author: a.commits + a.lines_added + a.lines_deleted for a in artifact.authorship
    }
    total = sum(weight.values())
    if total == 0:
        return None
    return sum(v for author, v in weight.items() if author in emails) / total


def _commits(artifact, emails: frozenset) -> int:
    if emails:
        return sum(a.commits for a in artifact.authorship if a.author in emails)
    return sum(a.commits for a in artifact.authorship)


def candidates(artifacts, config=None) -> Report:
    """What looks like clutter. An opinion offered, never acted on."""
    excluded = set(config.excluded) if config else set()
    opted_in = set(config.opt_in) if config else set()
    emails = frozenset(e.strip().lower() for e in (config.emails if config else ()))
    in_a_collection = set()
    if config:
        for collection in config.collections:
            in_a_collection |= set(collection.artifacts)

    report = Report()
    for artifact in sorted(artifacts, key=lambda a: a.id):
        if artifact.id in excluded:
            report.already_excluded.append(artifact.id)
            continue
        # O Author já disse que estes importam. Não se sugere apagar o que
        # alguém acabou de escolher a dedo.
        if artifact.id in opted_in or artifact.id in in_a_collection:
            continue

        reason = _why(artifact, emails)
        if reason:
            report.candidates.append(
                Candidate(
                    artifact_id=artifact.id,
                    name=artifact.name or artifact.id,
                    reason=reason,
                )
            )
    return report


def _why(artifact, emails: frozenset) -> str | None:
    share = _share(artifact, emails)
    is_fork = any(s.is_fork for s in artifact.sources)

    if is_fork and share is not None and share < BARELY_MINE:
        return (
            f"a fork with {share:.1%} of the authored material yours — present in the "
            "archive, but not your work in any sense an interview would accept"
        )
    if is_fork and share is None and not artifact.tools:
        return "a fork with no recognised Tool and no way to tell how much of it is yours"

    commits = _commits(artifact, emails)
    if commits and commits <= FEW_COMMITS and not artifact.tools:
        return (
            f"{commits} commit(s) and no recognised Tool — often a test, an abandoned "
            "tutorial, or a forgotten `git init`"
        )
    if not artifact.activity.get("first"):
        return "no dated activity at all, so it cannot be placed on the timeline"
    return None
