# Crossword Helper - Implementation Specification

## Overview

This document provides detailed implementation requirements for all components of the Crossword Helper system.

**Target Audience:** Developers (Claude Code)  
**Prerequisite Reading:** Architecture Document, API Specification  

---

## Project Structure

```
crossword-helper/
├── backend/
│   ├── __init__.py
│   ├── app.py                    # Flask app entry + config
│   ├── core/                     # Business logic (service layer)
│   │   ├── __init__.py
│   │   ├── pattern_matcher.py   # Pattern matching + scoring
│   │   ├── numbering.py          # Auto-numbering + validation
│   │   ├── conventions.py        # Entry normalization
│   │   └── scoring.py            # Word scoring algorithms
│   ├── api/                      # API layer (Flask routes)
│   │   ├── __init__.py
│   │   ├── routes.py             # Endpoint definitions
│   │   ├── validators.py         # Request validation
│   │   └── errors.py             # Error handling
│   └── data/                     # Data access layer
│       ├── __init__.py
│       ├── onelook_client.py    # OneLook API integration
│       └── wordlist_manager.py  # File-based wordlist loading
│
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   │   └── main.css          # All styles (mobile-first)
│   │   ├── js/
│   │   │   ├── app.js            # Main application logic
│   │   │   ├── pattern.js        # Pattern matcher component
│   │   │   ├── numbering.js      # Numbering validator component
│   │   │   └── conventions.js    # Convention helper component
│   │   └── img/
│   │       └── logo.png
│   └── templates/
│       └── index.html            # Single page application
│
├── data/
│   └── wordlists/
│       ├── standard.txt          # Common crossword fill
│       └── personal.txt          # User's custom words
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── unit/
│   │   ├── test_pattern_matcher.py
│   │   ├── test_numbering.py
│   │   ├── test_conventions.py
│   │   └── test_scoring.py
│   ├── integration/
│   │   ├── test_api_pattern.py
│   │   ├── test_api_numbering.py
│   │   └── test_api_conventions.py
│   └── fixtures/
│       ├── sample_grids.json     # Test grid data
│       └── sample_wordlists.txt
│
├── .claude/
│   └── CLAUDE.md                 # Project configuration
│
├── run.py                        # Application entry point
├── requirements.txt              # Python dependencies
├── README.md                     # Setup and usage documentation
├── .gitignore
└── LICENSE
```

---

## Component Implementation Details

## 1. Backend - Service Layer

### 1.1 Pattern Matcher (`backend/core/pattern_matcher.py`)

**Purpose:** Find words matching crossword patterns, score by crossword-ability.

**Class Interface:**
```python
from typing import List, Tuple, Optional

class PatternMatcher:
    def __init__(self, wordlist_names: List[str] = None):
        """
        Initialize pattern matcher with word lists.
        
        Args:
            wordlist_names: List of wordlist file names (e.g., ['personal', 'standard'])
                          If None, uses ['standard']
        """
        pass
    
    def search(
        self, 
        pattern: str, 
        max_results: int = 20
    ) -> List[Tuple[str, int, str]]:
        """
        Find words matching pattern.
        
        Args:
            pattern: Pattern with ? as wildcards (e.g., '?I?A')
            max_results: Maximum number of results to return
        
        Returns:
            List of (word, score, source) tuples, sorted by score descending
            
        Raises:
            ValueError: If pattern is invalid (no ?, too long, etc.)
        """
        pass
    
    def score_word(self, word: str) -> int:
        """
        Calculate crossword-ability score for word.
        
        Args:
            word: Word to score (uppercase)
        
        Returns:
            Score from 1-100 (higher is better)
        """
        pass
    
    def _merge_results(
        self,
        onelook_words: List[str],
        local_words: List[str]
    ) -> List[Tuple[str, int, str]]:
        """
        Merge results from OneLook API and local wordlists.
        
        Args:
            onelook_words: Words from OneLook API
            local_words: Words from local wordlists
        
        Returns:
            Merged list with (word, score, source) tuples
        """
        pass
```

**Implementation Requirements:**

