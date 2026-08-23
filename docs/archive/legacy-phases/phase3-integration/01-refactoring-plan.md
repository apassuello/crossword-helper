# Phase 3: Integration - Refactoring Plan

**Version:** 1.0
**Date:** 2025-11-18
**Status:** Ready for Implementation
**Prerequisites:** Phase 1 ✅ Phase 2 ✅

---

## Executive Summary

Refactor the web application (Phase 1) to use the CLI tool (Phase 2) as its backend implementation, creating a unified codebase with dual interfaces (web + CLI).

**Timeline:** 1 week (5-7 days)
**Complexity:** Medium
**Value:** High (eliminates code duplication, adds autofill to web)

---

## Current State Analysis

### Phase 1 (Webapp) - Standalone
```
backend/
├── api/routes.py           # Direct implementations
│   ├── /api/pattern        → PatternMatcher (OneLook + local)
│   ├── /api/number         → NumberingValidator
│   └── /api/normalize      → ConventionHelper
├── core/
│   ├── pattern_matcher.py  # ~50 lines
│   ├── numbering.py        # ~80 lines
│   └── conventions.py      # ~30 lines
```

### Phase 2 (CLI) - Standalone
```
cli/
├── crossword               # Entry point
├── src/cli.py             # Click commands
├── src/core/              # Grid, numbering, validation
├── src/fill/              # Autofill engine (CSP solver)
└── src/export/            # HTML, PDF, .puz
```

### Issues with Current State
- ❌ **Code Duplication:** Numbering logic exists in both phases
- ❌ **Maintenance Burden:** Changes must be applied twice
- ❌ **No Autofill in Web:** Users must use CLI for autofill
- ❌ **Divergence Risk:** Phase 1 and Phase 2 implementations drift apart
- ⚠️ **Already Fixed:** Grid format compatibility, word scoring

---

## Target Architecture

### After Integration
```
Frontend (Browser)
    ↓ HTTP
Backend API (Flask)
    ↓ subprocess calls
CLI Tool (Python)
    ↓
Shared Implementations
    ├── Grid Engine
    ├── Autofill (CSP)
    ├── Pattern Matching
    ├── Numbering
    └── Export

→ Single source of truth
→ Web UI + CLI both use same code
```

### API Evolution
```python
# Before (Phase 1)
@api.route('/pattern', methods=['POST'])
def pattern_search():
    results = pattern_matcher.search(...)  # Direct call
    return jsonify(results)

# After (Phase 3)
@api.route('/pattern', methods=['POST'])
def pattern_search():
    # Call CLI tool via subprocess
    result = subprocess.run(['crossword', 'pattern', pattern], ...)
    return jsonify(parse_cli_output(result))
```

---

## Implementation Plan

### Phase 3.1: CLI Command Parity (2 days)

**Goal:** Add CLI commands that match web API functionality

#### Tasks

**1. Add `crossword pattern` command**
```bash
crossword pattern "C?T" --wordlists standard.txt --max-results 20
# Output: JSON array of {word, score, source}
```

**Implementation:**
- Add to `cli/src/cli.py`
- Use existing `PatternMatcher`
- Output JSON to stdout
- Handle OneLook API integration

**2. Add `crossword number` command**
```bash
crossword number grid.json
# Output: JSON object with numbering {(row,col): number}
```

**Implementation:**
- Already exists in Phase 2
- Verify JSON output format matches Phase 1

**3. Add `crossword normalize` command**
```bash
crossword normalize "Tina Fey"
# Output: JSON {original: "Tina Fey", normalized: "TINAFEY"}
```

**Implementation:**
- Add convention helper to CLI
- Match Phase 1 normalization rules

**Testing:**
```bash
# Test each CLI command produces same output as web API
pytest cli/tests/integration/test_cli_parity.py
```

---

### Phase 3.2: Web API Subprocess Integration (2 days)

**Goal:** Refactor Flask routes to call CLI tool

#### Architecture Pattern

