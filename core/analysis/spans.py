"""When a named thing was first and last used, and in how many Artifacts.

Tools and Techniques both answer to it. A Tool is what an Artifact is written
in and a Technique is how it was built, but *since when, and in how many* is
one question asked twice — and this module does not know which of the two it
is holding. It reads `{"name": ...}` entries off the Artifact and counts.

Computed over **the Artifacts present in the build being produced**, not over
the whole store. A published span is therefore narrower than the Author's own
by construction: a visitor must not learn that private work existed in an
interval, and the Author widens it by aliasing the Artifacts that matter
(FR-027, ADR-0011).

Within each Artifact the window is the Author's **own** commits, not the
Artifact's whole activity. A fork carries its upstream's history: `gpuocelot`,
forked with commits back to 2009, would otherwise make C++, Docker, Python and
Shell all read "first used 2009" for an Author whose work starts in 2020. That
overstates experience, and overstating is the one direction ADR-0009 rules out.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    name: str
    first: str | None
    last: str | None
    artifact_count: int
    # Artifacts que usam a Tool e onde o Author não tem commit nenhum. Ficam
    # fora das datas, mas não somem: esconder um fork seria mentir na outra
    # direção, e o Author precisa ver por que a conta não fecha.
    untouched_count: int = 0
    # Falso quando não há e-mails configurados: sem eles não existe "meu" para
    # medir, e a janela é só o que foi observado. SC-007 fala em anos de
    # experiência — uma janela não atribuída não sustenta essa frase.
    attributed: bool = True


def _own_window(artifact, own_emails: frozenset) -> tuple[str | None, str | None]:
    """The Author's own first and last commit dates in one Artifact."""
    firsts = [a.first for a in artifact.authorship if a.author in own_emails and a.first]
    lasts = [a.last for a in artifact.authorship if a.author in own_emails and a.last]
    return (min(firsts, default=None), max(lasts, default=None))


def compute(artifacts, emails: tuple[str, ...] = (),
            of: str = "tools") -> dict[str, Span]:
    """Spans keyed by name, over exactly the Artifacts handed in.

    `of` names the list to read — `tools` or `techniques`.

    Without `emails` the window falls back to each Artifact's whole activity and
    the Span is marked unattributed, so a caller can say what it is rather than
    pass a fork's dates off as the Author's.

    A Technique span answers a narrower question than it looks like. Techniques
    are read from the tree at HEAD, so what was observed is that the marker is
    there *now*: `first` is the earliest the Author worked on an Artifact that
    shows it today, not the date the Technique was adopted. Adopted and later
    abandoned leaves no trace at all. The contract says this out loud rather
    than letting the field be read as an adoption date.
    """
    attributed = bool(emails)
    # `Authorship` normaliza o e-mail gravado; o configurado tem que combinar.
    own_emails = frozenset(e.strip().lower() for e in emails)
    firsts: dict[str, list[str]] = {}
    lasts: dict[str, list[str]] = {}
    counts: dict[str, int] = {}
    untouched: dict[str, int] = {}

    for artifact in artifacts:
        if attributed:
            first, last = _own_window(artifact, own_emails)
            mine = first is not None or last is not None
        else:
            first = artifact.activity.get("first")
            last = artifact.activity.get("last")
            mine = True

        for item in getattr(artifact, of):
            name = item["name"]
            counts.setdefault(name, 0)
            untouched.setdefault(name, 0)
            if not mine:
                untouched[name] += 1
                continue
            counts[name] += 1
            if first:
                firsts.setdefault(name, []).append(first)
            if last:
                lasts.setdefault(name, []).append(last)

    return {
        name: Span(
            name=name,
            first=min(firsts.get(name, []), default=None),
            last=max(lasts.get(name, []), default=None),
            artifact_count=count,
            untouched_count=untouched[name],
            attributed=attributed,
        )
        for name, count in counts.items()
    }
