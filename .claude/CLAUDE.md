# Crossword Construction Helper - Claude Code Guide

**Project Type:** Progressive enhancement crossword toolkit
**Current Phase:** Documentation complete, ready for Phase 1 implementation
**Total Timeline:** 5-6 weeks across 3 phases

---

## Project Overview

Building a comprehensive crossword construction system in three progressive phases:

### Phase 1: Web Application (3-5 days) - CURRENT
Simple Flask web app with 3 helper tools for immediate value.

### Phase 2: CLI Tool (3-4 weeks)
Comprehensive command-line tool with CSP-based autofill (main feature).

### Phase 3: Integration (1 week)
Refactor web app to use CLI backend for shared implementation + autofill in web UI.

**See:** `docs/ROADMAP.md` for complete development plan

---

## Quick Reference

### Technology Stack

**Phase 1 (Web App):**
- Backend: Flask 3.0+, Python 3.9+
- Frontend: Vanilla HTML/CSS/JavaScript
- Data: File-based wordlists
- Testing: pytest

**Phase 2 (CLI Tool):**
- Language: Python 3.9+
- CLI: Click + Rich
- Algorithms: NumPy
- Export: reportlab, pypuz
- Data: JSON, SQLite

**Phase 3 (Integration):**
- Refactored Phase 1 calling Phase 2 as subprocess
- Single codebase for all logic

### Build Commands

```bash
# Phase 1: Web App
pip install -r requirements.txt
python run.py                  # → http://localhost:5000

# Testing
pytest                         # All tests
pytest --cov=backend          # With coverage
pytest tests/unit/ -v         # Unit tests only

# Phase 2: CLI Tool (not yet implemented)
crossword new --size 15
crossword fill puzzle.json
crossword export puzzle.json --format pdf
```

---

## Documentation Structure

```
docs/
├── ROADMAP.md                      # Master development plan
├── phase1-webapp/
│   ├── README.md                   # Phase 1 overview
│   ├── 01-architecture.md          # System design
│   ├── 02-api-specification.md     # API contracts
│   ├── 03-implementation-guide.md  # Implementation details
│   └── 04-implementation-prompts.md # Step-by-step execution
├── phase2-cli/
│   ├── README.md                   # Phase 2 overview
│   ├── 01-architecture.md          # CLI architecture
│   ├── 02-specifications.md        # Detailed specs
│   └── 03-implementation-prompts.md # Step-by-step execution
├── phase3-integration/
│   └── README.md                   # Phase 3 overview
└── guides/
    ├── claude-ai-setup.md          # Claude.ai project setup
    ├── README-claude-code.md       # Claude Code guide
    └── custom-instructions-claude-ai.md # AI custom instructions
```

---

## File Structure

```
crossword-helper/
├── backend/                    # Phase 1 backend
│   ├── app.py                  # Flask application
│   ├── core/                   # Business logic (pure functions)
│   │   ├── pattern_matcher.py # Pattern search + scoring
│   │   ├── numbering.py        # Grid numbering logic
│   │   ├── conventions.py      # Entry normalization
│   │   └── scoring.py          # Word scoring algorithms
│   ├── api/                    # API layer (thin wrappers)
│   │   ├── routes.py           # Endpoint definitions
│   │   ├── validators.py       # Request validation
│   │   └── errors.py           # Error handling
│   └── data/                   # Data access layer
│       ├── onelook_client.py   # OneLook API client
│       └── wordlist_manager.py # Wordlist file management
├── frontend/                   # Phase 1 frontend
│   ├── static/
│   │   ├── css/main.css        # Styles (mobile-first)
│   │   └── js/                 # Frontend logic
│   │       ├── app.js          # Main application
│   │       ├── pattern.js      # Pattern matcher UI
│   │       ├── numbering.js    # Numbering validator UI
│   │       └── conventions.js  # Convention helper UI
│   └── templates/
│       └── index.html          # Single page app
├── data/
│   └── wordlists/              # Word list files
│       ├── standard.txt        # Common crossword fill
│       └── personal.txt        # Custom words
├── tests/
│   ├── unit/                   # Fast, isolated tests
│   ├── integration/            # API endpoint tests
│   └── fixtures/               # Test data
├── docs/                       # All documentation
├── .claude/                    # Claude Code config
│   ├── CLAUDE.md               # This file
│   └── commands/               # Custom commands
├── run.py                      # Development server launcher
├── requirements.txt            # Python dependencies
└── pytest.ini                  # Test configuration
```

---

## Development Workflow

### For Phase 1 Implementation

**Step 1: Understand the Design**
```bash
# Read in this order:
docs/phase1-webapp/01-architecture.md      # Understand "what" and "why"
docs/phase1-webapp/02-api-specification.md # Know exact API contracts
docs/phase1-webapp/03-implementation-guide.md # See code patterns
```

**Step 2: Execute Implementation**
```bash
# Follow step-by-step:
docs/phase1-webapp/04-implementation-prompts.md
```

The prompts guide you through:
1. Backend core (services layer) - 2-3 hours
2. API layer (Flask routes) - 1-2 hours
3. Frontend (HTML/CSS/JS) - 2-3 hours
4. Testing & polish - 1-2 hours

