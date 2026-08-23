# Theme List Implementation Plan

**Date**: December 28, 2025
**Feature**: Custom Wordlist Selection + Theme List Priority
**Status**: Planning Phase

---

## Overview

Implement a two-phase feature enhancement:

**Phase 1**: Enable selection of custom wordlists in the web UI autofill panel
**Phase 2**: Allow designation of one wordlist as "theme list" with mandatory inclusion priority

---

## Current State

### ✅ What Works
- Backend supports custom wordlists via `resolve_wordlist_paths()`
- Users can upload custom wordlists via Word Lists panel
- Custom wordlists are stored in `data/wordlists/custom/`
- CLI can use custom wordlists with `-w` flag

### ❌ What's Broken
- AutofillPanel has hardcoded wordlist checkboxes
- Custom wordlists cannot be selected in web UI
- No way to prioritize specific wordlists
- Uploaded wordlists are essentially useless in web UI

---

## Phase 1: Enable Custom Wordlist Selection

### Goals
1. Dynamically load and display all available wordlists
2. Allow users to select custom wordlists for autofill
3. Maintain backward compatibility with existing hardcoded lists
4. Clean, organized UI with categories

### Implementation Steps

#### 1.1: Modify AutofillPanel.jsx

**File**: `src/components/AutofillPanel.jsx`

**Changes**:
```javascript
// Add state for available wordlists
const [availableWordlists, setAvailableWordlists] = useState({
  built_in: [],
  custom: []
});

// Load wordlists on component mount
useEffect(() => {
  loadAvailableWordlists();
}, []);

const loadAvailableWordlists = async () => {
  try {
    const response = await axios.get('/api/wordlists');
    const wordlists = response.data.wordlists;

    // Separate built-in from custom
    const builtIn = wordlists.filter(wl => wl.category !== 'custom');
    const custom = wordlists.filter(wl => wl.category === 'custom');

    setAvailableWordlists({ built_in: builtIn, custom: custom });
  } catch (error) {
    console.error('Failed to load wordlists:', error);
  }
};
```

#### 1.2: Update Wordlist Selection UI

**Replace hardcoded checkboxes** (lines 507-589) with:

```jsx
<div className="option-group">
  <label>Word Lists</label>

  {/* Built-in wordlists */}
  <div className="wordlist-section">
    <h4>Built-in Lists</h4>
    <div className="wordlist-checkboxes">
      {availableWordlists.built_in.map(wl => (
        <label key={wl.key}>
          <input
            type="checkbox"
            checked={options.wordlists.includes(wl.key)}
            onChange={(e) => {
              const lists = e.target.checked
                ? [...options.wordlists, wl.key]
                : options.wordlists.filter(l => l !== wl.key);
              handleOptionChange('wordlists', lists);
            }}
          />
          {wl.name} ({wl.word_count} words)
        </label>
      ))}
    </div>
  </div>

  {/* Custom wordlists */}
  {availableWordlists.custom.length > 0 && (
    <div className="wordlist-section custom-section">
      <h4>🎨 Custom Lists</h4>
      <div className="wordlist-checkboxes">
        {availableWordlists.custom.map(wl => (
          <label key={wl.key}>
            <input
              type="checkbox"
              checked={options.wordlists.includes(wl.key)}
              onChange={(e) => {
                const lists = e.target.checked
                  ? [...options.wordlists, wl.key]
                  : options.wordlists.filter(l => l !== wl.key);
                handleOptionChange('wordlists', lists);
              }}
            />
            {wl.name} ({wl.word_count} words)
          </label>
        ))}
      </div>
    </div>
  )}
</div>
```

#### 1.3: Add CSS Styling

**File**: `src/components/AutofillPanel.scss`

```scss
.wordlist-section {
  margin-bottom: 1rem;

  h4 {
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: #555;
  }

  &.custom-section {
    border-top: 1px solid #e0e0e0;
    padding-top: 0.75rem;

    h4 {
      color: #7b1fa2;
    }
  }
}

.wordlist-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;

  label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem;
    border-radius: 4px;
    transition: background-color 0.2s;

    &:hover {
      background-color: #f5f5f5;
    }

    input[type="checkbox"] {
      margin: 0;
    }
  }
}
```

#### 1.4: Testing

**Test Cases**:
1. Upload custom wordlist via Word Lists panel
2. Navigate to Autofill panel
3. Verify custom list appears in "Custom Lists" section
4. Select custom list + comprehensive list
5. Run autofill
6. Verify both wordlists are used (check logs/output)

**Expected Result**: Custom wordlist words should appear in filled grid

---

## Phase 2: Theme List Designation

### Goals
1. Allow user to mark ONE wordlist as "theme list"
2. Backend prioritizes theme list words (tries to use as many as possible)
3. Visual indication of which list is designated as theme list
4. Clear UX for theme list selection

### Conceptual Design