**1.1.1 Pattern Validation:**
```python
def _validate_pattern(pattern: str) -> None:
    """
    Validate pattern format.
    
    Rules:
    - Must contain at least one ?
    - Length must be 3-15 characters
    - Must contain only A-Z and ?
    
    Raises:
        ValueError: With specific message about what's wrong
    """
    if '?' not in pattern:
        raise ValueError("Pattern must contain at least one ? wildcard")
    
    if len(pattern) < 3 or len(pattern) > 15:
        raise ValueError(f"Pattern length must be 3-15, got {len(pattern)}")
    
    if not all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ?' for c in pattern):
        raise ValueError("Pattern must contain only letters and ?")
```

**1.1.2 Local Word List Matching:**
```python
def _match_local(self, pattern: str, words: List[str]) -> List[str]:
    """
    Match pattern against local word list.
    
    Algorithm:
    1. Filter words by length (must match pattern length)
    2. For each word, check if it matches pattern:
       - ? matches any letter
       - A-Z must match exactly
    3. Return matching words
    
    Example:
        pattern = '?I?A'
        'VISA' matches (length 4, positions match)
        'PIZZA' doesn't match (length 5)
        'BEST' doesn't match (positions don't match)
    """
    matches = []
    pattern_len = len(pattern)
    
    for word in words:
        if len(word) != pattern_len:
            continue
        
        if all(
            pattern[i] == '?' or pattern[i] == word[i]
            for i in range(pattern_len)
        ):
            matches.append(word)
    
    return matches
```

**1.1.3 OneLook API Integration:**
```python
def _search_onelook(self, pattern: str) -> List[str]:
    """
    Query OneLook API for matching words.
    
    API: https://www.onelook.com/
    Endpoint: https://api.onelook.com/words?sp={pattern}
    
    Timeout: 5 seconds
    Fallback: Return empty list on error (graceful degradation)
    
    Returns:
        List of words (uppercase)
    """
    try:
        response = requests.get(
            'https://api.onelook.com/words',
            params={'sp': pattern.lower(), 'max': 100},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        return [entry['word'].upper() for entry in data]
    except (requests.Timeout, requests.RequestException) as e:
        logger.warning(f"OneLook API unavailable: {e}")
        return []
```

**1.1.4 Scoring Algorithm:**
```python
COMMON_LETTERS = set('EARIOTNS')
UNCOMMON_LETTERS = set('JQXZ')

def score_word(self, word: str) -> int:
    """
    Score word for crossword-ability.
    
    Algorithm:
    1. Count common letters (E, A, R, I, O, T, N, S) → +10 each
    2. Count regular letters → +5 each
    3. Count uncommon letters (J, Q, X, Z) → -15 each
    4. Length bonus → +2 per letter
    5. Clamp to 1-100
    
    Examples:
        'AREA': 4 common (40) + 0 uncommon + length 4 (8) = 48
        'QUIZ': 1 common (10) + 1 regular (5) + 2 uncommon (-30) + length 4 (8) = -7 → 1
        'YOGA': 1 common (10) + 3 regular (15) + 0 uncommon + length 4 (8) = 33
    """
    common_count = sum(1 for c in word if c in COMMON_LETTERS)
    uncommon_count = sum(1 for c in word if c in UNCOMMON_LETTERS)
    regular_count = len(word) - common_count - uncommon_count
    
    base_score = (common_count * 10) + (regular_count * 5) - (uncommon_count * 15)
    length_bonus = len(word) * 2
    
    final_score = base_score + length_bonus
    return max(1, min(100, final_score))
```

**1.1.5 Letter Quality Analysis:**
```python
def _analyze_letters(self, word: str) -> dict:
    """
    Analyze letter quality for word.
    
    Returns:
        {
            'common': count of E/A/R/I/O/T/N/S,
            'uncommon': count of J/Q/X/Z
        }
    """
    return {
        'common': sum(1 for c in word if c in COMMON_LETTERS),
        'uncommon': sum(1 for c in word if c in UNCOMMON_LETTERS)
    }
```

**Test Requirements:**
- Test pattern validation (valid/invalid cases)
- Test local matching (exact matches, wildcards)
- Test OneLook integration (mock responses)
- Test scoring (edge cases: all common, all uncommon)
- Test merging (deduplicate, sort by score)

---

### 1.2 Numbering Validator (`backend/core/numbering.py`)

**Purpose:** Auto-number grids, validate user numbering.

