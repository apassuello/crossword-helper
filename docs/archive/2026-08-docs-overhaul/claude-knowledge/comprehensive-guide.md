# Crossword Helper - Comprehensive Reference

**Use this when you need detailed information about architecture, API endpoints, testing strategies, or development workflows.**

---

## Architecture Deep Dive

### CLI-as-Single-Source-of-Truth

**Key Principle:** ALL business logic lives in the CLI tool. The web backend is a thin HTTP wrapper.

```
React Frontend (src/) → Axios HTTP requests
    ↓
Flask Backend (backend/) → CLIAdapter (subprocess.run)
    ↓
CLI Tool (cli/src/) → Core algorithms (NumPy, CSP, Pattern Matching)
```

**Critical Integration Point:** `backend/core/cli_adapter.py`
- Every backend API call executes CLI via subprocess
- JSON input/output for all CLI commands
- Subprocess overhead: 100-300ms (acceptable for 30s-5min operations)

---

## Complete API Reference

### Core Endpoints

**Pattern Search:**
```python
POST /api/pattern
{
  "pattern": "C?T",
  "wordlist_paths": ["comprehensive.txt"],
  "algorithm": "trie"  # 10-50x faster than regex
}
Response: {"results": [{"word": "CAT", "score": 95, "length": 3}, ...]}
```

**Auto-Numbering:**
```python
POST /api/number
{"grid": {...}}
Response: {"grid": {...}, "numbered": true}
```

**Autofill (Async with SSE):**
```python
POST /api/fill/with-progress
{
  "grid": {...},
  "wordlist_paths": ["comprehensive.txt"],
  "algorithm": "hybrid",  # CSP + Beam Search
  "timeout": 180
}
Response: {"task_id": "abc123", "progress_url": "/api/progress/abc123"}

# SSE Stream at /api/progress/abc123
data: {"status": "running", "progress": 25, "message": "Filling slot 1,1 ACROSS"}
data: {"status": "completed", "grid": {...}, "stats": {...}}
```

### Theme Endpoints

```python
POST /api/theme/upload              # Upload theme word list
POST /api/theme/suggest-placements  # Get placement suggestions
POST /api/theme/validate            # Validate theme placement
POST /api/theme/apply-placement     # Apply theme word to grid
```

### Wordlist Endpoints

```python
GET    /api/wordlists               # List all (454k+ words)
GET    /api/wordlists/<name>        # Get details
POST   /api/wordlists/<name>        # Create new
PUT    /api/wordlists/<name>        # Update
DELETE /api/wordlists/<name>        # Delete
POST   /api/wordlists/search        # Search across lists
```

### Pause/Resume Endpoints

```python
POST /api/pause                     # Pause autofill, serialize state to gzipped JSON
POST /api/resume                    # Resume with optional grid edits
GET  /api/pause-state               # Check if paused state exists
```

**How Pause/Resume Works:**
1. User pauses → backend writes pause signal file
2. CLI detects signal → serializes algorithm state (backtrack stack, candidates, constraints)
3. User edits grid manually
4. Resume → backend validates edits, CLI loads state + applies edits (locks edited cells)
5. Autofill continues from exact position

---

## Testing Strategy Details

### Test Pyramid (165 tests)

```
Backend Unit Tests (24 files)
├── Mocked subprocess calls (fast, <1s per file)
├── Test CLIAdapter, EditMerger, ThemePlacer
└── pytest with pytest-mock

Backend Integration Tests
├── Real CLI subprocess execution
├── Flask test client (no actual HTTP)
└── Test full request→CLI→response flow

CLI Tests (18 files)
├── Grid operations, numbering, validation
├── Autofill algorithms (CSP, Beam Search, Hybrid)
└── Pattern matching (regex, trie, aho-corasick)

Frontend Tests (5 files)
├── React component tests (vitest + React Testing Library)
├── MSW for API mocking
└── User interaction simulation
```

