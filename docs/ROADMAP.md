# Crossword Helper - Development Roadmap

## Overview

Three-phase development plan building from simple web app → comprehensive CLI tool → integrated system.

**Total Timeline:** 5-6 weeks
**Current Phase:** Pre-implementation (Documentation complete)

---

## Development Philosophy

### Progressive Enhancement
- **Phase 1:** Get something working fast (web app MVP)
- **Phase 2:** Build powerful features (CLI with autofill)
- **Phase 3:** Integrate for best of both worlds

### Why This Order?

1. **Phase 1 First (Web App):**
   - Fastest path to usable tool (3-5 days)
   - Validates core concepts
   - Immediately useful while building Phase 2
   - Low complexity, high value

2. **Phase 2 Second (CLI Tool):**
   - Most complex features (CSP autofill)
   - Standalone utility with rich capabilities
   - No dependency on web app
   - Can be used independently

3. **Phase 3 Last (Integration):**
   - Refactor web app to use CLI backend
   - Best of both: web UI + powerful algorithms
   - Minimal code duplication
   - Maximum capability

---

## Phase 1: Web Application (3-5 days)

**Goal:** Local Flask web app with 3 helper tools

### Features
1. **Pattern Matcher** - Find words matching `?I?A` patterns
2. **Numbering Validator** - Auto-number grids
3. **Convention Helper** - Normalize entries ("Tina Fey" → "TINAFEY")

### Tech Stack
- Backend: Flask 3.0+, Python 3.9+
- Frontend: Vanilla HTML/CSS/JavaScript
- Data: File-based wordlists
- Testing: pytest

### Deliverables
- ✅ Working web app at localhost:5000
- ✅ 3 REST API endpoints
- ✅ Responsive single-page frontend
- ✅ Unit + integration tests (>85% coverage)
- ✅ OneLook API integration with fallback
- ✅ Local wordlist support

### Documentation
- `phase1-webapp/01-architecture.md` - System design
- `phase1-webapp/02-api-specification.md` - Complete API contracts
- `phase1-webapp/03-implementation-guide.md` - Implementation details
- `phase1-webapp/04-implementation-prompts.md` - Step-by-step execution

### Success Criteria
- [ ] All 3 tools functional in browser
- [ ] Tests pass with >85% coverage
- [ ] Response times: Pattern <1s, Numbering <100ms, Normalize <50ms
- [ ] Mobile responsive (works at 360px width)
- [ ] Graceful error handling (OneLook timeout handled)

**Status:** ⏸️ Ready to implement

---

## Phase 2: CLI Tool (3-4 weeks)

**Goal:** Comprehensive Python CLI for crossword construction

### Features
1. **Grid Engine** - Create, validate, manage grids
2. **Autofill Engine** - CSP solver with backtracking
3. **Pattern Matcher** - Enhanced word search with scoring
4. **Clue Manager** - Store and retrieve clues
5. **Export Engine** - HTML, PDF, .puz formats

### Tech Stack
- Language: Python 3.9+
- CLI: Click + Rich (terminal UI)
- Algorithms: NumPy for grid operations
- Data: JSON files, SQLite for clues
- Export: reportlab (PDF), pypuz (.puz)

### Core Algorithm: Constraint Satisfaction with Backtracking
```
1. Find empty cell with minimum remaining values (MRV heuristic)
2. Get candidate words sorted by value (LCV heuristic)
3. Try word, check constraints (arc consistency)
4. If valid → recurse to next cell
5. If invalid → backtrack, try next candidate
6. If no candidates → backtrack to previous cell
```

### Deliverables
- ✅ Complete CLI with commands: new, fill, export, clue
- ✅ Autofill algorithm with performance targets:
  - 11×11 grid: <30 seconds
  - 15×15 grid: <5 minutes
  - 21×21 grid: <30 minutes
