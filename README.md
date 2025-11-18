# Crossword Construction Helper

A comprehensive crossword puzzle construction toolkit being built in three progressive phases.

**Current Status:** 📋 Documentation complete, ready for Phase 1 implementation

---

## Project Vision

Build a powerful crossword construction system through progressive enhancement:
1. **Phase 1 (3-5 days):** Simple web app with 3 helper tools → Fast value
2. **Phase 2 (3-4 weeks):** Comprehensive CLI with autofill → Powerful features
3. **Phase 3 (1 week):** Integrate web + CLI → Best of both worlds

**Total Timeline:** 5-6 weeks

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for complete development plan.

---

## Quick Start

### Phase 1: Web Application (Current)

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python run.py

# Open browser
# → http://localhost:5000
```

**Features Available:**
- Pattern Matching (find words matching `?I?A` patterns)
- Grid Numbering (auto-number crossword grids)
- Convention Normalization (normalize "Tina Fey" → "TINAFEY")

---

## Documentation

### Master Plan
- **[`docs/ROADMAP.md`](docs/ROADMAP.md)** - Complete 3-phase development plan

### Phase 1: Web Application
- [`docs/phase1-webapp/README.md`](docs/phase1-webapp/README.md) - Phase 1 overview
- [`docs/phase1-webapp/01-architecture.md`](docs/phase1-webapp/01-architecture.md) - System design
- [`docs/phase1-webapp/02-api-specification.md`](docs/phase1-webapp/02-api-specification.md) - API contracts
- [`docs/phase1-webapp/03-implementation-guide.md`](docs/phase1-webapp/03-implementation-guide.md) - Implementation details
- [`docs/phase1-webapp/04-implementation-prompts.md`](docs/phase1-webapp/04-implementation-prompts.md) - Step-by-step execution

### Phase 2: CLI Tool
- [`docs/phase2-cli/README.md`](docs/phase2-cli/README.md) - Phase 2 overview
- [`docs/phase2-cli/01-architecture.md`](docs/phase2-cli/01-architecture.md) - CLI architecture
- [`docs/phase2-cli/02-specifications.md`](docs/phase2-cli/02-specifications.md) - Detailed specs
- [`docs/phase2-cli/03-implementation-prompts.md`](docs/phase2-cli/03-implementation-prompts.md) - Step-by-step execution

### Phase 3: Integration
- [`docs/phase3-integration/README.md`](docs/phase3-integration/README.md) - Phase 3 overview
- *(Additional docs will be created after Phase 2)*

### Guides
- [`docs/guides/claude-ai-setup.md`](docs/guides/claude-ai-setup.md) - Claude.ai project setup
- [`.claude/CLAUDE.md`](.claude/CLAUDE.md) - Claude Code configuration

---

## Project Structure

```
crossword-helper/
├── backend/              # Backend Python code (Phase 1)
│   ├── core/            # Core business logic
│   ├── api/             # REST API routes
│   └── data/            # Data access layer
├── frontend/            # Frontend assets (Phase 1)
│   ├── static/          # CSS and JavaScript
│   └── templates/       # HTML templates
├── tests/               # Test suite
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── data/                # Wordlist data files
│   └── wordlists/      # Word lists for pattern matching
├── docs/                # Documentation
│   ├── ROADMAP.md      # Master development plan
│   ├── phase1-webapp/  # Phase 1 documentation
│   ├── phase2-cli/     # Phase 2 documentation
│   ├── phase3-integration/ # Phase 3 documentation
│   └── guides/         # General guides
└── .claude/            # Claude Code configuration
    ├── CLAUDE.md       # Project overview for AI assistants
    └── commands/       # Custom commands
