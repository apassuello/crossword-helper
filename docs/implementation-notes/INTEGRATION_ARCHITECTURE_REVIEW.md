# Integration Architecture Review: Critical Data Format Bug Analysis

## Executive Summary

A critical data format mismatch was discovered in the integration between the frontend, backend, and CLI components. The bug occurred because:

1. **Frontend sends**: Grid data as objects with `{letter: "A", isBlack: false}`
2. **Backend expects**: To forward this to CLI after transformation
3. **CLI expects**: Simple string arrays like `["A", "#", "."]`

The transformation logic exists in `routes.py` lines 201-218 for the `/api/fill` endpoint, but similar bugs likely exist in other integration points. This architectural review identifies the root causes and provides recommendations to prevent this class of bugs.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  Data Format: {letter: "A", isBlack: false, number: null, ...}  │
└─────────────────────────┬────────────────────────────────────────┘
                          │ HTTP/JSON
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Backend API Layer (Flask)                     │
│                        /backend/api/routes.py                    │
│  • /api/pattern     → delegates to CLI                           │
│  • /api/number      → delegates to CLI                           │
│  • /api/normalize   → delegates to CLI                           │
│  • /api/fill        → TRANSFORMS data then delegates to CLI      │
└─────────────────────────┬────────────────────────────────────────┘
                          │ Subprocess + JSON files
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│                   CLI Adapter Layer                              │
│                 /backend/core/cli_adapter.py                     │
│  • Writes grid data to temp JSON file                            │
│  • Executes CLI subprocess                                       │
│  • Parses JSON output                                            │
└─────────────────────────┬────────────────────────────────────────┘
                          │ Temp JSON files
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Tool (Python)                        │
│                       /cli/src/core/grid.py                      │
│  Data Format: ["A", "#", "."] - simple strings                   │
│  • Grid.from_dict() expects string arrays                        │
│  • Lines 313-326 parse cell values                               │
└───────────────────────────────────────────────────────────────────┘
```

## Data Format Contracts

### Frontend Format (Object-based)
```javascript
{
  size: 15,
  grid: [
    [
      {letter: "A", isBlack: false, number: 1, isThemeLocked: false},
      {letter: "", isBlack: true, number: null, isThemeLocked: false},
      {letter: "", isBlack: false, number: null, isThemeLocked: false}
    ],
    // ... more rows
  ]
}
```

### CLI Format (String-based)
```json
{
  "size": 15,
  "grid": [
    ["A", "#", ".", "B", "C"],
    // ... more rows with simple strings
  ]
}
```

## Integration Points Analysis

### 1. `/api/fill` endpoint ✅ HAS TRANSFORMATION
- **Location**: `backend/api/routes.py` lines 201-218, 382-399
- **Status**: CORRECTLY transforms from object to string format
- **Code**:
```python
# Lines 201-218 handle regular fill
cli_grid = []
for row in data["grid"]:
    cli_row = []
    for cell in row:
        if isinstance(cell, dict):
            if cell.get("isBlack", False):
                cli_row.append("#")
            elif cell.get("letter", ""):
                cli_row.append(cell["letter"].upper())
            else:
                cli_row.append(".")
        else:
            # Already in CLI format (string)
            cli_row.append(cell)
    cli_grid.append(cli_row)
