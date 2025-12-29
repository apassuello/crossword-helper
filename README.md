# Crossword Construction Helper

[![Tests & Coverage](https://github.com/apassuello/crossword-helper/actions/workflows/test.yml/badge.svg)](https://github.com/apassuello/crossword-helper/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/apassuello/crossword-helper/branch/main/graph/badge.svg)](https://codecov.io/gh/apassuello/crossword-helper)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive crossword puzzle construction toolkit with web interface and powerful CLI tools.

**Current Status:** ✅ **Phase 3 Complete** - Full System Operational with Comprehensive Documentation

---

## 📚 New Here? Start With The Reading List
**→ [READING_LIST.md](READING_LIST.md)** - Choose your path and read only what you need

---

## 🚀 Getting Started - Choose Your Path

### New to Crossword Construction?
**→ Start Here**: [USER_GUIDE_COMPLETE_WORKFLOW.md](USER_GUIDE_COMPLETE_WORKFLOW.md)

This guide walks you through the COMPLETE process:
- Starting with grid size (15x15, 21x21) + theme words
- Step-by-step to a finished, filled puzzle
- Two approaches: **Web Interface** (recommended for themes) or **CLI Only**
- Actual tested commands with expected results

### Want to See Proof It Works?
**→ Check**:
- **[COMPLETE_TESTING_REPORT.md](COMPLETE_TESTING_REPORT.md)** - Comprehensive testing of both 15×15 and 21×21
- [ACTUAL_DEMONSTRATION_RESULTS.md](ACTUAL_DEMONSTRATION_RESULTS.md) - 15×15 grid with custom wordlists
- [ACTUAL_DEMONSTRATION_21X21.md](ACTUAL_DEMONSTRATION_21X21.md) - 21×21 grid complete workflow

Real terminal output showing:
- ✅ Custom wordlist integration (VERIFIED with 18 custom words)
- ✅ Multiple wordlist support (VERIFIED with 44,032 words)
- ✅ Complete 15×15 and 21×21 workflows (TESTED with real output)
- ✅ Performance testing (0.01s for 15×15, 0.02s for 21×21)
- ❌ What's broken and why (HONEST assessment with workarounds)

### Need Quick Reference?
**→ See**: Quick Start section below

---

## Features

### Grid Editor
- Interactive crossword grid editing
- Keyboard shortcuts for fast entry
- Symmetry enforcement
- Auto-numbering
- Theme entry locking (preserve specific words during autofill)
- Import/Export grids (JSON format)

### Pattern Matcher
- Find words matching patterns (e.g., `C?T` → CAT, COT, CUT)
- Two algorithms: Regex (stable) and Trie (10-50x faster)
- Multiple wordlist support
- OneLook API integration
- Score-based ranking

### Autofill Engine
- Constraint Satisfaction with backtracking
- Beam Search for global optimization
- Iterative Repair for partial solutions
- Theme entry preservation
- Real-time progress tracking
- Cancellable operations
- Supports grids from 3×3 to 50×50

### Wordlist Management
- Browse 454k+ words across multiple categories
- Upload custom wordlists (.txt files)
- View statistics and distributions
- Add words to existing lists
- Curated collections (crosswordese, expressions, etc.)

---

## Quick Start

### Prerequisites

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies (for frontend)
npm install
```

### Run the Application

**Option 1: Production Mode (Recommended)**
```bash
# Build the frontend once
npm run build

# Run Flask server
python3 run.py

# Open browser → http://localhost:5000
```

**Option 2: Development Mode (Hot Reload)**
```bash
# Terminal 1: Run Flask backend
python3 run.py

# Terminal 2: Run Vite dev server
npm run dev

# Open browser → http://localhost:3000
# (Frontend will auto-reload on changes)
```

**Note**: In development mode, the Vite dev server (port 3000) proxies API requests to Flask (port 5000) automatically.

### Create Your First Puzzle

#### For Puzzles WITH Theme Words (Recommended: Web Interface)
1. **Start backend**: `python run.py` → `http://localhost:5000`
2. **Create grid**: Select size, create new grid
3. **Add theme words**: Type them into specific positions
4. **Lock theme words**: Mark them to preserve during autofill
5. **Add black squares**: Use optimizer or click manually
6. **Autofill**: Configure and run (theme words preserved)
7. **Export**: Download as PDF or .puz

#### For Puzzles WITHOUT Theme Words (CLI Works Great)
```bash
# 1. Create grid
python -m cli.src.cli new --size 15 -o puzzle.json

# 2. Add black squares (manual JSON editing or script)

# 3. Validate
python -m cli.src.cli validate puzzle.json

# 4. Fill
python -m cli.src.cli fill puzzle.json \
  -w data/wordlists/comprehensive.txt \
  -t 180 --min-score 30 -o filled.json

# 5. Export
python -m cli.src.cli export filled.json --format pdf -o puzzle.pdf
```

---

## ⚠️ Reality Check: What Actually Works

Based on comprehensive testing (see [ACTUAL_DEMONSTRATION_RESULTS.md](ACTUAL_DEMONSTRATION_RESULTS.md)):

### ✅ Fully Working Features
- ✅ **Custom wordlists** - Create and use your own word lists
- ✅ **Multiple wordlists** - Combine comprehensive + custom + themed lists
- ✅ **Pattern matching** - Find words by pattern (C?T → CAT, COT, CUT)
- ✅ **Grid validation** - Check symmetry, connectivity, NYT standards
- ✅ **Autofill (no themes)** - Fill entire grids with quality words
- ✅ **Pause/resume** - Pause long-running fills, resume later
- ✅ **Export** - PDF, .puz, JSON formats all work
- ✅ **Web interface** - All features work including theme preservation

### ⚠️ Known Issues
- ❌ **CLI `--theme-entries` flag** - Does NOT preserve theme words
  - **Workaround**: Use web interface for themed puzzles
- ❌ **CLI `--adaptive` flag** - Does NOT auto-add black squares
  - **Workaround**: Use web interface black square optimizer

**Bottom Line**: Web interface works perfectly. CLI works great for non-themed puzzles. For themed puzzles, use the web interface.

---

## Project Structure

```
crossword-helper/
├── backend/                # Flask backend (Python)
│   ├── api/                # API routes and validation
│   ├── core/               # CLI adapter (single source of truth)
│   ├── data/               # Wordlist management
│   └── app.py              # Flask application
│
├── cli/                    # Command-line interface (Python)
│   └── src/
│       ├── cli.py          # CLI entry point
│       ├── core/           # Grid, numbering, validation
│       └── fill/           # Autofill algorithms
│
├── src/                    # React frontend
│   ├── components/         # React components
│   │   ├── GridEditor.jsx
│   │   ├── AutofillPanel.jsx
│   │   ├── WordListPanel.jsx
│   │   └── ...
│   └── styles/             # SCSS styles
│
├── data/wordlists/         # Wordlist files (454k+ words)
│   ├── comprehensive.txt
│   ├── core/               # Core wordlists
│   └── themed/             # Themed wordlists
│
├── docs/                   # Documentation
│   ├── README.md           # Documentation navigation
│   ├── ARCHITECTURE.md     # System architecture
│   ├── specs/              # Component specifications
│   ├── api/                # API documentation
│   ├── ops/                # Operational guides
│   ├── dev/                # Developer guides
│   └── archive/            # Historical documentation
│
└── tests/                  # Test suites
    ├── backend/            # Backend tests (37/37 passing)
    └── cli/                # CLI tests
```

---

## Documentation

### Getting Started
- **[Quick Start](#quick-start)** - Get running in 5 minutes
- **[docs/README.md](docs/README.md)** - Complete documentation navigation
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture

### Documentation Structure
- **[Component Specs](docs/specs/)** - CLI, Backend, Frontend specifications
- **[API Reference](docs/api/API_REFERENCE.md)** - Complete API documentation
- **[Testing Guide](docs/ops/TESTING.md)** - Testing strategies and examples
- **[Development Guide](docs/dev/DEVELOPMENT.md)** - Developer onboarding

### Implementation History
- **[ROADMAP.md](docs/ROADMAP.md)** - Development roadmap and timeline
- **[Archive](docs/archive/)** - Historical documentation and progress reports

---

## Technology Stack

**Backend:**
- Flask 3.0+ (Python web framework)
- Click (CLI framework)
- NumPy (grid algorithms)
- pytest (testing)

**Frontend:**
- React 18 (UI framework)
- Vite 5 (build tool & dev server)
- SCSS (styling with Sass)
- Axios (HTTP client)
- Server-Sent Events (real-time progress)

**Data:**
- 454k+ word comprehensive wordlist
- Curated specialty lists (crosswordese, expressions, foreign words)
- JSON-based grid format

---

## Testing

### Backend Tests
```bash
python3 -m pytest backend/tests/ -v
```
**Status:** ✅ 165/165 tests passing (100%)

### Full Test Suite
```bash
# All tests (backend + CLI)
python3 -m pytest -v
```
**Status:** ✅ 165/165 tests passing across backend and CLI

---

## Features in Detail

### Grid Editor

**Keyboard Shortcuts:**
- `A-Z` - Enter letter
- `Arrow Keys` - Navigate cells
- `Space` or `.` - Toggle black square
- `Backspace` - Clear and move back
- `Tab` - Jump to next word
- `Ctrl/Cmd+L` - Toggle theme lock

**Mouse Actions:**
- `Click` - Select cell
- `Shift+Click` - Toggle black square
- `Right-click` - Toggle theme lock

### Autofill Options

**Algorithms:**
- **Regex** (Classic) - Stable, well-tested
- **Trie** (Fast) - 10-50x faster for large wordlists

**Wordlists:**
- Comprehensive (454k words)
- 3-letter words
- Crosswordese
- Expressions & Slang
- Foreign classics (ES/FR)
- Custom uploads

**Settings:**
- Minimum word score (0-100)
- Timeout (1-10 minutes)
- Theme entry preservation

### Import/Export

**Grid Format (JSON):**
```json
{
  "size": 15,
  "grid": [
    ["H", "E", "L", "L", "O", ...],
    ["#", ".", ".", ".", ".", ...],
    ...
  ]
}
```

**Features:**
- Preserves theme locks
- Auto-numbering on import
- Validation on load

---

## Development Timeline

### ✅ Completed Phases

**Phase 1: Web Application** (December 2025)
- Basic Flask backend with 3 helper tools
- Pattern matching, grid numbering, convention normalization

**Phase 2: CLI Tool** (Earlier 2025)
- Comprehensive command-line interface
- CSP-based autofill with beam search + iterative repair

**Phase 3: Integration** (December 2025)
- Web app refactored to use CLI backend
- Single source of truth architecture

**Web Interface Enhancements** (December 2025)
- ✅ Grid import/export functionality
- ✅ Theme entry locking
- ✅ Wordlist upload UI
- ✅ Autofill cancel functionality
- ✅ Backend test fixes (165/165 passing)

**Documentation Consolidation** (December 27, 2025)
- ✅ Comprehensive architecture documentation
- ✅ Complete API reference (26 endpoints)
- ✅ Component specifications (CLI, Backend, Frontend)
- ✅ Testing and development guides
- ✅ Archived 87 historical documents

### 📋 Current Status

All 3 phases complete with comprehensive documentation. System ready for production use and future enhancements.

---

## Contributing

### Code Style
- Python: Follow PEP 8
- JavaScript: ESLint configuration
- React: Functional components with hooks
- Testing: pytest (backend), Jest (frontend)

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and test
pytest tests/
npm test

# Commit with descriptive message
git commit -m "Add: feature description"

# Push and create PR
git push origin feature/my-feature
```

---

## Known Issues & Limitations

### Current Limitations
- Frontend tests not yet implemented (Phase 5)
- No authentication/multi-user support
- Local-only deployment (no cloud hosting yet)

### Browser Support
- ✅ Chrome/Edge (tested)
- ✅ Firefox (tested)
- ✅ Safari (tested)
- ⚠️ IE11 (not supported)

---

## Performance

### Autofill Speed (Trie algorithm)
- 11×11 grid: < 30 seconds (typical)
- 15×15 grid: < 5 minutes (typical)
- 21×21 grid: < 30 minutes (typical)

**Factors affecting speed:**
- Grid constraints (more prefilled = faster)
- Wordlist size
- Minimum score threshold
- Theme entries (slightly slower)

### Wordlist Statistics
- Total words: 454,378
- Average word length: 8.2 letters
- Shortest: 3 letters
- Longest: 21 letters

---

## License

[Your License Here]

---

## Support

- **Documentation:** See [docs/README.md](docs/README.md)
- **Issues:** Check existing documentation first
- **Setup Problems:** See [DEPLOYMENT.md](DEPLOYMENT.md)

---

## Acknowledgments

- Wordlist sources: Various open crossword wordlists
- Algorithm research: CSP techniques for crossword construction
- Community feedback and testing

---

**Built with ❤️ for crossword constructors**

**Version:** 2.0.0
**Last Updated:** December 27, 2025
