# Frontend API Client Audit - Phase 1.4

**Date**: December 27, 2025
**Purpose**: Identify all fetch() calls that should be migrated to axios for consistency

---

## Executive Summary

**Total fetch() calls found**: 11 across 4 components
**Already using axios**: 2 components (PatternMatcher, WordListPanel)
**Need migration**: 4 components with 11 fetch calls

**Reason for standardization**:
- Cleaner syntax (no manual JSON parsing, headers)
- Better error handling (err.response?.data?.error pattern)
- Consistency across codebase
- Automatic JSON serialization/deserialization

---

## Current State

### ✅ Already Using axios (2 components)

**1. PatternMatcher.jsx**
```javascript
import axios from 'axios';

// Example usage:
const response = await axios.post('/api/pattern/with-progress', {
  pattern: pattern.toUpperCase(),
  max_results: 50,
  wordlists: selectedWordlists,
  algorithm: algorithm
});

const { task_id } = response.data;
```

**2. WordListPanel.jsx**
```javascript
import axios from 'axios';

// Example usage:
const response = await axios.get('/api/wordlists');
setAvailableWordlists(response.data.wordlists);
```

### ❌ Still Using fetch() (4 components, 11 calls)

---

## Components Requiring Migration

### 1. App.jsx (2 fetch calls)

**Location**: `src/App.jsx`

**Fetch Call #1** - Line 193: Autofill Initiation
```javascript
// CURRENT (fetch):
const initResponse = await fetch('/api/fill/with-progress', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    grid: exportGrid(),
    wordlists: autofillConfig.wordlists,
    algorithm: autofillConfig.algorithm,
    min_score: autofillConfig.minScore,
    timeout: autofillConfig.timeout,
    theme_entries: autofillConfig.preserveTheme ? getThemeEntries() : []
  })
});

if (!initResponse.ok) {
  throw new Error('Failed to start autofill');
}

const { task_id } = await initResponse.json();

// RECOMMENDED (axios):
const initResponse = await axios.post('/api/fill/with-progress', {
  grid: exportGrid(),
  wordlists: autofillConfig.wordlists,
  algorithm: autofillConfig.algorithm,
  min_score: autofillConfig.minScore,
  timeout: autofillConfig.timeout,
  theme_entries: autofillConfig.preserveTheme ? getThemeEntries() : []
});

const { task_id } = initResponse.data;
```

**Fetch Call #2** - Line 346: Cancel Autofill (fire-and-forget)
```javascript
// CURRENT (fetch):
fetch(`/api/cancel/${currentTaskId}`, { method: 'POST' }).catch(err => {
  console.error('Cancel request failed:', err);
});

// RECOMMENDED (axios):
axios.post(`/api/cancel/${currentTaskId}`).catch(err => {
  console.error('Cancel request failed:', err);
});
```

**Migration Complexity**: Low
- **Lines to change**: ~15-20 lines
- **Error handling**: Already uses try/catch, just needs to update error extraction
- **Estimated time**: 15 minutes

---

### 2. AutofillPanel.jsx (4 fetch calls)

**Location**: `src/components/AutofillPanel.jsx`

**Fetch Call #1** - Line 48: Get State
```javascript
// CURRENT (fetch):
const response = await fetch(`/api/fill/state/${taskId}`);
if (!response.ok) {
  throw new Error('Failed to load state');
}
const stateData = await response.json();

// RECOMMENDED (axios):
const response = await axios.get(`/api/fill/state/${taskId}`);
const stateData = response.data;
```

**Fetch Call #2** - Line 71: Pause Autofill
```javascript
// CURRENT (fetch):
const response = await fetch(`/api/fill/pause/${currentTaskId}`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' }
});

if (!response.ok) {
  throw new Error('Failed to pause');
}

const result = await response.json();

// RECOMMENDED (axios):
const response = await axios.post(`/api/fill/pause/${currentTaskId}`);
const result = response.data;
```

**Fetch Call #3** - Line 104: Resume Autofill
```javascript
// CURRENT (fetch):
const response = await fetch('/api/fill/resume', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ state: resumeState })
});

if (!response.ok) {
  throw new Error('Failed to resume');
}

const { task_id } = await response.json();

// RECOMMENDED (axios):
const response = await axios.post('/api/fill/resume', {
  state: resumeState
});

const { task_id } = response.data;
```

