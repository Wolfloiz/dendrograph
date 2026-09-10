"""Todo comando nos READMEs tem que sobreviver a ser colado num shell.

O primeiro comando dos três passos já foi um `gh repo create --template` que
não podia funcionar. Depois foi `scan github:<your-account>`: em zsh e bash
`<palavra` é redirecionamento de entrada, então o shell tenta abrir o arquivo e
falha antes de a CLI existir. Duas vezes o mesmo defeito com formas diferentes,
e nenhuma das duas quebrava teste nenhum.

Este arquivo não roda os comandos — vários tocam a rede ou o disco de quem lê.
Ele checa o que é verificável sem executar: que a sintaxe é válida para o shell,
que nada dentro de um bloco `bash` é um placeholder que o shell interpreta, e
que as duas traduções mandam colar a mesma coisa. A ADR-0001 põe a CLI do lado
inglês e a documentação nos dois idiomas: a prosa traduz, o comando não.
"""

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
READMES = (ROOT / "README.md", ROOT / "README.pt-br.md")

# `<algo>` é o que a documentação usa como placeholder e o shell lê como
# arquivo. É o par de ângulos que importa aqui.
PLACEHOLDER = re.compile(r"<[^>]*>")

# Os únicos placeholders que a tradução troca. Tudo o mais é a CLI, e a CLI
# não é traduzida.
TRANSLATED = (("SUA-CONTA", "YOUR-ACCOUNT"), ("o-projeto", "the-project"))


def bash_blocks(path: Path) -> list[str]:
    return re.findall(r"```bash\n(.*?)```", path.read_text(encoding="utf-8"), re.S)


def commands(path: Path) -> list[str]:
    out = []
    for block in bash_blocks(path):
        for line in block.splitlines():
            bare = line.split("#", 1)[0].strip()
            if bare:
                out.append(bare)
    return out


class EveryPastedCommandSurvivesTheShell(unittest.TestCase):
    def test_no_block_carries_an_angle_bracket_placeholder(self):
        for readme in READMES:
            for block in bash_blocks(readme):
                for line in block.splitlines():
                    found = PLACEHOLDER.search(line.split("#", 1)[0])
                    self.assertIsNone(
                        found,
                        f"{readme.name}: {found.group(0) if found else ''} in "
                        f"{line.strip()!r} — the shell reads this as a redirect, not as a "
                        "placeholder. Use YOUR-ACCOUNT, not <your-account>.",
                    )

    def test_every_block_parses_as_shell(self):
        # `bash -n` lê e não executa: pega aspas abertas, `fi` faltando, e o
        # redirecionamento sem alvo que um placeholder deixa para trás.
        for readme in READMES:
            blocks = bash_blocks(readme)
            self.assertTrue(blocks, f"{readme.name} has no bash blocks; did the format change?")
            for block in blocks:
                done = subprocess.run(
                    ["bash", "-n"], input=block, text=True, capture_output=True
                )
                self.assertEqual(
                    done.returncode, 0,
                    f"bash rejects this block in {readme.name}:\n{block}\n{done.stderr}",
                )


class TheTwoReadmesAskForTheSameCommands(unittest.TestCase):
    """Duas cópias das mesmas instruções é uma cópia que envelhece sozinha.

    Corrigir um comando num idioma e esquecer o outro não quebra nada visível,
    e o leitor em português passa a colar o comando de ontem.
    """

    def test_the_command_lines_match_one_for_one(self):
        english = commands(READMES[0])
        translated = commands(READMES[1])
        for pt, en in TRANSLATED:
            translated = [line.replace(pt, en) for line in translated]
        self.assertEqual(
            english, translated,
            "README.md and README.pt-br.md no longer ask for the same commands",
        )


if __name__ == "__main__":
    unittest.main()
