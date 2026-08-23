# Crossword Builder - Technical Specifications

This document provides detailed specifications for implementing each component of the crossword builder system.

---

## Table of Contents

1. [Core Grid Module](#1-core-grid-module)
2. [Pattern Matching Module](#2-pattern-matching-module)
3. [Autofill Engine Module](#3-autofill-engine-module)
4. [Word List Manager Module](#4-word-list-manager-module)
5. [Clue Manager Module](#5-clue-manager-module)
6. [Export Engine Module](#6-export-engine-module)
7. [CLI Interface Module](#7-cli-interface-module)
8. [Test Specifications](#8-test-specifications)

---

## 1. Core Grid Module

### 1.1 Grid Class (`src/core/grid.py`)

#### Purpose
Manage crossword grid state, enforce construction rules, and provide operations for grid manipulation.

#### Class Definition

```python
from typing import Dict, List, Set, Tuple, Optional
import numpy as np
from dataclasses import dataclass

@dataclass
class Word:
    """Represents a word in the grid"""
    text: str
    number: int
    direction: str  # 'across' or 'down'
    row: int
    col: int
    length: int
    
class Grid:
    """
    Crossword grid with constraint enforcement.
    
    Attributes:
        size: Grid dimension (11, 15, or 21)
        cells: NumPy array representing grid state
        black_squares: Set of (row, col) coordinates for black squares
        words: Dictionary mapping position to Word objects
        numbers: Cell numbering for clues
    """
    
    def __init__(self, size: int = 15):
        """
        Initialize empty grid.
        
        Args:
            size: Grid dimension (must be odd: 11, 15, or 21)
            
        Raises:
            ValueError: If size is not 11, 15, or 21
        """
        pass
    
    # === Grid Operations ===
    
    def place_black_square(self, row: int, col: int) -> None:
        """
        Place black square and its symmetric counterpart.
        
        Args:
            row: Row coordinate (0-indexed)
            col: Column coordinate (0-indexed)
            
        Raises:
            ValueError: If position invalid or creates <3 letter word
        """
        pass
    
    def remove_black_square(self, row: int, col: int) -> None:
        """Remove black square and its symmetric counterpart."""
        pass
    
    def place_word(self, word: str, row: int, col: int, 
                   direction: str) -> Word:
        """
        Place word in grid.
        
        Args:
            word: Word text (letters only, uppercase)
            row: Starting row
            col: Starting column
            direction: 'across' or 'down'
            
        Returns:
            Word object representing placed word
            
        Raises:
            ValueError: If word doesn't fit or conflicts with existing
        """
        pass
    
    def remove_word(self, number: int, direction: str) -> None:
        """Remove word by its clue number."""
        pass
    
    def get_word(self, number: int, direction: str) -> Optional[Word]:
        """Retrieve word by clue number."""
        pass
    
    # === Validation ===
    
    def validate_symmetry(self) -> bool:
        """
        Check if grid has 180° rotational symmetry.
        
        Returns:
            True if symmetric, False otherwise
        """
        pass
    
    def validate_connectivity(self) -> Tuple[bool, List[Set]]:
        """
        Check if all white squares are connected.
        
        Returns:
            (is_connected, list_of_disconnected_regions)
        """
        pass
    
    def validate_no_unchecked(self) -> Tuple[bool, List[Tuple[int,int]]]:
        """
        Check that every letter is in both across and down word.
        
        Returns:
            (all_checked, list_of_unchecked_positions)
        """
        pass
    
    def validate_min_word_length(self) -> Tuple[bool, List[Word]]:
        """
        Check that all words are at least 3 letters.
        
        Returns:
            (all_valid, list_of_too_short_words)
        """
        pass
    
    def validate_black_square_count(self) -> Tuple[bool, int, int]:
        """
        Check black square percentage.
        
        Returns:
            (within_limit, actual_count, max_allowed)
        """
        pass
    
    def validate_all(self) -> Dict[str, any]:
        """
        Run all validation checks.
        
        Returns:
            Dictionary with validation results:
            {
                'symmetric': bool,
                'connected': bool,
                'no_unchecked': bool,
                'min_word_length': bool,
                'black_square_count': bool,
                'errors': List[str]
            }
        """
        pass
    
    # === Numbering ===
    
    def auto_number(self) -> Dict[Tuple[int, int], int]:
        """
        Assign clue numbers to grid cells.
        
        Algorithm:
        1. Scan left-to-right, top-to-bottom
        2. Number any cell that starts an across OR down word
        3. Increment sequentially
        
        Returns:
            Dictionary mapping (row, col) to clue number
        """
        pass
    
    def get_across_words(self) -> List[Word]:
        """Get all across words in clue number order."""
        pass
    
    def get_down_words(self) -> List[Word]:
        """Get all down words in clue number order."""
        pass
    
    # === Slots (for autofill) ===
    
    def get_empty_slots(self) -> List['Slot']:
        """
        Get all unfilled word slots (across and down).
        
        Returns:
            List of Slot objects representing empty positions
        """
        pass
    
    def get_pattern(self, slot: 'Slot') -> str:
        """
        Get pattern for a slot with current crossings.
        
        Args:
            slot: Slot to analyze
            
        Returns:
            Pattern string (e.g., "?I?A?")
        """
        pass
    
    # === State Management ===
    
    def to_dict(self) -> dict:
        """Serialize grid to dictionary (for JSON export)."""
        pass
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Grid':
        """Deserialize grid from dictionary."""
        pass
    
    def clone(self) -> 'Grid':
        """Create deep copy of grid."""
        pass
    
    # === Display ===
    
    def __str__(self) -> str:
        """ASCII representation of grid."""
        pass
    
    def to_html(self, show_numbers: bool = True) -> str:
        """HTML representation for display."""
        pass
```

#### Cell Encoding

```python
# Cell value meanings:
EMPTY = 0        # White square, not yet filled
BLACK = -1       # Black square
A = 1, B = 2, ... Z = 26  # Letters
```

#### Symmetry Algorithm

```python
def validate_symmetry(self) -> bool:
    """
    180° rotational symmetry check.
    
    Algorithm:
    1. Rotate grid 180° using NumPy
    2. Compare black squares only (ignore letters)
    3. Return True if identical
    """
    rotated = np.rot90(self.cells, 2)
    
    # Compare only black square positions
    black_mask = self.cells == BLACK
    rotated_black_mask = rotated == BLACK
    
    return np.array_equal(black_mask, rotated_black_mask)
```

#### Connectivity Algorithm (DFS)

```python
def validate_connectivity(self) -> Tuple[bool, List[Set]]:
    """
    Use depth-first search to find connected components.
    
    Algorithm:
    1. Find all white squares
    2. DFS from first white square
    3. If all white squares visited → connected
    4. Otherwise, return disconnected regions
    """
    white_squares = set(
        (r, c) for r in range(self.size) 
        for c in range(self.size) 
        if self.cells[r, c] != BLACK
    )
    
    if not white_squares:
        return True, []
    
    visited = set()
    def dfs(row, col):
        if (row, col) in visited or (row, col) not in white_squares:
            return
        visited.add((row, col))
        # Visit neighbors (up, down, left, right)
        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
            dfs(row + dr, col + dc)
    
    # Start DFS from first white square
    start = next(iter(white_squares))
    dfs(start[0], start[1])
    
    if len(visited) == len(white_squares):
        return True, []
    else:
        # Return disconnected regions
        remaining = white_squares - visited
        return False, [visited, remaining]
```

---

### 1.2 Slot Class (`src/core/word.py`)

```python
@dataclass
class Slot:
    """
    Represents an empty word slot to be filled.
    
    Used by autofill algorithm to track unfilled positions.
    """
    number: int          # Clue number
    direction: str       # 'across' or 'down'
    row: int            # Starting row
    col: int            # Starting column
    length: int         # Word length
    pattern: str        # Current pattern (e.g., "?I?A?")
    
    def get_constraints(self) -> List['Slot']:
        """Get slots that cross this one."""
        pass
    
    def count_candidates(self, word_list: 'WordList') -> int:
        """Count words that match this slot's pattern."""
        pass
```

---

## 2. Pattern Matching Module

### 2.1 PatternMatcher Class (`src/fill/pattern_matcher.py`)

#### Purpose
Efficiently find words matching wildcard patterns.

#### Class Definition

```python
from typing import List, Tuple, Pattern
import re

class PatternMatcher:
    """
    Fast pattern matching for crossword fill.
    
    Supports wildcards:
    - '?' matches any single letter
    - Specific letters match themselves
    
    Examples:
    - "?I?A" matches VISA, PITA, DIVA
    - "RE??" matches READ, REAL, REAP
    """
    
    def __init__(self, word_list: 'WordList'):
        """
        Initialize matcher with word list.
        
        Args:
            word_list: WordList object containing scored words
        """
        self.word_list = word_list
        self._build_index()
    
    def _build_index(self) -> None:
        """
        Build indices for fast lookup.
        
        Creates:
        - Length index: words grouped by length
        - First letter index: words grouped by first letter
        - Pattern cache: memoize recent patterns
        """
        pass
    
    def find(self, pattern: str, 
             min_score: int = 30,
             max_results: int = 100) -> List[Tuple[str, int]]:
        """
        Find words matching pattern.
        
        Args:
            pattern: Pattern string (e.g., "?I?A")
            min_score: Minimum crossword-ability score
            max_results: Maximum number of results
            
        Returns:
            List of (word, score) tuples, sorted by score descending
            
        Example:
            >>> matcher.find("?I?A")
            [('VISA', 85), ('PITA', 80), ('DIVA', 75), ('RITA', 70)]
        """
        pass
    
    def _pattern_to_regex(self, pattern: str) -> Pattern:
        """
        Convert crossword pattern to regex.
        
        Args:
            pattern: Pattern with '?' wildcards
            
        Returns:
            Compiled regex pattern
            
        Example:
            "?I?A" → "^.I.A$"
        """
        regex_str = "^" + pattern.replace("?", ".") + "$"
        return re.compile(regex_str, re.IGNORECASE)
    
    def find_crossing_compatible(self, 
                                 pattern: str,
                                 crossing_slot: Slot,
                                 crossing_position: int) -> List[Tuple[str, int]]:
        """
        Find words that are compatible with a crossing word slot.
        
        Args:
            pattern: Pattern for current slot
            crossing_slot: Slot that crosses this one
            crossing_position: Position in current word where crossing occurs
            
        Returns:
            Words that maintain valid crossing
        """
        pass
```

#### Pattern Matching Algorithm

```python
def find(self, pattern: str, min_score: int = 30, 
         max_results: int = 100) -> List[Tuple[str, int]]:
    """
    Algorithm:
    1. Check cache for this pattern
    2. Filter by length (exact match)
    3. If pattern has no wildcards, hash lookup
    4. Otherwise, regex match
    5. Filter by minimum score
    6. Sort by score descending
    7. Return top N results
    """
    
    # Check cache
    cache_key = (pattern, min_score)
    if cache_key in self._cache:
        return self._cache[cache_key]
    
    length = len(pattern)
    
    # Get words of correct length
    candidates = self.word_list.get_by_length(length)
    
    # If no wildcards, exact match
    if '?' not in pattern:
        word = pattern.upper()
        if word in candidates:
            score = self.word_list.get_score(word)
            return [(word, score)] if score >= min_score else []
        return []
    
    # Regex matching
    regex = self._pattern_to_regex(pattern)
    matches = [
        (word, score)
        for word, score in candidates
        if regex.match(word) and score >= min_score
    ]
    
    # Sort by score
    matches.sort(key=lambda x: x[1], reverse=True)
    
    # Cache and return
    result = matches[:max_results]
    self._cache[cache_key] = result
    return result
```

---

## 3. Autofill Engine Module

### 3.1 Autofill Class (`src/fill/autofill.py`)

#### Purpose
Fill grid using constraint satisfaction with backtracking.

#### Class Definition

```python
from typing import List, Optional, Dict
from dataclasses import dataclass
import time

@dataclass
class FillResult:
    """Result of autofill attempt."""
    success: bool
    grid: Grid
    time_elapsed: float
    slots_filled: int
    total_slots: int
    problematic_slots: List[Slot]
    
class Autofill:
    """
    Constraint satisfaction solver for crossword grids.
    
    Uses backtracking with heuristics:
    - MCV (Most Constrained Variable): Fill hardest slots first
    - LCV (Least Constraining Value): Choose words that preserve options
    - Forward Checking: Eliminate impossible candidates early
    """
    
    def __init__(self, 
                 grid: Grid,
                 word_list: 'WordList',
                 pattern_matcher: PatternMatcher,
                 timeout: int = 300):
        """
        Initialize autofill solver.
        
        Args:
            grid: Grid to fill (can be partially filled)
            word_list: Available words
            pattern_matcher: Pattern matching engine
            timeout: Maximum seconds to spend filling
        """
        pass
    
    def fill(self, interactive: bool = False) -> FillResult:
        """
        Fill grid using backtracking CSP.
        
        Args:
            interactive: If True, prompt user before each placement
            
        Returns:
            FillResult with success status and filled grid
        """
        pass
    
    def _select_slot(self, slots: List[Slot]) -> Slot:
        """
        Select next slot to fill (MCV heuristic).
        
        Choose slot with fewest candidate words.
        Ties broken by:
        1. Fewest unconstrained crossing slots
        2. Longest word length (prefer anchors)
        """
        pass
    
    def _get_candidates(self, slot: Slot) -> List[Tuple[str, int]]:
        """
        Get candidate words for slot (LCV heuristic).
        
        Sort by score, but also consider impact on crossing slots.
        """
        pass
    
    def _forward_check(self, slot: Slot, word: str) -> bool:
        """
        Check if placing word eliminates all options for any crossing slot.
        
        Returns:
            True if placement is safe, False if creates dead end
        """
        pass
    
    def _backtrack(self, 
                   slots: List[Slot],
                   current_index: int) -> bool:
        """
        Recursive backtracking.
        
        Algorithm:
        1. If all slots filled → Success
        2. Select next slot (MCV)
        3. Get candidates (LCV)
        4. For each candidate:
           a. Place word
           b. Forward check
           c. If safe, recurse
           d. If recursion succeeds → Return success
           e. Otherwise, backtrack (remove word)
        5. If no candidate works → Return failure
        """
        pass
```

#### Backtracking Algorithm (Detailed)

```python
def _backtrack(self, slots: List[Slot], current_index: int) -> bool:
    """
    Core backtracking algorithm with forward checking.
    """
    
    # Check timeout
    if time.time() - self.start_time > self.timeout:
        raise TimeoutError("Autofill timeout")
    
    # Base case: all slots filled
    if current_index >= len(slots):
        return True
    
    # Select slot (MCV)
    slot = self._select_slot(slots[current_index:])
    
    # Get candidates (LCV)
    candidates = self._get_candidates(slot)
    
    if not candidates:
        # No valid words for this slot
        return False
    
    # Try each candidate
    for word, score in candidates:
        # Place word
        self.grid.place_word(
            word, 
            slot.row, 
            slot.col, 
            slot.direction
        )
        
        # Forward check
        if not self._forward_check(slot, word):
            # This placement creates dead end
            self.grid.remove_word(slot.number, slot.direction)
            continue
        
        # Recurse
        if self._backtrack(slots, current_index + 1):
            return True  # Success!
        
        # Backtrack
        self.grid.remove_word(slot.number, slot.direction)
    
    # No candidate worked
    return False
```

#### Forward Checking

```python
def _forward_check(self, slot: Slot, word: str) -> bool:
    """
    After placing word, check if any crossing slot has zero candidates.
    
    Algorithm:
    1. Get all slots that cross this word
    2. For each crossing slot:
       a. Generate pattern with new constraint
       b. Check if any words match
       c. If zero matches → return False
    3. If all crossing slots have options → return True
    """
    
    crossing_slots = slot.get_constraints()
    
    for crossing_slot in crossing_slots:
        # Get position where they cross
        cross_pos = self._get_crossing_position(slot, crossing_slot)
        
        # Get letter at crossing
        crossing_letter = word[cross_pos]
        
        # Update crossing slot's pattern
        pattern = self.grid.get_pattern(crossing_slot)
        
        # Check if any words match updated pattern
        candidates = self.pattern_matcher.find(pattern, min_score=30)
        
        if not candidates:
            # Dead end: no words fit crossing slot
            return False
    
    return True
```

---

## 4. Word List Manager Module

### 4.1 WordList Class (`src/fill/word_list.py`)

```python
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass

@dataclass
class WordEntry:
    """Single word entry with metadata."""
    word: str
    score: int          # 1-100 crossword-ability score
    length: int
    tags: Set[str]      # e.g., {'fruit', 'common', 'multiword'}
    
class WordList:
    """
    Manages crossword word lists with scoring.
    
    Supports:
    - Multiple word lists (personal, standard, themed)
    - Scoring and filtering
    - Multi-word entries (REALMADRID)
    """
    
    def __init__(self):
        self._words: Dict[str, WordEntry] = {}
        self._by_length: Dict[int, List[WordEntry]] = {}
        self._by_first_letter: Dict[str, List[WordEntry]] = {}
    
    def load_from_file(self, 
                       filepath: str,
                       format: str = 'txt') -> None:
        """
        Load word list from file.
        
        Supported formats:
        - txt: One word per line
        - tsv: WORD\tSCORE\tTAGS (tab-separated)
        - json: Structured format
        
        Args:
            filepath: Path to word list file
            format: File format ('txt', 'tsv', 'json')
        """
        pass
    
    def add_word(self, 
                 word: str, 
                 score: int = 50,
                 tags: Set[str] = None) -> None:
        """Add single word to list."""
        pass
    
    def remove_word(self, word: str) -> None:
        """Remove word from list."""
        pass
    
    def get_score(self, word: str) -> int:
        """Get crossword-ability score for word."""
        pass
    
    def get_by_length(self, length: int) -> List[Tuple[str, int]]:
        """Get all words of specified length."""
        pass
    
    def get_by_pattern(self, pattern: str) -> List[Tuple[str, int]]:
        """Get words matching pattern (delegates to PatternMatcher)."""
        pass
    
    def merge(self, other: 'WordList', prefer: str = 'higher_score') -> None:
        """
        Merge another word list into this one.
        
        Args:
            other: WordList to merge
            prefer: How to handle duplicates ('higher_score', 'this', 'other')
        """
        pass
    
    def analyze(self) -> Dict[str, any]:
        """
        Analyze word list statistics.
        
        Returns:
            {
                'total_words': int,
                'by_length': {3: 1200, 4: 3400, ...},
                'avg_score': float,
                'letter_frequency': {'A': 0.08, 'B': 0.02, ...},
                'top_words': [(word, score), ...],
                'crosswordese': [(word, score), ...]  # score < 30
            }
        """
        pass
```

#### Word Scoring Algorithm

```python
def calculate_score(word: str, 
                   frequency_in_puzzles: int = 0,
                   is_personal: bool = False) -> int:
    """
    Calculate crossword-ability score (1-100).
    
    Factors:
    1. Letter frequency (30%): Common letters (E, A, T, O) score higher
    2. Word commonness (40%): Frequency in published puzzles
    3. Crossing potential (30%): Avoid Q, X, Z unless high-value word
    
    Adjustments:
    - Personal words: +10 bonus
    - Multi-word entries: -5 penalty (harder to clue)
    - All caps (acronyms): -10 penalty
    """
    
    # Letter frequency score
    common_letters = set('ETAOINSHRDLU')
    letter_score = sum(
        2 if c in common_letters else 1 
        for c in word
    ) / len(word) * 30
    
    # Word commonness (from frequency in puzzles)
    commonness_score = min(frequency_in_puzzles / 100, 1.0) * 40
    
    # Crossing potential (penalize tough letters)
    tough_letters = set('QXZJK')
    crossing_penalty = sum(5 for c in word if c in tough_letters)
    crossing_score = max(30 - crossing_penalty, 0)
    
    total = letter_score + commonness_score + crossing_score
    
    # Adjustments
    if is_personal:
        total += 10
    if ' ' in word or word.count(word[0].upper()) > 2:
        total -= 5  # Multi-word or acronym
    
    return int(max(1, min(100, total)))
```

---

## 5. Clue Manager Module

### 5.1 ClueManager Class (`src/clues/clue_manager.py`)

```python
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class DifficultyLevel(Enum):
    """NYT difficulty levels."""
    MONDAY = 1      # Easiest
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4    # Gimmicks
    FRIDAY = 5
    SATURDAY = 6    # Hardest

@dataclass
class Clue:
    """Single clue for a word."""
    text: str
    difficulty: DifficultyLevel
    clue_type: str  # 'definition', 'fill_blank', 'trivia', 'wordplay', 'question'
    
class ClueManager:
    """
    Manage clues for crossword puzzle.
    
    Supports:
    - Multiple clues per word at different difficulties
    - Local clue database
    - Clue generation suggestions
    """
    
    def __init__(self, database_path: str = "data/clues/clue_database.json"):
        self.database_path = database_path
        self._clues: Dict[str, List[Clue]] = {}
        self._load_database()
    
    def get_clues(self, 
                  word: str,
                  difficulty: DifficultyLevel = DifficultyLevel.WEDNESDAY,
                  count: int = 5) -> List[Clue]:
        """
        Get clues for word at specified difficulty.
        
        Args:
            word: Word to get clues for
            difficulty: Desired difficulty level
            count: Maximum number of clues to return
            
        Returns:
            List of matching clues, sorted by relevance
        """
        pass
    
    def add_clue(self, word: str, clue: Clue) -> None:
        """Add clue to database."""
        pass
    
    def generate_suggestions(self, word: str) -> List[Clue]:
        """
        Generate clue suggestions for word.
        
        Uses templates and patterns:
        - Definition: "Type of [category]"
        - Fill blank: "_____ and [related word]"
        - Trivia: "[Famous person/place] is one"
        - Question: "[Adjective]?" for feelings
        """
        pass
    
    def import_from_csv(self, filepath: str) -> int:
        """Import clues from CSV file. Returns count imported."""
        pass
    
    def export_to_csv(self, filepath: str) -> None:
        """Export current database to CSV."""
        pass
```

---

## 6. Export Engine Module

### 6.1 HTMLExporter Class (`src/export/html_exporter.py`)

```python
from jinja2 import Template

class HTMLExporter:
    """Export crossword to HTML format."""
    
    BLANK_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ title }}</title>
        <style>
            .grid { 
                display: grid;
                grid-template-columns: repeat({{ size }}, 40px);
                gap: 0;
                border: 2px solid black;
                width: fit-content;
            }
            .cell {
                width: 40px;
                height: 40px;
                border: 1px solid #999;
                position: relative;
            }
            .cell.black {
                background: black;
            }
            .number {
                position: absolute;
                top: 2px;
                left: 2px;
                font-size: 10px;
            }
            .clues {
                margin: 20px 0;
                columns: 2;
            }
            .clue {
                break-inside: avoid;
                margin: 5px 0;
            }
        </style>
    </head>
    <body>
        <h1>{{ title }}</h1>
        <div class="grid">
            {% for row in range(size) %}
                {% for col in range(size) %}
                    <div class="cell {{ 'black' if is_black(row, col) else '' }}">
                        {% if get_number(row, col) %}
                            <span class="number">{{ get_number(row, col) }}</span>
                        {% endif %}
                    </div>
                {% endfor %}
            {% endfor %}
        </div>
        
        <div class="clues">
            <h2>Across</h2>
            {% for clue in across_clues %}
                <div class="clue">
                    <strong>{{ clue.number }}.</strong> {{ clue.text }}
                </div>
            {% endfor %}
            
            <h2>Down</h2>
            {% for clue in down_clues %}
                <div class="clue">
                    <strong>{{ clue.number }}.</strong> {{ clue.text }}
                </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """
    
    def export(self, 
               grid: Grid,
               clues: Dict[str, str],
               output_path: str,
               show_answers: bool = False,
               title: str = "Crossword Puzzle") -> None:
        """
        Export grid to HTML.
        
        Args:
            grid: Grid to export
            clues: Dictionary mapping (number, direction) to clue text
            output_path: Where to save HTML file
            show_answers: If True, show filled letters
            title: Puzzle title
        """
        pass
```

### 6.2 PuzExporter Class (`src/export/puz_exporter.py`)

```python
import puz

class PuzExporter:
    """Export to .puz (Across Lite) format."""
    
    def export(self,
               grid: Grid,
               clues: Dict[str, str],
               output_path: str,
               title: str = "Crossword Puzzle",
               author: str = "",
               copyright: str = "") -> None:
        """
        Export to .puz format.
        
        Args:
            grid: Grid to export
            clues: Clue dictionary
            output_path: Output file path
            title: Puzzle title
            author: Constructor name
            copyright: Copyright notice
        """
        
        # Create puz object
        puzzle = puz.Puzzle()
        
        # Set metadata
        puzzle.title = title
        puzzle.author = author
        puzzle.copyright = copyright
        puzzle.width = grid.size
        puzzle.height = grid.size
        
        # Convert grid to string format
        solution = self._grid_to_solution_string(grid)
        fill = self._grid_to_fill_string(grid)
        
        puzzle.solution = solution
        puzzle.fill = fill
        
        # Set clues
        clue_list = []
        for word in grid.get_across_words():
            clue_key = (word.number, 'across')
            clue_list.append(clues.get(clue_key, f"{word.number} Across"))
        
        for word in grid.get_down_words():
            clue_key = (word.number, 'down')
            clue_list.append(clues.get(clue_key, f"{word.number} Down"))
        
        puzzle.clues = clue_list
        
        # Save
        puzzle.save(output_path)
    
    def _grid_to_solution_string(self, grid: Grid) -> str:
        """Convert grid to flat solution string (row-major order)."""
        result = []
        for row in range(grid.size):
            for col in range(grid.size):
                if grid.cells[row, col] == BLACK:
                    result.append('.')
                else:
                    letter_code = grid.cells[row, col]
                    result.append(chr(ord('A') + letter_code - 1))
        return ''.join(result)
```

---

## 7. CLI Interface Module

### 7.1 Main CLI (`src/cli/main.py`)

```python
import click
from rich.console import Console
from rich.table import Table

console = Console()

@click.group()
def cli():
    """Crossword Builder - Create NYT-style crossword puzzles."""
    pass

@cli.command()
@click.option('--size', default=15, type=click.Choice([11, 15, 21]))
@click.option('--output', required=True, help='Output file path')
def new(size, output):
    """Create new empty grid."""
    grid = Grid(size=size)
    grid.save(output)
    console.print(f"[green]Created {size}x{size} grid: {output}[/green]")

@cli.command()
@click.argument('grid_file')
@click.argument('pattern')
@click.option('--wordlist', default='data/wordlists/standard.txt')
@click.option('--count', default=20)
def pattern(grid_file, pattern, wordlist, count):
    """Find words matching pattern (e.g., ?I?A)."""
    word_list = WordList()
    word_list.load_from_file(wordlist)
    
    matcher = PatternMatcher(word_list)
    matches = matcher.find(pattern, max_results=count)
    
    # Display in table
    table = Table(title=f"Matches for pattern: {pattern}")
    table.add_column("Word", style="cyan")
    table.add_column("Score", style="green")
    
    for word, score in matches:
        table.add_row(word, str(score))
    
    console.print(table)

@cli.command()
@click.argument('grid_file')
@click.option('--wordlist', default='data/wordlists/standard.txt')
@click.option('--interactive', is_flag=True)
@click.option('--timeout', default=300)
def fill(grid_file, wordlist, interactive, timeout):
    """Autofill grid using backtracking."""
    grid = Grid.from_file(grid_file)
    word_list = WordList()
    word_list.load_from_file(wordlist)
    
    matcher = PatternMatcher(word_list)
    autofill = Autofill(grid, word_list, matcher, timeout=timeout)
    
    console.print("[yellow]Starting autofill...[/yellow]")
    
    with console.status("Filling grid..."):
        result = autofill.fill(interactive=interactive)
    
    if result.success:
        console.print(f"[green]Success! Filled {result.slots_filled} slots in {result.time_elapsed:.1f}s[/green]")
        grid.save(grid_file)
    else:
        console.print(f"[red]Failed to fill grid. {len(result.problematic_slots)} problematic slots.[/red]")
        for slot in result.problematic_slots:
            console.print(f"  - {slot.number} {slot.direction} ({slot.length} letters)")

@cli.command()
@click.argument('grid_file')
@click.option('--format', type=click.Choice(['html', 'puz', 'pdf', 'json']))
@click.option('--output', required=True)
@click.option('--title', default='Crossword Puzzle')
def export(grid_file, format, output, title):
    """Export puzzle to various formats."""
    grid = Grid.from_file(grid_file)
    
    if format == 'html':
        exporter = HTMLExporter()
        exporter.export(grid, {}, output, title=title)
    elif format == 'puz':
        exporter = PuzExporter()
        exporter.export(grid, {}, output, title=title)
    # ... other formats
    
    console.print(f"[green]Exported to {output}[/green]")

if __name__ == '__main__':
    cli()
```

---

## 8. Test Specifications

### 8.1 Grid Tests (`tests/test_grid.py`)

```python
import pytest
import numpy as np
from src.core.grid import Grid, BLACK, EMPTY

def test_grid_creation():
    """Test creating grids of different sizes."""
    for size in [11, 15, 21]:
        grid = Grid(size=size)
        assert grid.size == size
        assert grid.cells.shape == (size, size)
        assert np.all(grid.cells == EMPTY)

def test_invalid_grid_size():
    """Test that invalid sizes raise ValueError."""
    with pytest.raises(ValueError):
        Grid(size=14)  # Must be odd

def test_black_square_symmetry():
    """Test that placing black square creates symmetric pair."""
    grid = Grid(size=15)
    grid.place_black_square(0, 0)
    
    # Check symmetric position (14, 14)
    assert grid.cells[0, 0] == BLACK
    assert grid.cells[14, 14] == BLACK
    assert grid.validate_symmetry()

def test_auto_numbering():
    """Test auto-numbering algorithm."""
    grid = Grid(size=15)
    
    # Place black squares to create words
    grid.place_black_square(0, 3)
    grid.place_black_square(14, 11)
    
    numbers = grid.auto_number()
    
    # Cell (0,0) should be numbered (starts both across and down)
    assert (0, 0) in numbers
    assert numbers[(0, 0)] == 1

def test_word_placement():
    """Test placing words in grid."""
    grid = Grid(size=15)
    word = grid.place_word("HELLO", 0, 0, "across")
    
    assert word.text == "HELLO"
    assert word.length == 5
    assert grid.cells[0, 0] == 8  # H = 8
    assert grid.cells[0, 4] == 15  # O = 15

def test_connectivity_validation():
    """Test that isolated regions are detected."""
    grid = Grid(size=11)
    
    # Create isolated region
    for i in range(11):
        grid.place_black_square(5, i)
    
    is_connected, regions = grid.validate_connectivity()
    assert not is_connected
    assert len(regions) == 2  # Top and bottom halves
```

### 8.2 Pattern Matcher Tests (`tests/test_pattern_matcher.py`)

```python
def test_exact_match():
    """Test pattern with no wildcards."""
    word_list = WordList()
    word_list.add_word("VISA", score=85)
    word_list.add_word("PITA", score=80)
    
    matcher = PatternMatcher(word_list)
    results = matcher.find("VISA")
    
    assert len(results) == 1
    assert results[0][0] == "VISA"

def test_wildcard_pattern():
    """Test pattern with wildcards."""
    word_list = WordList()
    word_list.add_word("VISA", score=85)
    word_list.add_word("PITA", score=80)
    word_list.add_word("DIVA", score=75)
    
    matcher = PatternMatcher(word_list)
    results = matcher.find("?I?A")
    
    assert len(results) == 3
    # Should be sorted by score
    assert results[0][0] == "VISA"
    assert results[1][0] == "PITA"
    assert results[2][0] == "DIVA"

def test_pattern_cache():
    """Test that repeated patterns use cache."""
    word_list = WordList()
    for i in range(1000):
        word_list.add_word(f"WORD{i}", score=50)
    
    matcher = PatternMatcher(word_list)
    
    # First call (cache miss)
    import time
    start = time.time()
    matcher.find("W???")
    first_time = time.time() - start
    
    # Second call (cache hit)
    start = time.time()
    matcher.find("W???")
    second_time = time.time() - start
    
    assert second_time < first_time * 0.1  # 10x faster
```

### 8.3 Autofill Tests (`tests/test_autofill.py`)

```python
def test_simple_fill():
    """Test filling a simple grid."""
    grid = Grid(size=11)
    
    # Create simple pattern
    grid.place_black_square(5, 5)
    
    word_list = WordList()
    word_list.load_from_file("tests/fixtures/test_wordlist.txt")
    
    matcher = PatternMatcher(word_list)
    autofill = Autofill(grid, word_list, matcher)
    
    result = autofill.fill()
    
    assert result.success
    assert result.slots_filled > 0

def test_unfillable_grid():
    """Test handling of unfillable grid."""
    grid = Grid(size=11)
    
    # Create impossible configuration
    grid.place_word("QQQQ", 0, 0, "across")
    grid.place_word("ZZZZ", 1, 0, "across")
    
    word_list = WordList()
    word_list.add_word("QUIZ", score=50)
    
    matcher = PatternMatcher(word_list)
    autofill = Autofill(grid, word_list, matcher, timeout=5)
    
    result = autofill.fill()
    
    assert not result.success
    assert len(result.problematic_slots) > 0
```

---

## Data Format Specifications

### Puzzle State JSON Format

```json
{
  "version": "1.0",
  "metadata": {
    "title": "Birthday Puzzle",
    "author": "You",
    "date": "2025-01-15",
    "difficulty": 3
  },
  "grid": {
    "size": 15,
    "cells": [[0, 1, 2, ...], ...],
    "black_squares": [[7, 7], [7, 14], ...],
    "numbers": {"0,0": 1, "0,4": 2, ...}
  },
  "words": {
    "1-across": {
      "text": "BANANA",
      "row": 0,
      "col": 0,
      "length": 6
    },
    "1-down": {
      "text": "BERRY",
      "row": 0,
      "col": 0,
      "length": 5
    }
  },
  "clues": {
    "1-across": "Arthur's favorite breakfast fruit",
    "1-down": "Raspberry, for one"
  }
}
```

### Word List TSV Format

```
WORD    SCORE   TAGS
VISA    85      common,standard
RASPBERRIES     75      fruit,long,personal
REALMADRID      60      sports,multiword,personal
YOGA    82      exercise,common,personal
```

---

## Performance Benchmarks

### Target Performance

| Operation | Simple (11×11) | Medium (15×15) | Large (21×21) |
|-----------|---------------|---------------|---------------|
| Grid creation | <5ms | <10ms | <20ms |
| Pattern match (500K words) | <50ms | <100ms | <100ms |
| Autofill (empty grid) | <5s | <30s | <3min |
| Autofill (50% filled) | <1s | <10s | <1min |
| HTML export | <100ms | <500ms | <1s |
| .puz export | <50ms | <100ms | <200ms |

---

## Implementation Checklist

### Phase 1: Core (Week 1)
- [ ] Project structure & setup
- [ ] Grid class with NumPy
- [ ] Symmetry validation
- [ ] Auto-numbering algorithm
- [ ] Word placement/removal
- [ ] Basic CLI skeleton
- [ ] Unit tests for core

### Phase 2: Fill Engine (Week 1)
- [ ] WordList class
- [ ] Pattern matcher with regex
- [ ] Word scoring algorithm
- [ ] Pattern matching tests

### Phase 3: Autofill (Week 2)
- [ ] Slot identification
- [ ] Backtracking framework
- [ ] MCV heuristic
- [ ] LCV heuristic
- [ ] Forward checking
- [ ] Autofill tests

### Phase 4: Export & Polish (Week 2)
- [ ] HTML exporter
- [ ] .puz exporter
- [ ] Clue manager (basic)
- [ ] All CLI commands
- [ ] Integration tests
- [ ] Documentation

---

This completes the technical specifications. Use these as reference when implementing each module.
