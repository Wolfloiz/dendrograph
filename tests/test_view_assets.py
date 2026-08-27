"""Tudo que uma view referencia tem que existir no site publicado.

O defeito que este arquivo previne já esteve a um passo de acontecer: as views
passaram de quatro arquivos irmãos para doze — `theme.js`, sete woff2 e a
licença delas — e o `emit` que os copia é uma lista de extensões. Uma view que
passe a referenciar um `.svg` continua parecendo correta no repositório e sai
quebrada no site, onde ninguém tem como consertar.

A outra metade é a Princípio III: a página não busca nada na rede. Uma URL
absoluta numa view é uma CDN, e uma CDN é um site que deixa de abrir de um pen
drive com a rede desligada (FR-016, ADR-0004).
"""

import re
import shutil
import tempfile
import unittest
from pathlib import Path

from core import build, config

ROOT = Path(__file__).resolve().parent.parent
VIEWS = ROOT / "views"
TEMPLATE = ROOT / "templates" / "archive"

REFERENCE = re.compile(r'(?:src|href)="([^"]+)"|url\("([^"]+)"\)')


def references(text: str) -> set[str]:
    found = set()
    for src, url in REFERENCE.findall(text):
        found.add(src or url)
    return found


class TheViewsReachNothingOnTheNetwork(unittest.TestCase):
    def test_no_view_names_an_absolute_url(self):
        for path in sorted(VIEWS.rglob("*")):
            if path.suffix not in (".html", ".css", ".js"):
                continue
            for reference in references(path.read_text(encoding="utf-8")):
                self.assertFalse(
                    reference.startswith(("http://", "https://", "//")),
                    f"{path.name} reaches {reference}",
                )


class EveryReferenceShipsWithTheSite(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dendro-assets-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        shutil.copytree(TEMPLATE, self.tmp / "archive")
        self.archive = self.tmp / "archive"
        build.build(self.archive, config=config.load(self.archive))
        self.site = build.output_dir(self.archive, build.MODE_PUBLIC)

    def test_every_relative_reference_exists_in_the_built_site(self):
        checked = 0
        for path in sorted(VIEWS.rglob("*")):
            if path.suffix not in (".html", ".css"):
                continue
            for reference in references(path.read_text(encoding="utf-8")):
                if reference.startswith(("http", "//", "#", "data:")):
                    continue
                self.assertTrue(
                    (self.site / reference).exists(),
                    f"{path.name} references {reference}, which the build does not copy",
                )
                checked += 1
        self.assertGreater(checked, 8, "the sweep did not reach the fonts")

    def test_a_bundled_font_carries_its_licence(self):
        fonts = list(self.site.glob("fonts/*.woff2"))
        self.assertTrue(fonts, "no font shipped")
        licences = list(self.site.glob("fonts/LICENSE*"))
        self.assertTrue(
            licences, "fonts ship without the licence that permits redistributing them"
        )

    def test_the_two_views_ship_at_all(self):
        for name in ("timeline.html", "graph.html", "loader.js", "style.css"):
            self.assertTrue((self.site / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
