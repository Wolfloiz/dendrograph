"""A máquina propõe, o Author dispõe (Principle I, ADR-0009).

O invariante desta suíte é único e severo: **nenhuma aresta `SUCCEEDS` existe no
grafo sem uma linha de config que a confirme** (FR-011, SC-008). Tudo o mais
aqui existe para tornar esse invariante difícil de quebrar por acidente.
"""

import unittest

from core import graph, prune, suggest
from core.config import Collection, Config, Merge, Succession
from core.store import Artifact, Authorship, Source


def artifact(artifact_id, name, first, last, tools=(), **kwargs):
    return Artifact(
        id=artifact_id,
        identity={"method": "root-commit", "value": artifact_id},
        name=name,
        activity={"first": first, "last": last},
        tools=[{"name": t} for t in tools],
        **kwargs,
    )


def sequence():
    return [
        artifact("root-old", "tinybox", "2022-01-01", "2024-04-22", ("Shell", "Python")),
        artifact("root-new", "tinyos", "2024-05-02", "2026-01-01", ("Shell", "Python")),
    ]


class NoSucceedsEdgeWithoutConfirmation(unittest.TestCase):
    def succeeds(self, artifacts, config=None):
        payload = graph.build(artifacts, config=config)
        return [e for e in payload["edges"] if e["type"] == "SUCCEEDS"]

    def test_a_strong_candidate_still_produces_no_edge(self):
        # O par que `suggest` propõe com mais confiança continua sem aresta.
        proposals = suggest.propose(sequence())
        self.assertTrue(proposals.succeeds, "the fixture stopped being a candidate")
        self.assertEqual(self.succeeds(sequence()), [])

    def test_no_edge_appears_with_an_empty_config(self):
        self.assertEqual(self.succeeds(sequence(), Config()), [])

    def test_a_collection_does_not_imply_a_succession(self):
        config = Config(collections=(Collection("Both", ("root-old", "root-new")),))
        self.assertEqual(self.succeeds(sequence(), config), [])

    def test_the_confirming_line_creates_it(self):
        config = Config(successions=(Succession("root-old", "root-new"),))
        edges = self.succeeds(sequence(), config)
        self.assertEqual(len(edges), 1)

    def test_it_is_oriented_from_the_later_artifact_to_the_earlier(self):
        config = Config(successions=(Succession("root-old", "root-new"),))
        edge = self.succeeds(sequence(), config)[0]
        self.assertEqual(edge["from"], "root-new")
        self.assertEqual(edge["to"], "root-old")

    def test_a_note_travels_onto_the_edge(self):
        config = Config(successions=(Succession("root-old", "root-new", "the rewrite"),))
        self.assertEqual(self.succeeds(sequence(), config)[0]["note"], "the rewrite")

    def test_confirming_an_artifact_that_is_not_stored_creates_nothing(self):
        # Um id que ainda não existe pode estar num HD desconectado; não é erro,
        # e também não é motivo para inventar uma aresta pendurada no nada.
        config = Config(successions=(Succession("root-old", "root-absent"),))
        self.assertEqual(self.succeeds(sequence(), config), [])

    def test_every_edge_type_in_the_graph_is_declared_in_the_schema(self):
        config = Config(successions=(Succession("root-old", "root-new"),))
        payload = graph.build(sequence(), config=config)
        declared = set(payload["schema"]["edge_types"])
        self.assertTrue({e["type"] for e in payload["edges"]} <= declared)


class SuggestionsAreOfferedNotApplied(unittest.TestCase):
    def test_a_succession_is_proposed_with_its_evidence(self):
        proposal = suggest.propose(sequence()).succeeds[0]
        self.assertIn("tinyos", proposal.summary)
        self.assertIn("2024-04-22", proposal.because)

    def test_the_proposal_prints_the_line_that_would_confirm_it(self):
        proposal = suggest.propose(sequence()).succeeds[0]
        self.assertIn("[[succession]]", proposal.config_line)
        self.assertIn('earlier = "root-old"', proposal.config_line)
        self.assertIn('later = "root-new"', proposal.config_line)

    def test_a_confirmed_pair_is_not_proposed_again(self):
        config = Config(successions=(Succession("root-old", "root-new"),))
        self.assertEqual(suggest.propose(sequence(), config).succeeds, [])

    def test_overlapping_projects_are_not_a_sequence(self):
        overlapping = [
            artifact("root-a", "thing", "2022-01-01", "2025-01-01", ("Python",)),
            artifact("root-b", "thingy", "2023-01-01", "2026-01-01", ("Python",)),
        ]
        self.assertEqual(suggest.propose(overlapping).succeeds, [])

    def test_unrelated_names_are_not_a_sequence(self):
        unrelated = [
            artifact("root-a", "invoices", "2022-01-01", "2023-01-01", ("Python",)),
            artifact("root-b", "weather", "2023-06-01", "2024-01-01", ("Python",)),
        ]
        self.assertEqual(suggest.propose(unrelated).succeeds, [])

    def test_a_decade_long_gap_is_not_a_sequence(self):
        distant = [
            artifact("root-a", "thing", "2001-01-01", "2002-01-01", ("Python",)),
            artifact("root-b", "thing2", "2020-01-01", "2021-01-01", ("Python",)),
        ]
        self.assertEqual(suggest.propose(distant).succeeds, [])

    def test_the_output_says_plainly_that_nothing_was_created(self):
        text = suggest.propose(sequence()).render()
        self.assertIn("Nothing above has been created", text)

    def test_an_empty_archive_says_so_without_inventing_work(self):
        self.assertIn("Nothing to propose", suggest.propose([]).render())


