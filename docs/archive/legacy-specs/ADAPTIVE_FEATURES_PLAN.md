# Adaptive Features Implementation Plan

**Created:** December 27, 2025
**Features:** Theme Word Integration + Strategic Black Square Placement

---

## Overview

Two powerful features to improve crossword construction workflow:

1. **Better Theme Word Integration** - Easy import and placement of personalized theme words
2. **Strategic Black Square Placement** - Intelligent "cheater squares" to resolve stuck fills

---

## FEATURE 1: Enhanced Theme Word Integration

### User Problem
- Has list of theme words for partner (names, dates, inside jokes)
- Current workflow requires manual placement and individual cell locking
- No validation if theme words will work together
- No smart placement suggestions

### Solution: Quick Theme Entry Workflow

#### UI Component: "Theme Words Panel"

```jsx
<ThemeWordsPanel>
  <textarea
    placeholder="Paste theme words (one per line)
PARTNERNAME
ANNIVERSARY
FAVORITEPLACE"
    rows={10}
  />

  <button onClick={handleAnalyzeThemeWords}>
    🎯 Analyze & Place Theme Words
  </button>

  {suggestions && (
    <ThemePlacementSuggestions>
      {suggestions.map(s => (
        <Suggestion>
          <Word>{s.word}</Word>
          <Placement>
            {s.placement.row}, {s.placement.col} {s.placement.direction}
          </Placement>
          <Score>Fit Score: {s.score}/100</Score>
          <button onClick={() => applyPlacement(s)}>✓ Use This</button>
        </Suggestion>
      ))}
    </ThemePlacementSuggestions>
  )}
</ThemeWordsPanel>
```

#### Backend: Theme Placement Suggester

**Endpoint:** `POST /api/grid/suggest-theme-placements`

**Input:**
```json
{
  "grid_size": 15,
  "theme_words": ["PARTNERNAME", "ANNIVERSARY", "FAVORITEPLACE"],
  "existing_grid": [[...], ...]  // Optional
}
```

**Algorithm:**
```python
def suggest_theme_placements(grid_size, theme_words, existing_grid=None):
    """
    Suggest optimal placements for theme words.

    Strategy:
    1. Sort words by length (longest first)
    2. Place longest word centered, horizontally
    3. Place second word intersecting vertically
    4. Place remaining words with maximum spacing
    5. Ensure rotational symmetry
    """

    suggestions = []

    # Sort by length
    words_sorted = sorted(theme_words, key=len, reverse=True)

    for word in words_sorted:
        # Find valid placements
        placements = []

        # Try horizontal centered (for long words)
        if len(word) >= grid_size * 0.6:  # 60% of grid width
            row = grid_size // 2
            col = (grid_size - len(word)) // 2
            placements.append({
                'row': row,
                'col': col,
                'direction': 'across',
                'score': 100  # High score for centered symmetric placement
            })

        # Try all other positions
        for row in range(grid_size):
            for col in range(grid_size):
                for direction in ['across', 'down']:
                    if fits_in_grid(word, row, col, direction, grid_size):
                        score = score_placement(word, row, col, direction, existing_grid)
                        if score > 50:  # Only suggest good fits
                            placements.append({
                                'row': row,
                                'col': col,
                                'direction': direction,
                                'score': score
                            })

        # Return top 3 placements
        placements.sort(key=lambda x: x['score'], reverse=True)
        suggestions.append({
            'word': word,
            'placements': placements[:3]
        })

    return suggestions

def score_placement(word, row, col, direction, existing_grid):
    """Score a theme word placement."""
    score = 50  # Base score

    # Bonus for symmetry
    if is_centered(row, col, len(word), direction, grid_size):
        score += 30

    # Bonus for intersections with other theme words
    intersections = count_intersections(word, row, col, direction, existing_grid)
    score += intersections * 10

    # Penalty for conflicts
    conflicts = count_conflicts(word, row, col, direction, existing_grid)
    score -= conflicts * 50

    # Bonus for length variety
    if 7 <= len(word) <= 15:
        score += 20

    return max(0, min(100, score))
```

