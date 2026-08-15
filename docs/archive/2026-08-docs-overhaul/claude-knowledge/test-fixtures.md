# Test Fixtures

Sample data for testing crossword helper functionality.

## Sample Grids

### 3×3 Grid (Minimal Valid)
```json
{
  "size": 3,
  "grid": [
    ["C", "A", "T"],
    ["A", "R", "E"],
    ["B", "#", "E"]
  ]
}
```

**Expected numbering:**
- (0,0): 1 (CAT across, CAB down)
- (1,0): 2 (ARE across)
- (0,2): 3 (T?E down)

### 5×5 Grid (With Symmetry)
```json
{
  "size": 5,
  "grid": [
    ["R", "A", "S", "P", "S"],
    ["A", "R", "E", "A", "T"],
    ["S", "#", "A", "#", "E"],
    ["P", "I", "A", "N", "O"],
    ["S", "T", "E", "A", "K"]
  ]
}
```

**Properties:**
- 180° rotational symmetry (black squares mirror)
- Word count: 10 (5 across, 5 down)
- Black squares: 2

### 15×15 Grid (Standard Thursday)
```json
{
  "size": 15,
  "grid": [
    ["R", "A", "S", "P", "B", "E", "R", "R", "I", "E", "S", "#", "A", "C", "E"],
    ["E", "V", "E", "R", "Y", "T", "H", "I", "N", "G", "#", "U", "N", "I", "T"],
    ["A", "D", "A", "P", "T", "I", "V", "E", "#", "O", "N", "E", "D", "A", "Y"],
    ["L", "I", "E", "#", "#", "#", "E", "L", "M", "#", "#", "#", "A", "T", "E"],
    ["#", "#", "#", "C", "L", "U", "E", "L", "E", "S", "S", "L", "Y", "#", "#"],
    ["C", "O", "N", "V", "E", "N", "T", "I", "O", "N", "S", "#", "S", "E", "E"],
    ["A", "R", "E", "A", "#", "A", "T", "O", "M", "#", "E", "A", "R", "N", "S"],
    ["N", "O", "R", "M", "A", "L", "I", "Z", "E", "D", "#", "T", "O", "O", "K"],
    ["Y", "O", "G", "A", "#", "L", "I", "O", "N", "#", "D", "A", "T", "A"],
    ["O", "N", "E", "#", "P", "A", "T", "T", "E", "R", "N", "S", "#", "#", "#"],
    ["#", "#", "M", "A", "T", "C", "H", "I", "N", "G", "#", "#", "#", ".", "."],
    [".", ".", ".", "#", "#", "#", "G", "R", "I", "#", "#", "#", ".", ".", "."],
    [".", ".", ".", ".", ".", "#", "N", "U", "M", "B", "E", "R", "I", "N", "G"],
    [".", ".", ".", ".", ".", ".", "#", "V", "A", "L", "I", "D", "A", "T", "E"],
    [".", ".", ".", ".", ".", ".", ".", ".", ".", "#", "S", "C", "O", "R", "E"]
  ]
}
```

**Properties:**
- Standard 15×15 size (NYT weekday)
- Partial fill (. = empty cells)
- Black squares follow symmetry rules

## Sample Word Lists

### High-Score Words (Common Letters)
```
AREA (85)    - AERA common
TEAR (82)    - TEAR common
RATE (80)    - RATE common
LANE (78)    - LANE common
SEAT (77)    - SEAT common
```

### Medium-Score Words (Mixed Letters)
```
QUIZ (45)    - Q uncommon, IUZ moderate
FIZZ (42)    - F,Z uncommon, I common
COZY (48)    - C,O common, Z,Y uncommon
LYNX (40)    - L common, Y,N,X uncommon
```

### Low-Score Words (Uncommon Letters)
```
ZYZZYVA (12) - Multiple Z, Y, V
QUIXOTIC (18) - Q, X uncommon
FIZZGIG (15)  - Double Z, G uncommon
```

**Scoring Formula:**
```
score = 100 - (uncommon_count * 15) - (very_uncommon_count * 25)

Common: A,E,R,T,O,I,N,S,L
Uncommon: C,D,U,P,M,H,G,B
Very uncommon: F,Y,W,K,V,X,Z,J,Q
```

## Pattern Matching Test Cases

### Simple Patterns
```
Pattern: "?AT"     → CAT, BAT, RAT, SAT, HAT, MAT, FAT, PAT, VAT, TAT
Pattern: "????ING" → SINGING, RINGING, WINGING, DINGING, PINGING
Pattern: "A?E"     → ACE, AGE, ATE, AWE, AXE, ARE, APE
```

