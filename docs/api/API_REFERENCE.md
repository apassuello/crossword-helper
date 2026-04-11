# Crossword Helper API Reference

> **Version**: 2.0.0
> **Base URL**: `http://localhost:5000/api`
> **Architecture**: Flask backend delegating to CLI via subprocess

This document provides practical, developer-friendly documentation for the Crossword Helper REST API.

**For machine-readable specification**, see: [`openapi.yaml`](./openapi.yaml)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Operations](#core-operations)
   - [Health Check](#health-check)
   - [Pattern Search](#pattern-search)
   - [Grid Numbering](#grid-numbering)
   - [Entry Normalization](#entry-normalization)
   - [Grid Autofill](#grid-autofill)
3. [Grid Helpers](#grid-helpers)
   - [Suggest Black Squares](#suggest-black-squares)
   - [Apply Black Squares](#apply-black-squares)
   - [Validate Grid](#validate-grid)
4. [Theme Management](#theme-management)
   - [Upload Theme Words](#upload-theme-words)
   - [Suggest Placements](#suggest-placements)
   - [Apply Theme Placement](#apply-theme-placement)
5. [Pause/Resume](#pauseresume)
   - [Pause Autofill](#pause-autofill)
   - [Cancel Autofill](#cancel-autofill)
   - [Resume Autofill](#resume-autofill)
   - [Get Saved State](#get-saved-state)
   - [Delete Saved State](#delete-saved-state)
   - [List Saved States](#list-saved-states)
   - [Cleanup Old States](#cleanup-old-states)
   - [Preview Edit Summary](#preview-edit-summary)
6. [Progress Tracking](#progress-tracking)
   - [Stream Progress Updates](#stream-progress-updates)
7. [Wordlist Management](#wordlist-management)
   - [List Wordlists](#list-wordlists)
   - [Get Wordlist](#get-wordlist)
   - [Create Wordlist](#create-wordlist)
   - [Update Wordlist](#update-wordlist)
   - [Delete Wordlist](#delete-wordlist)
   - [Get Wordlist Statistics](#get-wordlist-statistics)
   - [Import Wordlist](#import-wordlist)
8. [Constraint Analysis](#constraint-analysis)
   - [Get Grid Constraints](#get-grid-constraints)
   - [Get Placement Impact](#get-placement-impact)
9. [Common Patterns](#common-patterns)
10. [Data Structures](#data-structures)
11. [Error Handling](#error-handling)
12. [Complete Workflows](#complete-workflows)

---

## Quick Start

### Installation and Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python run.py

# Server runs at http://localhost:5000
```

### Your First API Call

```bash
# Health check
curl http://localhost:5000/api/health

# Pattern search
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{"pattern": "?A?E"}'
```

### Authentication

Currently **no authentication required** (local-only tool). Future versions may add API key authentication for production deployments.

---

## Core Operations

### Health Check

Check API and CLI backend health status.

**Endpoint**: `GET /api/health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "architecture": "cli-backend",
  "components": {
    "cli_adapter": "ok",
    "api_server": "ok"
  }
}
```

**Response** (503 Service Unavailable - CLI backend unavailable):
```json
{
  "status": "degraded",
  "version": "2.0.0",
  "architecture": "cli-backend",
  "components": {
    "cli_adapter": "error",
    "api_server": "ok"
  }
}
```

**curl Example**:
```bash
curl http://localhost:5000/api/health
```

**Use Cases**:
- Verify API is running
- Check CLI backend connectivity
- Monitor service health

---

### Pattern Search

Search for words matching a pattern using wildcard matching.

**Endpoint**: `POST /api/pattern`

**Request Body**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `pattern` | string | Yes | - | Pattern with `?` for wildcards |
| `wordlists` | array | No | `["comprehensive"]` | Wordlist names to search |
| `max_results` | integer | No | `20` | Maximum results (1-100) |
| `algorithm` | string | No | `"regex"` | Algorithm: `regex` or `trie` |

**Pattern Examples**:
- `?A?E` - 4-letter words with A as 2nd letter, E as 4th
- `CAT` - Exact match
- `????` - Any 4-letter word
- `?????ING` - 8-letter words ending in ING

**Request Example**:
```json
{
  "pattern": "?A?E",
  "wordlists": ["comprehensive"],
  "max_results": 10,
  "algorithm": "regex"
}
```

**Response** (200 OK):
```json
{
  "results": [
    {
      "word": "CAKE",
      "score": 85,
      "source": "comprehensive"
    },
    {
      "word": "CAFE",
      "score": 82,
      "source": "comprehensive"
    },
    {
      "word": "CASE",
      "score": 80,
      "source": "comprehensive"
    }
  ],
  "meta": {
    "total_found": 127,
    "query_time_ms": 245
  }
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "?A?E",
    "wordlists": ["comprehensive"],
    "max_results": 10
  }'
```

**Error Responses**:
- `400 Bad Request`: Invalid pattern or wordlists
- `505 HTTP Version Not Supported`: Pattern search timeout
- `500 Internal Server Error`: Server error

**Common Use Cases**:
- Find word candidates for crossword slots
- Explore vocabulary matching constraints
- Test word existence with exact patterns

**Tips**:
- Use `trie` algorithm for faster searches on large wordlists
- Limit `max_results` for faster responses
- Score indicates word quality (higher = better for crosswords)

---

### Pattern Search with Progress

Search for words matching a pattern with Server-Sent Events (SSE) progress tracking for long-running searches.

**Endpoint**: `POST /api/pattern/with-progress`

**Request Body**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `pattern` | string | Yes | - | Pattern with `?` for wildcards |
| `wordlists` | array | No | `["comprehensive"]` | Wordlist names to search |
| `max_results` | integer | No | `20` | Maximum results (1-100) |
| `algorithm` | string | No | `"regex"` | Algorithm: `regex` or `trie` |

**Request Example**:
```json
{
  "pattern": "??????",
  "wordlists": ["comprehensive", "themed/music"],
  "max_results": 100,
  "algorithm": "trie"
}
```

**Response** (202 Accepted):
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "progress_url": "/api/progress/550e8400-e29b-41d4-a716-446655440000"
}
```

**curl Example**:
```bash
# Start pattern search with progress
curl -X POST http://localhost:5000/api/pattern/with-progress \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "??????",
    "wordlists": ["comprehensive"],
    "max_results": 100
  }'

# Then connect to SSE stream
curl -N http://localhost:5000/api/progress/550e8400-e29b-41d4-a716-446655440000
```

**Progress Events**:
The progress URL returns Server-Sent Events with status updates:
```
data: {"status":"running","progress":25,"message":"Searching comprehensive..."}

data: {"status":"running","progress":75,"message":"Found 89 matches..."}

data: {"status":"completed","progress":100,"result":{"results":[...],"meta":{...}}}
```

**Use Cases**:
- Search large wordlists without timeout
- Monitor progress for long-running pattern searches
- Implement responsive UI with real-time feedback

**Difference from Standard Pattern Search**:
| Aspect | `/api/pattern` | `/api/pattern/with-progress` |
|--------|----------------|------------------------------|
| Response | Synchronous (200 OK) | Async (202 Accepted + SSE) |
| Timeout | 60 seconds | No timeout (monitored via SSE) |
| Progress | No feedback | Real-time progress events |
| Use When | Quick searches | Large wordlists, many results |

---

### Grid Numbering

Auto-number crossword grid cells according to standard conventions.

**Endpoint**: `POST /api/number`

**Request Body**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `grid` | Grid | Yes | - | 2D array of cells |
| `size` | integer | No | `15` | Grid size: 11, 13, 15, 17, or 21 |

**Request Example**:
```json
{
  "grid": [
    [
      {"letter": "", "isBlack": false},
      {"letter": "", "isBlack": false},
      {"letter": "", "isBlack": true}
    ],
    [
      {"letter": "", "isBlack": false},
      {"letter": "", "isBlack": false},
      {"letter": "", "isBlack": false}
    ]
  ],
  "size": 15
}
```

**Response** (200 OK):
```json
{
  "numbering": {
    "(0,0)": 1,
    "(0,1)": 2,
    "(1,0)": 3
  },
  "validation": {
    "is_valid": true,
    "errors": []
  },
  "grid_info": {
    "size": [2, 3],
    "word_count": 3
  }
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/number \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [[{"letter":"","isBlack":false},{"letter":"","isBlack":false}]],
    "size": 15
  }'
```

**Numbering Rules**:
- Cells are numbered if they start an across or down word
- Numbers are assigned sequentially (1, 2, 3, ...)
- Black squares and cells not starting words have no number

**Error Responses**:
- `400 Bad Request`: Invalid grid structure
- `504 Gateway Timeout`: Grid numbering timeout
- `500 Internal Server Error`: Server error

**Use Cases**:
- Auto-number grid after placing black squares
- Validate grid structure
- Get word count and grid dimensions

---

### Entry Normalization

Normalize entry text according to crossword conventions.

**Endpoint**: `POST /api/normalize`

**Request Body**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Entry text to normalize |

**Normalization Rules**:
- Remove spaces in names: `"Tina Fey"` → `"TINAFEY"`
- Spell out fractions: `"50/50"` → `"FIFTYFIFTY"`
- Remove hyphens: `"X-ray"` → `"XRAY"`
- Uppercase all letters

**Request Example**:
```json
{
  "text": "Tina Fey"
}
```

**Response** (200 OK):
```json
{
  "normalized": "TINAFEY",
  "rule": {
    "type": "two_word_names",
    "description": "Remove spaces from two-word names"
  },
  "examples": [
    ["Tracy Jordan", "TRACYJORDAN"],
    ["Sarah Connor", "SARAHCONNOR"],
    ["Tony Stark", "TONYSTARK"]
  ]
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/normalize \
  -H "Content-Type: application/json" \
  -d '{"text": "Tina Fey"}'
```

**Error Responses**:
- `400 Bad Request`: Missing or invalid text
- `506 Variant Also Negotiates`: Normalization timeout
- `500 Internal Server Error`: Server error

**Use Cases**:
- Validate theme word entries
- Convert clue answers to grid format
- Learn crossword entry conventions

**Common Normalizations**:
- `"50/50"` → `"FIFTYFIFTY"`
- `"X-ray"` → `"XRAY"`
- `"re-do"` → `"REDO"`
- `"St. Louis"` → `"STLOUIS"`

---

### Grid Autofill

Fill crossword grid using CSP-based autofill algorithm.

**Endpoint**: `POST /api/fill`

**Request Body**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `grid` | Grid | Yes | - | 2D array of cells |
| `size` | integer | Yes | - | Grid size: 11, 13, 15, 17, or 21 |
| `wordlists` | array | No | `["comprehensive"]` | Wordlist names |
| `timeout` | integer | No | `300` | Timeout in seconds |
| `min_score` | integer | No | `30` | Minimum word quality (0-100) |
| `algorithm` | string | No | `"trie"` | Algorithm: `regex`, `trie`, or `beam` |
| `theme_entries` | object | No | `{}` | Theme words to preserve |
| `adaptive_mode` | boolean | No | `false` | Enable automatic black square placement |
| `max_adaptations` | integer | No | `3` | Maximum adaptive black squares (1-5) |

**Request Example**:
```json
{
  "grid": [
    [{"letter":"","isBlack":false}, {"letter":"","isBlack":false}, {"letter":"","isBlack":true}],
    [{"letter":"","isBlack":false}, {"letter":"","isBlack":false}, {"letter":"","isBlack":false}],
    [{"letter":"","isBlack":true}, {"letter":"","isBlack":false}, {"letter":"","isBlack":false}]
  ],
  "size": 15,
  "wordlists": ["comprehensive"],
  "timeout": 300,
  "min_score": 30,
  "algorithm": "trie",
  "theme_entries": {
    "(0,0,across)": "PARTNERNAME"
  },
  "adaptive_mode": false
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "grid": [
    [{"letter":"C","isBlack":false}, {"letter":"A","isBlack":false}, {"letter":"","isBlack":true}],
    [{"letter":"A","isBlack":false}, {"letter":"T","isBlack":false}, {"letter":"S","isBlack":false}],
    [{"letter":"","isBlack":true}, {"letter":"O","isBlack":false}, {"letter":"P","isBlack":false}]
  ],
  "slots_filled": 8,
  "total_slots": 8,
  "adaptations_applied": 0,
  "message": "Grid filled successfully"
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/fill \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [[{"letter":"","isBlack":false}]],
    "size": 15,
    "timeout": 300
  }'
```

**For Real-Time Progress**, use `/api/fill/with-progress` instead (see [Progress Tracking](#progress-tracking)).

**Error Responses**:
- `400 Bad Request`: Invalid grid or parameters
- `507 Insufficient Storage`: Grid fill timeout
- `500 Internal Server Error`: Server error

**Algorithm Comparison**:
| Algorithm | Speed | Memory | Best For |
|-----------|-------|--------|----------|
| `regex` | Slow | Low | Small grids, simple patterns |
| `trie` | Fast | Medium | Most grids (default) |
| `beam` | Very Fast | High | Large grids, complex constraints |

**Theme Entry Format**:
```json
{
  "(row,col,direction)": "WORD"
}
```

Example:
```json
{
  "(0,0,across)": "PARTNERNAME",
  "(7,5,down)": "ANNIVERSARY"
}
```

**Adaptive Mode**:
When `adaptive_mode: true`, the algorithm automatically places black squares to resolve impossible constraints. Use `max_adaptations` to limit modifications.

**Performance Expectations**:
- 11×11: < 30 seconds
- 15×15: < 5 minutes
- 21×21: < 30 minutes

**Use Cases**:
- Autofill empty crossword grid
- Complete partially filled grid
- Preserve theme words while filling
- Adaptively fix unsolvable grids

---

## Grid Helpers

### Suggest Black Squares

Suggest optimal black square placements to split problematic slots.

**Endpoint**: `POST /api/grid/suggest-black-square`

**Request Body**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `grid` | Grid | Yes | - | 2D array of cells |
| `grid_size` | integer | No | `15` | Grid size |
| `problematic_slot` | Slot | Yes | - | Slot to split |
| `max_suggestions` | integer | No | `3` | Maximum suggestions (1-10) |

**Request Example**:
```json
{
  "grid": [[{"letter":"","isBlack":false}]],
  "grid_size": 15,
  "problematic_slot": {
    "row": 0,
    "col": 0,
    "direction": "across",
    "length": 15,
    "pattern": "???????????????",
    "candidate_count": 0
  },
  "max_suggestions": 3
}
```

**Response** (200 OK):
```json
{
  "suggestions": [
    {
      "position": 7,
      "row": 0,
      "col": 7,
      "score": 850,
      "reasoning": "Splits into 7+7 letter words, both common lengths",
      "left_length": 7,
      "right_length": 7,
      "symmetric_position": {
        "row": 14,
        "col": 7
      },
      "new_word_count": 78,
      "constraint_reduction": 4
    },
    {
      "position": 5,
      "row": 0,
      "col": 5,
      "score": 720,
      "reasoning": "Splits into 5+9 letter words",
      "left_length": 5,
      "right_length": 9,
      "symmetric_position": {
        "row": 14,
        "col": 9
      },
      "new_word_count": 76,
      "constraint_reduction": 3
    }
  ],
  "slot_info": {
    "row": 0,
    "col": 0,
    "direction": "across",
    "length": 15
  },
  "grid_size": 15,
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": []
  }
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/grid/suggest-black-square \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [[{"letter":"","isBlack":false}]],
    "problematic_slot": {
      "row": 0,
      "col": 0,
      "direction": "across",
      "length": 15
    }
  }'
```

**Scoring Criteria**:
- Word length balance (7+7 better than 3+11)
- Rotational symmetry maintained
- Word count within standard range
- Constraint reduction (fewer crossing constraints)

**Use Cases**:
- Fix slots with no valid words
- Split very long slots
- Improve grid fillability

---

### Apply Black Squares

Apply a symmetric black square pair to the grid.

**Endpoint**: `POST /api/grid/apply-black-squares`

**Request Body**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `grid` | Grid | Yes | 2D array of cells |
| `primary` | Position | Yes | Primary black square position |
| `symmetric` | Position | Yes | Symmetric black square position |

**Request Example**:
```json
{
  "grid": [[{"letter":"","isBlack":false}]],
  "primary": {
    "row": 0,
    "col": 7
  },
  "symmetric": {
    "row": 14,
    "col": 7
  }
}
```

**Response** (200 OK):
```json
{
  "grid": [[{"letter":"","isBlack":true}]],
  "applied": true,
  "positions": [
    {"row": 0, "col": 7},
    {"row": 14, "col": 7}
  ]
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/grid/apply-black-squares \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [[{"letter":"","isBlack":false}]],
    "primary": {"row": 0, "col": 7},
    "symmetric": {"row": 14, "col": 7}
  }'
```

**Use Cases**:
- Apply suggestion from `/api/grid/suggest-black-square`
- Manually place symmetric black squares
- Modify grid structure

---

### Validate Grid

Validate grid quality metrics and get improvement suggestions.

**Endpoint**: `POST /api/grid/validate`

**Request Body**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `grid` | Grid | Yes | - | 2D array of cells |
| `grid_size` | integer | No | `15` | Grid size |

**Request Example**:
```json
{
  "grid": [[{"letter":"","isBlack":false}]],
  "grid_size": 15
}
```

**Response** (200 OK):
```json
{
  "valid": true,
  "word_count": 76,
  "black_square_count": 38,
  "black_square_percentage": 16.9,
  "word_count_range": [72, 80],
  "warnings": [
    "Black square percentage is slightly high (16.9% vs. ideal 15-16%)"
  ],
  "suggestions": [
    "Consider removing 2-3 symmetric black square pairs to increase word count"
  ]
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/grid/validate \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [[{"letter":"","isBlack":false}]],
    "grid_size": 15
  }'
```

**Validation Criteria**:
- Word count within standard range (15×15: 72-80 words)
- Black square percentage (ideal: 15-16%)
- Rotational symmetry maintained
- No 2-letter words

**Use Cases**:
- Check grid quality before autofill
- Get improvement suggestions
- Validate grid meets crossword standards

---

## Theme Management

### Upload Theme Words

Parse and validate theme words from file content.

**Endpoint**: `POST /api/theme/upload`

**Request Body**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `content` | string | Yes | - | Newline-separated theme words |
| `grid_size` | integer | No | `15` | Grid size |

**Request Example**:
```json
{
  "content": "PARTNERNAME\nANNIVERSARY\nFAVORITEPLACE",
  "grid_size": 15
}
```

**Response** (200 OK):
```json
{
  "words": [
    "PARTNERNAME",
    "ANNIVERSARY",
    "FAVORITEPLACE"
  ],
  "count": 3,
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": []
  }
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/theme/upload \
  -H "Content-Type: application/json" \
  -d '{
    "content": "PARTNERNAME\nANNIVERSARY\nFAVORITEPLACE",
    "grid_size": 15
  }'
```

**Validation Checks**:
- Word length fits grid size
- Only valid characters (A-Z)
- No duplicate words
- Word length ≥ 3

**Error Responses**:
- `400 Bad Request`: Invalid content or validation errors

**Use Cases**:
- Upload theme words from file
- Validate theme word format
- Get theme word count

---

### Validate Theme Words

Validate theme words without generating placements. Quick validation check for word suitability.

**Endpoint**: `POST /api/theme/validate`

**Request Body**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `theme_words` | array | Yes | - | List of theme words to validate |
| `grid_size` | integer | No | `15` | Grid size for validation |

**Request Example**:
```json
{
  "theme_words": ["PARTNERNAME", "ANNIVERSARY", "FAVORITEPLACE"],
  "grid_size": 15
}
```

**Response** (200 OK):
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    "FAVORITEPLACE: Very long (13 letters), may be hard to place"
  ]
}
```

**Validation Checks**:
- **Length**: Word fits in grid (≤ grid_size)
- **Characters**: Only A-Z (uppercase)
- **Duplicates**: No duplicate words
- **Minimum Length**: Word length ≥ 3
- **Placement Feasibility**: Words can theoretically be placed

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/theme/validate \
  -H "Content-Type: application/json" \
  -d '{
    "theme_words": ["PARTNERNAME", "ANNIVERSARY"],
    "grid_size": 15
  }'
```

**Error Response** (400 Bad Request):
```json
{
  "valid": false,
  "errors": [
    "VERYLONGWORDTHATDOESNOTFIT: Exceeds grid size (25 > 15)"
  ],
  "warnings": []
}
```

**Use Cases**:
- Pre-validate theme words before placement
- Check word suitability without full placement algorithm
- Quick feedback on theme word constraints

**Difference from Upload**:
| Endpoint | Purpose | Response |
|----------|---------|----------|
| `/api/theme/upload` | Parse file content | Parsed words + validation |
| `/api/theme/validate` | Validate word list | Validation result only |

---

### Suggest Placements

Generate optimal placement suggestions for theme words.

**Endpoint**: `POST /api/theme/suggest-placements`

**Request Body**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `theme_words` | array | Yes | - | List of theme words |
| `grid_size` | integer | No | `15` | Grid size |
| `existing_grid` | Grid | No | `null` | Existing grid to place into |
| `max_suggestions` | integer | No | `3` | Max suggestions per word |

**Request Example**:
```json
{
  "theme_words": ["PARTNERNAME", "ANNIVERSARY"],
  "grid_size": 15,
  "max_suggestions": 3
}
```

**Response** (200 OK):
```json
{
  "suggestions": [
    {
      "word": "PARTNERNAME",
      "length": 11,
      "suggestions": [
        {
          "row": 0,
          "col": 2,
          "direction": "across",
          "score": 95,
          "reasoning": "Top row, symmetric position, good spacing"
        },
        {
          "row": 7,
          "col": 2,
          "direction": "across",
          "score": 90,
          "reasoning": "Middle row, symmetric, allows cross-theme intersections"
        }
      ]
    },
    {
      "word": "ANNIVERSARY",
      "length": 11,
      "suggestions": [
        {
          "row": 14,
          "col": 2,
          "direction": "across",
          "score": 95,
          "reasoning": "Bottom row, symmetric with PARTNERNAME"
        }
      ]
    }
  ],
  "grid_size": 15
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/theme/suggest-placements \
  -H "Content-Type: application/json" \
  -d '{
    "theme_words": ["PARTNERNAME", "ANNIVERSARY"],
    "grid_size": 15
  }'
```

**Scoring Criteria**:
- Symmetric positioning
- Standard placement (top/middle/bottom rows)
- Spacing between theme words
- Potential for theme word intersections

**Use Cases**:
- Find optimal theme word placements
- Explore symmetric arrangements
- Plan grid structure before autofill

---

### Apply Theme Placement

Apply a theme word placement to the grid and mark cells as theme-locked.

**Endpoint**: `POST /api/theme/apply-placement`

**Request Body**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `grid` | Grid | Yes | 2D array of cells |
| `placement` | ThemePlacement | Yes | Theme word placement |

**ThemePlacement Object**:
```json
{
  "word": "PARTNERNAME",
  "row": 0,
  "col": 2,
  "direction": "across"
}
```

**Request Example**:
```json
{
  "grid": [[{"letter":"","isBlack":false}]],
  "placement": {
    "word": "PARTNERNAME",
    "row": 0,
    "col": 2,
    "direction": "across"
  }
}
```

**Response** (200 OK):
```json
{
  "grid": [
    [
      {"letter":"","isBlack":false},
      {"letter":"","isBlack":false},
      {"letter":"P","isBlack":false,"isThemeLocked":true},
      {"letter":"A","isBlack":false,"isThemeLocked":true},
      {"letter":"R","isBlack":false,"isThemeLocked":true}
    ]
  ],
  "applied": true
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/theme/apply-placement \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [[{"letter":"","isBlack":false}]],
    "placement": {
      "word": "PARTNERNAME",
      "row": 0,
      "col": 2,
      "direction": "across"
    }
  }'
```

**Theme-Locked Cells**:
- Marked with `isThemeLocked: true`
- Cannot be modified by autofill
- Preserved during pause/resume

**Use Cases**:
- Apply suggestion from `/api/theme/suggest-placements`
- Manually place theme words
- Lock theme words before autofill

---

## Pause/Resume

### Pause Autofill

Request an active autofill task to pause and save state.

**Endpoint**: `POST /api/fill/pause/{task_id}`

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | string | Unique task identifier |

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Pause requested",
  "task_id": "abc123-def456"
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/fill/pause/abc123-def456
```

**Error Responses**:
- `404 Not Found`: Task not found

**Use Cases**:
- Pause long-running autofill
- Save intermediate progress
- Allow user edits before continuing

**Note**: Pause is not immediate. The task will pause at the next safe checkpoint (after completing current iteration).

---

### Cancel Autofill

> ⚠️ **IMPLEMENTATION STATUS**: Not yet implemented (planned for Phase 3.1)
>
> This endpoint is fully documented and will be implemented using the existing `PauseController` infrastructure. See BACKEND_SPEC.md for implementation notes.

Cancel an active autofill task immediately.

**Endpoint**: `POST /api/fill/cancel/{task_id}`

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | string | Unique task identifier |

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Task canceled",
  "task_id": "abc123-def456"
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/fill/cancel/abc123-def456
```

**Error Responses**:
- `404 Not Found`: Task not found
- `409 Conflict`: Task already completed or canceled

**Use Cases**:
- Stop autofill when results are unsatisfactory
- Free resources for new autofill task
- Abort long-running operation

**Note**: Unlike pause, cancel is immediate and discards any progress. Use pause if you want to save intermediate state.

**Difference from Pause**:
| Action | Saves State | Resumable | Use When |
|--------|-------------|-----------|----------|
| Pause | Yes | Yes | Want to edit and continue |
| Cancel | No | No | Want to abandon and restart |

---

### Resume Autofill

Resume a paused autofill task with optional user edits.

**Endpoint**: `POST /api/fill/resume`

**Request Body**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | string | Yes | Saved state task ID |
| `edited_grid` | Grid | No | User-edited grid |
| `options` | object | No | Autofill options (same as `/api/fill`) |

**Request Example**:
```json
{
  "task_id": "abc123-def456",
  "edited_grid": [[{"letter":"C","isBlack":false}]],
  "options": {
    "min_score": 40,
    "timeout": 600
  }
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "new_task_id": "xyz789-uvw012",
  "original_task_id": "abc123-def456",
  "message": "Resumed with user edits",
  "slots_filled": 45,
  "total_slots": 76
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/fill/resume \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "abc123-def456",
    "edited_grid": [[{"letter":"C","isBlack":false}]]
  }'
```

**Error Responses**:
- `404 Not Found`: Saved state not found
- `409 Conflict`: User edits create unsolvable state

**Conflict Response** (409):
```json
{
  "error": "User edits create unsolvable state",
  "details": "Word at (5,3,across) conflicts with (3,5,down)"
}
```

**Use Cases**:
- Continue paused autofill
- Apply user corrections and resume
- Change autofill parameters mid-run

---

### Get Saved State

Get metadata and grid preview for a saved state.

**Endpoint**: `GET /api/fill/state/{task_id}`

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | string | Saved state task ID |

**Response** (200 OK):
```json
{
  "task_id": "abc123-def456",
  "timestamp": "2025-12-27T10:30:00Z",
  "algorithm": "trie",
  "slots_filled": 45,
  "total_slots": 76,
  "grid_size": [15, 15],
  "iteration_count": 1250,
  "grid_preview": [[{"letter":"C","isBlack":false}]]
}
```

**curl Example**:
```bash
curl http://localhost:5000/api/fill/state/abc123-def456
```

**Error Responses**:
- `404 Not Found`: State not found

**Use Cases**:
- Preview saved state before resuming
- Check autofill progress
- Get saved state metadata

---

### Delete Saved State

Delete a saved state file.

**Endpoint**: `DELETE /api/fill/state/{task_id}`

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | string | Saved state task ID |

**Response** (200 OK):
```json
{
  "success": true,
  "message": "State deleted"
}
```

**curl Example**:
```bash
curl -X DELETE http://localhost:5000/api/fill/state/abc123-def456
```

**Error Responses**:
- `404 Not Found`: State not found

**Use Cases**:
- Clean up unwanted saved states
- Free disk space

---

### List Saved States

List all saved autofill states with optional age filter.

**Endpoint**: `GET /api/fill/states`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `max_age_days` | integer | Only return states newer than this (in days) |

**Response** (200 OK):
```json
{
  "states": [
    {
      "task_id": "abc123-def456",
      "timestamp": "2025-12-27T10:30:00Z",
      "algorithm": "trie",
      "slots_filled": 45,
      "total_slots": 76,
      "grid_size": [15, 15]
    },
    {
      "task_id": "xyz789-uvw012",
      "timestamp": "2025-12-26T14:20:00Z",
      "algorithm": "beam",
      "slots_filled": 60,
      "total_slots": 76,
      "grid_size": [15, 15]
    }
  ],
  "count": 2
}
```

**curl Example**:
```bash
# List all states
curl http://localhost:5000/api/fill/states

# List states from last 7 days
curl http://localhost:5000/api/fill/states?max_age_days=7
```

**Use Cases**:
- View all saved states
- Find recent autofill sessions
- Audit saved state storage

---

### Cleanup Old States

Delete state files older than specified age.

**Endpoint**: `POST /api/fill/states/cleanup`

**Request Body**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_age_days` | integer | `7` | Delete states older than this (in days) |

**Request Example**:
```json
{
  "max_age_days": 7
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "deleted_count": 12,
  "message": "Deleted 12 states older than 7 days"
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/fill/states/cleanup \
  -H "Content-Type: application/json" \
  -d '{"max_age_days": 7}'
```

**Use Cases**:
- Clean up old saved states
- Free disk space
- Maintain state directory

---

### Preview Edit Summary

Get summary of user edits without performing full merge.

**Endpoint**: `POST /api/fill/edit-summary`

**Request Body**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | string | Yes | Saved state task ID |
| `edited_grid` | Grid | Yes | User-edited grid |

**Request Example**:
```json
{
  "task_id": "abc123-def456",
  "edited_grid": [[{"letter":"C","isBlack":false}]]
}
```

**Response** (200 OK):
```json
{
  "filled_count": 5,
  "emptied_count": 2,
  "modified_count": 3,
  "new_words": ["CAT", "DOG"],
  "removed_words": ["RAT", "HOG"]
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/fill/edit-summary \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "abc123-def456",
    "edited_grid": [[{"letter":"C","isBlack":false}]]
  }'
```

**Error Responses**:
- `404 Not Found`: State not found

**Use Cases**:
- Preview changes before resuming
- Show user what edits will be applied
- Validate edit impact

---

## Progress Tracking

### Stream Progress Updates

Server-Sent Events (SSE) endpoint for real-time progress updates.

**Endpoint**: `GET /api/progress/{task_id}`

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | string | Task identifier from `/api/fill/with-progress` |

**Response**: `text/event-stream` (SSE)

**Event Format**:
```
data: {"progress": 45, "message": "Processing...", "status": "running", "timestamp": 1703686200.5}

data: {"progress": 100, "message": "Complete", "status": "complete", "timestamp": 1703686300.2, "data": {"grid": [...]}}
```

**Event Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `progress` | integer | Progress percentage (0-100) |
| `message` | string | Human-readable progress message |
| `status` | string | `running`, `complete`, or `error` |
| `timestamp` | float | Unix timestamp |
| `data` | object | Result data (only on `complete`) |

**JavaScript Example**:
```javascript
const eventSource = new EventSource('http://localhost:5000/api/progress/abc123-def456');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.progress}%`);
  console.log(`Message: ${data.message}`);

  if (data.status === 'complete') {
    console.log('Grid filled:', data.data.grid);
    eventSource.close();
  } else if (data.status === 'error') {
    console.error('Error:', data.message);
    eventSource.close();
  }
};

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  eventSource.close();
};
```

**curl Example** (limited - SSE best consumed by JavaScript):
```bash
curl -N http://localhost:5000/api/progress/abc123-def456
```

**Error Responses**:
- `404 Not Found`: Task not found

**Use Cases**:
- Real-time autofill progress
- Display progress bar to user
- Get intermediate status updates

**Workflow**:
1. Start autofill with `/api/fill/with-progress`
2. Receive `task_id` in response
3. Connect to `/api/progress/{task_id}` with SSE
4. Receive progress events until complete

---

## Wordlist Management

### List Wordlists

List all available wordlists with metadata and categories.

**Endpoint**: `GET /api/wordlists`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | string | Filter by category (core, themed, custom, etc.) |

**Response** (200 OK):
```json
{
  "wordlists": [
    {
      "name": "comprehensive",
      "category": "core",
      "word_count": 250000,
      "metadata": {
        "description": "Comprehensive crossword wordlist",
        "category": "core",
        "tags": ["general", "crossword"],
        "difficulty": "medium",
        "source": "curated",
        "created": "2025-01-01T00:00:00Z",
        "updated": "2025-12-01T00:00:00Z"
      }
    },
    {
      "name": "themed/music",
      "category": "themed",
      "word_count": 5000,
      "metadata": {
        "description": "Music-related words",
        "category": "themed",
        "tags": ["music", "themed"],
        "difficulty": "easy"
      }
    }
  ],
  "categories": {
    "core": 3,
    "themed": 12,
    "custom": 5
  },
  "tags": {
    "general": 3,
    "music": 2,
    "sports": 1
  }
}
```

**curl Example**:
```bash
# List all wordlists
curl http://localhost:5000/api/wordlists

# Filter by category
curl http://localhost:5000/api/wordlists?category=themed
```

**Use Cases**:
- Browse available wordlists
- Filter by category or tags
- Get wordlist metadata

---

### Search Wordlists

Search for words matching a pattern across multiple wordlists. Returns words with their source wordlists.

**Endpoint**: `POST /api/wordlists/search`

**Request Body**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `pattern` | string | Yes | - | Pattern with `?` for wildcards |
| `wordlists` | array | No | All wordlists | Specific wordlists to search |

**Request Example**:
```json
{
  "pattern": "?A?E",
  "wordlists": ["core/common_3_letter", "themed/slang"]
}
```

**Response** (200 OK):
```json
{
  "pattern": "?A?E",
  "total_matches": 15,
  "results": [
    {
      "word": "CAKE",
      "sources": ["core/common_3_letter", "comprehensive"]
    },
    {
      "word": "CAFE",
      "sources": ["themed/slang"]
    },
    {
      "word": "CASE",
      "sources": ["core/common_3_letter"]
    }
  ]
}
```

**curl Example**:
```bash
# Search specific wordlists
curl -X POST http://localhost:5000/api/wordlists/search \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "?A?E",
    "wordlists": ["core/common_3_letter", "themed/slang"]
  }'

# Search all wordlists
curl -X POST http://localhost:5000/api/wordlists/search \
  -H "Content-Type: application/json" \
  -d '{"pattern": "????ING"}'
```

**Error Responses**:
- `400 Bad Request`: Missing pattern or invalid wordlist
- `500 Internal Server Error`: Search error

**Use Cases**:
- Find which wordlists contain specific words
- Search across themed wordlists
- Discover word sources for quality assessment

**Difference from Pattern Search**:
| Endpoint | Focus | Response |
|----------|-------|----------|
| `/api/pattern` | Find words, score by quality | Words with scores |
| `/api/wordlists/search` | Find words, group by source | Words with source wordlists |

**Tips**:
- Omit `wordlists` to search all available wordlists
- Use to identify which themed wordlists contain relevant words
- Results show all sources if word appears in multiple wordlists

---

### Get Wordlist

Get specific wordlist content and metadata.

**Endpoint**: `GET /api/wordlists/{name}`

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Wordlist name (can include category path) |

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `stats` | boolean | `false` | Include word statistics |

**Response** (200 OK):
```json
{
  "metadata": {
    "description": "Comprehensive crossword wordlist",
    "category": "core",
    "tags": ["general", "crossword"],
    "difficulty": "medium"
  },
  "words": [
    "AARDVARK",
    "ABACUS",
    "ABANDON"
  ],
  "stats": {
    "total_words": 250000,
    "length_distribution": {
      "3": 1200,
      "4": 5000,
      "5": 8000,
      "6": 12000
    },
    "avg_length": 7.2,
    "min_length": 3,
    "max_length": 21
  }
}
```

**curl Example**:
```bash
# Get wordlist
curl http://localhost:5000/api/wordlists/comprehensive

# Get wordlist with stats
curl http://localhost:5000/api/wordlists/comprehensive?stats=true

# Get themed wordlist (with category path)
curl http://localhost:5000/api/wordlists/themed/music
```

**Error Responses**:
- `404 Not Found`: Wordlist not found

**Use Cases**:
- View wordlist contents
- Get wordlist statistics
- Inspect word distribution

---

### Create Wordlist

Create a new wordlist with words and metadata.

**Endpoint**: `POST /api/wordlists/{name}`

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Wordlist name |

**Request Body**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `words` | array | Yes | List of words |
| `metadata` | object | No | Wordlist metadata |

**Request Example**:
```json
{
  "words": [
    "GUITAR",
    "PIANO",
    "DRUMS",
    "VIOLIN"
  ],
  "metadata": {
    "description": "Musical instruments",
    "category": "themed",
    "tags": ["music", "instruments"],
    "difficulty": "easy"
  }
}
```

**Response** (201 Created):
```json
{
  "message": "Wordlist created",
  "word_count": 4
}
```

**curl Example**:
```bash
curl -X POST http://localhost:5000/api/wordlists/my_instruments \
  -H "Content-Type: application/json" \
  -d '{
    "words": ["GUITAR", "PIANO", "DRUMS"],
    "metadata": {
      "description": "Musical instruments",
      "category": "themed"
    }
  }'
```

**Error Responses**:
- `400 Bad Request`: Invalid words or metadata

**Use Cases**:
- Create custom wordlists
- Upload themed word collections
- Build specialized vocabularies

---

### Update Wordlist

Update existing wordlist (replace, add, or remove words).

**Endpoint**: `PUT /api/wordlists/{name}`

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Wordlist name |

**Request Body** (choose one operation):
| Field | Type | Description |
|-------|------|-------------|
| `words` | array | Replace all words |
| `add_words` | array | Add specific words |
| `remove_words` | array | Remove specific words |
| `metadata` | object | Update metadata |

**Request Example** (add words):
```json
{
  "add_words": ["SAXOPHONE", "TRUMPET"],
  "metadata": {
    "updated": "2025-12-27T10:30:00Z"
  }
}
```

**Request Example** (replace all):
```json
{
  "words": ["GUITAR", "PIANO", "DRUMS", "VIOLIN", "SAXOPHONE"],
  "metadata": {
    "description": "Updated instrument list"
  }
}
```

**Response** (200 OK):
```json
{
  "message": "Wordlist updated"
}
```

**curl Example**:
```bash
# Add words
curl -X PUT http://localhost:5000/api/wordlists/my_instruments \
  -H "Content-Type: application/json" \
  -d '{
    "add_words": ["SAXOPHONE", "TRUMPET"]
  }'

# Remove words
curl -X PUT http://localhost:5000/api/wordlists/my_instruments \
  -H "Content-Type: application/json" \
  -d '{
    "remove_words": ["DRUMS"]
  }'
```

**Error Responses**:
- `404 Not Found`: Wordlist not found

**Use Cases**:
- Add new words to existing wordlist
- Remove unwanted words
- Update wordlist metadata

---

### Delete Wordlist

Delete a wordlist file.

**Endpoint**: `DELETE /api/wordlists/{name}`

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Wordlist name |

**Response** (200 OK):
```json
{
  "message": "Wordlist deleted"
}
```

**curl Example**:
```bash
curl -X DELETE http://localhost:5000/api/wordlists/my_instruments
```

**Error Responses**:
- `404 Not Found`: Wordlist not found

**Use Cases**:
- Delete unwanted wordlists
- Clean up temporary wordlists

---

### Get Wordlist Statistics

Get detailed statistics for a wordlist.

**Endpoint**: `GET /api/wordlists/{name}/stats`

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Wordlist name |

**Response** (200 OK):
```json
{
  "total_words": 250000,
  "length_distribution": {
    "3": 1200,
    "4": 5000,
    "5": 8000,
    "6": 12000,
    "7": 15000,
    "8": 18000,
    "9": 20000,
    "10": 22000
  },
  "avg_length": 7.2,
  "min_length": 3,
  "max_length": 21
}
```

**curl Example**:
```bash
curl http://localhost:5000/api/wordlists/comprehensive/stats
```

**Error Responses**:
- `404 Not Found`: Wordlist not found

**Use Cases**:
- Analyze wordlist composition
- Check word length distribution
- Validate wordlist quality

---

### Import Wordlist

Import wordlist from text content or URL.

**Endpoint**: `POST /api/wordlists/import`

**Request Body**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Wordlist name |
| `content` | string | No* | Newline-separated words |
| `url` | string | No* | URL to fetch wordlist from |
| `category` | string | No | Category (default: `"imports"`) |
| `metadata` | object | No | Wordlist metadata |

*One of `content` or `url` required

**Request Example** (from content):
```json
{
  "name": "my_import",
  "content": "GUITAR\nPIANO\nDRUMS\nVIOLIN",
  "category": "imports",
  "metadata": {
    "description": "Imported instruments",
    "source": "manual"
  }
}
```

**Request Example** (from URL):
```json
{
  "name": "external_wordlist",
  "url": "https://example.com/wordlists/music.txt",
  "category": "imports"
}
```

**Response** (201 Created):
```json
{
  "message": "Wordlist imported",
  "name": "my_import",
  "word_count": 4
}
```

**curl Example**:
```bash
# From content
curl -X POST http://localhost:5000/api/wordlists/import \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_import",
    "content": "GUITAR\nPIANO\nDRUMS"
  }'

# From URL
curl -X POST http://localhost:5000/api/wordlists/import \
  -H "Content-Type: application/json" \
  -d '{
    "name": "external_wordlist",
    "url": "https://example.com/wordlists/music.txt"
  }'
```

**Error Responses**:
- `400 Bad Request`: Invalid content or missing fields
- `501 Not Implemented`: URL import not yet implemented

**Use Cases**:
- Import wordlists from external sources
- Bulk upload words from files
- Integrate external wordlist repositories

---

## Common Patterns

### Grid Data Structure

All grid data uses this consistent structure:

```json
{
  "grid": [
    [
      {
        "letter": "C",
        "isBlack": false,
        "number": 1,
        "isError": false,
        "isHighlighted": false,
        "isThemeLocked": false
      },
      {
        "letter": "A",
        "isBlack": false,
        "number": null,
        "isError": false,
        "isHighlighted": false,
        "isThemeLocked": false
      },
      {
        "letter": "",
        "isBlack": true,
        "number": null,
        "isError": false,
        "isHighlighted": false,
        "isThemeLocked": false
      }
    ]
  ]
}
```

**Cell Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `letter` | string | Letter (A-Z) or empty string |
| `isBlack` | boolean | Whether cell is a black square |
| `number` | integer\|null | Clue number (1, 2, 3, ...) or null |
| `isError` | boolean | Validation error indicator |
| `isHighlighted` | boolean | UI highlight state |
| `isThemeLocked` | boolean | Theme-locked cell (cannot be modified by autofill) |

**Minimal Grid** (required fields only):
```json
{
  "grid": [
    [
      {"letter": "", "isBlack": false},
      {"letter": "", "isBlack": false}
    ]
  ]
}
```

---

### Error Response Format

All error responses follow this format:

```json
{
  "error": "Brief error message",
  "details": "Detailed error information",
  "code": "ERROR_CODE",
  "validation": {
    "valid": false,
    "errors": ["Error 1", "Error 2"],
    "warnings": ["Warning 1"]
  }
}
```

**Common HTTP Status Codes**:
| Code | Meaning | When Used |
|------|---------|-----------|
| `200` | OK | Successful request |
| `201` | Created | Resource created |
| `202` | Accepted | Async task started |
| `400` | Bad Request | Invalid input |
| `404` | Not Found | Resource not found |
| `409` | Conflict | State conflict (e.g., unsolvable edits) |
| `500` | Internal Server Error | Server error |
| `503` | Service Unavailable | CLI backend unavailable |
| `504` | Gateway Timeout | Grid numbering timeout |
| `505` | HTTP Version Not Supported | Pattern search timeout |
| `506` | Variant Also Negotiates | Normalization timeout |
| `507` | Insufficient Storage | Grid fill timeout |

---

### Server-Sent Events (SSE) Pattern

For long-running operations with progress updates:

**Step 1**: Start async operation
```bash
curl -X POST http://localhost:5000/api/fill/with-progress \
  -H "Content-Type: application/json" \
  -d '{"grid": [...], "size": 15}'

# Response: {"task_id": "abc123", "progress_url": "/api/progress/abc123"}
```

**Step 2**: Connect to SSE endpoint
```javascript
const eventSource = new EventSource('http://localhost:5000/api/progress/abc123');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.status === 'complete') {
    console.log('Result:', data.data);
    eventSource.close();
  }
};
```

**Event Lifecycle**:
1. `status: "running"` - Operation in progress
2. `status: "complete"` - Operation finished (includes result in `data` field)
3. `status: "error"` - Operation failed

---

## Constraint Analysis

### Get Grid Constraints

Analyze every white cell in the grid and return how many valid words can fill the crossing slots through it. Powers the **crossing quality heatmap** in the UI.

**Endpoint:** `POST /api/constraints`

**Request:**
```json
{
  "grid": [[".", "C", "A", "T", "."], ...],
  "wordlists": ["comprehensive"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `grid` | 2D array | Yes | Grid rows; `"."` = empty white cell, `"#"` = black square, letter = filled cell |
| `wordlists` | string[] | No | Wordlist names to use (default: `["comprehensive"]`) |

**Response:**
```json
{
  "constraints": {
    "0,0": {
      "across_options": 142,
      "down_options": 38,
      "min_options": 38
    },
    "0,1": {
      "across_options": 142,
      "down_options": 55,
      "min_options": 55
    }
  },
  "summary": {
    "total_cells": 189,
    "critical_cells": 12,
    "average_min_options": 47.3
  }
}
```

| Field | Description |
|-------|-------------|
| `constraints` | Map of `"row,col"` → per-cell data |
| `across_options` | Words that fit the across slot through this cell |
| `down_options` | Words that fit the down slot through this cell |
| `min_options` | `min(across_options, down_options)` — the bottleneck |
| `summary.critical_cells` | Cells where `min_options < 5` |

**Status Codes:** `200 OK`, `400 Bad Request` (missing grid or no valid wordlists), `500 Internal Server Error`

**UI heatmap thresholds:**

| min_options | Color | Meaning |
|-------------|-------|---------|
| < 5 | 🔴 Red | Critical — almost no words fit |
| 5–19 | 🟠 Orange | Tight |
| 20–49 | 🟡 Yellow | Moderate |
| ≥ 50 | 🟢 Green | Healthy |

---

### Get Placement Impact

Analyze how placing a specific word in a slot affects the option count of all crossing slots. Useful for evaluating candidate words before committing.

**Endpoint:** `POST /api/constraints/impact`

**Request:**
```json
{
  "grid": [[".", ".", ".", ".", "."], ...],
  "word": "OCEAN",
  "slot": {"row": 0, "col": 0, "direction": "across", "length": 5},
  "wordlists": ["comprehensive"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `grid` | 2D array | Yes | Current grid state |
| `word` | string | Yes | Word to test (case-insensitive) |
| `slot` | object | Yes | Target slot: `row`, `col`, `direction`, `length` |
| `wordlists` | string[] | No | Wordlist names (default: `["comprehensive"]`) |

**Response:**
```json
{
  "impacts": {
    "0,1,down": {"before": 142, "after": 18, "delta": -124, "length": 15},
    "0,2,down": {"before": 97,  "after": 31, "delta": -66,  "length": 15},
    "0,3,down": {"before": 110, "after": 44, "delta": -66,  "length": 15}
  },
  "summary": {
    "total_crossings": 5,
    "worst_delta": -124,
    "crossings_eliminated": 0
  }
}
```

| Field | Description |
|-------|-------------|
| `impacts` | Map of `"row,col,direction"` → impact data for each crossing slot |
| `before` | Option count before placing the word |
| `after` | Option count after placing the word |
| `delta` | `after - before` (always ≤ 0; placing a word never adds options) |
| `length` | Length of the crossing slot |
| `summary.worst_delta` | Most negative delta across all crossings |
| `summary.crossings_eliminated` | Crossings reduced to 0 options (would make grid unsolvable) |

**Status Codes:** `200 OK`, `400 Bad Request` (missing grid/word/slot fields), `500 Internal Server Error`

---

## Data Structures

### Cell

```json
{
  "letter": "C",
  "isBlack": false,
  "number": 1,
  "isError": false,
  "isHighlighted": false,
  "isThemeLocked": false
}
```

### Grid

2D array of cells (rows × columns):

```json
[
  [{"letter":"C","isBlack":false}, {"letter":"A","isBlack":false}],
  [{"letter":"T","isBlack":false}, {"letter":"","isBlack":true}]
]
```

### Position

```json
{
  "row": 0,
  "col": 5
}
```

### Slot

```json
{
  "row": 0,
  "col": 0,
  "direction": "across",
  "length": 7,
  "pattern": "C??WORD",
  "candidate_count": 25
}
```

### Theme Placement

```json
{
  "word": "PARTNERNAME",
  "row": 0,
  "col": 2,
  "direction": "across"
}
```

---

## Error Handling

### Handling Timeouts

Different operations use different HTTP status codes for timeouts:

```bash
# Pattern search timeout (505)
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{"pattern": "????????????????"}'

# Grid numbering timeout (504)
curl -X POST http://localhost:5000/api/number \
  -H "Content-Type: application/json" \
  -d '{"grid": [[...very large grid...]]}'

# Normalization timeout (506)
curl -X POST http://localhost:5000/api/normalize \
  -H "Content-Type: application/json" \
  -d '{"text": "very complex text"}'

# Grid fill timeout (507)
curl -X POST http://localhost:5000/api/fill \
  -H "Content-Type: application/json" \
  -d '{"grid": [...], "size": 15, "timeout": 10}'
```

**Recommended Handling**:
```javascript
fetch('/api/fill', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({grid: [...], size: 15})
})
.then(response => {
  if (response.status === 507) {
    // Timeout - suggest using /fill/with-progress instead
    console.log('Autofill timed out. Use /fill/with-progress for long-running fills.');
  } else if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
})
.then(data => console.log('Success:', data))
.catch(error => console.error('Error:', error));
```

### Handling Validation Errors

Validation errors include detailed field-level information:

```json
{
  "error": "Validation failed",
  "details": "Invalid grid structure",
  "validation": {
    "valid": false,
    "errors": [
      "Grid must be rectangular",
      "Cell at (5,3) missing 'isBlack' field"
    ],
    "warnings": [
      "Grid has no black squares"
    ]
  }
}
```

### Handling State Conflicts

When resuming with user edits that create conflicts:

```json
{
  "error": "User edits create unsolvable state",
  "details": "Word at (5,3,across) 'CATS' conflicts with (3,5,down) 'DOGS' at intersection (5,5)"
}
```

**Recommended Handling**:
1. Show user the conflict details
2. Offer to undo edits
3. Suggest alternative words
4. Allow user to edit again

---

## Complete Workflows

### Workflow 1: Pattern Search and Fill

```bash
# 1. Search for 4-letter words with A as 2nd letter
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{"pattern": "?A?E", "max_results": 10}'

# 2. Choose word and update grid manually
# (Frontend updates grid state)

# 3. Autofill remaining slots
curl -X POST http://localhost:5000/api/fill \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [[{"letter":"C","isBlack":false}]],
    "size": 15,
    "timeout": 300
  }'
```

### Workflow 2: Theme Word Placement

```bash
# 1. Upload theme words
curl -X POST http://localhost:5000/api/theme/upload \
  -H "Content-Type: application/json" \
  -d '{
    "content": "PARTNERNAME\nANNIVERSARY\nFAVORITEPLACE",
    "grid_size": 15
  }'

# 2. Get placement suggestions
curl -X POST http://localhost:5000/api/theme/suggest-placements \
  -H "Content-Type: application/json" \
  -d '{
    "theme_words": ["PARTNERNAME", "ANNIVERSARY", "FAVORITEPLACE"],
    "grid_size": 15,
    "max_suggestions": 3
  }'

# 3. Apply chosen placement
curl -X POST http://localhost:5000/api/theme/apply-placement \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [[{"letter":"","isBlack":false}]],
    "placement": {
      "word": "PARTNERNAME",
      "row": 0,
      "col": 2,
      "direction": "across"
    }
  }'

# 4. Autofill with theme words locked
curl -X POST http://localhost:5000/api/fill \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [[{"letter":"P","isBlack":false,"isThemeLocked":true}]],
    "size": 15,
    "theme_entries": {
      "(0,2,across)": "PARTNERNAME"
    }
  }'
```

### Workflow 3: Autofill with Progress Tracking

```javascript
// 1. Start autofill with progress
fetch('/api/fill/with-progress', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    grid: [[{letter:'',isBlack:false}]],
    size: 15
  })
})
.then(response => response.json())
.then(data => {
  // 2. Connect to SSE endpoint
  const eventSource = new EventSource(data.progress_url);

  eventSource.onmessage = (event) => {
    const progress = JSON.parse(event.data);

    // 3. Update UI with progress
    console.log(`${progress.progress}%: ${progress.message}`);

    // 4. Handle completion
    if (progress.status === 'complete') {
      console.log('Grid filled:', progress.data.grid);
      eventSource.close();
    }
  };
});
```

### Workflow 4: Pause, Edit, Resume

```bash
# 1. Start autofill with progress
TASK_ID=$(curl -X POST http://localhost:5000/api/fill/with-progress \
  -H "Content-Type: application/json" \
  -d '{"grid": [...], "size": 15}' \
  | jq -r '.task_id')

# 2. Monitor progress via SSE
# (Frontend connects to /api/progress/${TASK_ID})

# 3. Pause autofill
curl -X POST http://localhost:5000/api/fill/pause/${TASK_ID}

# 4. Get saved state
curl http://localhost:5000/api/fill/state/${TASK_ID}

# 5. User edits grid in frontend
# (Frontend allows manual edits)

# 6. Preview edit summary
curl -X POST http://localhost:5000/api/fill/edit-summary \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "'${TASK_ID}'",
    "edited_grid": [[{"letter":"C","isBlack":false}]]
  }'

# 7. Resume with edits
curl -X POST http://localhost:5000/api/fill/resume \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "'${TASK_ID}'",
    "edited_grid": [[{"letter":"C","isBlack":false}]],
    "options": {
      "min_score": 40,
      "timeout": 600
    }
  }'
```

### Workflow 5: Fix Problematic Slot

```bash
# 1. Autofill fails on specific slot
curl -X POST http://localhost:5000/api/fill \
  -H "Content-Type: application/json" \
  -d '{"grid": [...], "size": 15}'

# Response indicates slot (7,3,across) has 0 candidates

# 2. Get black square suggestions
curl -X POST http://localhost:5000/api/grid/suggest-black-square \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [[...]],
    "problematic_slot": {
      "row": 7,
      "col": 3,
      "direction": "across",
      "length": 15
    },
    "max_suggestions": 3
  }'

# 3. Apply chosen black square pair
curl -X POST http://localhost:5000/api/grid/apply-black-squares \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [[...]],
    "primary": {"row": 7, "col": 10},
    "symmetric": {"row": 7, "col": 4}
  }'

# 4. Validate new grid quality
curl -X POST http://localhost:5000/api/grid/validate \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [[...]],
    "grid_size": 15
  }'

# 5. Retry autofill
curl -X POST http://localhost:5000/api/fill \
  -H "Content-Type: application/json" \
  -d '{"grid": [...], "size": 15}'
```

### Workflow 6: Custom Wordlist Management

```bash
# 1. Create custom wordlist
curl -X POST http://localhost:5000/api/wordlists/my_music \
  -H "Content-Type: application/json" \
  -d '{
    "words": ["GUITAR", "PIANO", "DRUMS", "VIOLIN"],
    "metadata": {
      "description": "Musical instruments",
      "category": "themed",
      "tags": ["music"]
    }
  }'

# 2. Get wordlist stats
curl http://localhost:5000/api/wordlists/my_music/stats

# 3. Add more words
curl -X PUT http://localhost:5000/api/wordlists/my_music \
  -H "Content-Type: application/json" \
  -d '{
    "add_words": ["SAXOPHONE", "TRUMPET", "CLARINET"]
  }'

# 4. Use in pattern search
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "?????",
    "wordlists": ["my_music"],
    "max_results": 10
  }'

# 5. Use in autofill
curl -X POST http://localhost:5000/api/fill \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [[...]],
    "size": 15,
    "wordlists": ["comprehensive", "my_music"]
  }'
```

---

## Tips and Best Practices

### Performance Optimization

1. **Use appropriate algorithms**:
   - `trie` for most pattern searches (faster than `regex`)
   - `beam` for large grids with many constraints

2. **Limit results**:
   - Set `max_results` on pattern searches to reduce response size
   - Use pagination for large wordlist queries

3. **Use progress tracking for long operations**:
   - Always use `/api/fill/with-progress` for grids ≥15×15
   - Connect to SSE endpoint for real-time updates
   - Don't poll synchronous `/api/fill` endpoint

4. **Cache wordlists**:
   - Wordlists are loaded into memory on server startup
   - Reuse wordlist names across requests for consistency

### Error Handling

1. **Always check HTTP status codes**:
   ```javascript
   if (!response.ok) {
     const error = await response.json();
     console.error(`Error ${response.status}:`, error.error);
   }
   ```

2. **Handle timeouts gracefully**:
   - Suggest using progress tracking for slow operations
   - Offer to retry with increased timeout
   - Show user timeout parameter for transparency

3. **Validate input before sending**:
   - Check grid structure is rectangular
   - Verify all cells have required fields
   - Ensure patterns use only `?` and `A-Z`

### Grid Quality

1. **Validate grid before autofill**:
   ```bash
   curl -X POST http://localhost:5000/api/grid/validate \
     -H "Content-Type: application/json" \
     -d '{"grid": [...], "grid_size": 15}'
   ```

2. **Use adaptive mode for difficult grids**:
   ```json
   {
     "adaptive_mode": true,
     "max_adaptations": 3
   }
   ```

3. **Check word count ranges** (for 15×15):
   - Standard: 72-80 words
   - Themeless: 68-76 words
   - Very open: 60-68 words

### Theme Words

1. **Upload and validate before placement**:
   - Always use `/api/theme/upload` first
   - Check validation errors
   - Ensure word lengths fit grid size

2. **Get multiple placement suggestions**:
   - Request 3-5 suggestions per word
   - Choose based on score and reasoning
   - Consider symmetry and spacing

3. **Lock theme cells**:
   - Always set `isThemeLocked: true` on theme cells
   - Include theme entries in autofill request
   - Verify locks are preserved after autofill

### State Management

1. **Clean up old states regularly**:
   ```bash
   curl -X POST http://localhost:5000/api/fill/states/cleanup \
     -H "Content-Type: application/json" \
     -d '{"max_age_days": 7}'
   ```

2. **Preview edits before resuming**:
   ```bash
   curl -X POST http://localhost:5000/api/fill/edit-summary \
     -H "Content-Type: application/json" \
     -d '{"task_id": "...", "edited_grid": [...]}'
   ```

3. **List states to find recent sessions**:
   ```bash
   curl http://localhost:5000/api/fill/states?max_age_days=1
   ```

---

**For additional help, see**:
- [OpenAPI Specification](./openapi.yaml) - Machine-readable API spec
- [Backend Specification](../specs/BACKEND_SPEC.md) - Backend architecture
- [Architecture Overview](../ARCHITECTURE.md) - System architecture
