# Crossword Builder - System Architecture

## Executive Summary

A Python-based crossword construction toolkit designed to eliminate manual pain points in puzzle creation. Primary focus: **automated grid filling** using constraint satisfaction with backtracking. Secondary capabilities include pattern matching, auto-numbering, clue management, and professional export formats.

**Target User:** Expert developer creating personalized crossword for partner's birthday
**Primary Pain Point:** Grid filling - finding words that fit patterns and satisfy crossing constraints
**Design Philosophy:** Self-contained Python application with CLI interface, no external dependencies on Claude-specific features

---

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Crossword Builder CLI                     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│              │      │              │      │              │
│  Grid Engine │      │  Fill Engine │      │ Export Engine│
│              │      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
        │                     │                     │
        ├─ Symmetry           ├─ Pattern Match      ├─ HTML
        ├─ Validation         ├─ Backtracking       ├─ .puz
        ├─ Numbering          ├─ Scoring            ├─ PDF
        └─ Constraints        └─ Word Lists         └─ JSON
```

---

## Core Components

### 1. Grid Engine (`src/core/`)

**Purpose:** Manage crossword grid data structure and enforce construction rules

**Key Responsibilities:**
- Maintain 2D grid representation
- Enforce 180° rotational symmetry
- Validate all-over interlock (connectivity)
- Detect unchecked squares
- Auto-numbering system
- Black square management

**Critical Constraints:**
- Minimum 3-letter words
- Maximum ~17% black squares
- All white squares must be in both across and down words
- Grid must be fully connected (no isolated regions)

**Data Structure:**
```python
class Grid:
    size: int                          # 11, 15, or 21
    cells: np.ndarray                  # 2D array of cells
    black_squares: Set[Tuple[int,int]] # Coordinates of black squares
    words: Dict[str, Word]             # Across/Down words by position
    numbers: Dict[Tuple[int,int], int] # Cell numbering
```

**Cell Representation:**
```python
# Numeric encoding:
-1: Black square
 0: Empty (to be filled)
 1-26: Letters (A=1, B=2, ..., Z=26)
```

---

### 2. Fill Engine (`src/fill/`)

**Purpose:** Automated grid filling using constraint satisfaction

**Key Responsibilities:**
- Pattern matching (e.g., `?I?A` → VISA, PITA, DIVA)
- Constraint satisfaction problem (CSP) solving
- Backtracking search with heuristics
- Word scoring for "crossword-ability"
- Detect unfillable regions

**Algorithm: Backtracking CSP**

```
1. Find next empty slot (across or down word)
2. Generate candidate words (pattern matching)
3. For each candidate (sorted by score):
   a. Check if it violates crossing constraints
   b. If valid, place it and recurse
   c. If recursion succeeds, return success
   d. If recursion fails, backtrack (remove word)
