# Claude Code Implementation Prompts

This document contains step-by-step prompts to paste into Claude Code for implementing the crossword builder. Each prompt is self-contained and includes all necessary context.

**Usage Instructions:**
1. Start Claude Code in your project directory: `claude`
2. Copy-paste each prompt in order
3. Review the implementation after each phase
4. Test before moving to next phase

---

## PROMPT 0: Project Setup

```
I'm building a Python crossword constructor application. Please set up the complete project structure with all necessary files.

**Requirements:**
1. Create this directory structure:

crossword-builder/
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── grid.py
│   │   ├── cell.py
│   │   ├── word.py
│   │   ├── symmetry.py
│   │   ├── numbering.py
│   │   └── validator.py
│   ├── fill/
│   │   ├── __init__.py
│   │   ├── pattern_matcher.py
│   │   ├── word_list.py
│   │   ├── scorer.py
│   │   ├── autofill.py
│   │   └── heuristics.py
│   ├── clues/
│   │   ├── __init__.py
│   │   ├── clue_manager.py
│   │   ├── clue_database.py
│   │   └── generator.py
│   ├── export/
│   │   ├── __init__.py
│   │   ├── html_exporter.py
│   │   ├── pdf_exporter.py
│   │   ├── puz_exporter.py
│   │   └── json_exporter.py
│   └── cli/
│       ├── __init__.py
│       ├── main.py
│       ├── commands.py
│       └── interactive.py
├── data/
│   ├── wordlists/
│   ├── clues/
│   └── grids/
│       └── templates/
├── tests/
│   ├── __init__.py
│   ├── test_grid.py
│   ├── test_pattern_matcher.py
│   ├── test_autofill.py
│   ├── test_symmetry.py
│   └── fixtures/
│       └── test_grids.json
├── .claude/
│   ├── CLAUDE.md
│   └── commands/
│       ├── build.md
│       ├── test.md
│       ├── pattern-match.md
│       └── fill-grid.md
├── requirements.txt
├── setup.py
├── README.md
└── .gitignore

2. Create requirements.txt with these dependencies:
numpy>=1.24.0
regex>=2023.0.0
pypuz>=0.2.0
reportlab>=4.0.0
Jinja2>=3.1.0
click>=8.1.0
rich>=13.0.0
prompt-toolkit>=3.0.0
pytest>=7.4.0
pytest-cov>=4.1.0
mypy>=1.5.0
pylint>=2.17.0
black>=23.7.0

3. Create setup.py for package installation:
```python
from setuptools import setup, find_packages

setup(
    name="crossword-builder",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.24.0",
        "regex>=2023.0.0",
        "pypuz>=0.2.0",
        "reportlab>=4.0.0",
        "Jinja2>=3.1.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "prompt-toolkit>=3.0.0",
    ],
    entry_points={
        'console_scripts': [
            'crossword=src.cli.main:cli',
        ],
    },
)
```

4. Create README.md with project overview and setup instructions

5. Create .gitignore with Python-specific excludes

6. Create .claude/CLAUDE.md with this content:

# Crossword Builder

## Project Overview
Python CLI tool for crossword puzzle construction with NYT-style features.

**Tech Stack:** Python 3.9+, NumPy, pypuz, reportlab  
**Primary Language:** Python  
**Build System:** pip, pytest

## Development Commands

### Setup
```bash
pip install -e .
pip install -r requirements.txt
```

### Build & Test
```bash
pytest tests/ -v
pytest tests/test_grid.py -v  # Specific test
mypy src/  # Type checking
pylint src/  # Linting
black src/  # Format
```

### CLI Usage
```bash
crossword new --size 15 --output puzzle.json
crossword pattern "?I?A" --wordlist data/wordlists/standard.txt
crossword fill puzzle.json --wordlist data/wordlists/standard.txt
crossword export puzzle.json --format html --output puzzle.html
```

## Code Patterns

### Grid Operations
- Grid represented as `numpy.ndarray` (2D array)
- Black squares: `-1`
- Empty squares: `0`
- Letters: `1-26` (A=1, B=2, etc.)

### Pattern Matching
- Use `?` for wildcards
- Return scored matches (1-100)
- Sort by crossword-ability

### Numbering Algorithm
Scan left-to-right, top-to-bottom.
Number cell if it starts an across OR down word.

## Anti-Patterns

❌ Don't modify grid without validation
✅ Use methods that enforce constraints

❌ Don't hardcode word lists
✅ Load from external files

## Testing
- Framework: pytest
- Coverage target: >80%
- TDD workflow: test → implement → verify

## Before Coding
1. Understand grid constraints
2. Consider edge cases (boundaries, symmetry)
3. Plan test cases

## While Coding
1. Follow TDD workflow
2. Run tests after changes: `pytest tests/ -v`
3. Keep functions pure when possible
4. Document complex algorithms

## After Coding
- [ ] All tests pass
- [ ] Linting clean
- [ ] Type hints added
- [ ] Docstrings present

Please create all these files and directories. Use proper Python package structure with __init__.py files. The files can be empty/stubs for now - we'll implement them in phases.
```

---

## PROMPT 1: Core Grid Module - Data Structure

```
Now let's implement the core Grid class. This is the foundation for everything else.

**Implement src/core/grid.py with the following:**

1. **Grid Class** with NumPy-based grid representation:
   - `size`: int (11, 15, or 21)
   - `cells`: np.ndarray of shape (size, size)
   - `black_squares`: Set of (row, col) tuples
   - `words`: Dict mapping position to Word objects
   - `numbers`: Dict mapping (row, col) to clue numbers

2. **Cell encoding:**
   - `-1` = black square
   - `0` = empty square
   - `1-26` = letters (A=1, B=2, ..., Z=26)

3. **Key methods to implement:**

```python
def __init__(self, size: int = 15):
    """Initialize empty grid. Validate size is 11, 15, or 21."""
    