**Class Interface:**
```python
from typing import Dict, Tuple, List

class NumberingValidator:
    def auto_number(self, grid: List[List[str]]) -> Dict[Tuple[int, int], int]:
        """
        Automatically number grid using standard crossword rules.
        
        Args:
            grid: 2D array of grid cells (A-Z, #, .)
        
        Returns:
            Dict mapping (row, col) to number
        """
        pass
    
    def validate(
        self,
        grid: List[List[str]],
        user_numbering: Dict[Tuple[int, int], int]
    ) -> Tuple[bool, List[dict]]:
        """
        Validate user's numbering against standard rules.
        
        Args:
            grid: 2D array of grid cells
            user_numbering: User's numbering to validate
        
        Returns:
            (is_valid, list_of_errors)
            
        Error dict format:
            {
                'type': 'MISSING_NUMBER' | 'WRONG_NUMBER' | 'EXTRA_NUMBER',
                'position': (row, col),
                'expected': number or None,
                'actual': number or None,
                'message': human-readable explanation
            }
        """
        pass
    
    def analyze_grid(self, grid: List[List[str]]) -> dict:
        """
        Analyze grid characteristics.
        
        Returns:
            {
                'size': [rows, cols],
                'black_squares': count,
                'white_squares': count,
                'word_count': count,
                'black_square_percentage': percentage,
                'meets_nyt_standards': bool
            }
        """
        pass
```

**Implementation Requirements:**

**1.2.1 Auto-Numbering Algorithm:**
```python
def auto_number(self, grid: List[List[str]]) -> Dict[Tuple[int, int], int]:
    """
    Standard crossword numbering algorithm.
    
    Rules:
    1. Scan grid left-to-right, top-to-bottom
    2. For each white cell:
       a. Check if starts ACROSS word:
          - Cell to left is black OR at left edge
          - AND cell to right exists and is not black
       b. Check if starts DOWN word:
          - Cell above is black OR at top edge
          - AND cell below exists and is not black
       c. If starts across OR down: assign next number
    3. Numbers increment sequentially (1, 2, 3, ...)
    4. Each cell gets at most one number
    
    Example:
        R  A  T
        #  T  #
        C  A  T
        
        Numbers:
        1  2     (1: starts across+down, 2: starts across)
        #  3  #  (3: starts down)
        4  5     (4: starts across+down, 5: starts across)
    """
    numbering = {}
    current_number = 1
    rows, cols = len(grid), len(grid[0])
    
    for row in range(rows):
        for col in range(cols):
            if grid[row][col] == '#':
                continue
            
            starts_across = (
                (col == 0 or grid[row][col-1] == '#') and
                (col < cols-1 and grid[row][col+1] != '#')
            )
            
            starts_down = (
                (row == 0 or grid[row-1][col] == '#') and
                (row < rows-1 and grid[row+1][col] != '#')
            )
            
            if starts_across or starts_down:
                numbering[(row, col)] = current_number
                current_number += 1
    
    return numbering
```

**1.2.2 Grid Validation:**
```python
def _validate_grid(self, grid: List[List[str]]) -> None:
    """
    Validate grid format.
    
    Rules:
    - Must be square (n×n)
    - Size must be 11×11, 15×15, or 21×21
    - Cells must be A-Z, #, or .
    
    Raises:
        ValueError: With specific message
    """
    rows = len(grid)
    cols = len(grid[0]) if grid else 0
    
    if rows != cols:
        raise ValueError(f"Grid must be square, got {rows}×{cols}")
    
    if rows not in [11, 15, 21]:
        raise ValueError(f"Grid size must be 11×11, 15×15, or 21×21, got {rows}×{rows}")
    
    for row_idx, row in enumerate(grid):
        for col_idx, cell in enumerate(row):
            if not (cell == '#' or cell == '.' or (len(cell) == 1 and cell.isalpha())):
                raise ValueError(
                    f"Invalid cell value '{cell}' at ({row_idx}, {col_idx}). "
                    f"Must be A-Z, #, or ."
                )
```

**1.2.3 Grid Analysis:**
```python
def analyze_grid(self, grid: List[List[str]]) -> dict:
    """
    Analyze grid characteristics.
    
    NYT Standards (for 15×15):
    - Black squares: <16% (~36 squares)
    - Word count: <78 (themed), <72 (themeless)
    """
    rows, cols = len(grid), len(grid[0])
    total_squares = rows * cols
    
    black_count = sum(
        1 for row in grid for cell in row if cell == '#'
    )
    white_count = total_squares - black_count
    
    # Count words (simplified: count number cells)
    numbering = self.auto_number(grid)
    word_count = len(numbering) * 2  # Rough estimate
    
    black_percentage = (black_count / total_squares) * 100
    
    # NYT standards check
    max_black_percentage = 16
    max_words = 78 if rows == 15 else 140  # 15×15 or 21×21
    
    meets_standards = (
        black_percentage <= max_black_percentage and
        word_count <= max_words
    )
    
    return {
        'size': [rows, cols],
        'black_squares': black_count,
        'white_squares': white_count,
        'word_count': word_count,
        'black_square_percentage': round(black_percentage, 1),
        'meets_nyt_standards': meets_standards
    }
```