```

---

## Development Workflow

### Phase 1 Implementation (3-5 days)

**Step 1:** Read documentation
```bash
# Read in this order:
docs/phase1-webapp/01-architecture.md
docs/phase1-webapp/02-api-specification.md
docs/phase1-webapp/03-implementation-guide.md
```

**Step 2:** Execute implementation prompts
```bash
# Follow step-by-step:
docs/phase1-webapp/04-implementation-prompts.md
```

**Step 3:** Test
```bash
pytest tests/              # Run all tests
pytest --cov=backend       # With coverage
python run.py              # Manual testing
```

### Phase 2 Implementation (3-4 weeks)

Will begin after Phase 1 is complete and stable.

See `docs/phase2-cli/README.md` for details.

### Phase 3 Implementation (1 week)

Will begin after Phase 2 is complete.

See `docs/phase3-integration/README.md` for details.

---

## Technology Stack

### Phase 1: Web Application
- **Backend:** Flask 3.0+ (Python 3.9+)
- **Frontend:** Vanilla HTML/CSS/JavaScript
- **Data:** File-based wordlists
- **Testing:** pytest

### Phase 2: CLI Tool
- **Language:** Python 3.9+
- **CLI Framework:** Click + Rich
- **Algorithms:** NumPy for grid operations
- **Export:** reportlab (PDF), pypuz (.puz)
- **Data:** JSON files, SQLite for clues

### Phase 3: Integration
- Uses Phase 1 + Phase 2 codebases
- Web app calls CLI tool as backend
- Adds autofill feature to web UI

---

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/unit/test_pattern_matcher.py -v

# Run specific test
pytest tests/unit/test_pattern_matcher.py::test_simple_pattern -v
```

### Running
```bash
# Development server (Phase 1)
python run.py

# CLI tool (Phase 2 - not yet implemented)
crossword new --size 15
crossword fill puzzle.json
crossword export puzzle.json --format pdf
```

### Code Quality
```bash
# Lint code (Phase 2)
pylint backend/

# Format code (Phase 2)
black backend/

# Type checking (Phase 2)
mypy backend/
```

---

## Features by Phase

### Phase 1: Web App ✅ Documented
- ✅ Pattern Matching (OneLook API + local wordlists)
- ✅ Grid Numbering (auto-number and validation)
- ✅ Convention Normalization (multi-word entry handling)

### Phase 2: CLI Tool ✅ Documented
- ⏸️ Grid Engine (create, validate grids)
- ⏸️ **Autofill Engine** (CSP with backtracking) ← Main feature
- ⏸️ Pattern Matcher (enhanced with scoring)
- ⏸️ Clue Manager (local database)
- ⏸️ Export Engine (HTML, PDF, .puz)

### Phase 3: Integration ✅ Documented
- ⏸️ Web app uses CLI backend
- ⏸️ Autofill available in web UI
- ⏸️ Single codebase for all logic
- ⏸️ Improved maintainability

---

## Performance Targets

### Phase 1 Targets
| Operation | Target | Status |
|-----------|--------|--------|
| Pattern search | <1s | ⏸️ TBD |
| Grid numbering | <100ms | ⏸️ TBD |
| Normalization | <50ms | ⏸️ TBD |

### Phase 2 Targets
| Operation | Target | Status |
|-----------|--------|--------|
| 11×11 autofill | <30s | ⏸️ TBD |
| 15×15 autofill | <5min | ⏸️ TBD |
| 21×21 autofill | <30min | ⏸️ TBD |

---

## Integration with Crosshare

This tool complements [Crosshare.org](https://crosshare.org):

1. **Theme/words** → Claude.ai Project (brainstorming)
2. **Pattern matching** → This tool (Phase 1)
3. **Grid editing** → Crosshare.org (visual editor)
4. **Autofill** → This tool (Phase 2)
5. **Validation** → This tool (Phase 1)
6. **Clues** → Claude.ai Project (creative writing)
7. **Export** → Crosshare or This tool (Phase 2)

**Key Insight:** This tool doesn't replace Crosshare, it assists while using it.

---

## Status & Next Steps

**Current Status:** 📋 All documentation complete

**Next Milestone:** Begin Phase 1 implementation

**How to Start:**
1. Read [`docs/phase1-webapp/README.md`](docs/phase1-webapp/README.md)
2. Follow documentation in order (01 → 02 → 03 → 04)
3. Execute implementation prompts
4. Test thoroughly
5. Move to Phase 2

---

## Questions & Support

**For implementation questions:**
- Read relevant phase documentation
- Check troubleshooting guide (will be populated during implementation)
- Review analysis documents in `docs/` (CONSISTENCY_ANALYSIS.md, etc.)

**For architecture questions:**
- See [`docs/ROADMAP.md`](docs/ROADMAP.md) for high-level plan
- See phase-specific `01-architecture.md` files for detailed design

---

## Contributing

This is a personal project under active development. Contributions are not currently accepted, but you're welcome to fork and adapt for your own use.

---

## License

TBD

---

**Last Updated:** Documentation reorganization complete (2024)
**Version:** 0.1.0-pre (pre-implementation)
