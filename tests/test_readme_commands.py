"""Todo comando no README tem que sobreviver a ser colado num shell.

O primeiro comando dos três passos já foi um `gh repo create --template` que
não podia funcionar. Depois foi `scan github:<your-account>`: em zsh e bash
`<palavra` é redirecionamento de entrada, então o shell tenta abrir o arquivo e
falha antes de a CLI existir. Duas vezes o mesmo defeito com formas diferentes,
e nenhuma das duas quebrava teste nenhum.

Este arquivo não roda os comandos — vários tocam a rede ou o disco de quem lê.
Ele checa o que é verificável sem executar: que a sintaxe é válida para o shell,
e que nada dentro de um bloco `bash` é um placeholder que o shell interpreta.
"""

import re
import subprocess
import unittest
from pathlib import Path

README = Path(__file__).resolve().parent.parent / "README.md"

# `<algo>` e `>algo` são redirecionamento; `|` e `&` fora de contexto mudam o
# comando. O que importa aqui é o par de ângulos, que é o que a documentação
# usa como placeholder e o shell usa como arquivo.
PLACEHOLDER = re.compile(r"<[^>]*>")


def bash_blocks() -> list[str]:
    return re.findall(r"```bash\n(.*?)```", README.read_text(encoding="utf-8"), re.S)


class EveryPastedCommandSurvivesTheShell(unittest.TestCase):
    def setUp(self):
        self.blocks = bash_blocks()
        self.assertTrue(self.blocks, "README has no bash blocks; did the format change?")

    def test_no_block_carries_an_angle_bracket_placeholder(self):
        for block in self.blocks:
            for line in block.splitlines():
                bare = line.split("#", 1)[0]
                found = PLACEHOLDER.search(bare)
                self.assertIsNone(
                    found,
                    f"{found.group(0) if found else ''} in {line.strip()!r} — the shell reads "
                    "this as a redirect, not as a placeholder. Use YOUR-ACCOUNT, not <your-account>.",
                )

    def test_every_block_parses_as_shell(self):
        # `bash -n` lê e não executa: pega aspas abertas, `fi` faltando, e o
        # redirecionamento sem alvo que um placeholder deixa para trás.
        for block in self.blocks:
            done = subprocess.run(
                ["bash", "-n"], input=block, text=True, capture_output=True
            )
            self.assertEqual(
                done.returncode, 0,
                f"bash rejects this block:\n{block}\n{done.stderr}",
            )


if __name__ == "__main__":
    unittest.main()
