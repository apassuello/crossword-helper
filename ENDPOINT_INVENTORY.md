# Endpoint Inventory - Phase 1.1 Analysis

**Date**: December 27, 2025
**Total Implemented Endpoints**: 32
**Documented in BACKEND_SPEC.md**: 13
**Documented in API_REFERENCE.md**: 30
**Gap (BACKEND_SPEC)**: 19 endpoints

---

## Summary by Category

| Category | Implemented | In BACKEND_SPEC | In API_REFERENCE | Decision |
|----------|-------------|-----------------|------------------|----------|
| Core Operations | 7 | 5 | 7 | **KEEP all** |
| Grid Helpers | 3 | 1 | 3 | **KEEP all** |
| Theme Management | 4 | 2 | 4 | **KEEP all** |
| Pause/Resume | 7 | 2 | 7 | **KEEP all** |
| Progress Tracking | 3 | 1 | 1 | **REVIEW** |
| Wordlist Management | 8 | 1 | 8 | **KEEP all** |
| **TOTAL** | **32** | **13** | **30** | - |

---

## Detailed Endpoint Analysis

### Core Operations (routes.py)

| # | Endpoint | Method | BACKEND_SPEC | API_REF | Frontend Usage | Tests | Decision |
|---|----------|--------|--------------|---------|----------------|-------|----------|
| 1 | /api/health | GET | ✅ | ✅ | App.jsx (health check) | ✅ | **KEEP** - Standard health endpoint |
| 2 | /api/pattern | POST | ✅ | ✅ | PatternMatcher.jsx | ✅ | **KEEP** - Core feature |
| 3 | /api/number | POST | ✅ | ✅ | App.jsx (grid numbering) | ✅ | **KEEP** - Core feature |
| 4 | /api/normalize | POST | ✅ | ✅ | ToolPanel.jsx | ✅ | **KEEP** - Core feature |
| 5 | /api/fill | POST | ✅ | ✅ | AutofillPanel.jsx | ✅ | **KEEP** - Primary feature |
| 6 | /api/pattern/with-progress | POST | ❌ | ✅ | PatternMatcher.jsx (optional) | ✅ | **KEEP** - SSE variant |
| 7 | /api/fill/with-progress | POST | ✅ | ✅ | AutofillPanel.jsx (primary) | ✅ | **KEEP** - SSE autofill |

**Analysis**: All core operations are essential. Pattern/fill with-progress variants provide SSE progress tracking for long-running operations.

---

### Grid Helpers (grid_routes.py)

| # | Endpoint | Method | BACKEND_SPEC | API_REF | Frontend Usage | Tests | Decision |
|---|----------|--------|--------------|---------|----------------|-------|----------|
| 8 | /api/grid/suggest-black-square | POST | ✅ | ✅ | BlackSquareSuggestions.jsx | ✅ | **KEEP** - Adaptive autofill |
| 9 | /api/grid/apply-black-squares | POST | ❌ | ✅ | BlackSquareSuggestions.jsx | ✅ | **KEEP** - Required for suggestions |
| 10 | /api/grid/validate | POST | ❌ | ✅ | App.jsx (validation) | ✅ | **KEEP** - Grid validation |

**Analysis**: All 3 endpoints work together for adaptive autofill black square suggestions. Essential feature set.

---

### Theme Management (theme_routes.py)

| # | Endpoint | Method | BACKEND_SPEC | API_REF | Frontend Usage | Tests | Decision |
|---|----------|--------|--------------|---------|----------------|-------|----------|
| 11 | /api/theme/upload | POST | ✅ | ✅ | ThemeWordsPanel.jsx | ✅ | **KEEP** - Theme entry point |
| 12 | /api/theme/suggest-placements | POST | ✅ | ✅ | ThemeWordsPanel.jsx | ✅ | **KEEP** - Core theme feature |
| 13 | /api/theme/validate | POST | ❌ | ✅ | ThemeWordsPanel.jsx | ✅ | **KEEP** - Validation before placement |
| 14 | /api/theme/apply-placement | POST | ❌ | ✅ | ThemeWordsPanel.jsx | ✅ | **KEEP** - Apply suggested placement |

**Analysis**: Complete theme word workflow. All endpoints heavily used in ThemeWordsPanel.

---

### Pause/Resume (pause_resume_routes.py)

| # | Endpoint | Method | BACKEND_SPEC | API_REF | Frontend Usage | Tests | Decision |
|---|----------|--------|--------------|---------|----------------|-------|----------|
| 15 | /api/fill/pause/{task_id} | POST | ✅ | ✅ | AutofillPanel.jsx | ✅ | **KEEP** - Core pause feature |
| 16 | /api/fill/resume | POST | ✅ | ✅ | AutofillPanel.jsx | ✅ | **KEEP** - Core resume feature |
| 17 | /api/fill/state/{task_id} | GET | ❌ | ✅ | AutofillPanel.jsx (check state) | ✅ | **KEEP** - State inspection |
| 18 | /api/fill/state/{task_id} | DELETE | ❌ | ✅ | AutofillPanel.jsx (cleanup) | ✅ | **KEEP** - State cleanup |
| 19 | /api/fill/states | GET | ❌ | ✅ | AutofillPanel.jsx (list all) | ✅ | **KEEP** - State management |
| 20 | /api/fill/states/cleanup | POST | ❌ | ✅ | Not used | ✅ | **KEEP** - Maintenance endpoint |
| 21 | /api/fill/edit-summary | POST | ❌ | ✅ | AutofillPanel.jsx | ✅ | **KEEP** - Edit merging |

