# Phase 1: Web Application

**Goal:** Build a simple, fast, local web app with 3 crossword helper tools

**Timeline:** 3-5 days
**Complexity:** Low
**Status:** ⏸️ Ready to implement

---

## Overview

Flask-based web application that helps with crossword construction by solving three specific pain points:

1. **Pattern Matching** - Find words that fit partial patterns (e.g., `?I?A` for 4-letter words with I as 2nd letter, A as 4th)
2. **Grid Numbering** - Automatically number crossword grids according to standard rules
3. **Convention Normalization** - Handle multi-word entries correctly (e.g., "Tina Fey" → "TINAFEY")

---

## Quick Start

```bash
cd crossword-helper
pip install -r requirements.txt
python run.py
# Opens browser at http://localhost:5000
```

---

## Documentation

| Document | Purpose | When to Read |
|----------|---------|--------------|
| `01-architecture.md` | System design, tech choices, layer responsibilities | First (understand "what" and "why") |
| `02-api-specification.md` | Complete API contracts with request/response examples | Second (know exact contracts) |
| `03-implementation-guide.md` | Class interfaces, algorithms, code patterns | Third (see "how") |
| `04-implementation-prompts.md` | Step-by-step execution script | Last (build it) |

**Recommended reading order:** 01 → 02 → 03 → 04

---

## Features

### 1. Pattern Matcher
**Problem:** Need words that fit `?I?A` (4 letters, I in position 2, A in position 4)

**Solution:**
- Search OneLook API for matches
- Search local word lists
- Score by "crossword-ability" (common letters = higher score)
- Return top 20 results sorted by score

**API:** `POST /api/pattern`

**Response Time:** <1 second

### 2. Numbering Validator
**Problem:** Manually numbering grids is tedious and error-prone

**Solution:**
- Scan grid left-to-right, top-to-bottom
- Number cells that start an across OR down word
- Validate user's numbering (if provided)
- Return correct numbering

**API:** `POST /api/number`

**Response Time:** <100ms for 15×15 grid

### 3. Convention Helper
**Problem:** Multi-word entries need special handling ("Tina Fey" vs "TINAFEY")

**Solution:**
- Identify convention type (two-word names, articles, hyphens, etc.)
- Normalize according to rules
- Explain rule with examples
- Provide alternatives if applicable

**API:** `POST /api/normalize`

**Response Time:** <50ms

---

## Architecture

### Three Layers

```
Frontend (Browser)
    ↓ HTTP/JSON
API Layer (Flask routes)
    ↓ delegates to
Service Layer (Pure Python)
    ↓ uses
Data Layer (OneLook API, Files)
```

**Why layered:**
- Service layer is pure logic (testable in isolation)
- API layer is thin HTTP wrapper
- Enables reuse (CLI can use same services later → Phase 3)

### Technology Choices

| Component | Choice | Why |
|-----------|--------|-----|
| Backend | Flask 3.0+ | Simple, synchronous (I/O-bound), no async complexity |
| Frontend | Vanilla JS | Only 3 components, no build step, faster development |
| Data | File-based | Local tool, no database overhead |
| Testing | pytest | Industry standard, excellent fixtures |

---

## Implementation Workflow

### Phase 1A: Backend Core (2-3 hours)
1. Set up Flask app structure
2. Implement PatternMatcher service
3. Implement NumberingValidator service
4. Implement ConventionHelper service
5. Unit tests for all services (>90% coverage)

**Checkpoint:** All unit tests pass

### Phase 1B: API Layer (1-2 hours)
1. Implement 3 API endpoints
2. Add request validation
3. Add error handling
4. Integration tests for all endpoints

**Checkpoint:** API returns correct responses via curl

### Phase 1C: Frontend (2-3 hours)
1. Build HTML structure
2. Add CSS styling (mobile-first)
3. Implement JavaScript for each tool
4. Connect to API endpoints

**Checkpoint:** All 3 tools work in browser

### Phase 1D: Polish & Test (1-2 hours)
1. Test on mobile (360px width)
2. Test error scenarios
3. Test OneLook timeout fallback
4. Fix any bugs
5. Final integration test

**Checkpoint:** Ready for use

---

## Success Criteria

Before considering Phase 1 complete, verify:

- [ ] **Functionality:** All 3 tools work correctly in browser
- [ ] **Testing:** Test coverage >85% for backend
- [ ] **Performance:** Pattern search <1s, Numbering <100ms, Normalize <50ms
- [ ] **Responsive:** Works at 360px width (mobile)
- [ ] **Error Handling:** OneLook timeout handled gracefully
- [ ] **Code Quality:** No console errors, clean code
- [ ] **Documentation:** README updated with setup instructions

---

## Testing Strategy

### Unit Tests (`tests/unit/`)
Test each service method in isolation:
- PatternMatcher: pattern parsing, OneLook integration, local search, scoring
- NumberingValidator: grid scanning, numbering logic, validation
- ConventionHelper: rule detection, normalization, examples

**Target:** >90% coverage of service layer

### Integration Tests (`tests/integration/`)
Test API endpoints end-to-end:
- POST /api/pattern with various patterns
- POST /api/number with different grids
- POST /api/normalize with different text

**Target:** >80% coverage of API layer

### Manual Testing
Browser testing checklist:
- Each tool works with valid input
- Each tool shows errors with invalid input
- Mobile layout works
- Loading states display correctly
- Results render properly

---

## File Structure

```
backend/
├── app.py                  # Flask app factory
├── core/                   # Business logic
│   ├── pattern_matcher.py # Pattern matching + scoring
│   ├── numbering.py        # Grid numbering logic
│   ├── conventions.py      # Entry normalization
│   └── scoring.py          # Word scoring algorithms
├── api/                    # API layer
│   ├── routes.py           # Endpoint definitions
│   ├── validators.py       # Request validation
│   └── errors.py           # Error handling
└── data/                   # Data access
    ├── onelook_client.py   # OneLook API client
    └── wordlist_manager.py # File-based wordlist loading

frontend/
├── static/
│   ├── css/main.css        # All styles (mobile-first)
│   └── js/
│       ├── app.js          # Main application logic
│       ├── pattern.js      # Pattern matcher UI
│       ├── numbering.js    # Numbering validator UI
│       └── conventions.js  # Convention helper UI
└── templates/
    └── index.html          # Single page application

tests/
├── unit/                   # Service layer tests
├── integration/            # API endpoint tests
└── fixtures/               # Test data
```

---

## Common Issues & Solutions

### OneLook API Timeout
**Problem:** OneLook API is slow or unavailable

**Solution:** Implemented automatic fallback to local wordlists. User sees all results, just marked with different source.

### CORS Errors
**Problem:** Browser blocks API calls

**Solution:** Flask-CORS configured to allow localhost. No action needed.

### Pattern Returns No Results
**Problem:** Pattern too specific or unusual

**Solution:** UI shows "No matches found" with suggestion to broaden pattern (use more `?` wildcards).

---

## Dependencies

```
Flask==3.0.0
flask-cors==4.0.0
requests==2.31.0
pytest==7.4.3
pytest-cov==4.1.0
```

**Why these versions:**
- Flask 3.0.0: Latest stable with async support (though we don't use it)
- requests: Mature, simple HTTP client for OneLook
- pytest: Industry standard testing framework

---

## Next Steps

### After Phase 1 Complete:
1. **Use the tool** while building crosswords
2. **Collect feedback** on what works/doesn't work
3. **Consider Phase 2** (CLI tool with autofill)

### Integration with Crosshare:
This tool complements Crosshare.org:
1. Brainstorm themes → Claude.ai
2. **Pattern matching** → This tool (Phase 1)
3. Grid editing → Crosshare.org
4. **Validation** → This tool (Phase 1)
5. Clue writing → Claude.ai
6. Export → Crosshare.org

**This tool doesn't replace Crosshare, it assists while using it.**

---

## Performance Targets

| Operation | Target | Measured | Status |
|-----------|--------|----------|--------|
| Pattern search | <1s | TBD | ⏸️ Not implemented |
| Grid numbering | <100ms | TBD | ⏸️ Not implemented |
| Normalization | <50ms | TBD | ⏸️ Not implemented |
| Page load | <500ms | TBD | ⏸️ Not implemented |

---

## Questions & Decisions

### Resolved:
- ✅ Flask over FastAPI (simpler for synchronous work)
- ✅ Vanilla JS over React (only 3 components, faster development)
- ✅ File-based over database (local tool, no server needed)

### Open:
- ⏸️ Add search history? (Phase 2 feature)
- ⏸️ Add word list management UI? (Phase 2 feature)
- ⏸️ Dark mode? (Nice to have, not critical)

---

**Ready to start?** Read the docs in order (01 → 02 → 03 → 04) and follow the implementation prompts.