4. If no candidates work, return failure
```

**Heuristics for Optimization:**
- **Most Constrained Variable (MCV):** Fill slots with fewest candidate words first
- **Least Constraining Value (LCV):** Choose words that leave most options for crossing slots
- **Forward Checking:** After placing word, eliminate invalid candidates from crossing slots
- **Arc Consistency:** Maintain consistency between all crossing word pairs

**Word Scoring Formula:**
```python
score = (
    letter_frequency_score * 0.3 +    # Common letters (E, A, T, O, I) score higher
    word_commonness_score * 0.4 +     # Frequency in published puzzles
    crossing_potential_score * 0.3    # Avoids Q, X, Z unless in good words
)
```

---

### 3. Pattern Matcher (`src/fill/pattern_matcher.py`)

**Purpose:** Find words matching crossword patterns with wildcards

**Input Format:**
- `?` = any letter (wildcard)
- `[A-Z]` = specific letter
- Examples: `?I?A`, `RE??`, `????E?`

**Process:**
1. Load word list into trie/hash structure
2. Parse pattern into regex
3. Filter words by length
4. Match against pattern
5. Score matches for crossword-ability
6. Return sorted list

**Performance Requirements:**
- Sub-100ms response for word lists <500K words
- Memory-efficient for large dictionaries
- Support multiple simultaneous lookups

**Example:**
```python
matcher = PatternMatcher("data/wordlists/standard.txt")
results = matcher.find("?I?A")
# Returns: [
#   ("VISA", 85),  # score
#   ("PITA", 80),
#   ("DIVA", 75),
#   ("RITA", 70)
# ]
```

---

### 4. Word List Manager (`src/fill/word_list.py`)

**Purpose:** Load, score, and manage crossword word lists

**Features:**
- Load multiple word lists (personal, standard, themed)
- Assign crossword-ability scores
- Filter by length, score threshold
- Merge and deduplicate lists
- Support for multi-word entries (REALMADRID, LAHAINE)

**Word List Format (TSV):**
```
WORD    SCORE    TAGS
VISA    85       standard,common
RASPBERRIES    75    fruit,long
REALMADRID    60    sports,multiword
```

**Scoring Categories:**
- 90-100: Premium fill (fresh, interesting words)
- 70-89: Good fill (solid, crossword-friendly)
- 50-69: Acceptable fill (fine but not exciting)
- 30-49: Crosswordese (stale, overused)
- 1-29: Last resort (obscure, poor crossing letters)

---

### 5. Clue Manager (`src/clues/`)

**Purpose:** Store, retrieve, and generate clues

**Features:**
- Local clue database (JSON/SQLite)
- Difficulty level tagging (Monday-Saturday)
- Multiple clue types per word
- Clue templates for common patterns
- Import from external databases (optional)

**Clue Types:**
- `definition`: Straight definition
- `fill_blank`: "_____ and void"
- `trivia`: "Author of 'Hamlet'"
- `wordplay`: Puns and misdirection
- `question`: "Surprised?" → ASTONISHED

**Storage Format:**
```python
{
  "VISA": [
    {"clue": "Credit card type", "difficulty": 1, "type": "definition"},
    {"clue": "Entry stamp", "difficulty": 2, "type": "definition"},
    {"clue": "It might be required for travel", "difficulty": 3, "type": "trivia"}
  ]
}
```

---

### 6. Export Engine (`src/export/`)

**Purpose:** Generate puzzle outputs in multiple formats

**Supported Formats:**

**HTML:**
- Blank grid for solving
- Answer key with filled letters
- Clues formatted (Across left, Down right)
- Print-friendly CSS
- Mobile-responsive design

**PDF:**
- Professional typesetting
- Customizable fonts, grid size
- Separate files for blank and solution

**.puz (Across Lite format):**
- Industry-standard binary format
- Compatible with all crossword apps
- Includes grid, clues, solution, metadata

**JSON:**
- Machine-readable format
- Full puzzle state
- For saving/loading in-progress puzzles

---

### 7. CLI Interface (`src/cli/`)

**Purpose:** User-friendly command-line interface

**Commands:**

```bash
# Create new grid
crossword new --size 15 --output puzzle.json

# Add theme words
crossword theme puzzle.json --words "RASPBERRIES,YOGA,GREEN"

# Fill grid automatically
crossword fill puzzle.json --wordlist personal.txt --interactive

# Pattern matching
crossword pattern "?I?A" --wordlist personal.txt

# Add clues
crossword clue puzzle.json --difficulty 3

# Export
crossword export puzzle.json --format html --output birthday-puzzle.html

# Validate
crossword validate puzzle.json
```

**Interactive Mode:**
```bash
crossword interactive puzzle.json
> Commands: place, remove, fill, pattern, clue, export, save, quit
> Status: 15x15 grid, 12/78 words placed, 58% filled
```

---

## Data Flow

### Grid Creation Flow

```
1. User creates new grid
   └─> Grid Engine initializes empty grid
   
2. User places theme words (optional)
   ├─> Grid Engine validates word placement
   ├─> Grid Engine adds symmetric black squares
   └─> Grid Engine validates constraints
   
3. User triggers autofill
   ├─> Fill Engine analyzes empty slots
   ├─> Pattern Matcher generates candidates for each slot
   ├─> Backtracking algorithm fills grid
   └─> Result: Filled grid or "unfillable" error
   
4. User adds clues
   ├─> Clue Manager retrieves suggestions
   ├─> User selects/edits clues
   └─> Clues stored in puzzle state
   
5. User exports
   └─> Export Engine generates files
```

### Autofill Process (Detailed)

```
Input: Partially filled grid + word list