- ✅ Export to 3 formats (HTML, PDF, .puz)
- ✅ Comprehensive test suite (>90% coverage)
- ✅ Interactive mode for stepwise filling

### Documentation
- `phase2-cli/01-architecture.md` - CLI architecture
- `phase2-cli/02-specifications.md` - Detailed specs
- `phase2-cli/03-implementation-prompts.md` - Step-by-step execution

### Success Criteria
- [ ] CLI commands functional: `crossword new`, `crossword fill`, `crossword export`
- [ ] Autofill successfully fills 11×11 in <30s
- [ ] Exports work for all 3 formats
- [ ] Tests pass with >90% coverage
- [ ] Interactive mode allows manual word placement
- [ ] Symmetry validation works (rotational + reflection)

**Status:** ⏸️ Waiting for Phase 1 completion

---

## Phase 3: Integration (1 week)

**Goal:** Refactor web app to use CLI backend

### Approach

**Before Integration:**
```
Web App API → Direct implementation
    ├─ Pattern Matcher (web)
    ├─ Numbering Validator (web)
    └─ Convention Helper (web)

CLI Tool → Standalone
    ├─ Grid Engine
    ├─ Autofill Engine
    └─ Export Engine
```

**After Integration:**
```
Web App API → CLI Tool Wrapper
    ├─ Pattern → calls `crossword pattern ?I?A`
    ├─ Number → calls `crossword number grid.json`
    ├─ Normalize → calls `crossword normalize "Tina Fey"`
    └─ NEW: Autofill → calls `crossword fill grid.json`

CLI Tool → Shared implementation (single source of truth)
```

### Benefits
1. **No code duplication** - One implementation, two interfaces
2. **More features in web app** - Autofill becomes available
3. **Easier maintenance** - Update once, affects both
4. **Better testing** - Shared logic tested once

### Refactoring Strategy

#### Step 1: Add CLI Commands to Web Tools (2 days)
- Add `crossword pattern` CLI command
- Add `crossword number` CLI command
- Add `crossword normalize` CLI command
- Ensure CLI and web versions produce identical output

#### Step 2: Refactor Web API to Call CLI (2 days)
- Replace Flask route implementations with subprocess calls
- Keep API contracts identical (backward compatible)
- Add caching layer (Redis optional, in-memory sufficient)
- Handle CLI errors gracefully

#### Step 3: Add Autofill to Web App (2 days)
- New API endpoint: `POST /api/fill`
- Frontend component for autofill
- Progress tracking (WebSocket or polling)
- Cancel/pause controls

#### Step 4: Testing & Optimization (1 day)
- Test all endpoints still work
- Performance benchmarking (subprocess overhead)
- Optimize hot paths if needed
- Documentation updates

### Deliverables
- ✅ Web app routes call CLI backend
- ✅ New autofill feature in web UI
- ✅ Tests updated and passing
- ✅ Performance acceptable (<100ms overhead per request)
- ✅ Documentation updated

### Success Criteria
- [ ] All Phase 1 features still work
- [ ] Autofill available in web UI
- [ ] Tests pass with maintained coverage
- [ ] API response times within +100ms of Phase 1
- [ ] Single codebase for all logic

**Status:** ⏸️ Waiting for Phase 2 completion

---

## Timeline Summary

| Phase | Duration | Complexity | Value | Status |
|-------|----------|------------|-------|--------|
| **Phase 1** | 3-5 days | Low | High | Ready |
| **Phase 2** | 3-4 weeks | High | High | Ready |
| **Phase 3** | 1 week | Medium | Medium | Ready |
| **Total** | 5-6 weeks | - | - | - |

---

## Dependencies

### Phase 1 → Phase 2
- **None** (parallel development possible)
- Phase 2 can start before Phase 1 complete
- Phase 1 informs Phase 2 API design

### Phase 2 → Phase 3
- **Phase 2 must be complete** before Phase 3 starts
- Integration requires working CLI tool

