"""`graph.json` — the derived output every consumer reads.

The graph speaks only of Artifacts, Tools, Techniques, Periods, Collections,
Authors, Dependencies and Epoch Markers. It does not know what a commit is:
collectors know about repositories and commits, the graph does not (Principle V).

See `specs/001-git-collector/contracts/graph.md`.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import replace
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


def dependency_id(ecosystem: str, name: str) -> str:
    """`@babel/cli` e `babel-cli` são dois pacotes, e precisam de dois nós.

    `slug` transforma `@` e `/` no mesmo hífen que já separa palavras, então o
    escopo do npm evapora e nomes distintos disputam um id só. O guard de
    rótulos recusa a fusão — corretamente —, mas o preço é o build inteiro cair
    por causa de um `package.json`. Aqui cada segmento do nome é sluggado por
    si, e a barra sobrevive como separador.

    Um nome do qual o slug não deixa nada — só pontuação, ou escrita fora do
    alfabeto latino — é derivado por digest, como um Author: ilegível, mas sem
    arrastar o vizinho para o mesmo nó.
    """
    segments = [part for part in (slug(piece) for piece in name.split("/")) if part]
    if not segments:
        digest = hashlib.sha256(name.strip().encode("utf-8")).hexdigest()
        return f"dependency:{ecosystem}/{digest[:16]}"
    scope = "@" if name.startswith("@") else ""
    return f"dependency:{ecosystem}/{scope}{'/'.join(segments)}"


LINEAGE_EDGES = ("DERIVES_FROM", "SUCCEEDS")


class CollidingLabels(Exception):
    """Two distinct labels resolved to one node id."""


class GraphBuilder:
    def __init__(self):
        self._nodes: dict[str, dict] = {}
        self._edges: set[tuple[str, str, str]] = set()
        self._edge_payload: dict[tuple[str, str, str], dict] = {}
        # Nós cujas arestas de linhagem nunca podem cruzar: uma aresta de um
        # nó anônimo para um Artifact público identifica o anônimo.
        self._shielded: set[str] = set()

    def shield(self, node_id_: str) -> None:
        self._shielded.add(node_id_)

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
        if edge_type in LINEAGE_EDGES and (
            source in self._shielded or target in self._shielded
        ):
            return
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


def _detected_lineage(artifacts):
    """Whatever the lineage detector found, or nothing if there is no detector.

    An inferred relationship with no detector behind it would be a claim nobody
    made, so the absence of the module means the absence of the edge — never a
    guess made here instead (FR-012, SC-008).
    """
    try:
        from core.analysis import lineage as lineage_module
    except ImportError:
        return []
    return lineage_module.candidates(artifacts)


def unreachable_sources(artifacts, build_mode: str = "public") -> list[dict]:
    """Sources the archive knows it cannot reach, reported rather than omitted.

    Derived from the store, not from the run: a rebuild has not scanned
    anything, and "we could not reach it" is a state the store carries between
    runs (FR-007, FR-019).

    Only sources of the Artifacts in *this* build appear. That matters once a
    published build excludes private Artifacts: a source with no visible
    Artifact behind it would tell a visitor that private work exists, which is
    exactly what Principle IV forbids.

    A `local` locator is a path on the Author's machine and is withheld from a
    published build — the kind and the date say what happened without
    publishing their directory layout. A `github` locator is already public and
    already in the graph, so it stays.
    """
    published = build_mode != "full"
    rows = []
    for artifact in artifacts:
        # Um locator de um Artifact sob alias é exatamente o que o alias
        # existe para não publicar; nem o par kind/last_seen atravessa, porque
        # "algo inacessível existiu aqui" já é informação sobre ele.
        if getattr(artifact, "aliased", False):
            continue
        for source in artifact.sources:
            if source.reachable:
                continue
            row = {"kind": source.kind, "last_seen": source.last_seen}
            if not (published and source.kind == "local"):
                row["locator"] = source.locator
            rows.append(row)
    return sorted(rows, key=lambda r: (r["kind"], r.get("locator") or "", r["last_seen"] or ""))


def build(artifacts, *, config=None, build_mode: str = "public",
          spans=None, lineage=None, aggregates: dict | None = None,
          unreachable: list | None = None, generated_at: str | None = None) -> dict:
    """Turn a list of store Artifacts into the graph a consumer reads."""
    from core.analysis import tool_spans

    builder = GraphBuilder()
    emails = tuple(config.emails) if config else ()
    stored = {a.id for a in artifacts}

    # O span é computado sobre os Artifacts presentes NESTE build — e um
    # Artifact sob alias só contribui para o span de uma Tool cuja aresta USES
    # foi publicada; mover o span de uma Tool que o anônimo "não usa" revela
    # que trabalho privado existiu num intervalo (FR-027).
    span_view = []
    for artifact in artifacts:
        if getattr(artifact, "aliased", False) and not (
            set(getattr(artifact, "reveal", ()) or ()) & {"tools"}
        ):
            span_view.append(replace(artifact, tools=[]))
        else:
            span_view.append(artifact)
    spans = spans if spans is not None else tool_spans.compute(span_view, emails)
    if unreachable is None:
        unreachable = unreachable_sources(artifacts, build_mode)

    for artifact in artifacts:
        aliased = getattr(artifact, "aliased", False)
        reveal = set(getattr(artifact, "reveal", ()) or ())
        extra = {}
        if artifact.activity.get("first"):
            extra["first"] = artifact.activity["first"]
        if artifact.activity.get("last"):
            extra["last"] = artifact.activity["last"]
        if aliased:
            extra["aliased"] = True
        elif artifact.description:
            # Sob alias a descrição nunca cruza, em nenhum ajuste: ela nomeia o
            # cliente com a mesma clareza que o nome real (ADR-0011).
            extra["description"] = artifact.description
        if not (aliased and "authorship" not in reveal):
            share = _share(artifact, emails)
            if share is not None:
                extra["authorship"] = {"share": share}

        artifact_node = builder.node(
            artifact.id, "Artifact", artifact.name or artifact.id, **extra
        )
        if aliased:
            builder.shield(artifact_node)

        for tool in artifact.tools:
            if aliased and "tools" not in reveal:
                continue
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
            # A evidência é um caminho de arquivo, e `clientname/api/deploy.yml`
            # desfaz o anonimato sem que ninguém tenha olhado. Sob alias a
            # Technique viaja sem o ponteiro — e portanto sem verificação; o que
            # ela perde é dito, não escondido (contracts/graph.md).
            builder.edge(
                artifact_node,
                technique_node,
                "APPLIES",
                confidence=technique.get("confidence"),
                evidence=[] if aliased else technique.get("evidence", []),
            )

        for dependency in artifact.dependencies:
            label = dependency["name"]
            dependency_node = builder.node(
                dependency_id(dependency["ecosystem"], label),
                "Dependency",
                label,
                ecosystem=dependency["ecosystem"],
            )
            builder.edge(artifact_node, dependency_node, "DEPENDS_ON")

        for period in () if aliased and "period" not in reveal else _periods(artifact):
            period_node = builder.node(node_id("Period", period), "Period", period)
            builder.edge(artifact_node, period_node, "IN_PERIOD")

        for entry in (
            ()
            if aliased and "authorship" not in reveal
            else artifact.authorship
        ):
            # O e-mail de um Author identifica tanto quanto o nome: sob alias,
            # AUTORED_BY só cruza quando `reveal` o nomeia.
            author_node = builder.node(
                node_id("Author", entry.author), "Author", entry.author
            )
            builder.edge(artifact_node, author_node, "AUTHORED_BY")

    # DERIVES_FROM é inferido, então carrega confiança e evidência na própria
    # aresta (SC-008).
    #
    # `lineage.candidates` ordena older → newer: `from` é o mais antigo. Emitir
    # nessa ordem afirmaria o falso — na varredura real saía
    # `tinygrad DERIVES_FROM tinyos`, quando tinygrad é de 2020 e tinyos de
    # 2024, e quem deriva é o segundo. A aresta é invertida aqui para se ler
    # como frase, igual a todas as outras do grafo.
    for relation in lineage if lineage is not None else _detected_lineage(artifacts):
        older, newer = relation["from"], relation["to"]
        if older in stored and newer in stored:
            builder.edge(
                newer,
                older,
                "DERIVES_FROM",
                confidence=relation.get("confidence"),
                evidence=list(relation.get("evidence") or []),
            )

    if config:
        # IN_COLLECTION vem só do config: a máquina propõe, o Author dispõe (FR-021).
        stored_ids = stored
        for collection in config.collections:
            collection_node = builder.node(
                node_id("Collection", collection.name), "Collection", collection.name
            )
            for artifact_id in collection.artifacts:
                if artifact_id in stored_ids:
                    builder.edge(artifact_id, collection_node, "IN_COLLECTION")
        # SUCCEEDS existe porque uma linha do config diz que existe, nunca
        # porque a ferramenta achou parecido (FR-011, ADR-0009). `dendro
        # suggest` propõe o par; só isto aqui o cria.
        for succession in config.successions:
            if succession.earlier in stored_ids and succession.later in stored_ids:
                builder.edge(
                    succession.later,
                    succession.earlier,
                    "SUCCEEDS",
                    **({"note": succession.note} if succession.note else {}),
                )

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
