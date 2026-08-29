"""Exit codes and the run report. A scheduled run has to be able to tell
"nothing to see" from "half your archive was skipped"."""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cli  # noqa: E402
from core.report import EXIT_FAILURE, EXIT_OK, EXIT_PARTIAL, EXIT_USAGE, RunReport  # noqa: E402


def run(*argv) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class ExitCodes(unittest.TestCase):
    def test_no_command_is_a_usage_error(self):
        code, _, err = run()
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("usage", err.lower())

    def test_an_unknown_command_is_a_usage_error(self):
        with self.assertRaises(SystemExit) as caught:
            run("teleport")
        self.assertEqual(caught.exception.code, EXIT_USAGE)

    def test_a_command_that_cannot_complete_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Sem argumento e sem [[sources]]: não há o que varrer.
            code, _, err = run("scan", "--root", tmp)
        self.assertEqual(code, EXIT_FAILURE)
        self.assertIn("dendro:", err)
        self.assertIn("nothing to scan", err)

    def test_no_command_ever_writes_into_the_current_directory_by_default(self):
        # FR-023: nenhum comando escreve dado de Author no repositório da
        # ferramenta. Um --root que cai em "." por descuido é como isso aconteceria.
        with tempfile.TemporaryDirectory() as tmp:
            run("build", "--root", tmp)
            self.assertTrue((Path(tmp) / "site" / "graph.json").exists())
        self.assertFalse(Path("site").exists(), "build wrote into the tool repository")

    def test_a_broken_config_exits_one_and_names_the_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "dendrograph.toml").write_text('[publish]\nmoed = "public"\n')
            code, _, err = run("prune", "--root", tmp)
        self.assertEqual(code, EXIT_FAILURE)
        self.assertIn("moed", err)

    def test_a_clean_run_exits_zero(self):
        self.assertEqual(RunReport().exit_code, EXIT_OK)

    def test_an_unreachable_source_exits_three_not_zero(self):
        report = RunReport(unreachable=["/media/backup"])
        self.assertEqual(report.exit_code, EXIT_PARTIAL)


class Report(unittest.TestCase):
    def test_a_dry_run_says_it_wrote_nothing(self):
        report = RunReport(dry_run=True, added=["root-aaa"])
        self.assertIn("nothing was written", report.render())

    def test_unreachable_sources_are_reported_not_omitted(self):
        report = RunReport(unreachable=["/media/backup", "github:author"])
        rendered = report.render()
        self.assertIn("/media/backup", rendered)
        self.assertIn("github:author", rendered)
        self.assertIn("never as deleted", rendered)

    def test_declarations_naming_unseen_artifacts_are_reported_not_fatal(self):
        report = RunReport(declared_but_unseen=["root-ghost"])
        self.assertIn("root-ghost", report.render())
        self.assertEqual(report.exit_code, EXIT_OK)

    def test_counts_are_stated_even_when_nothing_happened(self):
        self.assertIn("0 Artifact(s) added", RunReport().render())


class Surface(unittest.TestCase):
    def test_exactly_the_seven_commands_fr020_requires(self):
        self.assertEqual(
            sorted(cli.COMMANDS),
            ["build", "login", "prune", "publish", "scan", "search", "suggest"],
        )

    def test_dry_run_is_offered_by_every_command_that_writes(self):
        parser = cli.build_parser()
        writing = {"scan", "build", "publish"}
        actions = parser._subparsers._group_actions[0].choices  # noqa: SLF001
        for name in writing:
            flags = {o for a in actions[name]._actions for o in a.option_strings}
            self.assertIn("--dry-run", flags, f"{name} writes but has no --dry-run")

    def test_full_is_a_build_flag_never_a_published_mode(self):
        self.assertIn("full", cli.BUILD_MODES)
        from core.config import PUBLISH_MODES

        self.assertNotIn("full", PUBLISH_MODES)


if __name__ == "__main__":
    unittest.main()
