"""
Constraint analyzer for crossword grids.

Computes per-cell constraint data (how many words can fill each crossing slot)
and placement impact analysis (how placing a word affects neighboring slots).
"""

from typing import Any, Dict


def analyze_constraints(grid, word_list, pattern_matcher) -> Dict[str, Any]:
    """
    Analyze constraints for every white cell in the grid.

    For each white cell, counts valid words for the across and down slot
    passing through it. Returns per-cell data and a summary.

    Args:
        grid: Grid object
        word_list: WordList object (unused directly, but pattern_matcher is built from it)
        pattern_matcher: TriePatternMatcher or PatternMatcher instance

    Returns:
        Dict with 'constraints' (per-cell data) and 'summary' keys.
    """
    slots = grid.get_word_slots()

    # Count matches per slot (cache by slot identity)
    slot_counts = {}
    for slot in slots:
        slot_key = (slot["row"], slot["col"], slot["direction"])
        pattern = grid.get_pattern_for_slot(slot)
        matches = pattern_matcher.find(pattern, min_score=0)
        slot_counts[slot_key] = len(matches)

    # Build cell-to-slot mapping
    cell_across = {}  # (row, col) -> match count for across slot
    cell_down = {}  # (row, col) -> match count for down slot

    for slot in slots:
        slot_key = (slot["row"], slot["col"], slot["direction"])
        count = slot_counts[slot_key]
        row, col = slot["row"], slot["col"]

        for i in range(slot["length"]):
            if slot["direction"] == "across":
                cell = (row, col + i)
            else:
                cell = (row + i, col)

            if slot["direction"] == "across":
                cell_across[cell] = count
            else:
                cell_down[cell] = count

    # Build per-cell constraint dict
    constraints = {}
    all_white_cells = set()

    for row in range(grid.size):
        for col in range(grid.size):
            if not grid.is_black(row, col):
                all_white_cells.add((row, col))

    for cell in all_white_cells:
        row, col = cell
        across = cell_across.get(cell, 0)
        down = cell_down.get(cell, 0)
        # Use min when both directions exist; otherwise use whichever exists.
        # NOTE: must check `is not None` (not truthiness) — zero options is valid.
        if cell in cell_across and cell in cell_down:
            min_opts = min(across, down)
        else:
            min_opts = across or down

        constraints[f"{row},{col}"] = {
            "across_options": across,
            "down_options": down,
            "min_options": min_opts,
        }

    # Summary
    total_cells = len(constraints)
    critical = sum(1 for c in constraints.values() if c["min_options"] < 5)
    avg_min = sum(c["min_options"] for c in constraints.values()) / total_cells if total_cells > 0 else 0

    return {
        "constraints": constraints,
        "summary": {
            "total_cells": total_cells,
            "critical_cells": critical,
            "average_min_options": round(avg_min, 1),
        },
    }


def analyze_placement_impact(grid, word: str, slot: Dict, word_list, pattern_matcher) -> Dict[str, Any]:
    """
    Analyze how placing a word affects crossing slot options.

    Args:
        grid: Grid object
        word: Word to place (e.g., "OCEAN")
        slot: Target slot dict with 'row', 'col', 'direction', 'length'
        word_list: WordList object
        pattern_matcher: Pattern matcher instance

    Returns:
        Dict with 'impacts' (per-crossing-slot data) and 'summary' keys.
    """
    all_slots = grid.get_word_slots()
    target_cells = set()
    row, col = slot["row"], slot["col"]

    for i in range(slot["length"]):
        if slot["direction"] == "across":
            target_cells.add((row, col + i))
        else:
            target_cells.add((row + i, col))

    # Find crossing slots (slots that share at least one cell with target)
    crossing_slots = []
    for s in all_slots:
        s_id = (s["row"], s["col"], s["direction"])
        # Skip the target slot itself
        if s_id == (slot["row"], slot["col"], slot["direction"]):
            continue

        s_cells = set()
        for i in range(s["length"]):
            if s["direction"] == "across":
                s_cells.add((s["row"], s["col"] + i))
            else:
                s_cells.add((s["row"] + i, s["col"]))

        if s_cells & target_cells:
            crossing_slots.append(s)

    # Compute before counts
    before_counts = {}
    for s in crossing_slots:
        pattern = grid.get_pattern_for_slot(s)
        matches = pattern_matcher.find(pattern, min_score=0)
        s_key = f"{s['row']},{s['col']},{s['direction']}"
        before_counts[s_key] = len(matches)

    # Place word temporarily in a clone
    cloned_grid = grid.clone()
    cloned_grid.place_word(word.upper(), slot["row"], slot["col"], slot["direction"])

    # Compute after counts
    after_counts = {}
    for s in crossing_slots:
        pattern = cloned_grid.get_pattern_for_slot(s)
        matches = pattern_matcher.find(pattern, min_score=0)
        s_key = f"{s['row']},{s['col']},{s['direction']}"
        after_counts[s_key] = len(matches)

    # Build impacts
    impacts = {}
    for s_key in before_counts:
        before = before_counts[s_key]
        after = after_counts.get(s_key, 0)
        # Find the slot to get its length
        s_parts = s_key.split(",")
        s_slot = next(
            (
                s
                for s in crossing_slots
                if s["row"] == int(s_parts[0]) and s["col"] == int(s_parts[1]) and s["direction"] == s_parts[2]
            ),
            None,
        )
        impacts[s_key] = {
            "before": before,
            "after": after,
            "delta": after - before,
            "length": s_slot["length"] if s_slot else 0,
        }

    # Summary
    worst_delta = min((i["delta"] for i in impacts.values()), default=0)
    eliminated = sum(1 for i in impacts.values() if i["after"] == 0)

    return {
        "impacts": impacts,
        "summary": {
            "total_crossings": len(impacts),
            "worst_delta": worst_delta,
            "crossings_eliminated": eliminated,
        },
    }
