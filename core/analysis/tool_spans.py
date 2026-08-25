"""When a Tool was first and last used, and in how many Artifacts.

Computed over **the Artifacts present in the build being produced**, not over
the whole store. A published span is therefore narrower than the Author's own
by construction: a visitor must not learn that private work existed in an
interval, and the Author widens it by aliasing the Artifacts that matter
(FR-027, ADR-0011).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    tool: str
    first: str | None
    last: str | None
    artifact_count: int


def compute(artifacts) -> dict[str, Span]:
    """Spans keyed by Tool name, over exactly the Artifacts handed in."""
    firsts: dict[str, list[str]] = {}
    lasts: dict[str, list[str]] = {}
    counts: dict[str, int] = {}

    for artifact in artifacts:
        first = artifact.activity.get("first")
        last = artifact.activity.get("last")
        for tool in artifact.tools:
            name = tool["name"]
            counts[name] = counts.get(name, 0) + 1
            if first:
                firsts.setdefault(name, []).append(first)
            if last:
                lasts.setdefault(name, []).append(last)

    return {
        name: Span(
            tool=name,
            first=min(firsts.get(name, []), default=None),
            last=max(lasts.get(name, []), default=None),
            artifact_count=count,
        )
        for name, count in counts.items()
    }