class CollectionsAreProposedNotAssigned(unittest.TestCase):
    def group(self):
        return [
            artifact(f"root-{i}", f"thing{i}", "2022-01-01", "2023-01-01", ("Python", "Docker"))
            for i in range(4)
        ]

    def test_a_shared_tool_set_is_proposed(self):
        self.assertTrue(suggest.propose(self.group()).collections)

    def test_no_in_collection_edge_appears_without_config(self):
        payload = graph.build(self.group())
        self.assertEqual([e for e in payload["edges"] if e["type"] == "IN_COLLECTION"], [])

    def test_the_config_line_creates_the_membership(self):
        config = Config(collections=(Collection("Tools", ("root-0", "root-1")),))
        payload = graph.build(self.group(), config=config)
        edges = [e for e in payload["edges"] if e["type"] == "IN_COLLECTION"]
        self.assertEqual(len(edges), 2)

    def test_an_artifact_with_an_unanswered_suggestion_stays_usable_and_ungrouped(self):
        # FR-021: nada fica bloqueado esperando confirmação.
        payload = graph.build(self.group())
        nodes = [n for n in payload["nodes"] if n["type"] == "Artifact"]
        self.assertEqual(len(nodes), 4)
        self.assertEqual([n for n in payload["nodes"] if n["type"] == "Collection"], [])

    def test_two_artifacts_are_not_enough_to_be_worth_asking_about(self):
        self.assertEqual(suggest.propose(self.group()[:2]).collections, [])

    def test_a_single_shared_tool_is_a_filter_not_a_collection(self):
        loose = [
            artifact(f"root-{i}", f"thing{i}", "2022-01-01", "2023-01-01", ("Python",))
            for i in range(5)
        ]
        self.assertEqual(suggest.propose(loose).collections, [])


class RewrittenHistoryIsProposedForMerging(unittest.TestCase):
    def pair(self):
        files = {
            "algorithm": "sha256",
            "authored_files": [{"path": "engine.py", "size": 900, "hash": "a" * 64}],
        }
        return [
            artifact("root-before", "thing", "2020-01-01", "2021-01-01", content_hashes=files),
            artifact("root-after", "thing", "2021-02-01", "2023-01-01", content_hashes=files),
        ]

    def test_identical_authored_files_under_different_roots_are_proposed(self):
        proposals = suggest.propose(self.pair()).identity_merges
        self.assertEqual(len(proposals), 1)
        self.assertIn("[[identity.merge]]", proposals[0].config_line)

    def test_a_declared_merge_is_not_proposed_again(self):
        config = Config(merges=(Merge(ids=("root-before", "root-after")),))
        self.assertEqual(suggest.propose(self.pair(), config).identity_merges, [])

    def test_different_files_are_not_proposed(self):
        one, two = self.pair()
        two.content_hashes = {
            "algorithm": "sha256",
            "authored_files": [{"path": "other.py", "size": 900, "hash": "b" * 64}],
        }
        self.assertEqual(suggest.propose([one, two]).identity_merges, [])


