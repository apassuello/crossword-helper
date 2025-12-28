# Backend/Web API Specification

**Document Type:** Component Specification (Layer 2)
**Version:** 2.0.0 (Phase 3 Integration Complete)
**Last Updated:** 2025-12-27
**Status:** All phases complete, 165/165 tests passing

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [API Endpoints](#api-endpoints)
4. [CLIAdapter - The Integration Bridge](#cliadapter---the-integration-bridge)
5. [Core Components](#core-components)
6. [Request Validation](#request-validation)
7. [Error Handling](#error-handling)
8. [CORS Configuration](#cors-configuration)
9. [Real-Time Progress Tracking (SSE)](#real-time-progress-tracking-sse)
10. [Performance Characteristics](#performance-characteristics)
11. [Testing](#testing)
12. [Security](#security)
13. [Configuration](#configuration)

---

## Overview

### Purpose

The Backend/Web API is a **thin HTTP wrapper** around the CLI tool, providing RESTful API endpoints for the React frontend. It follows the "single source of truth" architecture established in Phase 3 integration.

**Key Design Principle:** Delegate all crossword logic to CLI via subprocess, maintain zero business logic duplication.

### Role in System

```
Frontend (React/Vite)
    ↓ HTTP/JSON
Backend (Flask)
    ↓ subprocess + JSON
CLI Tool (Python Click)
    ↓ algorithms
Core Libraries (CSP solver, pattern matching, etc.)
```

The backend serves as:
- **HTTP→CLI translator**: Converts HTTP requests to CLI commands
- **Format adapter**: Transforms frontend grid format to CLI format
- **Progress streamer**: Provides real-time updates via Server-Sent Events
- **State manager**: Handles pause/resume autofill state

### Why "Thin"

Backend contains **minimal logic**:
- Request validation (schemas, input sanitization)
- Grid format conversion (frontend ↔ CLI)
- Subprocess orchestration
- SSE streaming for progress updates

All crossword algorithms, business rules, and domain logic live in the CLI.

**Benefits:**
- Single implementation of all features
- CLI fully testable without HTTP stack
- Backend integration tests are lightweight
- Easy to add new features (implement in CLI, expose via route)

---

## Architecture

### Three-Layer Design

```
┌─────────────────────────────────────────────┐
│  API Layer (backend/api/*.py)               │
│  - Routes (blueprints)                      │
│  - Request validation                       │
│  - Response formatting                      │
│  - Error handling                           │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  Core Layer (backend/core/*.py)             │
│  - CLIAdapter (subprocess execution)        │
│  - EditMerger (pause/resume logic)          │
│  - ThemePlacer (placement suggestions)      │
│  - BlackSquareSuggester (grid helpers)      │
│  - WordlistResolver (path resolution)       │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  Data Layer (backend/data/*.py)             │
│  - WordListManager (wordlist CRUD)          │
│  - File I/O (wordlists, state files)        │
└─────────────────────────────────────────────┘
```

### Flask Blueprints (6 total)

The API is organized into 6 blueprints, all registered under `/api` prefix:

| Blueprint | File | Prefix | Purpose |
|-----------|------|--------|---------|
| `api` | `routes.py` | `/api` | Core operations (pattern, number, normalize, fill) |
| `grid_api` | `grid_routes.py` | `/api/grid` | Grid helpers (black squares, validation) |
| `theme_api` | `theme_routes.py` | `/api/theme` | Theme word management |
| `pause_resume_api` | `pause_resume_routes.py` | `/api/fill` | Pause/resume autofill |
| `progress_api` | `progress_routes.py` | `/api/progress` | SSE progress streaming |
| `wordlist_api` | `wordlist_routes.py` | `/api/wordlists` | Wordlist CRUD |

### Request Flow

**Typical request lifecycle:**

```
1. HTTP Request → Flask route handler
2. Validate request (validators.py)
3. Format conversion (if needed)
4. CLIAdapter.{method}()
   4a. Build CLI command args
   4b. Execute subprocess
   4c. Parse JSON stdout
   4d. Handle errors
5. Format response
6. Return JSON
```

**Example (pattern search):**

```python
# 1. HTTP POST /api/pattern {"pattern": "C?T"}
# 2. validate_pattern_request(data)
# 3. No conversion needed (pattern is string)
# 4. cli_adapter.pattern("C?T", wordlist_paths, max_results=20)
#    → subprocess: crossword pattern C?T --json-output --max-results 20
#    → stdout: {"results": [...], "meta": {...}}
# 5. Return parsed JSON
# 6. HTTP 200 {"results": [...]}
```

### Directory Structure

```
backend/
├── app.py                      # Flask app factory
├── api/                        # API layer (blueprints)
│   ├── routes.py               # Core routes
│   ├── grid_routes.py          # Grid helper routes
│   ├── theme_routes.py         # Theme routes
│   ├── pause_resume_routes.py  # Pause/resume routes
│   ├── progress_routes.py      # SSE progress routes
│   ├── wordlist_routes.py      # Wordlist CRUD routes
│   ├── validators.py           # Request validation
│   └── errors.py               # Error response formatting
├── core/                       # Core layer (business logic)
│   ├── cli_adapter.py          # CLI subprocess wrapper
│   ├── edit_merger.py          # Pause/resume edit merging
│   ├── theme_placer.py         # Theme placement suggestions
│   ├── black_square_suggester.py  # Grid helpers
│   └── wordlist_resolver.py    # Wordlist path resolution
├── data/                       # Data access layer
│   └── wordlist_manager.py     # Wordlist file operations
└── tests/                      # Test suite (92% coverage)
    ├── unit/                   # Fast, isolated tests
    ├── integration/            # API endpoint tests
    └── fixtures/               # Test data
```

---

## API Endpoints

### Core Operations (routes.py)

#### GET /api/health

**Purpose:** Health check endpoint with component status

**Request:**
```bash
curl http://localhost:5000/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "architecture": "cli-backend",
  "components": {
    "cli_adapter": "ok",
    "api_server": "ok"
  }
}
```

**Status Codes:**
- `200 OK` - All systems operational
- `503 Service Unavailable` - CLI adapter unhealthy

**Performance:** <50ms

---

#### POST /api/pattern

**Purpose:** Search for words matching a pattern

**Request:**
```json
{
  "pattern": "C?T",
  "wordlists": ["comprehensive"],
  "max_results": 20,
  "algorithm": "regex"
}
```

**Response:**
```json
{
  "results": [
    {"word": "CAT", "score": 85, "source": "comprehensive"},
    {"word": "COT", "score": 82, "source": "comprehensive"},
    {"word": "CUT", "score": 80, "source": "comprehensive"}
  ],
  "meta": {
    "total_found": 127,
    "query_time_ms": 245,
    "algorithm": "regex"
  }
}
```

**Parameters:**
- `pattern` (required): Pattern string, `?` = wildcard, letters = exact match
- `wordlists` (optional): Array of wordlist names, default `["comprehensive"]`
- `max_results` (optional): Integer 1-100, default 20
- `algorithm` (optional): `"regex"` or `"trie"`, default `"regex"`

**Example:**
```bash
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{"pattern": "C?T", "max_results": 10}'
```

**Performance:** <1s (OneLook API + local search)
**CLI Command:** `crossword pattern C?T --json-output --max-results 20 --wordlists /path/to/comprehensive.txt`

---

#### POST /api/number

**Purpose:** Auto-number a crossword grid

**Request:**
```json
{
  "size": 15,
  "grid": [
    ["R", "A", "S", "#", "P", ...],
    ["I", "N", "T", "#", "A", ...],
    ...
  ]
}
```

**Response:**
```json
{
  "numbering": {
    "(0,0)": 1,
    "(0,5)": 2,
    "(1,0)": 3
  },
  "grid_info": {
    "size": [15, 15],
    "word_count": 76,
    "black_square_count": 38,
    "black_square_percentage": 16.8
  }
}
```

**Parameters:**
- `size` (required): Grid size (integer 3-50)
- `grid` (required): 2D array of strings (letters, `#` = black, `.` = empty)

**Example:**
```bash
curl -X POST http://localhost:5000/api/number \
  -H "Content-Type: application/json" \
  -d '{"size": 15, "grid": [[...]]}'
```

**Performance:** <100ms (pure computation)
**CLI Command:** `crossword number /tmp/grid_xyz.json --json-output`

---

#### POST /api/normalize

**Purpose:** Normalize crossword entry according to conventions

**Request:**
```json
{
  "text": "Tina Fey"
}
```

**Response:**
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

**Parameters:**
- `text` (required): Text to normalize (string, max 100 chars)

**Example:**
```bash
curl -X POST http://localhost:5000/api/normalize \
  -H "Content-Type: application/json" \
  -d '{"text": "Tina Fey"}'
```

**Performance:** <50ms (regex patterns)
**CLI Command:** `crossword normalize "Tina Fey" --json-output`
**Caching:** Results cached with LRU cache (128 entries)

---

#### POST /api/fill

**Purpose:** Auto-fill crossword grid using CSP solver

**Request:**
```json
{
  "size": 15,
  "grid": [
    [{"letter": "", "isBlack": false}, ...],
    ...
  ],
  "wordlists": ["comprehensive"],
  "timeout": 300,
  "min_score": 30,
  "algorithm": "trie",
  "theme_entries": {
    "(0,0,across)": "EXAMPLE",
    "(7,4,down)": "THEME"
  },
  "adaptive_mode": false
}
```

**Response:**
```json
{
  "grid": [
    [{"letter": "R", "isBlack": false}, ...],
    ...
  ],
  "status": "complete",
  "slots_filled": 76,
  "total_slots": 76,
  "iteration_count": 3429,
  "time_elapsed": 45.3
}
```

**Parameters:**
- `size` (required): Grid size (integer 3-50)
- `grid` (required): 2D array of cell objects `{letter, isBlack}`
- `wordlists` (optional): Array of wordlist names
- `timeout` (optional): Timeout in seconds (10-1800), default 300
- `min_score` (optional): Minimum word quality score (0-100), default 30
- `algorithm` (optional): `"regex"` or `"trie"`, default `"trie"`
- `theme_entries` (optional): Pre-filled theme words
- `adaptive_mode` (optional): Enable adaptive black square placement

**Example:**
```bash
curl -X POST http://localhost:5000/api/fill \
  -H "Content-Type: application/json" \
  -d '{"size": 15, "grid": [[...]], "timeout": 120}'
```

**Performance:** Variable (11×11: <30s, 15×15: <5min, 21×21: <30min)
**CLI Command:** `crossword fill /tmp/grid_xyz.json --timeout 300 --min-score 30 --wordlists /path/to/comprehensive.txt`

**Grid Format Conversion:**

Frontend format (React):
```json
[{"letter": "A", "isBlack": false}, {"letter": "", "isBlack": true}]
```

CLI format (Python):
```json
["A", "#"]
```

Backend performs bidirectional conversion.

---

#### POST /api/fill/with-progress

**Purpose:** Auto-fill with real-time progress updates via SSE

**Request:** Same as `/api/fill`

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "progress_url": "/api/progress/550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Code:** `202 Accepted` (task started)

**Usage:**
1. POST to `/api/fill/with-progress` → get `task_id`
2. Connect to SSE endpoint `/api/progress/{task_id}`
3. Receive real-time progress events
4. Final event contains completed grid

**See:** [Real-Time Progress Tracking](#real-time-progress-tracking-sse) for details

---

### Grid Helper Routes (grid_routes.py)

#### POST /api/grid/suggest-black-square

**Purpose:** Suggest strategic black square placements to resolve stuck fills

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
      "reasoning": "Balanced split (7+7 letters), Both lengths in sweet spot (3-7)",
      "left_length": 7,
      "right_length": 7,
      "symmetric_position": {"row": 14, "col": 7},
      "new_word_count": 77,
      "constraint_reduction": 4
    }
  ],
  "slot_info": {...}
}
```

**Algorithm:**
- Scores placements by: balanced splits, word length sweet spot, symmetry, word count impact
- Returns top N suggestions sorted by score
- Includes symmetric pair position for each suggestion

---

### Theme Routes (theme_routes.py)

#### POST /api/theme/upload

**Purpose:** Upload theme words from file content

**Request:**
```json
{
  "content": "WORD1\nWORD2\nWORD3",
  "grid_size": 15
}
```

**Response:**
```json
{
  "words": ["WORD1", "WORD2", "WORD3"],
  "count": 3,
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": []
  }
}
```

---

#### POST /api/theme/suggest-placements

**Purpose:** Suggest optimal placements for theme words

**Request:**
```json
{
  "theme_words": ["WORD1", "WORD2"],
  "grid_size": 15,
  "existing_grid": [[...], ...],
  "max_suggestions": 3
}
```

**Response:**
```json
{
  "suggestions": [
    {
      "word": "WORD1",
      "length": 5,
      "suggestions": [
        {
          "row": 7,
          "col": 5,
          "direction": "across",
          "score": 95,
          "reasoning": "Centered placement (symmetric), Good horizontal position"
        }
      ]
    }
  ]
}
```

**Scoring Factors:**
- Symmetry (0-30 points): Centered or symmetric placement
- Intersections (0-20 points): Overlap with existing letters
- Position (0-20 points): Middle rows/cols preferred
- Length (0-10 points): Bonus for long centered words
- Spacing (0-10 points): Good distance from other theme words

---

### Pause/Resume Routes (pause_resume_routes.py)

#### POST /api/fill/pause/:task_id

**Purpose:** Request autofill to pause

**Request:**
```bash
curl -X POST http://localhost:5000/api/fill/pause/task_abc123
```

**Response:**
```json
{
  "success": true,
  "message": "Pause requested for task task_abc123",
  "task_id": "task_abc123"
}
```

**Mechanism:**
- Creates pause flag file in `/tmp/pause_{task_id}`
- CLI checks this file periodically during autofill
- When detected, CLI saves CSP state and exits gracefully

---

#### POST /api/fill/resume

**Purpose:** Resume paused autofill with optional user edits

**Request:**
```json
{
  "task_id": "task_abc123",
  "edited_grid": [[...], ...],
  "options": {
    "min_score": 50,
    "timeout": 300,
    "wordlists": ["comprehensive"],
    "algorithm": "trie"
  }
}
```

**Response:**
```json
{
  "success": true,
  "new_task_id": "resume_xyz456",
  "original_task_id": "task_abc123",
  "message": "Resume state prepared",
  "slots_filled": 38,
  "total_slots": 76
}
```

**Process:**
1. Load saved CSP state from file
2. If `edited_grid` provided, merge edits using `EditMerger`
   - Detect changes (filled/emptied/modified slots)
   - Mark new filled cells as locked
   - Update CSP domains with AC-3 constraint propagation
   - Validate solvability
3. Save updated state with new task ID
4. Return new task ID for client to resume autofill

**Error Codes:**
- `400 Bad Request` - Missing task_id or invalid grid
- `404 Not Found` - Saved state not found
- `409 Conflict` - Edits create unsolvable state

---

### Progress Routes (progress_routes.py)

#### GET /api/progress/:task_id

**Purpose:** Stream progress updates via Server-Sent Events

**Connection:**
```javascript
const eventSource = new EventSource('/api/progress/550e8400-...');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.progress, data.message);

  if (data.status === 'complete') {
    console.log('Grid:', data.data.grid);
    eventSource.close();
  }
};
```

**Event Format:**
```json
{
  "progress": 45,
  "message": "Filled 34/76 slots (backtracked 127 times)",
  "status": "running",
  "timestamp": 1703612345.678,
  "data": {...}
}
```

**Status Values:**
- `running` - Operation in progress
- `complete` - Successfully completed (includes result data)
- `error` - Failed (includes error message)

**Heartbeat:** Sends `: heartbeat\n\n` every 30s to keep connection alive

**Cleanup:** Progress tracker automatically removed when client disconnects

---

### Wordlist Routes (wordlist_routes.py)

#### GET /api/wordlists

**Purpose:** List all available wordlists with metadata

**Query Parameters:**
- `category` (optional): Filter by category

**Response:**
```json
{
  "wordlists": [
    {
      "name": "comprehensive",
      "category": "core",
      "word_count": 412483,
      "description": "Comprehensive crossword word list",
      "tags": ["core", "comprehensive"]
    }
  ],
  "categories": {
    "core": 5,
    "themed": 12,
    "custom": 3
  },
  "tags": {
    "slang": 4,
    "technical": 2
  }
}
```

---

## CLIAdapter - The Integration Bridge

**File:** `backend/core/cli_adapter.py`

### Purpose

The CLIAdapter is the **heart of the Phase 3 integration**, providing a clean Python API for executing CLI commands via subprocess. It ensures the backend has zero duplicated business logic.

### Key Responsibilities

1. **Subprocess Execution**
   - Build CLI command arguments
   - Execute subprocess with timeout
   - Parse JSON stdout
   - Handle stderr errors

2. **Format Conversion**
   - Convert between frontend and CLI grid formats
   - Handle temporary file creation/cleanup
   - Manage JSON serialization

3. **Error Handling**
   - Catch subprocess timeouts
   - Parse CLI error messages
   - Propagate errors with context

4. **Performance Optimization**
   - LRU caching for normalization results
   - Auto-detection of CLI path
   - Configurable timeouts per operation

### Architecture

```python
class CLIAdapter:
    def __init__(self, cli_path: Optional[str] = None, timeout: int = 30):
        # Auto-detect CLI path if not provided
        # Validate CLI exists and is executable

    def _run_command(self, args: List[str], timeout: Optional[int] = None) -> Tuple[str, str, int]:
        # Execute subprocess, return (stdout, stderr, returncode)

    def pattern(self, pattern: str, wordlist_paths: List[str], ...) -> Dict:
        # Pattern search via CLI

    def normalize(self, text: str) -> Dict:
        # Normalize text via CLI

    def number(self, grid_data: Dict, ...) -> Dict:
        # Auto-number grid via CLI

    def fill(self, grid_data: Dict, wordlist_paths: List[str], ...) -> Dict:
        # Auto-fill grid via CLI

    def fill_with_resume(self, task_id: str, state_file_path: str, ...) -> Dict:
        # Resume from saved state

    def health_check(self) -> bool:
        # Check if CLI is accessible
```

---

## Core Components

### EditMerger (edit_merger.py)

**Purpose:** Merge user edits into saved autofill state while maintaining CSP consistency

**Key Algorithm:** AC-3 Constraint Propagation

**Process:**

1. **Detect Changes** between saved and edited grids
2. **Update Locked Slots** (newly filled cells cannot be changed)
3. **Update Domains** using AC-3 constraint propagation
4. **Validate Solvability** (no empty domains)
5. **Create Updated State** ready for resume

**AC-3 Algorithm:**

```python
def _propagate_constraints(domains, constraints, grid, slot_list):
    queue = deque(all_arcs)
    while queue:
        slot_id, other_slot, pos1, pos2 = queue.popleft()
        if _revise(domains, slot_id, other_slot, pos1, pos2):
            # Domain changed, re-check neighbors
            for neighbor in neighbors(slot_id):
                queue.append((neighbor, slot_id, ...))
    return domains
```

---

### ThemePlacer (theme_placer.py)

**Purpose:** Suggest optimal placements for theme words in grids

**Strategy:**
1. Sort words by length (longest first)
2. Generate all valid placements
3. Score each placement (0-100)
4. Return top N suggestions per word

**Scoring Factors:**

| Factor | Points | Description |
|--------|--------|-------------|
| Symmetry | 0-30 | Centered or rotationally symmetric placement |
| Intersections | 0-20 | Overlap with existing letters (10 pts per intersection) |
| Position | 0-20 | Middle rows/cols preferred |
| Length | 0-10 | Bonus for long centered words (≥60% grid width) |
| Spacing | 0-10 | Good distance from other theme words (>4 cells) |
| **Penalties** | -20 | Edge placements for long words (>8 letters) |

---

### BlackSquareSuggester (black_square_suggester.py)

**Purpose:** Suggest strategic black square placements to resolve stuck fills

**Algorithm:**

1. **Identify Problematic Slot** (0 or very few candidates)
2. **Generate Placement Candidates** (try splits at each position)
3. **Score Each Candidate** (0-1000 points):
   - Balanced Split (0-300)
   - Sweet Spot Lengths (0-200)
   - Symmetry (0-200)
   - Word Count (0-150)
   - Constraint Reduction (0-150)
4. **Return Top N Suggestions**

---

### WordlistResolver (wordlist_resolver.py)

**Purpose:** Resolve wordlist names to absolute file paths

**Supports:**
- Simple names: `"comprehensive"` → `data/wordlists/comprehensive.txt`
- Category paths: `"core/common_3_letter"` → `data/wordlists/core/common_3_letter.txt`
- Absolute paths: `/abs/path/to/wordlist.txt` (passed through)

**Benefits:**
- Single implementation (DRY)
- Consistent path resolution across all routes
- Supports flexible wordlist organization

---

## Request Validation

**File:** `backend/api/validators.py`

### Purpose

Validate incoming request data **before** delegating to CLI. Prevents:
- Invalid CLI invocations
- Confusing CLI error messages
- Security vulnerabilities (injection, path traversal)

### Validation Functions

#### validate_pattern_request()

Checks:
- `pattern` exists and is string
- `wordlists` is array of strings (if provided)
- `max_results` is integer 1-100 (if provided)

#### validate_grid_request()

Checks:
- `size` exists and is integer 3-50
- `grid` exists and is 2D array
- `numbering` is object (if provided)

#### validate_fill_request()

Checks:
- `grid` and `size` exist
- `timeout` is integer 10-1800 (if provided)
- `min_score` is integer 0-100 (if provided)
- `theme_entries` has valid key format `"(row,col,direction)"` (if provided)

---

## Error Handling

**File:** `backend/api/errors.py`

### Error Response Format

All API errors follow consistent JSON structure:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Field 'pattern' must be string"
  }
}
```

### Error Codes

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `INVALID_CONTENT_TYPE` | 400 | Content-Type must be application/json |
| `INVALID_JSON` | 400 | Failed to parse JSON body |
| `EMPTY_BODY` | 400 | Request body is empty |
| `INVALID_REQUEST` | 400 | Validation failed (see message for details) |
| `TIMEOUT` | 504-507 | CLI command timed out |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

**Timeout Status Codes** (unique per operation):
- 504: Grid numbering timeout
- 505: Pattern search timeout
- 506: Normalization timeout
- 507: Grid fill timeout

---

## CORS Configuration

**File:** `backend/app.py`

### Allowed Origins

```python
CORS(app, origins=[
    'http://localhost:5000',      # Flask server (dev)
    'http://127.0.0.1:5000',
    'http://localhost:3000',      # React dev server (Vite)
    'http://127.0.0.1:3000'
])
```

**Development Mode:**
- Backend: `localhost:5000`
- Frontend: `localhost:3000` (Vite dev server)

**Production Mode:**
- Frontend built to `frontend/dist/`
- Served by Flask from `/` route
- All requests same-origin → no CORS needed

---

## Real-Time Progress Tracking (SSE)

**File:** `backend/api/progress_routes.py`

### Architecture

```
Client                Backend                      CLI
  |                     |                            |
  |  POST /api/fill/    |                            |
  |  with-progress      |                            |
  |-------------------->|                            |
  |  202 {task_id}      |                            |
  |<--------------------|                            |
  |                     | Start background thread    |
  |                     |--------------------------->|
  |  GET /progress/     |                            |
  |  {task_id}          |                            |
  |-------------------->|                            |
  |  SSE stream         |                            |
  |<~~~~~~~~~~~~~~~~~~~>|                            |
  |                     |  Read stderr (progress)    |
  |                     |<---------------------------|
  |  event: {progress}  |                            |
  |<--------------------|                            |
```

### Components

#### Progress Tracker

```python
# Global state (in-memory)
progress_queues: Dict[str, queue.Queue] = {}

def create_progress_tracker() -> str:
    task_id = str(uuid.uuid4())
    progress_queues[task_id] = queue.Queue()
    return task_id

def send_progress(task_id: str, progress: int, message: str, status: str, data: Dict = None):
    event = {'progress': progress, 'message': message, 'status': status, 'data': data}
    progress_queues[task_id].put(event, block=False)
```

#### SSE Stream Endpoint

```python
@progress_api.route('/progress/<task_id>', methods=['GET'])
def stream_progress(task_id: str):
    def generate():
        while True:
            event = task_queue.get(timeout=30)
            yield f"data: {json.dumps(event)}\n\n"
            if event.get('status') in ['complete', 'error']:
                break

    return Response(generate(), mimetype='text/event-stream')
```

### Client Usage

```javascript
const eventSource = new EventSource(progress_url);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  updateProgressBar(data.progress);

  if (data.status === 'complete') {
    displayFilledGrid(data.data.grid);
    eventSource.close();
  }
};
```

---

## Performance Characteristics

### API Endpoint Response Times

| Endpoint | Target | Actual | Bottleneck |
|----------|--------|--------|------------|
| GET /api/health | <50ms | ~10ms | None |
| POST /api/normalize | <50ms | ~5ms (cached) | Subprocess overhead |
| POST /api/number | <100ms | ~150ms | Subprocess + grid processing |
| POST /api/pattern | <1s | ~400ms | OneLook API + local search |
| POST /api/fill (11×11) | <30s | ~15s | CSP solving |
| POST /api/fill (15×15) | <5min | ~2min | CSP solving |
| POST /api/fill (21×21) | <30min | ~12min | CSP solving |

### Subprocess Overhead

**Typical overhead:** ~120ms per CLI invocation

**Breakdown:**
- Process spawn: ~50ms
- CLI import/startup: ~30ms
- Actual operation: varies
- Process cleanup: ~30ms

### Caching Impact

**Normalization Cache (LRU, 128 entries):**

- First call (cold): 120ms
- Second call (cached): <1ms
- Cache hit rate: ~80% in typical usage

---

## Testing

### Test Organization

```
backend/tests/
├── unit/                          # Fast, isolated tests
│   ├── test_validators.py         # Request validation
│   ├── test_edit_merger.py        # Edit merging logic
│   └── test_grid_transformation.py # Grid format conversion
├── integration/                   # API endpoint tests
│   ├── test_api.py                # Core routes
│   ├── test_cli_integration.py    # CLIAdapter tests
│   ├── test_pause_resume_api.py   # Pause/resume endpoints
│   └── test_progress_integration.py # SSE progress tracking
└── fixtures/                      # Test data
```

### Test Coverage

**Overall:** 92% backend coverage (165/165 tests passing)

**By Module:**
- `api/routes.py`: 95% (all endpoints covered)
- `api/validators.py`: 100% (exhaustive input validation tests)
- `core/cli_adapter.py`: 90% (all methods tested)
- `core/edit_merger.py`: 88% (AC-3 algorithm tested)
- `core/theme_placer.py`: 85% (scoring logic tested)

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=backend --cov-report=html

# Specific test suite
pytest tests/unit/ -v
pytest tests/integration/ -v
```

---

## Security

### Input Validation

All user input validated before CLI invocation:

```python
# Pattern validation
if not pattern or not pattern.strip():
    raise ValueError("Pattern cannot be empty")

# Grid size validation
if data['size'] < 3 or data['size'] > 50:
    raise ValueError("Field 'size' must be between 3 and 50")
```

**Prevents:**
- Empty/null inputs causing CLI crashes
- Excessively large grids (DoS)
- Buffer overflow attempts

---

### Subprocess Security

**No shell injection risk:**

```python
# SAFE: args passed as list
subprocess.run([str(cli_path), 'pattern', user_pattern], ...)

# UNSAFE: shell=True (NOT USED)
subprocess.run(f"crossword pattern {user_pattern}", shell=True)
```

**File path sanitization:**

```python
# Wordlist resolution: only allows files in data/wordlists/
def _resolve_single_wordlist(wordlist_name: str, data_dir: Path) -> Path:
    # Reject absolute paths outside data_dir
    # Reject path traversal attempts (..)
```

**Prevents:**
- Command injection via pattern/text fields
- Path traversal (e.g., `../../../etc/passwd`)
- Execution of arbitrary code

---

## Configuration

### Environment Variables

**Current (none required):**

Backend auto-detects all configuration.

**Future Production:**

```bash
# Flask configuration
FLASK_ENV=production

# CORS origins
CORS_ORIGINS=https://crossword-app.example.com

# CLI path (if not auto-detectable)
CLI_PATH=/opt/crossword/cli/crossword

# Data directory
DATA_DIR=/var/lib/crossword/data
```

### Flask Configuration

**File:** `backend/app.py`

```python
def create_app(testing=False):
    app = Flask(__name__)
    app.config['TESTING'] = testing
    app.config['JSON_SORT_KEYS'] = False  # Preserve key order
    CORS(app, origins=[...])
    # Register blueprints
    return app
```

---

## Summary

### Architecture Highlights

1. **Thin Wrapper Design** - Backend delegates all logic to CLI
2. **Clean Separation** - API layer, Core layer, Data layer
3. **Real-Time Capabilities** - SSE for progress, pause/resume with state

### Key Components

- **CLIAdapter**: Subprocess wrapper for CLI commands
- **EditMerger**: AC-3 constraint propagation for pause/resume
- **ThemePlacer**: Optimal theme word placement suggestions
- **BlackSquareSuggester**: Strategic black square placement
- **WordlistResolver**: Flexible wordlist path resolution

### Performance

- Fast operations: <100ms (normalize, number)
- Medium operations: <1s (pattern search)
- Long operations: minutes (autofill with progress tracking)
- Subprocess overhead: ~120ms (acceptable, optimizable)

### Testing

- 165/165 tests passing
- 92% backend coverage
- Unit tests: validators, edit merging, format conversion
- Integration tests: all API endpoints, pause/resume, SSE

### Security

- Input validation before CLI invocation
- No shell injection risk (subprocess with list args)
- Path traversal protection
- CORS protection
- No secrets/credentials needed (local-only tool)

---

**End of Backend Specification**
