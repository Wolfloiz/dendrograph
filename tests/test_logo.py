"""A marca existe em dois lugares, e os dois têm que desenhar a mesma coisa.

`views/logo.svg` é o arquivo — favicon do site e imagem do README, onde só o
`prefers-color-scheme` do sistema está disponível. O header de `index.html`
carrega a mesma marca inline, porque a página tem um botão de tema e um
`<img>` não enxerga esse botão.

Duas cópias da mesma geometria é uma cópia que envelhece sozinha: mexer no
desenho e esquecer a outra não quebra nada visível em teste nenhum, e o site
passa a mostrar um logo e o README outro. Este arquivo compara as duas.
"""

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIEWS = ROOT / "views"

INLINE_MARK = re.compile(r'<svg class="mark".*?</svg>', re.S)

# Atributos que dizem onde a marca está sendo usada, não o que ela desenha.
CONTEXT = frozenset({
    "class", "role", "focusable", "width", "height",
    "aria-hidden", "aria-label", "aria-labelledby",
})


def shape(svg: str) -> list:
    """A geometria e a cor, sem o contexto de uso e sem namespace."""
    drawing = []
    for element in ET.fromstring(svg).iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag in ("title", "style"):
            continue
        attrs = {k: v for k, v in element.attrib.items() if k not in CONTEXT}
        drawing.append((tag, tuple(sorted(attrs.items()))))
    return drawing


class TheMarkIsTheSameInBothPlaces(unittest.TestCase):
    def setUp(self):
        self.file = (VIEWS / "logo.svg").read_text(encoding="utf-8")
        page = (VIEWS / "index.html").read_text(encoding="utf-8")
        found = INLINE_MARK.search(page)
        self.assertTrue(found, "index.html no longer carries an inline .mark svg")
        self.inline = found.group(0)

    def test_the_file_and_the_header_draw_the_same_mark(self):
        self.assertEqual(
            shape(self.file), shape(self.inline),
            "views/logo.svg and the inline mark in index.html have drifted apart",
        )

    def test_both_take_every_colour_from_the_design_system(self):
        # Nenhum hex solto: no arquivo as cores vêm do seu próprio <style>, e na
        # página vêm de style.css. Um literal aqui é uma cor que não troca de
        # tema junto com o resto.
        for name, svg in (("logo.svg", self.file), ("index.html", self.inline)):
            body = svg.split("</style>")[-1]
            self.assertNotRegex(
                body, r'(?:fill|stroke)="#',
                f"{name} paints the mark with a literal colour instead of a token",
            )

    def test_the_file_declares_both_themes(self):
        # O favicon e o README renderizam fora da página, longe do style.css:
        # sem a media query a marca fica com as cores do tema claro no escuro.
        self.assertIn("prefers-color-scheme: dark", self.file)

    def test_the_page_asks_for_the_favicon_that_ships(self):
        page = (VIEWS / "index.html").read_text(encoding="utf-8")
        self.assertIn('<link rel="icon" href="logo.svg"', page)


if __name__ == "__main__":
    unittest.main()