**What "Theme List" Means**:
- The autofill algorithm will **prefer** words from the theme list when multiple candidates exist
- Algorithm will **try harder** to use theme list words (relaxed constraints if needed)
- Example use case: Halloween puzzle with Halloween-themed wordlist

**Implementation Strategy**:
1. Add scoring bonus for theme list words (+50 to score)
2. In CSP solver, prioritize slots where theme list has candidates
3. Track theme list usage and report to user ("Used 15/20 theme words")

### Implementation Steps

#### 2.1: Update AutofillPanel State

```javascript
const [options, setOptions] = useState({
  minScore: 50,
  preferPersonalWords: true,
  timeout: 300,
  wordlists: ['comprehensive'],
  themeList: null,  // NEW: designated theme list key
  algorithm: 'beam',
  adaptiveMode: false,
  maxAdaptations: 3
});
```

#### 2.2: Add Theme List Selection UI

Add radio buttons in custom wordlists section:

```jsx
{availableWordlists.custom.length > 0 && (
  <div className="wordlist-section custom-section">
    <h4>🎨 Custom Lists</h4>
    <div className="wordlist-checkboxes">
      {availableWordlists.custom.map(wl => (
        <div key={wl.key} className="wordlist-item-container">
          <label className="wordlist-checkbox">
            <input
              type="checkbox"
              checked={options.wordlists.includes(wl.key)}
              onChange={(e) => {
                const lists = e.target.checked
                  ? [...options.wordlists, wl.key]
                  : options.wordlists.filter(l => l !== wl.key);
                handleOptionChange('wordlists', lists);

                // If unchecking and it's the theme list, clear theme designation
                if (!e.target.checked && options.themeList === wl.key) {
                  handleOptionChange('themeList', null);
                }
              }}
            />
            {wl.name} ({wl.word_count} words)
          </label>

          {/* Theme designation radio button */}
          {options.wordlists.includes(wl.key) && (
            <label className="theme-designation">
              <input
                type="radio"
                name="themeList"
                checked={options.themeList === wl.key}
                onChange={() => handleOptionChange('themeList', wl.key)}
              />
              <span className="theme-label">⭐ Theme List</span>
            </label>
          )}
        </div>
      ))}
    </div>

    {options.themeList && (
      <div className="theme-info">
        <strong>Theme List Active:</strong> {availableWordlists.custom.find(w => w.key === options.themeList)?.name}
        <p className="help-text">
          The autofill algorithm will prioritize words from this list and try to use as many as possible.
        </p>
      </div>
    )}
  </div>
)}
```

#### 2.3: Backend Support - Add Theme List Parameter

**File**: `backend/api/routes.py`

Modify autofill endpoints to accept `theme_wordlist`:

```python
@app.route('/api/fill/stream', methods=['POST'])
def fill_grid_stream():
    # ... existing code ...

    # Get theme wordlist if specified
    theme_wordlist = data.get('theme_wordlist')  # NEW

    # Resolve wordlist paths
    wordlist_names = data.get("wordlists", ["comprehensive"])
    wordlist_paths = resolve_wordlist_paths(wordlist_names)

    # Build CLI command
    cmd_args = [
        sys.executable, '-m', 'cli.src.cli', 'fill',
        temp_grid_file,
        '--timeout', str(timeout),
        '--min-score', str(min_score),
        '--algorithm', algorithm,
    ]

    for wp in wordlist_paths:
        cmd_args.extend(["--wordlists", wp])

    # Add theme wordlist flag if specified
    if theme_wordlist:
        theme_path = resolve_wordlist_paths([theme_wordlist])
        if theme_path:
            cmd_args.extend(["--theme-wordlist", theme_path[0]])  # NEW FLAG

    # ... rest of code ...
```

#### 2.4: CLI Support - Add Theme List Flag

**File**: `cli/src/cli.py`

Add new CLI flag:

```python
@click.option(
    '--theme-wordlist',
    type=click.Path(exists=True),
    help='Wordlist to prioritize (theme list) - algorithm will prefer these words'
)
def fill(grid_file, wordlists, theme_wordlist, ...):
    # ... existing code ...

    # Load theme wordlist separately
    theme_words = set()
    if theme_wordlist:
        with open(theme_wordlist, 'r') as f:
            theme_words = {line.strip().upper() for line in f if line.strip()}

        print(f"  ⭐ Theme wordlist: {theme_wordlist}")
        print(f"  Loaded {len(theme_words)} theme words")

    # Pass to autofill algorithm
    result = autofill.fill(
        grid=grid,
        word_list=word_list,
        theme_words=theme_words,  # NEW PARAMETER
        # ... other params ...
    )
```

#### 2.5: Modify Autofill Algorithm

**File**: `cli/src/fill/hybrid_autofill.py` (and other autofill classes)