**Step 3: Test Thoroughly**
```bash
pytest tests/                    # All tests pass
pytest --cov=backend            # >85% coverage
python run.py                    # Manual testing
# Test in browser at localhost:5000
# Test mobile view (360px width)
```

**Step 4: Validate Success**
- [ ] All 3 tools functional in browser
- [ ] Tests pass with >85% coverage
- [ ] Response times meet targets
- [ ] Mobile responsive
- [ ] Error handling works

### For Phase 2 Implementation

Will begin after Phase 1 is complete. See `docs/phase2-cli/03-implementation-prompts.md` for detailed execution guide (10 sequential prompts).

### For Phase 3 Implementation

Will begin after Phase 2 is complete. Documentation will be created after Phase 2.

---

## Architecture Principles

### Phase 1 Architecture

**Three Layers:**
```
API Layer (routes.py)
    ↓ delegates to
Service Layer (core/*.py)
    ↓ uses
Data Layer (data/*.py)
```

**Why Layered:**
- Service layer = pure logic (testable in isolation)
- API layer = thin HTTP wrapper (< 20 lines per endpoint)
- Data layer = external integrations (OneLook, files)

**Key Decisions:**
- **Flask over FastAPI:** Simpler for synchronous I/O-bound work
- **Vanilla JS over React:** Only 3 components, no build step needed
- **File-based over DB:** Local tool, no server required
- **Thin API layer:** Enables CLI reuse in Phase 3

### Phase 2 Architecture

**Core Algorithm: CSP with Backtracking**
```
1. Find empty cell with minimum remaining values (MRV)
2. Get candidate words sorted by value (LCV)
3. Try word, check constraints (arc consistency)
4. If valid → recurse
5. If invalid → backtrack
```

**Performance Targets:**
- 11×11: <30 seconds
- 15×15: <5 minutes
- 21×21: <30 minutes

### Phase 3 Architecture

**Integration Strategy:**
- Web app routes call CLI tool via subprocess
- Keep API contracts identical (backward compatible)
- Add new `/api/fill` endpoint for autofill
- Use caching to minimize subprocess overhead

---

## Testing Strategy

### Unit Tests (`tests/unit/`)
- Test each method independently
- Mock external dependencies (OneLook API, file I/O)
- Fast (<1s for entire suite)
- **Target:** >90% coverage of service layer

### Integration Tests (`tests/integration/`)
- Test API endpoints end-to-end
- Use test client (Flask test fixture)
- Include error scenarios
- **Target:** >80% coverage of API layer

### Manual Testing
- Browser testing (all features work)
- Mobile testing (360px width)
- Error handling (invalid input, timeouts)
- Performance (response times meet targets)

**Test-Driven Development:**
- Write tests alongside code
- Run tests after each change
- Don't proceed until tests pass

---

## API Contracts (Phase 1)

### Pattern Search
```bash
POST /api/pattern
{"pattern": "?I?A", "wordlists": ["personal", "standard"]}

→ 200 OK
{
  "results": [{"word": "VISA", "score": 85, "source": "onelook"}],
  "meta": {"total_found": 127, "query_time_ms": 245}
}
```

### Grid Numbering
```bash
POST /api/number
{"grid": [["R","A","S",...], ...]}

→ 200 OK
{
  "numbering": {"(0,0)": 1, "(0,5)": 2},
  "validation": {"is_valid": true, "errors": []},
  "grid_info": {"size": [15,15], "word_count": 76}
}
```

### Convention Normalization
```bash
POST /api/normalize
{"text": "Tina Fey"}

→ 200 OK
{
  "normalized": "TINAFEY",
  "rule": {"type": "two_word_names", "description": "..."},
  "examples": [["Tracy Jordan", "TRACYJORDAN"]]
}
```

---

## Key Patterns & Anti-Patterns

### ✅ Good: Service Layer (Pure Logic)
```python
class PatternMatcher:
    def search(self, pattern: str, wordlists: List[str]) -> List[Tuple[str, int]]:
        """Pure business logic, no HTTP concerns."""
        api_results = self._search_onelook(pattern)
        local_results = self._search_local(pattern, wordlists)
        return self._merge_and_score(api_results, local_results)
```

### ✅ Good: API Layer (Thin Wrapper)
```python
@app.route('/api/pattern', methods=['POST'])
def pattern_search():
    data = request.json
    if not data.get('pattern'):
        return jsonify({'error': 'Pattern required'}), 400

    results = pattern_matcher.search(
        pattern=data['pattern'],
        wordlists=data.get('wordlists', ['standard'])
    )
    return jsonify({'results': results})
```

### ❌ Bad: Logic in Routes
```python
@app.route('/api/pattern')
def pattern_search():
    # ❌ BAD: Business logic in route
    pattern = request.json['pattern']
    url = f"https://api.onelook.com/words?sp={pattern}"
    response = requests.get(url)
    # ... processing ...
    return jsonify(results)
```

### ✅ Good: Error Handling
```python
try:
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    data = response.json()
except (requests.Timeout, requests.RequestException) as e:
    logger.warning(f"OneLook API failed: {e}")
    # Fallback to local word lists
    data = []
```