#### Implementation Steps

**Step 1: UI Component (2 hours)**
- [ ] Create `ThemeWordsPanel.jsx` component
- [ ] Add textarea for word list input
- [ ] Add "Analyze" button
- [ ] Display placement suggestions with scores
- [ ] Add "Apply" buttons for each suggestion

**Step 2: Backend Endpoint (3 hours)**
- [ ] Create `/api/grid/suggest-theme-placements` endpoint
- [ ] Implement placement algorithm
- [ ] Add validation (word lengths, conflicts)
- [ ] Return top 3 suggestions per word

**Step 3: Integration (2 hours)**
- [ ] Connect UI to backend endpoint
- [ ] Apply placements to grid state
- [ ] Auto-lock applied theme words
- [ ] Update visual indicators (purple background)

**Total: ~7 hours (1 day)**

---

## FEATURE 2: Strategic Black Square Placement

### User Problem
- Autofill gets stuck with unsolvable slots
- Endless backtracking wastes time
- No way to adaptively modify grid to resolve conflicts

### Solution: Intelligent "Cheater Squares"

#### When to Use

**Trigger Conditions:**
1. **Manual:** User clicks "💡 Suggest Black Square" button
2. **Auto:** Autofill detects zero candidates for a slot
3. **Auto:** Backtracking exceeds 100 attempts on same slot
4. **Auto:** Beam search stalls for >50 iterations

#### Where to Place (Scoring Algorithm)

**Heuristic Score Factors:**

```python
def score_black_square_position(grid, slot, position):
    """
    Score a candidate black square position.

    Args:
        grid: Current grid state
        slot: Problematic slot dict {row, col, direction, length}
        position: Position within slot (0 to length-1)

    Returns:
        score: 0-1000 (higher is better)
    """

    score = 0

    # Calculate resulting word lengths
    left_len = position
    right_len = slot['length'] - position - 1

    # ========================================
    # FACTOR 1: Length Balance (0-100 points)
    # ========================================
    # Prefer balanced splits (7+8 better than 3+12)
    balance = abs(left_len - right_len)
    balance_score = 100 - (balance * 10)
    score += max(0, balance_score)

    # ========================================
    # FACTOR 2: Ideal Length Range (0-100 points)
    # ========================================
    # Crossword sweet spot: 3-7 letters
    if 3 <= left_len <= 7:
        score += 50
    if 3 <= right_len <= 7:
        score += 50

    # Strong penalty for 1-2 letter words
    if left_len < 3 or right_len < 3:
        score -= 500  # Almost always reject

    # ========================================
    # FACTOR 3: Symmetry Maintenance (0-200 points)
    # ========================================
    # CRITICAL: Must maintain rotational symmetry
    symmetric_pos = get_symmetric_position(grid, slot, position)

    if can_place_symmetric_black(grid, symmetric_pos):
        score += 200  # Big bonus
    else:
        score -= 1000  # Reject if breaks symmetry

    # ========================================
    # FACTOR 4: Word Count Impact (0-100 points)
    # ========================================
    # Standard 15×15: 72-78 words total
    current_word_count = count_words(grid)
    new_word_count = current_word_count + 2  # Split adds 1 word

    if 72 <= new_word_count <= 78:
        score += 100  # Within standard range
    elif new_word_count > 78:
        score -= (new_word_count - 78) * 20  # Penalty for excess
    elif new_word_count < 72:
        score += (72 - new_word_count) * 10  # Bonus for approaching target

    # ========================================
    # FACTOR 5: Constraint Reduction (0-200 points)
    # ========================================
    # How much does this reduce crossing constraints?
    constraint_reduction = calculate_constraint_reduction(grid, slot, position)
    score += constraint_reduction * 40

    # ========================================
    # FACTOR 6: Unchecked Squares (0-50 points)
    # ========================================
    # Prefer positions that don't create unchecked squares
    unchecked_penalty = count_unchecked_squares_created(grid, slot, position)
    score -= unchecked_penalty * 25

    return max(0, score)
```