**Fetch Call #4** - Line 152: Delete State (fire-and-forget)
```javascript
// CURRENT (fetch):
fetch(`/api/fill/state/${pausedTaskId}`, { method: 'DELETE' })
  .catch(err => console.error('Failed to clean up state:', err));

// RECOMMENDED (axios):
axios.delete(`/api/fill/state/${pausedTaskId}`)
  .catch(err => console.error('Failed to clean up state:', err));
```

**Migration Complexity**: Low
- **Lines to change**: ~25-30 lines
- **Error handling**: Already uses try/catch patterns
- **Estimated time**: 20 minutes

---

### 3. ThemeWordsPanel.jsx (3 fetch calls)

**Location**: `src/components/ThemeWordsPanel.jsx`

**Fetch Call #1** - Line 49: Upload Theme Entries
```javascript
// CURRENT (fetch):
const response = await fetch('/api/theme/upload', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ entries: parsedEntries })
});

if (!response.ok) {
  const error = await response.json();
  throw new Error(error.error || 'Upload failed');
}

const data = await response.json();

// RECOMMENDED (axios):
const response = await axios.post('/api/theme/upload', {
  entries: parsedEntries
});

const data = response.data;

// Error handling (in catch block):
catch (err) {
  const errorMsg = err.response?.data?.error || 'Upload failed';
  setError(errorMsg);
}
```

**Fetch Call #2** - Line 97: Suggest Placements
```javascript
// CURRENT (fetch):
const response = await fetch('/api/theme/suggest-placements', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    grid: exportedGrid,
    entries: themeEntries
  })
});

if (!response.ok) {
  throw new Error('Failed to get suggestions');
}

const data = await response.json();

// RECOMMENDED (axios):
const response = await axios.post('/api/theme/suggest-placements', {
  grid: exportedGrid,
  entries: themeEntries
});

const data = response.data;
```

**Fetch Call #3** - Line 130: Apply Placement
```javascript
// CURRENT (fetch):
const response = await fetch('/api/theme/apply-placement', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    grid: exportedGrid,
    placement: placement
  })
});

if (!response.ok) {
  throw new Error('Failed to apply placement');
}

const result = await response.json();

// RECOMMENDED (axios):
const response = await axios.post('/api/theme/apply-placement', {
  grid: exportedGrid,
  placement: placement
});

const result = response.data;
```

**Migration Complexity**: Low
- **Lines to change**: ~20-25 lines
- **Error handling**: Needs update to use err.response?.data?.error pattern
- **Estimated time**: 20 minutes

---

### 4. BlackSquareSuggestions.jsx (2 fetch calls)

**Location**: `src/components/BlackSquareSuggestions.jsx`

**Fetch Call #1** - Line 26: Get Black Square Suggestions
```javascript
// CURRENT (fetch):
const response = await fetch('/api/grid/suggest-black-square', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ grid: exportedGrid })
});

if (!response.ok) {
  throw new Error('Failed to get suggestions');
}

const data = await response.json();

// RECOMMENDED (axios):
const response = await axios.post('/api/grid/suggest-black-square', {
  grid: exportedGrid
});

const data = response.data;
```

**Fetch Call #2** - Line 60: Apply Black Squares
```javascript
// CURRENT (fetch):
const response = await fetch('/api/grid/apply-black-squares', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    grid: exportedGrid,
    positions: suggestion.positions
  })
});

if (!response.ok) {
  throw new Error('Failed to apply suggestion');
}

const result = await response.json();

// RECOMMENDED (axios):
const response = await axios.post('/api/grid/apply-black-squares', {
  grid: exportedGrid,
  positions: suggestion.positions
});

const result = response.data;
```

**Migration Complexity**: Low
- **Lines to change**: ~15-20 lines
- **Error handling**: Already uses try/catch
- **Estimated time**: 15 minutes

---

## Migration Summary

| Component | Fetch Calls | Lines to Change | Est. Time | Priority |
|-----------|-------------|-----------------|-----------|----------|
| App.jsx | 2 | 15-20 | 15 min | High (core autofill) |
| AutofillPanel.jsx | 4 | 25-30 | 20 min | High (pause/resume) |
| ThemeWordsPanel.jsx | 3 | 20-25 | 20 min | Medium (theme feature) |
| BlackSquareSuggestions.jsx | 2 | 15-20 | 15 min | Medium (suggestions) |
| **TOTAL** | **11** | **75-95** | **70 min** | - |