**Test Requirements:**
- Test auto-numbering (various grid sizes, edge cases)
- Test validation (correct/incorrect numbering)
- Test grid analysis (count squares, check standards)
- Test edge cases (empty grid, all black, single row)

---

### 1.3 Convention Helper (`backend/core/conventions.py`)

**Purpose:** Normalize entry conventions with explanations.

**Class Interface:**
```python
from typing import Tuple, Dict, List

class ConventionHelper:
    # Convention rules
    RULES = {
        'two_word_names': {
            'pattern': r'^[A-Z][a-z]+ [A-Z][a-z]+$',
            'transform': lambda s: s.replace(' ', '').upper(),
            'description': 'Remove space between words, capitalize all',
            'examples': [
                ('Tina Fey', 'TINAFEY'),
                ('Tracy Jordan', 'TRACYJORDAN'),
                ('Real Madrid', 'REALMADRID')
            ]
        },
        'title_with_article': {
            'pattern': r'^(La|Le|The|A|An) ',
            'transform': lambda s: s.replace(' ', '').upper(),
            'description': 'Remove space after article (La/Le/The/A/An)',
            'examples': [
                ('La haine', 'LAHAINE'),
                ('The Office', 'THEOFFICE'),
                ('A Star Is Born', 'ASTARISBORN')
            ]
        },
        'hyphenated': {
            'pattern': r'-',
            'transform': lambda s: s.replace('-', '').upper(),
            'description': 'Remove hyphen',
            'examples': [
                ('self-aware', 'SELFAWARE'),
                ('co-worker', 'COWORKER'),
                ('real-time', 'REALTIME')
            ]
        },
        'apostrophe': {
            'pattern': r"'",
            'transform': lambda s: s.replace("'", '').upper(),
            'description': "Remove apostrophe",
            'examples': [
                ("driver's license", "DRIVERSLICENSE"),
                ("can't", "CANT"),
                ("it's", "ITS")
            ]
        }
    }
    
    def normalize(self, text: str) -> Tuple[str, Dict]:
        """
        Normalize entry according to conventions.
        
        Args:
            text: Entry to normalize
        
        Returns:
            (normalized_text, rule_info)
            
        Rule info format:
            {
                'type': rule_name,
                'description': description,
                'pattern': regex pattern,
                'examples': [(input, output), ...],
                'confidence': 'high' | 'medium' | 'low'
            }
        """
        pass
    
    def get_alternatives(self, text: str, normalized: str) -> List[Dict]:
        """
        Get alternative normalizations if applicable.
        
        Returns:
            List of {'form': alternative, 'note': explanation, 'confidence': level}
        """
        pass
```

**Implementation Requirements:**

**1.3.1 Rule Matching:**
```python
import re

def normalize(self, text: str) -> Tuple[str, Dict]:
    """
    Apply first matching rule, or default if none match.
    
    Algorithm:
    1. Try each rule in order
    2. If pattern matches, apply transformation
    3. Return normalized text + rule info
    4. If no match, apply default (remove spaces, uppercase)
    """
    for rule_name, rule in self.RULES.items():
        if re.search(rule['pattern'], text):
            normalized = rule['transform'](text)
            return (normalized, {
                'type': rule_name,
                'description': rule['description'],
                'pattern': rule['pattern'],
                'examples': rule['examples'],
                'confidence': 'high'
            })
    
    # Default rule
    normalized = text.replace(' ', '').upper()
    return (normalized, {
        'type': 'default',
        'description': 'Default: remove spaces, uppercase',
        'examples': [],
        'confidence': 'medium'
    })
```