```python
# backend/api/cli_adapter.py - New module
class CLIAdapter:
    """Adapter for calling CLI tool from web API."""

    def __init__(self, cli_path='crossword'):
        self.cli_path = cli_path

    def call_cli(self, args, input_data=None, timeout=30):
        """
        Call CLI tool and parse output.

        Args:
            args: List of CLI arguments
            input_data: Optional JSON to pipe to stdin
            timeout: Command timeout in seconds

        Returns:
            Parsed JSON output

        Raises:
            CLIError: If command fails
        """
        cmd = [self.cli_path] + args

        try:
            result = subprocess.run(
                cmd,
                input=json.dumps(input_data) if input_data else None,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )
            return json.loads(result.stdout)

        except subprocess.TimeoutExpired:
            raise CLIError(f"Command timeout after {timeout}s")
        except subprocess.CalledProcessError as e:
            raise CLIError(f"CLI error: {e.stderr}")
        except json.JSONDecodeError:
            raise CLIError("Invalid JSON from CLI")
```

#### Refactor Routes

**Pattern Endpoint:**
```python
# backend/api/routes.py
@api.route('/pattern', methods=['POST'])
def pattern_search():
    try:
        data = validate_pattern_request(request.json)

        # Call CLI instead of direct implementation
        cli = CLIAdapter()
        results = cli.call_cli([
            'pattern',
            data['pattern'],
            '--wordlists', ','.join(data.get('wordlists', ['standard'])),
            '--max-results', str(data.get('max_results', 20))
        ])

        return jsonify({
            'results': results,
            'meta': {
                'pattern': data['pattern'],
                'total_found': len(results),
                'results_returned': len(results)
            }
        }), 200

    except CLIError as e:
        return handle_error('CLI_ERROR', str(e), 500)
```

**Numbering Endpoint:** (Similar pattern)

**Normalize Endpoint:** (Similar pattern)

#### Error Handling

```python
class CLIError(Exception):
    """CLI tool invocation error."""
    pass

def handle_cli_error(error):
    """Convert CLI errors to HTTP responses."""
    return jsonify({
        'error': 'CLI_ERROR',
        'message': str(error),
        'timestamp': datetime.utcnow().isoformat()
    }), 500
```

#### Performance Considerations

- **Subprocess Overhead:** ~50-100ms per call (acceptable)
- **Caching:** Add in-memory LRU cache for repeated requests
- **Optimization:** Keep Phase 1 implementation as fallback if needed

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def pattern_search_cached(pattern, wordlists, max_results):
    """Cached pattern search."""
    return cli.call_cli(['pattern', pattern, ...])
```

---

### Phase 3.3: Autofill Web Integration (2 days)

**Goal:** Add autofill feature to web application

#### New API Endpoint

```python
# backend/api/routes.py
@api.route('/fill', methods=['POST'])
def fill_grid():
    """
    Auto-fill crossword grid using CSP solver.

    Request:
    {
        "grid": [[...]],
        "size": 15,
        "wordlists": ["standard.txt"],
        "timeout": 300,
        "min_score": 30
    }

    Response:
    {
        "success": true,
        "grid": [[...]],  # Filled grid
        "time_elapsed": 45.2,
        "slots_filled": 78,
        "total_slots": 78,
        "iterations": 1523
    }
    """
    try:
        data = validate_fill_request(request.json)

        # Save grid to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'size': data['size'], 'grid': data['grid']}, f)
            grid_file = f.name

        try:
            # Call CLI fill command
            cli = CLIAdapter()
            result = cli.call_cli([
                'fill',
                grid_file,
                '--wordlists', ','.join(data.get('wordlists', [])),
                '--timeout', str(data.get('timeout', 300)),
                '--min-score', str(data.get('min_score', 30)),
                '--output', grid_file  # Overwrite with filled grid
            ], timeout=data.get('timeout', 300) + 10)  # Add buffer

            # Read filled grid
            with open(grid_file, 'r') as f:
                filled_data = json.load(f)

            return jsonify({
                'success': result.get('success', False),
                'grid': filled_data['grid'],
                'time_elapsed': result.get('time_elapsed', 0),
                'slots_filled': result.get('slots_filled', 0),
                'total_slots': result.get('total_slots', 0),
                'iterations': result.get('iterations', 0),
                'problematic_slots': result.get('problematic_slots', [])
            }), 200

        finally:
            # Clean up temp file
            os.unlink(grid_file)

    except CLIError as e:
        return handle_error('FILL_ERROR', str(e), 500)
    except Exception as e:
        return handle_error('INTERNAL_ERROR', str(e), 500)