```

### 2. `/api/number` endpoint ❌ NO TRANSFORMATION
- **Location**: `backend/api/routes.py` lines 95-136
- **Status**: MISSING transformation - passes data directly to CLI
- **Bug**: Line 121 passes raw data without checking format
```python
# Line 121 - BUG: No transformation!
result = cli_adapter.number(grid_data=data, allow_nonstandard=allow_nonstandard)
```

### 3. `/api/pattern` endpoint ✅ NO GRID INVOLVED
- **Location**: `backend/api/routes.py` lines 51-93
- **Status**: Safe - only handles pattern strings, not grids

### 4. `/api/normalize` endpoint ✅ NO GRID INVOLVED
- **Location**: `backend/api/routes.py` lines 138-171
- **Status**: Safe - only handles text normalization

## Root Cause Analysis

### 1. Inconsistent Data Contract Documentation
- **Problem**: No formal schema definition between layers
- **Evidence**: API spec (`docs/phase1-webapp/02-api-specification.md`) shows string format for grids, but frontend actually sends objects
- **Impact**: Developers implement based on incomplete understanding

### 2. No Contract Validation at Boundaries
- **Problem**: No runtime validation of data formats
- **Evidence**: `cli_adapter.py` writes data directly to JSON without validation
- **Impact**: Format mismatches only discovered at runtime in CLI

### 3. Transformation Logic Duplicated and Inconsistent
- **Problem**: Grid transformation code duplicated in multiple places
- **Evidence**:
  - `/api/fill` lines 201-218
  - `/api/fill/with-progress` lines 382-399
  - Missing from `/api/number`
- **Impact**: Easy to miss transformations, hard to maintain

### 4. Tests Don't Verify Integration Contract
- **Problem**: Tests use string format, not the actual object format from frontend
- **Evidence**: `backend/tests/test_api.py` line 169 uses string arrays:
```python
'grid': [
    ['R', 'A', 'T', '#', '.', '.', '.', '.', '.', '.', '.'],
    # ... strings, not objects
]
```
- **Impact**: Tests pass but real integration fails

## Architectural Flaws

### 1. Subprocess Pattern Creates Hidden Dependencies
- **Issue**: CLI tool is a separate process with its own data expectations
- **Problem**: No compile-time checking of data contracts
- **Risk**: Changes to CLI break backend silently

### 2. No Shared Data Model
- **Issue**: Frontend, backend, and CLI each have their own grid representations
- **Problem**: No single source of truth for data structures
- **Risk**: Drift between components over time

### 3. Adapter Layer Lacks Abstraction
- **Issue**: `CLIAdapter` is a thin wrapper, not a true adapter
- **Problem**: Doesn't abstract away CLI's data format requirements
- **Risk**: Leaks CLI implementation details to API layer

## Additional Bugs Found

### Bug #1: `/api/number` Missing Transformation
```python
# backend/api/routes.py line 121
# BUG: Should transform grid data like /api/fill does
result = cli_adapter.number(grid_data=data, allow_nonstandard=allow_nonstandard)
```

### Bug #2: Frontend Numbering Uses Wrong Format
```javascript
// src/App.jsx lines 194-198
// Transforms for /api/fill but not for /api/number
grid: grid.map(row => row.map(cell =>
    cell.isBlack ? '#' : (cell.letter || '.')
)),
```

### Bug #3: Tests Use Wrong Data Format
```python
# backend/tests/test_api.py
# All grid tests use string format, not object format
# This means tests don't catch integration bugs
```

## Recommendations

### 1. Immediate Fixes (High Priority)

#### Fix `/api/number` endpoint
```python
# Add transformation before calling CLI adapter
if 'grid' in data and isinstance(data['grid'][0][0], dict):
    cli_grid = []
    for row in data["grid"]:
        cli_row = []
        for cell in row:
            if isinstance(cell, dict):
                if cell.get("isBlack", False):
                    cli_row.append("#")
                elif cell.get("letter", ""):
                    cli_row.append(cell["letter"].upper())
                else:
                    cli_row.append(".")
            else:
                cli_row.append(cell)
        cli_grid.append(cli_row)
    data = {**data, 'grid': cli_grid}
```

#### Create Centralized Transformation Function
```python
# backend/core/grid_transformer.py
def frontend_to_cli_grid(frontend_grid):
    """Transform frontend grid format to CLI format."""
    cli_grid = []
    for row in frontend_grid:
        cli_row = []
        for cell in row:
            if isinstance(cell, dict):
                if cell.get("isBlack", False):
                    cli_row.append("#")
                elif cell.get("letter", ""):
                    cli_row.append(cell["letter"].upper())
                else:
                    cli_row.append(".")
            else:
                # Already in CLI format
                cli_row.append(cell)
        cli_grid.append(cli_row)
    return cli_grid
```

### 2. Medium-term Improvements

#### Use Pydantic for Data Validation
```python
# backend/models/grid.py
from pydantic import BaseModel
from typing import List, Union, Optional

class FrontendCell(BaseModel):
    letter: Optional[str] = ""
    isBlack: bool = False
    number: Optional[int] = None
    isThemeLocked: bool = False