**1.3.2 Alternatives Generation:**
```python
def get_alternatives(self, text: str, normalized: str) -> List[Dict]:
    """
    Generate alternative normalizations for edge cases.
    
    Cases that have alternatives:
    - Very long entries (>15 letters): suggest keeping spaces
    - Titles with articles: suggest keeping/removing article
    """
    alternatives = []
    
    if len(normalized) > 15:
        with_spaces = text.upper()
        alternatives.append({
            'form': with_spaces,
            'note': 'Keep spaces for very long entries (easier to read)',
            'confidence': 'medium'
        })
    
    # Check if title with article
    if re.match(r'^(La|Le|The|A|An) ', text):
        without_article = re.sub(r'^(La|Le|The|A|An) ', '', text).replace(' ', '').upper()
        if without_article != normalized:
            alternatives.append({
                'form': without_article,
                'note': 'Alternative: remove article entirely',
                'confidence': 'low'
            })
    
    return alternatives
```

**Test Requirements:**
- Test each rule type with examples
- Test default rule (no pattern match)
- Test alternatives generation
- Test edge cases (empty string, very long text)

---

## 2. Backend - Data Layer

### 2.1 OneLook Client (`backend/data/onelook_client.py`)

**Purpose:** Interface to OneLook API with error handling.

**Class Interface:**
```python
import requests
import logging

class OneLookClient:
    BASE_URL = 'https://api.onelook.com/words'
    
    def __init__(self, timeout: int = 5):
        """
        Initialize OneLook API client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
    
    def search(self, pattern: str, max_results: int = 100) -> List[str]:
        """
        Search OneLook API for pattern matches.
        
        Args:
            pattern: Crossword pattern (e.g., '?i?a')
            max_results: Maximum number of results
        
        Returns:
            List of matching words (uppercase)
            Empty list on error (graceful degradation)
        """
        try:
            response = requests.get(
                self.BASE_URL,
                params={'sp': pattern.lower(), 'max': max_results},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            words = [entry['word'].upper() for entry in data]
            
            self.logger.info(f"OneLook found {len(words)} matches for '{pattern}'")
            return words
            
        except requests.Timeout:
            self.logger.warning(f"OneLook API timeout for pattern '{pattern}'")
            return []
        
        except requests.RequestException as e:
            self.logger.warning(f"OneLook API error: {e}")
            return []
        
        except (KeyError, ValueError) as e:
            self.logger.error(f"OneLook response parsing error: {e}")
            return []
```

**Test Requirements:**
- Mock successful responses
- Mock timeout scenarios
- Mock error responses (404, 500)
- Mock malformed JSON
- Verify logging

---

### 2.2 Word List Manager (`backend/data/wordlist_manager.py`)

**Purpose:** Load and cache word lists from files.

**Class Interface:**
```python
import os
from typing import List, Dict

class WordListManager:
    def __init__(self, wordlist_dir: str = 'data/wordlists'):
        """
        Initialize word list manager.
        
        Args:
            wordlist_dir: Directory containing .txt wordlist files
        """
        self.wordlist_dir = wordlist_dir
        self._cache: Dict[str, List[str]] = {}
    
    def load(self, name: str) -> List[str]:
        """
        Load word list from file (with caching).
        
        Args:
            name: Wordlist name (without .txt extension)
        
        Returns:
            List of words (uppercase)
        
        Raises:
            FileNotFoundError: If wordlist doesn't exist
        """
        if name in self._cache:
            return self._cache[name]
        
        filepath = os.path.join(self.wordlist_dir, f"{name}.txt")
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Wordlist '{name}' not found at {filepath}"
            )
        
        words = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    words.append(line.upper())
        
        self._cache[name] = words
        return words
    
    def list_available(self) -> List[str]:
        """
        List all available wordlists.
        
        Returns:
            List of wordlist names (without .txt extension)
        """
        if not os.path.exists(self.wordlist_dir):
            return []
        
        files = os.listdir(self.wordlist_dir)
        return [
            f[:-4]  # Remove .txt
            for f in files
            if f.endswith('.txt')
        ]
```

**Test Requirements:**
- Test loading existing wordlist
- Test caching (load twice, check cache hit)
- Test missing wordlist (FileNotFoundError)
- Test comment/empty line handling
- Test list_available

---

## 3. Backend - API Layer

### 3.1 Routes (`backend/api/routes.py`)

**Purpose:** Flask route definitions (thin wrapper around services).

