"""FR-015 is a prohibition, and a prohibition with no gate is a wish.

dendrograph does not judge quality, does not prove complexity, and does not infer
whether a person or a model wrote something. All three are refused outright rather
than merely unimplemented (Principle V)."""

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from collectors.git import scan  # noqa: E402
from core import build as build_module  # noqa: E402
from core import store  # noqa: E402
from core.analysis import techniques  # noqa: E402
from support.fixtures import FixtureCase  # noqa: E402

# Vocabulário que o Princípio V recusa. Se algum destes aparecer numa saída,
# a ferramenta passou a afirmar algo que declarou não afirmar.
FORBIDDEN = re.compile(
    r"\b(quality[_ ]?score|code[_ ]?quality|grade|rating|maintainability[_ ]?index|"
    r"complexity[_ ]?(score|proof)|big[- ]?o|ai[_ -]?(generated|authored|written)|"
    r"human[_ -]?written|llm[_ -]?(generated|authored))\b",
    re.IGNORECASE,
)


class NoJudgement(FixtureCase):
    def build_all_modes(self):
        repository = self.unbundle("multi-contributor")
        store.save(
            scan.observe(repository, kind="local", locator=str(repository),
                         visibility="public", seen="2026-08-25"),
            self.tmp / "archive",
        )
        for mode in ("public", "redacted", "full"):
            yield mode, build_module.build(
                self.tmp / "archive", mode=mode, generated_at="2026-08-25T00:00:00Z"
            )

    def test_no_output_claims_quality_complexity_or_ai_authorship(self):
        for mode, payload in self.build_all_modes():
            text = json.dumps(payload)
            match = FORBIDDEN.search(text)
            self.assertIsNone(
                match, f"{mode} build asserts {match.group(0) if match else ''}"
            )

    def test_no_artifact_node_carries_a_score(self):
        for _, payload in self.build_all_modes():
            for node in payload["nodes"]:
                self.assertNotIn("score", node)
                self.assertNotIn("grade", node)
                self.assertNotIn("quality", node)

    def test_no_technique_rule_infers_authorship_or_quality(self):
        for name, _confidence, _pattern in techniques.RULES:
            self.assertIsNone(
                FORBIDDEN.search(name), f"Technique rule {name!r} makes a refused claim"
            )

    def test_confidence_is_a_declared_strength_not_a_quality_score(self):
        # Confidence diz quão firmemente a Technique é reivindicada, nunca quão
        # bom é o trabalho (CONTEXT.md).
        from core.analysis.evidence import (
            CONFIDENCE_HIGH,
            CONFIDENCE_LOW,
            CONFIDENCE_MEDIUM,
        )

        self.assertEqual(
            {CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW},
            {"high", "medium", "low"},
        )
        for _name, confidence, _pattern in techniques.RULES:
            self.assertIn(confidence, {"high", "medium", "low"})

    def test_every_technique_carries_evidence(self):
        # Uma Technique sem evidência é inválida e nunca é produzida (SC-006).
        repository = self.unbundle("multi-contributor")
        from collectors.git import plumbing

        found = techniques.detect(plumbing.tracked_files(repository))
        self.assertTrue(found)
        for technique in found:
            self.assertTrue(technique["evidence"])
            for pointer in technique["evidence"]:
                self.assertIn("kind", pointer)
                self.assertIn("detail", pointer)


if __name__ == "__main__":
    unittest.main()


class TheProhibitionCoversEveryFileOnDisk(FixtureCase):
    """O grafo em memória passar não basta: o que sai no disco é o que é lido.

    `graph.sqlite` e `llms.txt` carregam o mesmo payload em outras formas, e uma
    prosa gerada é justamente onde um julgamento entraria sem ninguém notar.
    """

    def written_files(self):
        repository = self.unbundle("multi-contributor")
        store.save(
            scan.observe(repository, kind="local", locator=str(repository),
                         visibility="public", seen="2026-08-25"),
            self.tmp / "archive",
        )
        for mode in ("public", "redacted", "full"):
            build_module.build(
                self.tmp / "archive", mode=mode, generated_at="2026-08-25T00:00:00Z"
            )
            directory = build_module.output_dir(self.tmp / "archive", mode)
            for path in sorted(directory.iterdir()):
                yield mode, path

    def test_no_written_output_asserts_quality_or_authorship(self):
        checked = 0
        for mode, path in self.written_files():
            raw = path.read_bytes()
            # sqlite é binário; decodifica com tolerância para varrer o texto.
            text = raw.decode("utf-8", errors="ignore")
            match = FORBIDDEN.search(text)
            self.assertIsNone(
                match, f"{mode}/{path.name} asserts {match.group(0) if match else ''}"
            )
            checked += 1
        self.assertGreater(checked, 6, "the sweep did not reach the new outputs")

    def test_the_sweep_actually_reaches_sqlite_and_the_prose(self):
        names = {path.name for _, path in self.written_files()}
        self.assertIn("graph.sqlite", names)
        self.assertIn("llms.txt", names)
