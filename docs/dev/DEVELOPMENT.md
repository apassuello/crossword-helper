# Development Guide

**Document Type:** Developer Onboarding & Workflow Guide
**Version:** 2.0.0
**Last Updated:** 2025-12-27
**Status:** Complete

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Project Structure](#project-structure)
4. [Development Environment](#development-environment)
5. [Development Workflow](#development-workflow)
6. [Code Style Guidelines](#code-style-guidelines)
7. [Building and Running](#building-and-running)
8. [Debugging](#debugging)
9. [Adding New Features](#adding-new-features)
10. [Working with Dependencies](#working-with-dependencies)
11. [Database and Data](#database-and-data)
12. [Performance Considerations](#performance-considerations)
13. [Common Tasks](#common-tasks)
14. [Troubleshooting](#troubleshooting)
15. [Resources](#resources)

---

## Overview

### What is Crossword Helper?

The Crossword Helper is a comprehensive crossword puzzle construction toolkit that provides both a web interface and command-line tools for creating, filling, and exporting crossword puzzles. It implements a **CLI-as-single-source-of-truth** architecture where all business logic lives in the CLI tool, and the web backend acts as a thin HTTP wrapper.

### Architecture at a Glance

```
┌─────────────────────────────────────┐
│  Frontend (React + Vite)            │
│  - Grid Editor                      │
│  - Autofill Panel                   │
│  - Pattern Matcher                  │
└────────────────┬────────────────────┘
                 │ HTTP + SSE
┌────────────────▼────────────────────┐
│  Backend (Flask)                    │
│  - API Routes (thin wrapper)        │
│  - CLI Adapter (subprocess)         │
└────────────────┬────────────────────┘
                 │ subprocess.run()
┌────────────────▼────────────────────┐
│  CLI Tool (Python + Click)          │
│  - Grid Engine                      │
│  - Autofill Algorithms (CSP/Beam)   │
│  - Pattern Matching                 │
│  - Word List Manager                │
└─────────────────────────────────────┘
```

### Key Technologies

- **Backend:** Python 3.9+, Flask 3.0, Click 8.1
- **Frontend:** React 18, Vite 5, SCSS
- **Algorithms:** NumPy, CSP with backtracking, Beam Search
- **Testing:** pytest 7.4, 165 tests (100% passing), 92% backend coverage
- **Data:** File-based word lists (454k+ words), JSON grid state

### Development Philosophy

1. **Single Source of Truth:** All crossword logic in CLI tool
2. **Test-Driven Development:** Write tests first, then implement
3. **Fast Feedback:** Unit tests complete in <5 seconds
4. **Progressive Enhancement:** Build incrementally with working features
5. **Documentation First:** Document as you build

---

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

**Required:**
- Python 3.9 or higher
- pip 21+
- Node.js 18+
- npm 9+
- Git

**Recommended:**
- virtualenv or venv for Python environment isolation
- VS Code or PyCharm for development
- Chrome or Firefox with DevTools

**System Requirements:**
- 4GB RAM minimum (8GB recommended for large grids)
- 500MB disk space
- macOS, Linux, or Windows (macOS/Linux preferred)

### Installation Steps

#### 1. Clone the Repository

```bash
# Clone the repository
git clone <repository-url>
cd crossword-helper

# Verify you're in the correct directory
pwd  # Should show: /path/to/crossword-helper
```

#### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# Verify Python version
python --version  # Should be 3.9+
```

#### 3. Install Backend Dependencies

```bash
# Install backend dependencies
pip install -r requirements.txt

# Verify Flask installation
python -c "import flask; print(flask.__version__)"  # Should print 3.0.0
```

#### 4. Install CLI Dependencies

```bash
# Navigate to CLI directory
cd cli

# Install CLI dependencies
pip install -r requirements.txt

# Install CLI in editable mode (development)
pip install -e .

# Verify CLI installation
cd ..
crossword --version  # Should print version number

# If crossword command not found, use:
python cli/crossword --version
```

#### 5. Install Frontend Dependencies

```bash
# Install Node.js packages
npm install

# Verify React installation
npm list react  # Should show react@18.2.0
```

#### 6. Verify Installation

```bash
# Run backend health check
python -c "from backend.app import app; print('Backend OK')"

# Run frontend build check
npm run build  # Should complete without errors

# Run test suite
pytest backend/tests/unit/ -v  # Should show passing tests
```

### First-Time Setup Checklist

- [ ] Python 3.9+ installed and accessible
- [ ] Virtual environment created and activated
- [ ] Backend dependencies installed (Flask, pytest, etc.)
- [ ] CLI dependencies installed (Click, NumPy, etc.)
- [ ] CLI installed in editable mode
- [ ] Frontend dependencies installed (React, Vite, etc.)
- [ ] All health checks passing
- [ ] Test suite running successfully

**Estimated Setup Time:** 20-30 minutes

---

## Project Structure

### Directory Layout

```
crossword-helper/
├── backend/                    # Flask API server
│   ├── api/                    # API routes (6 blueprints)
│   │   ├── routes.py           # Core endpoints (pattern, number, normalize)
│   │   ├── grid_routes.py      # Grid operations
│   │   ├── pause_resume_routes.py  # Pause/resume autofill
│   │   ├── theme_routes.py     # Theme entry management
│   │   ├── wordlist_routes.py  # Wordlist operations
│   │   ├── progress_routes.py  # SSE progress streaming
│   │   ├── validators.py       # Request validation
│   │   └── errors.py           # Error handling
│   ├── core/                   # Business logic (thin layer)
│   │   ├── cli_adapter.py      # CLI subprocess execution
│   │   ├── edit_merger.py      # Edit validation for pause/resume
│   │   ├── theme_placer.py     # Theme placement suggestions
│   │   ├── black_square_suggester.py  # Black square recommendations
│   │   └── wordlist_resolver.py  # Wordlist path resolution
│   ├── data/                   # Data access layer
│   │   ├── wordlist_manager.py # Wordlist file management
│   │   └── progress_tracker.py # Progress file I/O
│   ├── tests/                  # Backend test suite
│   │   ├── conftest.py         # Shared fixtures
│   │   ├── fixtures/           # Test data
│   │   ├── unit/               # Fast, isolated tests
│   │   └── integration/        # Component interaction tests
│   └── app.py                  # Flask app factory
│
├── cli/                        # CLI tool (single source of truth)
│   ├── src/
│   │   ├── cli.py              # Click commands (8 commands)
│   │   ├── core/               # Core crossword logic
│   │   │   ├── grid.py         # Grid data structure (NumPy)
│   │   │   ├── numbering.py    # Auto-numbering algorithm
│   │   │   ├── validator.py    # Grid validation (symmetry, etc.)
│   │   │   ├── conventions.py  # Entry normalization rules
│   │   │   ├── scoring.py      # Word quality scoring
│   │   │   ├── cell_types.py   # Cell state enumeration
│   │   │   └── progress.py     # Progress tracking
│   │   ├── fill/               # Autofill algorithms
│   │   │   ├── autofill.py     # CSP with backtracking
│   │   │   ├── beam_search/    # Beam search algorithm
│   │   │   │   ├── orchestrator.py  # Main beam search
│   │   │   │   └── scorer.py   # Beam scoring
│   │   │   ├── pattern_matcher.py  # Regex pattern matching
│   │   │   ├── trie_matcher.py # Trie-based matching (10-50x faster)
│   │   │   ├── ahocorasick_matcher.py  # Aho-Corasick (batch)
│   │   │   ├── word_list.py    # Word list management
│   │   │   ├── state_manager.py  # Pause/resume state
│   │   │   └── pause_controller.py  # Pause signal handling
│   │   └── export/             # Export formats
│   │       ├── html_exporter.py  # HTML grid generation
│   │       └── json_exporter.py  # JSON persistence
│   ├── tests/                  # CLI test suite
│   │   ├── unit/               # Algorithm unit tests
│   │   └── integration/        # CLI command tests
│   └── crossword               # Entry point script
│
├── src/                        # React frontend
│   ├── components/             # UI components
│   │   ├── GridEditor.jsx      # Interactive grid (keyboard nav)
│   │   ├── AutofillPanel.jsx   # Autofill controls + progress
│   │   ├── PatternMatcher.jsx  # Pattern search UI
│   │   ├── WordlistPanel.jsx   # Wordlist management
│   │   ├── ThemePlacer.jsx     # Theme entry placement
│   │   ├── BlackSquareSuggester.jsx  # Black square suggestions
│   │   ├── ProgressBar.jsx     # Real-time progress
│   │   └── ToastNotifications.jsx  # User notifications
│   ├── hooks/                  # Custom React hooks
│   │   ├── useGrid.js          # Grid state management
│   │   └── useAutofill.js      # Autofill state + SSE
│   ├── styles/                 # SCSS styles
│   │   ├── main.scss           # Global styles
│   │   └── grid.scss           # Grid-specific styles
│   ├── utils/                  # Utility functions
│   ├── App.jsx                 # Main application component
│   └── main.jsx                # React entry point
│
├── data/
│   ├── wordlists/              # Word lists (454k+ words)
│   │   ├── comprehensive.txt   # All words (454k)
│   │   ├── core/               # Curated lists
│   │   │   ├── 3-letter.txt
│   │   │   └── crosswordese.txt
│   │   ├── themed/             # Specialty lists
│   │   │   ├── expressions.txt
│   │   │   ├── foreign-es.txt
│   │   │   └── foreign-fr.txt
│   │   └── custom/             # User uploads
│   └── tmp/                    # Temporary files
│       ├── grids/              # Grid state files
│       ├── states/             # Pause/resume state
│       └── progress/           # Progress tracking files
│
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md         # System architecture
│   ├── specs/                  # Component specifications
│   │   ├── BACKEND_SPEC.md
│   │   ├── CLI_SPEC.md
│   │   └── FRONTEND_SPEC.md
│   ├── api/                    # API documentation
│   │   ├── openapi.yaml        # OpenAPI 3.1 spec
│   │   └── API_REFERENCE.md    # Human-readable reference
│   ├── ops/                    # Operations guides
│   │   └── TESTING.md          # Testing guide
│   ├── dev/                    # Developer guides
│   │   └── DEVELOPMENT.md      # This file
│   └── guides/                 # User guides
│
├── frontend/                   # Built frontend (production)
│   └── dist/                   # Vite build output
│
├── tests/                      # Root-level integration tests
│
├── run.py                      # Development server launcher
├── requirements.txt            # Backend dependencies
├── package.json                # Frontend dependencies
├── vite.config.js              # Vite build configuration
├── pytest.ini                  # Test configuration
└── .gitignore                  # Git ignore rules
```

### Key Directories Explained

#### `/backend/` - Flask API Server

**Purpose:** HTTP wrapper around CLI tool

**Key Files:**
- `app.py` - Flask application factory, CORS configuration
- `api/routes.py` - Core API endpoints (pattern, number, normalize, fill)
- `core/cli_adapter.py` - Subprocess execution manager (~400 lines, critical)

**Development Focus:**
- Keep API routes thin (<20 lines each)
- All business logic delegated to CLI
- Request validation in `validators.py`

#### `/cli/` - CLI Tool (Single Source of Truth)

**Purpose:** All crossword construction logic

**Key Files:**
- `src/cli.py` - Click command definitions (8 commands, 903 lines)
- `src/core/grid.py` - Grid data structure (NumPy arrays)
- `src/fill/autofill.py` - CSP autofill algorithm (~800 lines)
- `src/fill/beam_search/orchestrator.py` - Beam search (~600 lines)

**Development Focus:**
- Pure Python functions (no HTTP concerns)
- Comprehensive docstrings
- JSON input/output for subprocess integration

#### `/src/` - React Frontend

**Purpose:** Web-based UI for crossword construction

**Key Components:**
- `App.jsx` - Application state management (18,662 bytes)
- `components/GridEditor.jsx` - Interactive grid (~500 lines)
- `components/AutofillPanel.jsx` - Autofill controls + SSE (~400 lines)

**Development Focus:**
- Component reusability
- State management via hooks
- SCSS for styling (mobile-first)

#### `/data/wordlists/` - Word Lists

**Purpose:** 454k+ words for autofill

**Structure:**
- `comprehensive.txt` - All words (454k, ~5MB)
- `core/` - Curated subsets (3-letter, crosswordese)
- `themed/` - Specialty words (expressions, foreign)
- `custom/` - User uploads

**Format:**
```
WORD        SCORE  SOURCE
HELLO       85     comprehensive
CROSSWORD   90     comprehensive
```

### Configuration Files

#### `pytest.ini` - Test Configuration

```ini
[pytest]
testpaths = backend/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --cov=backend --cov-report=html --cov-report=term
markers =
    slow: marks tests as slow (deselect with -m "not slow")
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

#### `vite.config.js` - Frontend Build Configuration

```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'frontend/dist',
    emptyOutDir: true,
  },
});
```

#### `package.json` - Frontend Dependencies

```json
{
  "scripts": {
    "dev": "vite",             // Start dev server (HMR)
    "build": "vite build",     // Production build
    "preview": "vite preview"  // Preview production build
  },
  "dependencies": {
    "react": "^18.2.0",
    "axios": "^1.6.2",         // HTTP client
    "react-hot-toast": "^2.6.0" // Toast notifications
  }
}
```

---

## Development Environment

### Python Development

#### Virtual Environment Setup

**Best Practice:** Use virtual environments to isolate project dependencies.

```bash
# Create virtual environment
python3 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Verify activation
which python  # Should point to venv/bin/python

# Deactivate when done
deactivate
```

#### Dependency Management

**Install Dependencies:**
```bash
# Backend dependencies
pip install -r requirements.txt

# CLI dependencies
pip install -r cli/requirements.txt

# Development dependencies (optional)
pip install black mypy ruff pytest-xdist
```

**Update Dependencies:**
```bash
# List outdated packages
pip list --outdated

# Update specific package
pip install --upgrade flask

# Freeze dependencies
pip freeze > requirements.txt
```

#### IDE Recommendations

**VS Code (Recommended):**

**Extensions:**
- Python (Microsoft)
- Pylance (IntelliSense)
- Python Test Explorer
- ESLint (frontend)
- ES7+ React/Redux/React-Native snippets

**Settings (`.vscode/settings.json`):**
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["backend/tests"],
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

**PyCharm (Alternative):**

**Configuration:**
1. Open project: `File > Open > crossword-helper/`
2. Set interpreter: `Settings > Project > Python Interpreter > venv`
3. Enable pytest: `Settings > Tools > Python Integrated Tools > Testing > pytest`
4. Configure run configurations for `run.py` and `pytest`

**Python-Specific Tools:**

**Black (Code Formatter):**
```bash
# Install
pip install black

# Format file
black backend/app.py

# Format directory
black backend/

# Check without formatting
black --check backend/
```

**Ruff (Linter, faster than flake8):**
```bash
# Install
pip install ruff

# Lint file
ruff check backend/app.py

# Lint and fix
ruff check --fix backend/
```

**mypy (Type Checker):**
```bash
# Install
pip install mypy

# Type check
mypy backend/core/cli_adapter.py
```

### JavaScript Development

#### Node/npm Setup

**Verify Installation:**
```bash
# Check Node.js version
node --version  # Should be 18+

# Check npm version
npm --version   # Should be 9+
```

**Install Dependencies:**
```bash
# Install all packages
npm install

# Install specific package
npm install axios

# Install dev dependency
npm install --save-dev eslint
```

**Update Dependencies:**
```bash
# Check outdated packages
npm outdated

# Update all packages (careful!)
npm update

# Update specific package
npm install react@latest
```

#### Frontend Dev Server

**Start Development Server:**
```bash
npm run dev
# → http://localhost:3000
# Hot Module Replacement (HMR) enabled
# Changes reload automatically
```

**Build for Production:**
```bash
npm run build
# → Output: frontend/dist/
```

**Preview Production Build:**
```bash
npm run preview
# → http://localhost:3000 (serves built files)
```

#### IDE Configuration for JavaScript

**VS Code Extensions:**
- ESLint
- Prettier - Code formatter
- ES7+ React/Redux/React-Native snippets
- vscode-styled-components (for SCSS)

**ESLint Configuration (`.eslintrc.json`):**
```json
{
  "extends": [
    "eslint:recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended"
  ],
  "parserOptions": {
    "ecmaVersion": 2021,
    "sourceType": "module",
    "ecmaFeatures": {
      "jsx": true
    }
  },
  "rules": {
    "react/prop-types": "off",
    "no-unused-vars": "warn"
  }
}
```

### Git Configuration

#### Git Hooks and Linting

**Pre-commit Hook (`.git/hooks/pre-commit`):**
```bash
#!/bin/sh
# Run unit tests before commit
pytest backend/tests/unit/ -v || exit 1

# Run linter
ruff check backend/ || exit 1

echo "✅ Pre-commit checks passed"
```

**Make executable:**
```bash
chmod +x .git/hooks/pre-commit
```

**Pre-push Hook (`.git/hooks/pre-push`):**
```bash
#!/bin/sh
# Run full test suite before push
pytest --cov=backend --cov-report=term || exit 1

echo "✅ Pre-push checks passed"
```

**Using pre-commit Framework (Recommended):**

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
pre-commit install --hook-type pre-push
```

**Configuration (`.pre-commit-config.yaml`):**
```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: Run unit tests
        entry: pytest backend/tests/unit/ -v
        language: system
        pass_filenames: false
        always_run: true

      - id: black
        name: Format with black
        entry: black
        language: system
        types: [python]

      - id: ruff
        name: Lint with ruff
        entry: ruff check
        language: system
        types: [python]
```

---

## Development Workflow

### Branching Strategy

**Main Branches:**
- `main` - Production-ready code (always stable)
- `develop` - Integration branch for features (may be unstable)

**Feature Branches:**
- `feature/<feature-name>` - New features
- `bugfix/<bug-description>` - Bug fixes
- `hotfix/<issue>` - Critical production fixes

**Example Workflow:**
```bash
# Start new feature
git checkout main
git pull origin main
git checkout -b feature/theme-locking

# Make changes, commit frequently
git add backend/api/theme_routes.py
git commit -m "Add theme locking API endpoint"

# Push to remote
git push origin feature/theme-locking

# Create pull request on GitHub/GitLab
# After review and merge, delete branch
git checkout main
git pull origin main
git branch -d feature/theme-locking
```

### Making Changes

**Step-by-Step Process:**

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Write Tests First (TDD)**
   ```bash
   # Create test file
   touch backend/tests/unit/test_my_feature.py

   # Write failing test
   # Example: test_my_feature.py
   ```

3. **Implement Feature**
   ```bash
   # Edit code files
   # Run tests frequently
   pytest backend/tests/unit/test_my_feature.py -v
   ```

4. **Verify Tests Pass**
   ```bash
   pytest backend/tests/unit/ -v
   pytest backend/tests/integration/ -v
   ```

5. **Format and Lint**
   ```bash
   black backend/
   ruff check backend/
   ```

6. **Commit Changes**
   ```bash
   git add .
   git commit -m "Add feature: theme locking"
   ```

### Running Tests Locally

**Quick Unit Tests (Fast):**
```bash
pytest backend/tests/unit/ -v
# ~5 seconds
```

**All Tests:**
```bash
pytest
# ~35 seconds
```

**With Coverage:**
```bash
pytest --cov=backend --cov-report=html
open htmlcov/index.html
```

**Specific Test:**
```bash
pytest backend/tests/unit/test_validators.py::TestValidators::test_validate_pattern_request_valid -vv
```

**Skip Slow Tests:**
```bash
pytest -m "not slow"
```

### Code Review Process

**Before Creating Pull Request:**

1. **Self-Review Checklist:**
   - [ ] All tests passing locally
   - [ ] Code formatted (black, ruff)
   - [ ] Docstrings added for new functions
   - [ ] Type hints added (Python)
   - [ ] No debug print statements
   - [ ] Coverage >85% for new code

2. **Create Pull Request:**
   - Write clear title: "Add theme locking feature"
   - Description includes:
     - What changed
     - Why (link to issue if applicable)
     - How to test
     - Screenshots (if UI changes)

3. **Address Review Comments:**
   - Make requested changes
   - Push to same branch
   - Respond to comments

**Reviewer Checklist:**
- [ ] Code follows style guidelines
- [ ] Tests are comprehensive
- [ ] No unnecessary complexity
- [ ] Documentation updated
- [ ] Performance considerations addressed

### Merge Process

**After Approval:**

1. **Update Branch:**
   ```bash
   git checkout feature/my-feature
   git pull origin main
   git merge main
   # Resolve conflicts if any
   ```

2. **Final Tests:**
   ```bash
   pytest
   ```

3. **Merge via GitHub/GitLab:**
   - Squash commits if many small commits
   - Use merge commit for feature branches
   - Delete branch after merge

4. **Pull Latest Main:**
   ```bash
   git checkout main
   git pull origin main
   ```

---

## Code Style Guidelines

### Python Style (PEP 8, Black, Ruff)

**Key Principles:**
- Follow PEP 8 (enforced by black and ruff)
- Use type hints for function parameters and return values
- Write docstrings for all public functions/classes
- Maximum line length: 88 characters (black default)

**Example:**

```python
from typing import List, Dict, Optional


def search_pattern(
    pattern: str,
    wordlist_paths: List[str],
    max_results: int = 20,
    algorithm: str = "trie"
) -> Dict[str, any]:
    """
    Search for words matching a crossword pattern.

    Args:
        pattern: Pattern with wildcards (e.g., "C?T" for CAT, COT, CUT)
        wordlist_paths: Paths to word list files
        max_results: Maximum number of results to return
        algorithm: Matching algorithm ("regex", "trie", "ahocorasick")

    Returns:
        Dictionary with keys:
        - results: List of matching words with scores
        - meta: Query metadata (time, count)

    Raises:
        ValueError: If pattern is empty or invalid
        FileNotFoundError: If wordlist file not found

    Example:
        >>> search_pattern("C?T", ["wordlist.txt"], max_results=10)
        {
            "results": [
                {"word": "CAT", "score": 90},
                {"word": "COT", "score": 75}
            ],
            "meta": {"query_time_ms": 12, "total_found": 127}
        }
    """
    if not pattern:
        raise ValueError("Pattern cannot be empty")

    # Implementation here
    pass
```

**Docstring Format (Google Style):**
```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """
    Short description (one line).

    Longer description if needed. Explain what the function does,
    not how it does it (that's what the code is for).

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this exception is raised

    Example:
        >>> function_name(arg1, arg2)
        expected_output
    """
```

**Type Hints:**
```python
from typing import List, Dict, Optional, Union, Tuple

# Function with type hints
def process_grid(
    grid: List[List[str]],
    theme_entries: Optional[Dict[str, List[str]]] = None
) -> Tuple[bool, str]:
    """Process crossword grid with optional theme entries."""
    pass

# Class with type hints
class Grid:
    """Crossword grid data structure."""

    def __init__(self, size: int) -> None:
        self.size: int = size
        self.cells: np.ndarray = np.zeros((size, size), dtype=int)

    def get_letter(self, row: int, col: int) -> Optional[str]:
        """Get letter at position, or None if empty."""
        pass
```

### JavaScript/TypeScript Style (ESLint, Prettier)

**Key Principles:**
- Use functional components with hooks (React)
- Destructure props for clarity
- Use `const` by default, `let` when reassignment needed, never `var`
- Single quotes for strings
- 2-space indentation (JavaScript convention)

**Example (React Component):**

```javascript
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './GridEditor.scss';

/**
 * Interactive crossword grid editor with keyboard navigation.
 *
 * @param {Object} props - Component props
 * @param {Array<Array<Object>>} props.grid - Grid state (2D array of cells)
 * @param {Function} props.onGridChange - Callback when grid changes
 * @param {Object} props.themeEntries - Locked theme entries
 */
export const GridEditor = ({ grid, onGridChange, themeEntries }) => {
  const [selectedCell, setSelectedCell] = useState({ row: 0, col: 0 });
  const [direction, setDirection] = useState('across');

  useEffect(() => {
    // Handle keyboard navigation
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowRight') {
        moveSelection('right');
      } else if (e.key === 'ArrowDown') {
        moveSelection('down');
      }
      // ... other keys
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedCell]);

  const handleCellClick = (row, col) => {
    setSelectedCell({ row, col });
  };

  const handleCellChange = (row, col, letter) => {
    const newGrid = grid.map((r, rIdx) =>
      r.map((cell, cIdx) =>
        rIdx === row && cIdx === col
          ? { ...cell, letter: letter.toUpperCase() }
          : cell
      )
    );
    onGridChange(newGrid);
  };

  return (
    <div className="grid-editor">
      <div className="grid-container">
        {grid.map((row, rowIdx) => (
          <div key={rowIdx} className="grid-row">
            {row.map((cell, colIdx) => (
              <Cell
                key={`${rowIdx}-${colIdx}`}
                row={rowIdx}
                col={colIdx}
                cell={cell}
                isSelected={
                  selectedCell.row === rowIdx && selectedCell.col === colIdx
                }
                onClick={handleCellClick}
                onChange={handleCellChange}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};
```

**JSDoc Comments:**
```javascript
/**
 * Calculate word score based on letter frequency and usage.
 *
 * @param {string} word - Word to score
 * @param {Object} options - Scoring options
 * @param {number} options.minScore - Minimum acceptable score
 * @param {boolean} options.penalizeDuplicates - Penalize repeated letters
 * @returns {number} Score from 0-100
 *
 * @example
 * calculateScore('HELLO', { minScore: 30, penalizeDuplicates: true })
 * // returns 75
 */
function calculateScore(word, options = {}) {
  // Implementation
}
```

### Naming Conventions

**Python:**
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

```python
# Good
def search_pattern(pattern: str) -> List[str]:
    pass

class PatternMatcher:
    MAX_RESULTS = 1000

    def _internal_helper(self):
        pass
```

**JavaScript:**
- Functions/variables: `camelCase`
- Components: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`

```javascript
// Good
const searchPattern = (pattern) => { };

const GridEditor = ({ grid }) => { };

const MAX_RESULTS = 1000;
```

### Documentation Standards

**Python Docstrings (Google Style):**
```python
def complex_function(param1, param2, param3=None):
    """
    Short one-line description.

    Longer description explaining the function's purpose,
    behavior, and any important details.

    Args:
        param1 (str): Description of param1
        param2 (int): Description of param2
        param3 (Optional[List[str]]): Description of param3

    Returns:
        Dict[str, Any]: Description of return value with structure:
            - key1 (str): Description
            - key2 (int): Description

    Raises:
        ValueError: When param1 is empty
        FileNotFoundError: When file doesn't exist

    Example:
        >>> complex_function("test", 42)
        {"key1": "value", "key2": 42}

    Note:
        This function has side effects (writes to disk).
    """
```

**JSDoc Comments:**
```javascript
/**
 * Complex function description.
 *
 * @param {string} param1 - Description of param1
 * @param {number} param2 - Description of param2
 * @param {Object} [options] - Optional configuration
 * @param {boolean} options.flag - Some flag
 * @returns {Promise<Object>} Promise resolving to result object
 * @throws {Error} When validation fails
 *
 * @example
 * await complexFunction('test', 42, { flag: true })
 * // returns { key: 'value' }
 */
async function complexFunction(param1, param2, options = {}) {
  // Implementation
}
```

### Import Organization

**Python:**
```python
# Standard library imports
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Third-party imports
import click
import numpy as np
from flask import Flask, request, jsonify

# Local imports
from backend.core.cli_adapter import CLIAdapter
from backend.api.validators import validate_pattern_request
```

**JavaScript:**
```javascript
// React/library imports
import React, { useState, useEffect } from 'react';
import axios from 'axios';

// Component imports
import { GridEditor } from './components/GridEditor';
import { AutofillPanel } from './components/AutofillPanel';

// Utility imports
import { formatGrid } from './utils/grid';

// Style imports
import './App.scss';
```

---

## Building and Running

### CLI Development

#### Running CLI Locally

**Direct Execution:**
```bash
# From project root
python cli/src/cli.py --help

# Or if installed in editable mode
crossword --help
```

**Common CLI Commands:**

```bash
# Create new grid
crossword new --size 15 --output puzzle.json

# Fill grid with autofill
crossword fill puzzle.json \
  --algorithm hybrid \
  --wordlists data/wordlists/comprehensive.txt \
  --timeout 300

# Search for pattern
crossword pattern "C?T" \
  --wordlists data/wordlists/comprehensive.txt \
  --max-results 20 \
  --json-output

# Auto-number grid
crossword number puzzle.json --json-output

# Normalize entry
crossword normalize "Tina Fey" --json-output
```

#### Testing CLI Commands

**Interactive Testing:**
```bash
# Create test grid
echo '{"size": 5, "grid": [[".", ".", ".", ".", "."], [".", ".", ".", ".", "."], [".", ".", "#", ".", "."], [".", ".", ".", ".", "."], [".", ".", ".", ".", "."]]}' > test.json

# Test fill command
crossword fill test.json --algorithm csp --timeout 60

# View result
cat test.json
```

**Automated Testing:**
```bash
# Run CLI unit tests
pytest cli/tests/unit/ -v

# Run CLI integration tests
pytest cli/tests/integration/ -v
```

#### Debugging CLI

**Add Debug Output:**
```python
# In cli/src/cli.py
@click.command()
@click.option('--debug', is_flag=True, help='Enable debug output')
def fill(debug):
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        logger.debug(f"Starting fill with options: {options}")

    # Command implementation
```

**Run with Debug:**
```bash
crossword fill puzzle.json --debug
```

**Use Python Debugger:**
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Then run command
crossword fill puzzle.json
```

### Backend Development

#### Running Flask Server

**Development Mode (Debug + Auto-reload):**
```bash
# From project root
python run.py

# Server starts at http://localhost:5000
# Debug mode: ON
# Auto-reload on code changes: ON
```

**Production Mode (No Debug):**
```bash
FLASK_ENV=production python run.py
```

**Custom Host/Port:**
```python
# Edit run.py
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
```

#### API Testing

**Using curl:**
```bash
# Health check
curl http://localhost:5000/api/health

# Pattern search
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{"pattern": "C?T", "max_results": 10}'

# Grid numbering
curl -X POST http://localhost:5000/api/number \
  -H "Content-Type: application/json" \
  -d '{"size": 5, "grid": [["A", ".", ".", ".", "."], [".", ".", ".", ".", "."], [".", ".", "#", ".", "."], [".", ".", ".", ".", "."], [".", ".", ".", ".", "."]]}'
```

**Using HTTPie (friendlier):**
```bash
# Install
pip install httpie

# Pattern search
http POST localhost:5000/api/pattern pattern=C?T max_results=10

# Pretty JSON output
http POST localhost:5000/api/pattern pattern=C?T max_results=10 | jq
```

**Using Postman/Insomnia:**
1. Import OpenAPI spec: `docs/api/openapi.yaml`
2. All endpoints auto-configured
3. Test interactively

#### Debugging Backend

**Flask Debug Mode:**
- Automatically enabled in `run.py`
- Shows detailed error pages in browser
- Auto-reloads on code changes

**Python Debugger (pdb):**
```python
# Add breakpoint in route
@app.route('/api/pattern', methods=['POST'])
def pattern_search():
    import pdb; pdb.set_trace()  # Debugger starts here
    data = request.json
    # ... rest of code
```

**Logging:**
```python
import logging

# In backend/app.py
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# In route
logger.debug(f"Pattern request: {data}")
logger.info(f"Found {len(results)} matches")
logger.error(f"Error: {e}")
```

**VS Code Debugging:**

**Configuration (`.vscode/launch.json`):**
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Flask",
      "type": "python",
      "request": "launch",
      "module": "flask",
      "env": {
        "FLASK_APP": "backend.app",
        "FLASK_ENV": "development"
      },
      "args": ["run", "--no-debugger", "--no-reload"],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

**Usage:**
1. Set breakpoints in VS Code
2. Press F5 to start debugging
3. Interact with API
4. Debugger pauses at breakpoints

### Frontend Development

#### Running React Dev Server

**Start Development Server:**
```bash
npm run dev

# Output:
#   VITE v5.0.8  ready in 450 ms
#
#   ➜  Local:   http://localhost:3000/
#   ➜  Network: use --host to expose
```

**Features:**
- **Hot Module Replacement (HMR):** Changes reflect instantly
- **Fast refresh:** React state preserved on component updates
- **Proxy to backend:** `/api/*` requests proxied to `localhost:5000`

#### Hot Reloading

**How It Works:**
1. Edit React component (e.g., `src/components/GridEditor.jsx`)
2. Save file
3. Browser updates automatically (no full reload)
4. Component state preserved

**When Full Reload Needed:**
- Changes to `vite.config.js`
- Changes to `index.html`
- Adding new dependencies

```bash
# Force full reload
# Press Ctrl+C, then npm run dev
```

#### Debugging Frontend

**Chrome DevTools:**

1. **Open DevTools:** Press F12
2. **Sources Tab:** Set breakpoints in React components
3. **Console Tab:** View console.log output
4. **Network Tab:** Inspect API requests
5. **React DevTools Extension:** Inspect component tree

**React DevTools:**
```bash
# Install Chrome extension
# Search "React Developer Tools" in Chrome Web Store
```

**Features:**
- Component tree inspection
- Props/state viewing
- Performance profiling
- Hooks inspection

**Console Debugging:**
```javascript
// In component
const GridEditor = ({ grid }) => {
  console.log('Grid state:', grid);
  console.log('Selected cell:', selectedCell);

  // Conditional logging
  if (DEBUG) {
    console.debug('Debug info:', debugInfo);
  }

  return <div>...</div>;
};
```

**VS Code Debugging:**

**Configuration (`.vscode/launch.json`):**
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Chrome: Frontend",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:3000",
      "webRoot": "${workspaceFolder}/src",
      "sourceMapPathOverrides": {
        "webpack:///src/*": "${webRoot}/*"
      }
    }
  ]
}
```

**Usage:**
1. Start dev server: `npm run dev`
2. Set breakpoints in VS Code
3. Press F5 to launch Chrome
4. Debugger pauses at breakpoints

---

## Debugging

### Python Debugging (pdb, IDE Debuggers)

#### Using pdb (Built-in Debugger)

**Basic Usage:**
```python
def pattern_matcher(pattern):
    import pdb; pdb.set_trace()  # Execution pauses here
    results = search_pattern(pattern)
    return results
```

**pdb Commands:**
```
(Pdb) h          # Help (list all commands)
(Pdb) n          # Next line (step over)
(Pdb) s          # Step into function
(Pdb) c          # Continue execution
(Pdb) p variable # Print variable value
(Pdb) pp obj     # Pretty-print object
(Pdb) l          # List code around current line
(Pdb) w          # Show stack trace
(Pdb) b 42       # Set breakpoint at line 42
(Pdb) q          # Quit debugger
```

**Example Session:**
```python
# In code
def autofill(grid, wordlist):
    import pdb; pdb.set_trace()
    slots = grid.get_slots()
    for slot in slots:
        candidates = wordlist.match(slot.pattern)
        # ...
```

```bash
# Run script
python cli/src/cli.py fill puzzle.json

# Debugger starts:
> /path/to/autofill.py(123)autofill()
-> slots = grid.get_slots()
(Pdb) n
> /path/to/autofill.py(124)autofill()
-> for slot in slots:
(Pdb) p slots
[Slot(0, 'across', 5, pattern='?????'), Slot(1, 'down', 4, pattern='????')]
(Pdb) c  # Continue execution
```

#### Using ipdb (Enhanced pdb)

**Install:**
```bash
pip install ipdb
```

**Usage:**
```python
import ipdb; ipdb.set_trace()
```

**Features over pdb:**
- Tab completion
- Syntax highlighting
- Better history

#### VS Code Python Debugger

**Set Breakpoint:**
1. Click in gutter left of line number
2. Red dot appears

**Start Debugging:**
1. Press F5 (or Run > Start Debugging)
2. Select "Python: Flask" configuration

**Debug Actions:**
- **Continue (F5):** Resume execution
- **Step Over (F10):** Execute current line, don't enter functions
- **Step Into (F11):** Enter function calls
- **Step Out (Shift+F11):** Exit current function
- **Restart (Ctrl+Shift+F5):** Restart debugger

**Watch Variables:**
- Hover over variables to see values
- Add to "Watch" panel for persistent monitoring

**Debug Console:**
- Evaluate expressions while paused
- Execute Python code in current context

```python
# While paused at breakpoint
# In Debug Console:
>>> len(results)
127
>>> results[0]
{'word': 'CAT', 'score': 90}
```

#### PyCharm Debugger

**Set Breakpoint:**
1. Click in gutter (red dot appears)
2. Right-click breakpoint for conditional breakpoints

**Start Debugging:**
1. Right-click `run.py`
2. Select "Debug 'run'"

**Features:**
- Conditional breakpoints
- Exception breakpoints (pause on any exception)
- Evaluate expressions
- Watches
- Frames view (call stack)

### JavaScript Debugging (Chrome DevTools, VS Code)

#### Chrome DevTools

**Open DevTools:**
- Press F12
- Or Right-click > Inspect

**Sources Tab Debugging:**

1. **Set Breakpoint:**
   - Open file in Sources tab
   - Click line number (blue marker appears)

2. **Conditional Breakpoint:**
   - Right-click line number
   - Select "Add conditional breakpoint"
   - Enter condition: `selectedCell.row === 5`

3. **Debug Controls:**
   - **Resume (F8):** Continue execution
   - **Step Over (F10):** Execute current line
   - **Step Into (F11):** Enter function
   - **Step Out (Shift+F11):** Exit function

4. **Scope Panel:**
   - View local variables
   - View closure variables
   - View global variables

5. **Watch Expressions:**
   - Add expressions to monitor
   - Example: `grid[selectedCell.row][selectedCell.col]`

6. **Call Stack:**
   - View function call history
   - Click to jump to calling function

**Console Debugging:**

```javascript
// Console methods
console.log('Simple message');
console.debug('Debug info');  // Only shows when verbose logging enabled
console.info('Information');
console.warn('Warning');
console.error('Error');

// Formatted output
console.log('Selected cell:', selectedCell);
console.table(gridData);  // Display array/object as table

// Grouping
console.group('Grid State');
console.log('Size:', grid.length);
console.log('Selected:', selectedCell);
console.groupEnd();

// Timing
console.time('autofill');
// ... code ...
console.timeEnd('autofill');  // Logs elapsed time

// Assertions
console.assert(selectedCell.row >= 0, 'Invalid row');
```

**Network Tab:**
- View all API requests
- Inspect request/response headers
- View request/response bodies
- Check status codes
- Measure request timing

**React DevTools:**

**Install:**
- Chrome Web Store: "React Developer Tools"

**Features:**
- **Components Tree:** Inspect component hierarchy
- **Props:** View component props
- **State:** View and edit component state
- **Hooks:** Inspect useState, useEffect, etc.
- **Profiler:** Measure render performance

**Example:**
1. Select component in tree
2. View props/state in right panel
3. Edit state directly to test changes

#### VS Code JavaScript Debugger

**Configuration (`.vscode/launch.json`):**
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Launch Chrome",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:3000",
      "webRoot": "${workspaceFolder}/src"
    }
  ]
}
```

**Debugging:**
1. Set breakpoints in VS Code
2. Press F5
3. Chrome launches with debugger attached
4. Interact with app
5. Debugger pauses at breakpoints

**Advantages over Chrome DevTools:**
- Debug in same editor
- Set breakpoints before running
- Better TypeScript support

### Common Issues and Solutions

#### Backend Issues

**Issue: ImportError**
```
ImportError: cannot import name 'app' from 'backend.app'
```

**Solution:**
```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or use editable install
pip install -e .
```

**Issue: CLI Not Found**
```
subprocess.CalledProcessError: Command 'crossword' not found
```

**Solution:**
```bash
# Install CLI in editable mode
cd cli
pip install -e .
cd ..

# Or set CLI_PATH environment variable
export CLI_PATH="$(pwd)/cli/crossword"
```

**Issue: Port Already in Use**
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port 5000
lsof -i :5000

# Kill process
kill -9 <PID>

# Or use different port
# Edit run.py: app.run(port=5001)
```

#### Frontend Issues

**Issue: npm install Fails**
```
npm ERR! code ELIFECYCLE
```

**Solution:**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall
npm install
```

**Issue: API Requests Failing (CORS)**
```
Access to XMLHttpRequest blocked by CORS policy
```

**Solution:**
```bash
# Verify Flask-CORS installed
pip list | grep flask-cors

# Check backend/app.py has CORS configured:
from flask_cors import CORS
CORS(app, origins=['http://localhost:3000'])

# Restart Flask server
```

**Issue: Build Fails**
```
vite build
ERROR: Failed to resolve import
```

**Solution:**
```bash
# Check import paths (case-sensitive)
# Verify file exists
ls src/components/GridEditor.jsx

# Check for circular dependencies
# Simplify imports
```

### Logging Best Practices

**Python Logging:**

```python
import logging

# Configure logging (in app.py or __main__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# In code
logger.debug('Detailed debug information')
logger.info('General information')
logger.warning('Warning message')
logger.error('Error occurred', exc_info=True)  # Include stack trace
```

**JavaScript Logging:**

```javascript
// Development logging
const DEBUG = process.env.NODE_ENV === 'development';

const log = {
  debug: (...args) => DEBUG && console.debug(...args),
  info: (...args) => console.log(...args),
  warn: (...args) => console.warn(...args),
  error: (...args) => console.error(...args),
};

// Usage
log.debug('Debug info:', data);
log.info('API request:', url);
log.warn('Slow operation:', time);
log.error('Failed:', error);
```

---

## Adding New Features

### Feature Planning

**Before Writing Code:**

1. **Define Requirements:**
   - What problem does this solve?
   - Who is the user?
   - What are the acceptance criteria?

2. **Design API/Interface:**
   - What are the inputs?
   - What are the outputs?
   - Error cases?

3. **Identify Components:**
   - CLI command? API endpoint? React component?
   - Where does business logic live (always in CLI)?

4. **Write Tests First (TDD):**
   - Unit tests for logic
   - Integration tests for API
   - E2E tests for workflows

**Example: Adding Black Square Suggestions Feature**

**Requirements:**
- User can request suggestions for strategic black square placement
- Suggestions maintain symmetry
- Suggestions improve fillability

**Design:**
```
API Endpoint: POST /api/grid/suggest-black-squares
Input: { grid, problematic_slots }
Output: { suggestions: [{ position, symmetric_position, reason, score }] }
```

**Components:**
- CLI: `crossword suggest-black-squares grid.json`
- Backend: `backend/api/grid_routes.py` (new endpoint)
- Frontend: `src/components/BlackSquareSuggester.jsx`

### Implementation Checklist

**Step-by-Step Implementation:**

#### 1. Write Failing Tests

**Backend Test:**
```python
# backend/tests/unit/test_black_square_suggester.py
import pytest
from backend.core.black_square_suggester import BlackSquareSuggester

class TestBlackSquareSuggester:
    def test_suggest_maintains_symmetry(self):
        """Test that suggestions maintain 180° symmetry."""
        grid = [['.'] * 15 for _ in range(15)]
        suggester = BlackSquareSuggester(grid)

        suggestions = suggester.suggest(problematic_slots=['7-ACROSS-8'])

        for suggestion in suggestions:
            pos = suggestion['position']
            sym_pos = suggestion['symmetric_position']
            # Verify symmetry
            assert sym_pos == (14 - pos[0], 14 - pos[1])

    def test_suggest_avoids_isolated_regions(self):
        """Test that suggestions don't create isolated regions."""
        # ... test implementation
```

**Run Tests (Should Fail):**
```bash
pytest backend/tests/unit/test_black_square_suggester.py -v
# FAILED - Module not found
```

#### 2. Implement Core Logic (CLI)

**Create Module:**
```python
# cli/src/core/black_square_suggester.py
from typing import List, Dict, Tuple

class BlackSquareSuggester:
    """Suggest strategic black square placements."""

    def __init__(self, grid: List[List[str]]):
        self.grid = grid
        self.size = len(grid)

    def suggest(
        self,
        problematic_slots: List[str],
        max_suggestions: int = 5
    ) -> List[Dict]:
        """
        Suggest black square placements to improve fillability.

        Args:
            problematic_slots: Slot IDs causing fill issues
            max_suggestions: Maximum suggestions to return

        Returns:
            List of suggestions with position, reason, score
        """
        suggestions = []

        for slot_id in problematic_slots:
            slot = self._parse_slot_id(slot_id)

            for pos in slot.positions:
                if self._is_valid_black_square(pos):
                    symmetric_pos = self._get_symmetric_position(pos)

                    suggestion = {
                        'position': pos,
                        'symmetric_position': symmetric_pos,
                        'reason': self._generate_reason(slot, pos),
                        'score': self._calculate_score(pos)
                    }
                    suggestions.append(suggestion)

        # Sort by score, return top N
        suggestions.sort(key=lambda s: s['score'], reverse=True)
        return suggestions[:max_suggestions]

    def _is_valid_black_square(self, pos: Tuple[int, int]) -> bool:
        """Check if position is valid for black square."""
        # Check doesn't violate minimum word length
        # Check doesn't create isolated regions
        # Check maintains connectivity
        pass

    def _get_symmetric_position(
        self,
        pos: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Get 180° rotationally symmetric position."""
        row, col = pos
        return (self.size - 1 - row, self.size - 1 - col)

    def _calculate_score(self, pos: Tuple[int, int]) -> int:
        """Calculate suggestion quality score (0-100)."""
        # Consider impact on fillability
        # Prefer positions that break long slots
        # Penalize positions creating many short slots
        pass
```

**Run Tests (Should Pass):**
```bash
pytest backend/tests/unit/test_black_square_suggester.py -v
# PASSED
```

#### 3. Add CLI Command

**Update CLI:**
```python
# cli/src/cli.py
import click
from cli.src.core.black_square_suggester import BlackSquareSuggester

@click.command()
@click.argument('grid_file', type=click.Path(exists=True))
@click.option('--problematic-slots', multiple=True, help='Problematic slot IDs')
@click.option('--max-suggestions', default=5, help='Max suggestions')
@click.option('--json-output', is_flag=True, help='Output JSON')
def suggest_black_squares(grid_file, problematic_slots, max_suggestions, json_output):
    """Suggest strategic black square placements."""
    # Load grid
    with open(grid_file) as f:
        grid_data = json.load(f)

    # Get suggestions
    suggester = BlackSquareSuggester(grid_data['grid'])
    suggestions = suggester.suggest(
        problematic_slots=list(problematic_slots),
        max_suggestions=max_suggestions
    )

    # Output
    if json_output:
        click.echo(json.dumps({'suggestions': suggestions}))
    else:
        for i, suggestion in enumerate(suggestions, 1):
            click.echo(f"{i}. Position {suggestion['position']}")
            click.echo(f"   Reason: {suggestion['reason']}")
            click.echo(f"   Score: {suggestion['score']}")

# Add to CLI group
cli.add_command(suggest_black_squares)
```

**Test CLI:**
```bash
crossword suggest-black-squares puzzle.json \
  --problematic-slots "7-ACROSS-8" \
  --max-suggestions 5 \
  --json-output
```

#### 4. Add Backend API Endpoint

**Backend Route:**
```python
# backend/api/grid_routes.py
from flask import Blueprint, request, jsonify
from backend.core.cli_adapter import get_adapter
from backend.api.validators import validate_grid_request

grid_bp = Blueprint('grid', __name__, url_prefix='/api/grid')

@grid_bp.route('/suggest-black-squares', methods=['POST'])
def suggest_black_squares():
    """Suggest strategic black square placements."""
    try:
        data = request.json

        # Validate request
        validate_grid_request(data)

        # Call CLI via adapter
        cli_adapter = get_adapter()
        result = cli_adapter.suggest_black_squares(
            grid_data=data['grid'],
            problematic_slots=data.get('problematic_slots', []),
            max_suggestions=data.get('max_suggestions', 5)
        )

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500
```

**CLI Adapter:**
```python
# backend/core/cli_adapter.py
class CLIAdapter:
    # ... existing methods ...

    def suggest_black_squares(
        self,
        grid_data: dict,
        problematic_slots: List[str],
        max_suggestions: int = 5
    ) -> dict:
        """Execute suggest-black-squares CLI command."""
        # Write grid to temp file
        grid_file = self._write_temp_grid(grid_data)

        try:
            # Build command
            cmd = [
                self.cli_path,
                'suggest-black-squares',
                grid_file,
                '--json-output',
                '--max-suggestions', str(max_suggestions)
            ]

            for slot in problematic_slots:
                cmd.extend(['--problematic-slots', slot])

            # Execute
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parse output
            return json.loads(result.stdout)

        finally:
            # Cleanup temp file
            os.remove(grid_file)
```

**Test API:**
```bash
curl -X POST http://localhost:5000/api/grid/suggest-black-squares \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [[".", ".", ".", ...], ...],
    "problematic_slots": ["7-ACROSS-8"],
    "max_suggestions": 5
  }'
```

#### 5. Add Frontend Component

**Component:**
```javascript
// src/components/BlackSquareSuggester.jsx
import React, { useState } from 'react';
import axios from 'axios';
import './BlackSquareSuggester.scss';

export const BlackSquareSuggester = ({ grid, onApplySuggestion }) => {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleGetSuggestions = async () => {
    setLoading(true);

    try {
      const response = await axios.post('/api/grid/suggest-black-squares', {
        grid,
        max_suggestions: 5
      });

      setSuggestions(response.data.suggestions);
    } catch (error) {
      console.error('Failed to get suggestions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApply = (suggestion) => {
    onApplySuggestion(suggestion.position, suggestion.symmetric_position);
  };

  return (
    <div className="black-square-suggester">
      <button onClick={handleGetSuggestions} disabled={loading}>
        {loading ? 'Getting Suggestions...' : 'Suggest Black Squares'}
      </button>

      {suggestions.length > 0 && (
        <div className="suggestions-list">
          <h3>Suggestions</h3>
          {suggestions.map((suggestion, idx) => (
            <div key={idx} className="suggestion-item">
              <div className="suggestion-info">
                <strong>Position:</strong> {suggestion.position.join(', ')}
                <br />
                <strong>Reason:</strong> {suggestion.reason}
                <br />
                <strong>Score:</strong> {suggestion.score}
              </div>
              <button onClick={() => handleApply(suggestion)}>
                Apply
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

**Integrate into App:**
```javascript
// src/App.jsx
import { BlackSquareSuggester } from './components/BlackSquareSuggester';

function App() {
  const [grid, setGrid] = useState(/* ... */);

  const handleApplySuggestion = (position, symmetricPosition) => {
    const newGrid = grid.map((row, rIdx) =>
      row.map((cell, cIdx) => {
        if (
          (rIdx === position[0] && cIdx === position[1]) ||
          (rIdx === symmetricPosition[0] && cIdx === symmetricPosition[1])
        ) {
          return { ...cell, isBlack: true };
        }
        return cell;
      })
    );

    setGrid(newGrid);
  };

  return (
    <div className="app">
      {/* ... other components ... */}
      <BlackSquareSuggester
        grid={grid}
        onApplySuggestion={handleApplySuggestion}
      />
    </div>
  );
}
```

#### 6. Write Integration Tests

**Backend Integration Test:**
```python
# backend/tests/integration/test_black_square_suggestions.py
import pytest

class TestBlackSquareSuggestionsAPI:
    def test_suggest_black_squares_endpoint(self, client):
        """Test /api/grid/suggest-black-squares endpoint."""
        grid = [['.'] * 15 for _ in range(15)]

        response = client.post('/api/grid/suggest-black-squares', json={
            'grid': grid,
            'problematic_slots': ['7-ACROSS-8'],
            'max_suggestions': 5
        })

        assert response.status_code == 200
        data = response.json

        assert 'suggestions' in data
        assert len(data['suggestions']) <= 5

        for suggestion in data['suggestions']:
            assert 'position' in suggestion
            assert 'symmetric_position' in suggestion
            assert 'reason' in suggestion
            assert 'score' in suggestion
```

#### 7. Update Documentation

**Update API Docs:**
```yaml
# docs/api/openapi.yaml
paths:
  /api/grid/suggest-black-squares:
    post:
      summary: Suggest strategic black square placements
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                grid:
                  type: array
                  items:
                    type: array
                    items:
                      type: string
                problematic_slots:
                  type: array
                  items:
                    type: string
                max_suggestions:
                  type: integer
                  default: 5
      responses:
        '200':
          description: Suggestions generated
          content:
            application/json:
              schema:
                type: object
                properties:
                  suggestions:
                    type: array
                    items:
                      type: object
```

**Update README:**
```markdown
# New Features

## Black Square Suggestions

Automatically suggests strategic black square placements to improve grid fillability.

**Usage:**

CLI:
```bash
crossword suggest-black-squares puzzle.json \
  --problematic-slots "7-ACROSS-8" \
  --max-suggestions 5
```

API:
```bash
POST /api/grid/suggest-black-squares
{
  "grid": [...],
  "problematic_slots": ["7-ACROSS-8"],
  "max_suggestions": 5
}
```

Frontend:
- Click "Suggest Black Squares" button
- Review suggestions
- Click "Apply" to add black squares
```

### Example: Adding a New API Endpoint

**Quick Template:**

```python
# 1. Add route (backend/api/your_routes.py)
@your_bp.route('/your-endpoint', methods=['POST'])
def your_endpoint():
    """Your endpoint description."""
    try:
        data = request.json
        validate_your_request(data)

        cli_adapter = get_adapter()
        result = cli_adapter.your_cli_command(data)

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

# 2. Add validator (backend/api/validators.py)
def validate_your_request(data):
    """Validate your request."""
    if not data.get('required_field'):
        raise ValueError("required_field is required")

    # ... more validation

# 3. Add CLI adapter method (backend/core/cli_adapter.py)
def your_cli_command(self, data):
    """Execute your CLI command."""
    cmd = [self.cli_path, 'your-command', '--json-output']
    # ... build command ...

    result = subprocess.run(cmd, ...)
    return json.loads(result.stdout)

# 4. Add CLI command (cli/src/cli.py)
@click.command()
@click.option('--json-output', is_flag=True)
def your_command(json_output):
    """Your CLI command."""
    # ... implementation ...

    if json_output:
        click.echo(json.dumps(result))

# 5. Write tests
def test_your_endpoint(client):
    response = client.post('/api/your-endpoint', json={...})
    assert response.status_code == 200
```

### Example: Adding a New React Component

**Quick Template:**

```javascript
// 1. Create component file (src/components/YourComponent.jsx)
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './YourComponent.scss';

/**
 * Your component description.
 *
 * @param {Object} props - Component props
 * @param {any} props.someProp - Description of prop
 */
export const YourComponent = ({ someProp }) => {
  const [state, setState] = useState(initialState);

  useEffect(() => {
    // Side effects
  }, [dependencies]);

  const handleSomething = async () => {
    try {
      const response = await axios.post('/api/your-endpoint', data);
      setState(response.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    <div className="your-component">
      {/* JSX here */}
    </div>
  );
};

// 2. Create styles (src/components/YourComponent.scss)
.your-component {
  // Styles here
}

// 3. Import in App.jsx
import { YourComponent } from './components/YourComponent';

function App() {
  return (
    <div className="app">
      <YourComponent someProp={value} />
    </div>
  );
}
```

---

## Working with Dependencies

### Adding Python Dependencies

#### Add New Package

```bash
# Install package
pip install package-name

# Update requirements.txt
pip freeze | grep package-name >> requirements.txt

# Or manually edit requirements.txt
echo "package-name==1.2.3" >> requirements.txt
```

#### Best Practices

**Pin Versions:**
```
# Good (specific version)
flask==3.0.0
requests==2.31.0

# Bad (no version, can break)
flask
requests
```

**Group Dependencies:**
```
# requirements.txt (production)
Flask==3.0.0
flask-cors==4.0.0
requests==2.31.0

# requirements-dev.txt (development only)
pytest==7.4.3
pytest-cov==4.1.0
black==23.7.0
mypy==1.5.0
```

**Install Development Dependencies:**
```bash
pip install -r requirements-dev.txt
```

#### Check for Security Issues

```bash
# Install safety
pip install safety

# Scan for vulnerabilities
safety check

# Update vulnerable packages
pip install --upgrade vulnerable-package
```

### Adding JavaScript Dependencies

#### Add New Package

```bash
# Production dependency
npm install package-name

# Development dependency
npm install --save-dev package-name

# Specific version
npm install package-name@1.2.3
```

#### Update Dependencies

```bash
# Check outdated packages
npm outdated

# Update all packages (careful!)
npm update

# Update specific package
npm install package-name@latest

# Update major version
npm install package-name@^2.0.0
```

#### Security Audit

```bash
# Audit for vulnerabilities
npm audit

# Fix automatically (if possible)
npm audit fix

# Force fix (may break things)
npm audit fix --force
```

### Updating Dependencies

#### Python

```bash
# List outdated packages
pip list --outdated

# Update specific package
pip install --upgrade flask

# Update all packages (careful!)
pip list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 pip install -U

# Freeze new versions
pip freeze > requirements.txt
```

#### JavaScript

```bash
# Check outdated
npm outdated

# Update minor/patch versions
npm update

# Update to latest (including major)
npm install package@latest

# Update package.json
npm install

# Verify build still works
npm run build
```

### Security Considerations

#### Scan for Vulnerabilities

**Python:**
```bash
# Install pip-audit
pip install pip-audit

# Audit dependencies
pip-audit

# Audit specific file
pip-audit -r requirements.txt
```

**JavaScript:**
```bash
# Built-in audit
npm audit

# View detailed report
npm audit --json

# Only show high severity
npm audit --audit-level=high
```

#### Dependency Review Checklist

Before adding new dependency:

- [ ] Is it actively maintained? (recent commits)
- [ ] Does it have security issues? (npm audit, safety)
- [ ] Is it well-documented?
- [ ] Does it have tests?
- [ ] Is the license compatible? (MIT, Apache, BSD)
- [ ] Is it necessary? (can we implement ourselves?)
- [ ] What's the bundle size? (JavaScript - check bundlephobia.com)

---

## Database and Data

### Wordlist Management

#### Wordlist File Format

**TSV Format (Tab-Separated Values):**
```
WORD        SCORE  SOURCE
HELLO       85     comprehensive
CROSSWORD   90     comprehensive
PUZZLE      88     comprehensive
```

**Columns:**
- `WORD` - Uppercase word (3-21 characters)
- `SCORE` - Quality score (0-100, higher = better)
- `SOURCE` - Origin (comprehensive, crosswordese, custom)

#### Adding Words to Wordlist

**Manual Edit:**
```bash
# Edit file directly
nano data/wordlists/custom/my-words.txt

# Add words (one per line)
MYWORD      85     custom
ANOTHER     90     custom
```

**Via API:**
```bash
# Add single word
curl -X POST http://localhost:5000/api/wordlists/custom/add-word \
  -H "Content-Type: application/json" \
  -d '{"word": "MYWORD", "score": 85}'
```

**Programmatically:**
```python
# Python script
def add_words_to_wordlist(wordlist_path, words):
    """Add words to wordlist file."""
    with open(wordlist_path, 'a') as f:
        for word, score in words:
            f.write(f"{word.upper()}\t{score}\tcustom\n")

# Usage
add_words_to_wordlist(
    'data/wordlists/custom/my-words.txt',
    [('HELLO', 85), ('WORLD', 90)]
)
```

#### Creating Custom Wordlist

**From Scratch:**
```bash
# Create file
touch data/wordlists/custom/themed-words.txt

# Add header (optional)
echo -e "WORD\tSCORE\tSOURCE" > data/wordlists/custom/themed-words.txt

# Add words
echo -e "THEMEWORD\t95\tcustom" >> data/wordlists/custom/themed-words.txt
```

**From Existing List:**
```python
# Convert plain text list to TSV
def convert_wordlist(input_file, output_file, default_score=80):
    """Convert plain text wordlist to TSV format."""
    with open(input_file) as f_in, open(output_file, 'w') as f_out:
        f_out.write("WORD\tSCORE\tSOURCE\n")

        for line in f_in:
            word = line.strip().upper()
            if 3 <= len(word) <= 21:  # Valid length
                f_out.write(f"{word}\t{default_score}\tcustom\n")

# Usage
convert_wordlist(
    'my-words.txt',
    'data/wordlists/custom/my-words-formatted.txt'
)
```

#### Upload Wordlist via Web UI

**API Endpoint:**
```bash
POST /api/wordlists/upload

# Upload file
curl -X POST http://localhost:5000/api/wordlists/upload \
  -F "file=@my-wordlist.txt" \
  -F "name=my-custom-list"
```

**Validation:**
- File extension must be `.txt`
- Maximum size: 10MB
- Words must be uppercase letters only
- Word length: 3-21 characters

### Test Data Creation

#### Creating Test Grids

**Empty Grid:**
```python
def create_empty_grid(size):
    """Create empty grid for testing."""
    return {
        'size': size,
        'grid': [
            [{'letter': '', 'isBlack': False} for _ in range(size)]
            for _ in range(size)
        ]
    }

# Usage
grid = create_empty_grid(15)
```

**Grid with Pattern:**
```python
def create_grid_with_pattern(size, black_squares):
    """Create grid with specific black square pattern."""
    grid = create_empty_grid(size)

    for row, col in black_squares:
        grid['grid'][row][col]['isBlack'] = True

    return grid

# Usage (NYT-style symmetric pattern)
black_squares = [
    (0, 5), (0, 11),  # Top row
    (14, 4), (14, 10),  # Bottom row (symmetric)
    # ... more squares
]
grid = create_grid_with_pattern(15, black_squares)
```

**Partially Filled Grid:**
```python
def create_partially_filled_grid(size, fill_percentage=0.3):
    """Create grid with some cells pre-filled."""
    import random
    import string

    grid = create_empty_grid(size)
    total_cells = size * size
    cells_to_fill = int(total_cells * fill_percentage)

    for _ in range(cells_to_fill):
        row = random.randint(0, size - 1)
        col = random.randint(0, size - 1)
        letter = random.choice(string.ascii_uppercase)

        grid['grid'][row][col]['letter'] = letter

    return grid

# Usage
grid = create_partially_filled_grid(15, fill_percentage=0.3)
```

### Fixture Management

**Shared Test Fixtures:**

```python
# backend/tests/fixtures/grid_fixtures.py
import pytest

@pytest.fixture
def empty_3x3_grid():
    """3×3 empty grid."""
    return {
        'size': 3,
        'grid': [
            [{'letter': '', 'isBlack': False}] * 3,
            [{'letter': '', 'isBlack': False}] * 3,
            [{'letter': '', 'isBlack': False}] * 3
        ]
    }

@pytest.fixture
def sample_wordlist():
    """Small wordlist for testing."""
    return ['CAT', 'DOG', 'RAT', 'BAT', 'HAT']

@pytest.fixture
def realistic_15x15_grid():
    """Realistic 15×15 NYT-style grid."""
    # Load from file or generate
    with open('backend/tests/fixtures/nyt_15x15.json') as f:
        return json.load(f)
```

**Usage in Tests:**
```python
# backend/tests/unit/test_something.py
from backend.tests.fixtures.grid_fixtures import empty_3x3_grid

def test_something(empty_3x3_grid):
    """Test using fixture."""
    grid = Grid.from_dict(empty_3x3_grid)
    assert grid.size == 3
```

### Data Migration

**Not Applicable:** This project uses file-based data (no database migrations).

**Wordlist Updates:**
```bash
# Add new wordlist version
cp data/wordlists/comprehensive.txt data/wordlists/comprehensive-v2.txt

# Update with new words
# ... edit file ...

# Switch default (update code reference)
# backend/core/wordlist_resolver.py
DEFAULT_WORDLIST = 'data/wordlists/comprehensive-v2.txt'
```

---

## Performance Considerations

### Profiling Tools

#### Python Profiling (cProfile)

**Basic Profiling:**
```python
import cProfile
import pstats

# Profile function
cProfile.run('autofill.fill()', 'profile_stats')

# View results
p = pstats.Stats('profile_stats')
p.sort_stats('cumulative')
p.print_stats(20)  # Top 20 slowest functions
```

**Decorator for Profiling:**
```python
import cProfile
import functools

def profile(func):
    """Profile function execution."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        result = profiler.runcall(func, *args, **kwargs)

        profiler.print_stats(sort='cumulative')
        return result

    return wrapper

# Usage
@profile
def slow_function():
    # ... code ...
    pass
```

#### Line Profiler (line_profiler)

**Install:**
```bash
pip install line_profiler
```

**Usage:**
```python
# Add @profile decorator (no import needed)
@profile
def autofill_grid(grid, wordlist):
    slots = grid.get_slots()  # Line-by-line timing
    for slot in slots:
        candidates = wordlist.match(slot.pattern)
        # ...
```

**Run:**
```bash
# Profile script
kernprof -l -v script.py

# Output shows time per line
Line #      Hits         Time  Per Hit   % Time  Line Contents
==============================================================
     5         1      1000.0   1000.0     10.0      slots = grid.get_slots()
     6       100     8000.0     80.0     80.0      for slot in slots:
     7       100     1000.0     10.0     10.0          candidates = wordlist.match(slot.pattern)
```

#### Memory Profiler (memory_profiler)

**Install:**
```bash
pip install memory_profiler
```

**Usage:**
```python
from memory_profiler import profile

@profile
def memory_intensive_function():
    large_list = [0] * 10000000  # Allocates ~76MB
    # ... processing ...
    return result
```

**Run:**
```bash
python -m memory_profiler script.py

# Output:
Line #    Mem usage    Increment  Occurrences   Line Contents
=============================================================
     3     20.5 MiB     20.5 MiB           1       large_list = [0] * 10000000
     4     96.9 MiB     76.4 MiB           1       # Allocated 76MB
```

#### JavaScript Profiling (Chrome DevTools)

**Performance Tab:**
1. Open DevTools (F12)
2. Go to Performance tab
3. Click Record
4. Interact with app (e.g., autofill grid)
5. Stop recording
6. Analyze flame graph

**Key Metrics:**
- **FPS:** Frames per second (should be 60)
- **CPU:** Time spent in JavaScript execution
- **Main Thread:** Long tasks blocking UI

**Identify Bottlenecks:**
- Look for long yellow bars (JavaScript execution)
- Red triangles indicate forced reflows/layouts
- Bottom-up view shows slowest functions

**React Profiler:**
```javascript
import { Profiler } from 'react';

function onRenderCallback(
  id,
  phase,
  actualDuration,
  baseDuration,
  startTime,
  commitTime
) {
  console.log(`${id} (${phase}) took ${actualDuration}ms`);
}

<Profiler id="GridEditor" onRender={onRenderCallback}>
  <GridEditor grid={grid} />
</Profiler>
```

### Performance Benchmarks

#### Autofill Performance Targets

**Grid Size vs. Time:**
| Grid Size | Algorithm | Target Time | Acceptable Time |
|-----------|-----------|-------------|-----------------|
| 11×11 | CSP | <15s | <30s |
| 11×11 | Beam Search | <30s | <60s |
| 15×15 | CSP | <2min | <5min |
| 15×15 | Hybrid | <3min | <5min |
| 21×21 | Hybrid | <15min | <30min |

**Iteration Counts:**
- Fast fill: 500-2000 iterations
- Average fill: 2000-10000 iterations
- Hard fill: 10000-50000 iterations
- Timeout: 100000+ iterations (unfillable)

#### API Response Time Targets

| Endpoint | Target | Acceptable | Notes |
|----------|--------|------------|-------|
| `/api/health` | <50ms | <100ms | No CLI call |
| `/api/pattern` | <500ms | <1s | CLI + trie search |
| `/api/number` | <100ms | <200ms | CLI + numbering |
| `/api/normalize` | <50ms | <100ms | CLI + string ops |
| `/api/fill` (start) | <300ms | <500ms | Spawn subprocess |
| `/api/fill` (complete) | Varies | - | See autofill targets |

#### Pattern Matching Performance

**Algorithm Comparison (454k words):**
| Algorithm | Cold Start | Warm Cache | Use Case |
|-----------|------------|------------|----------|
| Regex | 100-200ms | 80-150ms | Simple patterns |
| Trie | 50-100ms | 10-20ms | Default (10-50x faster) |
| Aho-Corasick | 150-300ms | 5-15ms | Batch operations |

### Optimization Strategies

#### Backend Optimizations

**1. Cache Wordlist in Memory:**
```python
# Instead of loading every request
class WordListCache:
    _cache = {}

    @classmethod
    def get_wordlist(cls, path):
        if path not in cls._cache:
            cls._cache[path] = WordList.load(path)
        return cls._cache[path]
```

**2. Use Trie for Pattern Matching:**
```python
# Trie is 10-50x faster than regex
matcher = TriePatternMatcher(wordlist)  # Build once
results = matcher.match('C?T')  # Fast lookup
```

**3. Limit Result Sets:**
```python
# Don't return all 127 matches
results = matcher.match('C?T', max_results=20)
```

**4. Use Subprocess Pool (Advanced):**
```python
# Keep CLI processes warm (eliminates startup time)
# Requires daemon mode in CLI
```

#### Frontend Optimizations

**1. Memoize Components:**
```javascript
import React, { memo } from 'react';

// Only re-render if props change
const Cell = memo(({ cell, row, col, onClick }) => {
  return <div onClick={() => onClick(row, col)}>{cell.letter}</div>;
});
```

**2. Virtualize Large Grids:**
```javascript
// For very large grids (21×21), render only visible cells
import { FixedSizeGrid } from 'react-window';

<FixedSizeGrid
  columnCount={21}
  columnWidth={40}
  height={600}
  rowCount={21}
  rowHeight={40}
  width={840}
>
  {Cell}
</FixedSizeGrid>
```

**3. Debounce Input:**
```javascript
import { debounce } from 'lodash';

const handlePatternChange = debounce((pattern) => {
  // Only search after user stops typing for 300ms
  searchPattern(pattern);
}, 300);
```

**4. Lazy Load Components:**
```javascript
import React, { lazy, Suspense } from 'react';

const HeavyComponent = lazy(() => import('./HeavyComponent'));

<Suspense fallback={<div>Loading...</div>}>
  <HeavyComponent />
</Suspense>
```

### Memory Management

#### Python Memory Management

**Use Generators for Large Datasets:**
```python
# BAD: Loads all 454k words into memory
def load_wordlist(path):
    with open(path) as f:
        return [line.strip() for line in f]

# GOOD: Yields one word at a time
def load_wordlist(path):
    with open(path) as f:
        for line in f:
            yield line.strip()
```

**Clear Large Objects:**
```python
# After autofill completes
del autofill_state
del candidate_cache
import gc
gc.collect()  # Force garbage collection
```

**Monitor Memory Usage:**
```python
import tracemalloc

tracemalloc.start()

# ... code ...

current, peak = tracemalloc.get_traced_memory()
print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")
tracemalloc.stop()
```

#### JavaScript Memory Management

**Avoid Memory Leaks:**
```javascript
// BAD: Event listener not cleaned up
useEffect(() => {
  window.addEventListener('resize', handleResize);
});

// GOOD: Cleanup function
useEffect(() => {
  window.addEventListener('resize', handleResize);

  return () => {
    window.removeEventListener('resize', handleResize);
  };
}, []);
```

**Clear Timers/Intervals:**
```javascript
useEffect(() => {
  const interval = setInterval(() => {
    // ... polling ...
  }, 1000);

  return () => clearInterval(interval);
}, []);
```

**Avoid Large State Objects:**
```javascript
// BAD: Entire grid in one state
const [appState, setAppState] = useState({
  grid: largeGrid,
  settings: {...},
  history: [...]
});

// GOOD: Separate states
const [grid, setGrid] = useState(largeGrid);
const [settings, setSettings] = useState({...});
const [history, setHistory] = useState([]);
```

---

## Common Tasks

### Add a New CLI Command

**Step-by-Step:**

1. **Add Command to CLI:**
```python
# cli/src/cli.py
@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.option('--json-output', is_flag=True, help='Output JSON')
def my_command(input_file, output, json_output):
    """
    My new command description.

    Example:
        crossword my-command input.json --output result.json
    """
    # Load input
    with open(input_file) as f:
        data = json.load(f)

    # Process
    result = process_data(data)

    # Output
    if json_output:
        click.echo(json.dumps(result))
    else:
        click.echo(f"Processed: {result}")

    # Save to file if specified
    if output:
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)

# Add to CLI group
cli.add_command(my_command)
```

2. **Test Command:**
```bash
crossword my-command test.json --json-output
```

3. **Add Tests:**
```python
# cli/tests/integration/test_cli_commands.py
def test_my_command():
    """Test my-command CLI command."""
    result = subprocess.run(
        ['crossword', 'my-command', 'test.json', '--json-output'],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert 'expected_key' in output
```

### Add a New API Endpoint

**Step-by-Step:**

1. **Add Route:**
```python
# backend/api/routes.py
@app.route('/api/my-endpoint', methods=['POST'])
def my_endpoint():
    """My new endpoint description."""
    try:
        data = request.json

        # Validate
        if not data.get('required_field'):
            return jsonify({'error': 'required_field is required'}), 400

        # Call CLI
        cli_adapter = get_adapter()
        result = cli_adapter.my_command(data)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

2. **Add CLI Adapter Method:**
```python
# backend/core/cli_adapter.py
def my_command(self, data):
    """Execute my-command via CLI."""
    # Write data to temp file
    temp_file = self._write_temp_file(data)

    try:
        cmd = [
            self.cli_path,
            'my-command',
            temp_file,
            '--json-output'
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        return json.loads(result.stdout)

    finally:
        os.remove(temp_file)
```

3. **Test Endpoint:**
```bash
curl -X POST http://localhost:5000/api/my-endpoint \
  -H "Content-Type: application/json" \
  -d '{"required_field": "value"}'
```

4. **Add Tests:**
```python
# backend/tests/integration/test_api.py
def test_my_endpoint(client):
    """Test /api/my-endpoint."""
    response = client.post('/api/my-endpoint', json={
        'required_field': 'value'
    })

    assert response.status_code == 200
    assert 'expected_key' in response.json
```

### Add a New React Component

**Step-by-Step:**

1. **Create Component File:**
```javascript
// src/components/MyComponent.jsx
import React, { useState } from 'react';
import './MyComponent.scss';

/**
 * MyComponent description.
 *
 * @param {Object} props - Component props
 * @param {string} props.title - Component title
 */
export const MyComponent = ({ title }) => {
  const [state, setState] = useState('initial');

  const handleClick = () => {
    setState('clicked');
  };

  return (
    <div className="my-component">
      <h2>{title}</h2>
      <button onClick={handleClick}>Click Me</button>
      <p>State: {state}</p>
    </div>
  );
};
```

2. **Create Styles:**
```scss
// src/components/MyComponent.scss
.my-component {
  padding: 1rem;
  border: 1px solid #ccc;
  border-radius: 4px;

  h2 {
    margin-top: 0;
  }

  button {
    padding: 0.5rem 1rem;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;

    &:hover {
      background: #0056b3;
    }
  }
}
```

3. **Import in App:**
```javascript
// src/App.jsx
import { MyComponent } from './components/MyComponent';

function App() {
  return (
    <div className="app">
      <MyComponent title="My New Component" />
    </div>
  );
}
```

4. **Test in Browser:**
```bash
npm run dev
# Open http://localhost:3000
```

### Update Wordlists

**Add Words Manually:**
```bash
# Edit wordlist
nano data/wordlists/custom/my-words.txt

# Add words (TSV format)
NEWWORD     85     custom
ANOTHER     90     custom

# Save and exit
```

**Add Words Programmatically:**
```python
# scripts/add_words.py
import sys

def add_words_to_wordlist(wordlist_path, words):
    """Add words to wordlist."""
    with open(wordlist_path, 'a') as f:
        for word, score in words:
            f.write(f"{word.upper()}\t{score}\tcustom\n")

    print(f"Added {len(words)} words to {wordlist_path}")

if __name__ == '__main__':
    words = [
        ('HELLO', 85),
        ('WORLD', 90),
        ('PYTHON', 95)
    ]

    add_words_to_wordlist('data/wordlists/custom/my-words.txt', words)
```

**Run Script:**
```bash
python scripts/add_words.py
```

**Validate Wordlist:**
```bash
# Check format
head data/wordlists/custom/my-words.txt

# Count words
wc -l data/wordlists/custom/my-words.txt

# Check for duplicates
sort data/wordlists/custom/my-words.txt | uniq -d
```

### Fix a Bug

**Step-by-Step Workflow:**

1. **Reproduce Bug:**
```bash
# Document exact steps to reproduce
# Example: Pattern search returns wrong results for "C?T"

curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{"pattern": "C?T", "max_results": 10}'

# Expected: CAT, COT, CUT
# Actual: CAT, CUT (COT missing)
```

2. **Write Failing Test:**
```python
# backend/tests/unit/test_pattern_matcher.py
def test_pattern_matcher_cot_bug():
    """Test that COT is returned for C?T pattern (bug fix)."""
    matcher = PatternMatcher(['CAT', 'COT', 'CUT'])
    results = matcher.match('C?T')

    assert 'COT' in results, "COT should be in results"
```

**Run Test (Should Fail):**
```bash
pytest backend/tests/unit/test_pattern_matcher.py::test_pattern_matcher_cot_bug -v
# FAILED - COT not in results
```

3. **Debug Issue:**
```python
# Add debug logging
import logging
logger = logging.getLogger(__name__)

def match(self, pattern):
    logger.debug(f"Matching pattern: {pattern}")
    results = self._search(pattern)
    logger.debug(f"Found {len(results)} matches: {results}")
    return results
```

**Run with Debug:**
```bash
python -m pytest backend/tests/unit/test_pattern_matcher.py::test_pattern_matcher_cot_bug -v -s --log-cli-level=DEBUG

# Output shows:
# Matching pattern: C?T
# Found 2 matches: ['CAT', 'CUT']
# → COT is missing from search!
```

4. **Identify Root Cause:**
```python
# In pattern_matcher.py
# BUG: Incorrect regex conversion
def _convert_pattern_to_regex(self, pattern):
    # BUG: Missing 'O' in character class
    regex = pattern.replace('?', '[A-NP-Z]')  # Skips 'O'!
    return regex

# Should be:
def _convert_pattern_to_regex(self, pattern):
    regex = pattern.replace('?', '[A-Z]')
    return regex
```

5. **Fix Bug:**
```python
# cli/src/fill/pattern_matcher.py
def _convert_pattern_to_regex(self, pattern):
    """Convert crossword pattern to regex."""
    regex = pattern.replace('?', '[A-Z]')  # FIX: Include all letters
    return regex
```

6. **Run Tests (Should Pass):**
```bash
pytest backend/tests/unit/test_pattern_matcher.py::test_pattern_matcher_cot_bug -v
# PASSED
```

7. **Run Full Test Suite:**
```bash
pytest
# All 165 tests passing
```

8. **Commit Fix:**
```bash
git add cli/src/fill/pattern_matcher.py backend/tests/unit/test_pattern_matcher.py
git commit -m "Fix: Include all letters in pattern matcher regex

- Bug: COT was missing from C?T pattern results
- Root cause: Regex excluded 'O' from character class
- Fix: Use [A-Z] instead of [A-NP-Z]
- Test: Added test_pattern_matcher_cot_bug to prevent regression"
```

### Write Tests

**Unit Test Template:**
```python
# backend/tests/unit/test_my_module.py
import pytest
from backend.core.my_module import MyClass

class TestMyClass:
    """Test MyClass functionality."""

    @pytest.fixture
    def my_instance(self):
        """Create instance for testing."""
        return MyClass(param='value')

    def test_basic_functionality(self, my_instance):
        """Test basic functionality."""
        result = my_instance.do_something()
        assert result == 'expected'

    def test_edge_case(self, my_instance):
        """Test edge case handling."""
        with pytest.raises(ValueError):
            my_instance.do_something(invalid_param=True)

    @pytest.mark.parametrize('input,expected', [
        ('input1', 'output1'),
        ('input2', 'output2'),
        ('input3', 'output3'),
    ])
    def test_multiple_cases(self, my_instance, input, expected):
        """Test multiple input/output cases."""
        result = my_instance.process(input)
        assert result == expected
```

**Integration Test Template:**
```python
# backend/tests/integration/test_my_api.py
import pytest

class TestMyAPI:
    """Test My API endpoints."""

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_successful_request(self, client):
        """Test successful API request."""
        response = client.post('/api/my-endpoint', json={
            'field': 'value'
        })

        assert response.status_code == 200
        data = response.json
        assert 'expected_field' in data

    def test_validation_error(self, client):
        """Test validation error handling."""
        response = client.post('/api/my-endpoint', json={
            # Missing required field
        })

        assert response.status_code == 400
        assert 'error' in response.json
```

**Run Tests:**
```bash
# Run specific test file
pytest backend/tests/unit/test_my_module.py -v

# Run with coverage
pytest backend/tests/unit/test_my_module.py --cov=backend.core.my_module

# Run matching pattern
pytest -k "test_my" -v
```

---

## Troubleshooting

### Common Error Messages

#### 1. ModuleNotFoundError

**Error:**
```
ModuleNotFoundError: No module named 'backend'
```

**Cause:** Python path not configured, or package not installed

**Solutions:**

```bash
# Option 1: Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Option 2: Install in editable mode
pip install -e .

# Option 3: Add to Python path in IDE
# VS Code: .vscode/settings.json
# "python.analysis.extraPaths": ["./"]
```

#### 2. CORS Error

**Error (Browser Console):**
```
Access to XMLHttpRequest at 'http://localhost:5000/api/pattern' from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Cause:** Flask CORS not configured or origins not whitelisted

**Solution:**

```python
# backend/app.py
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=[
    'http://localhost:3000',
    'http://127.0.0.1:3000'
])
```

**Restart Flask server after changes.**

#### 3. Port Already in Use

**Error:**
```
OSError: [Errno 48] Address already in use
```

**Cause:** Another process using port 5000 or 3000

**Solutions:**

```bash
# Find process using port
lsof -i :5000

# Kill process
kill -9 <PID>

# Or use different port
# run.py:
app.run(port=5001)

# package.json:
"dev": "vite --port 3001"
```

#### 4. npm install Fails

**Error:**
```
npm ERR! code ELIFECYCLE
npm ERR! errno 1
```

**Solutions:**

```bash
# Clear cache
npm cache clean --force

# Delete node_modules
rm -rf node_modules package-lock.json

# Reinstall
npm install

# If still fails, check Node version
node --version  # Should be 18+
nvm install 18
nvm use 18
npm install
```

#### 5. Tests Failing After git pull

**Error:**
```
FAILED backend/tests/unit/test_validators.py::TestValidators::test_validate_pattern_request_valid
```

**Cause:** Dependencies out of date, or fixtures changed

**Solutions:**

```bash
# Update dependencies
pip install -r requirements.txt
npm install

# Clear pytest cache
pytest --cache-clear

# Rebuild coverage
rm -rf .coverage htmlcov/
pytest --cov=backend

# If still failing, check git diff
git diff HEAD~1 backend/tests/
```

#### 6. CLI Command Not Found

**Error:**
```
crossword: command not found
```

**Cause:** CLI not installed or not in PATH

**Solutions:**

```bash
# Install CLI in editable mode
cd cli
pip install -e .
cd ..

# Verify installation
which crossword
crossword --version

# If still not found, use full path
python cli/src/cli.py --help

# Or add to PATH
export PATH="${PATH}:$(pwd)/cli"
```

#### 7. Autofill Timeout

**Error (API Response):**
```json
{
  "error": "Autofill timed out after 300 seconds"
}
```

**Cause:** Grid too hard to fill, or parameters too strict

**Solutions:**

```bash
# Increase timeout
curl -X POST http://localhost:5000/api/fill \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [...],
    "timeout": 600,  # 10 minutes instead of 5
    "algorithm": "hybrid"
  }'

# Lower min_score threshold
# ... "min_score": 30 (instead of 50)

# Use larger wordlist
# ... "wordlists": ["comprehensive"]

# Try different algorithm
# ... "algorithm": "beam_search"
```

#### 8. React Component Not Rendering

**Error:** Component appears blank, no errors

**Debugging:**

```javascript
// Add console.log in component
export const MyComponent = ({ prop }) => {
  console.log('MyComponent rendered with prop:', prop);

  // Check if prop is undefined
  if (!prop) {
    console.error('Prop is undefined!');
    return <div>Error: Prop required</div>;
  }

  return <div>{/* ... */}</div>;
};
```

**Check:**
- Browser console for errors
- React DevTools for component tree
- Props are being passed correctly
- Import/export syntax correct

### Build Failures

#### Backend Build Issues

**Symptom:** `python run.py` fails with import error

**Checklist:**

```bash
# 1. Verify virtual environment active
which python  # Should point to venv/bin/python

# 2. Check dependencies installed
pip list | grep flask

# 3. Reinstall dependencies
pip install -r requirements.txt

# 4. Check for syntax errors
python -m py_compile backend/app.py

# 5. Run with verbose errors
python -v run.py
```

#### Frontend Build Issues

**Symptom:** `npm run build` fails

**Checklist:**

```bash
# 1. Check Node version
node --version  # Should be 18+

# 2. Clear cache
rm -rf node_modules/.vite

# 3. Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# 4. Check for syntax errors
npm run dev  # Better error messages than build

# 5. Check import paths (case-sensitive)
# Ensure: import { Component } from './Component';
# Not:    import { Component } from './component';
```

### Test Failures

#### Tests Pass Locally, Fail in CI

**Common Causes:**

1. **Timing Issues:**
```python
# BAD: Hard-coded sleep
time.sleep(1)

# GOOD: Retry with timeout
from tenacity import retry, stop_after_delay

@retry(stop=stop_after_delay(5))
def wait_for_completion():
    assert task.status == 'complete'
```

2. **File Path Issues:**
```python
# BAD: Relative path (breaks in CI)
data = load_file('test_data/grid.json')

# GOOD: Absolute path from fixture
@pytest.fixture
def test_data_dir():
    return Path(__file__).parent / 'test_data'

def test_something(test_data_dir):
    data = load_file(test_data_dir / 'grid.json')
```

3. **Environment Differences:**
```python
# Use tmp_path fixture for temporary files
def test_file_creation(tmp_path):
    file = tmp_path / 'test.txt'
    file.write_text('test')
    assert file.exists()
```

#### Flaky Tests

**Symptom:** Test passes sometimes, fails other times

**Debugging:**

```bash
# Run test 100 times to reproduce
pytest backend/tests/unit/test_flaky.py -v --count=100

# Run with random order to detect dependencies
pytest --random-order

# Isolate test
pytest backend/tests/unit/test_flaky.py::test_specific -v -s
```

**Common Fixes:**

```python
# BAD: Depends on system time
def test_timestamp():
    now = time.time()
    assert result.timestamp == now  # Flaky!

# GOOD: Use freezegun
from freezegun import freeze_time

@freeze_time("2025-01-01 12:00:00")
def test_timestamp():
    assert result.timestamp == datetime(2025, 1, 1, 12, 0, 0)
```

### Runtime Issues

#### Memory Leak

**Symptom:** Memory usage grows over time

**Debugging:**

```python
import tracemalloc
import gc

tracemalloc.start()

# ... run code ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

**Common Causes:**

- Event listeners not cleaned up (JavaScript)
- Large objects not deleted (Python)
- Circular references preventing garbage collection

**Fixes:**

```javascript
// JavaScript: Clean up event listeners
useEffect(() => {
  window.addEventListener('resize', handleResize);

  return () => {
    window.removeEventListener('resize', handleResize);
  };
}, []);
```

```python
# Python: Explicitly delete large objects
del large_wordlist
del autofill_state
gc.collect()
```

#### Slow Performance

**Symptom:** Application feels sluggish

**Profiling:**

```bash
# Backend profiling
python -m cProfile -o profile.stats run.py
python -m pstats profile.stats
> sort cumulative
> stats 20

# Frontend profiling
# Use Chrome DevTools > Performance tab
```

**Common Bottlenecks:**

- **Backend:** Loading wordlist every request (cache it)
- **Frontend:** Re-rendering entire grid on every change (memoize cells)
- **API:** Subprocess overhead (keep CLI process alive)

### FAQ

**Q: How do I run only fast tests?**

```bash
pytest -m "not slow"
```

**Q: How do I debug a specific test?**

```bash
pytest backend/tests/unit/test_validators.py::TestValidators::test_validate_pattern_request_valid -vv -s --pdb
```

**Q: How do I see SQL queries being executed?**

A: This project doesn't use SQL (file-based data).

**Q: How do I clear the cache?**

```bash
# Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
pytest --cache-clear

# npm cache
npm cache clean --force

# Browser cache
# Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
```

**Q: How do I update the frontend without rebuilding?**

A: Use development server (`npm run dev`) which has Hot Module Replacement (HMR). Changes reflect instantly.

**Q: How do I test API endpoints without Postman?**

```bash
# Use curl
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{"pattern": "C?T"}'

# Or httpie (friendlier)
http POST localhost:5000/api/pattern pattern=C?T
```

**Q: How do I add a new dependency without breaking things?**

```bash
# 1. Install dependency
pip install new-package

# 2. Run tests
pytest

# 3. If tests pass, update requirements.txt
pip freeze | grep new-package >> requirements.txt

# 4. Commit both code and requirements.txt
git add requirements.txt
git commit -m "Add new-package for feature X"
```

---

## Resources

### Documentation

**Project Documentation:**
- Architecture: `docs/ARCHITECTURE.md`
- API Reference: `docs/api/API_REFERENCE.md`
- OpenAPI Spec: `docs/api/openapi.yaml`
- Testing Guide: `docs/ops/TESTING.md`
- Component Specs: `docs/specs/`

**External Documentation:**
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Click Documentation](https://click.palletsprojects.com/)
- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [pytest Documentation](https://docs.pytest.org/)
- [NumPy Documentation](https://numpy.org/doc/)

### Code Examples

**Example Tests:**
- `backend/tests/unit/test_validators.py` - Request validation
- `backend/tests/integration/test_api.py` - API endpoints
- `backend/tests/integration/test_realistic_grids.py` - E2E workflows

**Example Components:**
- `src/components/GridEditor.jsx` - Complex React component
- `src/components/AutofillPanel.jsx` - State management + SSE

**Example CLI Commands:**
- `cli/src/cli.py` - All 8 CLI commands
- `cli/src/fill/autofill.py` - CSP algorithm implementation

### Tools and Libraries

**Development Tools:**
- **Black:** Python code formatter
- **Ruff:** Fast Python linter
- **ESLint:** JavaScript linter
- **Prettier:** JavaScript formatter
- **pre-commit:** Git hooks framework

**Testing Tools:**
- **pytest:** Test framework
- **pytest-cov:** Coverage reporting
- **pytest-xdist:** Parallel test execution
- **React Testing Library:** React component testing (future)

**Debugging Tools:**
- **pdb:** Python debugger
- **ipdb:** Enhanced Python debugger
- **Chrome DevTools:** Browser debugging
- **React DevTools:** React component inspection

### Community

**Getting Help:**

1. **Check Existing Documentation:**
   - `docs/ARCHITECTURE.md` for system design
   - `docs/ops/TESTING.md` for testing help
   - This file for development workflows

2. **Search Issues:**
   - Check GitHub/GitLab issues for similar problems
   - Search closed issues for solutions

3. **Ask Team:**
   - Slack channel (if applicable)
   - Team email
   - Weekly standup

4. **External Resources:**
   - Stack Overflow (tag questions appropriately)
   - Flask/React communities
   - Python Discord

### Training Materials

**Python:**
- [Real Python](https://realpython.com/) - Tutorials and courses
- [Python Official Tutorial](https://docs.python.org/3/tutorial/)
- [Effective Python](https://effectivepython.com/) - Book

**React:**
- [React Official Tutorial](https://react.dev/learn)
- [React Patterns](https://reactpatterns.com/)
- [Kent C. Dodds Blog](https://kentcdodds.com/blog)

**Testing:**
- [pytest Documentation](https://docs.pytest.org/en/stable/contents.html)
- [Testing Best Practices](https://testdriven.io/)

**Algorithms:**
- [CSP Algorithms](https://en.wikipedia.org/wiki/Constraint_satisfaction_problem)
- [Backtracking](https://en.wikipedia.org/wiki/Backtracking)
- [Beam Search](https://en.wikipedia.org/wiki/Beam_search)

---

## Conclusion

This development guide should enable you to:

- ✅ Set up your development environment in **<30 minutes**
- ✅ Make your first code change in **<1 hour**
- ✅ Understand the development workflow
- ✅ Know where to find help

### Quick Start Checklist

**New Developer Setup:**
- [ ] Clone repository
- [ ] Install Python 3.9+, Node.js 18+
- [ ] Create virtual environment
- [ ] Install dependencies (backend + CLI + frontend)
- [ ] Run `pytest` (should pass)
- [ ] Run `npm run dev` (should start)
- [ ] Run `python run.py` (should start)
- [ ] Make test change and verify hot reload works

### Next Steps

1. **Read Architecture:** `docs/ARCHITECTURE.md`
2. **Explore Codebase:** Start with `backend/app.py`, `cli/src/cli.py`, `src/App.jsx`
3. **Run Tests:** `pytest -v` and explore test files
4. **Try CLI Commands:** `crossword --help`
5. **Make First Contribution:** Pick a small task or bug fix

### Getting Help

**In Order of Preference:**
1. Search this document (Ctrl+F)
2. Check `docs/ARCHITECTURE.md`
3. Check `docs/ops/TESTING.md`
4. Check component specs (`docs/specs/`)
5. Ask team in Slack/email
6. Create GitHub issue

---

**Document Version:** 1.0.0
**Last Updated:** 2025-12-27
**Maintained By:** Development Team
**Next Review:** After first 5 new developers onboard

**Feedback Welcome:** If you found this guide helpful or confusing, please let us know! Email [team@example.com] or create an issue.