**Structure:**
```python
from flask import Blueprint, request, jsonify
from backend.core.pattern_matcher import PatternMatcher
from backend.core.numbering import NumberingValidator
from backend.core.conventions import ConventionHelper
from backend.api.validators import validate_pattern_request, validate_grid_request
from backend.api.errors import handle_error

api = Blueprint('api', __name__)

# Initialize services
pattern_matcher = PatternMatcher(['personal', 'standard'])
numbering_validator = NumberingValidator()
convention_helper = ConventionHelper()

@api.route('/pattern', methods=['POST'])
def pattern_search():
    """POST /api/pattern - Pattern search endpoint."""
    try:
        # Validate request
        data = validate_pattern_request(request.json)
        
        # Delegate to service
        results = pattern_matcher.search(
            pattern=data['pattern'],
            max_results=data.get('max_results', 20)
        )
        
        # Format response
        return jsonify({
            'results': [
                {
                    'word': word,
                    'score': score,
                    'source': source,
                    'length': len(word),
                    'letter_quality': pattern_matcher._analyze_letters(word)
                }
                for word, score, source in results
            ],
            'meta': {
                'pattern': data['pattern'],
                'total_found': len(results),
                'results_returned': min(len(results), data.get('max_results', 20)),
                'query_time_ms': 0  # TODO: add timing
            }
        }), 200
        
    except ValueError as e:
        return handle_error('INVALID_PATTERN', str(e), 400)
    except Exception as e:
        return handle_error('INTERNAL_ERROR', str(e), 500)

@api.route('/number', methods=['POST'])
def number_grid():
    """POST /api/number - Numbering validation endpoint."""
    # Similar structure to pattern_search
    pass

@api.route('/normalize', methods=['POST'])
def normalize_entry():
    """POST /api/normalize - Convention normalization endpoint."""
    # Similar structure to pattern_search
    pass
```

**Implementation Requirements:**
- Keep routes thin (validation + delegation + formatting)
- No business logic in routes
- Consistent error handling
- Timing middleware for performance tracking

**Test Requirements:**
- Test each endpoint with valid requests
- Test error cases (400, 404, 500)
- Test validation rejection
- Mock service layer for isolation

---

### 3.2 Validators (`backend/api/validators.py`)

**Purpose:** Request validation (before hitting service layer).

**Functions:**
```python
def validate_pattern_request(data: dict) -> dict:
    """
    Validate pattern search request.
    
    Checks:
    - pattern exists and is string
    - wordlists is list of strings (if provided)
    - max_results is integer 1-100 (if provided)
    
    Returns:
        Validated data dict
    
    Raises:
        ValueError: With specific message
    """
    if not data:
        raise ValueError("Request body is required")
    
    if 'pattern' not in data:
        raise ValueError("Field 'pattern' is required")
    
    if not isinstance(data['pattern'], str):
        raise ValueError("Field 'pattern' must be string")
    
    if 'wordlists' in data:
        if not isinstance(data['wordlists'], list):
            raise ValueError("Field 'wordlists' must be array")
        if not all(isinstance(w, str) for w in data['wordlists']):
            raise ValueError("Field 'wordlists' must contain strings")
    
    if 'max_results' in data:
        if not isinstance(data['max_results'], int):
            raise ValueError("Field 'max_results' must be integer")
        if not 1 <= data['max_results'] <= 100:
            raise ValueError("Field 'max_results' must be 1-100")
    
    return data

def validate_grid_request(data: dict) -> dict:
    """Validate grid request (similar structure)."""
    pass

def validate_normalize_request(data: dict) -> dict:
    """Validate normalize request (similar structure)."""
    pass
```

---

### 3.3 Error Handlers (`backend/api/errors.py`)

**Purpose:** Consistent error response formatting.

**Functions:**
```python
from flask import jsonify

def handle_error(code: str, message: str, status: int, details: dict = None):
    """
    Format error response consistently.
    
    Args:
        code: Error code (e.g., 'INVALID_PATTERN')
        message: Human-readable message
        status: HTTP status code
        details: Optional additional context
    
    Returns:
        Flask response tuple (json, status)
    """
    response = {
        'error': {
            'code': code,
            'message': message
        }
    }
    
    if details:
        response['error']['details'] = details
    
    return jsonify(response), status
```

---

## 4. Frontend Implementation

### 4.1 HTML Structure (`frontend/templates/index.html`)

**Requirements:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crossword Helper</title>
    <link rel="stylesheet" href="/static/css/main.css">
