# Crossword Helper - Master Architecture Document

**Version:** 2.0
**Last Updated:** March 2026
**Status:** Production - All Phases Complete
**Test Coverage:** 165/165 tests passing (100%)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [High-Level Architecture](#high-level-architecture)
4. [Component Breakdown](#component-breakdown)
5. [Data Flow](#data-flow)
6. [Technology Stack](#technology-stack)
7. [Key Architectural Decisions](#key-architectural-decisions)
8. [Security Architecture](#security-architecture)
9. [Performance Characteristics](#performance-characteristics)
10. [Testing Architecture](#testing-architecture)
11. [Deployment Model](#deployment-model)
12. [Advanced Features](#advanced-features)

---

## Executive Summary

The Crossword Helper is a comprehensive crossword puzzle construction toolkit that provides both a web interface and command-line tools for creating, filling, and exporting crossword puzzles. Built progressively over three development phases, the system implements a **CLI-as-single-source-of-truth** architecture where the CLI tool contains all business logic, and the web backend acts as a thin HTTP wrapper around subprocess calls.

### Key Capabilities

- **Interactive Grid Editor** - Web-based crossword grid construction with keyboard shortcuts
- **Intelligent Autofill** - CSP-based and beam search algorithms for automated grid filling
- **Pattern Matching** - Find words matching crossword patterns (e.g., `C?T` → CAT, COT, CUT)
- **Wordlist Management** - 454k+ words across curated collections
- **Pause/Resume** - Interrupt long-running autofill operations and resume with edits
- **Theme Entry Locking** - Preserve specific words during autofill
- **Export Formats** - HTML, JSON, and text grid formats

### Primary Users

- **Expert Constructor** - Technical user creating personalized puzzles
- **Non-Technical Partner** - User who prefers web interface over CLI
- **Development Team** - Maintainers of the codebase

### Design Philosophy

**Progressive Enhancement:**
- Phase 1: Simple web app with immediate utility (3 helper tools)
- Phase 2: Powerful CLI tool with advanced algorithms (CSP autofill)
- Phase 3: Integration for unified codebase (web UI + CLI backend)

**Single Source of Truth:**
- All crossword logic lives in CLI tool
- Web backend delegates to CLI via subprocess calls
- No code duplication between interfaces
- Maximum reusability and maintainability

---

## System Overview

### Three-Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User's Browser                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │  React Frontend (Vite + React 18)                 │  │
│  │  - Grid Editor (interactive crossword UI)         │  │
│  │  - Autofill Panel (algorithm controls)            │  │
│  │  - Wordlist Manager (454k+ words)                 │  │
│  │  - Pattern Matcher (word search)                  │  │
│  └────────────────────┬──────────────────────────────┘  │
└─────────────────────────┼────────────────────────────────┘
                         │ HTTP + Server-Sent Events
                         │ (REST API + real-time progress)
┌────────────────────────▼─────────────────────────────────┐
│            Flask Backend (localhost:5000)                 │
│  ┌───────────────────────────────────────────────────┐  │
│  │  API Layer (Flask Routes)                         │  │
│  │  - 6 blueprints, 20+ endpoints                    │  │
│  │  - Request validation                             │  │
│  │  - SSE progress streaming                         │  │
│  │  - Error handling                                 │  │
│  └─────────────────────┬─────────────────────────────┘  │
│                        │ delegates to                     │
│  ┌─────────────────────▼─────────────────────────────┐  │
│  │  CLIAdapter (Subprocess Manager)                  │  │
│  │  - Executes CLI commands via subprocess           │  │
│  │  - Parses JSON output                             │  │
│  │  - Handles timeouts, errors                       │  │
│  │  - ~100-300ms overhead per request                │  │
│  └─────────────────────┬─────────────────────────────┘  │
└────────────────────────┼─────────────────────────────────┘
                         │ subprocess.run()
                         │ (stdin/stdout JSON communication)
┌────────────────────────▼─────────────────────────────────┐
│          CLI Tool (Python - Single Source of Truth)       │
│  ┌───────────────────────────────────────────────────┐  │
│  │  CLI Commands (Click framework - 8 commands)      │  │
│  │  - new, fill, pattern, number, normalize, etc.    │  │
│  └─────────────────────┬─────────────────────────────┘  │
│                        │                                  │
│  ┌─────────────────────▼─────────────────────────────┐  │
│  │  Core Modules (Business Logic)                    │  │
│  │  ├─ Grid Engine (grid.py, numbering.py)          │  │
│  │  ├─ Autofill Engine (CSP + Beam Search)          │  │
│  │  ├─ Pattern Matcher (Regex + Trie + AC)          │  │
│  │  ├─ Word List Manager (454k+ words)              │  │
│  │  └─ Export Engine (HTML, JSON, text)             │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│                External Resources                         │
│  - Word lists (data/wordlists/*.txt)                     │
│  - State files (pause/resume persistence)                │
│  - Progress files (real-time status)                     │
└───────────────────────────────────────────────────────────┘
```

### Integration Pattern: CLI as Backend

The key architectural innovation is that the CLI tool is not a separate application—it IS the backend. The Flask API routes are thin HTTP wrappers that:

1. Validate HTTP requests
2. Call CLI commands via subprocess
3. Parse CLI JSON output
4. Return HTTP responses

This eliminates code duplication while providing dual interfaces (web + CLI) from a single codebase.

---

## High-Level Architecture

### Component Relationships

```
Frontend (React)
    │
    ├─ GridEditor ──────────► POST /api/grid/update
    ├─ AutofillPanel ───────► POST /api/fill (SSE for progress)
    ├─ PatternMatcher ──────► POST /api/pattern
    ├─ WordlistManager ─────► GET /api/wordlists
    └─ ThemePlacer ─────────► POST /api/theme/place
                              │
                              ▼
Backend API (Flask)
    │
    ├─ routes.py ───────────► /api/pattern, /api/number, /api/normalize
    ├─ grid_routes.py ──────► /api/grid/* (update, suggest)
    ├─ pause_resume_routes.py ─► /api/fill/pause, /api/fill/resume
    ├─ theme_routes.py ─────► /api/theme/* (place, lock)
    ├─ wordlist_routes.py ──► /api/wordlists/* (list, upload)
    └─ progress_routes.py ──► /api/progress/:task_id (SSE stream)
                              │
                              ▼
CLI Adapter (backend/core/cli_adapter.py)
    │
    ├─ pattern() ───────────► crossword pattern "C?T" --json-output
    ├─ number() ────────────► crossword number grid.json
    ├─ fill() ──────────────► crossword fill grid.json --algorithm hybrid
    ├─ normalize() ─────────► crossword normalize "Tina Fey"
    └─ fill_with_resume() ──► crossword fill --resume-from state.json.gz
                              │
                              ▼
CLI Tool (cli/src/cli.py - 8 commands, 903 lines)
    │
    ├─ new ─────────────────► Create empty grid
    ├─ fill ────────────────► Autofill grid (CSP/Beam/Hybrid)
    ├─ pattern ─────────────► Search for matching words
    ├─ number ──────────────► Auto-number grid
    ├─ normalize ───────────► Normalize entry conventions
    ├─ validate ────────────► Validate grid constraints
    ├─ wordlists ───────────► Manage word lists
    └─ export ──────────────► Export to HTML/JSON
                              │
                              ▼
Core Modules (Single Source of Truth)
    │
    ├─ Grid (grid.py) ──────────────► 2D array, symmetry, constraints
    ├─ Autofill (autofill.py) ──────► CSP with backtracking + AC-3
    ├─ BeamSearch (orchestrator.py) ► Global optimization search
    ├─ PatternMatcher (3 algorithms) ► Regex, Trie, Aho-Corasick
    ├─ WordList (word_list.py) ─────► 454k+ words, scoring
    ├─ GridNumbering (numbering.py) ► Auto-numbering algorithm
    └─ StateManager (state_manager.py) ► Pause/resume persistence
```

### Data Formats

**Grid Representation (JSON):**
```json
{
  "size": 15,
  "grid": [
    ["H", "E", "L", "L", "O", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
    ["#", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
    ...
  ],
  "theme_entries": {
    "0-ACROSS-0": ["H", "E", "L", "L", "O"]
  },
  "black_squares": [[1, 0], [14, 14]]
}
```

**Word List Format (TSV):**
```
WORD         SCORE  SOURCE
HELLO        85     comprehensive
CROSSWORD    90     comprehensive
```

**Pattern Format:**
- `?` = any letter wildcard
- `[A-Z]` = specific letter
- Examples: `?I?A`, `RE??`, `C?T`

---

## Component Breakdown

### 4.1 Frontend (React + Vite)

**Location:** `/src/`
**Technology:** React 18, Vite 5, SCSS, Server-Sent Events
**Purpose:** Web-based user interface for crossword construction

#### Key Components

**GridEditor.jsx** (~500 lines)
- Interactive crossword grid rendering
- Keyboard navigation (arrows, Tab, Backspace)
- Mouse interactions (click to edit, Shift+Click for black squares)
- Right-click context menu for theme locking
- Symmetry enforcement (visual feedback)
- Auto-numbering display
- Cell highlighting (selected, crossing word, errors)

**AutofillPanel.jsx** (~400 lines)
- Algorithm selection (Regex, Trie, Beam Search, Hybrid)
- Wordlist selection (comprehensive, 3-letter, crosswordese, etc.)
- Parameter controls (timeout, min score, beam width)
- Start/Pause/Resume buttons
- Real-time progress display via SSE
- Fill statistics (iterations, slots filled, time elapsed)
- Error display for problematic slots

**WordlistPanel.jsx** (~300 lines)
- Browse 454k+ words across categories
- Upload custom wordlists (.txt files)
- View statistics (word count, length distribution)
- Add individual words to existing lists
- Search/filter functionality

**ThemePlacer.jsx** (~200 lines)
- Input theme words (one per line)
- Suggest optimal placements
- Lock/unlock theme entries
- Visual indicators for locked words

**PatternMatcher.jsx** (~150 lines)
- Pattern input with wildcard support
- Real-time results display
- Word score visualization
- Source indication (which wordlist matched)

#### State Management

**App.jsx** - Centralized state
- Grid state (2D array)
- Theme entries (locked words)
- Autofill status (idle, running, paused, complete, error)
- Task tracking (current fill task ID)
- Progress tracking (SSE stream handling)

**localStorage Persistence:**
- Grid state cached for browser refresh recovery
- Paused task IDs persisted
- User preferences (default wordlists, algorithm)

#### API Integration

- Axios for HTTP requests
- EventSource for Server-Sent Events (progress streaming)
- Automatic retry on connection failure
- Toast notifications for user feedback

---

### 4.2 Backend API (Flask)

**Location:** `/backend/`
**Technology:** Flask 3.0, Flask-CORS, Python 3.9+
**Purpose:** HTTP wrapper around CLI tool, thin API layer

#### Architecture Layers

**API Layer** (backend/api/)
- 6 Flask blueprints
- 20+ RESTful endpoints
- Request validation (validators.py)
- Error handling (errors.py)
- CORS configuration (localhost origins)

**Core Layer** (backend/core/)
- CLIAdapter: Subprocess execution manager
- EditMerger: Grid edit validation and merging
- ThemePlacer: Theme word placement suggestions
- BlackSquareSuggester: Strategic black square recommendations
- WordlistResolver: Wordlist path resolution

**Data Layer** (backend/data/)
- Wordlist file management
- Progress file I/O (for SSE streaming)
- State file management (pause/resume)

#### API Endpoints

**Core Endpoints** (routes.py)
- `GET /api/health` - Health check (includes CLI status)
- `POST /api/pattern` - Pattern search (delegates to CLI)
- `POST /api/number` - Grid numbering (delegates to CLI)
- `POST /api/normalize` - Convention normalization (delegates to CLI)
- `POST /api/fill` - Autofill grid (async via CLI subprocess)

**Grid Endpoints** (grid_routes.py)
- `POST /api/grid/update` - Update grid cells
- `POST /api/grid/suggest-black-squares` - Suggest strategic placement
- `POST /api/grid/validate` - Validate grid constraints

**Theme Endpoints** (theme_routes.py)
- `POST /api/theme/place` - Place theme words with suggestions
- `POST /api/theme/lock` - Lock/unlock theme entries
- `GET /api/theme/analyze` - Analyze theme word compatibility

**Pause/Resume Endpoints** (pause_resume_routes.py)
- `POST /api/fill/pause` - Pause running autofill
- `POST /api/fill/resume` - Resume paused autofill with edits
- `GET /api/fill/states` - List available paused states
- `GET /api/fill/state/:id` - Get specific state details
- `POST /api/fill/state/:id/edit-summary` - Analyze user edits
- `DELETE /api/fill/state/:id` - Delete saved state

**Wordlist Endpoints** (wordlist_routes.py)
- `GET /api/wordlists` - List available wordlists
- `POST /api/wordlists/upload` - Upload custom wordlist
- `GET /api/wordlists/:name/stats` - Get wordlist statistics
- `POST /api/wordlists/:name/add-word` - Add word to list

**Progress Endpoints** (progress_routes.py)
- `GET /api/progress/:task_id` - SSE stream for real-time progress

#### CLIAdapter: The Integration Bridge

**File:** `backend/core/cli_adapter.py` (~400 lines)

**Core Responsibility:** Execute CLI commands via subprocess and parse results

**Key Methods:**

```python
class CLIAdapter:
    def pattern(pattern, wordlist_paths, max_results, algorithm):
        """
        Execute: crossword pattern "C?T" --json-output
        Returns: {"results": [{"word": "CAT", "score": 85}, ...]}
        """

    def number(grid_data):
        """
        Execute: crossword number grid.json
        Returns: {"numbering": {...}, "validation": {...}}
        """

    def fill(grid_data, wordlists, timeout, min_score, algorithm):
        """
        Execute: crossword fill grid.json --algorithm hybrid
        Async execution with progress file monitoring
        Returns: Task ID for progress tracking
        """

    def fill_with_resume(state_file, grid_edits):
        """
        Execute: crossword fill --resume-from state.json.gz
        Merges user edits and resumes from exact algorithmic position
        Returns: Task ID for progress tracking
        """
```

**Subprocess Management:**
- Timeout handling (configurable per command)
- Error parsing (stderr → HTTP error codes)
- JSON communication (stdin/stdout)
- Working directory management
- Process cleanup

**Performance Optimization:**
- LRU cache for pattern searches (100-entry cache)
- Async subprocess execution for long-running fills
- Progress file monitoring (no blocking)

---

### 4.3 CLI Tool (Python Click)

**Location:** `/cli/src/`
**Technology:** Click, NumPy, Python 3.9+
**Purpose:** Single source of truth for all crossword logic

#### Command Structure

**File:** `cli/src/cli.py` (1,347 lines, 13 commands)

**Commands:**

1. **new** - Create empty grid
   ```bash
   crossword new --size 15 --output puzzle.json
   ```

2. **fill** - Autofill grid with CSP/Beam Search/Hybrid
   ```bash
   crossword fill puzzle.json \
     --algorithm hybrid \
     --wordlists comprehensive.txt \
     --timeout 300 \
     --min-score 30 \
     --resume-from state.json.gz  # Optional: resume paused fill
   ```

3. **pattern** - Search for words matching pattern
   ```bash
   crossword pattern "C?T" \
     --wordlists comprehensive.txt \
     --max-results 20 \
     --algorithm trie \
     --json-output
   ```

4. **number** - Auto-number grid
   ```bash
   crossword number puzzle.json --json-output
   ```

5. **normalize** - Normalize entry conventions
   ```bash
   crossword normalize "Tina Fey" --json-output
   # Output: {"original": "Tina Fey", "normalized": "TINAFEY"}
   ```

6. **validate** - Validate grid against NYT standards
   ```bash
   crossword validate puzzle.json
   ```

7. **export** - Export puzzle to HTML/JSON
   ```bash
   crossword export puzzle.json --format html --output puzzle.html
   ```

8. **show** - Display grid in terminal
   ```bash
   crossword show puzzle.json --format pretty
   ```

9. **build-cache** - Pre-build wordlist cache (.pkl)
   ```bash
   crossword build-cache comprehensive.txt --output comprehensive.pkl
   ```

10. **pause** - Signal a running autofill to pause
    ```bash
    crossword pause <task-id> --json-output
    ```

11. **resume** - Resume a paused autofill with optional edits
    ```bash
    crossword resume state.json.gz --edited-grid edited.json \
      --wordlists comprehensive.txt --timeout 300
    ```

12. **list-states** - List saved pause/resume states
    ```bash
    crossword list-states --json-output --sort-by date
    ```

#### Core Modules

**Grid Engine** (`cli/src/core/`)

- `grid.py` - Grid data structure (NumPy array), cell operations
- `numbering.py` - Auto-numbering algorithm (across/down slot detection)
- `validator.py` - Constraint validation (symmetry, connectivity, min word length)
- `conventions.py` - Entry normalization rules (multi-word, punctuation)
- `scoring.py` - Word quality scoring algorithms
- `cell_types.py` - Cell state enumeration (empty, letter, black)
- `progress.py` - Progress tracking for long operations

**Autofill Engines** (`cli/src/fill/`)

Four algorithm implementations with different trade-offs:

1. **CSP with Backtracking + MAC** (`autofill.py`, 1,248 lines)
   - Constraint Satisfaction Problem with AC-3 arc consistency
   - MAC (Maintaining Arc Consistency) during backtracking
   - Most Constrained Variable (MCV) heuristic for slot ordering
   - Least Constraining Value (LCV) with two-tier scoring:
     - Fast: pre-computed letter frequency table (O(1) estimates)
     - Accurate: counts exact remaining options (top 100 candidates)
   - Forward checking after each placement
   - Stratified sampling for large domains (>10,000 words)
   - Guaranteed solution if one exists
   - Fast for small grids (11×11 < 30s)

2. **Beam Search** (`fill/beam_search/`, 19 files across 6 subpackages)
   - **Orchestrator pattern** (`orchestrator.py`, 1,100 lines) coordinates:
     - `MRVSlotSelector` (selection/slot_selector.py) — Minimum Remaining Values
     - `MACConstraintEngine` (constraints/engine.py) — Constraint propagation
     - `CompositeValueOrdering` (selection/value_ordering.py) — Chained ordering pipeline:
       - ThemeWordPriorityOrdering → LCVValueOrdering → ThresholdDiverseOrdering → StratifiedValueOrdering
     - `DiversityManager` (beam/diversity.py) — Diverse Beam Search (Vijayakumar et al. 2016)
     - `BeamManager` (beam/manager.py) — Beam expansion and pruning
     - `StateEvaluator` (evaluation/state_evaluator.py) — Predictive risk assessment
     - Memory management (memory/domain_manager.py, grid_snapshot.py, pools.py)
   - Maintains top-k parallel solutions (beam width, default: 5)
   - Predictive risk scoring penalizes constrained crossings (0.70×–1.0×)
   - Dead end recovery: conflict-directed backjumping + escalating retries
   - Better word quality than CSP
   - Good for medium grids (15×15, 1-5min)

3. **Hybrid Algorithm** (`hybrid_autofill.py`, 191 lines) — **default**
   - **Phase 1 — Beam Search** (20% of timeout, max 60s): Global exploration
   - **Phase 2 — Iterative Repair** (80% of remaining): Fixes crossing mismatches
   - Returns better of beam vs. repair result
   - Best all-around performance

4. **Iterative Repair** (`iterative_repair.py`, 1,919 lines)
   - Region-based conflict detection and resolution
   - Multi-pass greedy fill with gibberish detection
   - **Tabu search** for local optimization (tenure = √num_slots)
   - Used as Phase 2 in Hybrid algorithm

5. **Adaptive Autofill** (`adaptive_autofill.py`, 415 lines)
   - Wrapper that monitors autofill progress
   - Auto-detects stuck situations (thrashing, stagnation)
   - Suggests strategic black square placements via `BlackSquareSuggester`
   - Max 3 adaptations per session, only for slots ≥6 letters

> **For detailed algorithm analysis:** See [ALGORITHM_DEEP_DIVE.md](./ALGORITHM_DEEP_DIVE.md)

**Pattern Matching** (`cli/src/fill/`)

Three implementations with different performance characteristics:

1. **Regex Matcher** (`pattern_matcher.py`)
   - Converts `C?T` → regex `^C.T$`, length-filtered
   - ~200-500ms per query on 454k words
   - LRU cache for repeated patterns

2. **Trie Matcher** (`trie_pattern_matcher.py` + `word_trie.py`)
   - Length-indexed tries (separate trie per word length 3–21)
   - Score-based subtree pruning via min/max bounds per node
   - Wildcard `?` branches to all children simultaneously
   - 10-50x faster than regex (~10-50ms per query)
   - Build time: ~2-3s for 454k words
   - **Default for autofill algorithms**

3. **Aho-Corasick** (`ahocorasick_matcher.py`)
   - Separate automaton per word length
   - 10-100x faster than regex (~1-20ms per query)
   - Requires `pyahocorasick` library (optional; falls back to Trie)

**Word List Manager** (`cli/src/fill/word_list.py`)

- Loads word lists from TSV files
- Supports multiple sources (comprehensive, themed, custom)
- Scoring and filtering by quality threshold
- Deduplication across lists
- Statistics (word count, length distribution)

**State Management** (`cli/src/fill/state_manager.py`)

- Serializes complete algorithm state (CSP or Beam Search)
- Gzip compression (~80% size reduction)
- State lifecycle management (creation, cleanup)
- Resume from exact algorithmic position

**Pause Controller** (`cli/src/fill/pause_controller.py`)

- File-based IPC for pause signaling
- Rate-limited checking (<0.1% overhead)
- Cross-platform compatible (Unix + Windows)

**Export Engine** (`cli/src/export/`)

- `html_exporter.py` - Generate printable HTML grids
- `json_exporter.py` - JSON state persistence
- Grid formatting (blank, solution, clues)

---

## Data Flow

### 5.1 Grid Creation Flow

```
1. User opens web interface
   └─► App.jsx loads with empty grid

2. User clicks cells to add letters/black squares
   ├─► GridEditor.jsx updates local state
   ├─► Symmetry enforced (auto-add opposite black square)
   └─► Auto-numbering triggered

3. User locks theme entries (right-click)
   └─► POST /api/theme/lock
       └─► Updates theme_entries in grid state

4. Grid state persisted
   ├─► localStorage (browser cache)
   └─► Backend state (for autofill)
```

### 5.2 Autofill Process (Detailed)

```
1. User clicks "Start Autofill" button
   └─► AutofillPanel.jsx gathers parameters
       ├─ Algorithm: "hybrid"
       ├─ Wordlists: ["comprehensive"]
       ├─ Timeout: 300s
       ├─ Min Score: 30
       └─ Theme entries: locked words

2. POST /api/fill request
   └─► Flask routes.py receives request
       └─► validate_fill_request(data)
           ├─ Check grid format
           ├─ Validate parameters
           └─ Resolve wordlist paths

3. CLIAdapter.fill() creates subprocess
   └─► Builds CLI command:
       crossword fill /tmp/grid_abc123.json \
         --algorithm hybrid \
         --wordlists /data/wordlists/comprehensive.txt \
         --timeout 300 \
         --min-score 30 \
         --progress-file /tmp/progress_abc123.json \
         --json-output

4. CLI subprocess executes
   ├─► Load grid from JSON
   ├─► Load wordlists (454k words into trie)
   ├─► Initialize Beam Search orchestrator
   ├─► Start filling loop:
   │   ├─ Select unfilled slot (MCV heuristic)
   │   ├─ Pattern match: get candidate words
   │   ├─ Score candidates (LCV heuristic)
   │   ├─ Try top candidate
   │   ├─ Update beam (keep top-k solutions)
   │   ├─ Check constraints (AC-3)
   │   ├─ Write progress to file (every 100 iterations)
   │   └─ Check for pause signal
   └─► Return filled grid or error

5. Backend monitors progress file
   └─► progress_routes.py streams SSE events:
       data: {"status": "running", "iterations": 500, "slots_filled": 42}

6. Frontend updates UI in real-time
   └─► AutofillPanel.jsx receives SSE events
       ├─ Update progress bar
       ├─ Show iteration count
       └─ Display time elapsed

7. Fill completes
   ├─► SUCCESS: Grid filled, return filled grid
   │   └─► Frontend: Display filled grid, update state
   │
   └─► FAILURE: Return problematic slots
       └─► Frontend: Highlight unfillable regions, suggest fixes
```

### 5.3 Pause/Resume Flow

```
1. User clicks "Pause" during autofill
   └─► POST /api/fill/pause
       └─► Write pause signal file
           └─► CLI detects pause (next check)
               └─► Serialize algorithm state
                   ├─ Grid state
                   ├─ Algorithm position (backtrack stack or beam)
                   ├─ Candidate lists
                   ├─ Constraint propagation state
                   └─ Iteration count
               └─► Write state.json.gz (gzip compressed)
               └─► Exit with "paused" status

2. User edits grid manually
   ├─► GridEditor.jsx: add/remove/change letters
   └─► Changes stored in local state

3. User clicks "Resume Autofill"
   └─► POST /api/fill/resume
       ├─ Send paused state ID
       ├─ Send grid edits (diff from paused grid)
       └─► Backend: EditMerger validates edits
           ├─ Run AC-3 constraint propagation
           ├─ Check for unsolvable constraints
           └─ Lock user edits (treat as theme entries)

4. CLIAdapter.fill_with_resume() executes
   └─► crossword fill --resume-from state.json.gz \
         --edits edits.json \
         --timeout 300  # Fresh timeout!

5. CLI loads saved state + applies edits
   ├─► Deserialize algorithm state
   ├─► Apply user edits to grid
   ├─► Mark edited slots as locked
   ├─► Resume from exact position
   └─► Continue filling (new timeout window)

6. Fill continues with edits locked
   └─► Autofill treats edited cells like theme entries
       └─► Cannot change during remainder of fill
```

### 5.4 Pattern Search Flow

```
1. User types pattern "C?T" in PatternMatcher
   └─► POST /api/pattern
       └─► CLIAdapter.pattern() executes:
           crossword pattern "C?T" \
             --wordlists comprehensive.txt \
             --max-results 20 \
             --algorithm trie \
             --json-output

2. CLI Pattern Matcher
   ├─► Load comprehensive wordlist into trie (cached)
   ├─► Traverse trie matching pattern
   │   ├─ 'C' (fixed)
   │   ├─ '?' (any letter A-Z)
   │   └─ 'T' (fixed)
   ├─► Score matches (word quality algorithm)
   └─► Return top 20 results

3. Results returned as JSON
   {
     "results": [
       {"word": "CAT", "score": 90, "source": "comprehensive"},
       {"word": "COT", "score": 75, "source": "comprehensive"},
       {"word": "CUT", "score": 85, "source": "comprehensive"},
       ...
     ],
     "meta": {
       "total_found": 127,
       "query_time_ms": 12
     }
   }

4. Frontend displays results
   └─► PatternMatcher.jsx renders table
       └─► Sorted by score, color-coded
```

---

## Technology Stack

### 6.1 Backend Stack

| Component | Choice | Version | Rationale |
|-----------|--------|---------|-----------|
| **Language** | Python | 3.9+ | Expert familiarity, rich ecosystem, numpy support |
| **Web Framework** | Flask | 3.0+ | Simpler than FastAPI for synchronous subprocess calls |
| **CLI Framework** | Click | 8.1+ | Rich features, excellent composability, typing support |
| **Array Operations** | NumPy | 1.24+ | Fast 2D grid operations, symmetry validation |
| **Pattern Matching** | Regex + Custom Trie | Built-in + Custom | Regex for simplicity, Trie for 10-50x speedup |
| **Testing** | pytest | 7.4+ | Industry standard, excellent fixtures, 165 tests |
| **CORS** | Flask-CORS | 4.0+ | Enable React dev server communication |

**Not Using:**
- **FastAPI**: Async unnecessary (subprocess I/O, not high concurrency)
- **Django**: Too heavy for API wrapper around CLI
- **SQLAlchemy**: No database (file-based state, JSON grids)

### 6.2 Frontend Stack

| Component | Choice | Version | Rationale |
|-----------|--------|---------|-----------|
| **UI Framework** | React | 18+ | Component reusability, modern hooks, large ecosystem |
| **Build Tool** | Vite | 5+ | Fast HMR, optimized builds, modern ESM |
| **Styling** | SCSS | - | Variables, nesting, mixins for complex grid styles |
| **HTTP Client** | Axios | 1.6+ | Interceptors, better error handling than fetch |
| **Real-Time** | EventSource | Native | SSE for progress streaming, simpler than WebSocket |

**Not Using:**
- **Vue/Angular**: React chosen for component model and familiarity
- **TypeScript**: Adds build complexity, diminishing returns for this project size
- **CSS-in-JS**: SCSS sufficient for grid layout needs
- **Redux**: React Context + local state sufficient for app size

### 6.3 Data Storage

| Type | Solution | Rationale |
|------|----------|-----------|
| **Word Lists** | TSV files | Human-editable, version-controllable, simple parsing |
| **Grid State** | JSON files | Universal format, easy debugging, CLI/web compatible |
| **Pause States** | Gzipped JSON | Compressed for large algorithm states (~80% reduction) |
| **Progress Files** | JSON | Real-time updates, SSE streaming source |
| **User Uploads** | Filesystem | No database overhead, direct file access |

**Why No Database:**
- Local-only deployment (no multi-user)
- File-based simpler for single-user workflows
- Version control friendly (git wordlists)
- Easy backup/restore (copy files)
- Future migration path exists if needed

### 6.4 Algorithms

| Algorithm | Purpose | Complexity | Trade-offs |
|-----------|---------|------------|------------|
| **CSP + Backtracking** | Autofill (guaranteed solution) | O(b^d) worst case | Completeness vs speed |
| **Beam Search** | Autofill (quality optimization) | O(k·n) beam width | Quality vs guarantees |
| **AC-3** | Constraint propagation | O(ed³) edges/domain | Early pruning vs overhead |
| **Trie** | Pattern matching | O(m) pattern length | Speed vs memory |
| **Aho-Corasick** | Batch pattern matching | O(n+m+z) automaton | Batch speed vs build time |

---

## Key Architectural Decisions

### 7.1 CLI as Single Source of Truth

**Decision:** All business logic in CLI tool, web backend as thin wrapper

**Rationale:**
- ✅ **No Code Duplication**: One implementation, two interfaces
- ✅ **Easy Testing**: Test logic once, both interfaces benefit
- ✅ **Maintainability**: Changes apply to both web and CLI
- ✅ **Reusability**: CLI tool standalone utility, web optional
- ✅ **Clear Separation**: HTTP concerns separate from crossword logic

**Trade-offs:**
- ❌ **Subprocess Overhead**: ~100-300ms per request (acceptable for this use case)
- ❌ **JSON Serialization**: Grid must be serializable (not a problem for our data)
- ❌ **Error Propagation**: Must parse stderr, map to HTTP codes

**Why This Works:**
- Operations are infrequent (not high-throughput API)
- User tolerance for 100ms delay is high (perceived as instant)
- Autofill already takes 30s-5min (subprocess overhead insignificant)
- Debugging easier (can test CLI commands directly)

**Alternative Considered:** Direct Python imports from CLI
- ❌ Coupling between web and CLI code
- ❌ Shared state management complexity
- ❌ Testing requires both components together

### 7.2 Subprocess-Based Integration

**Decision:** Use `subprocess.run()` to execute CLI commands

**Implementation:**
```python
result = subprocess.run(
    ['crossword', 'pattern', 'C?T', '--json-output'],
    capture_output=True,
    text=True,
    timeout=30,
    cwd=cli_directory
)
output = json.loads(result.stdout)
```

**Security Considerations:**
- ✅ No shell=True (no shell injection)
- ✅ Validated input before subprocess call
- ✅ Timeout enforcement (prevent runaway processes)
- ✅ Working directory control (no path traversal)
- ✅ Fixed CLI path (no user-controlled executable)

**Error Handling:**
- TimeoutExpired → HTTP 504
- CalledProcessError → HTTP 500 (with stderr message)
- JSONDecodeError → HTTP 500 (CLI output format error)

### 7.3 Flask over FastAPI

**Decision:** Use Flask for web backend

**Rationale:**
- ✅ Synchronous model fits subprocess I/O pattern
- ✅ Simpler for low-concurrency local tool (1-2 users)
- ✅ Mature ecosystem (Flask-CORS, blueprints)
- ✅ Easier deployment (no async complications)

**Not Needed:**
- ❌ FastAPI async benefits (subprocess calls block anyway)
- ❌ Auto-generated OpenAPI docs (single-user tool)
- ❌ Pydantic validation (manual validation sufficient)

**When to Reconsider:**
- If deploying to cloud with 100+ concurrent users
- If adding non-blocking I/O operations (database, external APIs)
- If wanting auto-generated API documentation

### 7.4 React over Vanilla JS

**Decision:** Use React for frontend (changed from Phase 1 plan)

**Rationale:**
- ✅ Grid editor complexity (keyboard nav, symmetry, theme locking)
- ✅ SSE integration easier with hooks (useEffect)
- ✅ Component reusability (GridEditor, AutofillPanel, etc.)
- ✅ State management cleaner (useState, useContext)

**Original Plan:** Vanilla JS for "only 3 components"

**Reality:** 20+ components once feature-complete
- GridEditor, AutofillPanel, PatternMatcher, WordlistPanel
- ThemePlacer, BlackSquareSuggester, ProgressBar, ToastNotifications
- Modals, Tabs, Tooltips, ContextMenus

**Trade-off Accepted:**
- ❌ Build step required (npm run build)
- ❌ Larger bundle size (~500KB vs ~50KB)
- ✅ Development speed 3x faster (components, state, hooks)
- ✅ User experience significantly better (reactive UI)

### 7.5 NumPy for Grid Operations

**Decision:** Use NumPy arrays for grid representation

**Rationale:**
- ✅ Fast array operations (critical for autofill)
- ✅ Built-in matrix operations (rotation for symmetry check)
- ✅ Memory-efficient for large grids (21×21)
- ✅ Vectorized operations reduce code complexity

**Implementation:**
```python
grid = np.zeros((15, 15), dtype=int)
# -1 = black square, 0 = empty, 1-26 = letters A-Z

# Symmetry check (180° rotation)
is_symmetric = np.array_equal(grid == -1, np.rot90(grid == -1, 2))
```

**Alternative Considered:** Plain 2D Python lists
- ✅ Simpler, no dependencies
- ❌ Slower for repeated access (10-100x in tight loops)
- ❌ More complex symmetry validation code

### 7.6 Pause/Resume Architecture

**Decision:** File-based IPC for pause signaling, state serialization for resume

**Rationale:**
- ✅ Cross-platform (Unix + Windows)
- ✅ No threading complexity (subprocess is separate process)
- ✅ Persistent across browser refresh
- ✅ Debugging easier (can inspect state files)

**Implementation:**
- Pause: Write `/tmp/pause_<task_id>.signal` file
- CLI checks for file every 100 iterations (~0.1% overhead)
- State saved as gzipped JSON (~1-5MB compressed)
- Resume: Load state, apply edits, continue from exact position

**Alternative Considered:** In-memory state with threading
- ❌ Doesn't survive browser refresh
- ❌ Threading complexity in Flask
- ❌ Can't inspect state for debugging

### 7.7 Hybrid Autofill Algorithm

**Decision:** Default to hybrid (Beam Search → Iterative Repair)

**Rationale:**
- ✅ Beam Search finds high-quality partial fills (better words, global optimization)
- ✅ Iterative Repair fixes crossing mismatches via targeted word swaps (tabu search)
- ✅ Two-phase approach: exploration (20% time) + refinement (80% time)
- ✅ User can override if needed (--algorithm flag)

**Two-Phase Strategy:**
- Phase 1: Beam Search (20% of timeout, max 60s) — global exploration
- Phase 2: Iterative Repair (remaining time) — conflict resolution via region-based fill + tabu search

**Performance:**
- 11×11: <30s (Beam Search sufficient)
- 15×15: 1-5min (Hybrid best)
- 21×21: 5-30min (Iterative Repair critical for conflict resolution)

**Word Quality:**
- Beam Search average score: 75/100
- CSP average score: 65/100
- Hybrid average score: 72/100

---

## Security Architecture

### 8.1 Threat Model

**In Scope:**
- Local development environment (localhost)
- Trusted users (expert + partner)
- Private network (no internet exposure)

**Out of Scope:**
- Public internet deployment (future consideration)
- Multi-tenant authentication
- SQL injection (no database)
- Stored XSS (no user-generated HTML)

### 8.2 Input Validation

**API Layer Validation** (validators.py)

```python
def validate_pattern_request(data):
    """Validate pattern search request."""
    if not data.get('pattern'):
        raise ValueError("Pattern required")

    pattern = data['pattern']

    # Length limits (prevent DoS)
    if len(pattern) > 50:
        raise ValueError("Pattern too long (max 50)")

    # Character whitelist (prevent injection)
    if not re.match(r'^[A-Z?]+$', pattern):
        raise ValueError("Pattern must be uppercase letters and ?")

    # Max results limit
    max_results = data.get('max_results', 20)
    if max_results > 1000:
        raise ValueError("Max results too large (max 1000)")

    return data
```

**Grid Validation:**
- Size limits (min 3×3, max 50×50)
- Cell value validation (empty, letter, black square only)
- JSON depth limits (prevent nested object attacks)

**File Upload Validation:**
- Extension whitelist (.txt only)
- Size limits (max 10MB)
- Content validation (must be valid word list format)
- Path traversal protection (sanitize filenames)

### 8.3 Subprocess Security

**Command Injection Prevention:**

```python
# ✅ SAFE: Array of arguments (no shell interpretation)
subprocess.run(['crossword', 'pattern', user_pattern])

# ❌ UNSAFE: String command with shell=True
subprocess.run(f"crossword pattern {user_pattern}", shell=True)
```

**Path Traversal Protection:**

```python
# Validate CLI path is within project directory
cli_path = Path(cli_path).resolve()
project_root = Path(__file__).parent.parent.resolve()
if not cli_path.is_relative_to(project_root):
    raise SecurityError("CLI path outside project")
```

**Timeout Enforcement:**
- All subprocess calls have timeout (default 30s)
- Autofill timeout user-configurable (max 10min)
- Prevents resource exhaustion

### 8.4 CORS Configuration

**Allowed Origins:**
```python
CORS(app, origins=[
    'http://localhost:5000',    # Flask server
    'http://127.0.0.1:5000',
    'http://localhost:3000',    # React dev server
    'http://127.0.0.1:3000'
])
```

**Why Restrictive:**
- Prevents accidental public exposure
- Blocks cross-origin attacks if deployed
- Explicit whitelist (no wildcards)

### 8.5 File System Security

**Temporary File Handling:**
- Use Python `tempfile` module (secure temp file creation)
- Cleanup after subprocess execution
- Restricted permissions (user-only read/write)

**Wordlist Storage:**
- Read-only directory for built-in lists
- User uploads in separate directory (data/wordlists/custom/)
- No executable permissions on uploaded files

**State File Storage:**
- Short-lived (deleted after 7 days)
- User-specific (task ID includes timestamp)
- No sensitive data (grid state only)

---

## Performance Characteristics

### 9.1 API Response Times

| Endpoint | Target | Typical | Notes |
|----------|--------|---------|-------|
| `/api/health` | <50ms | 30ms | No CLI call, just status check |
| `/api/pattern` | <1s | 150-300ms | CLI overhead + trie search |
| `/api/number` | <200ms | 120-180ms | CLI overhead + numbering algorithm |
| `/api/normalize` | <100ms | 90-120ms | CLI overhead + string operations |
| `/api/fill` (start) | <500ms | 200-400ms | Just spawns subprocess, returns task ID |
| `/api/fill` (complete) | 30s-5min | Varies | Actual autofill time |

**Subprocess Overhead Breakdown:**
- Process spawn: 50-100ms
- JSON serialization: 10-50ms (grid size dependent)
- CLI startup: 50-100ms (Python interpreter + imports)
- JSON parsing: 10-30ms
- **Total:** 120-280ms average

**Optimization Opportunities:**
- Keep CLI process alive (daemon mode) - reduces startup overhead
- Pre-load wordlists (warm cache) - eliminates load time
- Binary protocol instead of JSON - 2-5x faster serialization

### 9.2 Autofill Performance

**11×11 Grid:**
- CSP: 10-30s (typical)
- Beam Search: 15-45s
- Hybrid: 12-35s

**15×15 Grid:**
- CSP: 1-5min (typical), can timeout on hard grids
- Beam Search: 2-8min
- Hybrid: 1.5-6min (best consistency)

**21×21 Grid:**
- CSP: 5-30min (often requires high min_score)
- Beam Search: 10-45min
- Hybrid: 8-35min

**Factors Affecting Performance:**
- **Pre-filled cells**: More pre-fill = faster (constraints guide search)
- **Theme entries**: Locked words constrain search (slight slowdown)
- **Min score threshold**: Higher threshold = fewer candidates = faster
- **Wordlist size**: 454k words vs 50k words = 2-3x slower
- **Grid connectivity**: More isolated regions = harder to fill

**Iteration Counts (15×15):**
- Fast fill: 500-2000 iterations
- Average fill: 2000-10000 iterations
- Hard fill: 10000-50000 iterations
- Timeout: 100000+ iterations (unfillable or needs different params)

### 9.3 Pattern Matching Performance

**Algorithm Comparison (454k word list):**

| Algorithm | Cold Start | Warm Cache | Use Case |
|-----------|------------|------------|----------|
| Regex | 100-200ms | 80-150ms | Small lists, simple patterns |
| Trie | 50-100ms | 10-20ms | Default, 10-50x faster |
| Aho-Corasick | 150-300ms | 5-15ms | Batch operations |

**Trie Structure:**
- Build time: 2-3s for 454k words
- Memory: ~50MB in-memory trie
- Cached in CLI process (amortized cost)

**Cache Strategy:**
- Pattern cache: LRU 100 entries (backend)
- Trie cache: Persistent in CLI (rebuilt on wordlist change)
- Results cache: 5-minute TTL

### 9.4 Memory Usage

**Backend (Flask):**
- Baseline: ~50MB
- Active fill (1 task): +10-20MB (progress monitoring)
- Peak: ~100MB (multiple concurrent fills)

**CLI Process:**
- Baseline: ~100MB (Python + NumPy)
- Wordlist loaded: +50MB (454k words in trie)
- Beam Search active: +100-300MB (beam states)
- Peak: ~500MB (21×21 grid, beam width 10)

**Frontend (Browser):**
- Initial load: ~5MB (React + app code)
- Grid state: ~50KB (15×15 grid JSON)
- Wordlist cache: ~2MB (if caching words locally)
- Peak: ~10MB (typical usage)

### 9.5 Disk I/O

**Read Operations:**
- Wordlist load: 5-10MB/s (454k words)
- Grid load: <1ms (5-50KB JSON)
- State load: 10-50ms (1-5MB gzipped)

**Write Operations:**
- Grid save: <5ms (JSON write)
- State save: 50-200ms (gzip compression + write)
- Progress updates: 1-5ms (small JSON writes every 100 iterations)

**Temporary Files:**
- Created: Grid files, state files, progress files
- Lifetime: Task duration + 7 days
- Cleanup: Automatic (scheduled cleanup, 7-day retention)

---

## Testing Architecture

### 10.1 Test Organization

**Total Tests:** 165 (100% passing)

```
backend/tests/
├── unit/ (85 tests)
│   ├── test_cli_adapter.py (15 tests)
│   ├── test_edit_merger.py (12 tests)
│   ├── test_theme_placer.py (10 tests)
│   ├── test_black_square_suggester.py (8 tests)
│   ├── test_wordlist_resolver.py (6 tests)
│   ├── test_grid_transformation.py (10 tests)
│   └── test_validators.py (24 tests)
│
├── integration/ (60 tests)
│   ├── test_api.py (20 tests) - Core API endpoints
│   ├── test_cli_integration.py (12 tests) - CLI subprocess calls
│   ├── test_pause_resume_api.py (10 tests) - Pause/resume workflow
│   ├── test_e2e_pause_resume.py (8 tests) - End-to-end scenarios
│   ├── test_realistic_grids.py (6 tests) - Real puzzle fills
│   └── test_progress_integration.py (4 tests) - SSE streaming
│
└── fixtures/ (shared test data)
    ├── grid_fixtures.py - Sample grids (3×3 to 21×21)
    └── realistic_grid_fixtures.py - NYT-style grids

cli/tests/
├── unit/ (40 tests)
│   ├── test_grid.py (12 tests)
│   ├── test_autofill.py (10 tests)
│   ├── test_beam_search.py (8 tests)
│   ├── test_pattern_matcher.py (6 tests)
│   └── test_state_manager.py (4 tests)
│
└── integration/ (20 tests)
    ├── test_cli_commands.py (12 tests)
    └── test_fill_algorithms.py (8 tests)
```

### 10.2 Test Coverage

**Backend Coverage:**
- Overall: 92% (target: >85%)
- Core modules: 95% (cli_adapter, edit_merger)
- API routes: 88%
- Validators: 100%

**CLI Coverage:**
- Overall: 89% (target: >80%)
- Grid engine: 93%
- Autofill algorithms: 85%
- Pattern matching: 90%

**Excluded from Coverage:**
- CLI entry point (manual testing)
- Error handling branches (rare failures)
- Defensive assertions (should never happen)

### 10.3 Test Types

**Unit Tests** (125 tests, <5s total)
- Test individual functions in isolation
- Mock external dependencies (subprocess, file I/O)
- Fast execution (pytest-xdist parallel)
- High coverage of business logic

**Integration Tests** (60 tests, <30s total)
- Test API endpoints end-to-end
- Use Flask test client (no actual HTTP)
- Test CLI subprocess execution
- Verify JSON output formats

**Realistic Grid Tests** (6 tests, ~5min total)
- Test autofill with real NYT-style grids
- Verify solution quality (word scores)
- Check performance (iteration counts)
- Ensure algorithms work on production data

**Smoke Tests** (8 tests, <10s total)
- Health check endpoints
- CLI command basics
- Critical path operations

### 10.4 Testing Strategy

**TDD Approach:**
1. Write failing test for new feature
2. Implement minimal code to pass test
3. Refactor while keeping tests green
4. Repeat

**Test Fixtures:**
```python
@pytest.fixture
def sample_grid():
    """3×3 grid with single word."""
    return {
        "size": 3,
        "grid": [
            ["C", "A", "T"],
            ["#", ".", "."],
            [".", ".", "."]
        ]
    }

@pytest.fixture
def cli_adapter():
    """CLI adapter with mocked subprocess."""
    return CLIAdapter(cli_path="/mock/cli")
```

**Mocking Strategy:**
- Mock subprocess calls in unit tests (no actual CLI execution)
- Use real CLI in integration tests (verify subprocess integration)
- Mock file I/O in fast tests, use temp files in integration tests

**Performance Tests:**
```python
def test_pattern_search_performance():
    """Pattern search completes in <1s."""
    start = time.time()
    result = cli_adapter.pattern("C?T", wordlists=["comprehensive"])
    elapsed = time.time() - start
    assert elapsed < 1.0, f"Too slow: {elapsed:.2f}s"
```

### 10.5 CI/CD Integration

**Pre-commit Checks:**
```bash
pytest backend/tests/unit/ -v        # Fast unit tests
pytest backend/tests/integration/ -v # Integration tests
pytest cli/tests/unit/ -v            # CLI unit tests
```

**Full Test Suite:**
```bash
pytest --cov=backend --cov=cli --cov-report=html
```

**Test Matrix:**
- Python 3.9, 3.10, 3.11, 3.12
- macOS, Linux (Windows future)

**Continuous Testing:**
- Run on every commit (GitHub Actions)
- Coverage report generated
- Fail build if <85% coverage
- Fail build if any test fails

---

## Deployment Model

### 11.1 Local Development Setup

**Prerequisites:**
```bash
# System requirements
- Python 3.9+
- Node.js 18+
- npm 9+
- 4GB RAM (8GB recommended for large grids)
- 500MB disk space
```

**Installation:**
```bash
# Clone repository
git clone <repo-url>
cd crossword-helper

# Backend setup
pip install -r requirements.txt

# CLI setup
cd cli && pip install -r requirements.txt && cd ..

# Frontend setup
npm install
```

**Development Mode:**
```bash
# Terminal 1: Flask backend
python run.py
# → http://localhost:5000 (API server)

# Terminal 2: React dev server
npm run dev
# → http://localhost:3000 (frontend with HMR)
```

**Production Mode:**
```bash
# Build frontend
npm run build  # Creates frontend/dist/

# Run Flask (serves built frontend)
python run.py
# → http://localhost:5000 (all-in-one)
```

### 11.2 File Structure

```
crossword-helper/
├── backend/                 # Flask API server
│   ├── api/                 # API routes (6 blueprints)
│   ├── core/                # CLI adapter, helpers
│   ├── data/                # Data access
│   ├── tests/               # Backend tests (165)
│   └── app.py               # Flask app factory
│
├── cli/                     # CLI tool (single source of truth)
│   ├── src/
│   │   ├── cli.py           # Click commands (8)
│   │   ├── core/            # Grid, numbering, validation
│   │   ├── fill/            # Autofill algorithms
│   │   └── export/          # Export formats
│   ├── tests/               # CLI tests
│   └── crossword            # Entry point script
│
├── src/                     # React frontend
│   ├── components/          # UI components (20+)
│   ├── hooks/               # Custom React hooks
│   ├── styles/              # SCSS styles
│   └── App.jsx              # Main app component
│
├── frontend/dist/           # Built frontend (production)
│
├── data/
│   ├── wordlists/           # Word lists (454k+ words)
│   │   ├── comprehensive.txt
│   │   ├── core/            # Curated core lists
│   │   └── themed/          # Specialty lists
│   └── tmp/                 # Temporary files (state, progress)
│
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md      # This file
│   ├── ROADMAP.md           # Development plan
│   ├── PAUSE_RESUME_ARCHITECTURE.md
│   ├── ADAPTIVE_FEATURES_PLAN.md
│   └── phase*/              # Phase-specific docs
│
├── tests/                   # Root-level integration tests
│
├── run.py                   # Flask server launcher
├── requirements.txt         # Backend dependencies
├── package.json             # Frontend dependencies
├── pytest.ini               # Test configuration
└── vite.config.js           # Vite build config
```

### 11.3 Configuration

**Environment Variables:**
```bash
# Flask
FLASK_ENV=development          # development | production
FLASK_DEBUG=1                  # Enable debug mode

# Paths (optional, auto-detected)
CLI_PATH=/path/to/cli/crossword
WORDLIST_DIR=/path/to/data/wordlists
TEMP_DIR=/tmp/crossword

# Performance
SUBPROCESS_TIMEOUT=30          # Default CLI timeout (seconds)
CACHE_SIZE=100                 # LRU cache size

# Logging
LOG_LEVEL=INFO                 # DEBUG | INFO | WARNING | ERROR
LOG_FILE=/var/log/crossword.log
```

**User Configuration** (future):
- Wordlist preferences
- Default algorithm choice
- UI theme (dark mode)
- Keyboard shortcuts customization

### 11.4 Production Deployment (Future)

**Current:** Local-only (localhost:5000)

**Future Cloud Deployment:**

```
┌─────────────────────────────────────────┐
│         NGINX (Reverse Proxy)           │
│  - SSL/TLS (Let's Encrypt)              │
│  - Static file serving (frontend)       │
│  - Request routing                      │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│      Gunicorn (WSGI Server)             │
│  - 4 worker processes                   │
│  - Flask app instances                  │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│         Flask Application               │
│  - API routes                           │
│  - CLI subprocess calls                 │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│       CLI Tool (same as local)          │
│  - Autofill algorithms                  │
│  - Pattern matching                     │
└─────────────────────────────────────────┘
```

**Deployment Checklist:**
- [ ] Docker containerization (Dockerfile)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Production WSGI server (Gunicorn)
- [ ] Reverse proxy (Nginx)
- [ ] SSL certificates (Let's Encrypt)
- [ ] Database for state (PostgreSQL/Redis)
- [ ] Monitoring (Prometheus + Grafana)
- [ ] Logging (centralized, structured)
- [ ] Backup strategy (wordlists, user data)
- [ ] Authentication (if multi-user)

**Why Not Deployed Yet:**
- Single-user tool (expert + partner)
- Local-only sufficient for current needs
- Cloud deployment adds complexity without value
- Easy to deploy later if needed (architecture supports it)

---

## Advanced Features

### 12.1 Pause/Resume System

**Problem:** Autofill can take 30min for 21×21 grids, user may need to pause

**Solution:** Full algorithm state serialization with edit support

**Architecture:**

```
1. User pauses autofill
   └─► Pause signal written (file-based IPC)
       └─► CLI detects signal (next iteration check)
           └─► Serialize complete state:
               ├─ Grid state (partially filled)
               ├─ Algorithm position (backtrack stack or beam)
               ├─ Candidate lists for each slot
               ├─ Constraint propagation state (AC-3 domains)
               ├─ Iteration count
               └─ Timestamp
           └─► Compress with gzip (~80% reduction)
           └─► Save to /tmp/state_<task_id>.json.gz

2. User edits grid manually
   ├─► GridEditor: add letters, remove words, change entries
   └─► Edits tracked as delta from paused grid

3. User resumes autofill
   └─► POST /api/fill/resume with edits
       └─► EditMerger validates edits:
           ├─ Run AC-3 constraint propagation
           ├─ Check for unsolvable constraints
           ├─ If invalid: return errors
           └─ If valid: lock edited cells
       └─► CLI loads state + applies edits:
           ├─ Deserialize algorithm state
           ├─ Update grid with user edits
           ├─ Mark edited slots as "locked" (theme entries)
           ├─ Resume from exact algorithmic position
           └─ Fresh timeout window (new 300s)
```

**State File Format:**
```json
{
  "version": "1.0",
  "algorithm": "beam_search",
  "grid": [[...]],
  "iteration": 5432,
  "beam": [
    {"grid": [[...]], "score": 85.2},
    {"grid": [[...]], "score": 82.1}
  ],
  "domains": {
    "0-ACROSS-0": ["CAT", "COT", "CUT"],
    "1-DOWN-0": ["CAPE", "CARE", "CASE"]
  },
  "locked_slots": ["2-ACROSS-5"],
  "timestamp": "2025-12-27T10:30:00Z"
}
```

**Performance:**
- State save: 50-200ms (gzip compression)
- State load: 10-50ms (gzip decompression)
- State size: 1-5MB compressed (10-30MB uncompressed)
- Check overhead: <0.1% (every 100 iterations)

### 12.2 Theme Entry System

**Problem:** User has specific words to include (partner's name, dates, inside jokes)

**Solution:** Lock cells to preserve words during autofill

**Implementation:**

```python
# Theme entry locked in grid
theme_entries = {
    "7-ACROSS-0": ["P", "A", "R", "T", "N", "E", "R", "N", "A", "M", "E"]
}

# During autofill
if slot in theme_entries:
    continue  # Skip this slot, word is locked

# During constraint propagation
for crossing_slot in get_crossing_slots(slot):
    if crossing_slot in theme_entries:
        # Constrain candidates to match locked letters
        pattern = build_pattern_with_locked_letters(
            crossing_slot, theme_entries[crossing_slot]
        )
        candidates = pattern_match(pattern)
```

**UI Features:**
- Right-click cell → Lock/Unlock
- Visual indicator (colored border)
- Theme word import (paste list of words)
- Suggested placement (analyze grid, suggest optimal positions)

### 12.3 Adaptive Black Square Placement

**Problem:** Grid stuck during autofill (unfillable region)

**Solution:** Suggest strategic "cheater squares" to resolve

**Algorithm:**
```python
def suggest_black_squares(grid, problematic_slots):
    """
    Find cells that, if made black, would:
    1. Break unfillable slot into two fillable slots
    2. Maintain symmetry
    3. Not violate min word length (3 letters)
    4. Not create isolated regions
    """
    suggestions = []

    for slot in problematic_slots:
        # Try each position in slot
        for i in range(len(slot)):
            pos = slot.positions[i]

            # Check if adding black square here helps
            if would_resolve_issue(grid, pos):
                symmetric_pos = get_symmetric_position(grid, pos)
                suggestions.append({
                    "position": pos,
                    "symmetric_position": symmetric_pos,
                    "impact": calculate_impact(grid, pos),
                    "score": calculate_black_square_score(grid, pos)
                })

    return sorted(suggestions, key=lambda s: s['score'], reverse=True)
```

**Endpoint:**
```
POST /api/grid/suggest-black-squares
{
  "grid": [[...]],
  "problematic_slots": ["15-ACROSS-8", "12-DOWN-10"]
}

Response:
{
  "suggestions": [
    {
      "position": [15, 12],
      "symmetric_position": [6, 8],
      "reason": "Breaks 15-ACROSS into two 7-letter slots",
      "score": 85
    }
  ]
}
```

### 12.4 Real-Time Progress Streaming

**Problem:** Long autofill operations need user feedback

**Solution:** Server-Sent Events (SSE) for real-time updates

**Architecture:**

```
Frontend (EventSource)
    │
    ├─ Connect to /api/progress/:task_id
    │
    ▼
Backend (progress_routes.py)
    │
    ├─ Start SSE stream
    ├─ Monitor progress file (/tmp/progress_<task_id>.json)
    ├─ Read file every 500ms
    ├─ Stream updates to client
    │
    ▼
CLI (writes progress file)
    │
    ├─ Every 100 iterations:
    │   ├─ Calculate stats
    │   ├─ Write JSON to progress file
    │   └─ Continue filling
```

**Progress File Format:**
```json
{
  "status": "running",
  "iteration": 5432,
  "slots_filled": 42,
  "total_slots": 78,
  "time_elapsed": 45.2,
  "estimated_remaining": 120.0,
  "current_word": "CROSSWORD",
  "timestamp": "2025-12-27T10:30:15Z"
}
```

**SSE Stream:**
```
data: {"status": "running", "iteration": 5432, "slots_filled": 42}

data: {"status": "running", "iteration": 5533, "slots_filled": 43}

data: {"status": "complete", "slots_filled": 78}
```

**Frontend Handling:**
```javascript
const eventSource = new EventSource(`/api/progress/${taskId}`);

eventSource.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  updateProgressBar(progress.slots_filled / progress.total_slots);
  updateStats(progress);
};

eventSource.onerror = () => {
  eventSource.close();
  showError("Connection lost");
};
```

### 12.5 Wordlist Management

**Features:**
- Browse 454k+ words across 10+ categories
- Upload custom wordlists (.txt files)
- View statistics (word count, length distribution, score distribution)
- Add individual words to existing lists
- Search/filter by length, score, pattern

**Categories:**
- `comprehensive.txt` - 454k words (all sources)
- `core/3-letter.txt` - Short words (critical for tight spots)
- `core/crosswordese.txt` - Common crossword fill
- `themed/expressions.txt` - Multi-word phrases
- `themed/foreign-es.txt` - Spanish words (cultural crosswords)
- `themed/foreign-fr.txt` - French words
- `custom/*.txt` - User uploads

**Upload Validation:**
```python
def validate_wordlist(file):
    """Validate uploaded wordlist file."""
    # Extension check
    if not file.filename.endswith('.txt'):
        raise ValueError("Must be .txt file")

    # Size check (max 10MB)
    if len(file.read()) > 10_000_000:
        raise ValueError("File too large (max 10MB)")

    # Format check (one word per line, uppercase)
    file.seek(0)
    for line in file:
        word = line.strip()
        if not re.match(r'^[A-Z]+$', word):
            raise ValueError(f"Invalid word: {word}")
        if len(word) < 3 or len(word) > 21:
            raise ValueError(f"Word length invalid: {word}")

    return True
```

---

## Conclusion

The Crossword Helper implements a sophisticated **CLI-as-single-source-of-truth architecture** that provides both web and command-line interfaces from a unified codebase. Built progressively over three development phases, the system demonstrates key architectural principles:

### Architectural Strengths

1. **Single Source of Truth**: CLI tool contains all business logic, eliminating code duplication
2. **Layered Architecture**: Clear separation between HTTP, business logic, and data access
3. **Subprocess Integration**: Clean integration pattern via CLIAdapter (100-300ms overhead)
4. **Algorithm Sophistication**: Multiple autofill algorithms (CSP, Beam Search, Hybrid)
5. **Pause/Resume System**: Full state serialization with edit support
6. **Real-Time Feedback**: SSE streaming for long-running operations
7. **Comprehensive Testing**: 165 tests (100% passing), 92% backend coverage, 89% CLI coverage

### Production Readiness

- ✅ All features implemented and tested
- ✅ Performance targets met (11×11 < 30s, 15×15 < 5min)
- ✅ Local deployment stable
- ✅ Error handling comprehensive
- ⏳ Cloud deployment (future enhancement)
- ⏳ Multi-user authentication (future enhancement)

### Next Steps

1. **User Testing**: Gather feedback from partner (non-technical user)
2. **Performance Optimization**: Daemon mode for CLI (eliminate process spawn overhead)
3. **Frontend Testing**: Add Jest + React Testing Library tests
4. **Cloud Deployment**: Docker + Nginx + Gunicorn (if sharing with others)
5. **Feature Expansion**: See ADAPTIVE_FEATURES_PLAN.md for roadmap

---

**Document Version:** 1.0
**Last Updated:** December 27, 2025
**Maintained By:** Development Team
**Next Review:** After user testing phase
