"""Config parsing: absent file works, unknown keys are refused, declarations may
name Artifacts that do not exist yet."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import Config, ConfigError, load, parse  # noqa: E402


class AbsentConfig(unittest.TestCase):
    def test_absent_file_is_valid(self):
        # Zero setup é o caminho da demo (SC-001).
        config = load("/nonexistent-directory")
        self.assertEqual(config, Config())
        self.assertEqual(config.publish_mode, "public")
        self.assertEqual(config.sources, ())


class UnknownKeys(unittest.TestCase):
    def test_unknown_top_level_table_is_an_error(self):
        with self.assertRaises(ConfigError) as caught:
            parse({"publsh": {}})
        self.assertIn("publsh", str(caught.exception))

    def test_unknown_key_in_publish_is_an_error(self):
        with self.assertRaises(ConfigError):
            parse({"publish": {"opt_ins": ["root-a"]}})

    def test_unknown_reveal_field_is_refused_not_ignored(self):
        with self.assertRaises(ConfigError) as caught:
            parse({"publish": {"alias": [{"id": "root-a", "reveal": ["everything"]}]}})
        self.assertIn("everything", str(caught.exception))

    def test_credentials_are_refused(self):
        with self.assertRaises(ConfigError) as caught:
            parse({"archive": {"token": "ghp_secret"}})
        self.assertIn("environment", str(caught.exception))

    def test_full_is_not_a_publishable_mode(self):
        with self.assertRaises(ConfigError):
            parse({"publish": {"mode": "full"}})


class Declarations(unittest.TestCase):
    def test_declarations_may_name_artifacts_that_do_not_exist(self):
        # Um id sem arquivo no store não é erro: o Artifact pode estar num
        # drive desconectado. O relatório da execução é que reporta.
        config = parse(
            {
                "publish": {"opt_in": ["root-ghost"]},
                "exclude": {"artifacts": ["root-other"]},
            }
        )
        self.assertIn("root-ghost", config.declared_ids())
        self.assertIn("root-other", config.declared_ids())

    def test_alias_defaults_to_revealing_nothing(self):
        config = parse({"publish": {"alias": [{"id": "root-a"}]}})
        alias = config.alias_for("root-a")
        self.assertEqual(alias.reveal, ())
        self.assertIsNone(alias.label)

    def test_alias_reveal_is_kept_in_order(self):
        config = parse(
            {"publish": {"alias": [{"id": "root-a", "reveal": ["period", "tools"]}]}}
        )
        self.assertEqual(config.alias_for("root-a").reveal, ("period", "tools"))

    def test_merge_needs_two_ids(self):
        with self.assertRaises(ConfigError):
            parse({"identity": {"merge": [{"ids": ["root-a"]}]}})

    def test_sources_take_account_or_path(self):
        config = parse(
            {
                "sources": [
                    {"kind": "github", "account": "author"},
                    {"kind": "local", "path": "/media/backup"},
                ]
            }
        )
        self.assertEqual(
            [(s.kind, s.locator) for s in config.sources],
            [("github", "author"), ("local", "/media/backup")],
        )

    def test_unknown_source_kind_is_an_error(self):
        with self.assertRaises(ConfigError):
            parse({"sources": [{"kind": "gitlab", "account": "author"}]})


class RoundTrip(unittest.TestCase):
    def test_documented_example_parses(self):
        import tempfile

        example = """
[archive]
author = "Luiz"
emails = ["luiz@example.com"]

[[sources]]
kind = "github"
account = "author"

[publish]
mode = "redacted"
opt_in = ["root-a1b2c3"]
target_repository = "author/archive-site"

[[publish.alias]]
id = "root-8c2d5a"
label = "Anonymous fintech project"
reveal = ["period", "tools"]

[exclude]
artifacts = ["root-d4e5f6"]

[[identity.merge]]
ids = ["root-a1b2c3", "root-9f8e7d"]
reason = "history rewritten in 2021"

[[collections]]
name = "Client work"
artifacts = ["root-a1b2c3"]

[[epoch_markers]]
date = "2023-03-14"
label = "AI assistants arrive"
"""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "dendrograph.toml").write_text(example)
            config = load(tmp)
        self.assertEqual(config.publish_mode, "redacted")
        self.assertEqual(config.target_repository, "author/archive-site")
        self.assertEqual(config.alias_for("root-8c2d5a").label, "Anonymous fintech project")
        self.assertEqual(config.collections[0].name, "Client work")
        self.assertEqual(config.epoch_markers[0].date, "2023-03-14")


if __name__ == "__main__":
    unittest.main()
