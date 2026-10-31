"""
Unit tests for the two engine save sites that no CLI run reaches
(clue-authoring spec 0.1.4, section 3.5): the beam orchestrator's pause metadata
and ``HybridAutofill``'s forwarding of ``carried_clues`` to its inner beam engine.

``BeamSearchAutofill`` passes ``task_id=None`` on purpose, so the orchestrator's
own save is unreachable from ``fill``/``resume``; the contract tests it here.
Nothing is written outside ``tmp_path``.
"""

import gzip
import json

from cli.src.core.clues import NULL_CLUES, engine_clues, store_carried_clues
from cli.src.core.grid import Grid
from cli.src.fill import hybrid_autofill
from cli.src.fill import state_manager as state_manager_module
from cli.src.fill.beam_search.orchestrator import BeamSearchOrchestrator
from cli.src.fill.beam_search.state import BeamState
from cli.src.fill.hybrid_autofill import HybridAutofill
from cli.src.fill.state_manager import StateManager
from cli.src.fill.trie_pattern_matcher import TriePatternMatcher
from cli.src.fill.word_list import WordList

CLUES = {
    "0,0,across": {"text": "Opening entry", "answer": "???"},
    "5,5,down": {"text": "Orphaned", "answer": "XY"},
}
TASK_ID = "engine_carry"


def make_orchestrator():
    word_list = WordList(["CAT", "BAT", "ACE", "ACT", "ART"])
    return BeamSearchOrchestrator(
        Grid(11), word_list, TriePatternMatcher(word_list), beam_width=2, candidates_per_slot=5, task_id=TASK_ID
    )


def save_pause_metadata(monkeypatch, tmp_path, carried_clues):
    """Trigger the orchestrator's pause save; return the saved state's metadata."""

    class TmpStateManager(StateManager):
        def __init__(self, *args, **kwargs):
            super().__init__(storage_dir=tmp_path)

    monkeypatch.setattr(state_manager_module, "StateManager", TmpStateManager)
    orchestrator = make_orchestrator()
    orchestrator.carried_clues = carried_clues
    beam = [BeamState(grid=orchestrator.grid.clone(), slots_filled=0, total_slots=1, score=50.0)]

    orchestrator._save_state_and_pause(beam, set(), 0, [], 1)

    state_file = tmp_path / f"{TASK_ID}.json.gz"
    assert state_file.exists(), "the orchestrator saved no state under tmp_path"
    with gzip.open(state_file, "rt", encoding="utf-8") as f:
        envelope = json.load(f)
    assert envelope["algorithm"] == "beam"
    return envelope["metadata"]


def test_orchestrator_pause_state_stores_the_carried_clues(monkeypatch, tmp_path):
    metadata = save_pause_metadata(monkeypatch, tmp_path, CLUES)

    assert metadata.get("clues") == CLUES


def test_orchestrator_pause_state_without_carried_clues_has_no_clues_key(monkeypatch, tmp_path):
    metadata = save_pause_metadata(monkeypatch, tmp_path, None)

    assert "clues" not in metadata


class FakeBeam:
    """Stands in for the inner BeamSearchAutofill and records what hybrid set on it."""

    instances = []

    def __init__(self, *args, **kwargs):
        self.carried_clues = "UNSET"
        FakeBeam.instances.append(self)

    def fill(self, timeout):
        class Result:
            paused = True

        return Result()


def run_hybrid(monkeypatch, carried_clues):
    FakeBeam.instances = []
    monkeypatch.setattr(hybrid_autofill, "BeamSearchAutofill", FakeBeam)
    word_list = WordList(["CAT", "BAT", "ACE"])
    hybrid = HybridAutofill(Grid(11), word_list, TriePatternMatcher(word_list))
    hybrid.carried_clues = carried_clues

    hybrid.fill(timeout=30)

    assert len(FakeBeam.instances) == 1
    return FakeBeam.instances[0]


def test_hybrid_forwards_carried_clues_to_its_inner_beam_engine(monkeypatch):
    beam = run_hybrid(monkeypatch, CLUES)

    assert beam.carried_clues == CLUES


def test_hybrid_forwards_no_clues_as_none(monkeypatch):
    beam = run_hybrid(monkeypatch, None)

    assert beam.carried_clues is None


# --- engine_clues / store_carried_clues: absent, null, map -------------------


def stored(carry):
    metadata = {}
    store_carried_clues(metadata, engine_clues(carry))
    return metadata


def test_engine_clues_is_none_for_an_absent_key():
    assert engine_clues({}) is None


def test_engine_clues_is_the_null_sentinel_for_a_null_value():
    assert engine_clues({"clues": None}) is NULL_CLUES


def test_engine_clues_passes_a_map_through():
    assert engine_clues({"clues": CLUES}) == CLUES


def test_absent_clues_reach_the_metadata_as_no_key():
    assert "clues" not in stored({})


def test_null_clues_reach_the_metadata_as_a_null_value():
    assert stored({"clues": None}).get("clues", "ABSENT") is None


def test_a_clues_map_reaches_the_metadata_unchanged():
    assert stored({"clues": CLUES}).get("clues", "ABSENT") == CLUES


def test_an_empty_clues_map_reaches_the_metadata_as_an_empty_map():
    assert stored({"clues": {}}).get("clues", "ABSENT") == {}
