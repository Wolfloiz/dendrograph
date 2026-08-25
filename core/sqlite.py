"""`graph.sqlite`: a query surface derived from `graph.json`, nothing more.

Not a graph database (Principle III, ADR-0004). One table per node type plus one
`edges` table, built from the same payload the JSON is written from, so anything
true of one is true of the other. Deleting it costs nothing — the next build
writes it again from `store/` (ADR-0002).

Attributes vary by node type and the schema is meant to stay readable, so each
table carries the columns its type actually uses plus an `attributes` column
holding the whole node as JSON. A query gets the common columns without a JSON
function, and never loses a field the columns do not name.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

FILENAME = "graph.sqlite"

# Colunas nomeadas por tipo, além de `id`, `label` e `attributes`, que todos têm.
TYPED_COLUMNS = {
    "Artifact": ("first", "last", "aliased", "authorship_share"),
    "Tool": ("first", "last", "artifact_count", "untouched_count", "attributed"),
    "Dependency": ("ecosystem",),
    "EpochMarker": ("date",),
}


def _table(node_type: str) -> str:
    return node_type.lower()


def _columns(node_type: str) -> tuple[str, ...]:
    return ("id", "label") + TYPED_COLUMNS.get(node_type, ()) + ("attributes",)


def _value(node: dict, column: str):
    if column == "attributes":
        return json.dumps(node, sort_keys=True, ensure_ascii=False)
    if column == "authorship_share":
        return (node.get("authorship") or {}).get("share")
    value = node.get(column)
    if isinstance(value, bool):
        return int(value)
    return value


def schema_statements(node_types) -> list[str]:
    statements = []
    for node_type in node_types:
        columns = ", ".join(
            f"{name} TEXT PRIMARY KEY" if name == "id" else name
            for name in _columns(node_type)
        )
        statements.append(f"CREATE TABLE {_table(node_type)} ({columns})")
    statements.append(
        "CREATE TABLE edges ("
        '"from" TEXT NOT NULL, "to" TEXT NOT NULL, type TEXT NOT NULL, '
        "attributes TEXT NOT NULL)"
    )
    statements.append("CREATE INDEX edges_from ON edges(\"from\")")
    statements.append("CREATE INDEX edges_to ON edges(\"to\")")
    statements.append("CREATE INDEX edges_type ON edges(type)")
    return statements


def write(payload: dict, directory: Path | str) -> Path:
    """Write `graph.sqlite` from the same payload `graph.json` is written from."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / FILENAME
    # Reconstruído do zero: é derivado, e um arquivo meio atualizado mentiria
    # sobre um store que já mudou.
    if path.exists():
        path.unlink()

    node_types = payload.get("schema", {}).get("node_types", [])
    connection = sqlite3.connect(path)
    try:
        with connection:
            for statement in schema_statements(node_types):
                connection.execute(statement)
            _create_search(connection)
            connection.execute(
                "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            connection.executemany(
                "INSERT INTO meta (key, value) VALUES (?, ?)",
                sorted(
                    (key, str(payload[key]))
                    for key in ("schema_version", "generated_at", "generator", "build_mode")
                    if key in payload
                ),
            )

            for node in payload.get("nodes", []):
                columns = _columns(node["type"])
                connection.execute(
                    f"INSERT INTO {_table(node['type'])} "
                    f"({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})",
                    [_value(node, column) for column in columns],
                )
                if node["type"] == "Artifact":
                    _index_for_search(connection, node)

            for edge in payload.get("edges", []):
                connection.execute(
                    'INSERT INTO edges ("from", "to", type, attributes) VALUES (?, ?, ?, ?)',
                    [
                        edge["from"],
                        edge["to"],
                        edge["type"],
                        json.dumps(edge, sort_keys=True, ensure_ascii=False),
                    ],
                )
    finally:
        connection.close()
    return path


# ---------- busca ----------


def _create_search(connection: sqlite3.Connection) -> None:
    """FTS5 sobre nomes e descrições de Artifact.

    Entra na v0.1 e nunca é consultada por ela. A busca da v0.2 precisa dela, e
    acrescentá-la depois obriga todo Author a reconstruir o arquivo — o custo
    agora é um INSERT por Artifact.
    """
    try:
        connection.execute(
            "CREATE VIRTUAL TABLE artifact_search USING fts5(id, label, description)"
        )
    except sqlite3.OperationalError:
        # Um Python compilado sem FTS5 continua produzindo um arquivo válido;
        # o que ele não pode é fingir que a tabela existe.
        pass


def has_search(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE name = 'artifact_search'"
    ).fetchone()
    return row is not None


def _index_for_search(connection: sqlite3.Connection, node: dict) -> None:
    if not has_search(connection):
        return
    connection.execute(
        "INSERT INTO artifact_search (id, label, description) VALUES (?, ?, ?)",
        [node["id"], node.get("label") or "", node.get("description") or ""],
    )
