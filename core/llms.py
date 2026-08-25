"""`llms.txt`: the archive explained in prose, for a reader that is not a browser.

An agent handed this directory should be able to answer questions about the
Author's work without parsing JSON first, and should know what the JSON holds
if it decides to (FR-017). Subject to the same privacy filtering as every other
output: it is written from the payload, so whatever was already excluded from
`graph.json` is absent here too.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

FILENAME = "llms.txt"


def _nodes(payload: dict, node_type: str) -> list[dict]:
    return [n for n in payload.get("nodes", []) if n["type"] == node_type]


def _date_range(artifacts: list[dict]) -> tuple[str | None, str | None]:
    firsts = [a["first"] for a in artifacts if a.get("first")]
    lasts = [a["last"] for a in artifacts if a.get("last")]
    return (min(firsts, default=None), max(lasts, default=None))


def _tool_line(tool: dict) -> str:
    window = (
        f"{tool.get('first')} to {tool.get('last')}"
        if tool.get("first")
        else "no dates the Author can claim"
    )
    line = f"- {tool['label']}: {window}, in {tool.get('artifact_count', 0)} Artifact(s)"
    if tool.get("untouched_count"):
        line += f"; {tool['untouched_count']} more use it but the Author never committed to them"
    if tool.get("attributed") is False:
        line += " (observed activity, NOT attributed to the Author — no emails configured)"
    return line


def render(payload: dict) -> str:
    artifacts = _nodes(payload, "Artifact")
    tools = _nodes(payload, "Tool")
    techniques = _nodes(payload, "Technique")
    first, last = _date_range(artifacts)
    mode = payload.get("build_mode", "public")
    aliased = [a for a in artifacts if a.get("aliased")]

    out: list[str] = []
    out.append("# dendrograph archive")
    out.append("")
    out.append(
        f"A knowledge graph of one person's body of work, built by {payload.get('generator', 'dendrograph')} "
        f"on {payload.get('generated_at', 'an unrecorded date')}."
    )
    out.append("")

    out.append("## What this archive contains")
    out.append("")
    out.append(f"- {len(artifacts)} Artifact(s)" + (f", spanning {first} to {last}" if first else ""))
    out.append(f"- {len(tools)} Tool(s), {len(techniques)} Technique(s)")
    out.append(f"- {len(payload.get('edges', []))} edges across {len(payload.get('nodes', []))} nodes")
    if aliased:
        out.append(
            f"- {len(aliased)} Artifact(s) published under an alias: the node and its dates "
            "are real, the name is not, and nothing else about them is here"
        )
    unreachable = payload.get("unreachable_sources") or []
    if unreachable:
        out.append(
            f"- {len(unreachable)} source(s) the archive could not reach on its last run. "
            "They are recorded as unreachable, never as deleted — the Artifacts remain"
        )
    out.append("")

    out.append("## What it deliberately does not contain")
    out.append("")
    # Escrito sem o vocabulário que o Princípio V recusa: `test_no_judgement`
    # varre os arquivos gerados, e um aviso não se distingue de uma afirmação
    # quando os dois usam as mesmas palavras.
    out.append(
        "This archive records what was built and when. It does not rank, score or judge "
        "anything it contains, it measures nothing about how well any of it was made, "
        "and it makes no claim about who — or what — wrote any line of it. Those "
        "judgements are refused by design, not merely unimplemented. Do not read them "
        "into this data."
    )
    if mode != "full":
        out.append("")
        out.append(
            "This is a published build. Private Artifacts are excluded unless the Author "
            "opted them in one by one, so counts and date ranges here are narrower than "
            "the Author's own view. Absence of an interval is not evidence that nothing "
            "was built in it."
        )
    out.append("")

    if tools:
        out.append("## Tools, and the span each one is claimed over")
        out.append("")
        out.append(
            "A span is the window of the **Author's own commits** in Artifacts using that "
            "Tool — not the Artifacts' whole history. A fork carries its upstream's past, "
            "and counting that would overstate experience."
        )
        out.append("")
        for tool in sorted(tools, key=lambda t: (t.get("first") or "9999", t["label"])):
            out.append(_tool_line(tool))
        out.append("")

    if techniques:
        out.append("## Techniques")
        out.append("")
        out.append(
            "Each Technique is inferred from evidence, and every claim carries a pointer "
            "to what it was derived from, on the APPLIES edge. A Technique on an aliased "
            "Artifact ships without its pointer and is not independently verifiable."
        )
        out.append("")
        for technique in sorted(techniques, key=lambda t: t["label"]):
            out.append(f"- {technique['label']}")
        out.append("")

    out.append("## How to read `graph.json`")
    out.append("")
    out.append(
        "`graph.json` sits next to this file and holds everything summarised above. It is "
        "self-describing: its `schema` key lists every node and edge type, so no companion "
        "documentation is needed."
    )
    out.append("")
    schema = payload.get("schema", {})
    out.append(f"- Node types: {', '.join(schema.get('node_types', []))}")
    out.append(f"- Edge types: {', '.join(schema.get('edge_types', []))}")
    out.append(
        "- Nodes are `{id, type, label, ...}`; edges are `{from, to, type, ...}` where "
        "`from` and `to` are node ids"
    )
    out.append(
        "- An Artifact's id is its root commit SHA prefixed `root-`, or a content hash "
        "prefixed `content-` where no root commit could be read. A fork shares the id of "
        "what it forked: it *is* the same Artifact, and how much of it is the Author's is "
        "a separate question, answered by `authorship.share` between 0 and 1"
    )
    out.append(
        "- `indexes.tool_to_artifacts` maps a Tool node id to the Artifacts using it"
    )
    out.append(
        "- `graph.sqlite` holds the same data as tables, if querying suits you better"
    )
    out.append("")

    edge_counts = Counter(e["type"] for e in payload.get("edges", []))
    if edge_counts:
        out.append("## Edge counts")
        out.append("")
        for name, count in sorted(edge_counts.items()):
            out.append(f"- {name}: {count}")
        out.append("")

    out.append("## Provenance")
    out.append("")
    out.append(
        "Relationships between Artifacts — that one succeeded another, that several form a "
        "Collection — appear only where the Author confirmed them. The tool proposes; it "
        "does not decide. An edge you see here was either directly observed in a "
        "repository or explicitly declared."
    )
    out.append("")
    return "\n".join(out)


def write(payload: dict, directory: Path | str) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / FILENAME
    path.write_text(render(payload), encoding="utf-8")
    return path