def place_black_square(self, row: int, col: int) -> None:
    """
    Place black square and its 180° rotationally symmetric counterpart.
    
    Steps:
    1. Validate position is in bounds
    2. Calculate symmetric position: (size-1-row, size-1-col)
    3. Set both cells to -1
    4. Add both to black_squares set
    5. Validate no <3 letter words created
    """
    
def remove_black_square(self, row: int, col: int) -> None:
    """Remove black square and its symmetric counterpart."""
    
def validate_symmetry(self) -> bool:
    """
    Check 180° rotational symmetry.
    
    Algorithm:
    1. Rotate grid 180° using np.rot90(cells, 2)
    2. Compare black square positions only
    3. Return True if identical
    """
    
def to_dict(self) -> dict:
    """Serialize to dictionary for JSON export."""
    
@classmethod
def from_dict(cls, data: dict) -> 'Grid':
    """Deserialize from dictionary."""
    
def clone(self) -> 'Grid':
    """Deep copy of grid."""
    
def __str__(self) -> str:
    """
    ASCII representation. Use:
    - '█' for black squares
    - '.' for empty squares
    - Letters for filled squares
    """
```

4. **Also implement src/core/word.py:**

```python
from dataclasses import dataclass

@dataclass
class Word:
    """Represents a word in the grid."""
    text: str
    number: int
    direction: str  # 'across' or 'down'
    row: int
    col: int
    length: int
```

5. **Write tests in tests/test_grid.py:**
   - test_grid_creation (sizes 11, 15, 21)
   - test_invalid_grid_size (should raise ValueError)
   - test_black_square_symmetry
   - test_grid_serialization
   - test_grid_clone

Run tests after implementation: `pytest tests/test_grid.py -v`

**Important:**
- Use NumPy for array operations
- Enforce symmetry on every black square placement
- Make deep copies for clone()
- Handle edge cases (corners, boundaries)
```

---

## PROMPT 2: Core Grid Module - Numbering & Validation

```
Now implement the auto-numbering system and validation methods for the Grid class.

**Add these methods to src/core/grid.py:**

1. **Auto-numbering system:**

```python
def auto_number(self) -> Dict[Tuple[int, int], int]:
    """
    Assign clue numbers to grid cells.
    
    Algorithm:
    1. Start with number = 1
    2. Scan left-to-right, top-to-bottom (row by row)
    3. For each cell:
       - If it starts an across word (white cell with black/edge to left), assign number
       - OR if it starts a down word (white cell with black/edge above), assign number
       - Only assign one number per cell even if starts both
    4. Increment number for each assigned cell
    
    Returns:
        Dictionary mapping (row, col) to clue number
        
    Helper methods you'll need:
    - starts_across_word(row, col): Check if cell starts across word
    - starts_down_word(row, col): Check if cell starts down word
    """
    
def starts_across_word(self, row: int, col: int) -> bool:
    """
    Cell starts across word if:
    - It's not a black square
    - Cell to the left is black OR at left edge
    - Cell to the right is not black (word continues)
    """
    
def starts_down_word(self, row: int, col: int) -> bool:
    """
    Cell starts down word if:
    - It's not a black square
    - Cell above is black OR at top edge
    - Cell below is not black (word continues)
    """
    
def get_across_words(self) -> List[Word]:
    """Get all across words in clue number order."""
    
def get_down_words(self) -> List[Word]:
    """Get all down words in clue number order."""
```

2. **Validation methods:**

```python
def validate_connectivity(self) -> Tuple[bool, List[Set]]:
    """
    Check if all white squares are connected (all-over interlock).
    
    Use depth-first search:
    1. Find all white squares
    2. Start DFS from first white square
    3. Track visited squares
    4. If all white squares visited → connected
    5. Otherwise → return disconnected regions
    """
    
def validate_no_unchecked(self) -> Tuple[bool, List[Tuple[int,int]]]:
    """
    Check every letter appears in both across and down word.
    
    Algorithm:
    1. For each non-black, non-empty cell
    2. Check if in both an across and down word
    3. Collect any that aren't
    """
    
def validate_min_word_length(self) -> Tuple[bool, List[Word]]:
    """
    Check all words are at least 3 letters.
    
    Helper needed:
    - get_all_words(): Extract all across and down words from grid
    """
    
def validate_black_square_count(self) -> Tuple[bool, int, int]:
    """
    Check black square percentage (should be <17% for 15x15).
    
    Max limits:
    - 11x11: ~20 black squares (16%)
    - 15x15: ~38 black squares (17%)
    - 21x21: ~75 black squares (17%)
    """
    
def validate_all(self) -> Dict[str, any]:
    """
    Run all validation checks. Return dict with results:
    {
        'symmetric': bool,
        'connected': bool,
        'no_unchecked': bool,
        'min_word_length': bool,
        'black_square_count': bool,
        'errors': List[str]
    }
    """
```

3. **Write comprehensive tests in tests/test_grid.py:**
   - test_auto_numbering_simple
   - test_auto_numbering_with_blacks
   - test_connectivity_valid
   - test_connectivity_invalid (isolated regions)
   - test_unchecked_squares
   - test_min_word_length
   - test_black_square_limits

Run: `pytest tests/test_grid.py -v`

**Important:**
- Auto-numbering follows standard crossword conventions
- DFS for connectivity must visit all 4 neighbors (up/down/left/right)
- Handle edge cases (grid boundaries)
```

---

## PROMPT 3: Word Placement & Slot Management

```
Now implement word placement and slot management for autofill.

**Add to src/core/grid.py:**

1. **Word placement methods:**

```python
def place_word(self, word: str, row: int, col: int, 
               direction: str) -> Word:
    """
    Place word in grid.
    
    Args:
        word: Uppercase letters only
        row: Starting row (0-indexed)
        col: Starting column (0-indexed)
        direction: 'across' or 'down'
        
    Steps:
    1. Validate word fits in grid
    2. Check no conflicts with existing letters
    3. Convert letters to numeric codes (A=1, B=2, etc.)
    4. Place in cells array
    5. Create Word object
    6. Store in self.words dict
    7. Return Word object
    
    Raises:
        ValueError if word doesn't fit or conflicts
    """
    
