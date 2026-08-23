# Backend Specification - Theme Words & Strategic Black Squares

**Last Updated:** December 27, 2024
**Status:** Implementation Complete
**Version:** 1.0.0

---

## Table of Contents

1. [Overview](#overview)
2. [Theme Placement System](#theme-placement-system)
3. [Black Square Suggester](#black-square-suggester)
4. [Theme API Routes](#theme-api-routes)
5. [Grid API Routes](#grid-api-routes)
6. [Adaptive Mode Integration](#adaptive-mode-integration)
7. [Data Structures](#data-structures)
8. [Validation Rules](#validation-rules)
9. [Error Handling](#error-handling)
10. [Performance Targets](#performance-targets)

---

## Overview

The backend implements two major features:

1. **Theme Word Integration** - Upload and intelligently place custom theme words
2. **Strategic Black Square Placement** - Manual and automatic "cheater square" suggestions

### Architecture

```
Flask API Layer (routes)
    ↓
Core Algorithms (theme_placer, black_square_suggester)
    ↓
CLI Integration (adaptive_autofill via subprocess)
```

### File Inventory

**Core Algorithms:**
- `backend/core/theme_placer.py` (409 lines)
- `backend/core/black_square_suggester.py` (473 lines)

**API Routes:**
- `backend/api/theme_routes.py` (275 lines)
- `backend/api/grid_routes.py` (255 lines)
- `backend/api/routes.py` (modified: lines 432-435 for adaptive mode)

**Integration:**
- `backend/app.py` (modified: lines 14-15, 51-52 for blueprint registration)

---

## Theme Placement System

### Component: `backend/core/theme_placer.py`

**Purpose:** Suggest optimal placements for custom theme words in crossword grids.

**Key Classes:**

#### `ThemePlacementSuggestion`

Represents a single placement suggestion.

```python
@dataclass
class ThemePlacementSuggestion:
    word: str
    row: int
    col: int
    direction: str  # 'across' or 'down'
    score: int      # 0-100
    reasoning: str  # Human-readable explanation
    intersections: int
    spacing_from_others: int
```

#### `ThemePlacer`

Main algorithm class for generating placement suggestions.

**Constructor:**
```python
def __init__(self, grid_size: int = 15):
    self.grid_size = grid_size
    # Standard placement preferences
    self.center_row = grid_size // 2
    self.center_col = grid_size // 2
```

**Public Methods:**

##### 1. `validate_theme_words(words: List[str]) -> Dict`

Validates theme word list before processing.

**Validation Rules:**
- No word can be longer than `grid_size`
- All words must be alphabetic characters only
- No duplicate words
- Warns if >50% of words are "long" (>11 letters)

**Returns:**
```python
{
    "valid": bool,
    "errors": List[str],    # Blocking errors
    "warnings": List[str]   # Non-blocking warnings
}
```

**Example:**
```python
placer = ThemePlacer(grid_size=15)
result = placer.validate_theme_words(["PARTNERNAME", "ANNIVERSARY"])

# Returns:
{
    "valid": True,
    "errors": [],
    "warnings": ["PARTNERNAME: Long word (11 letters), may be hard to place"]
}
```

##### 2. `suggest_placements(theme_words, existing_grid=None, max_suggestions_per_word=3) -> List[Dict]`

Generates optimal placement suggestions for each theme word.

**Parameters:**
- `theme_words`: List[str] - Words to place
- `existing_grid`: Optional[List[List]] - Current grid state (dict or string format)
- `max_suggestions_per_word`: int - Max suggestions to return per word (default: 3)

**Returns:**
```python
[
    {
        "word": "PARTNERNAME",
        "length": 11,
        "suggestions": [
            {
                "row": 7,
                "col": 2,
                "direction": "across",
                "score": 95,
                "reasoning": "Centered placement (symmetric), Good horizontal position, 0 intersections"
            },
            {
                "row": 2,
                "col": 7,
                "direction": "down",
                "score": 85,
                "reasoning": "Vertical placement, Good spacing from other theme words"
            }
        ]
    },
    ...
]
```

**Algorithm Flow:**

```python
def suggest_placements(self, theme_words, existing_grid=None, max_suggestions_per_word=3):
    # 1. Sort words by length (longest first - harder to place)
    words_sorted = sorted(theme_words, key=len, reverse=True)

    # 2. Initialize grid if not provided
    if existing_grid is None:
        grid = self._create_empty_grid()
    else:
        grid = self._normalize_grid_format(existing_grid)

    # 3. Track already-placed theme words
    placed_words = []

    # 4. For each word, generate candidate placements
    all_suggestions = []
    for word in words_sorted:
        candidates = []

        # Try across placements
        for row in range(self.grid_size):
            for col in range(self.grid_size - len(word) + 1):
                if self._can_place_word(grid, word, row, col, 'across'):
                    score = self._score_placement(...)
                    if score > 0:
                        candidates.append(...)

        # Try down placements
        for row in range(self.grid_size - len(word) + 1):
            for col in range(self.grid_size):
                if self._can_place_word(grid, word, row, col, 'down'):
                    score = self._score_placement(...)
                    if score > 0:
                        candidates.append(...)

        # Sort by score and take top N
        candidates.sort(key=lambda x: x.score, reverse=True)
        all_suggestions.append({
            "word": word,
            "length": len(word),
            "suggestions": candidates[:max_suggestions_per_word]
        })

    return all_suggestions
```

### Scoring Algorithm

The placement scoring uses a **multi-factor weighted system** (0-100 scale):

```python
def _score_placement(self, placement: Dict, word: str, grid: List[List], placed_words: List) -> int:
    score = 50  # Base score

    row, col, direction, word_len = placement['row'], placement['col'], placement['direction'], len(word)

    # ============================================
    # FACTOR 1: Symmetry (30 points max)
    # ============================================
    # Prefer centered placements (symmetric aesthetic)
    if self._is_centered(row, col, word_len, direction):
        score += 30  # Perfect center
    elif self._is_symmetric_pair_possible(row, col, direction):
        score += 15  # Can create symmetric pair

    # ============================================
    # FACTOR 2: Intersections (20 points max)
    # ============================================
    # More intersections = better grid connectivity
    intersection_count = self._count_intersections(grid, row, col, word, direction)
    score += min(20, intersection_count * 10)  # Cap at 20

    # ============================================
    # FACTOR 3: Position Preference (20 points max)
    # ============================================
    # Prefer middle rows/cols (more visible, easier to connect)
    distance_from_center = abs(row - self.center_row) + abs(col - self.center_col)
    if distance_from_center <= 2:
        score += 20  # Very close to center
    elif distance_from_center <= 4:
        score += 10  # Reasonably centered

    # ============================================
    # FACTOR 4: Length Consideration (10 points max)
    # ============================================
    # Reward appropriate word lengths
    if 7 <= word_len <= 15:
        score += 10  # Ideal length for theme words
    elif word_len >= 15:
        score += 5   # Acceptable (spanners)

    # ============================================
    # FACTOR 5: Spacing from Other Theme Words (10 points max)
    # ============================================
    # Avoid clustering theme words too closely
    min_spacing = self._calculate_min_spacing_to_placed_words(row, col, direction, word_len, placed_words)
    if min_spacing >= 5:
        score += 10  # Good spacing
    elif min_spacing >= 3:
        score += 5   # Acceptable spacing
    elif min_spacing < 2:
        score -= 20  # Too close (penalty)

    # ============================================
    # FACTOR 6: Boundary Penalties
    # ============================================
    # Slight penalty for edge placements (harder to connect)
    if row == 0 or row == self.grid_size - 1:
        score -= 5
    if col == 0 or col == self.grid_size - 1:
        score -= 5

    return max(0, min(100, score))  # Clamp to 0-100
```

**Scoring Examples:**

| Placement | Symmetry | Intersections | Position | Length | Spacing | Boundaries | **Total** |
|-----------|----------|---------------|----------|--------|---------|------------|-----------|
| Center horizontal 11-letter | +30 | +0 (new grid) | +20 | +10 | +10 | -0 | **120→100** |
| Off-center vertical 7-letter intersecting | +0 | +20 (2 crosses) | +10 | +10 | +5 | -0 | **95** |
| Edge horizontal 15-letter | +15 (symmetric) | +10 (1 cross) | +0 (far) | +5 | +10 | -10 | **80** |
| Corner placement | +0 | +0 | +0 | +10 | -20 (too close) | -10 | **30** |

---

## Black Square Suggester

### Component: `backend/core/black_square_suggester.py`

**Purpose:** Suggest optimal black square positions ("cheater squares") to split problematic slots into more fillable segments.

**Key Classes:**

#### `BlackSquareSuggestion`

Represents a single black square placement suggestion.

```python
@dataclass
class BlackSquareSuggestion:
    position: int           # Position within slot (0-indexed from slot start)
    row: int               # Grid row coordinate
    col: int               # Grid column coordinate
    score: int             # 0-1000 score
    reasoning: str         # Human-readable explanation
    left_length: int       # Length of left segment after split
    right_length: int      # Length of right segment after split
    symmetric_position: Dict[str, int]  # {'row': int, 'col': int}
    new_word_count: int    # Total words after placement
    constraint_reduction: int  # 0-5 scale
```

#### `BlackSquareSuggester`

Main algorithm for black square suggestions.

**Constructor:**
```python
def __init__(self, grid_size: int = 15):
    self.grid_size = grid_size
    # Standard word count ranges for quality grids
    self.word_count_ranges = {
        11: (60, 68),
        13: (66, 74),
        15: (72, 78),
        17: (80, 88),
        21: (90, 100)
    }
```

**Public Methods:**

##### `suggest_placements(grid, problematic_slot, max_suggestions=3) -> List[Dict]`

Generates top N black square placement suggestions for a problematic slot.

**Parameters:**
- `grid`: List[List] - Current grid state (dict or string format)
- `problematic_slot`: Dict with keys:
  - `row`: int - Slot starting row
  - `col`: int - Slot starting column
  - `direction`: 'across' | 'down'
  - `length`: int - Slot length
  - `pattern`: str - Current pattern (e.g., "A??LE??RY")
  - `candidate_count`: int - Number of valid words (optional)
- `max_suggestions`: int - Number of suggestions to return (default: 3)

**Returns:**
```python
[
    {
        "position": 7,
        "row": 0,
        "col": 7,
        "score": 850,
        "reasoning": "Balanced split (7+7 letters), Both lengths in sweet spot (3-7), Word count 77 (within range), Maintains symmetry",
        "left_length": 7,
        "right_length": 7,
        "symmetric_position": {"row": 14, "col": 7},
        "new_word_count": 77,
        "constraint_reduction": 4
    },
    ...
]
```

**Algorithm:** Only suggests for slots with `length >= 6` (configurable via `min_slot_length`).

### Scoring Algorithm

The black square scoring uses a **6-factor weighted system** (0-1000 scale):

```python
def _score_position(self, grid: List[List], slot: Dict, position: int) -> int:
    score = 0

    # Calculate resulting segment lengths
    left_len = position
    right_len = slot['length'] - position - 1

    # ================================================
    # FACTOR 1: Length Balance (0-100 points)
    # ================================================
    # Prefer even splits (7+7 better than 10+4)
    balance = abs(left_len - right_len)
    balance_score = 100 - (balance * 10)
    score += max(0, balance_score)

    # ================================================
    # FACTOR 2: Ideal Length Range (0-100 points)
    # ================================================
    # Sweet spot: 3-7 letter words (easiest to fill)
    if 3 <= left_len <= 7:
        score += 50
    if 3 <= right_len <= 7:
        score += 50

    # CRITICAL REJECTION: Never create 1-2 letter words
    if left_len < 3 or right_len < 3:
        score -= 500  # Almost always reject

    # ================================================
    # FACTOR 3: Rotational Symmetry (0-200 points)
    # ================================================
    # MUST maintain rotational symmetry (crossword standard)
    symmetric_pos = self._get_symmetric_position(grid, slot, position)

    if self._can_place_symmetric_black(grid, symmetric_pos):
        score += 200  # Critical bonus
    else:
        score -= 1000  # REJECT - breaks symmetry

    # ================================================
    # FACTOR 4: Word Count (0-100 points)
    # ================================================
    # Stay within standard range for grid quality
    current_word_count = self._count_words(grid)
    new_word_count = current_word_count + 2  # Splitting adds net +2 words

    min_words, max_words = self.word_count_ranges.get(self.grid_size, (70, 80))

    if min_words <= new_word_count <= max_words:
        score += 100  # Perfect range
    elif new_word_count > max_words:
        score -= (new_word_count - max_words) * 20  # Penalty for too many words
    elif new_word_count < min_words:
        score += (min_words - new_word_count) * 10  # Bonus for adding needed words

    # ================================================
    # FACTOR 5: Constraint Reduction (0-200 points)
    # ================================================
    # Estimate how much this reduces constraint conflicts
    constraint_reduction = self._estimate_constraint_reduction(slot, position)
    score += constraint_reduction * 40  # constraint_reduction is 0-5

    # ================================================
    # FACTOR 6: Unchecked Squares (0-50 points penalty)
    # ================================================
    # Avoid creating unchecked squares (letters in only one word)
    unchecked_count = self._count_unchecked_created(grid, slot, position)
    score -= unchecked_count * 25

    return max(0, score)  # No negative scores
```

**Constraint Reduction Heuristic:**

```python
def _estimate_constraint_reduction(self, slot: Dict, position: int) -> int:
    """
    Estimate 0-5 how much this placement reduces constraints.

    Theory: Constraint count proportional to length²
    Splitting reduces total constraint load.
    """
    original_length = slot['length']
    left_len = position
    right_len = original_length - position - 1

    # Original constraints
    original_constraints = original_length ** 2

    # New constraints (sum of both segments)
    new_constraints = (left_len ** 2) + (right_len ** 2)

    # Reduction
    reduction = original_constraints - new_constraints

    # Normalize to 0-5 scale
    return min(5, reduction // 20)
```

**Example:**
- 15-letter slot split at position 7:
  - Original: 15² = 225 constraints
  - New: 7² + 7² = 49 + 49 = 98 constraints
  - Reduction: 225 - 98 = 127
  - Score: min(5, 127 // 20) = 5/5 (maximum reduction)

**Rotational Symmetry Calculation:**

```python
def _get_symmetric_position(self, grid: List[List], slot: Dict, position: int) -> Dict:
    """
    Calculate rotationally symmetric position (180° rotation).
    """
    row = slot['row']
    col = slot['col']
    direction = slot['direction']

    if direction == 'across':
        # Black square at (row, col + position)
        black_row = row
        black_col = col + position

        # Symmetric position (rotate 180°)
        sym_row = self.grid_size - 1 - black_row
        sym_col = self.grid_size - 1 - black_col
    else:  # down
        # Black square at (row + position, col)
        black_row = row + position
        black_col = col

        # Symmetric position
        sym_row = self.grid_size - 1 - black_row
        sym_col = self.grid_size - 1 - black_col

    return {'row': sym_row, 'col': sym_col}
```

**Word Count Validation:**

```python
def _count_words(self, grid: List[List]) -> int:
    """
    Count total valid words in grid (across + down).

    Valid word: 3+ consecutive non-black cells.
    """
    count = 0

    # Count across words
    for row in grid:
        word_len = 0
        for cell in row:
            if not self._is_black_cell(cell):
                word_len += 1
            else:
                if word_len >= 3:
                    count += 1
                word_len = 0
        if word_len >= 3:
            count += 1

    # Count down words (similar logic for columns)
    for col in range(len(grid[0])):
        word_len = 0
        for row in range(len(grid)):
            if not self._is_black_cell(grid[row][col]):
                word_len += 1
            else:
                if word_len >= 3:
                    count += 1
                word_len = 0
        if word_len >= 3:
            count += 1

    return count
```

---

## Theme API Routes

### Component: `backend/api/theme_routes.py`

Blueprint name: `theme_api`
URL prefix: `/api`

---

### Endpoint 1: Upload Theme Words

**POST** `/api/theme/upload`

Parses and validates theme words from file content.

**Request:**
```json
{
  "content": "PARTNERNAME\nANNIVERSARY\nFAVORITEPLACE",
  "grid_size": 15
}
```

**Response (Success):**
```json
{
  "words": ["PARTNERNAME", "ANNIVERSARY", "FAVORITEPLACE"],
  "count": 3,
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": [
      "PARTNERNAME: Long word (11 letters), may be hard to place"
    ]
  }
}
```

**Response (Error - Word Too Long):**
```json
{
  "words": [],
  "count": 0,
  "validation": {
    "valid": false,
    "errors": [
      "Word 'VERYLONGWORDEXAMPLE' (19 letters) exceeds grid size (15)"
    ],
    "warnings": []
  }
}
```

**Implementation:**
```python
@theme_api.route("/theme/upload", methods=["POST"])
def upload_theme_words():
    try:
        data = request.get_json()

        if not data or 'content' not in data:
            return jsonify({'error': 'Missing content'}), 400

        grid_size = data.get('grid_size', 15)

        # Parse words from content (split by newline)
        lines = data['content'].split('\n')
        words = [line.strip().upper() for line in lines if line.strip()]

        # Remove duplicates while preserving order
        seen = set()
        unique_words = []
        for word in words:
            if word not in seen and word.isalpha():
                seen.add(word)
                unique_words.append(word)

        # Validate words
        placer = ThemePlacer(grid_size)
        validation = placer.validate_theme_words(unique_words)

        return jsonify({
            'words': unique_words,
            'count': len(unique_words),
            'validation': validation
        }), 200

    except Exception as e:
        logger.error(f"Error uploading theme words: {e}", exc_info=True)
        return handle_error(e, default_status=500)
```

---

### Endpoint 2: Suggest Placements

**POST** `/api/theme/suggest-placements`

Generates optimal placement suggestions for theme words.

**Request:**
```json
{
  "theme_words": ["PARTNERNAME", "ANNIVERSARY"],
  "grid_size": 15,
  "existing_grid": [[...], ...],  // Optional
  "max_suggestions": 3
}
```

**Response:**
```json
{
  "suggestions": [
    {
      "word": "PARTNERNAME",
      "length": 11,
      "suggestions": [
        {
          "row": 7,
          "col": 2,
          "direction": "across",
          "score": 95,
          "reasoning": "Centered placement (symmetric), Good horizontal position, 0 intersections"
        },
        {
          "row": 2,
          "col": 7,
          "direction": "down",
          "score": 85,
          "reasoning": "Vertical placement, Good spacing from other theme words"
        }
      ]
    },
    {
      "word": "ANNIVERSARY",
      "length": 11,
      "suggestions": [
        {
          "row": 7,
          "col": 2,
          "direction": "down",
          "score": 90,
          "reasoning": "Intersects with PARTNERNAME, Centered, 1 intersection"
        }
      ]
    }
  ],
  "grid_size": 15
}
```

**Error Response (Invalid Words):**
```json
{
  "error": "Invalid theme words",
  "validation": {
    "valid": false,
    "errors": ["Word 'TOOLONGWORD' exceeds grid size"],
    "warnings": []
  }
}
```
Status: `400 Bad Request`

**Implementation:**
```python
@theme_api.route("/theme/suggest-placements", methods=["POST"])
def suggest_placements():
    try:
        data = request.get_json()

        if not data or 'theme_words' not in data:
            return jsonify({'error': 'Missing theme_words'}), 400

        theme_words = data['theme_words']
        grid_size = data.get('grid_size', 15)
        existing_grid = data.get('existing_grid')
        max_suggestions = data.get('max_suggestions', 3)

        # Validate input
        if not isinstance(theme_words, list):
            return jsonify({'error': 'theme_words must be a list'}), 400

        if not theme_words:
            return jsonify({'error': 'theme_words cannot be empty'}), 400

        # Create placer and validate
        placer = ThemePlacer(grid_size)
        validation = placer.validate_theme_words(theme_words)

        if not validation['valid']:
            return jsonify({
                'error': 'Invalid theme words',
                'validation': validation
            }), 400

        # Generate suggestions
        suggestions = placer.suggest_placements(
            theme_words,
            existing_grid=existing_grid,
            max_suggestions_per_word=max_suggestions
        )

        return jsonify({
            'suggestions': suggestions,
            'grid_size': grid_size
        }), 200

    except Exception as e:
        logger.error(f"Error suggesting placements: {e}", exc_info=True)
        return handle_error(e, default_status=500)
```

---

### Endpoint 3: Validate Theme Words

**POST** `/api/theme/validate`

Validates theme words without generating placements (faster).

**Request:**
```json
{
  "theme_words": ["PARTNERNAME", "ANNIVERSARY"],
  "grid_size": 15
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    "PARTNERNAME: Long word (11 letters), may be hard to place",
    "ANNIVERSARY: Long word (11 letters), may be hard to place"
  ]
}
```

---

### Endpoint 4: Apply Placement

**POST** `/api/theme/apply-placement`

Applies a theme word placement to the grid and marks cells as theme-locked.

**Request:**
```json
{
  "grid": [[...], ...],
  "placement": {
    "word": "PARTNERNAME",
    "row": 7,
    "col": 2,
    "direction": "across"
  }
}
```

**Response:**
```json
{
  "grid": [[...], ...],  // Updated grid with isThemeLocked: true
  "applied": true
}
```

**Grid Cell Modification:**
```javascript
// Before:
{letter: '', isBlack: false, isThemeLocked: false}

// After:
{letter: 'P', isBlack: false, isThemeLocked: true}
{letter: 'A', isBlack: false, isThemeLocked: true}
// ... (entire word marked as theme-locked)
```

**Implementation:**
```python
@theme_api.route("/theme/apply-placement", methods=["POST"])
def apply_placement():
    try:
        data = request.get_json()

        if not data or 'grid' not in data or 'placement' not in data:
            return jsonify({'error': 'Missing grid or placement'}), 400

        grid = data['grid']
        placement = data['placement']

        # Validate placement
        required_fields = ['word', 'row', 'col', 'direction']
        if not all(field in placement for field in required_fields):
            return jsonify({'error': 'Incomplete placement data'}), 400

        word = placement['word'].upper()
        row = placement['row']
        col = placement['col']
        direction = placement['direction']

        # Apply word to grid
        for i, letter in enumerate(word):
            if direction == 'across':
                target_col = col + i
                if target_col >= len(grid[row]):
                    continue  # Skip if out of bounds

                cell = grid[row][target_col]
                if isinstance(cell, dict):
                    cell['letter'] = letter
                    cell['isThemeLocked'] = True
                else:
                    grid[row][target_col] = letter

            else:  # down
                target_row = row + i
                if target_row >= len(grid):
                    continue

                cell = grid[target_row][col]
                if isinstance(cell, dict):
                    cell['letter'] = letter
                    cell['isThemeLocked'] = True
                else:
                    grid[target_row][col] = letter

        return jsonify({
            'grid': grid,
            'applied': True
        }), 200

    except Exception as e:
        logger.error(f"Error applying placement: {e}", exc_info=True)
        return handle_error(e, default_status=500)
```

---

## Grid API Routes

### Component: `backend/api/grid_routes.py`

Blueprint name: `grid_api`
URL prefix: `/api`

---

### Endpoint 1: Suggest Black Square

**POST** `/api/grid/suggest-black-square`

Suggests strategic black square placements for a problematic slot.

**Request:**
```json
{
  "grid": [[...], ...],
  "grid_size": 15,
  "problematic_slot": {
    "row": 0,
    "col": 0,
    "direction": "across",
    "length": 15,
    "pattern": "???????????????",
    "candidate_count": 0
  },
  "max_suggestions": 3
}
```

**Response:**
```json
{
  "suggestions": [
    {
      "position": 7,
      "row": 0,
      "col": 7,
      "score": 850,
      "reasoning": "Balanced split (7+7 letters), Both lengths in sweet spot (3-7), Word count 77 (within range), Maintains symmetry",
      "left_length": 7,
      "right_length": 7,
      "symmetric_position": {"row": 14, "col": 7},
      "new_word_count": 77,
      "constraint_reduction": 4
    },
    {
      "position": 6,
      "row": 0,
      "col": 6,
      "score": 820,
      "reasoning": "Split into 6+8 letters, Both lengths in sweet spot (3-7), Word count 77 (within range), Maintains symmetry",
      "left_length": 6,
      "right_length": 8,
      "symmetric_position": {"row": 14, "col": 8},
      "new_word_count": 77,
      "constraint_reduction": 4
    }
  ],
  "slot_info": {
    "row": 0,
    "col": 0,
    "direction": "across",
    "length": 15,
    "pattern": "???????????????"
  },
  "grid_size": 15,
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": []
  }
}
```

**Response (No Suggestions):**
```json
{
  "suggestions": [],
  "message": "No viable black square positions found for this slot",
  "slot_info": {...}
}
```
Status: `200 OK` (not an error - just no suggestions)

**Implementation:**
```python
@grid_api.route("/grid/suggest-black-square", methods=["POST"])
def suggest_black_square():
    try:
        data = request.get_json()

        # Validate input
        if not data:
            return jsonify({'error': 'Missing request body'}), 400

        if 'grid' not in data:
            return jsonify({'error': 'Missing grid'}), 400

        if 'problematic_slot' not in data:
            return jsonify({'error': 'Missing problematic_slot'}), 400

        grid = data['grid']
        grid_size = data.get('grid_size', 15)
        slot = data['problematic_slot']
        max_suggestions = data.get('max_suggestions', 3)

        # Validate slot
        required_slot_fields = ['row', 'col', 'direction', 'length']
        if not all(field in slot for field in required_slot_fields):
            return jsonify({'error': 'Incomplete slot data'}), 400

        # Validate grid
        validation = validate_grid_for_black_squares(grid, grid_size)
        if not validation['valid']:
            return jsonify({
                'error': 'Invalid grid',
                'validation': validation
            }), 400

        # Create suggester and generate suggestions
        suggester = BlackSquareSuggester(grid_size)
        suggestions = suggester.suggest_placements(
            grid,
            slot,
            max_suggestions=max_suggestions
        )

        # Check if any suggestions found
        if not suggestions:
            return jsonify({
                'suggestions': [],
                'message': 'No viable black square positions found for this slot',
                'slot_info': slot
            }), 200

        return jsonify({
            'suggestions': suggestions,
            'slot_info': slot,
            'grid_size': grid_size,
            'validation': validation
        }), 200

    except Exception as e:
        logger.error(f"Error suggesting black square: {e}", exc_info=True)
        return handle_error(e, default_status=500)
```

---

### Endpoint 2: Apply Black Squares

**POST** `/api/grid/apply-black-squares`

Applies a symmetric black square pair to the grid.

**Request:**
```json
{
  "grid": [[...], ...],
  "primary": {"row": 0, "col": 7},
  "symmetric": {"row": 14, "col": 7}
}
```

**Response:**
```json
{
  "grid": [[...], ...],  // Updated grid with isBlack: true
  "applied": true,
  "positions": [
    {"row": 0, "col": 7},
    {"row": 14, "col": 7}
  ]
}
```

**Grid Cell Modification:**
```javascript
// Before:
{letter: 'A', isBlack: false, isThemeLocked: false}

// After (both positions):
{letter: '', isBlack: true, isThemeLocked: false}
```

**Implementation:**
```python
@grid_api.route("/grid/apply-black-squares", methods=["POST"])
def apply_black_squares():
    try:
        data = request.get_json()

        if not data or 'grid' not in data or 'primary' not in data or 'symmetric' not in data:
            return jsonify({'error': 'Missing grid or positions'}), 400

        grid = data['grid']
        primary = data['primary']
        symmetric = data['symmetric']

        # Apply black squares
        positions = [primary, symmetric]

        for pos in positions:
            row = pos['row']
            col = pos['col']

            if not (0 <= row < len(grid) and 0 <= col < len(grid[row])):
                continue  # Skip invalid positions

            cell = grid[row][col]
            if isinstance(cell, dict):
                cell['isBlack'] = True
                cell['letter'] = ''
                cell['isThemeLocked'] = False
            else:
                grid[row][col] = '#'

        return jsonify({
            'grid': grid,
            'applied': True,
            'positions': positions
        }), 200

    except Exception as e:
        logger.error(f"Error applying black squares: {e}", exc_info=True)
        return handle_error(e, default_status=500)
```

---

### Endpoint 3: Validate Grid

**POST** `/api/grid/validate`

Validates grid quality and provides statistics.

**Request:**
```json
{
  "grid": [[...], ...],
  "grid_size": 15
}
```

**Response:**
```json
{
  "valid": true,
  "word_count": 76,
  "black_square_count": 38,
  "black_square_percentage": 16.8,
  "word_count_range": [72, 78],
  "warnings": [],
  "suggestions": []
}
```

**Response (Quality Issues):**
```json
{
  "valid": true,
  "word_count": 85,
  "black_square_count": 25,
  "black_square_percentage": 11.1,
  "word_count_range": [72, 78],
  "warnings": [],
  "suggestions": [
    "High word count (85). Try adding black squares to reach 72-78.",
    "Low black square percentage (11.1%). Standard is ~16-18%."
  ]
}
```

---

## Adaptive Mode Integration

### Component: `backend/api/routes.py` (Modified)

Added adaptive mode support to the `/api/fill/with-progress` endpoint.

**Modified Lines: 432-435**

```python
# Add adaptive mode flag if enabled (auto black square placement)
if data.get("adaptive_mode", False):
    cmd_args.append("--adaptive")
    if "max_adaptations" in data:
        cmd_args.extend(["--max-adaptations", str(data["max_adaptations"])])
```

**Request Schema (New Fields):**
```json
{
  "grid": [[...], ...],
  "size": 15,
  "wordlists": ["comprehensive"],
  "timeout": 300,
  "min_score": 50,
  "algorithm": "beam",
  "theme_entries": {},
  "adaptive_mode": true,        // NEW
  "max_adaptations": 3          // NEW
}
```

**Progress Updates (Adaptive Events):**

When adaptive mode is enabled, the SSE stream includes adaptation events:

```json
{
  "status": "running",
  "progress": 45,
  "message": "Adaptation #2: Added black square at (7, 5) - Balanced split (6+6 letters)...",
  "data": {
    "adaptation": {
      "count": 2,
      "position": [7, 5],
      "reasoning": "Balanced split (6+6 letters), Both lengths in sweet spot (3-7), Word count 75 (within range)"
    }
  }
}
```

**Final Result (With Adaptations):**

```json
{
  "status": "complete",
  "progress": 100,
  "message": "Success with 2 adaptive black square(s)",
  "data": {
    "success": true,
    "grid": [[...], ...],  // Includes adapted black squares
    "slots_filled": 76,
    "total_slots": 76,
    "adaptations_applied": 2
  }
}
```

---

## Data Structures

### Grid Cell Format (Frontend/Backend)

**Dictionary Format:**
```python
{
    "letter": str,           # 'A'-'Z' or ''
    "isBlack": bool,         # True for black squares
    "number": int | None,    # Clue number (1, 2, 3, ...)
    "isError": bool,         # Validation error indicator
    "isHighlighted": bool,   # UI highlight state
    "isThemeLocked": bool    # NEW: Prevents autofill modification
}
```

**String Format (CLI):**
```python
'A'    # Letter
'#'    # Black square
'.'    # Empty cell
```

### Theme Entry Format (CLI)

**JSON File Format:**
```json
{
  "(row,col,direction)": "WORD",
  "(0,0,across)": "PARTNERNAME",
  "(7,5,down)": "ANNIVERSARY"
}
```

**Python Format (After Parsing):**
```python
{
    (0, 0, 'across'): "PARTNERNAME",
    (7, 5, 'down'): "ANNIVERSARY"
}
```

### Slot Format

```python
{
    "row": int,               # Starting row
    "col": int,               # Starting column
    "direction": str,         # 'across' or 'down'
    "length": int,            # Slot length
    "pattern": str,           # e.g., "A??LE" (? = empty)
    "candidate_count": int    # Number of valid words (optional)
}
```

---

## Validation Rules

### Theme Word Validation

1. **Length Check**: No word can exceed `grid_size`
2. **Character Check**: Only alphabetic characters (A-Z, a-z)
3. **Duplicate Check**: No duplicate words in list
4. **Quality Warning**: Warn if >50% of words are "long" (>11 letters)

### Grid Validation (Black Squares)

1. **Size Check**: Grid dimensions match `grid_size`
2. **Symmetry Enforcement**: All black square suggestions maintain rotational symmetry
3. **Word Count Check**: Warn if black square count > 16% of total cells
4. **Minimum Word Length**: Never suggest placements creating <3 letter words

### Placement Validation

1. **Bounds Check**: All positions within grid bounds
2. **Conflict Check**: No overwriting theme-locked cells
3. **Symmetry Check**: Symmetric position must be valid for black squares
4. **Word Count Limits**: Stay within standard ranges (e.g., 72-78 for 15×15)

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Suggestions generated |
| 400 | Bad Request | Missing required field, invalid data |
| 404 | Not Found | State file not found (pause/resume) |
| 500 | Internal Server Error | Unexpected backend exception |

### Error Response Format

```json
{
  "error": "Error message",
  "details": "Optional detailed explanation",
  "validation": {  // Optional
    "valid": false,
    "errors": ["Specific error 1", "Specific error 2"]
  }
}
```

### Common Errors

**1. Missing Required Field:**
```json
{
  "error": "Missing theme_words"
}
```
Status: `400 Bad Request`

**2. Invalid Theme Words:**
```json
{
  "error": "Invalid theme words",
  "validation": {
    "valid": false,
    "errors": ["Word 'TOOLONGWORD' (15 letters) exceeds grid size (11)"],
    "warnings": []
  }
}
```
Status: `400 Bad Request`

**3. Invalid Grid:**
```json
{
  "error": "Invalid grid",
  "validation": {
    "valid": false,
    "errors": ["Grid size mismatch: expected 15×15, got 14×15"],
    "warnings": []
  }
}
```
Status: `400 Bad Request`

**4. Server Error:**
```json
{
  "error": "Internal server error",
  "details": "Failed to generate suggestions: <exception details>"
}
```
Status: `500 Internal Server Error`

---

## Performance Targets

### Theme Word Operations

| Operation | Target | Actual (Typical) |
|-----------|--------|------------------|
| Upload & Parse (50 words) | <100ms | ~30ms |
| Validation | <50ms | ~10ms |
| Placement Suggestion (1 word) | <500ms | ~200ms |
| Placement Suggestion (10 words) | <3s | ~1.5s |
| Apply Placement | <50ms | ~20ms |

### Black Square Operations

| Operation | Target | Actual (Typical) |
|-----------|--------|------------------|
| Slot Analysis | <100ms | ~40ms |
| Scoring (3 positions) | <200ms | ~80ms |
| Total Suggestion Time | <500ms | ~150ms |
| Apply Black Squares | <50ms | ~15ms |
| Grid Validation | <100ms | ~30ms |

### Adaptive Autofill

| Metric | Target | Impact |
|--------|--------|--------|
| Detection Overhead | <0.1% | Negligible |
| Per-Adaptation Time | <1s | Acceptable |
| Max Adaptations (default) | 3 | Configurable 1-5 |
| Total Adaptation Overhead | <5s | ~3-5s for full session |

---

## Testing Checklist

### Unit Tests (Required)

**Theme Placement:**
- [ ] Validate theme words (valid input)
- [ ] Validate theme words (word too long)
- [ ] Validate theme words (non-alphabetic)
- [ ] Validate theme words (duplicates)
- [ ] Generate placements (empty grid)
- [ ] Generate placements (existing grid with conflicts)
- [ ] Score placement (centered)
- [ ] Score placement (edge)
- [ ] Score placement (with intersections)

**Black Square Suggester:**
- [ ] Suggest placements (15-letter slot)
- [ ] Suggest placements (6-letter slot minimum)
- [ ] Suggest placements (3-letter slot - should reject)
- [ ] Score position (balanced split)
- [ ] Score position (unbalanced split)
- [ ] Score position (breaks symmetry - should reject)
- [ ] Calculate symmetric position (across)
- [ ] Calculate symmetric position (down)
- [ ] Count words (empty grid)
- [ ] Count words (filled grid)

**API Routes:**
- [ ] POST /api/theme/upload (success)
- [ ] POST /api/theme/upload (invalid word)
- [ ] POST /api/theme/suggest-placements (success)
- [ ] POST /api/theme/suggest-placements (invalid words)
- [ ] POST /api/theme/apply-placement (success)
- [ ] POST /api/grid/suggest-black-square (success)
- [ ] POST /api/grid/suggest-black-square (no suggestions)
- [ ] POST /api/grid/apply-black-squares (success)
- [ ] POST /api/grid/validate (success)

### Integration Tests (Required)

- [ ] Upload theme words → Suggest placements → Apply placement (end-to-end)
- [ ] Find problematic slot → Suggest black square → Apply black squares (end-to-end)
- [ ] Adaptive autofill with theme words
- [ ] Adaptive autofill with stuck detection
- [ ] Multiple adaptations in single session

---

**END OF BACKEND SPECIFICATION**

**Last Updated:** December 27, 2024
**Version:** 1.0.0
**Status:** Implementation Complete, Ready for Testing
