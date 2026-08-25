# Contract: `store/artifacts/<id>.json`

One committed JSON file per Artifact. **This is the source of truth** (ADR-0002).
Everything else in the archive is derived from these files and can be deleted and
rebuilt; these cannot.

Lives in the Author's archive repository, never in the tool repository (ADR-0010).

## File naming

`store/artifacts/<id>.json`, where `<id>` is the Artifact id — see *Identity* below.
The id appears both in the file name and in the `id` field; they must agree.

## Writing rules

- **Append, never rebuild.** A scan merges observations into an existing file. A field
  the current run could not observe is left as it was, never overwritten with null.
- **Deterministic serialisation**: keys sorted, two-space indent, UTF-8, trailing
  newline. A run that observed nothing new must produce a byte-identical file, so
  `git diff` shows only real change (FR-018).
- **A source unreachable this run is not a deletion** (FR-007). Only that source's
  `reachable` flag changes; `last_seen` does not advance for it.

## Shape

```json
{
  "schema_version": 1,
  "id": "root-3f7a1c9e04b2d85f6a1b0c3d2e5f8a9b7c4d1e60",
  "identity": {
    "method": "root_commit",
    "value": "3f7a1c9e04b2d85f6a1b0c3d2e5f8a9b7c4d1e60",
    "fallback_content_hash": null
  },
  "name": "dendrograph",
  "description": "A knowledge graph of what a person has built.",
  "visibility": "public",
  "sources": [
    {
      "kind": "github",
      "locator": "https://github.com/author/dendrograph",
      "first_seen": "2026-08-24",
      "last_seen": "2026-08-24",
      "reachable": true,
      "visibility": "public",
      "is_fork": false,
      "upstream": null
    },
    {
      "kind": "local",
      "locator": "/media/backup/old-projects/dendrograph",
      "first_seen": "2026-08-24",
      "last_seen": "2026-08-24",
      "reachable": false,
      "visibility": "private",
      "is_fork": false,
      "upstream": null
    }
  ],
  "activity": { "first": "2019-03-11", "last": "2026-08-20" },
  "authorship": [
    {
      "author": "luiz@example.com",
      "commits": 412,
      "lines_added": 18422,
      "lines_deleted": 6031,
      "first": "2019-03-11",
      "last": "2026-08-20"
    }
  ],
  "tools": [
    { "name": "Python", "evidence": { "kind": "file_extension", "detail": "*.py" } }
  ],
  "techniques": [
    {
      "name": "Continuous Integration",
      "confidence": "high",
      "evidence": [{ "kind": "path", "detail": ".github/workflows/test.yml" }]
    }
  ],
  "dependencies": [
    { "name": "urllib3", "ecosystem": "pypi", "version": "2.2.1",
      "evidence": { "kind": "manifest", "detail": "requirements.txt" } }
  ],
  "content_hashes": {
    "algorithm": "sha256",
    "authored_files": [
      { "path": "core/identity.py", "size": 4821,
        "hash": "9f8e7d6c5b4a39281706f5e4d3c2b1a09f8e7d6c5b4a39281706f5e4d3c2b1a0" }
    ]
  },
  "last_seen": "2026-08-24",
  "declarations_applied": []
}
```

## Fields