#### Implementation: Manual Mode (Phase 1)

**UI Component:**

```jsx
// In AutofillPanel.jsx
{progress?.status === 'error' && (
  <div className="stuck-helper">
    <p>Autofill stuck! Try adding a strategic black square:</p>
    <button
      className="suggest-btn"
      onClick={handleSuggestBlackSquare}
    >
      💡 Suggest Black Square Placement
    </button>
  </div>
)}

// Show suggestions
{blackSquareSuggestions && (
  <div className="black-square-suggestions">
    <h4>Suggested Placements:</h4>
    {blackSquareSuggestions.map((s, i) => (
      <div key={i} className="suggestion">
        <div className="info">
          <strong>Option {i + 1}</strong>
          <span>Score: {s.score}/1000</span>
          <p>{s.reasoning}</p>
          <small>
            Split {s.original_length} letters →
            {s.left_length} + {s.right_length} letters
          </small>
        </div>
        <button onClick={() => applyBlackSquare(s)}>
          ✓ Apply This
        </button>
      </div>
    ))}
  </div>
)}
```

**Backend Endpoint:**

```python
@api.route("/grid/suggest-black-square", methods=["POST"])
def suggest_black_square():
    """
    POST /api/grid/suggest-black-square

    Suggests strategic black square placements to resolve stuck fills.

    Input:
    {
        "grid": [[...], ...],
        "problematic_slot": {
            "row": 0,
            "col": 0,
            "direction": "across",
            "length": 15,
            "pattern": "???????????????",
            "candidate_count": 0
        }
    }

    Output:
    {
        "suggestions": [
            {
                "position": 7,
                "score": 850,
                "reasoning": "Balanced 7+7 split, maintains symmetry",
                "left_length": 7,
                "right_length": 7,
                "symmetric_position": {"row": 14, "col": 7},
                "new_word_count": 77,
                "constraint_reduction": 45
            }
        ]
    }
    """

    data = request.json

    grid = data['grid']
    slot = data['problematic_slot']

    # Generate all candidate positions
    candidates = []

    for pos in range(1, slot['length'] - 1):  # Don't place at ends
        score = score_black_square_position(grid, slot, pos)

        if score > 0:  # Only include viable options
            candidates.append({
                'position': pos,
                'score': score,
                'reasoning': generate_reasoning(grid, slot, pos, score),
                'left_length': pos,
                'right_length': slot['length'] - pos - 1,
                'symmetric_position': get_symmetric_position(grid, slot, pos),
                'new_word_count': count_words(grid) + 2,
                'constraint_reduction': calculate_constraint_reduction(grid, slot, pos)
            })

    # Sort by score
    candidates.sort(key=lambda x: x['score'], reverse=True)

    # Return top 3
    return jsonify({
        'suggestions': candidates[:3],
        'slot_info': slot
    }), 200
```

#### Implementation: Auto Mode (Phase 2)

**Adaptive Autofill Class:**