class FrontendGrid(BaseModel):
    size: int
    grid: List[List[FrontendCell]]

class CLIGrid(BaseModel):
    size: int
    grid: List[List[str]]  # Only strings: "A", "#", "."

def transform_grid(frontend: FrontendGrid) -> CLIGrid:
    """Type-safe transformation with validation."""
    # ... transformation logic
```

#### Add Contract Tests
```python
# backend/tests/test_integration_contracts.py
def test_frontend_to_cli_transformation():
    """Test actual frontend format transforms correctly."""
    frontend_data = {
        "size": 3,
        "grid": [
            [{"letter": "A", "isBlack": False}, {"letter": "", "isBlack": True}],
            # ... actual frontend format
        ]
    }

    cli_data = transform_grid(frontend_data)
    assert cli_data["grid"][0][0] == "A"
    assert cli_data["grid"][0][1] == "#"
```

### 3. Long-term Architecture Improvements

#### Option A: Shared Python Package
Create a shared package with data models that both backend and CLI import:
```
crossword-common/
├── __init__.py
├── models.py      # Shared data models
├── validators.py  # Shared validation
└── transformers.py # Format conversions
```

#### Option B: Remove Subprocess Architecture
Instead of subprocess, import CLI as a Python module:
```python
# Instead of subprocess
from cli.src.core.grid import Grid
from cli.src.fill.autofill import Autofill

# Direct Python calls, no serialization needed
grid = Grid.from_frontend_format(data)
result = autofill.fill(grid)
```

#### Option C: Use Protocol Buffers or JSON Schema
Define contracts formally and generate code:
```yaml
# grid.schema.json
{
  "type": "object",
  "properties": {
    "size": {"type": "integer"},
    "grid": {
      "type": "array",
      "items": {
        "type": "array",
        "items": {
          "oneOf": [
            {"type": "string", "pattern": "^[A-Z#.]$"},
            {"type": "object", "properties": {...}}
          ]
        }
      }
    }
  }
}
```

## Testing Strategy

### 1. Add Integration Tests with Real Data
```python
def test_full_stack_integration():
    """Test with actual frontend data format."""
    # Capture real request from browser
    actual_frontend_request = {
        "grid": [[{"letter": "A", "isBlack": False}]],
        # ... real data
    }

    response = client.post('/api/fill', json=actual_frontend_request)
    assert response.status_code == 200
```

### 2. Add Contract Verification Tests
```python
def test_cli_accepts_transformed_data():
    """Verify CLI can parse our transformed output."""
    frontend_data = load_fixture('frontend_grid.json')
    cli_data = transform_grid(frontend_data)

    # Actually invoke CLI to verify it works
    result = subprocess.run(['cli', 'validate'],
                          input=json.dumps(cli_data))
    assert result.returncode == 0
```

### 3. Add Boundary Tests
```python
@pytest.mark.parametrize("endpoint", ["/api/fill", "/api/number"])
def test_endpoints_handle_both_formats(endpoint):
    """Each endpoint should handle both formats gracefully."""
    # Test with frontend format
    # Test with CLI format
    # Both should work
```

## Conclusion

The critical bug was caused by:
1. **Inconsistent data contracts** between layers
2. **Missing transformation logic** in some endpoints
3. **No validation** at integration boundaries
4. **Tests using wrong data format**

The subprocess architecture, while providing isolation, creates hidden dependencies that are difficult to test and maintain. The recommended approach is to:

1. **Immediately**: Fix the `/api/number` endpoint and centralize transformation logic
2. **Short-term**: Add Pydantic validation and contract tests
3. **Long-term**: Consider removing subprocess architecture or formalizing contracts with schemas

This class of bugs (data format mismatches at integration boundaries) is completely preventable with proper contract definition, validation, and testing.

## Action Items

- [ ] Fix `/api/number` endpoint transformation
- [ ] Create centralized `grid_transformer.py`
- [ ] Update all endpoints to use centralized transformation
- [ ] Add integration tests with real frontend data
- [ ] Add Pydantic models for data validation
- [ ] Update API documentation with actual data formats
- [ ] Consider architectural refactoring to remove subprocess dependency