"""`graph.json` — the derived output every consumer reads.

The graph speaks only of Artifacts, Tools, Techniques, Periods, Collections,
Authors, Dependencies and Epoch Markers. It does not know what a commit is:
collectors know about repositories and commits, the graph does not (Principle V).

See `specs/001-git-collector/contracts/graph.md`.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

SCHEMA_VERSION = 1
GENERATOR = "dendrograph 0.1.0"

NODE_TYPES = (
    "Artifact",
    "Tool",
    "Technique",
    "Period",
    "Collection",
    "Author",
    "Dependency",
    "EpochMarker",
)

EDGE_TYPES = (
    "USES",
    "APPLIES",
    "IN_PERIOD",
    "IN_COLLECTION",
    "AUTHORED_BY",
    "DEPENDS_ON",
    "DERIVES_FROM",
    "SUCCEEDS",
)


# Símbolos que distinguem nomes de Tool viram palavra antes de serem removidos.
# Sem isto C, C++ e C# colapsavam todos em `tool:c`: um nó só, com o rótulo de
# quem escreveu por último, as arestas USES das três somadas e o span de uma
# pendurado na identidade de outra.
SYMBOL_WORDS = (("+", "plus"), ("#", "sharp"), ("&", "and"))


def slug(text: str) -> str:
    lowered = text.lower()
    for symbol, word in SYMBOL_WORDS:
        lowered = lowered.replace(symbol, f"-{word}-")
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")


def node_id(node_type: str, label: str) -> str:
    # Um e-mail é identificador, não rótulo: sluggar come a pontuação e faz
    # `ebagola@gmail,.com` — vírgula perdida no git config de alguém — colidir
    # com `ebagola@gmail.com`. Ninguém pode consertar o config alheio, então o
    # id de Author é derivado sem perda em vez de legível. Também mantém o
    # endereço fora da string do id.
    if node_type == "Author":
        digest = hashlib.sha256(label.strip().lower().encode("utf-8")).hexdigest()
        return f"author:{digest[:16]}"
    return f"{node_type.lower()}:{slug(label)}"


class CollidingLabels(Exception):
    """Two distinct labels resolved to one node id."""


class GraphBuilder:
    def __init__(self):
        self._nodes: dict[str, dict] = {}
        self._edges: set[tuple[str, str, str]] = set()
        self._edge_payload: dict[tuple[str, str, str], dict] = {}

    def node(self, node_id_: str, node_type: str, label: str, **extra) -> str:
        existing = self._nodes.get(node_id_, {})
        # Reencontrar o mesmo id com outro rótulo não é deduplicação, é dois
        # nomes distintos caindo no mesmo nó. Silenciar isso já custou a fusão
        # de C com C++; falhar alto é a única saída que não corrompe o grafo.
        if existing and existing.get("label") != label:
            raise CollidingLabels(
                f"{node_type} labels {existing['label']!r} and {label!r} both "
                f"produce the node id {node_id_!r}. Two different things would "
                f"be merged into one node."
            )
        existing.update({"id": node_id_, "type": node_type, "label": label, **extra})
        self._nodes[node_id_] = existing
        return node_id_

    def edge(self, source: str, target: str, edge_type: str, **extra) -> None:
        key = (edge_type, source, target)
        self._edges.add(key)
        if extra:
            self._edge_payload[key] = extra

    def _ordered_nodes(self) -> list[dict]:
        # Ordenação determinística: dois builds do mesmo store diferem só em
        # generated_at, senão todo build suja o histórico do repositório (FR-018).
        return sorted(self._nodes.values(), key=lambda n: (n["type"], n["id"]))

    def _ordered_edges(self) -> list[dict]:
        rows = []
        for edge_type, source, target in sorted(self._edges):
            row = {"from": source, "to": target, "type": edge_type}
            row.update(self._edge_payload.get((edge_type, source, target), {}))
            rows.append(row)
        return rows

    def to_dict(self, *, build_mode: str, aggregates: dict | None = None,
                unreachable: list | None = None, generated_at: str | None = None) -> dict:
        nodes = self._ordered_nodes()
        tool_index: dict[str, list[str]] = {}
        for edge in self._ordered_edges():
            if edge["type"] == "USES":
                tool_index.setdefault(edge["to"], []).append(edge["from"])

        payload = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at
            or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generator": GENERATOR,
            "build_mode": build_mode,
            # Autodescritivo: um consumidor não precisa de documentação junto (FR-017).
            "schema": {"node_types": list(NODE_TYPES), "edge_types": list(EDGE_TYPES)},
            "nodes": nodes,
            "edges": self._ordered_edges(),
            # Presente na v0.1 e não renderizado por ela: a v0.2 precisa dele, e
            # acrescentá-lo depois obriga todo Author a reconstruir.
            "indexes": {"tool_to_artifacts": {k: sorted(v) for k, v in sorted(tool_index.items())}},
        }
        if aggregates:
            payload["aggregates"] = aggregates
        payload["unreachable_sources"] = unreachable or []
        return payload


def build(artifacts, *, config=None, build_mode: str = "public",
          spans=None, aggregates: dict | None = None,
          unreachable: list | None = None, generated_at: str | None = None) -> dict:
    """Turn a list of store Artifacts into the graph a consumer reads."""
    from core.analysis import tool_spans

    builder = GraphBuilder()
    emails = tuple(config.emails) if config else ()
    spans = spans if spans is not None else tool_spans.compute(artifacts, emails)

    for artifact in artifacts:
        extra = {}
        if artifact.activity.get("first"):
            extra["first"] = artifact.activity["first"]
        if artifact.activity.get("last"):
            extra["last"] = artifact.activity["last"]
        if getattr(artifact, "aliased", False):
            extra["aliased"] = True
        share = _share(artifact, emails)
        if share is not None:
            extra["authorship"] = {"share": share}

        artifact_node = builder.node(
            artifact.id, "Artifact", artifact.name or artifact.id, **extra
        )

        for tool in artifact.tools:
            span = spans.get(tool["name"])
            attrs = {}
            if span:
                attrs = {
                    "first": span.first,
                    "last": span.last,
                    "artifact_count": span.artifact_count,
                }
                # Só viajam quando dizem algo: um span atribuído sem forks
                # intocados não precisa carregar dois campos vazios.
                if span.untouched_count:
                    attrs["untouched_count"] = span.untouched_count
                if not span.attributed:
                    attrs["attributed"] = False
            tool_node = builder.node(
                node_id("Tool", tool["name"]), "Tool", tool["name"], **attrs
            )
            builder.edge(artifact_node, tool_node, "USES")

        for technique in artifact.techniques:
            technique_node = builder.node(
                node_id("Technique", technique["name"]), "Technique", technique["name"]
            )
            builder.edge(
                artifact_node,
                technique_node,
                "APPLIES",
                confidence=technique.get("confidence"),
                evidence=technique.get("evidence", []),
            )

        for dependency in artifact.dependencies:
            label = dependency["name"]
            dependency_node = builder.node(
                f"dependency:{dependency['ecosystem']}/{slug(label)}",
                "Dependency",
                label,
                ecosystem=dependency["ecosystem"],
            )
            builder.edge(artifact_node, dependency_node, "DEPENDS_ON")

        for period in _periods(artifact):
            period_node = builder.node(node_id("Period", period), "Period", period)
            builder.edge(artifact_node, period_node, "IN_PERIOD")

        for entry in artifact.authorship:
            author_node = builder.node(
                node_id("Author", entry.author), "Author", entry.author
            )
            builder.edge(artifact_node, author_node, "AUTHORED_BY")

    if config:
        # IN_COLLECTION vem só do config: a máquina propõe, o Author dispõe (FR-021).
        stored_ids = {a.id for a in artifacts}
        for collection in config.collections:
            collection_node = builder.node(
                node_id("Collection", collection.name), "Collection", collection.name
            )
            for artifact_id in collection.artifacts:
                if artifact_id in stored_ids:
                    builder.edge(artifact_id, collection_node, "IN_COLLECTION")
        for marker in config.epoch_markers:
            builder.node(
                node_id("EpochMarker", marker.label),
                "EpochMarker",
                marker.label,
                date=marker.date,
            )

    return builder.to_dict(
        build_mode=build_mode,
        aggregates=aggregates,
        unreachable=unreachable,
        generated_at=generated_at,
    )


def _periods(artifact) -> list[str]:
    first = artifact.activity.get("first")
    last = artifact.activity.get("last")
    if not first:
        return []
    start, end = int(first[:4]), int((last or first)[:4])
    return [str(year) for year in range(start, end + 1)]


def _share(artifact, emails: tuple[str, ...]) -> float | None:
    if not artifact.authorship or not emails:
        return None
    from collectors.git import authorship as authorship_module

    return authorship_module.share(artifact.authorship, emails)