```python
class AdaptiveAutofill:
    """
    Autofill engine with adaptive black square placement.

    Automatically adds "cheater squares" when stuck.
    """

    def __init__(self, grid, word_list, max_cheaters=4, auto_adapt=True):
        self.grid = grid
        self.word_list = word_list
        self.max_cheaters = max_cheaters
        self.auto_adapt = auto_adapt
        self.cheater_count = 0
        self.autofill = Autofill(grid, word_list)

    def fill_with_adaptation(self):
        """
        Fill grid with automatic adaptation.

        Returns:
            FillResult with adaptation metadata
        """

        attempt = 0
        max_attempts = self.max_cheaters + 1

        while attempt < max_attempts:
            # Try standard autofill
            result = self.autofill.fill()

            # Success!
            if result.success:
                result.cheater_squares_used = self.cheater_count
                return result

            # Check if we can adapt
            if not self.auto_adapt or self.cheater_count >= self.max_cheaters:
                return result  # Give up

            # Find problematic slot
            if not result.problematic_slots:
                return result  # No clear problem to fix

            problem_slot = result.problematic_slots[0]

            # Suggest black square
            suggestion = self.suggest_best_black_square(problem_slot)

            if suggestion and suggestion['score'] > 300:  # Only use good suggestions
                # Apply black square
                self.apply_black_square(suggestion)
                self.cheater_count += 1

                # Log for transparency
                logger.info(
                    f"🔲 Adaptive: Added cheater square #{self.cheater_count} "
                    f"at position {suggestion['position']} "
                    f"(score: {suggestion['score']})"
                )

                # Retry autofill
                attempt += 1
                continue

            # Can't find good adaptation
            return result

        # Exhausted all attempts
        return result

    def apply_black_square(self, suggestion):
        """Apply suggested black square to grid (symmetric)."""

        # Place primary black square
        self.grid.set_black(
            suggestion['row'],
            suggestion['col']
        )

        # Place symmetric black square
        sym = suggestion['symmetric_position']
        self.grid.set_black(
            sym['row'],
            sym['col']
        )

        # Reinitialize autofill with updated grid
        self.autofill = Autofill(self.grid, self.word_list)
```

#### Implementation Steps

**Phase 1: Manual Mode (4-6 hours)**
- [ ] Implement `score_black_square_position()` algorithm
- [ ] Create `/api/grid/suggest-black-square` endpoint
- [ ] Add "💡 Suggest Black Square" button to UI
- [ ] Display suggestions with reasoning
- [ ] Apply selected placement to grid

**Phase 2: Auto Mode (1-2 days)**
- [ ] Create `AdaptiveAutofill` class
- [ ] Integrate with existing autofill engines
- [ ] Add configuration option (max_cheaters)
- [ ] Add progress reporting for adaptations
- [ ] Test on difficult grids

---

## Implementation Priority

### Week 1: Quick Wins (High Value, Low Effort)

**Day 1-2: Theme Word Entry**
- ✅ High value for user (partner-themed puzzles)
- ✅ Moderate complexity (7 hours)
- ✅ Builds on existing theme infrastructure

**Day 3: Manual Black Square Suggester**
- ✅ Immediate utility when stuck
- ✅ Moderate complexity (4-6 hours)
- ✅ Foundation for auto mode

### Week 2: Advanced Features

**Day 4-5: Auto Black Square Placement**
- Adaptive autofill with automatic cheater squares
- Requires Phase 1 testing and refinement
- Higher complexity (1-2 days)

---

## Testing Strategy

### Theme Words
- [ ] Single theme word placement
- [ ] Multiple theme words with intersections
- [ ] Theme words with existing grid
- [ ] Invalid theme words (too long for grid)
- [ ] Conflicting theme words

### Black Squares
- [ ] Manual suggestion for stuck slot
- [ ] Score calculation accuracy
- [ ] Symmetry maintenance
- [ ] Word count constraints
- [ ] Auto mode with max_cheaters limit

---

## Success Metrics

**Theme Integration:**
- User can import 5+ theme words in <1 minute
- 90%+ placement suggestions are usable
- Theme words preserved through fill process

**Black Square Placement:**
- 80%+ of stuck fills resolved with 1-2 cheater squares
- Symmetry maintained in 100% of placements
- Word count stays within 72-78 range for 15×15

---

## Future Enhancements

1. **Theme Word Bank** - Save favorite theme word lists
2. **Smart Grid Designer** - Generate grid pattern from theme words
3. **Multi-objective Optimization** - Balance multiple criteria (word count, symmetry, theme density)
4. **Undo/Redo for Adaptations** - Try different black square placements
5. **Visualization** - Heatmap of constraint density to guide placements

---

**Next Steps:** Start with Theme Word Entry (highest user value, fastest to implement)
