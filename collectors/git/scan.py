"""discover → clone → analyse → resolve identity → write store.

Everything after discovery is identical whether a repository arrived via
`git clone` or was already on disk: the GitHub path is "discover and clone,
then do the local thing".
"""

from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path

from collectors.git import authorship, clone, github, plumbing
from core import identity as identity_module
from core import store
from core.analysis import dependencies, techniques, tools
from core.report import RunReport


def today() -> str:
    return date.today().isoformat()


class Progress:
    """Reported throughout, because a 30-minute unattended run that prints
    nothing is indistinguishable from one that hung (SC-001b)."""

    def __init__(self, total: int = 0, stream=sys.stderr, enabled: bool = True):
        self.total = total
        self.done = 0
        self.stream = stream
        self.enabled = enabled
        self.started = time.monotonic()

    def step(self, label: str) -> None:
        self.done += 1
        if not self.enabled:
            return
        elapsed = int(time.monotonic() - self.started)
        position = f"{self.done}/{self.total}" if self.total else str(self.done)
        print(f"[{position}] {elapsed:>4}s  {label}", file=self.stream, flush=True)

    def finish(self) -> None:
        if self.enabled:
            elapsed = int(time.monotonic() - self.started)
            print(f"scanned {self.done} in {elapsed}s", file=self.stream, flush=True)


def observe(
    repository: Path | str,
    *,
    kind: str,
    locator: str,
    visibility: str = store.VISIBILITY_UNKNOWN,
    is_fork: bool = False,
    upstream: str | None = None,
    name: str | None = None,
    description: str | None = None,
    emails: tuple[str, ...] = (),
    seen: str | None = None,
) -> store.Artifact:
    """Everything one repository on disk has to say about itself.

    Raises `Unidentifiable` for a repository with neither commits nor tracked
    files: such an Artifact is reported, never stored under a generated id.
    """
    repository = Path(repository)
    seen = seen or today()
    found = identity_module.resolve(repository)
    paths = plumbing.tracked_files(repository)
    counts = authorship.counts(repository)

    return store.Artifact(
        id=found.artifact_id,
        identity=found.to_dict(),
        name=name or repository.name,
        description=description,
        visibility=visibility,
        sources=[
            store.Source(
                kind=kind,
                locator=locator,
                first_seen=seen,
                last_seen=seen,
                reachable=True,
                visibility=visibility,
                is_fork=is_fork,
                upstream=upstream,
            )
        ],
        activity=authorship.activity(counts),
        authorship=counts,
        tools=tools.detect(paths),
        techniques=techniques.detect(paths),
        dependencies=dependencies.detect(repository, paths),
        content_hashes={
            "algorithm": "sha256",
            "authored_files": [
                {"path": path, "size": size, "hash": digest}
                for path, size, digest in identity_module.authored_files(repository)
            ],
        },
        last_seen=seen,
    )


def _persist(observed: store.Artifact, root: Path | str, report: RunReport, dry_run: bool):
    path = store.artifacts_dir(root) / f"{observed.id}.json"
    existed = path.exists()
    if not dry_run:
        store.save(observed, root)
    (report.changed if existed else report.added).append(observed.id)


def scan_github(
    account: str,
    root: Path | str = ".",
    *,
    token: str | None = None,
    emails: tuple[str, ...] = (),
    dry_run: bool = False,
    progress: Progress | None = None,
    report: RunReport | None = None,
) -> RunReport:
    report = report or RunReport()
    found = github.discover(account, token)
    report.unreachable.extend(found.unreachable)
    if token and not found.account_is_authenticated:
        report.notes.append(
            f"The credentials in use are not {account}'s, so only {account}'s "
            "public repositories were visible."
        )

    progress = progress or Progress(total=len(found.repositories))
    progress.total = progress.total or len(found.repositories)

    with clone.working_directory() as workdir:
        for repository in found.repositories:
            progress.step(repository.full_name)
            try:
                checkout = clone.clone_into(
                    repository.clone_url,
                    workdir,
                    repository.full_name.replace("/", "__"),
                    token=token,
                )
            except plumbing.GitError as exc:
                report.unreachable.append(f"{repository.html_url} ({exc})")
                continue
            try:
                observed = observe(
                    checkout,
                    kind="github",
                    locator=repository.html_url,
                    visibility=(
                        store.VISIBILITY_PRIVATE
                        if repository.private
                        else store.VISIBILITY_PUBLIC
                    ),
                    is_fork=repository.is_fork,
                    upstream=repository.upstream,
                    name=repository.name,
                    description=repository.description,
                    emails=emails,
                )
            except identity_module.Unidentifiable:
                report.unidentifiable.append(repository.html_url)
                continue
            _persist(observed, root, report, dry_run)
    progress.finish()
    return report
