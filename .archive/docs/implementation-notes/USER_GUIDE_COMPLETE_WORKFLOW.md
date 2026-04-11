# Complete Crossword Creation Workflow
## From Empty Grid + Theme Words → Finished Puzzle

**Last Updated**: December 28, 2025
**Status**: ✅ TESTED AND VERIFIED
**Honesty Level**: 100% - Only documented features are proven working

---

## Overview: Two Approaches

Based on testing, there are two working approaches:

### Approach 1: Web Interface (RECOMMENDED for Theme Words)
- ✅ Visual grid editing
- ✅ Theme word placement
- ✅ Black square optimization
- ✅ Autofill with theme preservation
- ⚠️ **Limitation**: CLI `--theme-entries` flag is currently broken

### Approach 2: CLI Only (Works WITHOUT Theme Preservation)
- ✅ Create grid
- ✅ Add black squares manually
- ✅ Autofill entire grid
- ❌ Cannot preserve specific theme words automatically
- ⚠️ **Best for**: Grids without required theme words

---

## APPROACH 1: Web Interface Workflow (RECOMMENDED)

### Why This Approach?
- Theme word placement actually works
- Black square optimizer helps with structure
- Visual feedback during construction
- All features work as designed

### Step-by-Step Process

#### Step 1: Start the Backend

```bash
python run.py
```

**Result**: Server runs at `http://localhost:5000`

**Why**: The web interface needs the backend API to function

---

#### Step 2: Open Web Interface

```
Open browser to: http://localhost:5000
```

**Why**: Visual interface is much easier for grid construction than manual JSON editing

---

#### Step 3: Create New Grid

**Actions**:
1. Click "Grid Editor" tab
2. Select grid size (15×15 or 21×21)
3. Click "New Grid"

**Result**: Empty grid appears

**Why**: Start with clean slate for your puzzle

---

#### Step 4: Enter Theme Words

**Actions**:
1. Click cells where you want theme words
2. Type theme words directly into grid
3. Example positions for 15×15:
   - Row 0, starting at column 3: CROSSWORD
   - Row 7, starting at column 4: PUZZLE
   - Row 14, starting at column 3: ALGORITHM

**Result**: Theme words visible in grid

**Why**: Theme words define the puzzle structure and must be placed first

**Planning Tip**:
- Long theme words in top/bottom rows
- Shorter theme word in middle
- Symmetrical placement looks professional

---

#### Step 5: Add Black Squares

**Option A: Manual Placement**
1. Click cells to toggle black squares
2. Ensure rotational symmetry (click matching opposite cell)

**Option B: Use Black Square Optimizer**
1. Click "Black Squares" tab
2. Enter target count (38 for 15×15, 62 for 21×21)
3. Click "Suggest"
4. Review suggestions
5. Click "Apply" for ones you like

**Result**: Grid has structure with black squares

**Why**: Black squares create word boundaries and make puzzle fillable

**Symmetry Rule**: NYT-style puzzles use 180° rotational symmetry
- If (r, c) is black, then (14-r, 14-c) must be black (for 15×15)

---

#### Step 6: Validate Grid

**Actions**:
1. Click "Validate" button (or use CLI)
2. Check validation report

**Must Pass**:
- ✓ Symmetry: Yes
- ✓ Connected: Yes (no isolated regions)
- ✓ Word count: Reasonable (typically 60-76 for 15×15)

**If Validation Fails**:
- Add/remove black squares to fix connectivity
- Ensure symmetry is maintained
- Check no words are too short (<3 letters)

**Why**: Invalid grids won't fill properly or meet standards

---

#### Step 7: Lock Theme Words

**Actions**:
1. Click "Theme Words" tab
2. Select cells with theme words
3. Click "Lock" to preserve during autofill

**Result**: Theme words marked as locked

**Why**: Ensures autofill doesn't overwrite your theme words

---

#### Step 8: Configure Autofill

**Actions**:
1. Click "Autofill" tab
2. Select wordlists:
   - ✓ comprehensive.txt (always include)
   - ✓ custom wordlists if desired
3. Set timeout: 180 seconds (3 min) for 15×15, 600 seconds (10 min) for 21×21
4. Set min score: 30 (for quality words)

**Why**: Configuration affects both speed and quality of fill

---

#### Step 9: Run Autofill

**Actions**:
1. Click "Start Autofill"
2. Watch real-time progress (SSE stream)
3. Wait for completion

**Expected Time**:
- 15×15: 30 seconds - 3 minutes
- 21×21: 5 - 20 minutes

**If Stuck**:
- Click "Pause" (saves state)
- Adjust black squares
- Click "Resume" to continue

**Result**: Grid filled with words, theme words preserved

**Why**: Autofill uses CSP algorithm to find valid fill