</head>
<body>
    <header>
        <h1>Crossword Helper</h1>
        <p>Tools for crossword construction</p>
    </header>
    
    <main>
        <!-- Pattern Matcher Section -->
        <section id="pattern-matcher" class="tool-section">
            <h2>Pattern Matcher</h2>
            <p>Find words matching pattern (use ? for any letter)</p>
            
            <div class="tool-input">
                <input 
                    type="text" 
                    id="pattern-input" 
                    placeholder="?I?A"
                    maxlength="15"
                    aria-label="Pattern"
                >
                <button id="pattern-search-btn">Search</button>
                <button id="pattern-clear-btn">Clear</button>
            </div>
            
            <div id="pattern-results" class="results-container"></div>
        </section>
        
        <!-- Numbering Validator Section -->
        <section id="numbering-validator" class="tool-section">
            <h2>Numbering Validator</h2>
            <p>Auto-number grid or validate existing numbering</p>
            
            <div class="tool-input">
                <textarea 
                    id="grid-input" 
                    placeholder="Paste grid JSON"
                    aria-label="Grid JSON"
                ></textarea>
                <button id="grid-validate-btn">Validate</button>
            </div>
            
            <div id="grid-results" class="results-container"></div>
        </section>
        
        <!-- Convention Helper Section -->
        <section id="convention-helper" class="tool-section">
            <h2>Convention Helper</h2>
            <p>Normalize entry conventions</p>
            
            <div class="tool-input">
                <input 
                    type="text" 
                    id="convention-input" 
                    placeholder="Tina Fey"
                    maxlength="50"
                    aria-label="Entry to normalize"
                >
                <button id="convention-normalize-btn">Normalize</button>
            </div>
            
            <div id="convention-results" class="results-container"></div>
        </section>
    </main>
    
    <footer>
        <p>Crossword Helper v1.0 | <a href="https://github.com/...">GitHub</a></p>
    </footer>
    
    <!-- Load scripts -->
    <script src="/static/js/app.js"></script>
    <script src="/static/js/pattern.js"></script>
    <script src="/static/js/numbering.js"></script>
    <script src="/static/js/conventions.js"></script>
</body>
</html>
```

**Accessibility Requirements:**
- Use semantic HTML (header, main, section, footer)
- Proper heading hierarchy (h1 → h2)
- ARIA labels on all inputs
- Focus management (buttons, inputs)
- Keyboard navigation support

---

### 4.2 CSS Styling (`frontend/static/css/main.css`)

**Requirements:**

**Mobile-First Approach:**
```css
/* Base styles (mobile) */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    margin: 0;
    padding: 20px;
    background: #f5f5f5;
}

.tool-section {
    background: white;
    padding: 20px;
    margin-bottom: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.tool-input {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
}

input, textarea {
    flex: 1;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 16px;
}

button {
    padding: 10px 20px;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 16px;
}

button:hover {
    background: #0056b3;
}

button:disabled {
    background: #ccc;
    cursor: not-allowed;
}

/* Desktop styles */
@media (min-width: 768px) {
    body {
        max-width: 1200px;
        margin: 0 auto;
    }
    
    .tool-section {
        padding: 30px;
    }
}
```

**Loading States:**
```css
.loading {
    opacity: 0.6;
    pointer-events: none;
}

.spinner {
    border: 3px solid #f3f3f3;
    border-top: 3px solid #007bff;
    border-radius: 50%;
    width: 20px;
    height: 20px;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
```

**Error States:**
```css
.error {
    color: #dc3545;
    background: #f8d7da;
    border: 1px solid #f5c6cb;
    padding: 10px;
    border-radius: 4px;
    margin-top: 10px;
}
```

---

### 4.3 JavaScript Components

**Pattern Matcher (`frontend/static/js/pattern.js`):**
```javascript
async function searchPattern() {
    const input = document.getElementById('pattern-input');
    const resultsDiv = document.getElementById('pattern-results');
    const searchBtn = document.getElementById('pattern-search-btn');
    
    const pattern = input.value.trim().toUpperCase();
    
    if (!pattern) {
        showError(resultsDiv, 'Please enter a pattern');
        return;
    }
    
    // Show loading state
    searchBtn.disabled = true;
    resultsDiv.innerHTML = '<div class="spinner"></div> Searching...';
    
    try {
        const response = await fetch('/api/pattern', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({pattern})
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error.message);
        }
        
        renderPatternResults(data, resultsDiv);
        
    } catch (error) {
        showError(resultsDiv, error.message);
    } finally {
        searchBtn.disabled = false;
    }
}

function renderPatternResults(data, container) {
    if (data.results.length === 0) {
        container.innerHTML = '<p>No matches found</p>';
        return;
    }
    
    const html = `
        <p>Found ${data.meta.total_found} matches (showing top ${data.results_returned})</p>
        <table>
            <thead>
                <tr>
                    <th>Word</th>
                    <th>Score</th>
                    <th>Quality</th>
                    <th>Source</th>
                </tr>
            </thead>
            <tbody>
                ${data.results.map(r => `
                    <tr>
                        <td><strong>${r.word}</strong></td>
                        <td>${r.score}</td>
                        <td>${'⭐'.repeat(Math.floor(r.score / 20))}</td>
                        <td>${r.source}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

function showError(container, message) {
    container.innerHTML = `<div class="error">${message}</div>`;
}

// Event listeners
document.getElementById('pattern-search-btn').addEventListener('click', searchPattern);
document.getElementById('pattern-clear-btn').addEventListener('click', () => {
    document.getElementById('pattern-input').value = '';
    document.getElementById('pattern-results').innerHTML = '';
});

// Enter key support
document.getElementById('pattern-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') searchPattern();
});
```

**Similar structure for:**
- `numbering.js` - Numbering validator component
- `conventions.js` - Convention helper component

---

## 5. Testing Requirements

### Unit Test Example

```python
# tests/unit/test_pattern_matcher.py
import pytest
from backend.core.pattern_matcher import PatternMatcher