def remove_word(self, number: int, direction: str) -> None:
    """Remove word by clue number. Set cells back to 0 (empty)."""
    
def get_word(self, number: int, direction: str) -> Optional[Word]:
    """Retrieve word by clue number."""
```

2. **Slot management for autofill:**

```python
@dataclass
class Slot:
    """Unfilled word slot (for autofill)."""
    number: int
    direction: str
    row: int
    col: int
    length: int
    pattern: str  # e.g., "?I??A"
    
def get_empty_slots(self) -> List[Slot]:
    """
    Get all unfilled word slots.
    
    Algorithm:
    1. Auto-number the grid
    2. For each numbered cell:
       - If starts across word, check if filled
       - If starts down word, check if filled
    3. For unfilled slots, create Slot object
    4. Generate pattern for each slot
    
    Returns:
        List of Slot objects
    """
    
def get_pattern(self, slot: Slot) -> str:
    """
    Get current pattern for slot considering crossing letters.
    
    For across word:
    - Scan from slot position, length=slot.length
    - For each position:
      - If empty (0): add '?'
      - If filled (1-26): add letter
      
    Example: If slot is 5 letters and positions are [0, 9, 0, 0, 1]:
    → Pattern is "?I??A"
    """
    
def get_letter_at(self, row: int, col: int) -> Optional[str]:
    """Get letter at position, or None if empty/black."""
    cell = self.cells[row, col]
    if cell <= 0:
        return None
    return chr(ord('A') + cell - 1)
```

3. **Tests for word placement (tests/test_grid.py):**
   - test_place_word_across
   - test_place_word_down
   - test_place_word_conflict (should raise ValueError)
   - test_place_word_out_of_bounds
   - test_remove_word
   - test_get_empty_slots
   - test_get_pattern_empty
   - test_get_pattern_partial

Run: `pytest tests/test_grid.py -v`
```

---

## PROMPT 4: Word List Management

```
Implement the word list management system for loading and scoring words.

**Implement src/fill/word_list.py:**

```python
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
import re

@dataclass
class WordEntry:
    """Single word with metadata."""
    word: str
    score: int  # 1-100 crossword-ability
    length: int
    tags: Set[str]

class WordList:
    """
    Manages crossword word lists with scoring.
    """
    
    def __init__(self):
        self._words: Dict[str, WordEntry] = {}
        self._by_length: Dict[int, List[Tuple[str, int]]] = {}
    
    def load_from_file(self, filepath: str, format: str = 'txt') -> None:
        """
        Load words from file.
        
        Formats:
        - txt: One word per line
        - tsv: WORD\tSCORE\tTAGS (tab-separated)
        
        Steps:
        1. Read file
        2. Parse lines based on format
        3. For txt: auto-score using calculate_score()
        4. For tsv: use provided score
        5. Add each word via add_word()
        """
    
    def add_word(self, word: str, score: int = 50, 
                 tags: Set[str] = None) -> None:
        """
        Add word to list.
        
        Steps:
        1. Normalize: uppercase, strip whitespace
        2. Create WordEntry
        3. Add to _words dict
        4. Add to _by_length index
        """
    
    def get_score(self, word: str) -> int:
        """Get score for word (return 50 if not found)."""
    
    def get_by_length(self, length: int) -> List[Tuple[str, int]]:
        """Get all words of specified length."""
    
    def calculate_score(self, word: str) -> int:
        """
        Calculate crossword-ability score (1-100).
        
        Factors:
        1. Letter frequency (30%): 
           - Common letters (ETAOINSHRDLU): +2 each
           - Other letters: +1 each
           - Normalize by word length
        
        2. Crossing potential (40%):
           - Penalize tough letters (QXZJK): -5 each
           - Base score: 40
           
        3. Word properties (30%):
           - Base: 30
           - Multi-word (has space): -5
           - All caps: -5
        
        Returns:
            Score 1-100
        """
    
    def analyze(self) -> Dict[str, any]:
        """
        Analyze word list statistics.
        
        Return:
        {
            'total_words': int,
            'by_length': {3: count, 4: count, ...},
            'avg_score': float,
            'score_distribution': {
                'premium': count (90-100),
                'good': count (70-89),
                'acceptable': count (50-69),
                'crosswordese': count (30-49),
                'poor': count (1-29)
            }
        }
        """
```

**Also implement src/fill/scorer.py for the scoring logic:**

```python
def calculate_score(word: str, 
                   frequency_in_puzzles: int = 0,
                   is_personal: bool = False) -> int:
    """
    Detailed word scoring.
    
    See specification for full algorithm.
    """
```

**Tests in tests/test_word_list.py:**
- test_add_word
- test_load_txt_file
- test_load_tsv_file
- test_get_by_length
- test_calculate_score_common_letters
- test_calculate_score_tough_letters
- test_analyze_statistics

**Create sample word list data/wordlists/test.txt:**
```
VISA
PITA
DIVA
QUIZ
JAZZ
TEST
```

Run: `pytest tests/test_word_list.py -v`
```

---

## PROMPT 5: Pattern Matching Engine

```
Implement the pattern matching engine for finding words.

**Implement src/fill/pattern_matcher.py:**

```python
from typing import List, Tuple, Dict, Pattern
import re
from functools import lru_cache

