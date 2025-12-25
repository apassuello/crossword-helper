#!/usr/bin/env python3
"""Simple debug script to trace beam search."""

import json
import sys

# Use the same imports as tests
from src.core.grid import Grid
from src.fill.pattern_matcher import PatternMatcher
from src.fill.beam_search_autofill import BeamSearchAutofill

# Load grid
print("Loading grid...")
with open('../test_grids/empty_15x15.json') as f:
    data = json.load(f)

grid = Grid.from_dict(data)

# Check empty slots
empty_slots = grid.get_empty_slots()
print(f"Empty slots found: {len(empty_slots)}")

# Create minimal wordlist
print("\nCreating pattern matcher...")
from src.fill.word_list import WordList
words = ["HELLO", "WORLD", "TEST", "PUZZLE", "CROSSWORD", "APPLE", "ORANGE", "BANANA"]
word_list = WordList(words)
pattern_matcher = PatternMatcher(word_list=word_list)

# Initialize beam search
print("Initializing beam search...")
autofill = BeamSearchAutofill(
    grid=grid,
    word_list=word_list,
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
