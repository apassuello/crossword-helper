# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Crossword Construction Helper

A comprehensive crossword puzzle construction toolkit with web interface and CLI tools, implementing a **CLI-as-single-source-of-truth architecture**.

**Current Status:** All 3 development phases complete (165/165 tests passing)

---

## Quick Start

### Development Setup

```bash
# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
npm install

# Run development servers
# Terminal 1: Flask backend
python run.py                    # → http://localhost:5000

# Terminal 2: Vite dev server (hot reload)
npm run dev                      # → http://localhost:3000
```

### Production Build

```bash
# Build frontend once
npm run build

# Run Flask (serves built frontend)
python run.py                    # → http://localhost:5000
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov=cli --cov-report=html

# Run specific test suite
pytest backend/tests/unit/ -v
pytest backend/tests/integration/ -v
pytest cli/tests/ -v

# Run single test
pytest backend/tests/unit/test_cli_adapter.py::test_pattern -vv
```

### CLI Usage

```bash
# Create new grid
python -m cli.src.cli new --size 15 -o puzzle.json

# Validate grid
python -m cli.src.cli validate puzzle.json

# Fill grid with autofill
python -m cli.src.cli fill puzzle.json \
  -w data/wordlists/comprehensive.txt \
  -t 180 --min-score 30 -o filled.json

# Pattern search
python -m cli.src.cli pattern "C?T" \
  -w data/wordlists/comprehensive.txt \
  --algorithm trie --json-output

# Export to PDF or HTML
python -m cli.src.cli export filled.json --format html -o puzzle.html
```

---

## Architecture Overview

### CLI as Single Source of Truth

The key architectural principle is that **all business logic lives in the CLI tool**. The web backend is a thin HTTP wrapper that executes CLI commands via subprocess.

```
React Frontend (src/)
    ↓ HTTP + Server-Sent Events
Flask Backend (backend/)
    ↓ subprocess.run()
CLI Tool (cli/src/)
    ↓ Core algorithms
NumPy + Pattern Matching + CSP Autofill
```

**Why this works:**
- No code duplication (one implementation, two interfaces)
- Easy testing (test logic once, both interfaces benefit)
- Clear separation (HTTP concerns vs. crossword logic)
- ~100-300ms subprocess overhead is negligible for operations that take 30s-5min

### Technology Stack

**Backend:**
- Flask 3.0 (web framework)
- Python 3.9+ (all backend code)
- CLIAdapter pattern (subprocess execution)
- Server-Sent Events (real-time progress)

**Frontend:**
- React 18 (UI framework)
- Vite 5 (build tool with hot reload)
- SCSS (styling)
- Axios (HTTP client)

**CLI:**
- Click (CLI framework)
- NumPy (grid operations)
- CSP + Beam Search + Hybrid (autofill algorithms)
- Trie-based pattern matching (10-50x faster than regex)

**Data:**
- 454k+ words across multiple wordlists
- JSON for grid state
- Gzipped JSON for pause/resume state
- File-based progress tracking

---

## Project Structure

