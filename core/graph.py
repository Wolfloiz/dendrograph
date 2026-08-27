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


# npm e PyPI discordam sobre quando dois nomes são o mesmo pacote, e um id só
# para os dois responde errado para um dos lados. O PyPI normaliza (PEP 503):
# `Django`, `django` e `Django_REST` designam um projeto só, e a caixa ali é
# grafia, não identidade. O npm não normaliza: nome novo tem que ser minúsculo,
# mas `LiveScript`, publicado antes dessa regra, segue sendo um pacote distinto
# de `livescript`. Dobrar a caixa dos dois funde dois pacotes num nó; não dobrar
# a de nenhum parte um projeto em dois.
_PEP503 = re.compile(r"[-_.]+")
_NORMALISING = frozenset({"pypi"})


def dependency_name(ecosystem: str, name: str) -> str:
    """O nome sob o qual o ecossistema reconhece o pacote.

    É também o rótulo do nó: escrever `Django` num `requirements.txt` e
    `django` noutro não são dois projetos, e o guard de rótulos recusaria os
    dois nomes no mesmo id — corretamente, se os nomes fossem mesmo distintos.
    """
    stripped = name.strip()
    if ecosystem in _NORMALISING:
        return _PEP503.sub("-", stripped).lower()
    return stripped


# O nome do pacote já é o identificador dele dentro do ecossistema; sluggar por
# cima inventa um segundo, e um que perde informação. `@babel/cli` e `babel-cli`
# caíam no mesmo id porque `@` e `/` viram o hífen que separa palavras, e o
# build inteiro caía por causa de um `package.json`.
#
# O que não couber no conjunto seguro sai por digest, como um Author: ilegível,
# mas sem arrastar o vizinho para o seu nó.
_SAFE_NAME = re.compile(r"^@?[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")


def dependency_id(ecosystem: str, name: str) -> str:
    canonical = dependency_name(ecosystem, name)
    if canonical and _SAFE_NAME.match(canonical):
        return f"dependency:{ecosystem}/{canonical}"
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"dependency:{ecosystem}/{digest[:16]}"


# Um endereço de e-mail publicado é um endereço colhido. O grafo já derivava o
# id de Author por digest para manter o endereço fora dele (`node_id`), mas o
# rótulo saía inteiro: numa varredura real, 1.165 contribuintes de repositórios
# públicos alheios, cada um com o e-mail legível, num site que a Princípio III
# manda abrir de qualquer lugar. O GitHub esconde o endereço atrás de `noreply`
# exatamente por isso, e nada aqui autoriza a ferramenta a desfazer isso.
#
# Publicado, o rótulo é a parte local do endereço, sem o prefixo numérico que o
# GitHub antepõe: `57202004+kshitija7@users.noreply.github.com` vira
# `kshitija7`, que já é o nome de usuário público. O modo `full`, que nunca sai
# da máquina do Author (`core/build.py`), mantém o endereço — distinguir dois
# `john` é problema de quem olha o próprio arquivo.
#
# O rótulo certo seria o nome do commit, e o coletor ainda não o guarda:
# `Authorship` tem só o endereço. Acrescentá-lo obriga todo Author a
# reconstruir, e é decisão de quem cuida de `collectors/git/` (ADR-0012).
_GITHUB_NUMERIC_PREFIX = re.compile(r"^\d+\+")
_LOOKS_LIKE_ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def author_label(email: str, name: str | None = None, *, published: bool) -> str:
    """Como um Author é chamado na saída, que não é como ele é identificado.

    O nome do commit é o rótulo certo quando existe: é o que a pessoa escolheu
    e o que o GitHub já mostra em cada commit dela. Registros guardados antes de
    o coletor passar a lê-lo não têm nome, e caem na parte local do endereço.
    """
    if not published:
        return email
    written = (name or "").strip()
    # Muita gente põe o próprio endereço em `user.name`. Aí o nome não é melhor
    # que o e-mail, e vale a mesma regra.
    if written and not _LOOKS_LIKE_ADDRESS.search(written):
        return written
    local = _GITHUB_NUMERIC_PREFIX.sub("", email.split("@", 1)[0].strip())
    if local:
        return local
    digest = hashlib.sha256(email.encode("utf-8")).hexdigest()
    return f"author-{digest[:8]}"


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


def _signatures(artifacts) -> dict[str, str]:
    """A grafia com que cada endereço mais assinou, sobre o build inteiro.

    A mesma pessoa assina diferente em repositórios diferentes — `Luiz` num,
    `loiz` noutro — e o id é o mesmo endereço nos dois. Escolher por Artifact
    faz o guard acusar de colisão uma fusão correta, e foi o que aconteceu na
    primeira varredura depois que o nome virou rótulo. É a regra de
    `authorship._chosen_name` um nível acima, pesada por commits: a grafia do
    repositório onde a pessoa mais trabalhou, desempate alfabético para que
    duas execuções não discordem.
    """
    tally: dict[str, dict[str, int]] = {}
    for artifact in artifacts:
        for entry in artifact.authorship:
            written = (entry.name or "").strip()
            if not written:
                continue
            seen = tally.setdefault(entry.author, {})
            seen[written] = seen.get(written, 0) + max(entry.commits, 1)
    return {
        author: sorted(seen.items(), key=lambda item: (-item[1], item[0]))[0][0]
        for author, seen in tally.items()
    }


def build(artifacts, *, config=None, build_mode: str = "public",
          spans=None, lineage=None, aggregates: dict | None = None,
          unreachable: list | None = None, generated_at: str | None = None) -> dict:
    """Turn a list of store Artifacts into the graph a consumer reads."""
    # Importado como função: o parâmetro `spans` já ocupa o nome do módulo.
    from core.analysis.spans import compute as compute_spans

    builder = GraphBuilder()
    emails = tuple(config.emails) if config else ()
    stored = {a.id for a in artifacts}
    signatures = _signatures(artifacts)

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
    spans = spans if spans is not None else compute_spans(span_view, emails)
    # Technique não passa pelo `span_view`: a aresta APPLIES de um Artifact sob
    # alias é publicada de propósito, sem o ponteiro (contracts/graph.md), e um
    # span tem que contar exatamente os Artifacts cuja aresta saiu. Contar
    # menos daria a uma Technique cinco arestas e três Artifacts.
    technique_spans = compute_spans(artifacts, emails, of="techniques")
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
            # "Faço teste automatizado desde quando" é a mesma pergunta que o
            # README responde para Rust com uma data. Sem o span, a Technique
            # respondia com pertencimento a um conjunto.
            span = technique_spans.get(technique["name"])
            attrs = {}
            if span:
                attrs = {
                    "first": span.first,
                    "last": span.last,
                    "artifact_count": span.artifact_count,
                }
                if span.untouched_count:
                    attrs["untouched_count"] = span.untouched_count
                if not span.attributed:
                    attrs["attributed"] = False
            technique_node = builder.node(
                node_id("Technique", technique["name"]), "Technique",
                technique["name"], **attrs
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
            ecosystem = dependency["ecosystem"]
            label = dependency_name(ecosystem, dependency["name"])
            dependency_node = builder.node(
                dependency_id(ecosystem, dependency["name"]),
                "Dependency",
                label,
                ecosystem=ecosystem,
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
                node_id("Author", entry.author),
                "Author",
                author_label(
                    entry.author,
                    signatures.get(entry.author),
                    published=build_mode != "full",
                ),
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
