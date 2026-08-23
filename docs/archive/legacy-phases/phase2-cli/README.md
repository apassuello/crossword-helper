# Phase 2: CLI Tool

**Goal:** Comprehensive Python CLI for crossword construction with autofill

**Timeline:** 3-4 weeks
**Complexity:** High
**Status:** ⏸️ Waiting for Phase 1 completion

---

## Overview

Command-line tool for crossword puzzle construction with focus on **automated grid filling** using constraint satisfaction algorithms.

**Key Feature:** CSP-based autofill that fills grids using backtracking with intelligent heuristics (MRV, LCV, forward checking).

---

## Features

1. **Grid Engine** - Create, validate, and manage grids
2. **Autofill Engine** - CSP solver with backtracking (THE main feature)
3. **Pattern Matcher** - Enhanced word search with scoring
4. **Clue Manager** - Store and retrieve clues with local database
5. **Export Engine** - HTML, PDF, .puz format export

---

## Documentation

| Document | Purpose |
|----------|---------|
| `01-architecture.md` | CLI tool design and CSP algorithm details |
| `02-specifications.md` | Detailed technical specifications for all components |
| `03-implementation-prompts.md` | Step-by-step execution script (10 prompts) |

---

## CLI Commands

```bash
# Create new grid
crossword new --size 15 --output puzzle.json

# Fill grid automatically
crossword fill puzzle.json --wordlists personal.txt standard.txt

# Validate grid
crossword validate puzzle.json

# Export to formats
crossword export puzzle.json --format puz --output puzzle.puz
crossword export puzzle.json --format html --output puzzle.html
crossword export puzzle.json --format pdf --output puzzle.pdf

# Interactive mode
crossword interactive puzzle.json
```

---

## Performance Targets

| Grid Size | Fill Time | Status |
|-----------|-----------|--------|
| 11×11 | <30 seconds | ⏸️ TBD |
| 15×15 | <5 minutes | ⏸️ TBD |
| 21×21 | <30 minutes | ⏸️ TBD |

---

## Status

**⏸️ Ready for implementation after Phase 1 complete**

See `03-implementation-prompts.md` for step-by-step execution guide.
