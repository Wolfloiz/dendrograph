"""`store/artifacts/<id>.json` — the source of truth (ADR-0002).

Everything else in the archive is derived and can be deleted and rebuilt. These
files cannot. Scans append to them; they never rebuild them, and a source that
was unreachable this run is recorded as state, never as removal.

See `specs/001-git-collector/contracts/store-artifact.md` for the contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path

SCHEMA_VERSION = 1

VISIBILITY_PUBLIC = "public"
VISIBILITY_PRIVATE = "private"
VISIBILITY_UNKNOWN = "unknown"


class SchemaVersionError(Exception):
    """Raised for a `schema_version` this build does not recognise (FR-025).

    Never partially read, never rewrite: a version from the future may mean
    anything, and guessing at a committed store is how archives get corrupted.
    """


class StoreError(Exception):
    pass


@dataclass(frozen=True)
class Source:
    """One place an Artifact was seen. Entries are never removed."""

    kind: str
    locator: str
    first_seen: str
    last_seen: str
    reachable: bool = True
    visibility: str = VISIBILITY_UNKNOWN
    is_fork: bool = False
    upstream: str | None = None

    @property
    def key(self) -> tuple[str, str]:
        return (self.kind, self.locator)


@dataclass(frozen=True)
class Authorship:
    author: str
    commits: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    first: str | None = None
    last: str | None = None

    def __post_init__(self):
        # git grava o que a pessoa digitou, e a mesma pessoa digita
        # `Cloud11665@gmail.com` num commit e `cloud11665@gmail.com` no
        # seguinte. Sem normalizar aqui viram dois autores: duas contagens
        # separadas, dois nós Author, e um `share` que não fecha em 1.
        object.__setattr__(self, "author", self.author.strip().lower())


@dataclass
class Artifact:
    id: str
    identity: dict
    name: str | None = None
    description: str | None = None
    visibility: str = VISIBILITY_UNKNOWN
    sources: list[Source] = field(default_factory=list)
    activity: dict = field(default_factory=dict)
    authorship: list[Authorship] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    techniques: list[dict] = field(default_factory=list)
    dependencies: list[dict] = field(default_factory=list)
    content_hashes: dict = field(default_factory=dict)
    last_seen: str | None = None
    declarations_applied: list[str] = field(default_factory=list)

    # ---------- serialização ----------

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "id": self.id,
            "identity": self.identity,
            "name": self.name,
            "description": self.description,
            "visibility": self.visibility,
            "sources": [_source_to_dict(s) for s in self.sources],
            "activity": self.activity,
            "authorship": [_authorship_to_dict(a) for a in self.authorship],
            "tools": self.tools,
            "techniques": self.techniques,
            "dependencies": self.dependencies,
            "content_hashes": self.content_hashes,
            "last_seen": self.last_seen,
            "declarations_applied": self.declarations_applied,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "Artifact":
        version = raw.get("schema_version")
        if version != SCHEMA_VERSION:
            raise SchemaVersionError(
                f"store file declares schema_version {version!r}, "
                f"this build understands {SCHEMA_VERSION}"
            )
        return cls(
            id=raw["id"],
            identity=raw.get("identity", {}),
            name=raw.get("name"),
            description=raw.get("description"),
            visibility=raw.get("visibility", VISIBILITY_UNKNOWN),
            sources=[Source(**s) for s in raw.get("sources", [])],
            activity=raw.get("activity", {}),
            authorship=[Authorship(**a) for a in raw.get("authorship", [])],
            tools=raw.get("tools", []),
            techniques=raw.get("techniques", []),
            dependencies=raw.get("dependencies", []),
            content_hashes=raw.get("content_hashes", {}),
            last_seen=raw.get("last_seen"),
            declarations_applied=raw.get("declarations_applied", []),
        )

    # ---------- acumulação ----------

    def merge(self, observed: "Artifact") -> "Artifact":
        """Fold a fresh observation into what is already known.

        A field the observation could not see is left as it was, never
        overwritten with null: an unreachable drive must not blank an Artifact.
        """
        if observed.id != self.id:
            raise StoreError(f"cannot merge {observed.id} into {self.id}")

        merged_sources = _merge_sources(self.sources, observed.sources)
        return Artifact(
            id=self.id,
            identity=observed.identity or self.identity,
            name=_prefer(observed.name, self.name),
            description=_prefer(observed.description, self.description),
            visibility=_latest_visibility(merged_sources, self.visibility),
            sources=merged_sources,
            activity=_merge_activity(self.activity, observed.activity),
            authorship=_merge_authorship(self.authorship, observed.authorship),
            tools=_merge_named(self.tools, observed.tools),
            techniques=_merge_named(self.techniques, observed.techniques),
            dependencies=_merge_named(self.dependencies, observed.dependencies),
            content_hashes=observed.content_hashes or self.content_hashes,
            last_seen=_max_date(self.last_seen, observed.last_seen),
            declarations_applied=self.declarations_applied,
        )

    def mark_unreachable(self, kind: str, locator: str) -> "Artifact":
        """Record that one source could not be reached. Not a deletion (FR-007)."""
        sources = [
            replace(s, reachable=False) if s.key == (kind, locator) else s
            for s in self.sources
        ]
        # last_seen NÃO avança: nada foi visto nesta execução por esta origem.
        return replace(self, sources=sources)


# ---------- auxiliares de merge ----------


def _prefer(new, old):
    return new if new is not None else old


def _max_date(a: str | None, b: str | None) -> str | None:
    return max([d for d in (a, b) if d], default=None)


def _min_date(a: str | None, b: str | None) -> str | None:
    return min([d for d in (a, b) if d], default=None)


def _merge_sources(existing: list[Source], observed: list[Source]) -> list[Source]:
    by_key = {s.key: s for s in existing}
    for source in observed:
        prior = by_key.get(source.key)
        if prior is None:
            by_key[source.key] = source
        else:
            by_key[source.key] = replace(
                source,
                first_seen=_min_date(prior.first_seen, source.first_seen),
                last_seen=_max_date(prior.last_seen, source.last_seen),
            )
    return sorted(by_key.values(), key=lambda s: s.key)


def _latest_visibility(sources: list[Source], fallback: str) -> str:
    """The most recently observed value, never the most permissive (FR-026).

    Keeps its last known value when nothing was observed; it never decays to
    public, because decaying towards public is how a client's name gets out.
    """
    observed = [s for s in sources if s.visibility != VISIBILITY_UNKNOWN]
    if not observed:
        return fallback
    newest = max(observed, key=lambda s: (s.last_seen or "", s.key))
    return newest.visibility


def _merge_activity(existing: dict, observed: dict) -> dict:
    first = _min_date(existing.get("first"), observed.get("first"))
    last = _max_date(existing.get("last"), observed.get("last"))
    merged = {}
    if first:
        merged["first"] = first
    if last:
        merged["last"] = last
    return merged


def _merge_authorship(
    existing: list[Authorship], observed: list[Authorship]
) -> list[Authorship]:
    """Keep the largest counts seen for each author.

    Two clones that diverged after the same root hold different later commits,
    so neither figure is the union. The larger is taken deliberately: it
    understates rather than overstates, and a tool whose output is repeated in
    interviews must err towards claiming less (ADR-0009).
    """
    by_author = {a.author: a for a in existing}
    for entry in observed:
        prior = by_author.get(entry.author)
        if prior is None:
            by_author[entry.author] = entry
            continue
        by_author[entry.author] = Authorship(
            author=entry.author,
            commits=max(prior.commits, entry.commits),
            lines_added=max(prior.lines_added, entry.lines_added),
            lines_deleted=max(prior.lines_deleted, entry.lines_deleted),
            first=_min_date(prior.first, entry.first),
            last=_max_date(prior.last, entry.last),
        )
    return sorted(by_author.values(), key=lambda a: a.author)


def _merge_named(existing: list[dict], observed: list[dict]) -> list[dict]:
    by_name = {item["name"]: item for item in existing}
    for item in observed:
        by_name[item["name"]] = item
    return sorted(by_name.values(), key=lambda item: item["name"])


def _source_to_dict(source: Source) -> dict:
    return {
        "kind": source.kind,
        "locator": source.locator,
        "first_seen": source.first_seen,
        "last_seen": source.last_seen,
        "reachable": source.reachable,
        "visibility": source.visibility,
        "is_fork": source.is_fork,
        "upstream": source.upstream,
    }


def _authorship_to_dict(entry: Authorship) -> dict:
    return {
        "author": entry.author,
        "commits": entry.commits,
        "lines_added": entry.lines_added,
        "lines_deleted": entry.lines_deleted,
        "first": entry.first,
        "last": entry.last,
    }


# ---------- acesso a arquivo ----------


def artifacts_dir(root: Path | str = ".") -> Path:
    return Path(root) / "store" / "artifacts"


def serialise(artifact: Artifact) -> str:
    """Deterministic: sorted keys, two-space indent, trailing newline.

    A run that observed nothing new must produce a byte-identical file, so
    `git diff` shows only real change (FR-018).
    """
    return json.dumps(artifact.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read(path: Path) -> Artifact:
    return Artifact.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def write(artifact: Artifact, root: Path | str = ".") -> Path:
    directory = artifacts_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{artifact.id}.json"
    path.write_text(serialise(artifact), encoding="utf-8")
    return path


def save(artifact: Artifact, root: Path | str = ".") -> Artifact:
    """Merge an observation into the stored Artifact and write the result."""
    path = artifacts_dir(root) / f"{artifact.id}.json"
    merged = read(path).merge(artifact) if path.exists() else artifact
    write(merged, root)
    return merged


def load_all(root: Path | str = ".") -> list[Artifact]:
    directory = artifacts_dir(root)
    if not directory.exists():
        return []
    return [read(p) for p in sorted(directory.glob("*.json"))]