```
crossword-helper/
├── backend/                    # Flask API (thin wrapper around CLI)
│   ├── api/                    # API routes (6 blueprints, 20+ endpoints)
│   │   ├── routes.py           # Core endpoints (pattern, number, fill)
│   │   ├── grid_routes.py      # Grid operations
│   │   ├── theme_routes.py     # Theme entry management
│   │   ├── pause_resume_routes.py  # Pause/resume autofill
│   │   ├── wordlist_routes.py  # Wordlist management
│   │   └── progress_routes.py  # SSE progress streaming
│   ├── core/                   # Backend logic
│   │   ├── cli_adapter.py      # Subprocess execution (THE INTEGRATION POINT)
│   │   ├── edit_merger.py      # Grid edit validation
│   │   ├── theme_placer.py     # Theme word suggestions
│   │   ├── black_square_suggester.py  # Strategic black square placement
│   │   └── wordlist_resolver.py  # Wordlist path resolution
│   ├── data/                   # Data access layer
│   ├── tests/                  # Backend tests (165 passing)
│   └── app.py                  # Flask app factory
│
├── cli/                        # CLI tool (SINGLE SOURCE OF TRUTH)
│   └── src/
│       ├── cli.py              # Click commands (8 commands)
│       ├── core/               # Grid, numbering, validation, scoring
│       │   ├── grid.py         # Grid data structure (NumPy)
│       │   ├── numbering.py    # Auto-numbering algorithm
│       │   ├── validator.py    # Constraint validation
│       │   ├── conventions.py  # Entry normalization
│       │   ├── scoring.py      # Word quality scoring
│       │   └── progress.py     # Progress tracking
│       ├── fill/               # Autofill algorithms
│       │   ├── autofill.py     # CSP with backtracking + AC-3
│       │   ├── beam_search/    # Beam search orchestrator
│       │   ├── pattern_matcher.py  # Regex pattern matching
│       │   ├── trie_matcher.py # Trie-based (10-50x faster)
│       │   ├── word_list.py    # Wordlist management
│       │   ├── state_manager.py  # Pause/resume state
│       │   └── pause_controller.py  # File-based IPC
│       └── export/             # Export formats (HTML, JSON)
│
├── src/                        # React frontend
│   ├── App.jsx                 # Main app component
│   ├── components/             # React components (20+)
│   │   ├── GridEditor.jsx      # Interactive crossword grid
│   │   ├── AutofillPanel.jsx   # Autofill controls + progress
│   │   ├── PatternMatcher.jsx  # Pattern search UI
│   │   ├── WordlistPanel.jsx   # Wordlist management
│   │   └── ThemePlacer.jsx     # Theme word placement
│   ├── hooks/                  # Custom React hooks
│   └── styles/                 # SCSS styles
│
├── data/wordlists/             # 454k+ words
│   ├── comprehensive.txt       # All words
│   ├── core/                   # Curated core lists
│   └── themed/                 # Specialty lists
│
├── docs/                       # Comprehensive documentation
│   ├── README.md               # Documentation navigation
│   ├── ARCHITECTURE.md         # System architecture (1,842 lines)
│   ├── ROADMAP.md              # Development history
│   ├── specs/                  # Component specifications
│   │   ├── CLI_SPEC.md         # CLI specification
│   │   ├── BACKEND_SPEC.md     # Backend API specification
│   │   └── FRONTEND_SPEC.md    # Frontend specification
│   └── api/                    # API documentation
│       ├── openapi.yaml        # OpenAPI 3.1.0 spec
│       └── API_REFERENCE.md    # Human-readable API reference
│
├── run.py                      # Flask dev server launcher
├── requirements.txt            # Python dependencies
├── package.json                # Node dependencies
├── pytest.ini                  # Test configuration
└── vite.config.js              # Vite build config
```

---

## Key Components

### CLIAdapter: The Integration Bridge

**Location:** `backend/core/cli_adapter.py`

This is the **critical integration point** between web and CLI. It executes CLI commands via subprocess and parses JSON output.

**Key methods:**
- `pattern()` - Execute pattern search
- `number()` - Auto-number grid
- `fill()` - Start autofill (async)
- `fill_with_resume()` - Resume paused autofill with edits

**Example:**
```python
from backend.core.cli_adapter import CLIAdapter

adapter = CLIAdapter()
result = adapter.pattern("C?T", wordlist_paths=["comprehensive.txt"])
# Internally: subprocess.run(['crossword', 'pattern', 'C?T', '--json-output'])
```

### Grid Autofill Algorithms

**Location:** `cli/src/fill/`

Three algorithms with different trade-offs:

1. **CSP with Backtracking** (`autofill.py`)
   - Constraint Satisfaction with AC-3 arc consistency
   - Guaranteed to find solution if one exists
   - Best for: Small grids (11×11)
   - Performance: <30s for 11×11

2. **Beam Search** (`beam_search/orchestrator.py`)
   - Global optimization, maintains top-k solutions
   - Better word quality than CSP
   - Best for: Medium grids (15×15)
   - Performance: 1-5min for 15×15

3. **Hybrid** (default)
   - Starts with Beam Search, falls back to CSP
   - Best all-around performance
   - Best for: All grid sizes
   - Performance: 1-5min for 15×15, 5-30min for 21×21

### Pause/Resume System

**How it works:**
1. User pauses autofill → backend writes pause signal file
2. CLI detects signal → serializes complete algorithm state to gzipped JSON
3. User manually edits grid (add/remove/change letters)
4. User resumes → backend validates edits, CLI loads state + applies edits
5. Autofill continues from exact position with edited cells locked

**State includes:**
- Grid state (partially filled)
- Algorithm position (backtrack stack or beam)
- Candidate lists for each slot
- Constraint propagation state
- Iteration count

### Pattern Matching

**Location:** `cli/src/fill/`

Three implementations:

1. **Regex** (`pattern_matcher.py`) - Simple, ~100ms for 454k words
2. **Trie** (`trie_matcher.py`) - 10-50x faster, ~10ms for 454k words (default)
3. **Aho-Corasick** (`ahocorasick_matcher.py`) - Fastest for batch operations

---

## Development Patterns

### Adding a New API Endpoint