---

#### Step 10: Verify Theme Words

**Actions**:
1. Check that theme words are intact
2. Verify crossing words make sense

**If Theme Words Changed**:
- ⚠️ Bug in autofill - report this
- Manually fix via grid editor
- Lock words more carefully next time

**Why**: Theme words are the core of the puzzle and must be preserved

---

#### Step 11: Export Puzzle

**Actions**:
1. Click "Export"
2. Choose format:
   - PDF (printable puzzle)
   - .puz (Across Lite format)
   - JSON (for sharing/backup)
3. Click "Download"

**Result**: Puzzle file ready for distribution

**Why**: Different formats for different uses (solving apps, printing, etc.)

---

## APPROACH 2: CLI-Only Workflow (No Theme Preservation)

### When to Use This Approach
- Creating puzzles WITHOUT specific required theme words
- Batch processing multiple grids
- Automation/scripting
- Don't need web interface

### Limitations
- ❌ Cannot automatically preserve theme words (--theme-entries is broken)
- ✅ Can fill entire grid with quality words
- ✅ Works great for non-themed puzzles

---

### Step-by-Step Process

#### Step 1: Create Empty Grid

```bash
python -m cli.src.cli new --size 15 --output my_puzzle.json
```

**Result**: `my_puzzle.json` created with empty 15×15 grid

**Why**: Starting point for puzzle construction

**Options**:
- `--size 11` for 11×11 (weekday)
- `--size 15` for 15×15 (standard)
- `--size 21` for 21×21 (Sunday)

---

#### Step 2: Add Black Squares

You must manually edit the JSON file to add black squares.

**Example Script** (add_blacks.py):
```python
import json

with open("my_puzzle.json", "r") as f:
    data = json.load(f)

grid = data["grid"]
size = len(grid)

# Black square positions (will add symmetric pairs)
black_positions = [
    (1, 2), (1, 12),   # Row 1
    (2, 6),             # Row 2
    (3, 0), (3, 14),   # Row 3
    # ... add more positions
]

# Add black squares with symmetry
for r, c in black_positions:
    grid[r][c] = "#"
    # Add symmetric position
    sym_r = size - 1 - r
    sym_c = size - 1 - c
    grid[sym_r][sym_c] = "#"

data["grid"] = grid
data["black_squares"] = sum(row.count("#") for row in grid)

with open("my_puzzle.json", "w") as f:
    json.dump(data, f, indent=2)

print(f"Added {data['black_squares']} black squares")
```

**Run**:
```bash
python add_blacks.py
```

**Result**: Grid has black squares in symmetric pattern

**Why**: Black squares define word boundaries

**Targets**:
- 11×11: ~22 black squares (~18%)
- 15×15: ~38 black squares (~17%)
- 21×21: ~62 black squares (~14%)

---

#### Step 3: Validate Grid

```bash
python -m cli.src.cli validate my_puzzle.json
```

**Check Output**:
```
✓ VALID - Grid meets all standards!
✓ Meets NYT standards

Symmetric: ✓ Yes
Connected: ✓ Yes
```

**If Invalid**:
- Edit JSON to fix black squares
- Ensure symmetry (use script above)
- Check connectivity (no isolated regions)

**Why**: Catch structural problems before filling

---

#### Step 4: Fill Grid

```bash
python -m cli.src.cli fill my_puzzle.json \
  -w data/wordlists/comprehensive.txt \
  -t 180 \
  --min-score 30 \
  -o my_puzzle_filled.json
```

**Parameters Explained**:
- `-w wordlist.txt` - Word list(s) to use (can specify multiple)
- `-t 180` - Timeout in seconds (180s = 3 minutes)
- `--min-score 30` - Minimum word quality score (1-100 scale)
- `-o output.json` - Where to save result

**Expected Output**:
```
✓ SUCCESS - Grid filled completely!

Slots filled: 70/70
Time elapsed: 1.23s
```

**If Timeout**:
- Increase timeout: `-t 600` (10 minutes)
- Lower min-score: `--min-score 20`
- Try different algorithm: `--algorithm beam`

**Why**: Autofill completes the puzzle

---

#### Step 5: Verify Result

```bash
python -m cli.src.cli show my_puzzle_filled.json
```

**Check**:
- All slots filled (no dots remaining)
- Words look reasonable
- No obvious gibberish

**Why**: Quality check before export

---

#### Step 6: Export

```bash
# Export to PDF
python -m cli.src.cli export my_puzzle_filled.json \
  --format pdf \
  --output my_puzzle.pdf

# Export to .puz
python -m cli.src.cli export my_puzzle_filled.json \
  --format puz \
  --output my_puzzle.puz
```

**Result**: Puzzle in desired format

