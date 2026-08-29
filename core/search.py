"""Search over the archive's own build, from the Author's machine.

The FTS5 table `artifact_search(id, label, description)` enters the archive in
v0.1 and is never queried by it. This module is its first caller (R1).

Scope is the whole build, **including the Artifacts the published site
withholds** — it runs locally against the Author's own archive, and the
published payload is a different artefact with a different audience (ADR-0005).
The page cannot use any of this: a `file://` document has no way to query
SQLite without a library, which ADR-0004 forbids. `views/search.js` answers the
same question over the payload it already holds.

Sem índice, o comando recusa em vez de cair para uma varredura linear: uma
busca que degrada em silêncio responde a outra pergunta sem dizer que trocou de
pergunta, e `sqlite.has_search()` existe exatamente para que a diferença seja
sabível (R6, Princípio I).

Contrato: `specs/002-usable-by-a-stranger/contracts/search.md`.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from core import sqlite as sqlite_module
from core.report import EXIT_USAGE, RunReport

# Na ordem do contrato: o build `full` quando existe, senão o publicado. O
# Author perguntando da própria máquina quer o alcance maior dos dois.
BUILD_DIRS = (".dendro-local", "site")

# Só duas colunas entram no MATCH. `id` também é indexada, mas um acerto nela
# não teria como ser explicado: o vocabulário das duas superfícies tem
# exatamente dois motivos — nome e descrição — e `dendro search root` casando
# com todo `root-<sha>` do arquivo devolveria 97 linhas dizendo "name" sobre um
# nome que não contém a palavra. Dizer um porquê falso é pior que não achar.
SEARCH_COLUMNS = "{label description}"
LABEL_COLUMN = 1
DESCRIPTION_COLUMN = 2

MATCHED_NAME = "name"
MATCHED_DESCRIPTION = "description"

# Marcadores que não sobrevivem a nenhuma descrição real: `highlight` devolve a
# coluna inteira quando ela não casou, e é a presença do marcador — não uma
# comparação de substring feita aqui — que responde "por que esta linha veio".
# Perguntar ao próprio FTS5 é o que mantém a resposta verdadeira quando a
# consulta tem duas palavras, uma no nome e outra na prosa.
_OPEN = "\x02"
_CLOSE = "\x03"


class NoSearchIndex(Exception):
    """The build has no `artifact_search` table. Refuse; never degrade (R6)."""


class NoArchive(Exception):
    """There is no build to search yet — a different failure from having no index."""


NO_INDEX_MESSAGE = (
    "dendro: this archive was built without a search index. Rebuild it with a Python\n"
    "        that has FTS5 (`python3 -c \"import sqlite3; sqlite3.connect(':memory:')\n"
    "        .execute('CREATE VIRTUAL TABLE t USING fts5(x)')\"` must succeed), then\n"
    "        run `dendro build` again."
)


class RefusedReport(RunReport):
    """A refusal that exits `2`, the usage code the contract names.

    Um relatório em vez de uma exceção porque `cli.main` já sabe transformar
    relatório em código de saída, e porque recusar por falta de índice não é
    "o comando falhou": é o arquivo estar num estado que o Author corrige.
    """

    @property
    def exit_code(self) -> int:
        return EXIT_USAGE


@dataclass(frozen=True)
class Result:
    """One row: the subject, its kind, and why it matched."""

    id: str
    label: str
    kind: str
    matched: str
    excerpt: str = ""

    def reason(self) -> str:
        if self.matched == MATCHED_NAME:
            return MATCHED_NAME
        return f'{MATCHED_DESCRIPTION}: "{self.excerpt}"'


def index_path(root: Path | str) -> Path:
    """The `graph.sqlite` to search, preferring the full build over the site."""
    root = Path(root)
    for directory in BUILD_DIRS:
        candidate = root / directory / sqlite_module.FILENAME
        if candidate.exists():
            return candidate
    raise NoArchive(f"no build to search in {root}. Run `dendro build` first.")


def connect(path: Path | str) -> sqlite3.Connection:
    """Read-only: asking a question writes nothing."""
    return sqlite3.connect(f"file:{Path(path)}?mode=ro", uri=True)


def expression(text: str) -> str | None:
    """An FTS5 expression from whatever the Author typed.

    Every word must appear, and the last word grows into a prefix when the
    Author stopped in the middle of it — `tutorial` não achar `tutorials` é o
    primeiro defeito que aparece numa busca por nome de projeto (8 acertos
    contra 2 no arquivo real). Quem digitou algo depois da última palavra —
    `c++`, ou um espaço — terminou a palavra, e ela vale exata.

    As aspas existem porque um termo cru como `c++` é erro de sintaxe em FTS5,
    e um traceback ali seria a ferramenta culpando o Author por ter digitado o
    nome da própria linguagem.
    """
    tokens = re.findall(r"[^\W_]+", text, flags=re.UNICODE)
    if not tokens:
        return None
    quoted = ['"{}"'.format(token.replace('"', '""')) for token in tokens]
    if re.search(r"[^\W_]$", text, flags=re.UNICODE):
        quoted[-1] += " *"
    return f"{SEARCH_COLUMNS} : ({' AND '.join(quoted)})"


def search(
    connection: sqlite3.Connection, text: str, *, limit: int | None = None
) -> tuple[list[Result], int]:
    """Rows for *text*, and how many there were before *limit* cut them.

    Ordering is FTS5 rank, then name: how often the words occur against how
    long the text is, and the alphabet to break ties. Nothing here weighs which
    Artifact matters more, because that would be an inference this tool does
    not make (Princípio I).

    O corte é feito aqui e não com `LIMIT` no SQL, porque o total precisa ser
    verdadeiro: "20 of 43" só é dizível por quem contou os 43. Um arquivo de
    500 Artifacts (ADR-0004) cabe nesta lista sem valer uma segunda consulta.
    """
    if not sqlite_module.has_search(connection):
        raise NoSearchIndex(NO_INDEX_MESSAGE)

    match = expression(text)
    if match is None:
        return [], 0

    rows = connection.execute(
        "SELECT id, label, "
        f"highlight(artifact_search, {LABEL_COLUMN}, ?, ?), "
        f"snippet(artifact_search, {DESCRIPTION_COLUMN}, '', '', '…', 10) "
        "FROM artifact_search WHERE artifact_search MATCH ? "
        "ORDER BY rank, label",
        (_OPEN, _CLOSE, match),
    ).fetchall()

    results = []
    for artifact_id, label, highlighted, excerpt in rows:
        by_name = _OPEN in (highlighted or "")
        results.append(
            Result(
                id=artifact_id,
                label=label,
                # A tabela indexa Artifacts e só eles; a coluna existe porque
                # as duas superfícies dizem de que tipo é cada linha (FR-008).
                kind="Artifact",
                matched=MATCHED_NAME if by_name else MATCHED_DESCRIPTION,
                excerpt="" if by_name else (excerpt or ""),
            )
        )

    total = len(results)
    if limit is not None and limit >= 0:
        results = results[:limit]
    return results, total


# ---------- saída ----------

# Larguras mínimas para que uma busca curta saia nas mesmas colunas de uma
# longa, e o Author não releia a linha a cada consulta.
_LABEL_WIDTH = 23
_KIND_WIDTH = 11


def render(results: list[Result], total: int) -> str:
    """The contract's three columns, then the count.

    A contagem é a deste build. Nada aqui soma de volta o que um build
    publicado deixou de fora: dizer "1 oculto" contaria ao visitante que
    existe trabalho privado casando com aquela palavra (FR-009, Princípio IV).
    """
    label_width = max([len(r.label) for r in results] + [_LABEL_WIDTH - 2]) + 2
    kind_width = max([len(r.kind) for r in results] + [_KIND_WIDTH - 2]) + 2
    lines = [
        f"{r.label:<{label_width}}{r.kind:<{kind_width}}{r.reason()}" for r in results
    ]
    if len(results) < total:
        lines.append(f"{len(results)} of {total} result(s).")
    else:
        lines.append(f"{total} result(s).")
    return "\n".join(lines)