class PruneOffersAnOpinionAndNothingElse(unittest.TestCase):
    def clutter(self):
        fork = artifact("root-fork", "someone-elses", "2019-01-01", "2019-02-01")
        fork.sources = [Source("github", "https://github.com/x/y", "2026-01-01", "2026-01-01", is_fork=True)]
        fork.authorship = [Authorship("them@example.com", 500, 5000, 100, "2019-01-01", "2019-02-01"),
                           Authorship("me@example.com", 1, 2, 0, "2019-02-01", "2019-02-01")]
        keeper = artifact("root-mine", "mine", "2020-01-01", "2026-01-01", ("Python",))
        keeper.authorship = [Authorship("me@example.com", 300, 4000, 200, "2020-01-01", "2026-01-01")]
        return [fork, keeper]

    def report(self, config=None):
        return prune.candidates(self.clutter(), config or Config(emails=("me@example.com",)))

    def test_a_barely_touched_fork_is_a_candidate(self):
        ids = [c.artifact_id for c in self.report().candidates]
        self.assertEqual(ids, ["root-fork"])

    def test_real_work_is_not_a_candidate(self):
        self.assertNotIn("root-mine", [c.artifact_id for c in self.report().candidates])

    def test_the_reason_is_stated_so_the_author_can_disagree(self):
        self.assertIn("fork", self.report().candidates[0].reason)

    def test_it_prints_the_line_that_would_exclude_them(self):
        self.assertIn('artifacts = ["root-fork"]', self.report().config_block())

    def test_it_says_plainly_that_nothing_was_deleted(self):
        self.assertIn("Nothing was deleted", self.report().render())

    def test_an_artifact_the_author_opted_in_is_never_suggested(self):
        config = Config(emails=("me@example.com",), opt_in=("root-fork",))
        self.assertEqual(prune.candidates(self.clutter(), config).candidates, [])

    def test_an_artifact_in_a_collection_is_never_suggested(self):
        config = Config(
            emails=("me@example.com",),
            collections=(Collection("Kept", ("root-fork",)),),
        )
        self.assertEqual(prune.candidates(self.clutter(), config).candidates, [])

    def test_an_excluded_artifact_is_reported_as_recoverable_not_re_suggested(self):
        config = Config(emails=("me@example.com",), excluded=("root-fork",))
        report = prune.candidates(self.clutter(), config)
        self.assertEqual(report.candidates, [])
        self.assertEqual(report.already_excluded, ["root-fork"])
        self.assertIn("brings them back intact", report.render())


class EpochMarkersAreDeclaredNeverInferred(unittest.TestCase):
    def test_a_marker_reaches_the_graph_from_config(self):
        from core.config import EpochMarker

        config = Config(epoch_markers=(EpochMarker("2023-03-14", "AI assistants arrive"),))
        payload = graph.build(sequence(), config=config)
        markers = [n for n in payload["nodes"] if n["type"] == "EpochMarker"]
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0]["date"], "2023-03-14")
        self.assertEqual(markers[0]["label"], "AI assistants arrive")

    def test_no_marker_is_invented_from_activity(self):
        payload = graph.build(sequence())
        self.assertEqual([n for n in payload["nodes"] if n["type"] == "EpochMarker"], [])


if __name__ == "__main__":
    unittest.main()


class LineageEdgesCarryTheirEvidence(unittest.TestCase):
    """DERIVES_FROM é inferido, então nunca viaja sem o que o sustenta (SC-008)."""

    def relation(self, **kwargs):
        base = {
            "from": "root-old",
            "to": "root-new",
            "confidence": "high",
            "evidence": [{"kind": "path", "at": "engine.py"}],
        }
        base.update(kwargs)
        return base

    def edges(self, lineage):
        payload = graph.build(sequence(), lineage=lineage)
        return [e for e in payload["edges"] if e["type"] == "DERIVES_FROM"]

    def test_a_detected_relation_becomes_an_edge(self):
        self.assertEqual(len(self.edges([self.relation()])), 1)

    def test_it_carries_confidence_and_evidence(self):
        edge = self.edges([self.relation()])[0]
        self.assertEqual(edge["confidence"], "high")
        self.assertEqual(edge["evidence"], [{"kind": "path", "at": "engine.py"}])

    def test_no_edge_is_emitted_when_nothing_was_detected(self):
        self.assertEqual(self.edges([]), [])

    def test_a_relation_naming_an_absent_artifact_creates_nothing(self):
        self.assertEqual(self.edges([self.relation(to="root-absent")]), [])

    def test_the_orientation_is_the_one_the_detector_produced(self):
        # older → newer, como contracts/graph.md pede e lineage.py implementa.
        edge = self.edges([self.relation()])[0]
        self.assertEqual((edge["from"], edge["to"]), ("root-old", "root-new"))

    def test_the_detector_drives_it_when_no_lineage_is_passed(self):
        # T077 é da faixa do agente A. Sem o módulo, o grafo não emite aresta
        # nenhuma — que é o comportamento correto e já coberto acima.
        try:
            from core.analysis import lineage as lineage_module
        except ImportError:
            self.skipTest("core/analysis/lineage.py not delivered yet (T077, agent A)")

        files = [
            {"path": f"f{i}.py", "size": 900, "hash": chr(97 + i) * 64} for i in range(4)
        ]
        shared = {"algorithm": "sha256", "authored_files": files}
        pair = [
            artifact("root-old", "thing", "2020-01-01", "2021-01-01", content_hashes=shared),
            artifact("root-new", "thing2", "2022-01-01", "2023-01-01", content_hashes=shared),
        ]
        self.assertTrue(lineage_module.candidates(pair), "the fixture stopped matching")
        payload = graph.build(pair)
        self.assertTrue([e for e in payload["edges"] if e["type"] == "DERIVES_FROM"])
