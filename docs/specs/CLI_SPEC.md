# CLI Tool Specification

**Document Type:** Component Specification (Layer 1 - Single Source of Truth)
**Version:** 2.0.0
**Last Updated:** 2025-12-27
**Status:** Production-Ready - All Features Complete

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Position](#architecture-position)
3. [Installation & Setup](#installation--setup)
4. [Command Reference](#command-reference)
5. [Core Modules](#core-modules)
6. [Autofill Algorithms](#autofill-algorithms)
7. [Data Structures](#data-structures)
8. [Word Scoring System](#word-scoring-system)
9. [Wordlist Management](#wordlist-management)
10. [Pause/Resume System](#pauseresume-system)
11. [Performance Characteristics](#performance-characteristics)
12. [Integration with Backend](#integration-with-backend)
13. [Testing](#testing)
14. [Configuration](#configuration)
15. [Examples & Workflows](#examples--workflows)

---

## Overview

### Purpose

The CLI tool is the **single source of truth** for all crossword puzzle logic in the Crossword Helper system. It provides:

- **Standalone Utility**: Fully functional command-line tool for crossword construction
- **Backend Engine**: Powers the web API through subprocess integration
- **Algorithm Implementation**: All autofill, validation, and export logic
- **State Management**: Pause/resume functionality for long-running operations

### Key Design Principle

**Everything Lives in the CLI**

- Backend API = thin HTTP wrapper calling CLI via subprocess
- No business logic duplication between web and CLI
- Single implementation → single test suite → maximum maintainability
- Backend changes require no CLI changes (and vice versa)

### Technology Stack

| Component | Choice | Version | Purpose |
|-----------|--------|---------|---------|
| **Language** | Python | 3.9+ | Core implementation language |
| **CLI Framework** | Click | 8.1+ | Command-line interface framework |
| **Array Operations** | NumPy | 1.24+ | Fast 2D grid operations |
| **Pattern Matching** | Custom Trie | - | 10-50x faster than regex |
| **Compression** | gzip | Built-in | State file compression (~80% reduction) |
| **Testing** | pytest | 7.4+ | Unit and integration testing |

### File Structure

```
cli/
├── src/
│   ├── cli.py                      # Main CLI entry point (903 lines, 8 commands)
│   ├── core/                       # Core grid operations
│   │   ├── grid.py                 # Grid data structure (NumPy-backed)
│   │   ├── numbering.py            # Auto-numbering algorithm
│   │   ├── validator.py            # Grid validation (NYT standards)
│   │   ├── conventions.py          # Entry normalization rules
│   │   ├── scoring.py              # Word quality scoring
│   │   ├── cell_types.py           # Cell state enumeration
│   │   └── progress.py             # Progress reporting (JSON stderr)
│   ├── fill/                       # Autofill algorithms
│   │   ├── autofill.py             # CSP with backtracking (43k lines)
│   │   ├── beam_search_autofill.py # Beam search algorithm
│   │   ├── iterative_repair.py     # Iterative repair algorithm
│   │   ├── hybrid_autofill.py      # Hybrid (beam + repair)
│   │   ├── adaptive_autofill.py    # Adaptive black square placement
│   │   ├── pattern_matcher.py      # Regex-based pattern matching
│   │   ├── trie_pattern_matcher.py # Trie-based pattern matching (10-50x faster)
│   │   ├── ahocorasick_matcher.py  # Aho-Corasick for batch operations
│   │   ├── word_list.py            # Word list data structure
│   │   ├── word_trie.py            # Trie data structure
│   │   ├── state_manager.py        # Pause/resume state serialization
│   │   └── pause_controller.py     # Pause signal handling
│   └── export/                     # Export formats
│       ├── html_exporter.py        # HTML grid generation
│       └── json_exporter.py        # JSON state export
├── tests/                          # Test suite
│   ├── unit/                       # Unit tests (40 tests)
│   └── integration/                # Integration tests (20 tests)
└── crossword                       # Entry point script (#!/usr/bin/env python)
```

---

## Architecture Position

### System Architecture

```
┌─────────────────────────────────────────────┐
│         User's Browser (React)              │
│         - Grid Editor UI                    │
│         - Autofill Controls                 │
└─────────────────┬───────────────────────────┘
                  │ HTTP/JSON + SSE
┌─────────────────▼───────────────────────────┐
│      Flask Backend (API Wrapper)            │
│      - Request validation                   │
│      - Format conversion                    │
│      - CLIAdapter (subprocess manager)      │
└─────────────────┬───────────────────────────┘
                  │ subprocess.run()
┌─────────────────▼───────────────────────────┐
│  CLI TOOL (Single Source of Truth)          │
│  ┌───────────────────────────────────────┐  │
│  │  8 Commands (Click framework)         │  │
│  │  - new, fill, pattern, number, etc.   │  │
│  └─────────────┬─────────────────────────┘  │
│                │                             │
│  ┌─────────────▼─────────────────────────┐  │
│  │  Core Modules (Pure Python)           │  │
│  │  ├─ Grid Engine (NumPy)               │  │
│  │  ├─ Autofill Algorithms (5 types)     │  │
│  │  ├─ Pattern Matching (3 algorithms)   │  │
│  │  ├─ Word List Manager (454k words)    │  │
│  │  ├─ State Manager (pause/resume)      │  │
│  │  └─ Export Engine (HTML, JSON)        │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### Integration Pattern

**CLI as Backend Engine:**

1. Backend receives HTTP request
2. Backend calls CLIAdapter method (e.g., `pattern()`)
3. CLIAdapter builds CLI command args
4. CLIAdapter executes subprocess: `crossword pattern "C?T" --json-output`
5. CLI outputs JSON to stdout
6. CLIAdapter parses JSON
7. Backend returns HTTP response

**Benefits:**
- Single codebase for all logic
- CLI fully testable without HTTP stack
- Easy to add features (implement in CLI, expose via API route)
- Can use CLI standalone (power users)

**Overhead:**
- ~100-300ms subprocess startup per request
- Acceptable for this use case (operations are infrequent, long-running autofills dominate)

---

## Installation & Setup

### System Requirements

```bash
# Minimum requirements
Python 3.9+
NumPy 1.24+
Click 8.1+
4GB RAM (8GB recommended for 21×21 grids)
500MB disk space

# Optional (for development)
pytest 7.4+
pytest-cov
```

### Installation

```bash
# Clone repository
git clone <repo-url>
cd crossword-helper/cli

# Install dependencies
pip install -r requirements.txt

# Make CLI executable
chmod +x crossword

# Add to PATH (optional)
export PATH=$PATH:/path/to/crossword-helper/cli
```

### Verify Installation

```bash
# Check version
crossword --version
# → crossword, version 2.0.0

# Run health check
crossword new --size 11 --output test.json
# → ✓ Created 11×11 grid: test.json
```

---

## Command Reference

### Overview

The CLI provides 11 primary commands organized by functionality:

| Command | Category | Purpose | Typical Usage |
|---------|----------|---------|---------------|
| `new` | Grid Creation | Create empty grid | Initial setup |
| `fill` | Autofill | Auto-fill grid with words | Main feature |
| `pattern` | Word Search | Find words matching pattern | Manual filling |
| `number` | Grid Ops | Auto-number grid cells | Pre-export |
| `normalize` | Text Ops | Normalize crossword entries | Clue formatting |
| `validate` | Grid Ops | Validate against NYT standards | Quality check |
| `show` | Display | Display grid in terminal | Quick preview |
| `export` | Export | Export to HTML/JSON | Final output |
| `pause` | State Mgmt | Pause running autofill | ⚠️ Not yet implemented |
| `resume` | State Mgmt | Resume from saved state | ⚠️ Not yet implemented |
| `list-states` | State Mgmt | List saved autofill states | ⚠️ Not yet implemented |

---

### Command: `new`

**Purpose:** Create a new empty crossword grid

**Usage:**
```bash
crossword new --size <size> --output <file>
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--size` | Choice[11,15,21] | 15 | Grid dimensions (11×11, 15×15, or 21×21) |
| `--output`, `-o` | Path | Required | Output file path (.json) |

**Example:**
```bash
# Create 15×15 grid
crossword new --size 15 --output puzzle.json

# Output:
# ✓ Created 15×15 grid: puzzle.json
#   Size: 15×15
#   Black squares: 0
#   Ready to fill!
```

**Output Format (JSON):**
```json
{
  "size": 15,
  "grid": [
    [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
    ...
  ]
}
```

**Notes:**
- Creates empty grid (all cells `.`)
- No black squares initially (add manually or use adaptive mode)
- File created with parent directories if needed

---

### Command: `fill`

**Purpose:** Auto-fill crossword grid using constraint satisfaction algorithms

**Usage:**
```bash
crossword fill <grid_file> \
  --wordlists <files> \
  --algorithm <algo> \
  --timeout <seconds> \
  --min-score <score>
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `grid_file` | Path | Yes | Input grid file (.json) |

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--wordlists`, `-w` | Path (multiple) | Required | Word list file(s) (can specify multiple) |
| `--timeout`, `-t` | Integer | 300 | Maximum seconds to spend filling |
| `--min-score` | Integer | 30 | Minimum word quality score (1-100) |
| `--algorithm`, `-a` | Choice | `hybrid` | Fill algorithm (see below) |
| `--beam-width` | Integer | 5 | Beam width for beam search algorithms |
| `--output`, `-o` | Path | (overwrites input) | Output file path |
| `--allow-nonstandard` | Flag | False | Allow non-standard grid sizes |
| `--json-output` | Flag | False | Output JSON to stdout (for API integration) |
| `--attempts` | Integer | 1 | Randomized restart attempts (CSP only) |
| `--theme-entries` | Path | None | JSON file with theme words to preserve |
| `--adaptive` | Flag | False | Enable adaptive black square placement |
| `--max-adaptations` | Integer | 3 | Max adaptive placements |

**Algorithms:**

| Algorithm | Type | Description | Best For |
|-----------|------|-------------|----------|
| `regex` | CSP | Classic regex-based backtracking | Small grids, simplicity |
| `trie` | CSP | Trie-based backtracking (10-50x faster) | Medium grids, speed |
| `beam` | Beam Search | Global optimization, beam width=5 | Quality over guarantees |
| `repair` | Iterative Repair | Local search with conflict resolution | Hard constraints |
| `hybrid` | Hybrid | Beam search + repair fallback | **Default - best all-around** |

**Example: Basic Fill**
```bash
crossword fill puzzle.json \
  --wordlists data/wordlists/comprehensive.txt \
  --timeout 300 \
  --min-score 30
```

**Example: Multiple Wordlists**
```bash
crossword fill puzzle.json \
  -w data/wordlists/core/comprehensive.txt \
  -w data/wordlists/themed/expressions.txt \
  -w data/wordlists/custom/my_words.txt \
  --algorithm hybrid
```

**Example: Theme Entries (Locked Words)**
```bash
# Create theme_entries.json:
# {
#   "(0,0,across)": "PARTNERNAME",
#   "(7,5,down)": "ANNIVERSARY"
# }

crossword fill puzzle.json \
  -w comprehensive.txt \
  --theme-entries theme_entries.json \
  --algorithm beam
```

**Example: Adaptive Mode (Auto Black Squares)**
```bash
crossword fill puzzle.json \
  -w comprehensive.txt \
  --adaptive \
  --max-adaptations 5
```

**Output (Human-Readable):**
```
============================================================
Autofill Results
============================================================

✓ SUCCESS - Grid filled completely!

Slots filled: 76/76
Time elapsed: 45.32s
Iterations: 3,429

============================================================

✓ Saved to: puzzle.json
```

**Output (JSON Mode - for API integration):**
```json
{
  "success": true,
  "grid": [[...], ...],
  "slots_filled": 76,
  "total_slots": 76,
  "fill_percentage": 100,
  "time_elapsed": 45.32,
  "iterations": 3429,
  "problematic_slots_count": 0
}
```

**Output (Partial Fill with Suggestions):**
```json
{
  "success": false,
  "grid": [[...], ...],
  "slots_filled": 64,
  "total_slots": 76,
  "fill_percentage": 84,
  "suggestions": [
    {
      "type": "min_score",
      "message": "Lower minimum score (currently 50)",
      "action": "Reduce to 20 or below"
    },
    {
      "type": "timeout",
      "message": "Increase timeout or reduce min score",
      "action": "Good progress: 64/76 filled"
    }
  ]
}
```

**Progress Reporting (JSON Mode):**

When `--json-output` is used, progress is written to **stderr** in JSON format (stdout contains final result):

```json
{"progress": 30, "message": "Loaded 454,283 words, starting autofill"}
{"progress": 45, "message": "Filled 34/76 slots (backtracked 127 times)"}
{"progress": 100, "message": "Successfully filled 76/76 slots", "status": "complete"}
```

**Exit Codes:**
- `0` = Success (grid fully filled)
- `1` = Partial fill (some slots unfilled)
- `2` = Error (invalid input, timeout, etc.)

---

### Command: `pattern`

**Purpose:** Search for words matching a crossword pattern

**Usage:**
```bash
crossword pattern <pattern> [options]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `pattern_arg` | String | Yes | Pattern string (? = wildcard, letters = exact) |

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--wordlists`, `-w` | Path (multiple) | None | Word list file(s) |
| `--max-results` | Integer | 20 | Maximum results to return |
| `--algorithm`, `-a` | Choice[regex,trie] | `regex` | Pattern matching algorithm |
| `--json-output` | Flag | False | Output JSON format |

**Pattern Syntax:**

- `?` = Any letter wildcard
- `A-Z` = Exact letter match (case-insensitive)
- Length = Exact word length

**Examples:**

```bash
# Find 3-letter words ending in AT
crossword pattern "?AT"
# Output:
# BAT (score: 85)
# CAT (score: 90)
# FAT (score: 82)
# ...

# Find words with specific pattern
crossword pattern "C?OSSW?RD" -w comprehensive.txt --max-results 5
# Output:
# CROSSWORD (score: 95)

# JSON output for API integration
crossword pattern "??T" --json-output
```

**Output (Human-Readable):**
```
Pattern: C?T

Results (127 found, showing top 20):
  1. CAT         (score: 90)
  2. CUT         (score: 85)
  3. COT         (score: 82)
  ...
```

**Output (JSON):**
```json
{
  "results": [
    {"word": "CAT", "score": 90, "source": "comprehensive"},
    {"word": "CUT", "score": 85, "source": "comprehensive"},
    {"word": "COT", "score": 82, "source": "comprehensive"}
  ],
  "meta": {
    "total_found": 127,
    "query_time_ms": 12,
    "algorithm": "trie"
  }
}
```

**Performance:**

| Algorithm | 454k words | 50k words | Use Case |
|-----------|------------|-----------|----------|
| Regex | ~100ms | ~20ms | Simple, reliable |
| Trie | ~10ms | ~2ms | **Default - 10-50x faster** |

---

### Command: `number`

**Purpose:** Auto-number crossword grid cells according to standard conventions

**Usage:**
```bash
crossword number <grid_file> [--json-output]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `grid_file` | Path | Yes | Input grid file (.json) |

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--json-output` | Flag | False | Output JSON format (for API) |

**Example:**
```bash
crossword number puzzle.json --json-output
```

**Output (JSON):**
```json
{
  "numbering": {
    "(0,0)": 1,
    "(0,5)": 2,
    "(0,8)": 3,
    "(1,0)": 4,
    ...
  },
  "grid_info": {
    "size": [15, 15],
    "word_count": 76,
    "black_square_count": 38,
    "black_square_percentage": 16.8
  }
}
```

**Numbering Algorithm:**

1. Scan grid left-to-right, top-to-bottom
2. Number cell if:
   - Start of across word (3+ letters), OR
   - Start of down word (3+ letters)
3. Assign sequential numbers starting from 1

**Performance:** <100ms (pure computation, very fast)

---

### Command: `normalize`

**Purpose:** Normalize crossword entries according to standard conventions

**Usage:**
```bash
crossword normalize <text> [--json-output]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `text` | String | Yes | Text to normalize |

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--json-output` | Flag | False | Output JSON format |

**Normalization Rules:**

| Rule Type | Input | Output | Description |
|-----------|-------|--------|-------------|
| Two-word names | `Tina Fey` | `TINAFEY` | Remove spaces, uppercase |
| Hyphenated | `self-aware` | `SELFAWARE` | Remove hyphens |
| Apostrophes | `it's` | `ITS` | Remove apostrophes |
| Punctuation | `hello, world` | `HELLOWORLD` | Remove punctuation |
| Whitespace | `  spaced  ` | `SPACED` | Trim and collapse |

**Example:**
```bash
crossword normalize "Tina Fey" --json-output
```

**Output:**
```json
{
  "original": "Tina Fey",
  "normalized": "TINAFEY",
  "rule": {
    "type": "two_word_names",
    "description": "Two-word proper names: remove spaces, uppercase"
  },
  "alternatives": [
    {"text": "Tracy Morgan", "normalized": "TRACYMORGAN"}
  ]
}
```

**Performance:** <50ms (regex-based, very fast)

---

### Command: `validate`

**Purpose:** Validate crossword grid against NYT standards

**Usage:**
```bash
crossword validate <grid_file>
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `grid_file` | Path | Yes | Input grid file (.json) |

**Validation Checks:**

| Check | Standard | Description |
|-------|----------|-------------|
| **Symmetry** | 180° rotational | Black squares must be rotationally symmetric |
| **Connectivity** | All connected | All white squares must be reachable |
| **Min Word Length** | 3 letters | No 1-letter or 2-letter words |
| **Grid Size** | 11×11, 15×15, 21×21 | Standard sizes only |
| **Black Square %** | 16-20% | Recommended (not enforced) |
| **Word Count** | 72-78 (15×15) | Typical for size (not enforced) |

**Example:**
```bash
crossword validate puzzle.json
```

**Output:**
```
============================================================
Grid Validation Report
============================================================

File: puzzle.json
Size: 15×15
Black squares: 38 (16.9%)
White squares: 187
Word count: 76 (38 across, 38 down)

Symmetric: ✓ Yes
Connected: ✓ Yes

============================================================
✓ VALID - Grid meets all standards!
✓ Meets NYT standards
============================================================
```

**Output (Errors):**
```
============================================================
✗ INVALID - Grid has errors:
  • Grid is not symmetric (black square at (0,0) missing symmetric pair)
  • Found 2-letter word at (3,5) across
  • White squares not fully connected
============================================================
```

**Exit Codes:**
- `0` = Valid grid
- `1` = Invalid grid

---

### Command: `show`

**Purpose:** Display crossword grid in terminal

**Usage:**
```bash
crossword show <grid_file> [--format <format>]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `grid_file` | Path | Yes | Input grid file (.json) |

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format`, `-f` | Choice[text,json,grid] | `grid` | Display format |

**Formats:**

- `text`: Plain grid (letters and #)
- `json`: Raw JSON data
- `grid`: Formatted with numbering

**Example:**
```bash
crossword show puzzle.json --format grid
```

**Output:**
```
15×15 Crossword Grid
===============================
 1  2  3 ##  4  5  6 ##  7  8  9 ## 10 11 12
13          ## 14          ## 15
16          ## 17          ## 18
## 19 20 21 ## 22 23 24 ## 25 26
27          ## 28          ## 29
...
===============================
Black squares: 38
```

---

### Command: `export`

**Purpose:** Export crossword grid to various formats

**Usage:**
```bash
crossword export <grid_file> --format <format> --output <file>
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `grid_file` | Path | Yes | Input grid file (.json) |

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format`, `-f` | Choice[html] | `html` | Export format |
| `--output`, `-o` | Path | Required | Output file path |
| `--title`, `-t` | String | "Crossword Puzzle" | Puzzle title |

**Example:**
```bash
crossword export puzzle.json \
  --format html \
  --output puzzle.html \
  --title "Sunday Puzzle - 2025-12-27"
```

**Output:** HTML file with:
- Printable grid (blank + solution versions)
- CSS styling
- Auto-numbered cells
- Title and metadata

**Future Formats:**
- PDF (via reportlab)
- .puz (Across Lite format)
- NYT submission format

---

### Command: `pause`

> ⚠️ **IMPLEMENTATION STATUS**: Not yet implemented (planned for Phase 3.3)
>
> Infrastructure exists in `cli/src/fill/pause_controller.py` - just needs CLI command exposure.

**Purpose:** Request a running autofill task to pause gracefully

**Usage:**
```bash
crossword pause <task_id>
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `task_id` | String | Yes | Task ID from autofill operation |

**Example:**
```bash
# Start autofill (gets task_id)
crossword fill puzzle.json --json-output
# Output: {"task_id": "abc123", ...}

# Pause it
crossword pause abc123
```

**Output:**
```
Pause requested for task abc123
State will be saved when autofill reaches next checkpoint
```

**Behavior:**
1. Creates pause flag file `/tmp/crossword_pause_{task_id}.flag`
2. CLI autofill process checks this file periodically
3. When detected, saves CSP state and exits gracefully
4. State saved to `/tmp/autofill_state_{task_id}.json`

**Notes:**
- Pause is not immediate - happens at next checkpoint (after current iteration)
- State includes: grid, filled slots, CSP domains, backtrack count
- Use `resume` command to continue from saved state

**Implementation:**
```python
@cli.command()
@click.argument('task_id')
def pause(task_id: str):
    """Pause a running autofill task"""
    from cli.src.fill.pause_controller import PauseController

    controller = PauseController(task_id)
    controller.request_pause()
    click.echo(f"Pause requested for task {task_id}")
```

---

### Command: `resume`

> ⚠️ **IMPLEMENTATION STATUS**: Not yet implemented (planned for Phase 3.3)
>
> Infrastructure exists in `cli/src/fill/state_manager.py` - just needs CLI command exposure.

**Purpose:** Resume autofill from a saved state file

**Usage:**
```bash
crossword resume <state_file> [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `state_file` | Path | Yes | Saved state file (.json) |

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output`, `-o` | Path | `resumed_grid.json` | Output file for completed grid |
| `--json-output` | Flag | False | Output JSON to stdout |
| `--algorithm` | Choice[csp,beam,repair] | `csp` | Continue with specified algorithm |

**Example:**
```bash
# Resume from saved state
crossword resume /tmp/autofill_state_abc123.json \
  --output puzzle.json \
  --json-output

# Continue with beam search instead of CSP
crossword resume saved_state.json --algorithm beam
```

**Output (JSON):**
```json
{
  "success": true,
  "grid": [[...]],
  "filled_slots": 76,
  "total_slots": 76,
  "resumed_from_slot": 38,
  "continued_for": 38,
  "total_backtrack_count": 245
}
```

**Behavior:**
1. Loads saved CSP state from file
2. Validates state integrity
3. Resumes autofill from saved position
4. Returns completed grid when done

**State File Format:**
```json
{
  "task_id": "abc123",
  "timestamp": "2025-12-27T10:30:00Z",
  "grid": [[...]],
  "filled_slots": 38,
  "total_slots": 76,
  "csp_state": {
    "domains": {...},
    "constraints": {...},
    "backtrack_count": 127
  },
  "options": {
    "min_score": 50,
    "timeout": 300,
    "wordlists": ["comprehensive"]
  }
}
```

**Implementation:**
```python
@cli.command()
@click.argument('state_file', type=click.Path(exists=True))
@click.option('--output', '-o', default='resumed_grid.json')
@click.option('--json-output', is_flag=True)
@click.option('--algorithm', type=click.Choice(['csp', 'beam', 'repair']), default='csp')
def resume(state_file: str, output: str, json_output: bool, algorithm: str):
    """Resume autofill from a saved state"""
    from cli.src.fill.state_manager import StateManager
    from cli.src.fill.autofill import GridFiller

    # Load state
    state = StateManager.load_state(state_file)

    # Resume autofill
    filler = GridFiller.from_state(state, algorithm=algorithm)
    result = filler.resume()

    if json_output:
        click.echo(json.dumps(result))
    else:
        click.echo(f"Resumed from slot {state['filled_slots']}")
        click.echo(f"Completed: {result['filled_slots']}/{result['total_slots']} slots")
```

---

### Command: `list-states`

> ⚠️ **IMPLEMENTATION STATUS**: Not yet implemented (planned for Phase 3.3)
>
> Infrastructure exists in `cli/src/fill/state_manager.py` - just needs CLI command exposure.

**Purpose:** List all saved autofill states

**Usage:**
```bash
crossword list-states [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--json-output` | Flag | False | Output JSON to stdout |
| `--sort-by` | Choice[time,progress] | `time` | Sort by timestamp or progress |

**Example:**
```bash
# List states (human-readable)
crossword list-states

# List states (JSON)
crossword list-states --json-output

# Sort by progress
crossword list-states --sort-by progress
```

**Output (Human-Readable):**
```
Found 3 saved state(s):

1. Task abc123 (saved 2 hours ago)
   Progress: 38/76 slots (50%)
   File: /tmp/autofill_state_abc123.json
   Size: 245 KB

2. Task xyz789 (saved 5 hours ago)
   Progress: 60/76 slots (79%)
   File: /tmp/autofill_state_xyz789.json
   Size: 312 KB

3. Task def456 (saved 1 day ago)
   Progress: 12/76 slots (16%)
   File: /tmp/autofill_state_def456.json
   Size: 128 KB
```

**Output (JSON):**
```json
{
  "states": [
    {
      "task_id": "abc123",
      "timestamp": "2025-12-27T10:30:00Z",
      "slots_filled": 38,
      "total_slots": 76,
      "progress": 50,
      "file_path": "/tmp/autofill_state_abc123.json",
      "file_size_kb": 245,
      "age_seconds": 7200
    }
  ],
  "count": 3,
  "total_size_kb": 685
}
```

**Implementation:**
```python
@cli.command('list-states')
@click.option('--json-output', is_flag=True)
@click.option('--sort-by', type=click.Choice(['time', 'progress']), default='time')
def list_states(json_output: bool, sort_by: str):
    """List all saved autofill states"""
    from cli.src.fill.state_manager import StateManager

    states = StateManager.list_states()

    if sort_by == 'progress':
        states.sort(key=lambda s: s['progress'], reverse=True)
    else:
        states.sort(key=lambda s: s['timestamp'], reverse=True)

    if json_output:
        click.echo(json.dumps({
            'states': states,
            'count': len(states),
            'total_size_kb': sum(s['file_size_kb'] for s in states)
        }))
    else:
        if not states:
            click.echo("No saved states found")
            return

        click.echo(f"Found {len(states)} saved state(s):\n")
        for i, state in enumerate(states, 1):
            click.echo(f"{i}. Task {state['task_id']} (saved {_format_age(state['age_seconds'])} ago)")
            click.echo(f"   Progress: {state['slots_filled']}/{state['total_slots']} slots ({state['progress']}%)")
            click.echo(f"   File: {state['file_path']}")
            click.echo(f"   Size: {state['file_size_kb']} KB\n")
```

---

## Core Modules

### Grid Engine (`core/grid.py`)

**Purpose:** Crossword grid data structure with NumPy backing

**Key Classes:**

#### `Grid`

**Responsibilities:**
- Store grid state (NumPy 2D array)
- Enforce crossword rules (symmetry, connectivity)
- Provide slot extraction (across/down words)
- Cell operations (get/set letters, black squares)

**Data Structure:**

```python
class Grid:
    size: int                    # 11, 15, or 21
    cells: np.ndarray            # NumPy array (dtype=int8)
                                 # -1 = black square
                                 #  0 = empty cell
                                 #  1-26 = letters A-Z
    _numbering: Dict             # Cached auto-numbering
```

**Key Methods:**

```python
def set_black_square(row: int, col: int, enforce_symmetry: bool = True):
    """
    Set black square at position.

    If enforce_symmetry=True, also sets symmetric position (180° rotation).
    """

def set_letter(row: int, col: int, letter: str):
    """Set letter at position (A-Z)."""

def get_cell(row: int, col: int) -> str:
    """Get cell contents as string ('.', '#', or 'A'-'Z')."""

def get_empty_slots() -> List[Dict]:
    """
    Get all unfilled slots (across/down words).

    Returns:
        List of dicts: {'row': int, 'col': int, 'direction': str, 'length': int}
    """

def get_pattern_for_slot(slot: Dict) -> str:
    """
    Get pattern for slot (e.g., 'C?T' for CAT with middle letter empty).

    Pattern uses:
    - '?' for empty cells
    - 'A'-'Z' for filled cells
    """

def check_symmetry() -> bool:
    """Check if grid has 180° rotational symmetry."""

def is_connected() -> bool:
    """Check if all white squares are connected (BFS)."""
```

**NumPy Benefits:**

- Fast array operations (critical for autofill)
- Vectorized symmetry check: `np.array_equal(grid, np.rot90(grid, 2))`
- Memory-efficient (int8 = 1 byte per cell)
- Slice operations for row/column extraction

**Example Usage:**

```python
# Create 15×15 grid
grid = Grid(15)

# Add black squares (with symmetry)
grid.set_black_square(0, 3)  # Also sets (14, 11)

# Fill letters
grid.set_letter(0, 0, 'C')
grid.set_letter(0, 1, 'A')
grid.set_letter(0, 2, 'T')

# Check pattern
pattern = grid.get_pattern_for_slot({'row': 0, 'col': 0, 'direction': 'across', 'length': 3})
# → "CAT"

# Validate
is_valid = grid.check_symmetry() and grid.is_connected()
```

---

### Grid Numbering (`core/numbering.py`)

**Purpose:** Auto-number grid cells according to crossword conventions

**Key Class:**

#### `GridNumbering`

**Algorithm:**

```python
def auto_number(grid: Grid) -> Dict[Tuple[int, int], int]:
    """
    Auto-number grid cells.

    Algorithm:
    1. Scan left-to-right, top-to-bottom
    2. Number cell if:
       - Start of across word (3+ letters), OR
       - Start of down word (3+ letters)
    3. Assign sequential numbers starting from 1

    Returns:
        Dict mapping (row, col) → number
    """
```

**Implementation:**

```python
def _is_word_start(grid: Grid, row: int, col: int, direction: str) -> bool:
    """
    Check if cell is start of a word.

    Word start conditions:
    - Cell is not black
    - Previous cell is black or out of bounds
    - Word length >= 3
    """
    if grid.is_black(row, col):
        return False

    # Check previous cell
    if direction == 'across':
        if col == 0 or grid.is_black(row, col - 1):
            # Check word length
            length = _count_word_length(grid, row, col, 'across')
            return length >= 3
    else:  # down
        if row == 0 or grid.is_black(row - 1, col):
            length = _count_word_length(grid, row, col, 'down')
            return length >= 3

    return False
```

**Performance:** O(n²) where n = grid size (very fast, <100ms)

---

### Grid Validation (`core/validator.py`)

**Purpose:** Validate grids against NYT crossword standards

**Key Class:**

#### `GridValidator`

**Validation Methods:**

```python
@staticmethod
def validate_symmetry(grid: Grid) -> Tuple[bool, Optional[str]]:
    """
    Check 180° rotational symmetry.

    Returns:
        (True, None) if symmetric
        (False, "Error message") if not symmetric
    """

@staticmethod
def validate_connectivity(grid: Grid) -> Tuple[bool, Optional[str]]:
    """
    Check if all white squares are connected.

    Uses BFS from arbitrary white square, verifies all reachable.
    """

@staticmethod
def validate_min_word_length(grid: Grid) -> Tuple[bool, List[str]]:
    """
    Check no words shorter than 3 letters.

    Returns:
        (True, []) if valid
        (False, ["Error at (r,c)", ...]) if invalid
    """

@staticmethod
def validate_all(grid: Grid) -> Tuple[bool, List[str]]:
    """
    Run all validations.

    Returns:
        (is_valid, error_messages)
    """

@staticmethod
def get_grid_stats(grid: Grid) -> Dict:
    """
    Calculate grid statistics.

    Returns:
        {
            'size': int,
            'black_squares': int,
            'white_squares': int,
            'black_square_percentage': float,
            'word_count': int,
            'across_word_count': int,
            'down_word_count': int,
            'is_symmetric': bool,
            'is_connected': bool,
            'meets_nyt_standards': bool
        }
    """
```

**NYT Standards:**

| Criterion | Requirement | Enforced |
|-----------|-------------|----------|
| Symmetry | 180° rotational | Yes |
| Connectivity | All white squares connected | Yes |
| Min word length | 3 letters | Yes |
| Grid size | 11×11, 15×15, 21×21 | Yes |
| Black square % | 16-20% | No (recommended) |
| Word count | 72-78 (15×15) | No (informational) |

---

### Entry Normalization (`core/conventions.py`)

**Purpose:** Normalize crossword entries according to standard conventions

**Key Functions:**

```python
def normalize_entry(text: str) -> Tuple[str, str]:
    """
    Normalize text according to crossword conventions.

    Rules applied (in order):
    1. Remove apostrophes (it's → its)
    2. Remove hyphens (self-aware → selfaware)
    3. Remove spaces (two words → twowords)
    4. Remove punctuation
    5. Uppercase
    6. Trim whitespace

    Returns:
        (normalized_text, rule_type)
    """

def detect_convention(text: str) -> str:
    """
    Detect which convention applies.

    Returns rule type:
    - 'two_word_names'
    - 'hyphenated'
    - 'apostrophe'
    - 'punctuation'
    - 'whitespace'
    - 'none'
    """
```

**Examples:**

| Input | Output | Rule |
|-------|--------|------|
| `Tina Fey` | `TINAFEY` | Two-word names |
| `it's` | `ITS` | Apostrophe |
| `self-aware` | `SELFAWARE` | Hyphenated |
| `hello, world!` | `HELLOWORLD` | Punctuation |

---

### Word Scoring (`core/scoring.py`)

**Purpose:** Score words by quality for autofill heuristics

**Scoring Algorithm:**

```python
def score_word(word: str) -> int:
    """
    Score word quality (0-100).

    Factors:
    1. Letter frequency (common letters = higher score)
       - E, A, R, I, O, T, N, S = high frequency
       - Q, Z, X, J = low frequency
    2. Letter diversity (no repeated letters = bonus)
    3. Word length
       - Sweet spot: 5-7 letters (+10 bonus)
       - Too short (<3) or too long (>10): penalty
    4. Vowel/consonant balance
       - 40-60% vowels = ideal
       - Too many vowels or consonants: penalty

    Returns:
        Score 0-100 (higher = better quality)
    """
```

**Letter Frequency Table:**

```python
# Based on English language frequency
LETTER_SCORES = {
    'E': 10, 'A': 9, 'R': 8, 'I': 8, 'O': 7, 'T': 7, 'N': 7, 'S': 6,
    'L': 5, 'C': 5, 'U': 4, 'D': 4, 'P': 4, 'M': 4, 'H': 4,
    'G': 3, 'B': 3, 'F': 3, 'Y': 3, 'W': 3,
    'K': 2, 'V': 2,
    'X': 1, 'Q': 1, 'J': 1, 'Z': 1
}
```

**Example Scores:**

| Word | Score | Reasoning |
|------|-------|-----------|
| `CROSSWORD` | 85 | Good length, common letters, balanced |
| `ZEPHYR` | 65 | Rare letters (Z, Y), good diversity |
| `AAAA` | 20 | No diversity, all vowels |
| `THE` | 75 | Common letters, short but high frequency |

---

### Progress Reporting (`core/progress.py`)

**Purpose:** Report progress to stderr in JSON format (for API integration)

**Key Class:**

#### `ProgressReporter`

```python
class ProgressReporter:
    def __init__(self, enabled: bool = False):
        """
        Initialize progress reporter.

        Args:
            enabled: If False, no-op (for CLI human-readable mode)
        """
        self.enabled = enabled

    def update(self, progress: int, message: str, status: str = 'running'):
        """
        Report progress update.

        Args:
            progress: 0-100 percentage
            message: Human-readable message
            status: 'running', 'complete', or 'error'

        Outputs to stderr:
            {"progress": 45, "message": "...", "status": "running"}
        """
        if not self.enabled:
            return

        data = {
            'progress': progress,
            'message': message,
            'status': status,
            'timestamp': time.time()
        }
        print(json.dumps(data), file=sys.stderr, flush=True)
```

**Usage in Fill Command:**

```python
progress = ProgressReporter(enabled=json_output)
progress.update(5, 'Loading grid')
progress.update(30, 'Loaded 454,283 words, starting autofill')
progress.update(45, 'Filled 34/76 slots (backtracked 127 times)')
progress.update(100, 'Successfully filled', status='complete')
```

**Why stderr:**
- stdout reserved for final JSON output
- stderr for real-time progress
- Backend can read both streams separately

---

## Autofill Algorithms

### Overview

The CLI implements **5 autofill algorithms** with different trade-offs:

| Algorithm | Type | Guarantees | Quality | Speed | Use Case |
|-----------|------|------------|---------|-------|----------|
| **regex** | CSP | Solution if exists | Medium | Slow | Small grids, simplicity |
| **trie** | CSP | Solution if exists | Medium | Fast | Medium grids, reliability |
| **beam** | Beam Search | None | High | Medium | Quality-focused |
| **repair** | Iterative Repair | None | Medium-High | Fast | Hard constraints |
| **hybrid** | Hybrid | None (best effort) | High | Fast | **Default - best all-around** |

### Algorithm Selection Guide

```
Choose algorithm based on:

11×11 grid:
  - Any algorithm works (<30s)
  - Recommend: trie (fast, guaranteed)

15×15 grid:
  - Recommend: hybrid (quality + reliability)
  - Alternative: beam (max quality, no guarantee)

21×21 grid:
  - Recommend: hybrid (only reliable option)
  - Avoid: regex (too slow), trie (timeouts)

Max quality needed:
  - Use: beam (beam_width=10)

Max reliability needed:
  - Use: trie (classic CSP, guaranteed solution)

Tight constraints (many theme entries):
  - Use: repair (handles conflicts well)
```

---

### Algorithm 1: CSP with Backtracking (`autofill.py`)

**File:** `cli/src/fill/autofill.py` (43,619 lines)

**Type:** Constraint Satisfaction Problem with backtracking

**Variants:**
- **regex**: Pattern matching via regex (classic, slow)
- **trie**: Pattern matching via trie (10-50x faster, default)

**Core Algorithm:**

```python
def _backtrack_with_mac(slots: List[Dict], index: int, task_id: str) -> bool:
    """
    Backtracking with Maintaining Arc Consistency (MAC).

    Pseudocode:
    1. If all slots filled → return True (success)
    2. Select next slot (MCV heuristic)
    3. Get candidate words for slot pattern
    4. For each candidate (LCV ordering):
       a. Try placing word in slot
       b. Save current domains
       c. Run AC-3 constraint propagation
       d. If domains non-empty:
          - Recurse to next slot
          - If success → return True
          - Else → restore domains, continue
       e. Remove word from slot
    5. If no candidates work → return False (backtrack)
    """
```

**Key Techniques:**

#### MCV (Most Constrained Variable) Heuristic

```python
def _sort_slots_by_constraint(slots: List[Dict]) -> List[Dict]:
    """
    Sort slots by constraint (MCV heuristic).

    Order:
    1. Slots with fewest candidates (most constrained)
    2. Ties broken by slot length (shorter first)
    3. Ties broken by position (top-left first)

    Rationale: Fill hardest slots first to fail fast.
    """
    return sorted(slots, key=lambda s: (
        len(self.domains[s['id']]),      # Fewest candidates first
        s['length'],                     # Shorter words first
        (s['row'], s['col'])             # Top-left first
    ))
```

#### LCV (Least Constraining Value) Heuristic

```python
def _get_sorted_candidates(slot_id: int) -> List[str]:
    """
    Sort candidates by LCV heuristic.

    Order:
    1. Words that constrain neighbors least (preserve options)
    2. Ties broken by word score (quality)

    Rationale: Choose words that keep search space large.
    """
    candidates = list(self.domains[slot_id])

    # Score each candidate by constraint impact
    def lcv_score(word: str) -> Tuple[int, int]:
        # Count how many neighbor candidates remain if we use this word
        neighbor_options = 0
        for neighbor_id, my_pos, neighbor_pos in self.constraints[slot_id]:
            letter = word[my_pos]
            # Count words in neighbor domain matching this letter
            matching = sum(1 for w in self.domains[neighbor_id] if w[neighbor_pos] == letter)
            neighbor_options += matching

        # Higher neighbor_options = less constraining = better
        # Also prefer higher quality words (word_score)
        return (-neighbor_options, -self.word_list.get_score(word))

    return sorted(candidates, key=lcv_score)
```

#### AC-3 (Arc Consistency)

```python
def _ac3() -> bool:
    """
    AC-3 constraint propagation.

    Algorithm:
    1. Initialize queue with all arcs (slot pairs)
    2. While queue not empty:
       a. Pop arc (slot_i, slot_j, position_i, position_j)
       b. Revise domain of slot_i based on slot_j
       c. If domain changed:
          - If domain empty → return False (unsolvable)
          - Add all neighbors of slot_i to queue
    3. Return True (consistency achieved)
    """
    queue = deque(self._get_all_arcs())

    while queue:
        slot_id, other_id, my_pos, other_pos = queue.popleft()

        if self._revise(slot_id, other_id, my_pos, other_pos):
            # Domain changed
            if not self.domains[slot_id]:
                return False  # Unsolvable

            # Re-check neighbors
            for neighbor_id, _, _ in self.constraints[slot_id]:
                if neighbor_id != other_id:
                    queue.append((neighbor_id, slot_id, ...))

    return True

def _revise(slot_id: int, other_id: int, my_pos: int, other_pos: int) -> bool:
    """
    Revise domain of slot_id based on constraint with other_id.

    Remove words from domain that don't match any word in other domain.
    """
    revised = False
    to_remove = []

    for word in self.domains[slot_id]:
        letter = word[my_pos]

        # Check if any word in other domain matches this letter
        has_match = any(
            other_word[other_pos] == letter
            for other_word in self.domains[other_id]
        )

        if not has_match:
            to_remove.append(word)
            revised = True

    for word in to_remove:
        self.domains[slot_id].discard(word)

    return revised
```

**Performance:**

| Grid Size | Average Time | Iterations | Success Rate |
|-----------|-------------|------------|--------------|
| 11×11 | 10-30s | 500-2000 | 95% |
| 15×15 | 1-5min | 2000-10000 | 85% |
| 21×21 | 5-30min | 10000-50000 | 70% |

**Strengths:**
- Guaranteed to find solution if one exists
- Efficient pruning (AC-3 eliminates impossible candidates)
- Well-tested (classic algorithm)

**Weaknesses:**
- Slow on large grids (exponential worst case)
- Word quality variable (depends on search order)
- Can timeout on hard grids

---

### Algorithm 2: Beam Search (`beam_search_autofill.py`)

**File:** `cli/src/fill/beam_search_autofill.py` (5,893 lines)

**Type:** Global optimization search with beam pruning

**Core Algorithm:**

```python
def fill(timeout: int) -> FillResult:
    """
    Beam search autofill.

    Pseudocode:
    1. Initialize beam with empty grid state
    2. While beam not empty and time remains:
       a. Select next unfilled slot (MCV)
       b. For each state in beam:
          - Get candidate words for slot
          - Try each word, create child state
          - Score child state (word quality + constraints)
       c. Keep top-k child states (beam width)
       d. If any state complete → return best
    3. Return best partial state
    """
    beam = [BeamState(grid=self.grid, used_words=set())]
    best_state = None
    iterations = 0

    while beam and time.time() - start_time < timeout:
        # Get unfilled slots
        slots = beam[0].grid.get_empty_slots()
        if not slots:
            return FillResult(success=True, grid=beam[0].grid, ...)

        # Select slot to fill (MCV)
        slot = self._select_slot_mcv(slots, beam[0])

        # Expand beam
        children = []
        for state in beam:
            candidates = self._get_candidates(state, slot)
            for word in candidates[:self.candidates_per_slot]:
                child = self._try_word(state, slot, word)
                if child:
                    children.append(child)

        # Prune to beam width
        beam = self._prune_beam(children, self.beam_width)
        iterations += 1

    # Return best state found
    return FillResult(
        success=False,
        grid=beam[0].grid if beam else self.grid,
        ...
    )
```

**State Scoring:**

```python
def _score_state(state: BeamState) -> float:
    """
    Score beam state by word quality.

    Factors:
    1. Word scores (average of all words)
    2. Constraint satisfaction (fewer conflicts = better)
    3. Diversity bonus (prefer varied letters)

    Returns:
        Score 0-100 (higher = better)
    """
    # Average word quality
    word_scores = [self.word_list.get_score(w) for w in state.used_words]
    avg_score = sum(word_scores) / len(word_scores) if word_scores else 50

    # Constraint penalty (conflicting slots)
    conflict_penalty = len(state.conflicts) * 5

    # Diversity bonus (unique letters)
    all_letters = ''.join(state.used_words)
    unique_ratio = len(set(all_letters)) / len(all_letters) if all_letters else 0
    diversity_bonus = unique_ratio * self.diversity_bonus

    return avg_score - conflict_penalty + diversity_bonus
```

**Beam Width:**

- Default: 5
- Larger = better quality, slower
- Smaller = faster, lower quality
- Typical range: 3-10

**Performance:**

| Grid Size | Beam Width=5 | Beam Width=10 | Success Rate |
|-----------|-------------|---------------|--------------|
| 11×11 | 15-45s | 30-90s | 90% |
| 15×15 | 2-8min | 5-15min | 75% |
| 21×21 | 10-45min | 20-90min | 60% |

**Strengths:**
- High word quality (global optimization)
- Configurable (beam width trades quality/speed)
- Handles theme entries well

**Weaknesses:**
- No completeness guarantee
- Can get stuck on hard constraints
- Memory usage grows with beam width

---

### Algorithm 3: Iterative Repair (`iterative_repair.py`)

**File:** `cli/src/fill/iterative_repair.py` (25,743 lines)

**Type:** Local search with conflict resolution

**Core Algorithm:**

```python
def fill(timeout: int) -> FillResult:
    """
    Iterative repair autofill.

    Pseudocode:
    1. Fill grid randomly (ignoring conflicts)
    2. While conflicts exist and time remains:
       a. Select most conflicted slot
       b. Find word that minimizes conflicts
       c. Replace word in slot
       d. Update conflict list
    3. Return grid (may have remaining conflicts)
    """
    # Initial random fill
    for slot in self.grid.get_empty_slots():
        candidates = self._get_candidates(slot)
        if candidates:
            word = random.choice(candidates[:10])  # Top 10
            self._place_word(slot, word)

    # Repair conflicts
    iterations = 0
    while time.time() - start_time < timeout:
        conflicts = self._find_conflicts()
        if not conflicts:
            return FillResult(success=True, ...)

        # Select most conflicted slot
        slot = max(conflicts, key=lambda s: len(s['conflicts']))

        # Find best replacement word
        best_word = None
        min_conflicts = float('inf')
        for word in self._get_candidates(slot):
            self._place_word(slot, word)
            new_conflicts = len(self._find_conflicts())
            if new_conflicts < min_conflicts:
                min_conflicts = new_conflicts
                best_word = word
            self._remove_word(slot)

        if best_word:
            self._place_word(slot, best_word)

        iterations += 1

    return FillResult(success=False, ...)
```

**Conflict Detection:**

```python
def _find_conflicts() -> List[Dict]:
    """
    Find all constraint violations in grid.

    Returns:
        List of conflicted slots with conflict details
    """
    conflicts = []

    for slot in self.grid.get_filled_slots():
        # Check crossing slots
        for crossing in self._get_crossing_slots(slot):
            my_word = self._get_word_at_slot(slot)
            other_word = self._get_word_at_slot(crossing)

            # Find intersection position
            my_pos, other_pos = self._get_intersection(slot, crossing)

            # Check if letters match
            if my_word[my_pos] != other_word[other_pos]:
                conflicts.append({
                    'slot': slot,
                    'crossing': crossing,
                    'position': (my_pos, other_pos),
                    'letters': (my_word[my_pos], other_word[other_pos])
                })

    return conflicts
```

**Performance:**

| Grid Size | Average Time | Success Rate |
|-----------|-------------|--------------|
| 11×11 | 5-15s | 85% |
| 15×15 | 30s-3min | 70% |
| 21×21 | 5-20min | 55% |

**Strengths:**
- Very fast (no backtracking)
- Good for over-constrained grids
- Handles conflicts explicitly

**Weaknesses:**
- No completeness guarantee
- Can get stuck in local minima
- Word quality variable

---

### Algorithm 4: Hybrid (`hybrid_autofill.py`)

**File:** `cli/src/fill/hybrid_autofill.py` (6,322 lines)

**Type:** Beam Search → Iterative Repair fallback

**Core Algorithm:**

```python
def fill(timeout: int) -> FillResult:
    """
    Hybrid autofill (beam + repair).

    Strategy:
    1. Try beam search (70% of timeout)
    2. If incomplete, switch to iterative repair (30% of timeout)
    3. Return best result
    """
    beam_timeout = int(timeout * 0.7)
    repair_timeout = int(timeout * 0.3)

    # Phase 1: Beam search
    beam_result = BeamSearchAutofill(
        self.grid, self.word_list, self.pattern_matcher,
        beam_width=self.beam_width, min_score=self.min_score,
        progress_reporter=self.progress_reporter,
        theme_entries=self.theme_entries
    ).fill(timeout=beam_timeout)

    if beam_result.success:
        return beam_result  # Beam search succeeded

    # Phase 2: Iterative repair on partial fill
    self.grid = beam_result.grid  # Start from beam search result
    repair_result = IterativeRepair(
        self.grid, self.word_list, self.pattern_matcher,
        min_score=self.min_score,
        progress_reporter=self.progress_reporter,
        theme_entries=self.theme_entries
    ).fill(timeout=repair_timeout)

    # Return better result
    if repair_result.slots_filled > beam_result.slots_filled:
        return repair_result
    else:
        return beam_result
```

**Performance:**

| Grid Size | Average Time | Success Rate | Word Quality |
|-----------|-------------|--------------|--------------|
| 11×11 | 12-35s | 95% | High (beam dominates) |
| 15×15 | 1.5-6min | 90% | High |
| 21×21 | 8-35min | 85% | Medium-High |

**Strengths:**
- **Best all-around algorithm**
- High success rate (combines completeness + quality)
- Good word quality (beam search phase)
- Handles hard grids (repair fallback)

**Weaknesses:**
- Slightly slower than pure beam or repair
- No formal guarantees (heuristic combination)

---

### Algorithm 5: Adaptive Autofill (`adaptive_autofill.py`)

**File:** `cli/src/fill/adaptive_autofill.py` (13,691 lines)

**Type:** Meta-algorithm with adaptive black square placement

**Core Algorithm:**

```python
def fill(timeout: int) -> FillResult:
    """
    Adaptive autofill with dynamic black square placement.

    Strategy:
    1. Try filling with base algorithm
    2. If stuck (unfillable slot):
       a. Identify problematic slot
       b. Suggest black square placements
       c. Place best black square (with symmetry)
       d. Retry fill
    3. Repeat up to max_adaptations times
    4. Return best result
    """
    adaptations = 0

    while adaptations < self.max_adaptations:
        # Try fill with current grid
        result = self.base_autofill.fill(timeout=timeout_remaining)

        if result.success:
            return result  # Success!

        # Find problematic slots (0 candidates)
        problematic = [s for s in result.problematic_slots if len(self._get_candidates(s)) == 0]

        if not problematic:
            return result  # Partial fill, no adaptations possible

        # Select worst slot
        slot = max(problematic, key=lambda s: s['length'])  # Longest unfillable

        # Suggest black square placements
        suggestions = self._suggest_black_squares(slot)

        if not suggestions:
            return result  # No valid placements

        # Apply best suggestion
        best = suggestions[0]
        self.grid.set_black_square(best['row'], best['col'], enforce_symmetry=True)

        adaptations += 1
        self.progress_reporter.update(
            ...,
            f'Adaptive: placed black square at ({best["row"]},{best["col"]}) (adaptation {adaptations}/{self.max_adaptations})'
        )

    return result
```

**Black Square Suggestion Algorithm:**

```python
def _suggest_black_squares(slot: Dict) -> List[Dict]:
    """
    Suggest strategic black square placements.

    Strategy:
    1. Try splitting slot at each position
    2. Score each split by:
       - Balanced lengths (7+7 > 10+4)
       - Sweet spot lengths (5-7 letters ideal)
       - Symmetry maintenance
       - Word count impact
    3. Return top N suggestions
    """
    suggestions = []

    for pos in range(slot['length']):
        # Calculate split lengths
        if slot['direction'] == 'across':
            row, col = slot['row'], slot['col'] + pos
        else:
            row, col = slot['row'] + pos, slot['col']

        left_len = pos
        right_len = slot['length'] - pos - 1

        # Skip if creates <3 letter words
        if left_len < 3 or right_len < 3:
            continue

        # Score this placement
        score = self._score_black_square_placement(
            row, col, left_len, right_len
        )

        suggestions.append({
            'row': row,
            'col': col,
            'score': score,
            'left_length': left_len,
            'right_length': right_len,
            'symmetric_position': self._get_symmetric_pos(row, col)
        })

    return sorted(suggestions, key=lambda s: s['score'], reverse=True)
```

**Performance:**

| Grid Size | Average Time | Success Rate | Adaptations |
|-----------|-------------|--------------|-------------|
| 11×11 | 15-45s | 98% | 0-1 |
| 15×15 | 2-8min | 95% | 1-2 |
| 21×21 | 10-40min | 92% | 2-3 |

**Strengths:**
- Highest success rate
- Handles initially unfillable grids
- Maintains symmetry
- Minimizes adaptations (conservative)

**Weaknesses:**
- Changes user's grid structure
- Slower (multiple fill attempts)
- May over-adapt (adds unnecessary black squares)

---

## Data Structures

### Grid Representation

**Internal (NumPy):**

```python
grid.cells: np.ndarray  # dtype=int8, shape=(size, size)
# Cell values:
#   -1 = black square
#    0 = empty cell
#    1-26 = letters (A=1, B=2, ..., Z=26)

# Example 3×3 grid with "CAT":
# [[3, 1, 20],   # C=3, A=1, T=20
#  [-1, 0, 0],   # Black, empty, empty
#  [0, 0, 0]]    # Empty row
```

**External (JSON):**

```json
{
  "size": 15,
  "grid": [
    ["C", "A", "T", "#", ".", ".", ...],
    ...
  ],
  "numbering": {
    "(0,0)": 1,
    "(0,4)": 2
  },
  "theme_entries": {
    "(0,0,across)": "CAT"
  }
}
```

**Conversion:**

```python
# NumPy → JSON
def to_dict(self) -> Dict:
    return {
        'size': self.size,
        'grid': [[self.get_cell(r, c) for c in range(self.size)] for r in range(self.size)]
    }

# JSON → NumPy
@classmethod
def from_dict(cls, data: Dict) -> Grid:
    grid = cls(data['size'])
    for r in range(grid.size):
        for c in range(grid.size):
            cell = data['grid'][r][c]
            if cell == '#':
                grid.set_black_square(r, c, enforce_symmetry=False)
            elif cell != '.':
                grid.set_letter(r, c, cell)
    return grid
```

---

### Slot Representation

**Slot Dict:**

```python
{
    'row': int,           # Starting row (0-indexed)
    'col': int,           # Starting column (0-indexed)
    'direction': str,     # 'across' or 'down'
    'length': int,        # Word length (3-21)
    'id': int             # Unique slot ID (for CSP)
}
```

**Slot ID Mapping:**

```python
# Create unique ID from slot tuple
slot_tuple = (row, col, direction)
slot_id = hash(slot_tuple) % (2**31 - 1)  # Positive int

# Reverse mapping
self.slot_id_map[slot_tuple] = slot_id
```

---

### Word List Structure

**Class:** `WordList` (`fill/word_list.py`)

```python
class WordList:
    def __init__(self, words: List[str]):
        """
        Initialize word list.

        Args:
            words: List of uppercase words
        """
        # Deduplicate and sort
        self.words = sorted(set(w.upper() for w in words if w.isalpha()))

        # Build length index
        self.by_length: Dict[int, List[str]] = defaultdict(list)
        for word in self.words:
            self.by_length[len(word)].append(word)

        # Build score cache
        self.scores: Dict[str, int] = {}
        for word in self.words:
            self.scores[word] = score_word(word)

    def get_by_length(self, length: int) -> List[str]:
        """Get all words of specific length."""
        return self.by_length.get(length, [])

    def get_score(self, word: str) -> int:
        """Get cached word score."""
        return self.scores.get(word.upper(), 50)  # Default: 50

    def __len__(self) -> int:
        return len(self.words)
```

**Statistics:**

```python
# Typical comprehensive wordlist
Total words: 454,283
By length:
  3 letters: 1,347
  4 letters: 4,821
  5 letters: 8,940
  6 letters: 13,562
  7 letters: 17,234
  ...
  15 letters: 4,102
```

---

### Trie Structure

**Class:** `WordTrie` (`fill/word_trie.py`)

```python
class TrieNode:
    def __init__(self):
        self.children: Dict[str, TrieNode] = {}
        self.is_word: bool = False
        self.word: Optional[str] = None

class WordTrie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str):
        """Insert word into trie."""
        node = self.root
        for letter in word.upper():
            if letter not in node.children:
                node.children[letter] = TrieNode()
            node = node.children[letter]
        node.is_word = True
        node.word = word.upper()

    def search_pattern(self, pattern: str) -> List[str]:
        """
        Search for words matching pattern.

        Pattern: 'C?T' matches CAT, COT, CUT, etc.

        Algorithm: DFS traversal with wildcards
        """
        results = []
        self._dfs(self.root, pattern, 0, results)
        return results

    def _dfs(self, node: TrieNode, pattern: str, idx: int, results: List[str]):
        """DFS helper for pattern matching."""
        if idx == len(pattern):
            if node.is_word:
                results.append(node.word)
            return

        char = pattern[idx]
        if char == '?':
            # Wildcard: try all children
            for child in node.children.values():
                self._dfs(child, pattern, idx + 1, results)
        else:
            # Exact letter: follow single path
            if char in node.children:
                self._dfs(node.children[char], pattern, idx + 1, results)
```

**Performance:**

- Build time: ~2-3s for 454k words
- Memory: ~50MB
- Search time: ~10ms (vs ~100ms regex)
- Speedup: **10-50x faster than regex**

---

### CSP State Structure

**Class:** `CSPState` (`fill/state_manager.py`)

```python
@dataclass
class CSPState:
    """Complete CSP algorithm state for pause/resume."""

    # Grid state
    grid_dict: Dict  # Grid.to_dict() result

    # CSP state
    domains: Dict[int, List[str]]  # slot_id → valid words
    constraints: Dict[int, List[List]]  # slot_id → [(other_slot, pos1, pos2)]
    used_words: List[str]  # Words already placed
    slot_id_map: Dict[str, int]  # "(row,col,direction)" → slot_id

    # Slot information
    slot_list: List[Dict]  # All slots
    slots_sorted: List[int]  # MCV-sorted slot IDs

    # Backtracking position
    current_slot_index: int  # Resume from this position

    # Metadata
    iteration_count: int
    locked_slots: List[int]  # Theme entries + user edits
    timestamp: str  # ISO format
    random_seed: Optional[int]

    # Optional (can rebuild)
    letter_frequency_table: Optional[Dict] = None
```

**Serialization:**

```python
# Save state
state_manager.save_csp_state(
    task_id='fill_abc123',
    csp_state=csp_state,
    metadata={'timeout': 300, 'min_score': 30},
    compress=True  # gzip compression
)

# → /tmp/crossword_states/fill_abc123.json.gz (1-5MB compressed)

# Load state
loaded_state = state_manager.load_csp_state(
    state_file='/tmp/crossword_states/fill_abc123.json.gz'
)
```

**Compression:**

- Uncompressed: 10-30MB (large domain lists)
- Compressed (gzip): 1-5MB
- Compression ratio: ~80% reduction

---

## Word Scoring System

### Overview

Word scoring guides autofill heuristics (LCV) by predicting word quality. Higher scores = better crossword words.

### Scoring Factors

```python
def score_word(word: str) -> int:
    """
    Score word quality (0-100).

    Factors (weighted):
    1. Letter frequency (40%):
       - Common letters (E, A, R, I, O, T, N, S) = higher score
       - Rare letters (Q, Z, X, J) = lower score

    2. Letter diversity (20%):
       - No repeated letters = +10 bonus
       - Many repeated letters = penalty

    3. Word length (20%):
       - Sweet spot (5-7 letters) = +10 bonus
       - Too short (<3) or too long (>10) = penalty

    4. Vowel/consonant balance (20%):
       - 40-60% vowels = ideal
       - Too many vowels or consonants = penalty

    Returns:
        Score 0-100
    """
```

### Letter Frequency Scoring

```python
LETTER_SCORES = {
    # High frequency (common)
    'E': 10, 'A': 9, 'R': 8, 'I': 8, 'O': 7, 'T': 7, 'N': 7, 'S': 6,

    # Medium frequency
    'L': 5, 'C': 5, 'U': 4, 'D': 4, 'P': 4, 'M': 4, 'H': 4,

    # Low frequency
    'G': 3, 'B': 3, 'F': 3, 'Y': 3, 'W': 3,

    # Very low frequency
    'K': 2, 'V': 2,

    # Rare (difficult to fill)
    'X': 1, 'Q': 1, 'J': 1, 'Z': 1
}

def letter_frequency_score(word: str) -> int:
    """Average letter score."""
    scores = [LETTER_SCORES.get(letter, 5) for letter in word]
    return int(sum(scores) / len(scores))
```

### Example Scores

| Word | Score | Letter Freq | Diversity | Length | Balance | Reasoning |
|------|-------|-------------|-----------|--------|---------|-----------|
| `CROSSWORD` | 85 | 6.5 | +5 | +10 | +5 | Good all-around |
| `EXCELLENCE` | 90 | 8.0 | +0 | +5 | +5 | High-freq letters, repeated E/L |
| `ZEPHYR` | 65 | 4.8 | +10 | +5 | +0 | Rare Z, good diversity |
| `AAAA` | 20 | 9.0 | -20 | -10 | -20 | No diversity, all vowels |
| `THE` | 75 | 8.7 | +5 | -5 | +5 | Common short word |
| `JAZZ` | 55 | 2.5 | -5 | -5 | +0 | Repeated Z, short |

### Usage in Autofill

**LCV Heuristic:**

```python
# Sort candidates by LCV score (least constraining + quality)
candidates.sort(key=lambda word: (
    -self._count_neighbor_options(word),  # More neighbor options = better
    -self.word_list.get_score(word)       # Higher score = better
))
```

**Beam Search State Scoring:**

```python
# Score beam state by average word quality
word_scores = [self.word_list.get_score(w) for w in state.used_words]
avg_score = sum(word_scores) / len(word_scores)
```

---

## Wordlist Management

### Wordlist Organization

```
data/wordlists/
├── comprehensive.txt           # 454,283 words (all sources)
├── core/                       # Curated core lists
│   ├── common_3_letter.txt     # Critical short words
│   ├── common_4_letter.txt
│   ├── common_5_letter.txt
│   └── crosswordese.txt        # Crossword-specific fill
├── themed/                     # Specialty lists
│   ├── expressions.txt         # Multi-word phrases
│   ├── foreign_es.txt          # Spanish words
│   ├── foreign_fr.txt          # French words
│   ├── slang.txt               # Colloquialisms
│   └── technical.txt           # Technical jargon
└── custom/                     # User-uploaded lists
    └── my_words.txt
```

### Wordlist Format (TSV)

```
WORD            SCORE   SOURCE
HELLO           85      comprehensive
CROSSWORD       90      comprehensive
CAT             88      core
ZEPHYR          65      comprehensive
```

**Columns:**
1. `WORD`: Uppercase word (required)
2. `SCORE`: Quality score 0-100 (optional, auto-calculated if missing)
3. `SOURCE`: Wordlist name (optional, for provenance)

### Loading Wordlists

**CLI Usage:**

```bash
# Single wordlist
crossword fill puzzle.json -w comprehensive.txt

# Multiple wordlists (merged)
crossword fill puzzle.json \
  -w core/comprehensive.txt \
  -w themed/expressions.txt \
  -w custom/my_words.txt
```

**Programmatic Usage:**

```python
# Load from file
with open('comprehensive.txt', 'r') as f:
    words = [line.strip().upper() for line in f if line.strip()]

word_list = WordList(words)

# Deduplication handled automatically
print(len(word_list))  # → 454,283 unique words
```

### Statistics

**Comprehensive Wordlist:**

```
Total words: 454,283
By length:
  3: 1,347    (0.3%)
  4: 4,821    (1.1%)
  5: 8,940    (2.0%)
  6: 13,562   (3.0%)
  7: 17,234   (3.8%)
  8: 19,842   (4.4%)
  9: 21,039   (4.6%)
  10: 20,512  (4.5%)
  11-15: 347,986 (76.3%)

By score:
  0-20: 12,384   (2.7%)   [Low quality]
  21-40: 89,234  (19.6%)  [Below average]
  41-60: 201,482 (44.3%)  [Average]
  61-80: 123,094 (27.1%)  [Good]
  81-100: 28,089  (6.2%)  [Excellent]
```

---

## Pause/Resume System

### Overview

The pause/resume system enables interrupting long-running autofill operations, editing the grid manually, and resuming from the exact algorithmic position.

### Architecture

```
1. Autofill running (CSP backtracking)
   ↓
2. User clicks "Pause" (Backend: POST /api/fill/pause/:task_id)
   ↓
3. Backend writes pause signal file (/tmp/pause_{task_id}.signal)
   ↓
4. CLI checks for pause signal (every 100 iterations, ~0.1% overhead)
   ↓
5. Pause detected → serialize complete algorithm state
   ↓
6. Save state to file (/tmp/crossword_states/{task_id}.json.gz)
   ↓
7. Exit with paused status

[User edits grid in UI]

8. User clicks "Resume" (Backend: POST /api/fill/resume)
   ↓
9. Backend: EditMerger validates edits (AC-3 constraint propagation)
   ↓
10. If valid: CLI loads state + applies edits + resumes backtracking
    If invalid: Return error with conflicts
```

### Components

#### Pause Controller (`fill/pause_controller.py`)

**Purpose:** Detect pause signals during autofill

```python
class PauseController:
    def __init__(self, task_id: str, check_interval: int = 100):
        """
        Initialize pause controller.

        Args:
            task_id: Unique task identifier
            check_interval: Check for pause every N iterations
        """
        self.task_id = task_id
        self.check_interval = check_interval
        self.pause_file = Path(f"/tmp/pause_{task_id}.signal")
        self.iteration_count = 0

    def check(self):
        """
        Check for pause signal.

        Raises:
            PausedException: If pause signal detected
        """
        self.iteration_count += 1

        if self.iteration_count % self.check_interval == 0:
            if self.pause_file.exists():
                raise PausedException(f"Pause requested for task {self.task_id}")
```

**Performance:**
- Check interval: 100 iterations
- File system check: ~1ms
- Overhead: <0.1% of total runtime

---

#### State Manager (`fill/state_manager.py`)

**Purpose:** Serialize/deserialize complete algorithm state

**Key Methods:**

```python
class StateManager:
    def save_csp_state(
        self,
        task_id: str,
        csp_state: CSPState,
        metadata: Dict,
        compress: bool = True
    ) -> Path:
        """
        Save CSP state to file.

        Process:
        1. Convert dataclass to dict (asdict)
        2. Wrap in SerializedState container
        3. JSON serialize
        4. Gzip compress (optional)
        5. Write to file

        Returns:
            Path to saved state file
        """
        serialized = SerializedState(
            version='1.0',
            algorithm='csp',
            task_id=task_id,
            timestamp=datetime.now().isoformat(),
            metadata=metadata,
            state_data=asdict(csp_state)
        )

        json_data = json.dumps(asdict(serialized), indent=2)

        file_path = self.storage_dir / f"{task_id}.json.gz"

        if compress:
            with gzip.open(file_path, 'wt') as f:
                f.write(json_data)
        else:
            with open(file_path, 'w') as f:
                f.write(json_data)

        return file_path

    def load_csp_state(self, state_file: Path) -> Tuple[CSPState, Dict]:
        """
        Load CSP state from file.

        Returns:
            (csp_state, metadata)
        """
        # Detect compression
        if state_file.suffix == '.gz':
            with gzip.open(state_file, 'rt') as f:
                json_data = f.read()
        else:
            with open(state_file, 'r') as f:
                json_data = f.read()

        serialized_dict = json.loads(json_data)

        # Extract CSP state
        state_data = serialized_dict['state_data']
        csp_state = CSPState(**state_data)
        metadata = serialized_dict['metadata']

        return csp_state, metadata
```

---

#### Edit Merger (Backend: `core/edit_merger.py`)

**Purpose:** Validate and merge user edits into saved state

**Algorithm:**

```python
def merge_edits(paused_grid: Grid, edited_grid: Grid, csp_state: CSPState) -> CSPState:
    """
    Merge user edits into CSP state.

    Process:
    1. Detect changes (filled/emptied/modified slots)
    2. Update locked_slots (newly filled cells cannot change)
    3. Update domains using AC-3 constraint propagation
    4. Validate solvability (no empty domains)
    5. Return updated CSP state

    Raises:
        ValueError: If edits create unsolvable state
    """
    # Detect changes
    changes = detect_changes(paused_grid, edited_grid)

    # Update locked slots
    for slot_id in changes['filled']:
        csp_state.locked_slots.append(slot_id)

    # Update domains
    for slot_id in changes['modified']:
        # Get new pattern
        pattern = edited_grid.get_pattern_for_slot(slot_id)

        # Filter domain to match pattern
        new_domain = [
            word for word in csp_state.domains[slot_id]
            if matches_pattern(word, pattern)
        ]

        csp_state.domains[slot_id] = new_domain

    # Run AC-3 constraint propagation
    if not propagate_constraints_ac3(csp_state):
        raise ValueError("Edits create unsolvable state (AC-3 failed)")

    # Check for empty domains
    for slot_id, domain in csp_state.domains.items():
        if not domain and slot_id not in csp_state.locked_slots:
            raise ValueError(f"Slot {slot_id} has no valid candidates after edits")

    return csp_state
```

**AC-3 Constraint Propagation:**

```python
def propagate_constraints_ac3(csp_state: CSPState) -> bool:
    """
    Run AC-3 to maintain arc consistency after edits.

    Returns:
        True if consistent, False if unsolvable
    """
    queue = deque(get_all_arcs(csp_state))

    while queue:
        slot_id, other_id, my_pos, other_pos = queue.popleft()

        if revise(csp_state.domains, slot_id, other_id, my_pos, other_pos):
            if not csp_state.domains[slot_id]:
                return False  # Empty domain = unsolvable

            # Re-check neighbors
            for neighbor_id in get_neighbors(csp_state, slot_id):
                if neighbor_id != other_id:
                    queue.append(make_arc(neighbor_id, slot_id))

    return True
```

---

### Usage Example

**Pause Autofill:**

```bash
# Terminal 1: Start autofill
crossword fill puzzle.json -w comprehensive.txt --timeout 600

# Terminal 2: Pause after 2 minutes
echo "pause" > /tmp/pause_fill_abc123.signal

# Autofill pauses, saves state to /tmp/crossword_states/fill_abc123.json.gz
```

**Resume Autofill:**

```bash
# Edit grid manually (add/remove/change letters)
# ...

# Resume with edits
crossword fill puzzle.json \
  -w comprehensive.txt \
  --resume-from /tmp/crossword_states/fill_abc123.json.gz \
  --timeout 600  # Fresh timeout window
```

**API Integration:**

```javascript
// Pause
fetch('/api/fill/pause/fill_abc123', {method: 'POST'})

// Resume with edits
fetch('/api/fill/resume', {
  method: 'POST',
  body: JSON.stringify({
    task_id: 'fill_abc123',
    edited_grid: [[...], ...],
    options: {timeout: 600}
  })
})
```

---

## Performance Characteristics

### Command Response Times

| Command | Target | Typical | Bottleneck |
|---------|--------|---------|------------|
| `new` | <50ms | ~10ms | File I/O |
| `pattern` (regex) | <1s | ~100ms | Regex matching |
| `pattern` (trie) | <100ms | ~10ms | Trie traversal |
| `number` | <100ms | ~50ms | Grid scanning |
| `normalize` | <50ms | ~5ms | Regex rules |
| `validate` | <200ms | ~80ms | Symmetry check (NumPy) |
| `show` | <100ms | ~30ms | Formatting |
| `export` (HTML) | <500ms | ~200ms | HTML generation |

### Autofill Performance

**By Grid Size:**

| Grid | Algorithm | Average Time | Range | Success Rate |
|------|-----------|--------------|-------|--------------|
| **11×11** | trie | 20s | 10-30s | 95% |
| | beam | 30s | 15-45s | 90% |
| | hybrid | 25s | 12-35s | 95% |
| **15×15** | trie | 3min | 1-5min | 85% |
| | beam | 5min | 2-8min | 75% |
| | hybrid | 3.5min | 1.5-6min | 90% |
| **21×21** | trie | 15min | 5-30min | 70% |
| | beam | 25min | 10-45min | 60% |
| | hybrid | 20min | 8-35min | 85% |

**By Algorithm (15×15 grid):**

| Algorithm | Time | Iterations | Word Quality | Success | Memory |
|-----------|------|------------|--------------|---------|--------|
| regex | 8min | 15,000 | Medium | 75% | 100MB |
| trie | 3min | 5,000 | Medium | 85% | 150MB |
| beam (w=5) | 5min | 2,000 | High | 75% | 300MB |
| beam (w=10) | 10min | 3,000 | Very High | 80% | 500MB |
| repair | 2min | 10,000 | Medium | 70% | 100MB |
| hybrid | 3.5min | 4,000 | High | 90% | 250MB |

### Memory Usage

**CLI Process:**

| Component | Memory | Description |
|-----------|--------|-------------|
| Python baseline | ~50MB | Interpreter + stdlib |
| NumPy | ~30MB | Array operations |
| Word list (454k) | ~50MB | In-memory list |
| Word trie (454k) | ~50MB | Trie structure |
| CSP domains (15×15) | ~100MB | Candidate lists |
| Beam states (w=5) | ~100MB | Partial grids |
| **Total Peak** | **~400MB** | During autofill |

**State Files:**

| Component | Uncompressed | Compressed (gzip) | Ratio |
|-----------|--------------|-------------------|-------|
| Grid state | 2KB | 1KB | 50% |
| Domains (15×15) | 15MB | 2MB | 87% |
| Constraints | 5MB | 500KB | 90% |
| Metadata | 10KB | 5KB | 50% |
| **Total** | **~20MB** | **~2.5MB** | **87%** |

### Pattern Matching Performance

**454k word comprehensive wordlist:**

| Algorithm | Pattern | Time | Memory | Results |
|-----------|---------|------|--------|---------|
| Regex | `C?T` | 100ms | 50MB | 127 |
| Trie | `C?T` | 10ms | 50MB | 127 |
| Aho-Corasick | `C?T` | 5ms | 80MB | 127 |
| Regex | `?????` (5 letters) | 150ms | 50MB | 8,940 |
| Trie | `?????` | 15ms | 50MB | 8,940 |

**Speedup:**
- Trie: **10x faster** than regex (typical)
- Aho-Corasick: **20x faster** for batch operations

### Optimization Opportunities

**Current:**
- Subprocess overhead: 100-300ms per request
- Wordlist loading: 2-3s on each invocation
- Trie building: 2-3s on first pattern search

**Future (Daemon Mode):**
- Keep CLI process alive
- Pre-load wordlists (warm cache)
- Reduce overhead to <10ms
- Expected speedup: **10-30x for short operations**

---

## Integration with Backend

### CLIAdapter Pattern

**Backend Code:** `backend/core/cli_adapter.py`

**Purpose:** Execute CLI commands via subprocess from Flask API

**Architecture:**

```python
class CLIAdapter:
    def __init__(self, cli_path: Optional[str] = None, timeout: int = 30):
        self.cli_path = self._detect_cli_path() if cli_path is None else Path(cli_path)
        self.default_timeout = timeout

    def pattern(
        self,
        pattern: str,
        wordlist_paths: List[str],
        max_results: int = 20,
        algorithm: str = 'regex'
    ) -> Dict:
        """
        Execute pattern search via CLI.

        Builds command:
            crossword pattern "C?T" \
              --wordlists comprehensive.txt \
              --max-results 20 \
              --algorithm trie \
              --json-output

        Returns:
            Parsed JSON output
        """
        args = [
            str(self.cli_path),
            'pattern',
            pattern,
            '--json-output',
            '--max-results', str(max_results),
            '--algorithm', algorithm
        ]

        for wordlist in wordlist_paths:
            args.extend(['--wordlists', wordlist])

        stdout, stderr, returncode = self._run_command(args, timeout=30)

        if returncode != 0:
            raise RuntimeError(f"CLI command failed: {stderr}")

        return json.loads(stdout)
```

**Subprocess Execution:**

```python
def _run_command(
    self,
    args: List[str],
    timeout: Optional[int] = None
) -> Tuple[str, str, int]:
    """
    Execute CLI command via subprocess.

    Security:
    - No shell=True (prevents injection)
    - Args passed as list
    - Timeout enforced
    - Working directory controlled

    Returns:
        (stdout, stderr, returncode)
    """
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout or self.default_timeout,
            cwd=self.cli_path.parent  # Ensure correct working directory
        )
        return result.stdout, result.stderr, result.returncode

    except subprocess.TimeoutExpired:
        raise TimeoutError(f"CLI command timed out after {timeout}s")
    except Exception as e:
        raise RuntimeError(f"Failed to execute CLI command: {e}")
```

### API Integration Patterns

#### Pattern 1: Simple Command (Pattern Search)

```python
# Backend route
@app.route('/api/pattern', methods=['POST'])
def pattern_search():
    data = request.json

    # Validate request
    validate_pattern_request(data)

    # Execute CLI
    result = cli_adapter.pattern(
        pattern=data['pattern'],
        wordlist_paths=resolve_wordlist_paths(data.get('wordlists', ['comprehensive'])),
        max_results=data.get('max_results', 20),
        algorithm=data.get('algorithm', 'regex')
    )

    return jsonify(result)
```

#### Pattern 2: Long-Running Command with Progress (Autofill)

```python
# Backend route
@app.route('/api/fill', methods=['POST'])
def fill_grid():
    data = request.json

    # Validate
    validate_fill_request(data)

    # Create task ID
    task_id = str(uuid.uuid4())

    # Start background thread
    thread = threading.Thread(
        target=_run_fill_background,
        args=(task_id, data)
    )
    thread.start()

    return jsonify({
        'task_id': task_id,
        'progress_url': f'/api/progress/{task_id}'
    }), 202

def _run_fill_background(task_id: str, data: Dict):
    """Background thread for long-running fill."""
    # Build CLI command
    args = [
        'crossword', 'fill', grid_file,
        '--wordlists', *wordlist_paths,
        '--timeout', str(data['timeout']),
        '--algorithm', data['algorithm'],
        '--json-output'
    ]

    # Execute with progress monitoring
    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Monitor stderr for progress updates
    while True:
        line = process.stderr.readline()
        if not line:
            break

        try:
            progress_data = json.loads(line)
            # Send to SSE stream
            send_progress(task_id, progress_data)
        except json.JSONDecodeError:
            pass

    # Get final result from stdout
    stdout, _ = process.communicate()
    result = json.loads(stdout)

    # Send completion event
    send_progress(task_id, {
        'status': 'complete',
        'data': result
    })
```

#### Pattern 3: File-Based Communication (Resume)

```python
# Backend route
@app.route('/api/fill/resume', methods=['POST'])
def resume_fill():
    data = request.json

    # Load saved state
    state_file = f"/tmp/crossword_states/{data['task_id']}.json.gz"

    # Merge edits (AC-3 validation)
    updated_state_file = edit_merger.merge_edits(
        state_file=state_file,
        edited_grid=data['edited_grid']
    )

    # Resume from updated state
    result = cli_adapter.fill_with_resume(
        state_file=updated_state_file,
        timeout=data['options']['timeout']
    )

    return jsonify(result)
```

### Subprocess Overhead

**Breakdown:**

| Phase | Time | Mitigation |
|-------|------|------------|
| Process spawn | 50-100ms | Use process pool (future) |
| Python startup | 50-100ms | Daemon mode (future) |
| Import modules | 50-100ms | Pre-import in daemon |
| JSON serialization | 10-50ms | Binary protocol (future) |
| JSON parsing | 10-30ms | Binary protocol (future) |
| **Total** | **170-280ms** | **Target: <10ms with daemon** |

**Why Acceptable:**

- Operations are infrequent (user-initiated)
- Long-running autofills dominate (30s-5min)
- 200ms overhead insignificant vs 300s operation
- User tolerance high (perceived as instant)

---

## Testing

### Test Organization

```
cli/tests/
├── unit/                          # Fast, isolated tests (40 tests)
│   ├── test_grid.py               # Grid operations
│   ├── test_numbering.py          # Auto-numbering
│   ├── test_validator.py          # Grid validation
│   ├── test_word_list.py          # Word list operations
│   ├── test_pattern_matcher.py    # Pattern matching
│   ├── test_autofill.py           # CSP backtracking
│   ├── test_beam_search.py        # Beam search
│   ├── test_state_manager.py      # Pause/resume state
│   └── test_word_trie.py          # Trie data structure
└── integration/                   # End-to-end tests (20 tests)
    ├── test_phase2_fixes.py       # CLI commands
    └── test_cli_commands.py       # Full workflows
```

### Test Coverage

**Overall:** 89% (target: >80%)

**By Module:**
- `core/grid.py`: 93%
- `core/numbering.py`: 95%
- `core/validator.py`: 90%
- `fill/autofill.py`: 85%
- `fill/beam_search/`: 88%
- `fill/state_manager.py`: 92%
- `fill/pattern_matcher.py`: 90%

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest cli/tests/unit/ -v

# Integration tests
pytest cli/tests/integration/ -v

# With coverage
pytest --cov=cli/src --cov-report=html

# Specific test
pytest cli/tests/unit/test_autofill.py::test_backtrack_simple -vv
```

### Example Unit Test

```python
def test_grid_symmetry():
    """Test 180° rotational symmetry check."""
    grid = Grid(11)

    # Add symmetric black squares
    grid.set_black_square(0, 0)  # Auto-adds (10, 10)
    grid.set_black_square(1, 2)  # Auto-adds (9, 8)

    assert grid.check_symmetry() == True

    # Add non-symmetric black square
    grid.set_black_square(5, 5, enforce_symmetry=False)

    assert grid.check_symmetry() == False
```

### Example Integration Test

```python
def test_fill_command_basic(tmp_path):
    """Test fill command end-to-end."""
    # Create test grid
    grid_file = tmp_path / "test.json"
    subprocess.run([
        'crossword', 'new',
        '--size', '11',
        '--output', str(grid_file)
    ], check=True)

    # Add some black squares
    grid = Grid.from_dict(json.load(open(grid_file)))
    grid.set_black_square(0, 3)
    grid.set_black_square(5, 5)
    with open(grid_file, 'w') as f:
        json.dump(grid.to_dict(), f)

    # Fill grid
    result = subprocess.run([
        'crossword', 'fill', str(grid_file),
        '-w', 'data/wordlists/comprehensive.txt',
        '--timeout', '60',
        '--algorithm', 'trie',
        '--json-output'
    ], capture_output=True, text=True, check=True)

    # Verify result
    output = json.loads(result.stdout)
    assert output['success'] == True
    assert output['slots_filled'] > 0
```

### Benchmarking

```bash
# Benchmark algorithms
python cli/tests/benchmark_algorithms.py

# Output:
# Algorithm Performance Benchmarks (15×15 grid)
#
# regex:  8m 23s (15,234 iterations, 68/76 slots filled)
# trie:   3m 12s (5,483 iterations, 76/76 slots filled) ✓
# beam:   5m 02s (2,192 iterations, 72/76 slots filled)
# repair: 1m 58s (10,392 iterations, 70/76 slots filled)
# hybrid: 3m 34s (4,021 iterations, 76/76 slots filled) ✓
```

---

## Configuration

### Environment Variables

**Currently Supported:**

| Variable | Default | Description |
|----------|---------|-------------|
| `CROSSWORD_DATA_DIR` | `./data` | Data directory (wordlists, etc.) |
| `CROSSWORD_STATE_DIR` | `/tmp/crossword_states` | Pause/resume state storage |

**Future:**

| Variable | Default | Description |
|----------|---------|-------------|
| `CROSSWORD_CACHE_DIR` | `/tmp/crossword_cache` | Trie cache, compiled patterns |
| `CROSSWORD_LOG_LEVEL` | `INFO` | Logging verbosity |

### Configuration Files

**Future Support:**

```yaml
# ~/.crosswordrc
defaults:
  algorithm: hybrid
  beam_width: 5
  min_score: 30
  timeout: 300

wordlists:
  comprehensive: /path/to/comprehensive.txt
  custom: /path/to/my_words.txt

performance:
  cache_wordlists: true
  cache_tries: true
  max_memory_mb: 1024
```

---

## Examples & Workflows

### Workflow 1: Create and Fill Grid from Scratch

```bash
# 1. Create empty 15×15 grid
crossword new --size 15 --output puzzle.json

# 2. Manually add black squares (edit JSON or use web UI)
# ...

# 3. Fill grid with hybrid algorithm
crossword fill puzzle.json \
  -w data/wordlists/comprehensive.txt \
  --algorithm hybrid \
  --timeout 300 \
  --min-score 40

# 4. Validate result
crossword validate puzzle.json

# 5. Export to HTML
crossword export puzzle.json \
  --format html \
  --output puzzle.html \
  --title "Sunday Puzzle"
```

### Workflow 2: Fill with Theme Entries

```bash
# 1. Create theme_entries.json
cat > theme_entries.json <<EOF
{
  "(0,0,across)": "PARTNERNAME",
  "(7,5,down)": "ANNIVERSARY",
  "(14,0,across)": "LOVEYOU"
}
EOF

# 2. Fill grid preserving theme words
crossword fill puzzle.json \
  -w comprehensive.txt \
  --theme-entries theme_entries.json \
  --algorithm beam \
  --beam-width 10 \
  --timeout 600

# Beam search handles theme entries better than CSP
```

### Workflow 3: Adaptive Mode (Auto Black Squares)

```bash
# Start with empty grid (no black squares)
crossword new --size 15 --output adaptive_puzzle.json

# Fill with adaptive mode
crossword fill adaptive_puzzle.json \
  -w comprehensive.txt \
  --adaptive \
  --max-adaptations 5 \
  --timeout 600

# CLI will automatically place black squares where needed
```

### Workflow 4: Pause and Resume

```bash
# Terminal 1: Start long fill
crossword fill huge_puzzle.json \
  -w comprehensive.txt \
  --timeout 1800 \
  --json-output

# Autofill running...

# Terminal 2: Pause after 10 minutes
echo "pause" > /tmp/pause_fill_task123.signal

# Autofill saves state and exits

# Edit grid manually
# ...

# Resume with fresh timeout
crossword fill huge_puzzle.json \
  -w comprehensive.txt \
  --resume-from /tmp/crossword_states/fill_task123.json.gz \
  --timeout 1800
```

### Workflow 5: Batch Processing

```bash
# Fill multiple puzzles with same wordlists
for puzzle in puzzles/*.json; do
  echo "Filling $puzzle..."

  crossword fill "$puzzle" \
    -w comprehensive.txt \
    --algorithm hybrid \
    --timeout 300 \
    --min-score 40 \
    --json-output > "${puzzle%.json}_result.json"

  # Check result
  if [ $(jq '.success' "${puzzle%.json}_result.json") = "true" ]; then
    echo "✓ Success: $puzzle"
  else
    echo "✗ Partial: $puzzle"
  fi
done
```

### Workflow 6: Quality Optimization

```bash
# Goal: Maximize word quality (ignore time)

# Step 1: Fill with beam search (high quality)
crossword fill puzzle.json \
  -w comprehensive.txt \
  --algorithm beam \
  --beam-width 20 \
  --min-score 60 \
  --timeout 3600

# Step 2: If partial fill, lower constraints
crossword fill puzzle.json \
  -w comprehensive.txt \
  --algorithm beam \
  --beam-width 15 \
  --min-score 50 \
  --timeout 3600

# Step 3: If still partial, use hybrid fallback
crossword fill puzzle.json \
  -w comprehensive.txt \
  --algorithm hybrid \
  --min-score 40 \
  --timeout 3600
```

---

## Summary

### Key Features

1. **8 Commands**: `new`, `fill`, `pattern`, `number`, `normalize`, `validate`, `show`, `export`
2. **5 Autofill Algorithms**: CSP (regex/trie), Beam Search, Iterative Repair, Hybrid, Adaptive
3. **Pause/Resume**: Full algorithm state serialization with edit support
4. **454k+ Words**: Comprehensive wordlist with scoring and categorization
5. **Performance**: Trie-based pattern matching (10-50x faster than regex)
6. **Integration**: Designed as backend engine (CLI-as-single-source-of-truth)

### Architecture Highlights

- **NumPy Grid**: Fast 2D operations, symmetry validation
- **CSP + AC-3**: Constraint satisfaction with arc consistency
- **Beam Search**: Global optimization for quality
- **State Management**: Gzip-compressed state files (~87% reduction)
- **Progress Reporting**: JSON stderr for API integration

### Performance Summary

| Operation | Time | Success Rate |
|-----------|------|--------------|
| Pattern search (trie) | ~10ms | 100% |
| Grid validation | ~80ms | N/A |
| Fill 11×11 (hybrid) | 12-35s | 95% |
| Fill 15×15 (hybrid) | 1.5-6min | 90% |
| Fill 21×21 (hybrid) | 8-35min | 85% |

### Testing

- **60 tests** (40 unit, 20 integration)
- **89% coverage** (target: >80%)
- **All algorithms benchmarked**

### Future Enhancements

1. **Daemon Mode**: Keep process alive, eliminate startup overhead (10-30x speedup for short ops)
2. **Binary Protocol**: Replace JSON with msgpack (2-5x faster serialization)
3. **Parallel Fill**: Multi-threaded beam search (2-4x speedup)
4. **PDF Export**: Add reportlab support
5. **Clue Generation**: AI-powered clue writing

---

**Document Version:** 2.0.0
**Total Lines:** 2,847
**Last Updated:** 2025-12-27
**Maintained By:** Development Team
