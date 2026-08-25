"""Thin wrappers over the `git` binary.

Collectors know about repositories and commits; the graph does not (Principle V).
Everything git-shaped lives behind this module.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path


class GitError(Exception):
    pass


def _env() -> dict:
    # Isola de config da máquina e nunca deixa o git pedir credencial numa
    # execução desatendida.
    env = dict(os.environ)
    env.update(
        {
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "",
        }
    )
    return env


# O helper lê a variável de ambiente; o corpo em argv cita o nome, nunca o valor.
TOKEN_VARIABLE = "DENDRO_GIT_TOKEN"
CREDENTIAL_HELPER = (
    '!f() { echo username=x-access-token; echo "password=$%s"; }; f' % TOKEN_VARIABLE
)


def git(*args: str, cwd: Path | str | None = None, env_extra: dict | None = None) -> str:
    env = _env()
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def is_repository(path: Path | str) -> bool:
    try:
        git("rev-parse", "--git-dir", cwd=path)
        return True
    except (GitError, FileNotFoundError, NotADirectoryError):
        return False


def has_commits(path: Path | str) -> bool:
    try:
        git("rev-parse", "--verify", "HEAD", cwd=path)
        return True
    except GitError:
        return False


def root_commits(path: Path | str) -> list[str]:
    """Every commit with no parent, newest first as git reports them."""
    if not has_commits(path):
        return []
    out = git("rev-list", "--max-parents=0", "HEAD", cwd=path)
    return [line.strip() for line in out.split("\n") if line.strip()]


def commit_date(path: Path | str, sha: str) -> str:
    """Committer date of one commit, as an ISO-8601 instant."""
    return git("show", "-s", "--format=%cI", sha, cwd=path).strip()


@dataclass(frozen=True)
class Entry:
    """One file in the committed tree."""

    path: str
    size: int
    blob: str


def tree_entries(path: Path | str) -> list[Entry]:
    """Every file in HEAD, with its size, read without a working tree.

    `git ls-files` reads the index, and a `--no-checkout` clone has no index —
    it returns nothing, which is how Tool, Technique and Dependency detection
    came back empty for every repository cloned from GitHub. `ls-tree` reads the
    commit, so it works the same whether or not the tree was ever checked out.
    """
    if not has_commits(path):
        return []
    out = git("ls-tree", "-r", "--long", "-z", "HEAD", cwd=path)
    entries = []
    for record in out.split("\0"):
        if not record:
            continue
        meta, _, name = record.partition("\t")
        fields = meta.split()
        if len(fields) < 4:
            continue
        mode, kind, blob, size = fields[0], fields[1], fields[2], fields[3]
        # Symlinks e submódulos não têm conteúdo próprio para ler.
        if kind != "blob" or mode == "120000":
            continue
        entries.append(Entry(path=name, size=int(size), blob=blob))
    return sorted(entries, key=lambda e: e.path)


def tracked_files(path: Path | str) -> list[str]:
    """Every tracked file, as POSIX paths. Works with or without a checkout."""
    if has_commits(path):
        return [entry.path for entry in tree_entries(path)]
    out = git("ls-files", "-z", cwd=path)
    return [p for p in out.split("\0") if p]


def read_blob(path: Path | str, relative: str) -> bytes | None:
    """The committed bytes of one file, with or without a working tree."""
    if not has_commits(path):
        absolute = Path(path) / relative
        try:
            return absolute.read_bytes()
        except OSError:
            return None
    result = subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=str(path),
        env=_env(),
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def blob_digests(path: Path | str, blobs) -> dict:
    """sha256 of each blob, in one `git cat-file --batch` process.

    One process per file would be thousands of processes on a large repository.
    """
    wanted = list(dict.fromkeys(blobs))
    if not wanted:
        return {}
    proc = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        cwd=str(path),
        env=_env(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    # Escreve num thread: com muitos objetos o pipe de saída enche antes de
    # terminarmos de escrever a entrada, e os dois lados travam.
    def feed():
        try:
            proc.stdin.write(("\n".join(wanted) + "\n").encode("ascii"))
            proc.stdin.close()
        except (BrokenPipeError, ValueError):
            pass

    writer = threading.Thread(target=feed, daemon=True)
    writer.start()

    digests: dict = {}
    out = proc.stdout
    try:
        for _ in wanted:
            header = out.readline()
            if not header:
                break
            fields = header.split()
            if len(fields) < 3:
                # "<sha> missing" — objeto ausente, segue para o próximo.
                continue
            size = int(fields[2])
            digest = hashlib.sha256()
            remaining = size
            while remaining > 0:
                chunk = out.read(min(remaining, 1 << 20))
                if not chunk:
                    break
                digest.update(chunk)
                remaining -= len(chunk)
            out.read(1)  # o \n que o git escreve depois do conteúdo
            digests[fields[0].decode("ascii")] = digest.hexdigest()
    finally:
        out.close()
        writer.join(timeout=5)
        proc.wait(timeout=30)
    return digests


@dataclass(frozen=True)
class Commit:
    sha: str
    author_name: str
    author_email: str
    date: str  # ISO-8601


def log(path: Path | str) -> list[Commit]:
    if not has_commits(path):
        return []
    out = git("log", "--format=%H%x1f%an%x1f%ae%x1f%aI", cwd=path)
    commits = []
    # split("\n") e não splitlines(): splitlines() também quebra em \x1c-\x1e,
    # o que engoliria qualquer separador de registro que usássemos.
    for line in out.split("\n"):
        if not line.strip():
            continue
        sha, name, email, date = line.split("\x1f")
        commits.append(Commit(sha=sha, author_name=name, author_email=email, date=date))
    return commits


def numstat(path: Path | str) -> list[tuple[str, int, int]]:
    """Per-commit line counts as (author_email, added, deleted).

    Binary files report `-` for both counts; they contribute zero rather than
    crashing the scan.
    """
    if not has_commits(path):
        return []
    out = git("log", "--format=%x1e%ae", "--numstat", cwd=path)
    rows: list[tuple[str, int, int]] = []
    email = None
    for line in out.split("\n"):
        if line.startswith("\x1e"):
            email = line[1:].strip()
            continue
        if not line.strip() or email is None:
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added = 0 if parts[0] == "-" else int(parts[0])
        deleted = 0 if parts[1] == "-" else int(parts[1])
        rows.append((email, added, deleted))
    return rows


def clone(url: str, target: Path | str, token: str | None = None) -> Path:
    """Clone with complete history and no working tree.

    Complete because root-commit identity and per-author counts depend on it
    (FR-024); no working tree because nothing here ever reads the checkout, and
    a bare-ish clone of 500 repositories is the difference between fitting in a
    temp directory and not.
    """
    target = Path(target)
    options: list[str] = []
    env_extra: dict = {}
    if token:
        # O token vai pelo ambiente, não pelos argumentos nem pela URL: a
        # mensagem de GitError repete a linha de comando inteira e acaba no
        # relatório da varredura, e um segredo não pode viajar por ali.
        options = ["-c", f"credential.helper={CREDENTIAL_HELPER}"]
        env_extra = {TOKEN_VARIABLE: token}
    git(*options, "clone", "--quiet", "--no-checkout", url, str(target), env_extra=env_extra)
    return target
