# Crossword Builder - Phase 2 CLI Tool

**Status:** 🚧 In Development
**Type:** Command-line application
**Primary Feature:** CSP-based automated grid filling

## Overview

Python CLI tool for comprehensive crossword puzzle construction with automated filling using constraint satisfaction algorithms.

## Components

### 1. Grid Engine (`src/core/`)
- Grid data structure (NumPy-based)
- 180° rotational symmetry enforcement
- Validation (connectivity, minimum word length)
- Auto-numbering system

### 2. Fill Engine (`src/fill/`)
- **CSP Solver** - Backtracking with heuristics (MCV, LCV, forward checking)
- Pattern matcher - Enhanced from Phase 1
- Word scorer - Crossword-ability scoring
- Word list manager

### 3. Clue Manager (`src/clues/`)
- Local clue database (JSON/SQLite)
- Difficulty tagging (Monday-Saturday NYT style)
- Multiple clue types per word

### 4. Export Engine (`src/export/`)
- HTML export
- PDF export (reportlab)
- .puz format (pypuz)
- JSON export

### 5. CLI Interface (`src/cli/`)
- Click-based command framework
- Rich terminal UI
- Interactive mode

## Commands

```bash
# Create new grid
crossword new --size 15 --output puzzle.json

# Fill grid automatically
crossword fill puzzle.json --wordlists personal.txt standard.txt

# Validate grid
crossword validate puzzle.json

# Export to formats
crossword export puzzle.json --format puz --output puzzle.puz
crossword export puzzle.json --format pdf --output puzzle.pdf

# Interactive mode
crossword interactive puzzle.json
```

## Architecture

```
CLI Layer (Click + Rich)
    ↓
Grid Engine (NumPy)
    ↓
Fill Engine (CSP Solver)
    ↓
Export Engine (HTML/PDF/.puz)
```

## Performance Targets

| Grid Size | Fill Time Target |
|-----------|------------------|
| 11×11     | <30 seconds      |
| 15×15     | <5 minutes       |
| 21×21     | <30 minutes      |

## Installation

```bash
cd cli
pip install -r requirements.txt
pip install -e .
```

## Development

```bash
# Run tests
pytest tests/ -v

# Type checking
mypy src/

# Format code
black src/
```

## Documentation

See `docs/phase2-cli/` for detailed architecture and implementation guides.