---

## Performance Considerations

### Phase 1 Targets
| Endpoint | Target | Why |
|----------|--------|-----|
| POST /api/pattern | <1s | OneLook API + local search |
| POST /api/number | <100ms | Pure computation, small grids |
| POST /api/normalize | <50ms | Simple string operations |

### Optimization Strategies
1. **OneLook API:** Timeout after 5s, fallback to local
2. **Local search:** Pre-load wordlists on startup (cache)
3. **Grid numbering:** O(n) scan, very fast
4. **Convention detection:** Regex patterns, pre-compiled

---

## Common Issues & Solutions

### Issue: OneLook API Timeout
**Solution:** Automatic fallback to local wordlists. User sees results from local sources only.

### Issue: CORS Errors
**Solution:** Flask-CORS configured for localhost. No action needed.

### Issue: Pattern Returns No Results
**Solution:** UI suggests broadening pattern (more `?` wildcards).

### Issue: Mobile Layout Broken
**Solution:** Use mobile-first CSS with media queries. Test at 360px.

### Issue: Tests Fail After Changes
**Solution:** Run `pytest -vv` for detailed output. Fix issues before proceeding.

---

## Integration with Claude.ai

**Tool Separation:**
- **Claude.ai Project:** Strategy, themes, clue writing (creative work)
- **Claude Code:** Implementation, algorithms, testing (technical work)

**See:** `docs/guides/claude-ai-setup.md` for Claude.ai project configuration

**Workflow:**
1. Brainstorm themes → Claude.ai
2. Build grid/tools → Claude Code (this project)
3. Write clues → Claude.ai
4. Export → This project (Phase 2)

---

## Debugging

### Backend Issues
```bash
# Run with debug mode
FLASK_DEBUG=1 python run.py

# Run specific test with verbose output
pytest tests/unit/test_pattern_matcher.py::test_name -vv -s

# Check for syntax errors
python -m py_compile backend/core/pattern_matcher.py
```

### Frontend Issues
- Open browser DevTools (F12)
- Check Network tab (API calls succeeding?)
- Check Console tab (JavaScript errors?)
- Check Response tab (JSON valid?)

### Common Fixes
- OneLook timeout: Check internet, verify fallback works
- Grid numbering wrong: Test with simple 3×3 grid first
- CORS errors: Verify Flask-CORS installed and configured

---

## Implementation Checklist

### Before Starting Phase 1:
- [ ] Read `docs/ROADMAP.md` (understand big picture)
- [ ] Read `docs/phase1-webapp/README.md` (understand phase)
- [ ] Read architecture docs (01 → 02 → 03)
- [ ] Review implementation prompts (04)

### During Phase 1:
- [ ] Follow prompts sequentially
- [ ] Test after each step
- [ ] Don't proceed until tests pass
- [ ] Commit regularly

### After Phase 1:
- [ ] All success criteria met
- [ ] Manual testing complete
- [ ] Documentation updated
- [ ] Ready for Phase 2

---

## Git Workflow

```bash
# Feature branches
git checkout -b feature/pattern-matcher
git commit -m "Implement pattern matcher service"
git push origin feature/pattern-matcher

# Testing before commit
pytest tests/                    # All tests pass
pytest --cov=backend            # Coverage acceptable

# Commit messages
# Good: "Add pattern matcher with OneLook integration"
# Good: "Fix numbering validation for edge cases"
# Bad: "Update stuff"
# Bad: "WIP"
```

---

## Help & Resources

### For Implementation Questions:
1. Check relevant phase README
2. Review architecture document
3. Search implementation guide
4. Check analysis docs (`docs/CONSISTENCY_ANALYSIS.md`)

### For Architecture Questions:
1. See `docs/ROADMAP.md` for high-level plan
2. See phase-specific `01-architecture.md` for detailed design
3. See API spec for exact contracts

### For Testing Questions:
1. Check `pytest.ini` for configuration
2. See `tests/conftest.py` for shared fixtures
3. Review existing test examples

---

## Status & Next Steps

**Current Status:** 📋 Documentation complete, ready for Phase 1

**Next Milestone:** Implement Phase 1 (3-5 days)

**How to Proceed:**
1. Read Phase 1 documentation (01 → 02 → 03 → 04)
2. Execute implementation prompts
3. Test thoroughly
4. Validate success criteria
5. Move to Phase 2

---

## Success Metrics

### Phase 1 Success:
- ✅ All 3 tools work in browser
- ✅ Tests pass (>85% coverage)
- ✅ Performance targets met
- ✅ Mobile responsive
- ✅ Error handling robust

### Phase 2 Success:
- ✅ CLI commands functional
- ✅ Autofill meets performance targets
- ✅ Export formats work correctly
- ✅ Tests pass (>90% coverage)

### Phase 3 Success:
- ✅ Integration complete
- ✅ No regressions
- ✅ Autofill in web UI
- ✅ Single codebase maintained

---

**Last Updated:** Documentation reorganization complete
**Version:** 0.1.0-pre (pre-implementation)