```python
class HybridAutofill:
    def __init__(self, word_list, theme_words=None, ...):
        self.word_list = word_list
        self.theme_words = theme_words or set()  # NEW
        # ... existing init ...

    def _score_candidate(self, word, slot):
        """Score a candidate word for a slot."""
        base_score = self.word_list.get_score(word)

        # Add bonus for theme words
        if word in self.theme_words:
            base_score += 50  # Significant bonus

        return base_score

    def _get_candidates(self, slot):
        """Get candidate words for a slot, prioritizing theme words."""
        pattern = slot.get_pattern()
        candidates = self.word_list.find_matches(pattern)

        # Sort: theme words first, then by score
        candidates.sort(key=lambda w: (
            w not in self.theme_words,  # False (theme) sorts before True (non-theme)
            -self._score_candidate(w, slot)  # Then by score descending
        ))

        return candidates
```

#### 2.6: Add Theme Usage Reporting

After autofill completes, report theme word usage:

```python
def fill(...):
    # ... autofill runs ...

    if theme_words:
        used_theme_words = set()
        for slot in filled_slots:
            if slot.word in theme_words:
                used_theme_words.add(slot.word)

        print(f"\n⭐ Theme Word Usage:")
        print(f"  Used {len(used_theme_words)}/{len(theme_words)} theme words")
        print(f"  Theme words used: {', '.join(sorted(used_theme_words))}")
```

#### 2.7: UI - Display Theme Usage Results

After autofill completes in web UI, show theme statistics:

```jsx
{progress.status === 'complete' && options.themeList && (
  <div className="theme-results">
    <h4>⭐ Theme List Results</h4>
    <div className="theme-stats">
      <span>Theme words used: {progress.theme_words_used || 0} / {progress.theme_words_total || 0}</span>
      {progress.theme_words && (
        <div className="theme-words-list">
          {progress.theme_words.map(word => (
            <span key={word} className="theme-word">{word}</span>
          ))}
        </div>
      )}
    </div>
  </div>
)}
```

---

## Testing Plan

### Phase 1 Testing

**Test 1: Custom List Selection**
1. Upload custom wordlist with 10 words
2. Navigate to Autofill panel
3. Verify custom list appears
4. Select custom list + comprehensive
5. Run autofill on small 5×5 grid
6. Verify custom words appear in fill

**Test 2: Multiple Custom Lists**
1. Upload 2 custom wordlists
2. Select both + comprehensive
3. Run autofill
4. Verify words from all 3 lists used

### Phase 2 Testing

**Test 3: Theme List Priority**
1. Create themed wordlist (e.g., "HALLOWEEN", "PUMPKIN", "GHOST", "WITCH")
2. Upload as custom list
3. Mark as theme list
4. Run autofill on 7×7 grid
5. Verify theme words appear preferentially

**Test 4: Theme Usage Reporting**
1. Run test 3
2. Check autofill results panel
3. Verify "Theme words used: X/Y" appears
4. Verify list of used theme words displayed

**Test 5: Theme List Edge Cases**
1. Uncheck theme list → verify theme designation cleared
2. Change theme list selection → verify only one can be theme
3. No theme list selected → verify autofill works normally

---

## Success Criteria

### Phase 1
- ✅ Custom wordlists appear in AutofillPanel
- ✅ Can select/deselect custom wordlists
- ✅ Selected custom wordlists are used during autofill
- ✅ UI is clean and organized
- ✅ No regressions in existing functionality

### Phase 2
- ✅ Can designate one wordlist as "theme list"
- ✅ Theme words receive priority during autofill
- ✅ Theme usage is reported after autofill
- ✅ UI clearly indicates theme list status
- ✅ Theme list works with all autofill algorithms

---

## Timeline Estimate

**Phase 1**: 2-3 hours
- Frontend changes: 1.5 hours
- Testing: 30-60 minutes

**Phase 2**: 4-5 hours
- UI changes: 1 hour
- Backend API changes: 1 hour
- CLI flag support: 30 minutes
- Autofill algorithm modifications: 1.5 hours
- Testing: 1 hour

**Total**: 6-8 hours for complete feature

---

## Risks and Mitigation

**Risk 1**: Performance impact of theme word prioritization
- Mitigation: Only applies sorting/bonus, minimal overhead
- Testing: Benchmark autofill with/without theme list

**Risk 2**: Theme words don't fit grid constraints
- Mitigation: Theme words are PREFERRED not MANDATORY (for Phase 1)
- Future: Could add "strict mode" for mandatory inclusion

**Risk 3**: UI becomes cluttered with many custom lists
- Mitigation: Use collapsible sections if >5 custom lists
- Add search/filter if >10 custom lists

---

## Future Enhancements (Phase 3+)

1. **Strict Theme Mode**: REQUIRE minimum number of theme words
2. **Theme Word Highlighting**: Highlight theme words in filled grid
3. **Theme List Templates**: Provide pre-made themed lists (holidays, sports, etc.)
4. **Multi-Theme Support**: Allow multiple theme lists with different priorities
5. **Theme Conflict Resolution**: Smart handling when theme words conflict

---

**Status**: Ready to implement Phase 1
**Next Step**: Modify AutofillPanel.jsx to load wordlists dynamically
