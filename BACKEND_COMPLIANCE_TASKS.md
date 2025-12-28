# Backend Compliance Tasks

**Goal:** Bring BACKEND_SPEC.md to 100% coverage of implementation
**Current Status:** 13/32 endpoints documented (41%)
**Target:** 32/32 endpoints documented (100%)
**Estimated Effort:** 1.5 days

---

## Priority 1: Document Undocumented Endpoints (CRITICAL)

**Timeline:** 4-6 hours
**Impact:** Brings spec from 41% to 100% endpoint coverage

### Task 1.1: Add Wordlist CRUD API Section (7 endpoints)

**Location:** After line 691 in BACKEND_SPEC.md

**Endpoints to document:**

1. **GET /api/wordlists/:name** - Retrieve specific wordlist details
   ```json
   Response: {
     "name": "comprehensive",
     "category": "core",
     "word_count": 412483,
     "description": "Comprehensive crossword word list",
     "tags": ["core", "comprehensive"],
     "created_at": "2025-01-15T10:30:00Z",
     "updated_at": "2025-12-20T14:22:00Z"
   }
   ```

2. **POST /api/wordlists/:name** - Create new wordlist
   ```json
   Request: {
     "category": "custom",
     "description": "My custom wordlist",
     "tags": ["personal", "themed"],
     "words": ["WORD1", "WORD2", ...]
   }
   ```

3. **PUT /api/wordlists/:name** - Update existing wordlist
   ```json
   Request: {
     "description": "Updated description",
     "tags": ["updated"],
     "words": ["NEWWORD1", "NEWWORD2", ...]
   }
   ```

4. **DELETE /api/wordlists/:name** - Delete wordlist
   ```json
   Response: {
     "success": true,
     "message": "Wordlist 'custom' deleted",
     "deleted_count": 15023
   }
   ```

5. **GET /api/wordlists/:name/stats** - Get wordlist statistics
   ```json
   Response: {
     "word_count": 412483,
     "avg_word_length": 6.8,
     "min_word_length": 2,
     "max_word_length": 21,
     "length_distribution": {
       "3": 1242, "4": 5123, ...
     },
     "file_size_bytes": 4582901
   }
   ```

6. **POST /api/wordlists/search** - Search within wordlists
   ```json
   Request: {
     "query": "CAT",
     "wordlists": ["comprehensive"],
     "match_type": "contains"  // "exact", "starts_with", "ends_with", "contains"
   }
   Response: {
     "results": ["CAT", "CATS", "CATAPULT", ...],
     "total_found": 127,
     "wordlists_searched": ["comprehensive"]
   }
   ```

7. **POST /api/wordlists/import** - Import wordlist from file
   ```json
   Request: {
     "file_content": "WORD1\nWORD2\n...",
     "name": "imported_list",
     "category": "custom",
     "description": "Imported from file"
   }
   Response: {
     "success": true,
     "words_imported": 5042,
     "words_skipped": 12,
     "validation": {
       "valid": true,
       "errors": [],
       "warnings": ["12 duplicate words skipped"]
     }
   }
   ```

**Template for each endpoint:**
```markdown
#### [METHOD] /api/wordlists/[path]

**Purpose:** [Description]

**Request:**
```json
[Schema]
```

**Response:**
```json
[Schema]
```

**Parameters:**
- [param]: [type] - [description]

**Status Codes:**
- 200 OK - [scenario]
- 400 Bad Request - [scenario]
- 404 Not Found - [scenario]

**Example:**
```bash
[curl command]
```

**Performance:** [target]
**CLI Command:** [if applicable]
```

---

### Task 1.2: Extend Pause/Resume Routes Section (5 endpoints)

**Location:** After line 644 in BACKEND_SPEC.md

**Endpoints to document:**