### Unit Test Pattern (Backend)

```python
# backend/tests/unit/test_cli_adapter.py
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

### Integration Test Pattern (Backend)

```python
# backend/tests/integration/test_api.py
def test_pattern_search_integration(client):
    # Real CLI execution
    response = client.post('/api/pattern', json={
        "pattern": "C?T",
        "wordlist_paths": ["comprehensive.txt"]
    })

    assert response.status_code == 200
    assert len(response.json['results']) > 0
    assert all(word['word'].startswith('C') for word in response.json['results'])
```

### Frontend Test Pattern

```jsx
// src/__tests__/GridEditor.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import GridEditor from '../components/GridEditor';

test('clicking cell selects it', () => {
  const mockOnCellClick = vi.fn();
  render(<GridEditor grid={mockGrid} onCellClick={mockOnCellClick} />);

  fireEvent.click(screen.getByTestId('cell-0-0'));

  expect(mockOnCellClick).toHaveBeenCalledWith(0, 0);
});
```

---

## Development Workflows

### Adding New API Endpoint (TDD)

1. **Write failing test:**
```python
# backend/tests/unit/test_grid_routes.py
def test_rotate_grid(client):
    response = client.post('/api/grid/rotate', json={"grid": {...}})
    assert response.status_code == 200
```

2. **Implement route:**
```python
# backend/api/grid_routes.py
@grid_api.route('/grid/rotate', methods=['POST'])
def rotate_grid():
    grid_data = request.json.get('grid')
    # If CLI functionality exists
    result = cli_adapter.rotate(grid_data)
    # OR implement directly
    rotated = perform_rotation(grid_data)
    return jsonify({"grid": rotated})
```

3. **Add CLI command (if needed):**
```python
# cli/src/cli.py
@click.command()
@click.argument('grid_file')
@click.option('--json-output', is_flag=True)
def rotate(grid_file, json_output):
    grid = load_grid(grid_file)
    rotated = rotate_grid_90(grid)
    if json_output:
        click.echo(json.dumps({"grid": rotated}))
```

4. **Update CLIAdapter:**
```python
# backend/core/cli_adapter.py
def rotate(self, grid_data):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(grid_data, f)
        grid_file = f.name

    cmd = ['python', '-m', 'cli.src.cli', 'rotate', grid_file, '--json-output']
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return json.loads(result.stdout)
```

5. **Verify all tests pass:**
```bash
pytest backend/tests/unit/test_grid_routes.py::test_rotate_grid -v
pytest backend/tests/integration/ -v  # No regressions
```

### Debugging Integration Test Failure

**Systematic approach:**

1. **Reproduce:**
```bash
pytest backend/tests/integration/test_pattern_search.py::test_large_wordlist -vv
```

2. **Test each layer:**
```bash
# Test CLI directly
python -m cli.src.cli pattern "C?T" -w data/wordlists/comprehensive.txt --json-output

# Check JSON parsing
echo '{"pattern": "C?T"}' | python -c "import sys, json; print(json.load(sys.stdin))"

# Check subprocess timeout
time python -m cli.src.cli pattern "C?T" -w data/wordlists/comprehensive.txt --json-output
```

3. **Check common issues:**
- Subprocess timeout too short? (increase in cli_adapter.py)
- Wordlist path resolution? (check wordlist_resolver.py)
- JSON output format changed? (verify CLI output)
- CORS issue? (check browser console, backend/app.py origins)

4. **Add debug logging:**
```python
# backend/core/cli_adapter.py
import logging
logger = logging.getLogger(__name__)

def pattern(self, pattern, wordlist_paths):
    logger.debug(f"Executing pattern search: {pattern}, wordlists: {wordlist_paths}")
    result = subprocess.run(cmd, ...)
    logger.debug(f"CLI output: {result.stdout[:200]}")
    return json.loads(result.stdout)
