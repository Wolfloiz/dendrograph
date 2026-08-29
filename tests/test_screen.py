"""O site publicado é uma tela, e é essa a lista de arquivos.

As duas páginas viraram uma. Um build que continuasse copiando `graph.html` e
`timeline.html` — porque alguém os recriou, ou porque o glob pegou uma sobra —
publicaria três telas concorrentes sem ninguém notar: as antigas até abririam,
com metade do comportamento e nenhuma navegação de volta.

Endereços antigos quebram nesta versão, de propósito e sem stub de redirect
(research.md, R8). O que este arquivo garante é que quebrem *inteiro*, e não
que sobrevivam pela metade.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import build, config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VIEWS = ROOT / "views"
TEMPLATE = ROOT / "templates" / "archive"

# contracts/screen.md, "Files the build emits".
SHELL = ("index.html", "screen.js", "view-graph.js", "view-timeline.js")
CARRIED = ("loader.js", "theme.js", "style.css")
DATA = ("graph.js", "graph.json", "graph.sqlite", "llms.txt")
GONE = ("graph.html", "timeline.html")


class TheSiteIsOneScreen(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dendro-screen-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        shutil.copytree(TEMPLATE, self.tmp / "archive")
        self.archive = self.tmp / "archive"
        build.build(self.archive, config=config.load(self.archive))
        self.site = build.output_dir(self.archive, build.MODE_PUBLIC)

    def test_the_shell_and_its_views_ship(self):
        for name in SHELL + CARRIED + DATA:
            self.assertTrue((self.site / name).exists(), f"{name} is not in the site")

    def test_the_two_old_pages_are_gone_from_the_site(self):
        for name in GONE:
            self.assertFalse(
                (self.site / name).exists(),
                f"{name} is still published — two screens competing is worse than one"
                " address that breaks",
            )

    def test_the_two_old_pages_are_gone_from_the_repository(self):
        # O build copia `views/*.html` por glob: enquanto o arquivo existir aqui
        # ele volta a ser publicado, e o teste acima passaria a mentir.
        for name in GONE:
            self.assertFalse((VIEWS / name).exists(), f"views/{name} is back")

    def test_only_one_html_page_is_published(self):
        pages = sorted(p.name for p in self.site.glob("*.html"))
        self.assertEqual(pages, ["index.html"], pages)


class TheShellCarriesNoRendering(unittest.TestCase):
    """A casca é marcação e uma chamada; quem desenha são os módulos."""

    def test_index_html_has_no_inline_script(self):
        text = (VIEWS / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>", text, "the shell grew logic of its own")

    def test_index_html_loads_every_module_it_needs(self):
        text = (VIEWS / "index.html").read_text(encoding="utf-8")
        for name in ("graph.js", "loader.js", "theme.js",
                     "view-graph.js", "view-timeline.js", "screen.js"):
            self.assertIn(f'src="{name}"', text, name)

    def test_the_views_own_no_stylesheet_of_their_own(self):
        # O `<style>` de cada página migrou para `style.css`, porque num
        # documento só as duas folhas se contradiziam — o grafo pedia
        # `overflow: hidden` no body, o que deixaria a linha do tempo sem
        # rolagem.
        for module in ("view-graph.js", "view-timeline.js"):
            self.assertNotIn("<style", (VIEWS / module).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
