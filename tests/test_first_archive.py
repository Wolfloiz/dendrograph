"""O primeiro arquivo de alguém tem quase nada dentro, e não pode parecer quebrado.

É o estado que todo adotante vê antes de qualquer outro: o template recém-copiado,
ou um scan que encontrou um repositório só. A terceira condição de aceitação da US4 —
*parar depois do passo um deixa uma coisa funcionando, não uma metade quebrada* — não
era verdade enquanto nada verificava isto, e nada verificava.

Um grafo de um nó, uma linha do tempo de uma linha e uma busca sem o que achar são
estados normais. Erro é outra coisa.
"""

import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import build, config, store  # noqa: E402
from support import archives  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "archive"


class TheTemplateBuildsBeforeAnythingIsScanned(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dendro-first-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        shutil.copytree(TEMPLATE, self.tmp / "archive")
        self.archive = self.tmp / "archive"

    def build(self):
        build.build(self.archive, config=config.load(self.archive))
        return build.output_dir(self.archive, build.MODE_PUBLIC)

    def test_an_empty_archive_still_produces_a_screen(self):
        site = self.build()
        for name in ("index.html", "screen.js", "view-graph.js", "view-timeline.js",
                     "view-tool.js", "graph.js"):
            self.assertTrue((site / name).exists(), name)

    def test_an_empty_graph_is_a_state_not_an_error(self):
        site = self.build()
        payload = (site / "graph.js").read_text(encoding="utf-8")
        self.assertIn("DENDROGRAPH_GRAPH", payload)
        self.assertIn('"nodes": []', payload)
        self.assertIn('"edges": []', payload)
        # O schema viaja mesmo vazio: quem abre um arquivo sem nada ainda
        # precisa saber o que ele teria dentro (FR-017).
        self.assertIn('"node_types"', payload)

    def test_one_artifact_is_enough_to_render_everything(self):
        archives.write(
            self.archive,
            archives.artifact(
                "root-first",
                name="my-first-thing",
                description="The one repository I have.",
                tools=("Python",),
                activity={"first": "2026-01-01", "last": "2026-02-01"},
            ),
        )
        site = self.build()
        payload = (site / "graph.json").read_text(encoding="utf-8")
        self.assertIn("my-first-thing", payload)
        # Um Artifact, uma Tool, um Period: nós de sobra para desenhar.
        import json

        graph = json.loads(payload)
        kinds = {n["type"] for n in graph["nodes"]}
        self.assertIn("Artifact", kinds)
        self.assertIn("Tool", kinds)
        self.assertGreaterEqual(len(graph["edges"]), 1)

    def test_the_prose_summary_survives_an_almost_empty_archive(self):
        # `llms.txt` é gerado por concatenação e é onde um arquivo vazio vira
        # uma frase sem sujeito.
        site = self.build()
        text = (site / "llms.txt").read_text(encoding="utf-8")
        self.assertIn("dendrograph", text)
        self.assertNotIn("None", text)
        self.assertNotIn("undefined", text)


class TheReadmePathIsThreeSteps(unittest.TestCase):
    """FR-015: três passos, e nenhum deles pede que se abra um arquivo-fonte."""

    def setUp(self):
        self.text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.section = self.text.split("## Three steps to your own archive")[1]
        self.section = self.section.split("\n## ")[0]

    def test_there_are_exactly_three(self):
        steps = re.findall(r"^\*\*(\d)\. ", self.section, re.M)
        self.assertEqual(steps, ["1", "2", "3"], steps)

    def test_each_step_says_what_success_looks_like(self):
        # Sem isto a falha aparece no fim, longe do passo que a causou.
        self.assertEqual(self.section.count("*You should see*"), 3)

    def test_the_publishing_step_states_what_the_site_does_not_contain(self):
        # Princípio IV: a afirmação sobre privacidade tem que estar onde a
        # pessoa publica, não num capítulo que ela pode não ler.
        for claim in ("Private Artifacts are not in it",
                      "No contributor's email address is in it",
                      "No path from your machine is in it"):
            self.assertIn(claim, self.section, claim)

    def test_no_step_asks_anyone_to_read_the_source(self):
        for phrase in ("see the code", "read the source", "look at core/", "in core/"):
            self.assertNotIn(phrase, self.section.lower())


if __name__ == "__main__":
    unittest.main()