def test_pattern_match_simple():
    """Test basic pattern matching with wildcards."""
    matcher = PatternMatcher(['test'])
    # Load test wordlist with known words
    
    results = matcher.search('?I?A')
    
    assert len(results) > 0
    assert all(len(word) == 4 for word, _, _ in results)
    assert all(word[1] == 'I' and word[3] == 'A' for word, _, _ in results)

def test_invalid_pattern():
    """Test that invalid patterns raise ValueError."""
    matcher = PatternMatcher([])
    
    with pytest.raises(ValueError, match="must contain at least one"):
        matcher.search('ABCD')

def test_score_word_common_letters():
    """Test scoring favors common letters."""
    matcher = PatternMatcher([])
    
    score_common = matcher.score_word('AREA')  # All common
    score_uncommon = matcher.score_word('QUIZ')  # Has Q, Z
    
    assert score_common > score_uncommon
```

### Integration Test Example

```python
# tests/integration/test_api_pattern.py
import pytest
from backend.app import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

def test_pattern_endpoint_success(client):
    """Test /api/pattern with valid input."""
    response = client.post('/api/pattern', json={
        'pattern': '?I?A'
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'results' in data
    assert len(data['results']) > 0

def test_pattern_endpoint_invalid(client):
    """Test /api/pattern with invalid pattern."""
    response = client.post('/api/pattern', json={
        'pattern': 'ABCD'
    })
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert data['error']['code'] == 'INVALID_PATTERN'
```

---

## 6. Setup and Configuration

### `run.py`

```python
"""Application entry point."""
from backend.app import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True
    )
```

### `backend/app.py`

```python
"""Flask application factory."""
from flask import Flask
from flask_cors import CORS
from backend.api.routes import api

def create_app(testing=False):
    app = Flask(__name__)
    
    # Configuration
    app.config['TESTING'] = testing
    
    # CORS (allow localhost)
    CORS(app, origins=['http://localhost:5000', 'http://127.0.0.1:5000'])
    
    # Register blueprints
    app.register_blueprint(api, url_prefix='/api')
    
    # Serve frontend
    @app.route('/')
    def index():
        return app.send_static_file('index.html')
    
    return app
```

### `requirements.txt`

```txt
flask==3.0.0
flask-cors==4.0.0
requests==2.31.0
pytest==7.4.0
pytest-cov==4.1.0
```

---

## Success Criteria

**MVP Complete When:**
- ✅ All three tools functional
- ✅ Unit tests >85% coverage
- ✅ Integration tests pass
- ✅ Mobile responsive
- ✅ Non-technical user can use without help
- ✅ README complete with setup instructions

**Performance:**
- Pattern search: <1s
- Numbering validation: <100ms
- Convention normalize: <50ms

**Quality:**
- No linting errors
- All tests pass
- Error handling comprehensive
- User-friendly error messages
