"""Rótulos gerados são `Private project N`, numerados do id ordenado.

ADR-0011: a numeração vem do id ordenado, nunca da ordem de descoberta. Dois
builds do mesmo store produzem os mesmos rótulos; a ordem em que os scans
chegaram não tem voz. E um campo desconhecido em `reveal` é recusado, nunca
ignorado — esquecimento aqui é vazamento.
"""

from core import privacy
from core.config import Alias, Config, ConfigError
from tests.support import archives
from tests.support.fixtures import FixtureCase


class LabelsComeFromSortedIds(FixtureCase):
    def labels_for(self, *artifact_ids):
        artifacts = [
            archives.artifact(aid, visibility="private") for aid in artifact_ids
        ]
        config = Config(aliases=(Alias(id=aid) for aid in artifact_ids))
        selection = privacy.select(artifacts, config=config)
        return {a.id: a.name for a in selection.included}

    def test_numbering_follows_the_sorted_id_not_discovery_order(self):
        by_unsorted = self.labels_for("root-c", "root-a", "root-b")
        by_sorted = self.labels_for("root-a", "root-b", "root-c")
        self.assertEqual(by_unsorted, by_sorted)
        self.assertEqual(
            sorted(by_unsorted.values()),
            ["Private project 1", "Private project 2", "Private project 3"],
        )
        self.assertEqual(by_unsorted["root-a"], "Private project 1")

    def test_an_explicit_label_is_never_replaced(self):
        artifacts = [archives.artifact("root-a", visibility="private")]
        config = Config(aliases=(Alias(id="root-a", label="Anonymous fintech project"),))
        selection = privacy.select(artifacts, config=config)
        self.assertEqual(selection.included[0].name, "Anonymous fintech project")

    def test_a_newly_scanned_artifact_that_sorts_last_keeps_the_others_stable(self):
        before = self.labels_for("root-a", "root-b")
        after = self.labels_for("root-a", "root-b", "root-c")
        self.assertEqual(
            {k: v for k, v in after.items() if k in before}, before
        )

    def test_an_insertion_before_existing_ids_shifts_them_deterministically(self):
        # Nota sobre a ADR-0011: a numeração posicional sobre ids ordenados é
        # determinística — o mesmo store produz sempre os mesmos rótulos, e um
        # Artifact novo que ordena ANTES dos existentes desloca os seguintes de
        # forma visível e estável no diff, nunca pela ordem de descoberta.
        # A estabilidade total sob inserção arbitrária exigiria persistir o
        # rótulo no store, o que conflita com "tudo além do store é derivado"
        # (ADR-0002); escolheu-se o determinismo.
        before = self.labels_for("root-b", "root-c")
        after = self.labels_for("root-a", "root-b", "root-c")
        self.assertNotEqual(after["root-b"], before["root-b"])
        again = self.labels_for("root-c", "root-a", "root-b")
        self.assertEqual(again, after)


class AnUnknownRevealFieldIsRejected(FixtureCase):
    def test_config_error_not_silence(self):
        from core import config as config_module

        with self.assertRaises(ConfigError) as ctx:
            config_module.parse({
                "publish": {"alias": [{
                    "id": archives.PRIVATE_ID,
                    "reveal": ["name", "bogus"],
                }]},
            })
        self.assertIn("bogus", str(ctx.exception))

    def test_the_disclosed_list_is_exhaustive(self):
        # `reveal` é lista de divulgação: só o que ela nomeia cruza. Não há
        # como expressar "tudo menos X", porque esse controle faz o
        # esquecimento virar o modo de falha (ADR-0011).
        from core import privacy
        from core.config import REVEAL_FIELDS

        self.assertEqual(
            REVEAL_FIELDS, ("period", "tools", "authorship", "dependencies")
        )
        # Uma lista só. `core.privacy` já teve a sua própria cópia, com um campo
        # a mais, e nada quebrou — porque ninguém a lia. Um campo publicável a
        # mais de um lado é um vazamento do outro.
        self.assertIs(privacy.REVEAL_FIELDS, REVEAL_FIELDS)
