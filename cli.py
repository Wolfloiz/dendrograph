"""`dendro` — the command surface.

Six commands, covering exactly what FR-020 requires. dendrograph is a local CLI
first; a scheduled Actions run is one caller of it, not the product's home
(ADR-0007).

See `specs/001-git-collector/contracts/cli.md` for the contract.
"""

from __future__ import annotations

import argparse
import sys

from core import config as config_module
from core.report import EXIT_FAILURE, EXIT_USAGE, RunReport

BUILD_MODES = ("public", "redacted", "full")


class CommandError(Exception):
    """A command could not complete. Exits `1`."""


def _add_common(parser: argparse.ArgumentParser, *, writes: bool = True) -> None:
    parser.add_argument(
        "--root", default=".", help="archive directory (default: current)"
    )
    if writes:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="report what would change and change nothing",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dendro", description="A knowledge graph of what you have built."
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")

    scan = commands.add_parser("scan", help="discover and scan a source")
    scan.add_argument(
        "source",
        nargs="?",
        help="a local path, github:account, or omitted to scan every configured source",
    )
    _add_common(scan)

    login = commands.add_parser("login", help="authenticate against GitHub")
    _add_common(login, writes=False)

    build = commands.add_parser("build", help="rebuild derived outputs from the store")
    build.add_argument("--mode", choices=BUILD_MODES, default="public")
    _add_common(build)

    publish = commands.add_parser("publish", help="produce the publishable site")
    _add_common(publish)

    suggest = commands.add_parser(
        "suggest", help="propose relationships and Collections for confirmation"
    )
    _add_common(suggest, writes=False)

    prune = commands.add_parser("prune", help="list Artifacts that look prunable")
    _add_common(prune, writes=False)

    return parser


# ---------- comandos ----------
# Cada handler devolve um RunReport. Os que dependem de fases posteriores
# levantam CommandError com o nome da tarefa que os entrega, para que uma
# execução prematura diga o que falta em vez de falhar de forma opaca.


def cmd_scan(args, config) -> RunReport:
    from collectors.git import auth, scan as scan_module

    source = args.source
    targets = []
    if source:
        if source.startswith("github:"):
            targets.append(("github", source.split(":", 1)[1]))
        else:
            targets.append(("local", source))
    else:
        targets = [(s.kind, s.locator) for s in config.sources]
    if not targets:
        raise CommandError(
            "nothing to scan. Pass a path or github:account, or list [[sources]] in "
            f"{config_module.CONFIG_NAME}."
        )

    report = RunReport()
    token = auth.resolve_token()
    for kind, locator in targets:
        if kind == "github":
            scan_module.scan_github(
                locator,
                args.root,
                token=token,
                emails=config.emails,
                dry_run=args.dry_run,
                report=report,
            )
        else:
            scan_module.scan_local(
                locator,
                args.root,
                emails=config.emails,
                dry_run=args.dry_run,
                report=report,
            )

    seen = {a.id for a in _stored_ids(args.root)}
    report.declared_but_unseen = sorted(config.declared_ids() - seen)
    return report


def _stored_ids(root):
    from core import store

    return store.load_all(root)


def cmd_login(args, config) -> RunReport:
    from collectors.git import auth

    existing = auth.resolve_token()
    if existing:
        print("Already authenticated from the environment; no browser needed.")
        return RunReport()
    try:
        code = auth.request_device_code()
        print(auth.instructions(code))
        auth.poll_for_token(code)
    except auth.AuthError as exc:
        raise CommandError(str(exc)) from exc
    print(
        "Authenticated. Export the token yourself if you want it to persist — "
        "dendrograph never writes it to disk."
    )
    return RunReport()


def cmd_build(args, config) -> RunReport:
    from core import build as build_module

    if args.dry_run:
        report = RunReport()
        report.changed = [a.id for a in _stored_ids(args.root)]
        return report
    build_module.build(args.root, mode=args.mode, config=config)
    report = RunReport()
    report.changed = [a.id for a in _stored_ids(args.root)]
    if args.mode == build_module.MODE_FULL:
        print(
            f"Full build written to {build_module.LOCAL_DIR}/ — never to "
            f"{build_module.SITE_DIR}/, and never deployed."
        )
    return report