class PatternMatcher:
    """
    Fast pattern matching for crossword fill.
    
    Supports '?' wildcards: ?I?A matches VISA, PITA, DIVA
    """
    
    def __init__(self, word_list: 'WordList'):
        self.word_list = word_list
        self._cache: Dict[Tuple, List] = {}
        self._build_index()
    
    def _build_index(self) -> None:
        """
        Build indices for fast lookup.
        
        Create:
        - _by_length: {3: [(word, score), ...], 4: [...], ...}
        - _by_first_letter: {'A': [(word, score), ...], ...}
        """
    
    def find(self, pattern: str, 
             min_score: int = 30,
             max_results: int = 100) -> List[Tuple[str, int]]:
        """
        Find words matching pattern.
        
        Algorithm:
        1. Check cache
        2. Get words of correct length
        3. If no wildcards: hash lookup
        4. Else: compile regex and match
        5. Filter by min_score
        6. Sort by score descending
        7. Cache result
        8. Return top max_results
        
        Example:
            >>> matcher.find("?I?A")
            [('VISA', 85), ('PITA', 80), ('DIVA', 75)]
        """
    
    def _pattern_to_regex(self, pattern: str) -> Pattern:
        """
        Convert crossword pattern to regex.
        
        Steps:
        1. Replace '?' with '.'
        2. Add anchors: ^ and $
        3. Compile case-insensitive
        
        Example:
            "?I?A" → "^.I.A$"
        """
    
    @lru_cache(maxsize=1000)
    def _find_cached(self, pattern: str, min_score: int) -> Tuple[Tuple[str, int], ...]:
        """LRU cache wrapper for find results."""
```

**Tests in tests/test_pattern_matcher.py:**

```python
def test_exact_match():
    """Pattern with no wildcards."""
    word_list = WordList()
    word_list.add_word("VISA", 85)
    matcher = PatternMatcher(word_list)
    
    results = matcher.find("VISA")
    assert len(results) == 1
    assert results[0][0] == "VISA"

def test_single_wildcard():
    """Pattern: ?ISA"""
    word_list = WordList()
    word_list.add_word("VISA", 85)
    word_list.add_word("PISA", 70)
    matcher = PatternMatcher(word_list)
    
    results = matcher.find("?ISA")
    assert len(results) == 2
    # Sorted by score
    assert results[0][0] == "VISA"

def test_multiple_wildcards():
    """Pattern: ?I?A"""
    # ... comprehensive wildcard test

def test_no_matches():
    """Pattern that matches nothing."""
    # ... should return empty list

def test_min_score_filter():
    """Test min_score parameter."""
    # ... should exclude low-scoring words

def test_cache_performance():
    """Repeated patterns should be faster."""
    # ... measure time difference
```

Run: `pytest tests/test_pattern_matcher.py -v`
```

---

## PROMPT 6: Autofill - Backtracking CSP

```
Implement the core autofill engine using constraint satisfaction with backtracking.

**Implement src/fill/autofill.py:**

```python
from typing import List, Optional, Tuple
from dataclasses import dataclass
import time

@dataclass
class FillResult:
    """Result of autofill attempt."""
    success: bool
    grid: 'Grid'
    time_elapsed: float
    slots_filled: int
    total_slots: int
    problematic_slots: List['Slot']

class Autofill:
    """
    Constraint satisfaction solver for crossword grids.
    """
    
    def __init__(self, 
                 grid: 'Grid',
                 word_list: 'WordList',
                 pattern_matcher: 'PatternMatcher',
                 timeout: int = 300):
        self.grid = grid.clone()  # Work on copy
        self.word_list = word_list
        self.pattern_matcher = pattern_matcher
        self.timeout = timeout
        self.start_time = None
    
    def fill(self, interactive: bool = False) -> FillResult:
        """
        Fill grid using backtracking CSP.
        
        Algorithm:
        1. Get empty slots
        2. If no empty slots → Success (already filled)
        3. Start backtracking recursion
        4. Return result
        """
        self.start_time = time.time()
        slots = self.grid.get_empty_slots()
        
        if not slots:
            return FillResult(
                success=True,
                grid=self.grid,
                time_elapsed=0,
                slots_filled=0,
                total_slots=0,
                problematic_slots=[]
            )
        
        try:
            success = self._backtrack(slots, 0, interactive)
            elapsed = time.time() - self.start_time
            
            if success:
                return FillResult(
                    success=True,
                    grid=self.grid,
                    time_elapsed=elapsed,
                    slots_filled=len(slots),
                    total_slots=len(slots),
                    problematic_slots=[]
                )
            else:
                # Find which slots couldn't be filled
                remaining = self.grid.get_empty_slots()
                return FillResult(
                    success=False,
                    grid=self.grid,
                    time_elapsed=elapsed,
                    slots_filled=len(slots) - len(remaining),
                    total_slots=len(slots),
                    problematic_slots=remaining
                )
        
        except TimeoutError:
            remaining = self.grid.get_empty_slots()
            return FillResult(
                success=False,
                grid=self.grid,
                time_elapsed=self.timeout,
                slots_filled=len(slots) - len(remaining),
                total_slots=len(slots),
                problematic_slots=remaining
            )
    
    def _backtrack(self, slots: List['Slot'], 
                   current_index: int,
                   interactive: bool) -> bool:
        """
        Recursive backtracking.
        
        Algorithm:
        1. Check timeout
        2. Base case: current_index >= len(slots) → Success
        3. Select slot (MCV heuristic)
        4. Get candidates (LCV heuristic)
        5. For each candidate:
           a. Place word
           b. Forward check
           c. If safe, recurse
           d. If recursion succeeds → Return True
           e. Backtrack (remove word)
        6. Return False (no candidate worked)
        """
        # Check timeout
        if time.time() - self.start_time > self.timeout:
            raise TimeoutError("Autofill timeout")
        
        # Base case
        if current_index >= len(slots):
            return True
        
        # Select slot (MCV)
        slot = self._select_slot(slots[current_index:])
        
        # Get candidates (LCV)
        candidates = self._get_candidates(slot)
        
        if not candidates:
            return False
        
        # Try each candidate
        for word, score in candidates:
            # Optional: print progress
            if interactive:
                print(f"Trying {word} for {slot.number}-{slot.direction}")
            
            # Place word
            self.grid.place_word(
                word,
                slot.row,
                slot.col,
                slot.direction
            )
            
            # Forward check
            if self._forward_check(slot, word):
                # Recurse
                if self._backtrack(slots, current_index + 1, interactive):
                    return True
            
            # Backtrack
            self.grid.remove_word(slot.number, slot.direction)
        
        return False
    
    def _select_slot(self, remaining_slots: List['Slot']) -> 'Slot':
        """
        Select next slot (MCV heuristic).
        
        Choose slot with fewest candidate words.
        
        Algorithm:
        1. For each slot, count candidates
        2. Return slot with minimum candidates
        3. Ties: prefer longer words (better anchors)
        """
    
    def _get_candidates(self, slot: 'Slot') -> List[Tuple[str, int]]:
        """
        Get candidate words for slot.
        
        Algorithm:
        1. Get pattern from grid
        2. Use pattern matcher to find words
        3. Sort by score (LCV)
        4. Return candidates
        """
        pattern = self.grid.get_pattern(slot)
        return self.pattern_matcher.find(pattern, min_score=30)
    
    def _forward_check(self, placed_slot: 'Slot', word: str) -> bool:
        """
        Check if placement creates dead ends.
        
        Algorithm:
        1. Get crossing slots
        2. For each crossing slot:
           a. Get updated pattern
           b. Check if any words match
           c. If zero matches → Return False
        3. Return True (all crossings have options)
        """
        # For now, implement simplified version:
        # Just check that placed word has valid letters
        return True  # TODO: Implement proper forward checking
