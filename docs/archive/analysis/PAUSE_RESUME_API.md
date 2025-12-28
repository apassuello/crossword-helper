# Pause/Resume API Documentation

**Version:** 1.0
**Last Updated:** 2025-12-26

This document describes the pause/resume API endpoints for the crossword autofill feature, enabling users to pause long-running autofill operations, manually edit the grid, and resume from the exact algorithmic position.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Endpoints](#endpoints)
   - [Pause Autofill](#pause-autofill)
   - [Resume Autofill](#resume-autofill)
   - [Get Saved State](#get-saved-state)
   - [Delete Saved State](#delete-saved-state)
   - [List Saved States](#list-saved-states)
   - [Cleanup Old States](#cleanup-old-states)
   - [Get Edit Summary](#get-edit-summary)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Workflow Examples](#workflow-examples)
7. [State File Format](#state-file-format)
8. [Best Practices](#best-practices)

---

## Overview

The pause/resume API allows users to:
- **Pause** active autofill operations at any time
- **Save** complete algorithm state to disk (compressed JSON)
- **Edit** the grid manually while paused
- **Resume** from the exact pause point with user edits locked

### Key Features

- **State Preservation**: Complete CSP state including domains, constraints, backtracking position
- **Edit Integration**: User edits are validated and merged with AC-3 constraint propagation
- **Automatic Cleanup**: Old state files deleted after 7 days (configurable)
- **Compression**: Gzip compression (~80% size reduction)
- **Validation**: Edit validation prevents unsolvable grid configurations

### Storage Location

State files are stored in: `backend/data/autofill_states/{task_id}.json.gz`

---

## Authentication

Currently, the API does not require authentication. All endpoints are publicly accessible on the local server.

**Future Considerations**: When deploying to production, add authentication middleware.

---

## Endpoints

### Pause Autofill

Request the autofill algorithm to pause gracefully.

**Endpoint:** `POST /api/fill/pause/{task_id}`

#### Path Parameters

| Parameter | Type   | Required | Description                    |
|-----------|--------|----------|--------------------------------|
| task_id   | string | Yes      | Unique task identifier to pause |

#### Request

```http
POST /api/fill/pause/task_abc123 HTTP/1.1
Host: localhost:5000
```

#### Response (200 OK)

```json
{
  "success": true,
  "message": "Pause requested for task task_abc123",
  "task_id": "task_abc123"
}
```

#### Error Responses

| Status | Description                |
|--------|----------------------------|
| 500    | Server error               |

#### Notes

- The pause request creates a flag file that the CLI checks every 100 iterations
- Pause may take 1-2 seconds to take effect
- State is automatically saved when pause is detected
- Calling pause on a non-existent task is safe (no error)

#### Example

```javascript
async function pauseAutofill(taskId) {
  const response = await fetch(`/api/fill/pause/${taskId}`, {
    method: 'POST'
  });

  const data = await response.json();

  if (data.success) {
    console.log('Pause requested');
  }
}
```

---

### Resume Autofill

Resume paused autofill with optional user edits.

**Endpoint:** `POST /api/fill/resume`

#### Request Body

```json
{
  "task_id": "task_abc123",
  "edited_grid": [[["R"], ["A"], ["T"]], ...],  // Optional
  "options": {                                    // Optional
    "min_score": 50,
    "timeout": 300,
    "wordlists": ["comprehensive"],
    "algorithm": "trie"
  }
}
```

#### Request Parameters

| Parameter    | Type     | Required | Description                           |
|--------------|----------|----------|---------------------------------------|
| task_id      | string   | Yes      | Task ID of saved state                |
| edited_grid  | array    | No       | Grid with user edits (2D array)       |
| options      | object   | No       | Autofill options (same as /api/fill)  |

#### Response (200 OK)

```json
{
  "success": true,
  "new_task_id": "resume_xyz456",
  "original_task_id": "task_abc123",
  "message": "Resume state prepared",
  "slots_filled": 38,
  "total_slots": 76
}
```

#### Response Fields

| Field             | Type    | Description                               |
|-------------------|---------|-------------------------------------------|
| success           | boolean | Always true on success                    |
| new_task_id       | string  | New task ID for resumed autofill          |
| original_task_id  | string  | Original task ID that was resumed from    |
| message           | string  | Human-readable status message             |
| slots_filled      | integer | Number of slots filled in saved state     |
| total_slots       | integer | Total number of slots in grid             |

#### Error Responses

| Status | Description                                      |
|--------|--------------------------------------------------|
| 400    | Missing required field (task_id)                 |
| 404    | Saved state not found                            |
| 409    | User edits create unsolvable configuration       |
| 500    | Server error                                     |

#### Error Response (409 Conflict)

```json
{
  "error": "User edits create unsolvable configuration",
  "details": "Empty domains for slots: (3,5) across, (5,3) down"
}
```

#### Edit Validation

When `edited_grid` is provided:

1. **Change Detection**: Compares saved grid with edited grid
2. **Locking**: Newly filled cells marked as locked (unchangeable)
3. **Constraint Propagation**: AC-3 algorithm updates domains
4. **Validation**: Ensures no empty domains (unsolvable state)

If validation fails, returns **409 Conflict** with details.

#### Example (No Edits)

```javascript
async function resumeAutofill(taskId) {
  const response = await fetch('/api/fill/resume', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task_id: taskId,
      options: {
        min_score: 50,
        timeout: 300
      }
    })
  });

  const data = await response.json();

  if (data.success) {
    // Start monitoring new_task_id for progress
    startAutofill(data.new_task_id);
  }
}
```

#### Example (With Edits)

```javascript
async function resumeWithEdits(taskId, editedGrid) {
  const response = await fetch('/api/fill/resume', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task_id: taskId,
      edited_grid: editedGrid,
      options: {
        min_score: 50,
        timeout: 300
      }
    })
  });

  if (response.status === 409) {
    const error = await response.json();
    alert(`Cannot resume: ${error.details}`);
    return;
  }

  const data = await response.json();
  startAutofill(data.new_task_id);
}
```

---

### Get Saved State

Get metadata about a saved state without loading the full state.

**Endpoint:** `GET /api/fill/state/{task_id}`

#### Path Parameters

| Parameter | Type   | Required | Description            |
|-----------|--------|----------|------------------------|
| task_id   | string | Yes      | Unique task identifier |

#### Request

```http
GET /api/fill/state/task_abc123 HTTP/1.1
Host: localhost:5000
```

#### Response (200 OK)

```json
{
  "task_id": "task_abc123",
  "timestamp": "2025-12-26T10:30:00Z",
  "algorithm": "csp",
  "version": "1.0",
  "slots_filled": 38,
  "total_slots": 76,
  "grid_size": [15, 15],
  "iteration_count": 1250,
  "grid_preview": [[["R"], ["A"], ["T"]], ...]
}
```

#### Response Fields

| Field           | Type    | Description                           |
|-----------------|---------|---------------------------------------|
| task_id         | string  | Task identifier                       |
| timestamp       | string  | ISO 8601 timestamp when state saved   |
| algorithm       | string  | Algorithm used ("csp" or "beam")      |
| version         | string  | State format version                  |
| slots_filled    | integer | Number of filled slots                |
| total_slots     | integer | Total slots in grid                   |
| grid_size       | array   | Grid dimensions [width, height]       |
| iteration_count | integer | Number of algorithm iterations        |
| grid_preview    | array   | Current grid state (2D array)         |

#### Error Responses

| Status | Description       |
|--------|-------------------|
| 404    | State not found   |
| 500    | Server error      |

#### Example

```javascript
async function getStateInfo(taskId) {
  const response = await fetch(`/api/fill/state/${taskId}`);

  if (response.ok) {
    const info = await response.json();
    console.log(`State: ${info.slots_filled}/${info.total_slots} filled`);
    return info;
  } else {
    console.error('State not found');
    return null;
  }
}
```

---

### Delete Saved State

Delete a saved state file.

**Endpoint:** `DELETE /api/fill/state/{task_id}`

#### Path Parameters

| Parameter | Type   | Required | Description            |
|-----------|--------|----------|------------------------|
| task_id   | string | Yes      | Unique task identifier |

#### Request

```http
DELETE /api/fill/state/task_abc123 HTTP/1.1
Host: localhost:5000
```

#### Response (200 OK)

```json
{
  "success": true,
  "message": "State deleted for task task_abc123"
}
```

#### Error Responses

| Status | Description       |
|--------|-------------------|
| 404    | State not found   |
| 500    | Server error      |

#### Example

```javascript
async function deleteState(taskId) {
  const response = await fetch(`/api/fill/state/${taskId}`, {
    method: 'DELETE'
  });

  const data = await response.json();
  console.log(data.message);
}
```

---

### List Saved States

List all saved states with optional filtering.

**Endpoint:** `GET /api/fill/states`

#### Query Parameters

| Parameter     | Type    | Required | Description                              |
|---------------|---------|----------|------------------------------------------|
| max_age_days  | integer | No       | Only return states newer than this (days)|

#### Request

```http
GET /api/fill/states?max_age_days=7 HTTP/1.1
Host: localhost:5000
```

#### Response (200 OK)

```json
{
  "states": [
    {
      "task_id": "task_abc123",
      "timestamp": "2025-12-26T10:30:00Z",
      "algorithm": "csp",
      "version": "1.0",
      "slots_filled": 38,
      "total_slots": 76,
      "grid_size": [15, 15],
      "iteration_count": 1250
    },
    {
      "task_id": "task_xyz456",
      "timestamp": "2025-12-25T15:20:00Z",
      "algorithm": "beam",
      "version": "1.0",
      "slots_filled": 52,
      "total_slots": 140,
      "grid_size": [21, 21],
      "iteration_count": 3400
    }
  ],
  "count": 2
}
```

#### Response Fields

| Field  | Type    | Description                           |
|--------|---------|---------------------------------------|
| states | array   | Array of state info objects           |
| count  | integer | Number of states returned             |

States are sorted by timestamp (newest first).

#### Error Responses

| Status | Description  |
|--------|--------------|
| 500    | Server error |

#### Example

```javascript
async function listRecentStates() {
  const response = await fetch('/api/fill/states?max_age_days=7');
  const data = await response.json();

  console.log(`Found ${data.count} recent states:`);
  data.states.forEach(state => {
    console.log(`- ${state.task_id}: ${state.slots_filled}/${state.total_slots}`);
  });
}
```

---

### Cleanup Old States

Delete state files older than specified days.

**Endpoint:** `POST /api/fill/states/cleanup`

#### Request Body

```json
{
  "max_age_days": 7  // Optional, defaults to 7
}
```

#### Request Parameters

| Parameter    | Type    | Required | Default | Description                    |
|--------------|---------|----------|---------|--------------------------------|
| max_age_days | integer | No       | 7       | Delete states older than this  |

#### Response (200 OK)

```json
{
  "success": true,
  "deleted_count": 3,
  "message": "Deleted 3 old state files"
}
```

#### Response Fields

| Field         | Type    | Description                      |
|---------------|---------|----------------------------------|
| success       | boolean | Always true on success           |
| deleted_count | integer | Number of files deleted          |
| message       | string  | Human-readable status message    |

#### Error Responses

| Status | Description  |
|--------|--------------|
| 500    | Server error |

#### Example

```javascript
async function cleanupOldStates() {
  const response = await fetch('/api/fill/states/cleanup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ max_age_days: 7 })
  });

  const data = await response.json();
  console.log(`Cleaned up ${data.deleted_count} old states`);
}
```

---

### Get Edit Summary

Preview the impact of user edits without committing changes.

**Endpoint:** `POST /api/fill/edit-summary`

#### Request Body

```json
{
  "task_id": "task_abc123",
  "edited_grid": [[["R"], ["A"], ["T"]], ...]
}
```

#### Request Parameters

| Parameter    | Type   | Required | Description                    |
|--------------|--------|----------|--------------------------------|
| task_id      | string | Yes      | Task ID of saved state         |
| edited_grid  | array  | Yes      | Grid with user edits (2D array)|

#### Response (200 OK)

```json
{
  "filled_count": 5,
  "emptied_count": 2,
  "modified_count": 1,
  "new_words": ["WORD", "TEST", "GRID"],
  "removed_words": ["OLD", "PREV"]
}
```

#### Response Fields

| Field           | Type    | Description                            |
|-----------------|---------|----------------------------------------|
| filled_count    | integer | Number of slots newly filled by user   |
| emptied_count   | integer | Number of slots emptied by user        |
| modified_count  | integer | Number of slots with changed content   |
| new_words       | array   | List of new words added by user        |
| removed_words   | array   | List of words removed by user          |

#### Error Responses

| Status | Description                          |
|--------|--------------------------------------|
| 400    | Missing required fields              |
| 404    | Saved state not found                |
| 500    | Server error                         |

#### Use Cases

- **Preview Mode**: Show user what changes they made before resuming
- **Validation**: Check edit impact without committing
- **UI Feedback**: Display edit statistics

#### Example

```javascript
async function previewEdits(taskId, editedGrid) {
  const response = await fetch('/api/fill/edit-summary', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task_id: taskId,
      edited_grid: editedGrid
    })
  });

  const summary = await response.json();

  console.log(`You filled ${summary.filled_count} slots`);
  console.log(`New words: ${summary.new_words.join(', ')}`);

  // Show confirmation dialog
  const proceed = confirm(
    `You've made ${summary.filled_count} changes. Resume?`
  );

  if (proceed) {
    resumeWithEdits(taskId, editedGrid);
  }
}
```

---

## Data Models

### Grid Format

Grids are represented as 2D arrays:

```javascript
[
  [["R"], ["A"], ["T"], ["#"], ["T"]],  // Row 0
  [["E"], ["."], ["."], ["#"], ["E"]],  // Row 1
  [["D"], ["."], ["."], ["#"], ["S"]],  // Row 2
  ...
]
```

**Cell Values:**
- `["."]` - Empty cell
- `["#"]` - Black square
- `["A"]` - Letter (A-Z)

### State Object

Complete CSP state stored in JSON:

```json
{
  "version": "1.0",
  "algorithm": "csp",
  "task_id": "task_abc123",
  "timestamp": "2025-12-26T10:30:00Z",
  "metadata": {
    "min_score": 50,
    "timeout": 300,
    "grid_size": [15, 15],
    "total_slots": 76,
    "slots_filled": 38
  },
  "state_data": {
    "grid": {...},
    "domains": {...},
    "constraints": {...},
    "used_words": [...],
    "slot_id_map": {...},
    "current_slot_index": 38,
    "locked_slots": [0, 5, 12],
    "iteration_count": 1250
  }
}
```

See [State File Format](#state-file-format) for complete details.

---

## Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "error": "Error message",
  "details": "Additional details (optional)"
}
```

### Common Error Codes

| Code | Description                           | Resolution                           |
|------|---------------------------------------|--------------------------------------|
| 400  | Bad Request - Missing/invalid params  | Check request body/params            |
| 404  | Not Found - State doesn't exist       | Verify task_id, check /api/fill/states |
| 409  | Conflict - Edits create unsolvable grid | Revert edits or try different values |
| 500  | Internal Server Error                 | Check server logs                    |

### Error Handling Example

```javascript
async function resumeWithErrorHandling(taskId, editedGrid) {
  try {
    const response = await fetch('/api/fill/resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_id: taskId,
        edited_grid: editedGrid
      })
    });

    if (!response.ok) {
      const error = await response.json();

      switch (response.status) {
        case 404:
          alert('Saved state not found. It may have been deleted.');
          break;
        case 409:
          alert(`Your edits create an unsolvable grid:\n${error.details}`);
          break;
        case 400:
          alert('Invalid request. Please check your input.');
          break;
        default:
          alert(`Error: ${error.error}`);
      }

      return null;
    }

    return await response.json();

  } catch (err) {
    alert('Network error. Please check your connection.');
    return null;
  }
}
```

---

## Workflow Examples

### Basic Pause/Resume

```javascript
// 1. Start autofill
const taskId = await startAutofill(gridData, options);

// 2. User clicks pause after 30 seconds
await pauseAutofill(taskId);

// Wait for pause to complete (1-2 seconds)
await new Promise(resolve => setTimeout(resolve, 2000));

// 3. Check saved state
const stateInfo = await getStateInfo(taskId);
console.log(`Paused at: ${stateInfo.slots_filled}/${stateInfo.total_slots}`);

// 4. Resume without edits
const resumeData = await resumeAutofill(taskId);

// 5. Monitor new task
monitorProgress(resumeData.new_task_id);
```

### Pause, Edit, Resume with Validation

```javascript
// 1. Pause autofill
await pauseAutofill(taskId);
await new Promise(resolve => setTimeout(resolve, 2000));

// 2. User edits grid
const editedGrid = userMakesEdits(currentGrid);

// 3. Preview edits
const summary = await fetch('/api/fill/edit-summary', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ task_id: taskId, edited_grid: editedGrid })
}).then(r => r.json());

console.log(`You filled ${summary.filled_count} slots`);
console.log(`New words: ${summary.new_words.join(', ')}`);

// 4. Show confirmation
if (confirm(`Continue with ${summary.filled_count} edits?`)) {
  // 5. Resume with edits
  const response = await fetch('/api/fill/resume', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task_id: taskId,
      edited_grid: editedGrid,
      options: { min_score: 50, timeout: 300 }
    })
  });

  if (response.status === 409) {
    const error = await response.json();
    alert(`Cannot resume: ${error.details}\nPlease adjust your edits.`);
  } else {
    const data = await response.json();
    monitorProgress(data.new_task_id);
  }
}
```

### State Management

```javascript
// List all recent states
const { states, count } = await fetch('/api/fill/states?max_age_days=7')
  .then(r => r.json());

console.log(`Found ${count} recent states:`);

// Show in UI for user to select
states.forEach(state => {
  console.log(`${state.task_id}: ${state.slots_filled}/${state.total_slots} (${state.timestamp})`);
});

// User selects a state to resume
const selectedTaskId = userSelectsState(states);

// Load and resume
const stateInfo = await getStateInfo(selectedTaskId);
displayGrid(stateInfo.grid_preview);

if (confirm('Resume this autofill?')) {
  const resumeData = await resumeAutofill(selectedTaskId);
  monitorProgress(resumeData.new_task_id);
}

// Cleanup old states (run periodically or on user action)
await fetch('/api/fill/states/cleanup', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ max_age_days: 7 })
}).then(r => r.json());
```

---

## State File Format

State files are stored as compressed JSON: `{task_id}.json.gz`

### File Structure

```json
{
  "version": "1.0",
  "algorithm": "csp",
  "task_id": "task_abc123",
  "timestamp": "2025-12-26T10:30:00Z",
  "metadata": {
    "min_score": 50,
    "timeout": 300,
    "algorithm": "trie",
    "grid_size": [15, 15],
    "total_slots": 76,
    "slots_filled": 38,
    "time_elapsed": 125.4
  },
  "state_data": {
    "grid_dict": {
      "size": 15,
      "grid": [[["R"], ["A"], ...], ...]
    },
    "domains": {
      "0": ["WORD1", "WORD2", ...],
      "1": ["ALPHA", "BRAVO", ...]
    },
    "constraints": {
      "0": [[1, 0, 2], [5, 1, 0]],
      "1": [[0, 2, 0]]
    },
    "used_words": ["WORD1", "ALPHA"],
    "slot_id_map": {
      "[0, 1, \"across\"]": 0,
      "[0, 1, \"down\"]": 1
    },
    "slot_list": [
      {"row": 0, "col": 1, "direction": "across", "length": 4},
      {"row": 0, "col": 1, "direction": "down", "length": 5}
    ],
    "slots_sorted": [0, 1, 2, ...],
    "current_slot_index": 38,
    "iteration_count": 1250,
    "locked_slots": [0, 5, 12],
    "timestamp": "2025-12-26T10:30:00Z",
    "random_seed": 42
  }
}
```

### Field Descriptions

**Top Level:**
- `version`: State format version (for migration)
- `algorithm`: "csp" or "beam"
- `task_id`: Unique identifier
- `timestamp`: When state was saved (ISO 8601)

**Metadata:**
- `min_score`: Minimum word quality score setting
- `timeout`: Timeout setting (seconds)
- `algorithm`: Pattern matching algorithm ("regex" or "trie")
- `grid_size`: [width, height]
- `total_slots`: Total word slots in grid
- `slots_filled`: Number of filled slots
- `time_elapsed`: Time spent before pause (seconds)

**State Data:**
- `grid_dict`: Complete grid state
- `domains`: Available words for each slot (pruned by AC-3)
- `constraints`: Slot intersection constraints
- `used_words`: Words already placed
- `slot_id_map`: Mapping of (row, col, direction) → slot_id
- `slot_list`: All slots with position/length info
- `slots_sorted`: Slots sorted by MCV heuristic
- `current_slot_index`: Resume from this position in slots_sorted
- `iteration_count`: Total backtracking iterations
- `locked_slots`: Slots that cannot be changed (theme + user edits)
- `random_seed`: Random seed for reproducibility

### File Size

Typical compressed state file sizes:
- **11×11 grid**: ~20-50 KB
- **15×15 grid**: ~50-150 KB
- **21×21 grid**: ~150-500 KB

Compression ratio: ~80% (5x reduction)

---

## Best Practices

### 1. Task ID Management

```javascript
// Store task_id in localStorage for persistence
function saveTaskId(taskId) {
  localStorage.setItem('current_autofill_task', taskId);
}

function getTaskId() {
  return localStorage.getItem('current_autofill_task');
}

// Clear on completion
function clearTaskId() {
  localStorage.removeItem('current_autofill_task');
}

// On page load, check for paused state
window.addEventListener('load', async () => {
  const taskId = getTaskId();
  if (taskId) {
    const stateInfo = await getStateInfo(taskId);
    if (stateInfo) {
      showResumePrompt(taskId, stateInfo);
    } else {
      clearTaskId(); // State no longer exists
    }
  }
});
```

### 2. Edit Validation

```javascript
// Always preview edits before resuming
async function validateAndResume(taskId, editedGrid) {
  // 1. Get edit summary
  const summary = await getEditSummary(taskId, editedGrid);

  // 2. Show user what changed
  const message = `
    You made ${summary.filled_count + summary.modified_count} changes:
    - Filled: ${summary.filled_count} slots
    - Modified: ${summary.modified_count} slots
    - New words: ${summary.new_words.join(', ')}

    Continue?
  `;

  if (!confirm(message)) {
    return;
  }

  // 3. Attempt resume
  try {
    const response = await fetch('/api/fill/resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId, edited_grid: editedGrid })
    });

    if (response.status === 409) {
      const error = await response.json();
      alert(`Your edits create an unsolvable grid:\n${error.details}\n\nPlease adjust your changes.`);
      return;
    }

    const data = await response.json();
    startAutofill(data.new_task_id);

  } catch (err) {
    console.error('Resume failed:', err);
    alert('Failed to resume. Please try again.');
  }
}
```

### 3. State Cleanup

```javascript
// Cleanup old states periodically (e.g., on app startup)
async function periodicCleanup() {
  const response = await fetch('/api/fill/states/cleanup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ max_age_days: 7 })
  });

  const data = await response.json();
  console.log(`Cleaned up ${data.deleted_count} old states`);
}

// Run on app startup
window.addEventListener('load', () => {
  periodicCleanup();
});
```

### 4. Error Handling

```javascript
// Centralized error handler
async function apiCall(url, options = {}) {
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      const error = await response.json();

      // Log for debugging
      console.error(`API Error [${response.status}]:`, error);

      // User-friendly messages
      switch (response.status) {
        case 400:
          throw new Error('Invalid request. Please check your input.');
        case 404:
          throw new Error('Resource not found. It may have been deleted.');
        case 409:
          throw new Error(`Cannot proceed: ${error.details}`);
        case 500:
          throw new Error('Server error. Please try again later.');
        default:
          throw new Error(error.error || 'Unknown error');
      }
    }

    return await response.json();

  } catch (err) {
    if (err.name === 'TypeError') {
      // Network error
      throw new Error('Network error. Please check your connection.');
    }
    throw err;
  }
}

// Usage
try {
  const data = await apiCall('/api/fill/resume', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId })
  });

  console.log('Resume successful:', data);

} catch (err) {
  alert(err.message);
}
```

### 5. Progress Monitoring

```javascript
// Monitor both pause status and normal progress
function monitorAutofill(taskId) {
  const eventSource = new EventSource(`/api/progress/${taskId}`);

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.status) {
      case 'running':
        updateProgress(data.progress, data.message);
        break;

      case 'paused':
        eventSource.close();
        handlePaused(taskId, data);
        break;

      case 'complete':
        eventSource.close();
        handleComplete(data);
        break;

      case 'error':
        eventSource.close();
        handleError(data);
        break;
    }
  };

  return eventSource;
}

function handlePaused(taskId, data) {
  saveTaskId(taskId);
  showPausedIndicator();
  enableResumeButton();

  // Display grid at paused state
  if (data.data && data.data.grid) {
    displayGrid(data.data.grid);
  }
}
```

---

## Changelog

### Version 1.0 (2025-12-26)

**Initial Release**

- POST /api/fill/pause/{task_id}
- POST /api/fill/resume
- GET /api/fill/state/{task_id}
- DELETE /api/fill/state/{task_id}
- GET /api/fill/states
- POST /api/fill/states/cleanup
- POST /api/fill/edit-summary

**Features:**
- Complete CSP state preservation
- Edit validation with AC-3 constraint propagation
- Automatic state cleanup (7-day retention)
- Gzip compression (~80% size reduction)
- Edit preview mode

---

## Support

For issues or questions:
- **GitHub Issues**: [crossword-helper/issues](https://github.com/your-repo/crossword-helper/issues)
- **Documentation**: See `docs/` directory
- **Examples**: See `docs/WORKFLOW_EXAMPLES.md`

---

## License

Same as parent project.