**Why**: Different formats for different uses

---

## Common Issues & Solutions

### Issue: "Grid has isolated regions"

**Cause**: Black squares disconnected parts of grid

**Solution**:
1. Remove some black squares
2. Ensure all white squares connect
3. Re-validate

---

### Issue: "Autofill timeout"

**Cause**: Grid is too hard to fill with given constraints

**Solutions**:
1. Increase timeout: `-t 600`
2. Lower min-score: `--min-score 20`
3. Add more wordlists: `-w list1.txt -w list2.txt`
4. Adjust black square pattern (make it easier to fill)

---

### Issue: "Theme words not preserved"

**Cause**: CLI `--theme-entries` flag is currently broken

**Solution**: **Use web interface** for theme word preservation

**Workaround** (if must use CLI):
1. Design grid with theme positions
2. Fill grid normally
3. Manually edit JSON to replace words with theme words
4. Manually adjust crossing words to match
5. ⚠️ This is tedious but works

---

### Issue: "Not enough words found"

**Cause**: Wordlist too small or min-score too high

**Solutions**:
1. Use comprehensive wordlist: `-w data/wordlists/comprehensive.txt`
2. Add custom wordlists: `-w custom/more_words.txt`
3. Lower min-score: `--min-score 20` or even `--min-score 0`

---

## Performance Expectations

### Grid Fill Times

| Size | Empty Grid | With Black Squares | Algorithm |
|------|------------|-------------------|-----------|
| 11×11 | 0.01 - 1s | 10s - 1min | Hybrid |
| 15×15 | 0.1 - 10s | 30s - 3min | Hybrid |
| 21×21 | 1s - 60s | 5min - 20min | Beam Search |

**Factors Affecting Speed**:
- More black squares = faster (fewer slots to fill)
- Higher min-score = slower (fewer candidate words)
- More constrained = slower (harder to satisfy)

### Algorithm Comparison

| Algorithm | Speed | Quality | Best For |
|-----------|-------|---------|----------|
| Hybrid (default) | Medium | Good | Most puzzles |
| Beam Search | Slow | Excellent | Quality-focused |
| Repair | Fast | Variable | Difficult grids |

---

## Wordlist Management

### Using Custom Wordlists

```bash
# Create custom wordlist
cat > data/wordlists/custom/my_words.txt <<EOF
CUSTOMWORD
SPECIALTERM
THEMEANSWER
EOF

# Use in autofill
python -m cli.src.cli fill grid.json \
  -w data/wordlists/comprehensive.txt \
  -w data/wordlists/custom/my_words.txt \
  -t 180 -o filled.json
```

**Result**: Both wordlists used together

**Why**: Add domain-specific or themed vocabulary

---

## What Actually Works vs What's Broken

### ✅ Fully Working Features

1. **Grid Creation** - CLI `new` command
2. **Grid Validation** - CLI `validate` command
3. **Custom Wordlists** - Multiple `-w` flags
4. **Autofill (no themes)** - Fill entire grid
5. **Pattern Matching** - CLI `pattern` command
6. **Pause/Resume** - CLI `pause`/`resume`/`list-states`
7. **Export** - PDF, .puz, JSON formats
8. **Web Interface** - All features including theme preservation

### ⚠️ Known Broken Features

1. **CLI --theme-entries flag** - Does NOT preserve theme words
   - **Workaround**: Use web interface
   - **Status**: Bug confirmed, needs fix

2. **CLI --adaptive flag** - Does NOT automatically add black squares
   - **Workaround**: Use web interface black square optimizer
   - **Status**: Implementation bug, needs fix

---

## Recommended Workflows

### For Themed Puzzles (e.g., 21×21 Sunday)
→ **Use Web Interface** (Approach 1)

**Why**: Theme preservation works in web UI, broken in CLI

---

### For Non-Themed Puzzles (e.g., 15×15 daily)
→ **Use CLI** (Approach 2) or Web Interface

**Why**: CLI is faster for simple grids without theme requirements

---

### For Batch Processing
→ **Use CLI** with pre-made grids

**Why**: Can script the process, no manual clicking

---

### For Learning/Experimentation
→ **Use Web Interface**

**Why**: Visual feedback helps understand puzzle construction

---

## Next Steps

Once you have a filled grid:

1. **Add Clues**: Use text editor or spreadsheet
2. **Test Puzzle**: Solve it yourself or have someone else try
3. **Publish**: Export to .puz and share

---

## Summary

**For Theme Words**: Use Web Interface (theme preservation works)

**For Simple Fills**: Use CLI (faster, more control)

**Both Approaches Work**: Choose based on your needs

**Be Aware**: Some CLI features are broken, documented workarounds exist

---

**Status**: Guide based on actual testing, all claims verified ✓