| Field | Type | Notes |
|---|---|---|
| `schema_version` | int | FR-025. Refuse unknown versions. |
| `id` | string | `root-<40 hex>` or `content-<64 hex>`. Matches the file name. |
| `identity.method` | enum | `root_commit` \| `content_hash` \| `override` |
| `identity.value` | string | The hash the id was built from. |
| `identity.fallback_content_hash` | string \| null | Present when `method` is `root_commit` **and** a content hash was also computed, so a later history rewrite can be recognised as the same Artifact (see *Rewritten history*). |
| `name` | string | Last observed name. Never used for identity. |
| `description` | string \| null | May be absent for local sources. |
| `visibility` | enum | `public` \| `private` \| `unknown`. Most permissive across reachable sources is **not** used — see *Visibility*. |
| `sources[]` | array | Every place this Artifact was ever seen. Entries are never removed. |
| `sources[].kind` | enum | `github` \| `local` |
| `sources[].locator` | string | URL for `github`, absolute path for `local`. |
| `sources[].reachable` | bool | As of the last run that attempted it. `false` is not deletion (FR-007). |
| `sources[].is_fork` | bool | Reported by the forge. Independent of identity — a fork shares upstream's root commit and **is** the same Artifact (ADR-0003). |
| `activity.first` / `.last` | date | Earliest and latest commit dates across all observations. Feeds Periods and SC-007. |
| `authorship[]` | array | Per-author commit and line counts. Answers *how much of this is mine*, separately from *which Artifact this is* (FR-006, ADR-0003). |
| `tools[]` | array | Each carries the evidence it was observed from. |
| `techniques[]` | array | Each carries `confidence` and at least one evidence pointer. **A Technique with no evidence is invalid** (FR-010, SC-006). |
| `techniques[].confidence` | enum | `high` \| `medium` \| `low`. Not a quality score (FR-015). |
| `dependencies[]` | array | Third-party work reused. Distinct from Tools (FR-022). |
| `content_hashes` | object | Authored files only, for lineage. See *Authored files*. |
| `last_seen` | date | The last run in which **any** source for this Artifact was reachable. |
| `declarations_applied[]` | array | Config declarations that shaped this file, for traceability. Not authoritative — config is (see `config.md`). |

## Identity

Per ADR-0003 and FR-004:

1. **Primary** — SHA of the repository's root commit. Stable across clone, rename,
   re-host and disk. Id is `root-<sha>`.
2. **Fallback** — SHA-256 over the identity set (see *Two file sets*): every tracked file
   not in an excluded directory, sorted by POSIX path, each contributing
   `path\0size\0sha256(content)`. Used for repositories with no commits, and for future
   non-git Artifacts. Id is `content-<sha>`.
3. **Override** — an Author declaration in config merges or separates Artifacts, and
   always wins (FR-005).

**Multiple root commits.** A repository with more than one root commit (merged
histories) uses the root commit with the earliest committer date; ties break on the
lexicographically smallest SHA. Deterministic, and stable under re-clone.

**No commits and no tracked files.** No stable identity is derivable. The Artifact is
**reported as unidentifiable and not stored** — never assigned a generated id, which
would change between runs and accumulate junk in a store that never deletes.

**Rewritten history.** A squashed import or `filter-branch` changes the root commit, so
the Artifact appears new. `fallback_content_hash` lets `dendro suggest` notice the
overlap and propose a merge, which the Author confirms as an identity override. The tool
never merges them on its own (Principle I).

## Visibility

`visibility` is the **most recently observed** value, not the most permissive across
sources (FR-026). An Artifact seen as public on GitHub in one run and private in the
next is private, and drops out of the published site on the next publish without the
Author acting. When the most recent observation is from an unreachable source,
`visibility` keeps its last known value; it never decays to `public`.

## Two file sets

Identity and lineage need different sets, and conflating them breaks identity.

**The identity set** is every tracked file outside an excluded directory —
`node_modules/`, `vendor/`, `.venv/`, `venv/`, `target/`, `dist/`, `build/`,
`__pycache__/`, `.git/`. **No size floor, and lockfiles are included.** A repository
whose files are all small is perfectly identifiable; it simply has nothing substantial
in it. Excluding by size here would leave such an Artifact with no identity at all.

**The lineage set** is stricter, because a false `DERIVES_FROM` is a false claim about
the Author's work. It takes the identity set and further excludes:

- lockfiles — `package-lock.json`, `yarn.lock`, `poetry.lock`, `Cargo.lock`, and peers
- generated output — anything matched by `.gitignore`, minified bundles
- files under 512 bytes, which are too common to be evidence of shared descent (FR-012)

Both lists are part of this contract. The identity set determines ids, so changing it
changes the ids of already-stored Artifacts — treat additions to it as a schema version
bump. The lineage set only affects inference, so changing it costs a rebuild.