1. Analyze Grid State
   ├─> Identify empty slots (across and down words)
   ├─> Calculate constraints for each slot
   └─> Sort slots by constraint count (MCV heuristic)

2. For each slot (most constrained first):
   ├─> Generate pattern (e.g., "?I??R?")
   ├─> Pattern Matcher finds candidates
   ├─> Score candidates by:
   │   ├─> Crossword-ability
   │   ├─> Crossing constraints
   │   └─> Impact on remaining slots
   └─> Sort candidates (LCV heuristic)

3. Backtracking Search:
   ├─> Pick best candidate
   ├─> Place in grid
   ├─> Update crossing constraints (forward checking)
   ├─> Recurse to next slot
   ├─> If success: continue
   └─> If failure: backtrack (remove word, try next candidate)

4. Termination:
   ├─> Success: All slots filled
   └─> Failure: No valid complete fill exists

5. Return:
   └─> Filled grid OR list of problematic slots
```

---

## File Structure

```
crossword-builder/
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── grid.py              # Grid data structure
│   │   ├── cell.py              # Cell representation
│   │   ├── word.py              # Word placement & tracking
│   │   ├── symmetry.py          # Symmetry validation
│   │   ├── numbering.py         # Auto-numbering system
│   │   └── validator.py         # Constraint checking
│   │
│   ├── fill/
│   │   ├── __init__.py
│   │   ├── pattern_matcher.py  # Pattern → words
│   │   ├── word_list.py         # Word list management
│   │   ├── scorer.py            # Word scoring
│   │   ├── autofill.py          # Backtracking CSP solver
│   │   └── heuristics.py        # MCV, LCV, forward checking
│   │
│   ├── clues/
│   │   ├── __init__.py
│   │   ├── clue_manager.py      # Clue storage/retrieval
│   │   ├── clue_database.py     # Local clue DB
│   │   └── generator.py         # Clue generation helpers
│   │
│   ├── export/
│   │   ├── __init__.py
│   │   ├── html_exporter.py     # HTML generation
│   │   ├── pdf_exporter.py      # PDF generation
│   │   ├── puz_exporter.py      # .puz format
│   │   └── json_exporter.py     # JSON state
│   │
│   └── cli/
│       ├── __init__.py
│       ├── main.py              # CLI entry point
│       ├── commands.py          # Command implementations
│       └── interactive.py       # Interactive mode
│
├── data/
│   ├── wordlists/
│   │   ├── standard.txt         # Standard crossword words (300K)
│   │   ├── personal.txt         # User's personal words
│   │   └── scored_standard.tsv  # Pre-scored standard list
│   │
│   ├── clues/
│   │   └── clue_database.json   # Local clue storage
│   │
│   └── grids/
│       └── templates/           # Standard grid patterns
│
├── tests/
│   ├── __init__.py
│   ├── test_grid.py
│   ├── test_pattern_matcher.py
│   ├── test_autofill.py
│   ├── test_symmetry.py
│   └── fixtures/
│       └── test_grids.json      # Test puzzles
│
├── docs/
│   ├── ARCHITECTURE.md          # This file
│   ├── SPECIFICATIONS.md        # Technical specs
│   ├── USAGE.md                 # User guide
│   └── EXAMPLES.md              # Example workflows
│
├── .claude/
│   ├── CLAUDE.md                # Claude Code configuration
│   └── commands/
│       ├── build.md
│       ├── test.md
│       ├── pattern-match.md
│       └── fill-grid.md
│
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup
├── README.md                    # Project overview
└── .gitignore
```

---

## Technology Stack

### Core Dependencies

```python
# Grid operations
numpy>=1.24.0          # Fast array operations

# Pattern matching
regex>=2023.0.0        # Advanced pattern matching

# File formats
pypuz>=0.2.0          # .puz export
reportlab>=4.0.0       # PDF generation
Jinja2>=3.1.0         # HTML templating

# CLI
click>=8.1.0          # Command-line interface
rich>=13.0.0          # Beautiful terminal output
prompt-toolkit>=3.0.0 # Interactive mode

# Testing
pytest>=7.4.0         # Test framework
pytest-cov>=4.1.0     # Coverage reporting

