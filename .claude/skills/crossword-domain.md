# Crossword Domain Knowledge

Progressive disclosure skill for crossword construction rules and conventions.

## Grid Standards (NYT)

### Symmetry
- **180° rotational symmetry required**
- Grid looks same when rotated upside down
- Black squares mirror across center

### Constraints
- All white squares must connect (no isolated regions)
- No 1 or 2-letter words (minimum 3 letters)
- Max 78 words for 15×15 themed puzzle
- Max 72 words for 15×15 themeless puzzle
- Black squares typically ~17% of grid (~38 for 15×15)

### Grid Sizes
- **11×11**: Compact daily puzzle
- **15×15**: Standard daily puzzle
- **21×21**: Sunday puzzle

---

## Numbering Algorithm

Standard crossword numbering rules:

1. **Scan left-to-right, top-to-bottom**
2. **Number cell if it starts:**
   - Across word (white cell with black/edge to left AND white to right)
   - OR down word (white cell with black/edge above AND white below)
3. **Numbers increment sequentially** (1, 2, 3, ...)
4. **Each cell gets maximum ONE number** (even if starts both across and down)

### Example:
```
R  A  T  #  C  A  T
#  T  #  #  #  T  #
D  O  G  #  B  A  T

Numbering:
1:R (starts across and down)
2:A (starts across)
3:C (starts across and down)
4:D (starts across and down)
5:O (starts across)
6:B (starts across and down)
```

---

## Multi-Word Entry Conventions

### Two-Word Names
Remove space, capitalize each word
- "Tina Fey" → **TINAFEY**
- "Real Madrid" → **REALMADRID**
- "Tracy Jordan" → **TRACYJORDAN**

### Titles with Articles
Keep article, remove space
- "La haine" → **LAHAINE**
- "The Office" → **THEOFFICE**
- "A League of Their Own" → **ALEAGUEOFTHEIROWN**

### Hyphenated Words
Remove hyphen
- "self-aware" → **SELFAWARE**
- "co-worker" → **COWORKER**
- "twenty-one" → **TWENTYONE**

### Apostrophes
Remove apostrophe
- "driver's license" → **DRIVERSLICENSE**
- "can't" → **CANT**

---

## Pattern Matching

### Wildcard Syntax
- `?` = any single letter
- Example: `?I?A` matches VISA, PITA, DIVA, KIWI

### Letter Frequency (for scoring)

**Most common (high score):**
E, A, R, I, O, T, N, S, L, U

**Medium frequency:**
D, C, H, M, P, G, B, F, Y, W, V

**Least common (low score):**
K, J, X, Q, Z

**Scoring principle:**
Words with more common letters score higher because they're easier to cross with other words.

---

## Crossword Fill Quality

### Good Fill
- Common words (everyday vocabulary)
- High letter frequency (EAIONRTLSU)
- Minimal crosswordese (overused obscure words)

### Crosswordese (avoid when possible)
- **ALOE** (plant mentioned too often)
- **OREO** (brand overused)
- **ESNE** (archaic for slave)
- **ETUI** (ornamental needle case)

### Best Practices
- Use fresh, interesting words
- Avoid repeating entries within puzzle
- Balance proper nouns with common words
- Theme entries should be longest in grid

---

**Usage:** Invoke this skill when working on crossword-specific logic (numbering, conventions, scoring, validation).