1. **Add CLI command** (if new functionality)
   ```python
   # cli/src/cli.py
   @click.command()
   @click.argument('grid_file')
   def my_command(grid_file):
       # Business logic here
       result = do_work(grid_file)
       click.echo(json.dumps(result))
   ```

2. **Add CLIAdapter method**
   ```python
   # backend/core/cli_adapter.py
   def my_operation(self, grid_data):
       cmd = ['crossword', 'my-command', grid_file]
       result = subprocess.run(cmd, capture_output=True, text=True)
       return json.loads(result.stdout)
   ```

3. **Add Flask route**
   ```python
   # backend/api/routes.py
   @api.route('/my-endpoint', methods=['POST'])
   def my_endpoint():
       data = request.json
       result = cli_adapter.my_operation(data)
       return jsonify(result)
   ```

4. **Add frontend integration**
   ```javascript
   // src/components/MyComponent.jsx
   const handleClick = async () => {
       const response = await axios.post('/api/my-endpoint', data);
       setResult(response.data);
   };
   ```

### Testing Best Practices

**Unit tests:**
- Mock subprocess calls (fast tests)
- Test business logic in isolation
- Use pytest fixtures for common data

**Integration tests:**
- Use Flask test client (no actual HTTP)
- Test real CLI subprocess execution
- Verify JSON output formats

**Example:**
```python
def test_pattern_search(cli_adapter, mocker):
    # Mock subprocess
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value.stdout = '{"results": [{"word": "CAT", "score": 90}]}'

    # Test
    result = cli_adapter.pattern("C?T", ["comprehensive.txt"])

    # Assert
    assert result['results'][0]['word'] == 'CAT'
    mock_run.assert_called_once()
```

### Performance Considerations

**API Response Times:**
- `/api/health`: ~30ms (no CLI call)
- `/api/pattern`: 150-300ms (CLI overhead + trie search)
- `/api/number`: 120-180ms (CLI overhead + numbering)
- `/api/fill` (start): 200-400ms (spawns subprocess, returns task ID)
- `/api/fill` (complete): 30s-5min (actual autofill time)

**Subprocess overhead:** 100-280ms average (acceptable for this use case)

**Memory usage:**
- Backend: ~50-100MB
- CLI process: ~100-500MB (depends on grid size and beam width)
- Frontend: ~10MB

---

## Common Development Tasks

### Running Tests During Development

```bash
# Fast: Unit tests only
pytest backend/tests/unit/ -v

# Quick integration check
pytest backend/tests/integration/test_api.py -v

# Full suite before commit
pytest --cov=backend --cov=cli
```

### Debugging Subprocess Issues

```bash
# Test CLI command directly
python -m cli.src.cli pattern "C?T" --json-output

# Enable subprocess debug logging
FLASK_DEBUG=1 python run.py

# Check specific test with output
pytest backend/tests/integration/test_cli_integration.py::test_pattern -vv -s
```

### Frontend Development

```bash
# Terminal 1: Flask backend
python run.py

# Terminal 2: Vite dev server (hot reload)
npm run dev

# Open http://localhost:3000 (proxies to Flask backend)
```

**Note:** In development mode, Vite proxies API requests from port 3000 to Flask on port 5000 automatically.

### Adding New Wordlists

1. Place `.txt` file in `data/wordlists/` (one word per line, uppercase)
2. Backend automatically discovers new wordlists
3. Frontend wordlist selector updates automatically

---

## Documentation

For comprehensive information, see:

- **[docs/README.md](../docs/README.md)** - Documentation navigation guide
- **[docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)** - Complete system architecture (1,842 lines)
- **[docs/api/API_REFERENCE.md](../docs/api/API_REFERENCE.md)** - API reference (26 endpoints)
- **[docs/specs/](../docs/specs/)** - CLI, Backend, Frontend specifications
- **[docs/ops/TESTING.md](../docs/ops/TESTING.md)** - Testing strategies
- **[docs/dev/DEVELOPMENT.md](../docs/dev/DEVELOPMENT.md)** - Developer onboarding

---

## Known Issues & Limitations

### Working Features ✅
- Custom wordlists
- Multiple wordlist support
- Pattern matching (all algorithms)
- Grid validation
- Autofill (all algorithms)
- Pause/resume autofill
- Theme entry locking (web UI)
- Export (PDF, HTML, JSON)
- Real-time progress tracking

### Known Issues ⚠️
- CLI `--theme-entries` flag does NOT preserve theme words
  - **Workaround:** Use web interface for themed puzzles
- CLI `--adaptive` flag does NOT auto-add black squares
  - **Workaround:** Use web interface black square optimizer

---

**Version:** 2.0.0 (All phases complete)
**Last Updated:** December 2025