```

**Tests in tests/test_autofill.py:**

```python
def test_simple_fill():
    """Test filling a very simple grid."""
    grid = Grid(size=11)
    # Create simple pattern with few blacks
    grid.place_black_square(5, 5)
    
    # Small test word list
    word_list = WordList()
    word_list.add_word("TEST", 80)
    word_list.add_word("WORD", 80)
    word_list.add_word("GRID", 80)
    # ... add more test words
    
    matcher = PatternMatcher(word_list)
    autofill = Autofill(grid, word_list, matcher, timeout=10)
    
    result = autofill.fill()
    
    assert result.success or len(result.problematic_slots) < 5

def test_timeout():
    """Test that timeout works."""
    grid = Grid(size=15)
    word_list = WordList()
    word_list.add_word("TEST", 50)
    
    matcher = PatternMatcher(word_list)
    autofill = Autofill(grid, word_list, matcher, timeout=1)
    
    result = autofill.fill()
    assert result.time_elapsed <= 2  # Should timeout near 1s
```

Run: `pytest tests/test_autofill.py -v`

**Note:** This implements basic backtracking. We'll add heuristics in next phase.
```

---

## PROMPT 7: Autofill - Heuristics & Forward Checking

```
Enhance the autofill with MCV, LCV heuristics and forward checking.

**Update src/fill/autofill.py:**

1. **Implement proper MCV (Most Constrained Variable):**

```python
def _select_slot(self, remaining_slots: List['Slot']) -> 'Slot':
    """
    MCV: Select slot with fewest candidates.
    
    Algorithm:
    1. For each slot:
       - Get pattern
       - Count matching candidates
       - Store (slot, candidate_count)
    2. Sort by candidate_count
    3. Break ties by preferring longer words
    4. Return slot with minimum candidates
    """
    slot_candidates = []
    
    for slot in remaining_slots:
        pattern = self.grid.get_pattern(slot)
        candidates = self.pattern_matcher.find(pattern, min_score=30)
        count = len(candidates)
        slot_candidates.append((slot, count))
    
    # Sort by count, then by length (prefer longer)
    slot_candidates.sort(key=lambda x: (x[1], -x[0].length))
    
    return slot_candidates[0][0]
```

2. **Implement LCV (Least Constraining Value):**

```python
def _get_candidates(self, slot: 'Slot') -> List[Tuple[str, int]]:
    """
    LCV: Choose words that preserve most options.
    
    Enhanced algorithm:
    1. Get pattern and find matches
    2. For each candidate:
       - Estimate impact on crossing slots
       - Calculate "constraint score"
    3. Sort by: crossword score * (1 + constraint_preservation)
    4. Return sorted candidates
    """
    pattern = self.grid.get_pattern(slot)
    candidates = self.pattern_matcher.find(pattern, min_score=30, max_results=50)
    
    # For now, just sort by score (simple LCV)
    # TODO: Add constraint analysis
    
    return candidates
```

3. **Implement proper forward checking:**

```python
def _forward_check(self, placed_slot: 'Slot', word: str) -> bool:
    """
    Check if placement eliminates all options for crossing slots.
    
    Algorithm:
    1. Identify crossing slots
    2. For each crossing slot:
       a. Calculate where they cross
       b. Get letter at crossing from placed word
       c. Update crossing slot's pattern with this constraint
       d. Check if any candidates remain
       e. If zero candidates → Return False (dead end)
    3. Return True (all crossings still fillable)
    """
    
    # Get crossing slots (implement helper method)
    crossing_slots = self._get_crossing_slots(placed_slot)
    
    for cross_slot in crossing_slots:
        # Find crossing position
        cross_pos = self._get_crossing_position(placed_slot, cross_slot)
        if cross_pos is None:
            continue
        
        # Get updated pattern for crossing slot
        pattern = self.grid.get_pattern(cross_slot)
        
        # Check if any words match
        candidates = self.pattern_matcher.find(pattern, min_score=30, max_results=1)
        
        if not candidates:
            # Dead end: no valid words for crossing slot
            return False
    
    return True

def _get_crossing_slots(self, slot: 'Slot') -> List['Slot']:
    """
    Get all slots that cross this slot.
    
    For across word: find down words that intersect
    For down word: find across words that intersect
    """
    crossings = []
    
    if slot.direction == 'across':
        # Find down words that cross this across word
        for col in range(slot.col, slot.col + slot.length):
            # Check if there's a down word starting at or above this position
            # that extends to this row
            # ... implementation details
    
    else:  # down
        # Find across words that cross this down word
        for row in range(slot.row, slot.row + slot.length):
            # Similar logic for across words
            # ... implementation details
    
    return crossings