```

#### Frontend Component

**New Page: `frontend/templates/fill.html`**

```html
<!DOCTYPE html>
<html>
<head>
    <title>Autofill Grid</title>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <div class="container">
        <h1>Autofill Crossword Grid</h1>

        <div class="input-section">
            <label>Grid JSON:</label>
            <textarea id="grid-input" rows="10"></textarea>

            <label>Word Lists:</label>
            <input type="text" id="wordlists" value="standard.txt">

            <label>Timeout (seconds):</label>
            <input type="number" id="timeout" value="300" min="10" max="1800">

            <label>Min Score:</label>
            <input type="number" id="min-score" value="30" min="0" max="100">

            <button id="fill-btn" onclick="fillGrid()">Fill Grid</button>
            <button id="cancel-btn" onclick="cancelFill()" disabled>Cancel</button>
        </div>

        <div id="progress-section" style="display:none;">
            <h3>Filling in progress...</h3>
            <div class="progress-bar">
                <div id="progress-fill"></div>
            </div>
            <p id="progress-text">Starting...</p>
        </div>

        <div id="results-section"></div>
    </div>

    <script src="/static/js/fill.js"></script>
</body>
</html>
```

**JavaScript: `frontend/static/js/fill.js`**

```javascript
let fillRequest = null;

async function fillGrid() {
    const gridJson = document.getElementById('grid-input').value;
    const wordlists = document.getElementById('wordlists').value.split(',');
    const timeout = parseInt(document.getElementById('timeout').value);
    const minScore = parseInt(document.getElementById('min-score').value);

    let gridData;
    try {
        gridData = JSON.parse(gridJson);
    } catch (e) {
        showError('Invalid JSON format');
        return;
    }

    // Show progress
    document.getElementById('progress-section').style.display = 'block';
    document.getElementById('fill-btn').disabled = true;
    document.getElementById('cancel-btn').disabled = false;

    try {
        const response = await fetch('/api/fill', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                grid: gridData.grid,
                size: gridData.size,
                wordlists: wordlists,
                timeout: timeout,
                min_score: minScore
            })
        });

        const result = await response.json();

        if (result.success) {
            displayFilledGrid(result);
        } else {
            showError('Fill failed. Check problematic slots.');
            displayProblematicSlots(result.problematic_slots);
        }

    } catch (error) {
        showError('Error: ' + error.message);
    } finally {
        document.getElementById('progress-section').style.display = 'none';
        document.getElementById('fill-btn').disabled = false;
        document.getElementById('cancel-btn').disabled = true;
    }
}

