#!/usr/bin/env python3
"""Debug script to trace beam search fill algorithm."""

import json
import sys
import os

# Add cli/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cli', 'src'))

# Import after path setup
import importlib
grid_module = importlib.import_module('core.grid')
beam_module = importlib.import_module('fill.beam_search_autofill')
pattern_module = importlib.import_module('fill.pattern_matcher')

Grid = grid_module.Grid
BeamSearchAutofill = beam_module.BeamSearchAutofill
PatternMatcher = pattern_module.PatternMatcher

# Load grid
print("Loading grid...")
with open('test_grids/empty_15x15.json') as f:
    data = json.load(f)

grid = Grid.from_dict(data)

# Check empty slots
empty_slots = grid.get_empty_slots()
print(f"Empty slots found: {len(empty_slots)}")

# Create minimal wordlist
print("\nCreating pattern matcher...")
wordlist = ["HELLO", "WORLD", "TEST", "PUZZLE", "CROSSWORD"]
pattern_matcher = PatternMatcher(wordlists=wordlist)

# Initialize beam search
print("Initializing beam search...")
autofill = BeamSearchAutofill(
    grid=grid,
    pattern_matcher=pattern_matcher,
    beam_width=3,
    candidates_per_slot=5,
    min_score=0,
    theme_entries=None
)

# Check theme_entries
print(f"Theme entries: {autofill.theme_entries}")
print(f"Theme entries type: {type(autofill.theme_entries)}")
print(f"Theme entries.keys(): {list(autofill.theme_entries.keys())}")

# Run fill with timeout
print("\nRunning fill...")
try:
    result = autofill.fill(timeout=10)
    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Slots filled: {result.slots_filled}/{result.total_slots}")
    print(f"  Iterations: {result.iterations}")
    print(f"  Time: {result.time_elapsed:.2f}s")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