**Total estimated migration time**: 1-1.5 hours

---

## Axios Pattern Reference

### Import Statement
```javascript
import axios from 'axios';
```

### GET Request
```javascript
try {
  const response = await axios.get('/api/endpoint');
  const data = response.data;  // Already parsed JSON
  // Use data...
} catch (err) {
  const errorMsg = err.response?.data?.error || 'Request failed';
  console.error(errorMsg);
}
```

### POST Request
```javascript
try {
  const response = await axios.post('/api/endpoint', {
    field1: value1,
    field2: value2
  });
  const data = response.data;  // Already parsed JSON
  // Use data...
} catch (err) {
  const errorMsg = err.response?.data?.error || 'Request failed';
  console.error(errorMsg);
}
```

### DELETE Request
```javascript
try {
  const response = await axios.delete(`/api/endpoint/${id}`);
  const data = response.data;
} catch (err) {
  console.error('Delete failed:', err);
}
```

### Fire-and-Forget Request (no response needed)
```javascript
axios.post('/api/endpoint', data)
  .catch(err => console.error('Request failed:', err));
```

---

## Benefits of Migration

### Code Reduction
**Before (fetch)**:
```javascript
const response = await fetch('/api/endpoint', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ data: value })
});

if (!response.ok) {
  throw new Error('Request failed');
}

const result = await response.json();
```
**9 lines**

**After (axios)**:
```javascript
const response = await axios.post('/api/endpoint', { data: value });
const result = response.data;
```
**2 lines** (78% reduction)

### Better Error Handling
**Before (fetch)**:
```javascript
try {
  const response = await fetch(...);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed');
  }
  const data = await response.json();
} catch (err) {
  console.error('Request failed:', err.message);
}
```

**After (axios)**:
```javascript
try {
  const response = await axios.post(...);
  const data = response.data;
} catch (err) {
  const errorMsg = err.response?.data?.error || 'Failed';
  console.error('Request failed:', errorMsg);
}
```

### Consistency
- All API calls use same pattern
- Error handling is standardized
- Easier to maintain and debug
- New developers only learn one pattern

---

## Implementation Plan (Phase 3.2)

### Step 1: Add axios import (all 4 files)
```javascript
import axios from 'axios';
```

### Step 2: Migrate by component (priority order)

**1. App.jsx** (15 min)
- Migrate autofill initiation fetch
- Migrate cancel fetch
- Update error handling

**2. AutofillPanel.jsx** (20 min)
- Migrate 4 pause/resume/state fetches
- Update error handling to use err.response?.data?.error

**3. ThemeWordsPanel.jsx** (20 min)
- Migrate 3 theme-related fetches
- Update error handling

**4. BlackSquareSuggestions.jsx** (15 min)
- Migrate 2 suggestion fetches
- Update error handling

### Step 3: Test each component (15 min)
- Verify all API calls work correctly
- Check error handling displays properly
- Test fire-and-forget calls (delete, cancel)

### Step 4: Remove unused code (5 min)
- Remove any fetch-specific helper functions if they exist
- Ensure no fetch() calls remain in API code

**Total time**: ~1.5 hours

---

## Testing Checklist

After migration, verify:

- [ ] **App.jsx**: Autofill starts correctly, cancel works
- [ ] **AutofillPanel.jsx**: Pause/resume/state operations work
- [ ] **ThemeWordsPanel.jsx**: Theme upload, suggestions, placement work
- [ ] **BlackSquareSuggestions.jsx**: Suggestions load and apply correctly
- [ ] **Error handling**: Errors display correctly in UI
- [ ] **Network tab**: Requests have correct headers and payloads
- [ ] **No console errors**: Clean console on all operations

---

## Risk Assessment

**Risk Level**: Low

**Why Low Risk**:
1. Axios already in use (2 components working)
2. Simple 1:1 replacement (no logic changes)
3. Same HTTP methods (GET, POST, DELETE)
4. Same endpoints (no API changes)
5. Easy to test (just check each feature works)

**Potential Issues**:
- None expected - axios is well-tested and widely used
- If issues arise, can revert individual components

---

**Completed**: Phase 1.4 - axios vs fetch Audit ✅
**Time**: ~30 minutes
**Output**:
- 11 fetch calls identified across 4 components
- Migration patterns documented
- Estimated 1-1.5 hours to migrate all components
- **No blockers** - migration can proceed in Phase 3.2