# Code quality
mypy>=1.5.0           # Type checking
pylint>=2.17.0        # Linting
black>=23.7.0         # Code formatting
```

### Optional Dependencies

```python
# Enhanced features (install separately)
python-levenshtein>=0.21.0  # Fuzzy pattern matching
networkx>=3.1               # Graph algorithms for connectivity
matplotlib>=3.7.0           # Visualization (for debugging)
```

---

## Design Decisions & Rationale

### 1. Why NumPy for Grid?

**Decision:** Use `numpy.ndarray` for grid representation

**Rationale:**
- ✅ Fast array operations (critical for backtracking)
- ✅ Built-in matrix operations (rotation for symmetry)
- ✅ Memory-efficient for large grids
- ✅ Vectorized operations reduce code complexity
- ❌ Slight learning curve (but user is expert)

**Alternative Considered:** Plain 2D Python lists
- ✅ Simpler, no dependencies
- ❌ Slower for repeated access
- ❌ More complex symmetry validation

### 2. Why Backtracking CSP?

**Decision:** Use backtracking with heuristics for autofill

**Rationale:**
- ✅ Guaranteed to find solution if one exists
- ✅ Heuristics (MCV, LCV) dramatically improve performance
- ✅ Forward checking prevents dead ends early
- ✅ Well-understood algorithm, easy to debug
- ❌ Can be slow for highly constrained grids

**Alternative Considered:** Genetic algorithms
- ✅ Can find "good enough" solutions quickly
- ❌ No guarantee of finding solution
- ❌ More complex, harder to debug
- ❌ Overkill for this problem size

### 3. Why CLI over GUI?

**Decision:** Command-line interface with interactive mode

**Rationale:**
- ✅ Faster to implement (GUI is 3-5x more code)
- ✅ Scriptable, automatable
- ✅ Works over SSH, in terminals
- ✅ Expert users prefer CLIs
- ❌ Less visual feedback

**Alternative Considered:** Web interface
- ✅ Visual grid editing
- ✅ Better for non-technical users
- ❌ Requires frontend framework (React, etc.)
- ❌ More complex deployment
- ❌ Not needed for one-off birthday puzzle

### 4. Why Local Clue Database?

**Decision:** JSON-based local storage with optional imports

**Rationale:**
- ✅ Works offline
- ✅ Fast lookups
- ✅ User can curate personal clues
- ✅ No API dependencies
- ❌ Limited to stored clues

**Alternative Considered:** External API (OneLook, etc.)
- ✅ Huge clue database
- ✅ Always up-to-date
- ❌ Requires internet
- ❌ API rate limits
- ❌ Privacy concerns

**Compromise:** Support both, prefer local

---

## Performance Requirements

### Grid Operations
- **Create grid:** <10ms for any size
- **Validate symmetry:** <5ms for 21×21
- **Auto-numbering:** <20ms for 21×21

### Pattern Matching
- **Single pattern:** <100ms for 500K word list
- **Cache warm-up:** <2s to load 500K words into memory

### Autofill
- **Simple grid (few constraints):** <1s
- **Medium grid (typical):** 5-30s
- **Hard grid (highly constrained):** 1-5 min
- **Timeout:** 5 min max, then report unfillable slots

### Export
- **HTML:** <500ms
- **PDF:** <2s
- **.puz:** <100ms
- **JSON:** <50ms

---

## Error Handling Strategy

### Grid Validation Errors
```python
class SymmetryViolationError(GridError):
    """Raised when placing black square breaks symmetry"""
    pass

class UnconnectedRegionError(GridError):
    """Raised when grid has isolated sections"""
    pass

class UncheckedSquareError(GridError):
    """Raised when letter appears in only one direction"""
    pass
```

**Behavior:** Prevent invalid operations at placement time, not at validation time

### Autofill Errors
```python
class UnfillableGridError(FillError):
    """Raised when no valid complete fill exists"""
    def __init__(self, problematic_slots: List[Slot]):
        self.slots = problematic_slots  # Which slots caused failure
```

**Behavior:** Return partial fill + problematic slots for manual adjustment

### Word List Errors
```python
class WordListNotFoundError(IOError):
    """Raised when word list file doesn't exist"""
    pass

class InvalidWordListFormatError(ValueError):
    """Raised when word list has incorrect format"""
    pass
