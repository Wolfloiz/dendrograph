"""Reads `dendrograph.toml` — the Author's declarations.

The store holds what was observed; this holds what the Author decided. Every
declaration here is reversible by deleting a line (Principle I, ADR-0002).

See `specs/001-git-collector/contracts/config.md` for the contract.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_NAME = "dendrograph.toml"

PUBLISH_MODES = ("public", "redacted")
# Campos que um `[[publish.alias]].reveal` pode nomear. Qualquer outra coisa é
# recusada aqui, nunca ignorada — esquecimento neste ponto é vazamento.
# `dependencies` entrou depois de as arestas DEPENDS_ON cruzarem sem gate
# nenhum sob alias (ADR-0011); é campo separado de `tools` porque um manifesto
# é dezenas de pacotes exatos e `tools` são dez nós curados.
REVEAL_FIELDS = ("period", "tools", "authorship", "dependencies", "collections")
SOURCE_KINDS = ("github", "local")


class ConfigError(Exception):
    """Raised for anything wrong in the file. Never a warning.

    A typo in `opt_in` that silently does nothing is a privacy failure, and this
    file is where privacy is decided.
    """


@dataclass(frozen=True)
class Source:
    kind: str
    locator: str


@dataclass(frozen=True)
class Alias:
    """One private Artifact published under a label (FR-028, ADR-0011)."""

    id: str
    label: str | None = None
    reveal: tuple[str, ...] = ()


@dataclass(frozen=True)
class Merge:
    ids: tuple[str, ...]
    reason: str | None = None


@dataclass(frozen=True)
class Separate:
    id: str
    locator: str


@dataclass(frozen=True)
class Collection:
    name: str
    artifacts: tuple[str, ...]


@dataclass(frozen=True)
class Succession:
    """One Artifact followed another. Confirmed here and nowhere else.

    `dendro suggest` proposes pairs; a SUCCEEDS edge exists only because a line
    in this file says so (FR-011, ADR-0009). The graph contract calls the edge
    "Author-confirmed only, never inferred", and this is the confirmation.
    """

    earlier: str
    later: str
    note: str | None = None


@dataclass(frozen=True)
class EpochMarker:
    date: str
    label: str


@dataclass(frozen=True)
class Config:
    author: str | None = None
    emails: tuple[str, ...] = ()
    sources: tuple[Source, ...] = ()
    publish_mode: str = "public"
    opt_in: tuple[str, ...] = ()
    target_repository: str | None = None
    aliases: tuple[Alias, ...] = ()
    excluded: tuple[str, ...] = ()
    merges: tuple[Merge, ...] = ()
    separations: tuple[Separate, ...] = ()
    collections: tuple[Collection, ...] = ()
    successions: tuple[Succession, ...] = ()
    epoch_markers: tuple[EpochMarker, ...] = ()

    def alias_for(self, artifact_id: str) -> Alias | None:
        for alias in self.aliases:
            if alias.id == artifact_id:
                return alias
        return None

    def declared_ids(self) -> set[str]:
        """Every Artifact id this file names, for the run report to check."""
        ids: set[str] = set(self.opt_in) | set(self.excluded)
        ids |= {a.id for a in self.aliases}
        ids |= {s.id for s in self.separations}
        for merge in self.merges:
            ids |= set(merge.ids)
        for collection in self.collections:
            ids |= set(collection.artifacts)
        for succession in self.successions:
            ids |= {succession.earlier, succession.later}
        return ids


def _reject_unknown(table: dict, allowed: tuple[str, ...], where: str) -> None:
    unknown = sorted(set(table) - set(allowed))
    if unknown:
        raise ConfigError(
            f"{where}: unknown key(s) {', '.join(unknown)}. "
            f"Known keys are {', '.join(allowed)}."
        )


def _require(table: dict, key: str, where: str):
    if key not in table:
        raise ConfigError(f"{where}: missing required key {key!r}")
    return table[key]


def _strings(value, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ConfigError(f"{where}: expected a list of strings")
    return tuple(value)


def _parse_sources(raw: list, out: list[Source]) -> None:
    for i, entry in enumerate(raw):
        where = f"[[sources]] #{i + 1}"
        _reject_unknown(entry, ("kind", "account", "path"), where)
        kind = _require(entry, "kind", where)
        if kind not in SOURCE_KINDS:
            raise ConfigError(
                f"{where}: kind must be one of {', '.join(SOURCE_KINDS)}, got {kind!r}"
            )
        key = "account" if kind == "github" else "path"
        out.append(Source(kind=kind, locator=str(_require(entry, key, where))))


def _parse_publish(raw: dict) -> dict:
    _reject_unknown(
        raw, ("mode", "opt_in", "target_repository", "alias"), "[publish]"
    )
    mode = raw.get("mode", "public")
    if mode not in PUBLISH_MODES:
        # `full` está fora de propósito: é um sinalizador de build para
        # inspeção local, nunca um modo de publicação (contracts/graph.md).
        raise ConfigError(
            f"[publish].mode must be one of {', '.join(PUBLISH_MODES)}, got {mode!r}"
        )
    aliases = []
    for i, entry in enumerate(raw.get("alias", [])):
        where = f"[[publish.alias]] #{i + 1}"
        _reject_unknown(entry, ("id", "label", "reveal"), where)
        reveal = _strings(entry.get("reveal", []), f"{where}.reveal")
        unknown = sorted(set(reveal) - set(REVEAL_FIELDS))
        if unknown:
            # `reveal` é lista de divulgação, não de redação: um nome desconhecido
            # é recusado em vez de ignorado, senão o esquecimento vira vazamento.
            raise ConfigError(
                f"{where}.reveal: unknown field(s) {', '.join(unknown)}. "
                f"Publishable fields are {', '.join(REVEAL_FIELDS)}."
            )
        aliases.append(
            Alias(
                id=str(_require(entry, "id", where)),
                label=entry.get("label"),
                reveal=reveal,
            )
        )
    return {
        "publish_mode": mode,
        "opt_in": _strings(raw.get("opt_in", []), "[publish].opt_in"),
        "target_repository": raw.get("target_repository"),
        "aliases": tuple(aliases),
    }


def _parse_identity(raw: dict) -> dict:
    _reject_unknown(raw, ("merge", "separate"), "[identity]")
    merges = []
    for i, entry in enumerate(raw.get("merge", [])):
        where = f"[[identity.merge]] #{i + 1}"
        _reject_unknown(entry, ("ids", "reason"), where)
        ids = _strings(_require(entry, "ids", where), f"{where}.ids")
        if len(ids) < 2:
            raise ConfigError(f"{where}: a merge needs at least two ids")
        merges.append(Merge(ids=ids, reason=entry.get("reason")))
    separations = []
    for i, entry in enumerate(raw.get("separate", [])):
        where = f"[[identity.separate]] #{i + 1}"
        _reject_unknown(entry, ("id", "locator"), where)
        separations.append(
            Separate(
                id=str(_require(entry, "id", where)),
                locator=str(_require(entry, "locator", where)),
            )
        )
    return {"merges": tuple(merges), "separations": tuple(separations)}


def parse(raw: dict) -> Config:
    """Turn an already-decoded TOML mapping into a Config."""
    _reject_unknown(
        raw,
        (
            "archive",
            "sources",
            "publish",
            "exclude",
            "identity",
            "collections",
            "succession",
            "epoch_markers",
        ),
        "top level",
    )

    archive = raw.get("archive", {})
    # A checagem de credencial vem antes da genérica: as duas recusam, mas esta
    # diz ao Author por quê, e o porquê é o que evita a segunda tentativa.
    for forbidden in ("token", "pat", "password", "secret"):
        if forbidden in archive:
            raise ConfigError(
                f"[archive].{forbidden}: credentials are read from the environment, "
                "never from this file."
            )
    _reject_unknown(archive, ("author", "emails"), "[archive]")

    sources: list[Source] = []
    _parse_sources(raw.get("sources", []), sources)

    exclude = raw.get("exclude", {})
    _reject_unknown(exclude, ("artifacts",), "[exclude]")

    collections = []
    for i, entry in enumerate(raw.get("collections", [])):
        where = f"[[collections]] #{i + 1}"
        _reject_unknown(entry, ("name", "artifacts"), where)
        collections.append(
            Collection(
                name=str(_require(entry, "name", where)),
                artifacts=_strings(entry.get("artifacts", []), f"{where}.artifacts"),
            )
        )

    successions = []
    for i, entry in enumerate(raw.get("succession", [])):
        where = f"[[succession]] #{i + 1}"
        _reject_unknown(entry, ("earlier", "later", "note"), where)
        earlier = str(_require(entry, "earlier", where))
        later = str(_require(entry, "later", where))
        if earlier == later:
            raise ConfigError(f"{where}: an Artifact cannot succeed itself.")
        successions.append(
            Succession(earlier=earlier, later=later, note=entry.get("note"))
        )

    markers = []
    for i, entry in enumerate(raw.get("epoch_markers", [])):
        where = f"[[epoch_markers]] #{i + 1}"
        _reject_unknown(entry, ("date", "label"), where)
        markers.append(
            EpochMarker(
                date=str(_require(entry, "date", where)),
                label=str(_require(entry, "label", where)),
            )
        )

    return Config(
        author=archive.get("author"),
        emails=_strings(archive.get("emails", []), "[archive].emails"),
        sources=tuple(sources),
        excluded=_strings(exclude.get("artifacts", []), "[exclude].artifacts"),
        collections=tuple(collections),
        successions=tuple(successions),
        epoch_markers=tuple(markers),
        **_parse_publish(raw.get("publish", {})),
        **_parse_identity(raw.get("identity", {})),
    )


def load(directory: Path | str = ".") -> Config:
    """Load the archive's config. An absent file is valid — zero setup is the demo path."""
    path = Path(directory) / CONFIG_NAME
    if not path.exists():
        return Config()
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    return parse(raw)