function displayFilledGrid(result) {
    const container = document.getElementById('results-section');

    let html = '<div class="success">';
    html += `<h3>✅ Fill Successful!</h3>`;
    html += `<p>Filled ${result.slots_filled} of ${result.total_slots} slots</p>`;
    html += `<p>Time: ${result.time_elapsed.toFixed(2)}s</p>`;
    html += `<p>Iterations: ${result.iterations}</p>`;
    html += '</div>';

    html += '<h3>Filled Grid:</h3>';
    html += '<pre>' + JSON.stringify({size: result.grid.length, grid: result.grid}, null, 2) + '</pre>';

    container.innerHTML = html;
}
```

#### Progress Tracking (Optional Enhancement)

For long-running fills, implement WebSocket or polling:

```python
# Option 1: Simple polling with status file
@api.route('/fill/status/<job_id>', methods=['GET'])
def fill_status(job_id):
    """Check fill progress."""
    status_file = f'/tmp/fill_{job_id}_status.json'
    if os.path.exists(status_file):
        with open(status_file, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({'status': 'not_found'}), 404
```

---

### Phase 3.4: Testing & Optimization (1 day)

#### Integration Tests

**Test File: `backend/tests/test_integration.py`**

```python
"""Integration tests for Phase 3."""

def test_pattern_via_cli(client):
    """Test pattern search calls CLI correctly."""
    response = client.post('/api/pattern', json={'pattern': 'C?T'})
    assert response.status_code == 200
    data = response.json
    assert 'results' in data
    # Verify results match CLI output

def test_number_via_cli(client):
    """Test numbering calls CLI correctly."""
    grid_data = {
        'size': 11,
        'grid': [['R', 'A', 'T'] + ['#'] * 8] + [['.'] * 11] * 10
    }
    response = client.post('/api/number', json=grid_data)
    assert response.status_code == 200
    # Verify numbering matches CLI output

def test_fill_integration(client):
    """Test autofill integration."""
    grid_data = {
        'size': 11,
        'grid': [['.'] * 11] * 11
    }
    response = client.post('/api/fill', json=grid_data)
    assert response.status_code == 200
    # May timeout or fail with empty word lists, just verify endpoint works
```

#### Performance Benchmarks

```python
import time

def benchmark_api_overhead():
    """Measure subprocess overhead."""
    # Direct call (Phase 1)
    start = time.time()
    result = pattern_matcher.search('C?T')
    direct_time = time.time() - start

    # CLI call (Phase 3)
    start = time.time()
    result = cli.call_cli(['pattern', 'C?T'])
    cli_time = time.time() - start

    overhead = cli_time - direct_time
    print(f"Subprocess overhead: {overhead*1000:.2f}ms")
    assert overhead < 0.2  # Less than 200ms acceptable
```

#### Backward Compatibility

```python
def test_api_contracts_unchanged():
    """Ensure API responses match Phase 1 format."""
    # All existing tests should still pass
    # Response schemas must be identical
```

---

## Migration Checklist

### Pre-Migration
- [x] Phase 2 complete and tested
- [x] Phase 1 still functional
- [x] Create Phase 3 branch

### Phase 3.1: CLI Parity
- [ ] Implement `crossword pattern` command
- [ ] Implement `crossword normalize` command
- [ ] Verify `crossword number` output format
- [ ] Test CLI commands produce matching output
- [ ] Write integration tests

### Phase 3.2: Web Refactoring
- [ ] Create `CLIAdapter` module
- [ ] Refactor `/api/pattern` to use CLI
- [ ] Refactor `/api/number` to use CLI
- [ ] Refactor `/api/normalize` to use CLI
- [ ] Add error handling
- [ ] Add caching layer
- [ ] Test all existing endpoints work

### Phase 3.3: Autofill Feature
- [ ] Add `/api/fill` endpoint
- [ ] Create fill.html page
- [ ] Implement fill.js frontend
- [ ] Add validation for fill requests
- [ ] Test with small grids (3×3, 5×5)
- [ ] Test with standard grids (11×11, 15×15)
- [ ] Add progress tracking (optional)

### Phase 3.4: Testing
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Performance benchmarks acceptable
- [ ] Backward compatibility verified
- [ ] Documentation updated

### Post-Migration
- [ ] Deploy to production
- [ ] Monitor performance
- [ ] Collect user feedback
- [ ] Remove deprecated Phase 1 implementations

---

## Rollback Plan

If integration fails or performance unacceptable:

**Option 1: Feature Flag**
```python
USE_CLI_BACKEND = os.environ.get('USE_CLI_BACKEND', 'false') == 'true'

if USE_CLI_BACKEND:
    results = cli.call_cli(['pattern', pattern])
else:
    results = pattern_matcher.search(pattern)  # Original
```

**Option 2: Revert Commits**
```bash
git revert <phase-3-commits>
```

**Option 3: Keep Both**
- Keep Phase 1 implementation as primary
- CLI as alternative (power users)
- Gradually migrate endpoints

---

## Success Metrics

### Functional
- ✅ All Phase 1 features still work
- ✅ Autofill available in web UI
- ✅ CLI commands produce correct output
- ✅ Error handling works correctly

### Performance
- ✅ API response time < +100ms vs Phase 1
- ✅ Autofill completes in reasonable time
- ✅ No memory leaks
- ✅ Subprocess cleanup works

### Code Quality
- ✅ Test coverage maintained (>85%)
- ✅ No code duplication
- ✅ Single source of truth
- ✅ Clean error handling

### User Experience
- ✅ No breaking changes to API
- ✅ Web UI responsive during fills
- ✅ Progress indication works
- ✅ Error messages clear

---

## Timeline

| Phase | Tasks | Duration | Status |
|-------|-------|----------|--------|
| 3.1 | CLI Parity | 2 days | Pending |
| 3.2 | Web Refactor | 2 days | Pending |
| 3.3 | Autofill Feature | 2 days | Pending |
| 3.4 | Testing | 1 day | Pending |
| **Total** | - | **7 days** | - |

---

## Next Steps

1. Create Phase 3 branch
2. Begin with Phase 3.1 (CLI Parity)
3. Implement incrementally
4. Test continuously
5. Document learnings

---

*Ready to begin implementation. All prerequisites met.*