1. **GET /api/fill/state/:task_id** - Retrieve saved autofill state
   ```json
   Response: {
     "task_id": "abc123",
     "created_at": "2025-12-27T10:00:00Z",
     "grid_size": 15,
     "slots_filled": 38,
     "total_slots": 76,
     "progress": 50,
     "state_file_path": "/tmp/autofill_states/abc123.json",
     "can_resume": true
   }
   ```

2. **DELETE /api/fill/state/:task_id** - Delete saved state
   ```json
   Response: {
     "success": true,
     "task_id": "abc123",
     "message": "Autofill state deleted"
   }
   ```

3. **GET /api/fill/states** - List all saved states
   ```json
   Response: {
     "states": [
       {
         "task_id": "abc123",
         "created_at": "2025-12-27T10:00:00Z",
         "grid_size": 15,
         "slots_filled": 38,
         "total_slots": 76,
         "progress": 50
       },
       ...
     ],
     "total_count": 5,
     "total_size_bytes": 1048576
   }
   ```

4. **POST /api/fill/states/cleanup** - Clean up old states
   ```json
   Request: {
     "older_than_hours": 24,
     "keep_recent": 5
   }
   Response: {
     "deleted_count": 12,
     "space_freed_bytes": 2097152,
     "remaining_count": 5
   }
   ```

5. **POST /api/fill/edit-summary** - Get summary of user edits
   ```json
   Request: {
     "original_grid": [[...]],
     "edited_grid": [[...]]
   }
   Response: {
     "edits": [
       {
         "row": 3,
         "col": 5,
         "old_value": "A",
         "new_value": "B",
         "type": "modified"
       },
       {
         "row": 4,
         "col": 2,
         "old_value": ".",
         "new_value": "C",
         "type": "filled"
       }
     ],
     "total_edits": 12,
     "edit_types": {
       "filled": 8,
       "modified": 3,
       "emptied": 1
     }
   }
   ```

---

### Task 1.3: Extend Grid Helper Routes Section (2 endpoints)

**Location:** After line 496 in BACKEND_SPEC.md

**Endpoints to document:**

1. **POST /api/grid/apply-black-squares** - Apply suggested black squares
   ```json
   Request: {
     "grid": [[...]],
     "grid_size": 15,
     "suggestions": [
       {"row": 0, "col": 7},
       {"row": 14, "col": 7}
     ],
     "apply_symmetric": true
   }
   Response: {
     "updated_grid": [[...]],
     "applied_positions": [
       {"row": 0, "col": 7},
       {"row": 14, "col": 7}
     ],
     "grid_info": {
       "size": [15, 15],
       "word_count": 77,
       "black_square_count": 40,
       "black_square_percentage": 17.8
     }
   }
   ```

2. **POST /api/grid/validate** - Validate grid structure
   ```json
   Request: {
     "grid": [[...]],
     "grid_size": 15,
     "check_symmetry": true,
     "check_connectivity": true
   }
   Response: {
     "valid": true,
     "errors": [],
     "warnings": ["One 2-letter word at (3,5)"],
     "checks": {
       "symmetry": "rotational",
       "connectivity": "all_cells_connected",
       "min_word_length": 3,
       "black_square_percentage": 16.8
     }
   }
   ```

---

### Task 1.4: Extend Theme Routes Section (2 endpoints)

**Location:** After line 570 in BACKEND_SPEC.md

**Endpoints to document:**

1. **POST /api/theme/validate** - Validate theme words
   ```json
   Request: {
     "theme_words": ["WORD1", "WORD2"],
     "grid_size": 15
   }
   Response: {
     "valid": true,
     "errors": [],
     "warnings": ["WORD1 is very long (12 letters) for 15x15 grid"],
     "validation": {
       "all_words_fit": true,
       "length_range": [5, 12],
       "suggested_grid_size": 15
     }
   }
   ```