**Analysis**: Complete pause/resume state management system. All endpoints are production-ready and tested. Heavy frontend usage except cleanup (maintenance endpoint).

**Missing (Critical)**:
- ❌ POST /api/fill/cancel/{task_id} - **DOCUMENTED but NOT IMPLEMENTED**

---

### Progress Tracking (progress_routes.py)

| # | Endpoint | Method | BACKEND_SPEC | API_REF | Frontend Usage | Tests | Decision |
|---|----------|--------|--------------|---------|----------------|-------|----------|
| 22 | /api/progress/{task_id} | GET | ✅ | ✅ | App.jsx (SSE stream) | ✅ | **KEEP** - SSE progress |
| 23 | /api/progress/start | POST | ❌ | ❌ | Not found | ⚠️ | **REVIEW** - Internal? |
| 24 | /api/progress/{task_id}/update | POST | ❌ | ❌ | Not found | ⚠️ | **REVIEW** - Internal? |

**Analysis**:
- /progress/{task_id} is the SSE endpoint - essential, heavily used
- /progress/start and /progress/update are likely internal endpoints used by background tasks
- **Need to verify**: Are these internal-only or should they be public?

**Action**: Grep frontend for usage before making decision

---

### Wordlist Management (wordlist_routes.py)

| # | Endpoint | Method | BACKEND_SPEC | API_REF | Frontend Usage | Tests | Decision |
|---|----------|--------|--------------|---------|----------------|-------|----------|
| 25 | /api/wordlists | GET | ✅ | ✅ | WordListPanel.jsx | ✅ | **KEEP** - List wordlists |
| 26 | /api/wordlists/{name} | GET | ❌ | ✅ | WordListPanel.jsx | ✅ | **KEEP** - Get wordlist |
| 27 | /api/wordlists/{name} | POST | ❌ | ✅ | WordListPanel.jsx | ✅ | **KEEP** - Create wordlist |
| 28 | /api/wordlists/{name} | PUT | ❌ | ✅ | WordListPanel.jsx | ✅ | **KEEP** - Update wordlist |
| 29 | /api/wordlists/{name} | DELETE | ❌ | ✅ | WordListPanel.jsx | ✅ | **KEEP** - Delete wordlist |
| 30 | /api/wordlists/{name}/stats | GET | ❌ | ✅ | WordListPanel.jsx | ✅ | **KEEP** - Stats display |
| 31 | /api/wordlists/search | POST | ❌ | ✅ | Not found | ✅ | **KEEP** - Cross-wordlist search |
| 32 | /api/wordlists/import | POST | ❌ | ✅ | WordListPanel.jsx | ✅ | **KEEP** - Import from file |

**Analysis**: Complete CRUD + extras. All heavily used in WordListPanel except /search (still valuable for API consumers).

---

## Decision Summary

### ✅ KEEP & DOCUMENT (30 endpoints)
All endpoints are production-ready, tested, and either used in frontend or provide important API functionality.

### 🔒 INTERNAL (2 endpoints) - Not for Public API
- POST /api/progress/start - Used internally to create progress trackers
- POST /api/progress/{task_id}/update - Testing/internal endpoint (marked in code as "for testing")

**Rationale**: Frontend connects directly to SSE endpoint (GET /api/progress/{task_id}). These endpoints are used internally by backend when starting operations. No frontend usage found. Can be mentioned in BACKEND_SPEC.md as internal implementation details but should NOT be in API_REFERENCE.md public API.

### ❌ MISSING (1 endpoint)
- POST /api/fill/cancel/{task_id} - Documented in API_REFERENCE.md but NOT implemented

---

## Recommendations

### For BACKEND_SPEC.md
**Add these 17 PUBLIC endpoints** (all marked ❌ in "BACKEND_SPEC" column above):
1. POST /api/pattern/with-progress
2. POST /api/grid/apply-black-squares
3. POST /api/grid/validate
4. POST /api/theme/validate
5. POST /api/theme/apply-placement
6. GET /api/fill/state/{task_id}
7. DELETE /api/fill/state/{task_id}
8. GET /api/fill/states
9. POST /api/fill/states/cleanup
10. POST /api/fill/edit-summary
11. GET /api/wordlists/{name}
12. POST /api/wordlists/{name}
13. PUT /api/wordlists/{name}
14. DELETE /api/wordlists/{name}
15. GET /api/wordlists/{name}/stats
16. POST /api/wordlists/search
17. POST /api/wordlists/import

**Mention as INTERNAL** (not part of public API contract):
- POST /api/progress/start (internal - used by backend)
- POST /api/progress/{task_id}/update (testing/internal)

### For Implementation
- **Implement**: POST /api/fill/cancel/{task_id}

### For API_REFERENCE.md
- No changes needed - API_REFERENCE.md is already complete with 30 public endpoints
- Do NOT add internal progress endpoints

---

## Next Steps (Phase 1.2-1.4)

1. ✅ **Checked frontend usage** - No usage found for internal progress endpoints
2. ✅ **Reviewed progress_routes.py** - Confirmed internal-only (marked "for testing")
3. **Proceed to test analysis** (Phase 1.2)
4. **Complete remaining discovery tasks** (Phase 1.3-1.4)

---

**Completed**: Phase 1.1 - Endpoint Inventory & Review ✅
**Time**: ~2 hours
**Output**:
- 30 public endpoints to document
- 2 internal endpoints (mention but don't document as public API)
- 1 endpoint to implement (cancel)
- **Final Gap**: 17 endpoints missing from BACKEND_SPEC.md (not 19)