def _get_crossing_position(self, slot1: 'Slot', slot2: 'Slot') -> Optional[int]:
    """
    Find position where two slots cross.
    
    Returns:
        Position in slot1 where slot2 crosses, or None if no crossing
    """
    # Implement crossing calculation logic
```

**Enhanced tests:**

```python
def test_mcv_heuristic():
    """Test that MCV selects most constrained slot first."""
    
def test_forward_checking():
    """Test that forward checking prevents dead ends."""
    grid = Grid(size=11)
    
    # Create scenario where one word choice blocks another
    # ... set up test case
    
    word_list = WordList()
    # Add words that create constraint conflict
    
    matcher = PatternMatcher(word_list)
    autofill = Autofill(grid, word_list, matcher)
    
    # Forward checking should detect dead end
    # ... assertions

def test_autofill_performance():
    """Test that heuristics improve performance."""
    # Compare time with and without heuristics
```

Run: `pytest tests/test_autofill.py -v`
```

---

## PROMPT 8: HTML Export

```
Implement HTML export for puzzle display.

**Implement src/export/html_exporter.py:**

```python
from jinja2 import Template
from typing import Dict

class HTMLExporter:
    """Export crossword to HTML format."""
    
    # HTML template with CSS
    BLANK_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 40px auto;
            padding: 20px;
        }
        h1 {
            text-align: center;
            margin-bottom: 30px;
        }
        .container {
            display: flex;
            gap: 40px;
            flex-wrap: wrap;
        }
        .grid-container {
            flex: 1;
            min-width: 400px;
        }
        .grid {
            display: inline-grid;
            grid-template-columns: repeat({{ size }}, 40px);
            gap: 0;
            border: 2px solid black;
        }
        .cell {
            width: 40px;
            height: 40px;
            border: 1px solid #999;
            position: relative;
            background: white;
        }
        .cell.black {
            background: black;
        }
        .cell input {
            width: 100%;
            height: 100%;
            border: none;
            text-align: center;
            font-size: 20px;
            text-transform: uppercase;
        }
        .number {
            position: absolute;
            top: 2px;
            left: 2px;
            font-size: 10px;
            font-weight: bold;
        }
        .clues {
            flex: 1;
            min-width: 300px;
        }
        .clue-section {
            margin-bottom: 30px;
        }
        .clue-section h2 {
            border-bottom: 2px solid black;
            padding-bottom: 5px;
        }
        .clue {
            margin: 8px 0;
            line-height: 1.4;
        }
        .clue-number {
            font-weight: bold;
            margin-right: 5px;
        }
        @media print {
            .container {
                flex-direction: column;
            }
            .grid-container {
                page-break-after: always;
            }
        }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    
    <div class="container">
        <div class="grid-container">
            <div class="grid">
                {% for row in range(size) %}
                    {% for col in range(size) %}
                        <div class="cell {% if cells[row][col] == -1 %}black{% endif %}">
                            {% if cells[row][col] != -1 %}
                                {% if numbers.get((row, col)) %}
                                    <span class="number">{{ numbers[(row, col)] }}</span>
                                {% endif %}
                                {% if show_answers and cells[row][col] > 0 %}
                                    {{ get_letter(cells[row][col]) }}
                                {% else %}
                                    <input type="text" maxlength="1">
                                {% endif %}
                            {% endif %}
                        </div>
                    {% endfor %}
                {% endfor %}
            </div>
        </div>
        
        <div class="clues">
            <div class="clue-section">
                <h2>Across</h2>
                {% for num, clue in across_clues %}
                    <div class="clue">
                        <span class="clue-number">{{ num }}.</span>
                        <span class="clue-text">{{ clue }}</span>
                    </div>
                {% endfor %}
            </div>
            
            <div class="clue-section">
                <h2>Down</h2>
                {% for num, clue in down_clues %}
                    <div class="clue">
                        <span class="clue-number">{{ num }}.</span>
                        <span class="clue-text">{{ clue }}</span>
                    </div>
                {% endfor %}
            </div>
        </div>
    </div>