```

**Behavior:** Clear error message with example of correct format

---

## Testing Strategy

### Unit Tests
- All core functions (grid, symmetry, numbering)
- Pattern matcher with edge cases
- Word scorer with various inputs
- Clue manager CRUD operations

### Integration Tests
- End-to-end grid creation → fill → export
- Multi-step workflows
- Error recovery scenarios

### Test Fixtures
- Pre-made grids of various sizes
- Known-solvable puzzles (regression tests)
- Edge cases (unfillable grids, unusual patterns)

### Coverage Target
- Overall: >80%
- Core modules (grid, fill): >90%
- CLI: >70% (harder to test, less critical)

---

## Future Enhancements (Out of Scope for V1)

### Phase 2 Features
- **Rebus support:** Multiple letters in one square
- **Theme detection:** Analyze grid to identify theme pattern
- **Clue difficulty AI:** ML model to rate clue difficulty
- **Web interface:** Visual grid editor

### Phase 3 Features
- **Collaborative editing:** Multiple users, real-time
- **Puzzle database:** Search published puzzles by theme
- **Competition mode:** Timed solving with leaderboard
- **Mobile app:** iOS/Android crossword constructor

---

## Success Metrics

**V1 Complete When:**
- ✅ Can create 15×15 grid with personal word list
- ✅ Autofill works for typical grids in <30s
- ✅ Export to HTML and .puz formats
- ✅ Pattern matching <100ms for 500K words
- ✅ Test coverage >80%
- ✅ Successfully create partner's birthday puzzle

**Quality Indicators:**
- Grid fills use >80% "good fill" (score >70)
- <5% crosswordese (score <50)
- Symmetry never violated
- No unchecked squares ever
- Auto-numbering 100% accurate

---

## Implementation Order (for Claude Code)

### Phase 1: Foundation (Week 1)
1. Project structure & setup
2. Grid data structure
3. Symmetry validation
4. Auto-numbering
5. Basic CLI skeleton
6. Unit tests for core

### Phase 2: Pattern Matching (Week 1)
7. Word list loader
8. Pattern matcher (basic wildcards)
9. Word scorer
10. Tests for pattern matching

### Phase 3: Autofill (Week 2)
11. Constraint satisfaction setup
12. Backtracking algorithm (naive)
13. Heuristics (MCV, LCV)
14. Forward checking
15. Tests with known-solvable grids

### Phase 4: Export & Polish (Week 2)
16. HTML exporter
17. .puz exporter
18. Clue manager (basic)
19. CLI commands implementation
20. Integration tests
21. Documentation & examples

---

## Dependencies on External Systems

### None Required
- No Claude-specific features (Skills, Agents)
- No external APIs (all offline)
- No cloud services

### Optional Enhancements
- OneLook API for pattern matching (future)
- Crossword database APIs for clues (future)
- GitHub Actions for CI/CD (convenience)

---

## Configuration

### `config.yaml` (User Settings)

```yaml
# Word list preferences
wordlists:
  default: data/wordlists/standard.txt
  personal: data/wordlists/personal.txt
  
# Autofill settings
autofill:
  timeout_seconds: 300
  min_word_score: 30
  prefer_personal_words: true
  
# Export settings
export:
  html_template: default
  pdf_font: "Helvetica"
  pdf_grid_size: 0.5  # inches per square
  
# Clue settings
clues:
  default_difficulty: 3  # Wednesday level
  max_suggestions: 5
```

---

## Maintenance & Updates

### Word List Updates
- User maintains personal word list manually
- Standard word list updated quarterly (download from source)
- Scored lists recalculated on major updates

### Clue Database Updates
- Import from external sources (CSV/JSON)
- Merge with existing, prefer newer clues
- User can flag clues for removal

### Code Updates
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Breaking changes = major version bump
- New features = minor version bump
- Bug fixes = patch version bump

---

## Conclusion

This architecture prioritizes the primary pain point (grid filling) while providing a complete, self-contained crossword construction toolkit. The design is pragmatic: proven algorithms, simple data structures, no complex dependencies. Perfect for an expert developer building a one-off personalized puzzle with potential for future reuse.

**Next Steps:**
1. Read `SPECIFICATIONS.md` for implementation details
2. Follow `CLAUDE-CODE-PROMPTS.md` for step-by-step building
3. Reference this document for design questions