2. **POST /api/theme/apply-placement** - Apply theme placement
   ```json
   Request: {
     "grid": [[...]],
     "grid_size": 15,
     "placement": {
       "word": "EXAMPLE",
       "row": 7,
       "col": 4,
       "direction": "across"
     }
   }
   Response: {
     "updated_grid": [[...]],
     "placement_info": {
       "word": "EXAMPLE",
       "row": 7,
       "col": 4,
       "direction": "across",
       "conflicts": [],
       "intersections": 2
     }
   }
   ```

---

### Task 1.5: Extend Progress Routes Section (2 endpoints)

**Location:** After line 687 in BACKEND_SPEC.md

**Endpoints to document:**

1. **POST /api/progress/start** - Manually start progress tracker
   ```json
   Response: {
     "task_id": "550e8400-...",
     "progress_url": "/api/progress/550e8400-..."
   }
   ```

2. **POST /api/progress/:task_id/update** - Manually update progress
   ```json
   Request: {
     "progress": 45,
     "message": "Processing slot 34/76",
     "status": "running",
     "data": {...}
   }
   Response: {
     "success": true,
     "task_id": "550e8400-..."
   }
   ```

---

### Task 1.6: Document Pattern with Progress (1 endpoint)

**Location:** After line 254 in BACKEND_SPEC.md

**Endpoint to document:**

1. **POST /api/pattern/with-progress** - Pattern search with SSE progress
   ```json
   Request: {
     "pattern": "C?T",
     "wordlists": ["comprehensive"],
     "max_results": 20
   }
   Response: {
     "task_id": "550e8400-...",
     "progress_url": "/api/progress/550e8400-..."
   }
   ```

---

## Priority 2: Fix Failing Tests (HIGH)

**Timeline:** 2-4 hours
**Impact:** Brings test pass rate from 96.4% to 100%

### Task 2.1: Fix CLI Integration Test

**File:** `backend/tests/integration/test_cli_integration.py`
**Test:** `TestCLIErrorHandling::test_cli_malformed_json_output`

**Action:**
1. Review test expectations
2. Check CLIAdapter JSON parsing error handling
3. Ensure proper error propagation
4. Update test if CLI behavior changed

---

### Task 2.2: Fix Progress Integration Tests (2 tests)

**File:** `backend/tests/integration/test_progress_integration.py`

**Tests:**
1. `TestFillWithProgressEndpoint::test_fill_with_progress_spawns_background_task`
2. `TestProgressStream::test_progress_endpoint_requires_task_id`

**Action:**
1. Review threading and SSE implementation
2. Check for race conditions in test
3. Verify task_id generation and tracking
4. Update tests to match current implementation

---

### Task 2.3: Fix Grid Transformation Test

**File:** `backend/tests/unit/test_grid_transformation.py`
**Test:** `TestGridTransformationInvariance::test_grid_dimensions_preserved`

**Action:**
1. Review grid format conversion logic
2. Verify dimensions are preserved in routes.py (lines 204-218)
3. Check for off-by-one errors
4. Update test or fix conversion logic

---

## Priority 3: Verify and Update Coverage Claims (MEDIUM)

**Timeline:** 30 minutes
**Impact:** Ensures documentation accuracy

### Task 3.1: Run Coverage Analysis

**Commands:**
```bash
cd /Users/apa/projects/untitled_project/crossword-helper
pytest backend/tests/ --cov=backend --cov-report=html --cov-report=term
```

**Action:**
1. Record actual coverage percentage
2. Update BACKEND_SPEC.md line 1109 with real number
3. Identify any uncovered critical paths
4. Add tests if coverage < 90%

---

### Task 3.2: Update Test Status in Spec

**File:** `docs/specs/BACKEND_SPEC.md`
**Lines to update:**
- Line 6: Change "165/165 tests passing" to actual count
- Line 1107: Update test counts

**Action:**
1. After fixing tests, update to "165/165 tests passing"
2. If tests still failing, update to "159/165 tests passing"
3. Add note about known issues if any remain

---

## Priority 4: Adjust Performance Targets (LOW)