```

5. **Write regression test:**
```python
def test_pattern_search_large_wordlist_timeout(client):
    """Regression test for timeout on large wordlist"""
    response = client.post('/api/pattern', json={
        "pattern": "???",  # 3-letter words (lots of results)
        "wordlist_paths": ["comprehensive.txt"]  # 454k words
    })
    assert response.status_code == 200
    assert len(response.json['results']) > 100
```

### Adding React Component with Backend Integration

1. **Design component:**
```jsx
// src/components/RotateGridButton.jsx
import React from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';

export default function RotateGridButton({ grid, onGridUpdate }) {
  const handleRotate = async () => {
    try {
      const response = await axios.post('/api/grid/rotate', { grid });
      onGridUpdate(response.data.grid);
      toast.success('Grid rotated!');
    } catch (error) {
      toast.error(`Rotation failed: ${error.response?.data?.error}`);
    }
  };

  return (
    <button onClick={handleRotate} className="rotate-button">
      ↻ Rotate 90°
    </button>
  );
}
```

2. **Write test:**
```jsx
// src/__tests__/RotateGridButton.test.jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import RotateGridButton from '../components/RotateGridButton';

const server = setupServer(
  rest.post('/api/grid/rotate', (req, res, ctx) => {
    return res(ctx.json({ grid: rotatedMockGrid }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('rotates grid on click', async () => {
  const mockOnUpdate = vi.fn();
  render(<RotateGridButton grid={mockGrid} onGridUpdate={mockOnUpdate} />);

  fireEvent.click(screen.getByText('↻ Rotate 90°'));

  await waitFor(() => expect(mockOnUpdate).toHaveBeenCalled());
  expect(mockOnUpdate).toHaveBeenCalledWith(rotatedMockGrid);
});
```

3. **Manual test:**
```bash
# Terminal 1
python run.py

# Terminal 2
npm run dev

# Open http://localhost:3000, click button, verify rotation
```

---

## Performance Characteristics

**API Response Times:**
- `/api/health`: ~30ms (no CLI call)
- `/api/pattern`: 150-300ms (subprocess + trie search ~10ms)
- `/api/number`: 120-180ms (subprocess + numbering ~20ms)
- `/api/fill` (start): 200-400ms (spawn subprocess, return task ID)
- `/api/fill` (complete): 30s-5min (actual autofill - CSP/Beam Search)

**Memory Usage:**
- Backend: ~50-100MB
- CLI process: ~100-500MB (grid size + beam width dependent)
- Frontend: ~10MB

**Subprocess Overhead:**
- Average: 100-280ms
- Acceptable for operations taking 30s-5min
- Trade-off: Simplicity vs performance

---

## Common Integration Patterns

### Server-Sent Events (SSE) for Progress

**Backend:**
```python
# backend/api/progress_routes.py
from flask import Response, stream_with_context
import json

@progress_api.route('/progress/<task_id>', methods=['GET'])
def stream_progress(task_id):
    def generate():
        # Read progress from CLI stdout or progress file
        while True:
            progress_data = read_progress(task_id)
            if progress_data:
                yield f"data: {json.dumps(progress_data)}\n\n"
            if progress_data.get('status') == 'completed':
                break
            time.sleep(0.5)

    return Response(stream_with_context(generate()),
                   mimetype='text/event-stream')
```

**Frontend:**
```jsx
const startAutofill = async () => {
  // Start autofill
  const response = await axios.post('/api/fill/with-progress', {...});
  const { task_id, progress_url } = response.data;

  // Subscribe to progress
  const eventSource = new EventSource(progress_url);

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    setProgress(data.progress);
    setStatus(data.message);

    if (data.status === 'completed') {
      setGrid(data.grid);
      eventSource.close();
    }
  };

  eventSource.onerror = () => {
    toast.error('Progress stream disconnected');
    eventSource.close();
  };
};
```

### CORS Configuration

```python
# backend/app.py
from flask_cors import CORS

CORS(app, origins=[
    'http://localhost:5000',      # Flask server
    'http://127.0.0.1:5000',
    'http://localhost:3000',      # Vite dev server
    'http://127.0.0.1:3000'
])
```

**Vite Proxy (Development):**
```javascript
// vite.config.js
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
});
```

---

## Algorithms Deep Dive

### Autofill Algorithms

**1. CSP with Backtracking (autofill.py)**
- Constraint Satisfaction Problem solver
- AC-3 arc consistency for constraint propagation
- Backtracking search with fail-first heuristic
- Best for: Small grids (11×11)
- Performance: <30s for 11×11

**2. Beam Search (beam_search/orchestrator.py)**
- Maintains top-k solutions (beam width)
- Global optimization across entire grid
- Better word quality than CSP
- Best for: Medium grids (15×15)
- Performance: 1-5min for 15×15

**3. Hybrid (default)**
- Starts with Beam Search
- Falls back to CSP if stuck
- Combines quality + reliability
- Best for: All grid sizes
- Performance: 1-5min for 15×15, 5-30min for 21×21

### Pattern Matching Algorithms

**1. Regex (pattern_matcher.py)**
- Simple, straightforward
- ~100ms for 454k words
- Use for: Simple patterns

**2. Trie (trie_matcher.py) - DEFAULT**
- 10-50x faster than regex
- ~10ms for 454k words
- Prefix-based search
- Use for: All production use

**3. Aho-Corasick (ahocorasick_matcher.py)**
- Fastest for batch operations
- Multiple pattern search
- Use for: Batch processing, multi-pattern search

---

## Known Issues & Workarounds

**CLI `--theme-entries` flag does NOT preserve theme words:**
- Root cause: Theme words not locked during autofill
- Workaround: Use web interface (locks theme words correctly via theme_routes.py)
- Fix location: `cli/src/fill/autofill.py` needs theme locking logic

**CLI `--adaptive` flag does NOT auto-add black squares:**
- Root cause: Adaptive placement not implemented in CLI
- Workaround: Use web interface black square suggester
- Fix location: `backend/core/black_square_suggester.py` → needs CLI equivalent

**Subprocess timeout on large wordlists:**
- Symptom: TimeoutExpired exception in tests
- Root cause: Default timeout too short
- Fix: Increase timeout in `backend/core/cli_adapter.py` (line ~45)
```python
result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)  # Was 10
```

**CORS errors in development:**
- Symptom: "CORS policy" error in browser console
- Root cause: Origin not whitelisted
- Fix: Add origin to `backend/app.py` CORS config

**React component not re-rendering:**
- Symptom: UI doesn't update after API call
- Root cause: State mutation instead of setting new state
- Fix: Use spread operator
```javascript
// Wrong
grid.cells[0][0] = 'A';
setGrid(grid);

// Right
setGrid({
  ...grid,
  cells: grid.cells.map((row, i) =>
    i === 0 ? [...row.slice(0, 0), 'A', ...row.slice(1)] : row
  )
});
```

---

## Git Workflow Best Practices

### Branch Strategy
- `main` - stable, all tests passing
- `feature/<name>` - new features
- `fix/<name>` - bug fixes
- `test/<name>` - test improvements

### Commit Message Convention
```
feat: add grid rotation endpoint
fix: increase subprocess timeout for large wordlists
test: add integration tests for theme validation
docs: update API reference with new endpoints
refactor: extract pattern matching to separate module
perf: optimize trie search for 3-letter patterns
chore: update dependencies
```

### Before Pushing Checklist
- [ ] All tests pass: `pytest && npm test`
- [ ] Frontend builds: `npm run build`
- [ ] No console errors in browser
- [ ] Backend starts without errors: `python run.py`
- [ ] Commit message follows convention
- [ ] No debug code (console.log, print statements)
- [ ] No TODOs/FIXMEs added

---

**Last Updated:** January 2026
**Maintained for:** Detailed reference, troubleshooting, and deep dives