def cmd_publish(args, config) -> RunReport:
    """Publish `site/`, refusing anything that smells like a full build (T065)."""
    from pathlib import Path

    from core import build as build_module
    from core import privacy, store

    report = RunReport()
    site = build_module.output_dir(Path(args.root), build_module.MODE_PUBLIC)

    # Segunda linha de defesa: por construção um build full escreve em
    # .dendro-local/, nunca aqui. A checagem existe porque o custo de errar é
    # uma quebra de NDA, não uma reconstrução.
    previous = _published_state(site)
    if previous["build_mode"] == build_module.MODE_FULL:
        raise CommandError(
            f"{site / 'graph.json'} declares build_mode: full — refusing to publish."
        )

    if args.dry_run:
        selection = privacy.select(
            store.load_all(args.root), config=config, mode=config.publish_mode
        )
        report.withheld = [
            f"{artifact.name or artifact.id} ({reason})"
            for artifact, reason in selection.withheld
        ]
        report.changed = [a.id for a in selection.included]
        return report

    build_module.build(args.root, mode=config.publish_mode, config=config, report=report)

    # FR-026: um Artifact cuja visibilidade mudou tem nome no relatório.
    current = _published_state(site)
    for artifact_id in sorted(previous["artifact_ids"] - current["artifact_ids"]):
        report.withheld.append(f"{artifact_id} (removed by a visibility change)")

    if config.target_repository:
        from core import publish as publish_module

        try:
            summary = publish_module.deploy(site, config.target_repository)
        except publish_module.PublishError as exc:
            raise CommandError(str(exc)) from exc
        report.notes.append(summary)
    else:
        report.notes.append(f"Site ready in {site}/.")
    return report


def _published_state(site):
    """What the last published output contained. Reads `site/` only — never `.dendro-local/`."""
    graph_json = site / "graph.json"
    if not graph_json.exists():
        return {"build_mode": None, "artifact_ids": set()}
    import json

    payload = json.loads(graph_json.read_text(encoding="utf-8"))
    return {
        "build_mode": payload.get("build_mode"),
        "artifact_ids": {
            node["id"] for node in payload.get("nodes", []) if node.get("type") == "Artifact"
        },
    }


def cmd_suggest(args, config) -> RunReport:
    """Proposes. Creates nothing (FR-011, FR-021, Principle I)."""
    from core import suggest

    artifacts = _stored_ids(args.root)
    if not artifacts:
        raise CommandError(
            f"nothing in the store yet. Run `dendro scan` first."
        )
    print(suggest.propose(artifacts, config).render())
    return RunReport()


def cmd_prune(args, config) -> RunReport:
    """Prints candidates and the lines that would exclude them. Deletes nothing (FR-008)."""
    from core import prune

    artifacts = _stored_ids(args.root)
    if not artifacts:
        raise CommandError("nothing in the store yet. Run `dendro scan` first.")
    print(prune.candidates(artifacts, config).render())
    return RunReport()


# Comandos que só leem. Ver contracts/cli.md: "Writes: Nothing — prints".
READ_ONLY_COMMANDS = frozenset({"suggest", "prune"})

COMMANDS = {
    "scan": cmd_scan,
    "login": cmd_login,
    "build": cmd_build,
    "publish": cmd_publish,
    "suggest": cmd_suggest,
    "prune": cmd_prune,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help(sys.stderr)
        return EXIT_USAGE

    try:
        config = config_module.load(args.root)
    except config_module.ConfigError as exc:
        print(f"dendro: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    try:
        report = COMMANDS[args.command](args, config)
    except CommandError as exc:
        print(f"dendro: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    report.dry_run = getattr(args, "dry_run", False)
    # `suggest` e `prune` não escrevem nada: "0 Artifact(s) added, 0 changed"
    # depois deles é ruído que sugere que houve uma escrita a considerar.
    if args.command not in READ_ONLY_COMMANDS:
        print(report.render())
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
