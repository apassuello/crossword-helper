# New Endpoints Documentation - To Be Added to BACKEND_SPEC.md

This document contains documentation for 17 endpoints that need to be added to BACKEND_SPEC.md.

---

## Section 1: Core Operations (routes.py)

### POST /api/pattern/with-progress

**Purpose:** Pattern search with real-time progress updates via SSE

**Request:** Same as `/api/pattern`

```json
{
  "pattern": "C?T",
  "max_results": 50,
  "wordlists": ["comprehensive"],
  "algorithm": "trie"
}
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "progress_url": "/api/progress/550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Code:** `202 Accepted` (task started)

**Usage:**
1. POST to `/api/pattern/with-progress` → get `task_id`
2. Connect to SSE endpoint `/api/progress/{task_id}`
3. Receive real-time progress events
4. Final event contains search results

**See:** [Real-Time Progress Tracking](#real-time-progress-tracking-sse) for SSE details

---

## Section 2: Grid Helper Routes (grid_routes.py)

### POST /api/grid/apply-black-squares

**Purpose:** Apply symmetric black square placements to grid

**Request:**
```json
{
  "grid": [[...], ...],
  "primary": {"row": 0, "col": 7},
  "symmetric": {"row": 14, "col": 7}
}
```

**Response:**
```json
{
  "grid": [[...], ...],
  "applied": true,
  "positions": [
    {"row": 0, "col": 7},
    {"row": 14, "col": 7}
  ]
}
```

**Status Codes:**
- `200 OK` - Black squares applied successfully
- `400 Bad Request` - Missing grid or positions
- `500 Internal Server Error` - Application failed

**Frontend Usage:** `BlackSquareSuggestions.jsx` - Apply suggested black square placement

---

### POST /api/grid/validate

**Purpose:** Validate grid quality and get statistics

**Request:**
```json
{
  "grid": [[...], ...],
  "grid_size": 15
}
```

**Response:**
```json
{
  "valid": true,
  "word_count": 76,
  "black_square_count": 38,
  "black_square_percentage": 16.8,
  "word_count_range": [70, 80],
  "warnings": [],
  "suggestions": [
    "Low word count (68). Try adding black squares to reach 70-80."
  ]
}
```

**Validation Checks:**
- Word count within acceptable range for grid size
- Black square percentage (~16-18% is ideal)
- Grid structure validity

**Status Codes:**
- `200 OK` - Validation complete (includes `valid` field)
- `400 Bad Request` - Missing grid
- `500 Internal Server Error` - Validation failed

**Frontend Usage:** `App.jsx` - Validate grid before operations

---

## Section 3: Theme Routes (theme_routes.py)

### POST /api/theme/validate

**Purpose:** Validate theme entries before placement

**Request:**
```json
{
  "entries": ["THEMEWORD1", "THEMEWORD2"],
  "grid_size": 15
}
```

**Response:**
```json
{
  "valid": true,
  "entries": [
    {
      "word": "THEMEWORD1",
      "length": 10,
      "valid": true,
      "issues": []
    },
    {
      "word": "THEMEWORD2",
      "length": 10,
      "valid": false,
      "issues": ["Too long for 15x15 grid (max 15 letters)"]
    }
  ],
  "warnings": ["Entry 2 is too long"]
}
```

**Validation Rules:**
- Words must fit in grid (length ≤ grid_size)
- Words must be uppercase letters only
- No duplicate entries

**Status Codes:**
- `200 OK` - Validation complete
- `400 Bad Request` - Missing entries or grid_size
- `500 Internal Server Error` - Validation failed

**Frontend Usage:** `ThemeWordsPanel.jsx` - Validate before suggesting placements

---

### POST /api/theme/apply-placement

**Purpose:** Apply a suggested theme word placement to grid

**Request:**
```json
{
  "grid": [[...], ...],
  "placement": {
    "word": "THEMEWORD",
    "row": 0,
    "col": 0,
    "direction": "across",
    "length": 9
  }
}
```

**Response:**
```json
{
  "grid": [[...], ...],
  "applied": true,
  "placement": {
    "word": "THEMEWORD",
    "row": 0,
    "col": 0,
    "direction": "across",
    "locked_cells": [
      {"row": 0, "col": 0},
      {"row": 0, "col": 1},
      ...
    ]
  },
  "conflicts": []
}
```

**Behavior:**
- Places word letters in grid
- Sets `isThemeLocked: true` on all cells
- Detects and reports conflicts with existing letters
- Preserves existing theme locks

**Status Codes:**
- `200 OK` - Placement applied
- `400 Bad Request` - Missing grid or placement
- `409 Conflict` - Placement conflicts with existing letters
- `500 Internal Server Error` - Application failed

**Frontend Usage:** `ThemeWordsPanel.jsx` - Apply user-selected placement

---

## Section 4: Pause/Resume Routes (pause_resume_routes.py)

### GET /api/fill/state/:task_id

**Purpose:** Get saved autofill state details

**Request:**
```bash
curl http://localhost:5000/api/fill/state/task_abc123
```

**Response:**
```json
{
  "task_id": "task_abc123",
  "timestamp": "2025-12-27T10:30:00Z",
  "slots_filled": 38,
  "total_slots": 76,
  "progress": 50,
  "state_size_kb": 245,
  "grid_preview": [[...], ...],
  "options": {
    "min_score": 50,
    "timeout": 300,
    "wordlists": ["comprehensive"],
    "algorithm": "trie"
  }
}
```

**Status Codes:**
- `200 OK` - State found
- `404 Not Found` - No state exists for task_id
- `500 Internal Server Error` - Failed to read state

**Frontend Usage:** `AutofillPanel.jsx` - Check state before resuming

---

### DELETE /api/fill/state/:task_id

**Purpose:** Delete a saved autofill state

**Request:**
```bash
curl -X DELETE http://localhost:5000/api/fill/state/task_abc123
```

**Response:**
```json
{
  "success": true,
  "task_id": "task_abc123",
  "message": "State deleted successfully"
}
```

**Status Codes:**
- `200 OK` - State deleted
- `404 Not Found` - No state exists for task_id
- `500 Internal Server Error` - Deletion failed

**Cleanup:** Removes state file from disk

**Frontend Usage:** `AutofillPanel.jsx` - Clean up after resume completes

---

### GET /api/fill/states

**Purpose:** List all saved autofill states

**Request:**
```bash
curl http://localhost:5000/api/fill/states
```

**Response:**
```json
{
  "states": [
    {
      "task_id": "task_abc123",
      "timestamp": "2025-12-27T10:30:00Z",
      "slots_filled": 38,
      "total_slots": 76,
      "progress": 50,
      "age_seconds": 3600
    },
    {
      "task_id": "task_xyz789",
      "timestamp": "2025-12-27T09:15:00Z",
      "slots_filled": 60,
      "total_slots": 76,
      "progress": 79,
      "age_seconds": 8100
    }
  ],
  "count": 2,
  "total_size_kb": 512
}
```

**Sorting:** States sorted by timestamp (newest first)

**Status Codes:**
- `200 OK` - States listed (may be empty array)
- `500 Internal Server Error` - Failed to read states

**Frontend Usage:** `AutofillPanel.jsx` - Show available states to resume from

---

### POST /api/fill/states/cleanup

**Purpose:** Clean up old saved states (maintenance endpoint)

**Request:**
```json
{
  "max_age_hours": 24,
  "keep_count": 10
}
```

**Response:**
```json
{
  "deleted_count": 5,
  "deleted_states": [
    "task_old123",
    "task_old456",
    "task_old789"
  ],
  "remaining_count": 10,
  "freed_space_kb": 1250
}
```

**Cleanup Rules:**
- Delete states older than `max_age_hours`
- Keep at most `keep_count` newest states
- Both parameters optional (defaults: 24 hours, 20 states)

**Status Codes:**
- `200 OK` - Cleanup complete
- `400 Bad Request` - Invalid parameters
- `500 Internal Server Error` - Cleanup failed

**Frontend Usage:** Not currently used (maintenance endpoint)

---

### POST /api/fill/edit-summary

**Purpose:** Get summary of user edits made to paused grid

**Request:**
```json
{
  "original_grid": [[...], ...],
  "edited_grid": [[...], ...],
  "task_id": "task_abc123"
}
```

**Response:**
```json
{
  "changes": {
    "filled_cells": [
      {"row": 0, "col": 5, "old": ".", "new": "A"}
    ],
    "emptied_cells": [
      {"row": 1, "col": 3, "old": "B", "new": "."}
    ],
    "modified_cells": [
      {"row": 2, "col": 7, "old": "C", "new": "D"}
    ]
  },
  "summary": {
    "total_changes": 3,
    "filled_count": 1,
    "emptied_count": 1,
    "modified_count": 1
  },
  "impact": {
    "affected_across_words": 2,
    "affected_down_words": 3,
    "new_constraints": 5
  }
}
```

**Purpose:** Shows what changed when user edits paused grid before resume

**Status Codes:**
- `200 OK` - Summary generated
- `400 Bad Request` - Missing grids
- `500 Internal Server Error` - Analysis failed

**Frontend Usage:** `AutofillPanel.jsx` - Show edit impact before resuming

---

## Section 5: Wordlist Routes (wordlist_routes.py)

### GET /api/wordlists/:name

**Purpose:** Get details about a specific wordlist

**Request:**
```bash
curl http://localhost:5000/api/wordlists/comprehensive
```

**Response:**
```json
{
  "name": "comprehensive",
  "category": "core",
  "word_count": 412483,
  "description": "Comprehensive crossword word list",
  "tags": ["core", "comprehensive"],
  "file_size_kb": 4125,
  "last_modified": "2025-12-27T10:00:00Z",
  "length_distribution": {
    "3": 1245,
    "4": 3521,
    "5": 8932,
    ...
  }
}
```

**Status Codes:**
- `200 OK` - Wordlist found
- `404 Not Found` - Wordlist doesn't exist
- `500 Internal Server Error` - Failed to read wordlist

**Frontend Usage:** `WordListPanel.jsx` - Show wordlist details

---

### POST /api/wordlists/:name

**Purpose:** Create a new wordlist from words

**Request:**
```json
{
  "words": ["CAT", "DOG", "RAT"],
  "category": "custom",
  "description": "My custom wordlist",
  "tags": ["pets", "animals"]
}
```

**Response:**
```json
{
  "name": "my-custom-list",
  "created": true,
  "word_count": 3,
  "file_path": "data/wordlists/custom/my-custom-list.txt",
  "message": "Wordlist created successfully"
}
```

**Validation:**
- Name must be unique
- Words must be uppercase letters only
- Removes duplicate words

**Status Codes:**
- `201 Created` - Wordlist created
- `400 Bad Request` - Invalid words or missing data
- `409 Conflict` - Wordlist already exists
- `500 Internal Server Error` - Creation failed

**Frontend Usage:** `WordListPanel.jsx` - Create custom wordlist

---

### PUT /api/wordlists/:name

**Purpose:** Update an existing wordlist

**Request:**
```json
{
  "words": ["CAT", "DOG", "RAT", "BAT"],
  "description": "Updated description",
  "tags": ["pets", "animals", "updated"]
}
```

**Response:**
```json
{
  "name": "my-custom-list",
  "updated": true,
  "word_count": 4,
  "changes": {
    "added": ["BAT"],
    "removed": [],
    "previous_count": 3
  },
  "message": "Wordlist updated successfully"
}
```

**Behavior:**
- Replaces entire wordlist contents
- Updates metadata (description, tags)
- Cannot update core wordlists (protected)

**Status Codes:**
- `200 OK` - Wordlist updated
- `400 Bad Request` - Invalid words or missing data
- `403 Forbidden` - Cannot modify core wordlist
- `404 Not Found` - Wordlist doesn't exist
- `500 Internal Server Error` - Update failed

**Frontend Usage:** `WordListPanel.jsx` - Add words to existing list

---

### DELETE /api/wordlists/:name

**Purpose:** Delete a wordlist

**Request:**
```bash
curl -X DELETE http://localhost:5000/api/wordlists/my-custom-list
```

**Response:**
```json
{
  "name": "my-custom-list",
  "deleted": true,
  "word_count": 4,
  "message": "Wordlist deleted successfully"
}
```

**Protection:** Cannot delete core wordlists

**Status Codes:**
- `200 OK` - Wordlist deleted
- `403 Forbidden` - Cannot delete core wordlist
- `404 Not Found` - Wordlist doesn't exist
- `500 Internal Server Error` - Deletion failed

**Frontend Usage:** `WordListPanel.jsx` - Delete custom wordlist

---

### GET /api/wordlists/:name/stats

**Purpose:** Get detailed statistics for a wordlist

**Request:**
```bash
curl http://localhost:5000/api/wordlists/comprehensive/stats
```

**Response:**
```json
{
  "name": "comprehensive",
  "word_count": 412483,
  "length_distribution": {
    "3": 1245,
    "4": 3521,
    "5": 8932,
    "6": 15234,
    ...
  },
  "letter_frequency": {
    "A": 45231,
    "B": 8932,
    "C": 12456,
    ...
  },
  "avg_word_length": 8.2,
  "min_length": 3,
  "max_length": 21,
  "unique_letters": 26,
  "most_common_words": [
    {"word": "THE", "count": 1},
    {"word": "AND", "count": 1}
  ]
}
```

**Performance:** Cached for 5 minutes to avoid recomputation

**Status Codes:**
- `200 OK` - Statistics generated
- `404 Not Found` - Wordlist doesn't exist
- `500 Internal Server Error` - Stats generation failed

**Frontend Usage:** `WordListPanel.jsx` - Show detailed wordlist statistics

---

### POST /api/wordlists/search

**Purpose:** Search across multiple wordlists with filters

**Request:**
```json
{
  "query": "CAT",
  "wordlists": ["comprehensive", "crosswordese"],
  "filters": {
    "min_length": 3,
    "max_length": 5,
    "starts_with": "C",
    "ends_with": "T",
    "contains": "A"
  },
  "max_results": 100
}
```

**Response:**
```json
{
  "results": [
    {
      "word": "CAT",
      "wordlist": "comprehensive",
      "length": 3,
      "score": 85
    },
    {
      "word": "CAST",
      "wordlist": "comprehensive",
      "length": 4,
      "score": 78
    }
  ],
  "query": "CAT",
  "total_found": 2,
  "wordlists_searched": ["comprehensive", "crosswordese"]
}
```

**Features:**
- Searches multiple wordlists simultaneously
- Applies filters to narrow results
- Removes duplicates across wordlists
- Sorts by score (word quality)

**Status Codes:**
- `200 OK` - Search complete
- `400 Bad Request` - Invalid query or filters
- `500 Internal Server Error` - Search failed

**Frontend Usage:** Not currently used (API capability)

---

### POST /api/wordlists/import

**Purpose:** Import wordlist from uploaded file

**Request:**
```json
{
  "filename": "my-words.txt",
  "content": "CAT\nDOG\nRAT\nBAT",
  "category": "custom",
  "description": "Imported from file",
  "tags": ["imported"]
}
```

**Response:**
```json
{
  "name": "my-words",
  "created": true,
  "word_count": 4,
  "imported": 4,
  "duplicates_removed": 0,
  "invalid_words": [],
  "message": "Wordlist imported successfully"
}
```

**Processing:**
- Parses file content (one word per line)
- Converts to uppercase
- Removes duplicates
- Validates words (letters only)
- Filters out invalid entries

**Supported Formats:**
- Plain text (.txt) - one word per line
- CSV (.csv) - first column is word
- JSON (.json) - array of words

**Status Codes:**
- `201 Created` - Wordlist imported
- `400 Bad Request` - Invalid file or content
- `409 Conflict` - Wordlist name already exists
- `500 Internal Server Error` - Import failed

**Frontend Usage:** `WordListPanel.jsx` - Upload wordlist file

---

**END OF NEW ENDPOINTS DOCUMENTATION**

These 17 endpoints should be added to BACKEND_SPEC.md in their respective sections:
- 1 in Core Operations (after POST /api/fill/with-progress)
- 2 in Grid Helper Routes (after POST /api/grid/suggest-black-square)
- 2 in Theme Routes (after POST /api/theme/suggest-placements)
- 5 in Pause/Resume Routes (after POST /api/fill/resume)
- 7 in Wordlist Routes (after GET /api/wordlists)
