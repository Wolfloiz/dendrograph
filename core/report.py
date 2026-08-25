"""What a run changed, and what it could not reach.

Every command ends with one of these. A run that silently skipped half an
archive is worse than one that failed, because the Author cannot tell the
difference from the output (FR-018, FR-019).
"""

from __future__ import annotations

from dataclasses import dataclass, field

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_PARTIAL = 3


@dataclass
class RunReport:
    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    unreachable: list[str] = field(default_factory=list)
    withheld: list[str] = field(default_factory=list)
    unidentifiable: list[str] = field(default_factory=list)
    declared_but_unseen: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    dry_run: bool = False

    @property
    def exit_code(self) -> int:
        """`3` when a source could not be reached.

        A scheduled Actions run has to be able to tell "nothing to see" from
        "half your archive was skipped", and a zero exit hides the difference.
        """
        return EXIT_PARTIAL if self.unreachable else EXIT_OK

    def lines(self) -> list[str]:
        out: list[str] = []
        if self.dry_run:
            out.append("Dry run — nothing was written.")
        out.append(
            f"{len(self.added)} Artifact(s) added, {len(self.changed)} changed."
        )
        for label, items in (
            ("Could not reach", self.unreachable),
            ("Withheld from output", self.withheld),
            ("Unidentifiable, not stored", self.unidentifiable),
            ("Declared but not seen", self.declared_but_unseen),
        ):
            if items:
                out.append(f"{label} ({len(items)}):")
                out.extend(f"  {item}" for item in sorted(items))
        if self.unreachable:
            out.append(
                "A source that could not be reached is recorded as unreachable, "
                "never as deleted."
            )
        out.extend(self.notes)
        return out

    def render(self) -> str:
        return "\n".join(self.lines())