### Phase 1 → Phase 3
- **Phase 1 must exist** to refactor
- Integration modifies Phase 1 codebase

---

## Risk Management

### Phase 1 Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OneLook API changes | Low | High | Fallback to local wordlists |
| CORS issues | Medium | Low | Flask-CORS configured |
| Browser compatibility | Low | Medium | ES6+ (2015), widely supported |

### Phase 2 Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Autofill too slow | Medium | High | Implement heuristics, parallel search |
| CSP algorithm bugs | High | High | Extensive testing, start simple (3×3) |
| Export format errors | Medium | Medium | Use established libraries |

### Phase 3 Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Subprocess overhead | Medium | Medium | Benchmarking, optimization |
| CLI breaking changes | Low | High | Version pinning, integration tests |
| Regression bugs | Medium | High | Comprehensive test suite |

---

## Post-Launch Enhancements

**Not in initial 3 phases, consider for Phase 4:**

### Optional Features
- Word list management UI (add/edit/delete via web)
- Search history (recent patterns saved)
- Grid visualization (show numbered grid visually)
- Crosshare JSON import/export
- Dark mode for web UI
- Save user preferences (SQLite)
- Deploy to web server (Heroku/Render)
- Multi-user support (authentication)
- Collaborative puzzle building
- Real-time updates (WebSocket)

### When to Add
- **After Phase 3 complete** and stable
- **User feedback** indicates priority
- **Time available** (not critical path)

---

## Documentation Status

✅ **Complete and Ready:**
- Phase 1 documentation (4 docs)
- Phase 2 documentation (3 docs)
- Guides (Claude AI setup, etc.)
- Analysis documents
- This roadmap

⏸️ **Pending:**
- Phase 3 refactoring plan (will write after Phase 2)
- Phase-specific testing guides
- Troubleshooting guide (will populate during implementation)

---

## Getting Started

### For Phase 1 Implementation:
1. Read `phase1-webapp/01-architecture.md` (understand design)
2. Review `phase1-webapp/02-api-specification.md` (know contracts)
3. Study `phase1-webapp/03-implementation-guide.md` (see patterns)
4. Execute `phase1-webapp/04-implementation-prompts.md` (build it)

### For Phase 2 Implementation:
1. Read `phase2-cli/01-architecture.md` (understand CLI design)
2. Review `phase2-cli/02-specifications.md` (detailed requirements)
3. Execute `phase2-cli/03-implementation-prompts.md` (build it)

### For Phase 3 Implementation:
1. Complete Phases 1 and 2 first
2. Documentation will be written after Phase 2

---

## Measuring Success

### Phase 1 Success Metrics
- ✅ All features work in browser
- ✅ Tests pass (>85% coverage)
- ✅ Performance targets met
- ✅ Zero console errors
- ✅ Mobile responsive

### Phase 2 Success Metrics
- ✅ CLI commands functional
- ✅ Autofill performance acceptable
- ✅ Exports work correctly
- ✅ Tests pass (>90% coverage)
- ✅ Symmetry validation works

### Phase 3 Success Metrics
- ✅ Integration complete
- ✅ No regressions
- ✅ Autofill in web UI
- ✅ Performance acceptable
- ✅ Single codebase

---

## Questions & Decisions

### Resolved Decisions
- ✅ Flask over FastAPI (simplicity for synchronous work)
- ✅ Vanilla JS over React (only 3 components)
- ✅ File-based over database (MVP, local use)
- ✅ Three-phase approach (progressive enhancement)
- ✅ Phase order: Web → CLI → Integration (fastest value)

### Open Decisions
- ⏸️ Caching strategy for Phase 3 (Redis vs in-memory)
- ⏸️ WebSocket vs polling for autofill progress
- ⏸️ Deployment platform if going online (Heroku vs Render)

---

**Last Updated:** Documentation reorganization complete
**Next Milestone:** Begin Phase 1 implementation
