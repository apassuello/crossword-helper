# Known Issues

**Last Updated**: December 28, 2025
**Status**: Multiple issues identified, needs debugging

---

## Critical Issues

### 1. Custom Wordlists Not Displaying in UI ✅ FIXED

**Status**: FIXED (December 28, 2025)
**Affected Component**: backend/data/wordlist_manager.py
**Symptoms**:
- Backend API correctly returns 4 custom wordlists
- API test: `fetch('/api/wordlists')` shows custom lists present
- Frontend React component does NOT render "🎨 Custom Lists" section
- Console test: `document.querySelector('.custom-section')` returns `null`

**Root Cause**: The wordlist `custom/theme_list` was missing the `name` field in the API response. When the metadata existed but was incomplete, the default values weren't applied, causing the frontend to crash silently when trying to render `wl.name`.

**Fix**: Modified `wordlist_manager.py` line 121-129 to always merge default metadata with actual metadata, ensuring all required fields are present even when metadata exists but is incomplete.

**Files Fixed**:
- `backend/data/wordlist_manager.py` (lines 121-129: metadata merging)

**Testing**:
- ✅ All 4 custom wordlists now have `name` field
- ✅ All wordlist-related tests pass (5/5)
- ✅ Frontend should now render custom lists correctly

---

### 2. Theme Word Priority - Untested

**Status**: IMPLEMENTED BUT UNTESTED
**Affected Components**: All autofill algorithms

**What Works**:
- ✅ Backend accepts `themeList` parameter
- ✅ CLI loads theme words from file
- ✅ Algorithms have theme_words parameter
- ✅ ThemeWordPriorityOrdering class created (+50 bonus logic)
- ✅ Integration into BeamSearchOrchestrator

**What's Broken**:
- ❌ Cannot test via UI (blocked by Issue #1)
- ❌ No end-to-end integration test
- ❌ Unknown if priority logic actually works in practice

**Impact**: Feature is code-complete but unverified

**Next Steps**:
1. Fix Issue #1 first
2. Create end-to-end test with real grid
3. Verify theme words appear preferentially

---

## Medium Priority Issues

### 3. Documentation Inconsistencies

**Status**: NEEDS UPDATE

**Problems**:
- Multiple documentation files claim feature is "complete and working"
- User guide describes UI that doesn't actually render
- Technical docs accurate for backend/algorithms, but UI broken

**Files Needing Update**:
- `THEME_WORD_PRIORITY_IMPLEMENTATION_COMPLETE.md` (claims UI works)
- `docs/THEME_LIST_FEATURE.md` (user guide for broken UI)
- `PHASE_2_IMPLEMENTATION_COMPLETE.md` (Phase 2 status)

**Next Steps**:
1. Update all docs to reflect current broken state
2. Add troubleshooting section
3. Create "known limitations" section

---

### 4. Untracked Test Files

**Status**: CLEANED UP (archived)

**What Was Done**:
- Moved test files to `archive/test-files/`
- Moved demo grids to `archive/demo-grids/`
- Moved old documentation to `archive/documentation/`
- Added `archive/` to `.gitignore`

**Remaining Untracked**:
- `READING_LIST.md` (keep or move?)
- `USER_GUIDE_COMPLETE_WORKFLOW.md` (keep or move?)
- `data/wordlists/custom/demo_words.txt` (keep for testing)

---

## Low Priority Issues

### 5. Git Commit Contains Broken Code

**Status**: COMMITTED (e213f74)

**Problem**:
- Commit message claims "Feature complete and tested"
- UI is actually broken
- Should have caught this before committing

**Impact**:
- Git history contains misleading commit
- May confuse future developers

**Options**:
1. Leave as-is, fix in next commit
2. Amend commit with corrected message (risky if pushed)
3. Create follow-up commit explaining issues

---

## What Actually Works

### ✅ Backend (Fully Functional)

- Custom wordlist upload and storage
- Wordlist metadata API (`/api/wordlists`)
- Theme wordlist resolution in routes.py
- CLI `--theme-wordlist` flag
- Theme words loading from file

**Tested**: API returns correct data

### ✅ Algorithms (Code Complete, Untested)

- ThemeWordPriorityOrchestrator class
- +50 bonus scoring for theme words
- Theme-first sorting in candidate lists
- Integration in BeamSearchOrchestrator
- Integration in IterativeRepair

**Tested**: Syntax checks pass, unit test passes

### ❌ Frontend (BROKEN)

- AutofillPanel not rendering custom lists
- Theme list UI not accessible
- Radio buttons not appearing
- Orange banner not showing

**Tested**: Console debugging confirms section missing

---

## Debugging Log

### December 28, 2025

**Console Tests Performed**:
```javascript
// Test 1: API works
fetch('/api/wordlists').then(r=>r.json())
// Result: ✅ Returns 4 custom lists

// Test 2: Section renders
document.querySelector('.custom-section')
// Result: ❌ Returns null (section not in DOM)

// Test 3: Sections on page
document.querySelectorAll('.wordlist-section')
// Result: Unknown (need to run)
```

**Findings**:
- Backend is functional
- Frontend React component is not populating custom wordlists
- Likely issue in `loadAvailableWordlists()` or component state

---

## Recommended Fix Order

1. **Fix Issue #1 (Custom lists not displaying)** - CRITICAL
   - Debug AutofillPanel.jsx component
   - Check React state population
   - Verify useEffect hooks firing
   - Add error handling to loadAvailableWordlists

2. **Test Issue #2 (Theme priority)** - HIGH
   - Create integration test
   - Verify +50 bonus works
   - Test with real grid

3. **Update Issue #3 (Documentation)** - MEDIUM
   - Correct all docs to reflect reality
   - Add "Known Issues" sections
   - Update troubleshooting guides

4. **Clean Issue #4 (Untracked files)** - LOW
   - Decide on READING_LIST.md fate
   - Decide on USER_GUIDE_COMPLETE_WORKFLOW.md
   - Commit or archive remaining files

5. **Address Issue #5 (Git history)** - LOW
   - Create follow-up commit with fixes
   - Update commit message via git notes (optional)

---

## For Next Developer

If you're picking this up:

1. **Start Here**: Fix `src/components/AutofillPanel.jsx`
2. **Check**: Lines 53-63 (loadAvailableWordlists)
3. **Verify**: Lines 569-590 (custom section render)
4. **Test**: Open browser console, run debug commands above
5. **Goal**: Make `.custom-section` appear in DOM

Good luck! 🍀

---

**Questions or updates?** Add them to this file with a timestamp.