**Timeline:** 1 hour
**Impact:** Sets realistic expectations

### Task 4.1: Update Performance Table

**File:** `docs/specs/BACKEND_SPEC.md`
**Location:** Lines 1053-1066

**Current unrealistic targets:**
- GET /api/health: <50ms (actual: ~120ms due to subprocess)
- POST /api/normalize: <50ms (actual: ~120ms cold, <1ms cached)
- POST /api/number: <100ms (actual: ~150ms)

**Proposed updates:**

```markdown
| Endpoint | Target (Cold) | Target (Cached) | Bottleneck |
|----------|---------------|-----------------|------------|
| GET /api/health | <150ms | N/A | Subprocess overhead |
| POST /api/normalize | <150ms | <5ms | Subprocess overhead, LRU cache helps |
| POST /api/number | <200ms | N/A | Subprocess + grid processing |
| POST /api/pattern | <1s | <500ms | OneLook API + local search |
| POST /api/fill (11×11) | <30s | N/A | CSP solving |
| POST /api/fill (15×15) | <5min | N/A | CSP solving |
| POST /api/fill (21×21) | <30min | N/A | CSP solving |
```

**Note to add:**
"Subprocess overhead of ~120ms applies to all CLI-delegated operations. This is an acceptable tradeoff for the benefits of single-source-of-truth architecture. Caching is implemented for frequently-called operations (normalize)."

---

## Checklist for Completion

### Documentation Update
- [ ] Wordlist CRUD API documented (7 endpoints)
- [ ] Pause/Resume state management documented (5 endpoints)
- [ ] Grid helpers extended (2 endpoints)
- [ ] Theme routes extended (2 endpoints)
- [ ] Progress management documented (2 endpoints)
- [ ] Pattern with progress documented (1 endpoint)
- [ ] Table of Contents updated
- [ ] All examples include curl commands
- [ ] All schemas validated against implementation

### Testing
- [ ] test_cli_malformed_json_output fixed
- [ ] test_fill_with_progress_spawns_background_task fixed
- [ ] test_progress_endpoint_requires_task_id fixed
- [ ] test_grid_dimensions_preserved fixed
- [ ] Coverage report generated
- [ ] Coverage claims updated in spec
- [ ] Test status updated to 165/165 (or accurate count)

### Performance
- [ ] Performance targets updated to reflect subprocess reality
- [ ] Caching benefits documented
- [ ] Note added about acceptable tradeoffs

### Validation
- [ ] All endpoint examples tested manually
- [ ] All schemas match actual API responses
- [ ] All curl commands work correctly
- [ ] Spec version bumped to 2.1.0
- [ ] "Last Updated" date updated

---

## Success Criteria

**Documentation:**
- ✅ 32/32 endpoints documented (100%)
- ✅ All request/response schemas complete
- ✅ All examples include working curl commands
- ✅ Table of Contents matches all sections

**Testing:**
- ✅ 165/165 tests passing (100%)
- ✅ Coverage ≥ 90% (verified)
- ✅ No known failing tests

**Quality:**
- ✅ No discrepancies between spec and implementation
- ✅ All performance targets realistic
- ✅ All architectural components documented

**Final Grade Target:** A (95/100)
- Implementation Quality: A (95/100) - Already achieved
- Documentation Completeness: A (95/100) - After tasks complete
- Test Coverage: A (95/100) - After fixes

---

## Estimated Timeline

**Day 1 (6 hours):**
- Morning (3 hours): Document wordlist CRUD + pause/resume endpoints
- Afternoon (3 hours): Document grid/theme/progress endpoints + examples

**Day 2 (4 hours):**
- Morning (2 hours): Fix 4 failing tests
- Afternoon (2 hours): Verify coverage, update performance targets, final validation

**Total:** 1.5 days (10 hours)

---

**Created:** 2025-12-27
**Status:** Ready for execution
**Next Step:** Begin Task 1.1 (Wordlist CRUD documentation)