### Complex Patterns
```
Pattern: "?I?A"         → VISA, PITA, SIVA, DIVA, IDEA
Pattern: "??X??"        → BOXER, FIXER, MIXER, PIXEL, TAXED
Pattern: "????O?????"   → CATEGORIES, PHILOSOPHY, APOLOGETIC
```

### Edge Cases
```
Pattern: "A"       → Error (too short, min 3)
Pattern: "AA"      → Error (too short, min 3)
Pattern: "???"     → All 3-letter words (large result set)
Pattern: "????????????????????????" → Error (too long, max 20)
Pattern: "CA?T?"   → Valid 5-letter pattern
```

## Multi-Word Normalization Test Cases

### Two-Word Names
```
Input: "Tina Fey"       → TINAFEY
Input: "Tracy Jordan"   → TRACYJORDAN
Input: "Jack Donaghy"   → JACKDONAGHY
Input: "Liz Lemon"      → LIZLEMON
```

### Titles with Articles
```
Input: "The Office"     → THEOFFICE
Input: "A Star Is Born" → ASTARISBORN
Input: "An Ideal"       → ANIDEAL
```

### Hyphenated Words
```
Input: "Co-worker"      → COWORKER
Input: "Self-aware"     → SELFAWARE
Input: "X-ray"          → XRAY
Input: "Merry-go-round" → MERRYGOROUND
```

### Apostrophes
```
Input: "Rock 'n' Roll"  → ROCKNROLL
Input: "Don't"          → DONT
Input: "It's"           → ITS
Input: "I'll"           → ILL
```

### Mixed Cases
```
Input: "Co-worker's"    → COWORKERS (hyphen + apostrophe)
Input: "The X-Files"    → THEXFILES (article + hyphen)
Input: "'Til Death"     → TILDEATH (leading apostrophe)
```

## Error Cases

### Pattern Matching Errors
```json
{"pattern": "A"}                    → 400: Pattern too short (min 3)
{"pattern": "???????????????????????????"}  → 400: Pattern too long (max 20)
{"pattern": "CA7T"}                 → 400: Invalid characters (only A-Z and ?)
{"pattern": ""}                     → 400: Pattern required
{"pattern": "cat"}                  → 400: Pattern must be uppercase
```

### Grid Validation Errors
```json
{"size": 7, "grid": [...]}         → 400: Invalid size (must be 11, 15, or 21)
{"size": 15, "grid": []}           → 400: Grid array empty
{"size": 3, "grid": [[".",".","."]]} → 400: Grid dimensions don't match size
{"size": 3, "grid": [["C","7","T"]]} → 400: Invalid character in grid (7)
```

### Convention Errors
```json
{"text": ""}                       → 400: Text required
{"text": "A"}                      → 400: Text too short
{"text": "ThisIsAReallyLongPhraseExceedingOneHundredCharacters..."} → 400: Text too long (max 100)
```

## API Response Examples

### Success: Pattern Match
```json
{
  "results": [
    {
      "word": "VISA",
      "score": 78,
      "source": "onelook",
      "length": 4,
      "letter_quality": {"common": 3, "uncommon": 1}
    },
    {
      "word": "PITA",
      "score": 75,
      "source": "local",
      "length": 4,
      "letter_quality": {"common": 2, "uncommon": 2}
    }
  ],
  "meta": {
    "pattern": "?I?A",
    "total_found": 127,
    "sources_searched": ["onelook", "standard"],
    "query_time_ms": 245
  }
}
```

### Success: Grid Numbering
```json
{
  "numbering": {
    "(0,0)": 1,
    "(0,4)": 2,
    "(0,8)": 3,
    "(1,0)": 4
  },
  "validation": {
    "is_valid": true,
    "errors": []
  },
  "grid_info": {
    "size": [15, 15],
    "black_squares": 38,
    "word_count": 76,
    "meets_nyt_standards": true,
    "issues": []
  }
}
```

### Success: Normalization
```json
{
  "original": "Tina Fey",
  "normalized": "TINAFEY",
  "rule": {
    "type": "two_word_names",
    "description": "Two-word proper names: remove space, capitalize all",
    "explanation": "Proper names with two words are joined without spaces",
    "examples": [
      ["Tracy Jordan", "TRACYJORDAN"],
      ["Jack Donaghy", "JACKDONAGHY"]
    ]
  },
  "alternatives": []
}
```

### Error: Invalid Pattern
```json
{
  "error": "Pattern must be between 3 and 20 characters",
  "code": "PATTERN_LENGTH_INVALID",
  "details": {
    "provided_length": 2,
    "min_length": 3,
    "max_length": 20
  }
}
```