</body>
</html>
    '''
    
    def export(self,
               grid: 'Grid',
               clues: Dict[Tuple[int, str], str],
               output_path: str,
               show_answers: bool = False,
               title: str = "Crossword Puzzle") -> None:
        """
        Export grid to HTML.
        
        Args:
            grid: Grid to export
            clues: Dict mapping (number, direction) to clue text
            output_path: Where to save HTML
            show_answers: If True, show filled letters
            title: Puzzle title
        """
        
        # Prepare data for template
        numbers = grid.auto_number()
        
        # Get clues organized by direction
        across_clues = []
        for word in grid.get_across_words():
            clue_key = (word.number, 'across')
            clue_text = clues.get(clue_key, f"Clue for {word.text}")
            across_clues.append((word.number, clue_text))
        
        down_clues = []
        for word in grid.get_down_words():
            clue_key = (word.number, 'down')
            clue_text = clues.get(clue_key, f"Clue for {word.text}")
            down_clues.append((word.number, clue_text))
        
        # Helper function for template
        def get_letter(cell_value):
            if cell_value <= 0:
                return ''
            return chr(ord('A') + cell_value - 1)
        
        # Render template
        template = Template(self.BLANK_TEMPLATE)
        html = template.render(
            title=title,
            size=grid.size,
            cells=grid.cells.tolist(),
            numbers=numbers,
            show_answers=show_answers,
            across_clues=across_clues,
            down_clues=down_clues,
            get_letter=get_letter
        )
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
```

**Tests:**

```python
def test_html_export_blank():
    """Test exporting blank puzzle."""
    grid = Grid(size=11)
    grid.place_word("TEST", 0, 0, "across")
    
    exporter = HTMLExporter()
    exporter.export(grid, {}, "test_blank.html", show_answers=False)
    
    # Verify file created
    assert os.path.exists("test_blank.html")
    
    # Verify content
    with open("test_blank.html") as f:
        html = f.read()
        assert "Crossword Puzzle" in html
        assert "Across" in html

def test_html_export_with_answers():
    """Test exporting solution."""
```

Run: `pytest tests/test_html_exporter.py -v`
```

---

## PROMPT 9: CLI Interface

```
Implement the complete CLI interface.

**Implement src/cli/main.py:**

```python
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import os

from src.core.grid import Grid
from src.fill.word_list import WordList
from src.fill.pattern_matcher import PatternMatcher
from src.fill.autofill import Autofill
from src.export.html_exporter import HTMLExporter

console = Console()

@click.group()
@click.version_option(version='0.1.0')
def cli():
    """
    Crossword Builder - Create NYT-style crossword puzzles.
    
    For help on commands: crossword COMMAND --help
    """
    pass

@cli.command()
@click.option('--size', default=15, type=click.Choice(['11', '15', '21']), 
              help='Grid size')
@click.option('--output', required=True, help='Output JSON file')
def new(size, output):
    """Create new empty crossword grid."""
    grid = Grid(size=int(size))
    grid.to_dict_file(output)
    console.print(f"[green]✓[/green] Created {size}×{size} grid: {output}")

@cli.command()
@click.argument('grid_file')
@click.argument('pattern')
@click.option('--wordlist', default='data/wordlists/standard.txt',
              help='Word list file')
@click.option('--count', default=20, help='Max results')
def pattern(grid_file, pattern, wordlist, count):
    """
    Find words matching pattern.
    
    Pattern uses '?' for wildcards.
    Example: ?I?A matches VISA, PITA, DIVA
    """
    
    if not os.path.exists(wordlist):
        console.print(f"[red]Error:[/red] Word list not found: {wordlist}")
        return
    
    # Load word list
    word_list = WordList()
    with console.status(f"Loading {wordlist}..."):
        word_list.load_from_file(wordlist)
    
    # Find matches
    matcher = PatternMatcher(word_list)
    matches = matcher.find(pattern, max_results=count)
    
    if not matches:
        console.print(f"[yellow]No matches found for pattern: {pattern}[/yellow]")
        return
    
    # Display in table
    table = Table(title=f"Matches for pattern: {pattern}")
    table.add_column("Rank", style="dim")
    table.add_column("Word", style="cyan bold")
    table.add_column("Score", style="green")
    
    for i, (word, score) in enumerate(matches, 1):
        table.add_row(str(i), word, str(score))
    
    console.print(table)
    console.print(f"\nTop suggestion: [bold cyan]{matches[0][0]}[/bold cyan] (score: {matches[0][1]})")

@cli.command()
@click.argument('grid_file')
@click.option('--wordlist', default='data/wordlists/standard.txt',
              help='Word list file')
@click.option('--interactive', is_flag=True, help='Interactive mode')
@click.option('--timeout', default=300, help='Timeout in seconds')
def fill(grid_file, wordlist, interactive, timeout):
    """
    Autofill grid using constraint satisfaction.
    
    Fills empty slots with words from word list.
    """
    
    # Load grid
    if not os.path.exists(grid_file):
        console.print(f"[red]Error:[/red] Grid file not found: {grid_file}")
        return
    
    grid = Grid.from_dict_file(grid_file)
    
    # Load word list
    if not os.path.exists(wordlist):
        console.print(f"[red]Error:[/red] Word list not found: {wordlist}")
        return
    
    word_list = WordList()
    with console.status(f"Loading {wordlist}..."):
        word_list.load_from_file(wordlist)
    
    # Create autofill
    matcher = PatternMatcher(word_list)
    autofill = Autofill(grid, word_list, matcher, timeout=timeout)
    
    # Run autofill
    console.print("[yellow]Starting autofill...[/yellow]")
    
    with Progress() as progress:
        task = progress.add_task("Filling grid...", total=100)
        result = autofill.fill(interactive=interactive)
    
    # Report results
    if result.success:
        console.print(f"\n[green]✓ Success![/green]")
        console.print(f"Filled {result.slots_filled} slots in {result.time_elapsed:.1f}s")
        
        # Save
        grid.to_dict_file(grid_file)
        console.print(f"Saved to {grid_file}")
    else:
        console.print(f"\n[red]✗ Failed to complete fill[/red]")
        console.print(f"Filled {result.slots_filled}/{result.total_slots} slots")
        console.print(f"Time: {result.time_elapsed:.1f}s")
        
        if result.problematic_slots:
            console.print("\nProblematic slots:")
            for slot in result.problematic_slots:
                console.print(f"  • {slot.number} {slot.direction} "
                            f"({slot.length} letters, pattern: {slot.pattern})")

@cli.command()
@click.argument('grid_file')
@click.option('--format', type=click.Choice(['html', 'puz', 'json']),
              default='html', help='Export format')
@click.option('--output', required=True, help='Output file')
@click.option('--title', default='Crossword Puzzle', help='Puzzle title')
@click.option('--answers', is_flag=True, help='Show answers (for HTML)')
def export(grid_file, format, output, title, answers):
    """
    Export puzzle to various formats.
    
    Formats: html, puz, json
    """
    
    # Load grid
    if not os.path.exists(grid_file):
        console.print(f"[red]Error:[/red] Grid file not found: {grid_file}")
        return
    
    grid = Grid.from_dict_file(grid_file)
    
    # Export
    with console.status(f"Exporting to {format}..."):
        if format == 'html':
            exporter = HTMLExporter()
            exporter.export(grid, {}, output, show_answers=answers, title=title)
        elif format == 'puz':
            # TODO: Implement PuzExporter
            console.print("[yellow]PUZ export not yet implemented[/yellow]")
            return
        elif format == 'json':
            grid.to_dict_file(output)
    
    console.print(f"[green]✓[/green] Exported to {output}")

@cli.command()
@click.argument('grid_file')
def validate(grid_file):
    """
    Validate grid against crossword rules.
    
    Checks: symmetry, connectivity, word lengths, etc.
    """
    
    # Load grid
    if not os.path.exists(grid_file):
        console.print(f"[red]Error:[/red] Grid file not found: {grid_file}")
        return
    
    grid = Grid.from_dict_file(grid_file)
    
    # Validate
    results = grid.validate_all()
    
    # Display results
    console.print("\n[bold]Validation Results:[/bold]\n")
    
    checks = [
        ('symmetric', 'Rotational symmetry'),
        ('connected', 'All-over interlock'),
        ('no_unchecked', 'No unchecked squares'),
        ('min_word_length', 'Minimum 3-letter words'),
        ('black_square_count', 'Black square limit'),
    ]
    
    all_passed = True
    for key, description in checks:
        if results[key]:
            console.print(f"[green]✓[/green] {description}")
        else:
            console.print(f"[red]✗[/red] {description}")
            all_passed = False
    
    if all_passed:
        console.print("\n[green]All checks passed![/green]")
    else:
        console.print("\n[red]Some checks failed. See errors above.[/red]")
        if results.get('errors'):
            for error in results['errors']:
                console.print(f"  • {error}")

if __name__ == '__main__':
    cli()
```

**Also add JSON serialization methods to Grid:**

```python
# In src/core/grid.py

def to_dict_file(self, filepath: str) -> None:
    """Save grid to JSON file."""
    import json
    with open(filepath, 'w') as f:
        json.dump(self.to_dict(), f, indent=2)

@classmethod
def from_dict_file(cls, filepath: str) -> 'Grid':
    """Load grid from JSON file."""
    import json
    with open(filepath) as f:
        data = json.load(f)
    return cls.from_dict(data)
```

**Test the CLI:**

```bash
# Create grid
crossword new --size 15 --output test.json

# Pattern matching
crossword pattern test.json "?I?A" --wordlist data/wordlists/test.txt

# Validate
crossword validate test.json

# Export
crossword export test.json --format html --output puzzle.html
```
```

---

## PROMPT 10: Final Integration & Testing

```
Final integration, comprehensive testing, and documentation.

**Tasks:**

1. **Create sample word list (data/wordlists/standard.txt):**

Add at least 100 common crossword words with good crossing potential:
```
VISA
PITA
DIVA
TEST
REST
BEST
AREA
IDEA
ORAL
...
```

2. **Create comprehensive integration test (tests/test_integration.py):**

```python
def test_full_workflow():
    """Test complete workflow: create → fill → export."""
    
    # 1. Create grid
    grid = Grid(size=11)
    grid.place_black_square(5, 5)
    grid.to_dict_file("test_workflow.json")
    
    # 2. Load word list
    word_list = WordList()
    word_list.load_from_file("data/wordlists/test.txt")
    
    # 3. Autofill
    matcher = PatternMatcher(word_list)
    autofill = Autofill(grid, word_list, matcher, timeout=30)
    result = autofill.fill()
    
    # Should fill or at least make progress
    assert result.slots_filled > 0
    
    # 4. Export
    exporter = HTMLExporter()
    exporter.export(result.grid, {}, "test_output.html")
    
    # Verify export
    assert os.path.exists("test_output.html")
    
    # Cleanup
    os.remove("test_workflow.json")
    os.remove("test_output.html")
```

3. **Create example workflow documentation (docs/USAGE.md):**

```markdown
# Crossword Builder - Usage Guide

## Quick Start

### 1. Install
```bash
pip install -e .
```

### 2. Create a new puzzle
```bash
crossword new --size 15 --output birthday-puzzle.json
```

### 3. Add your word list
Create `my-words.txt` with words you want:
```
RASPBERRIES
YOGA
GREEN
BANANA
```

### 4. Autofill the grid
```bash
crossword fill birthday-puzzle.json \
  --wordlist my-words.txt \
  --timeout 300
```

### 5. Export to HTML
```bash
crossword export birthday-puzzle.json \
  --format html \
  --output puzzle.html \
  --title "Birthday Puzzle"
```

## Example: Partner's Birthday Puzzle

[Include step-by-step example]
```

4. **Update README.md with:**
   - Installation instructions
   - Quick start guide
   - Link to full documentation
   - Example usage
   - Features list
   - License

5. **Run full test suite:**
```bash
pytest tests/ -v --cov=src --cov-report=html
```

6. **Check code quality:**
```bash
black src/ tests/
pylint src/
mypy src/
```

7. **Create final checklist in README:**

- [x] Core grid operations
- [x] Symmetry validation
- [x] Auto-numbering
- [x] Pattern matching
- [x] Word list management
- [x] Autofill with backtracking
- [x] Heuristics (MCV, LCV)
- [x] Forward checking
- [x] HTML export
- [x] CLI interface
- [x] Comprehensive tests (>80% coverage)
- [x] Documentation
- [ ] .puz export (optional)
- [ ] PDF export (optional)
- [ ] Clue generation (optional)

**Deliverables:**
- Working crossword builder CLI
- Sample word list
- Integration tests passing
- Usage documentation
- >80% test coverage
- Clean code (black, pylint, mypy)

This completes the core implementation!
```

---

## Summary

These 11 prompts will guide Claude Code through implementing the complete crossword builder:

1. **Prompt 0:** Project setup
2. **Prompt 1:** Grid data structure
3. **Prompt 2:** Numbering & validation
4. **Prompt 3:** Word placement & slots
5. **Prompt 4:** Word list management
6. **Prompt 5:** Pattern matching
7. **Prompt 6:** Autofill - backtracking
8. **Prompt 7:** Autofill - heuristics
9. **Prompt 8:** HTML export
10. **Prompt 9:** CLI interface
11. **Prompt 10:** Integration & testing

**Estimated Timeline:**
- Prompts 0-3: Day 1
- Prompts 4-5: Day 2
- Prompts 6-7: Day 3-4
- Prompts 8-10: Day 5
- Prompt 11: Day 6-7

**Tips for Success:**
1. Run tests after each prompt
2. Review code before moving to next prompt
3. Fix any issues before proceeding
4. Test CLI commands as you go
5. Keep word lists small initially for faster testing
6. Expand word lists once basic functionality works

Good luck building your crossword creator!
