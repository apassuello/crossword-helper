# Crossword Helper - API Specification

## Overview

This document specifies all API endpoints for the Crossword Helper backend.

**Base URL:** `http://localhost:5000`  
**Protocol:** HTTP/1.1  
**Content-Type:** `application/json`  
**Response Format:** JSON  

---

## Endpoint Summary

| Endpoint | Method | Purpose | Response Time Target |
|----------|--------|---------|---------------------|
| `/api/pattern` | POST | Find words matching pattern | <1s |
| `/api/number` | POST | Validate/auto-number grid | <100ms |
| `/api/normalize` | POST | Normalize entry conventions | <50ms |
| `/health` | GET | Health check | <10ms |

---

## 1. Pattern Search

### Endpoint
```
POST /api/pattern
```

### Purpose
Find words matching a crossword pattern (e.g., `?I?A` for 4-letter words with I as 2nd letter, A as 4th).

### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
    "pattern": "?I?A",
    "wordlists": ["personal", "standard"],
    "max_results": 20
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `pattern` | string | Yes | - | Pattern with ? as wildcard (e.g., `?I?A`) |
| `wordlists` | array[string] | No | `["standard"]` | Word list names to search |
| `max_results` | integer | No | `20` | Maximum results to return (1-100) |

**Validation Rules:**
- `pattern` must contain at least one `?`
- `pattern` length must be 3-15 characters
- `pattern` must match regex: `^[A-Z?]+$`
- `wordlists` must reference existing files
- `max_results` must be 1-100

### Response

**Success (200 OK):**
```json
{
    "results": [
        {
            "word": "VISA",
            "score": 85,
            "source": "onelook",
            "length": 4,
            "letter_quality": {
                "common": 3,
                "uncommon": 1
            }
        },
        {
            "word": "PITA",
            "score": 80,
            "source": "onelook",
            "length": 4,
            "letter_quality": {
                "common": 3,
                "uncommon": 1
            }
        },
        {
            "word": "KIWI",
            "score": 70,
            "source": "personal",
            "length": 4,
            "letter_quality": {
                "common": 2,
                "uncommon": 2
            }
        }
    ],
    "meta": {
        "pattern": "?I?A",
        "total_found": 127,
        "results_returned": 20,
        "query_time_ms": 245,
        "sources_queried": ["onelook", "personal", "standard"]
    }
}
```

**Result Object Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `word` | string | The matching word (uppercase) |
| `score` | integer | Crossword-ability score (1-100, higher is better) |
| `source` | string | Where word was found: `"onelook"`, `"personal"`, `"standard"` |
| `length` | integer | Word length (for quick reference) |
| `letter_quality.common` | integer | Count of common letters (EARIOTNS) |
| `letter_quality.uncommon` | integer | Count of uncommon letters (JQXZ) |

**Scoring Algorithm:**
```
score = base_letter_score + length_bonus - uncommon_penalty

base_letter_score = (common_letters * 10) + (regular_letters * 5)
length_bonus = length * 2
uncommon_penalty = (J/Q/X/Z count) * 15

Final score: clamp(1, score, 100)
```

**Error Responses:**

**400 Bad Request - Invalid Pattern:**
```json
{
    "error": {
        "code": "INVALID_PATTERN",
        "message": "Pattern must contain at least one ? wildcard",
        "details": {
            "received": "ABCD",
            "expected_format": "?I?A or A?C? or ????"
        }
    }
}
```

**400 Bad Request - Pattern Too Long:**
```json
{
    "error": {
        "code": "PATTERN_TOO_LONG",
        "message": "Pattern exceeds maximum length of 15 characters",
        "details": {
            "received_length": 18,
            "max_length": 15
        }
    }
}
```

**404 Not Found - Wordlist Not Found:**
```json
{
    "error": {
        "code": "WORDLIST_NOT_FOUND",
        "message": "Word list 'custom' not found",
        "details": {
            "requested": "custom",
            "available": ["personal", "standard"]
        }
    }
}
```

**503 Service Unavailable - OneLook Timeout:**
```json
{
    "error": {
        "code": "ONELOOK_UNAVAILABLE",
        "message": "OneLook API is unavailable, using local word lists only",
        "details": {
            "timeout_seconds": 5,
            "fallback_used": true
        }
    }
}
```

### Examples

**Example 1: Basic pattern search**
```bash
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{"pattern": "?I?A"}'
```

**Example 2: Search with custom wordlist**
```bash
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "???E?",
    "wordlists": ["personal"],
    "max_results": 10
  }'
```

**Example 3: Long pattern**
```bash
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{"pattern": "?A?P?E?R?E?"}'
```

---

## 2. Numbering Validation

### Endpoint
```
POST /api/number
```

### Purpose
Automatically number a crossword grid according to standard rules, or validate existing numbering.

### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
    "grid": [
        ["R", "A", "S", "P", "#", "Y", "O", "G", "A"],
        ["#", "T", "#", "#", "B", "#", "#", "#", "L"],
        ["C", "A", "T", "#", "#", "#", "D", "O", "G"]
    ],
    "user_numbering": {
        "(0,0)": 1,
        "(0,5)": 2,
        "(2,0)": 3
    }
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `grid` | array[array[string]] | Yes | 2D array representing grid |
| `user_numbering` | object | No | User's numbering to validate |

**Grid Cell Values:**
- `"A-Z"`: Filled letter
- `"#"`: Black square
- `"."`: Empty white square

**Numbering Format:**
- Keys: `"(row,col)"` as strings (0-indexed)
- Values: Numbers (1, 2, 3, ...)

**Validation Rules:**
- Grid must be square (n×n)
- Grid size must be 11×11, 15×15, or 21×21
- Grid must contain only A-Z, #, or .
- Numbering positions must be valid grid coordinates
- Numbering values must be positive integers

### Response

**Success (200 OK):**
```json
{
    "numbering": {
        "(0,0)": 1,
        "(0,5)": 2,
        "(0,8)": 3,
        "(1,1)": 4,
        "(2,0)": 5,
        "(2,6)": 6
    },
    "validation": {
        "is_valid": true,
        "errors": []
    },
    "grid_info": {
        "size": [9, 9],
        "black_squares": 6,
        "white_squares": 75,
        "word_count": 8,
        "black_square_percentage": 7.4,
        "meets_nyt_standards": true
    },
    "meta": {
        "numbering_method": "standard_left_to_right",
        "computation_time_ms": 12
    }
}
```

**With Validation Errors (200 OK but is_valid=false):**
```json
{
    "numbering": {
        "(0,0)": 1,
        "(0,5)": 2,
        "(0,8)": 3
    },
    "validation": {
        "is_valid": false,
        "errors": [
            {
                "type": "MISSING_NUMBER",
                "position": "(1,1)",
                "expected": 4,
                "message": "Cell at (1,1) should be numbered 4 (starts both across and down)"
            },
            {
                "type": "WRONG_NUMBER",
                "position": "(2,0)",
                "expected": 5,
                "actual": 3,
                "message": "Cell at (2,0) has number 3 but should be 5"
            }
        ]
    },
    "grid_info": { /* ... */ },
    "meta": { /* ... */ }
}
```

**Grid Info Fields:**

| Field | Description |
|-------|-------------|
| `size` | `[rows, cols]` |
| `black_squares` | Count of black squares |
| `white_squares` | Count of white squares |
| `word_count` | Total number of words (across + down) |
| `black_square_percentage` | Percentage of grid that's black |
| `meets_nyt_standards` | Boolean: black squares <16%, word count <78 (for 15×15) |

**Error Responses:**

**400 Bad Request - Invalid Grid:**
```json
{
    "error": {
        "code": "INVALID_GRID",
        "message": "Grid must be square",
        "details": {
            "received_dimensions": [9, 10],
            "valid_sizes": [[11, 11], [15, 15], [21, 21]]
        }
    }
}
```

**400 Bad Request - Invalid Grid Size:**
```json
{
    "error": {
        "code": "INVALID_GRID_SIZE",
        "message": "Grid size must be 11×11, 15×15, or 21×21",
        "details": {
            "received": [13, 13],
            "valid_sizes": [11, 15, 21]
        }
    }
}
```

**400 Bad Request - Invalid Cell Value:**
```json
{
    "error": {
        "code": "INVALID_CELL_VALUE",
        "message": "Grid contains invalid cell value",
        "details": {
            "position": [2, 3],
            "value": "?",
            "valid_values": ["A-Z", "#", "."]
        }
    }
}
```

### Numbering Algorithm Specification

**Rules:**
1. Scan grid left-to-right, top-to-bottom
2. For each white cell (not #):
   - Check if it starts an across word:
     - Cell to the left is black OR at left edge
     - AND cell to the right exists and is not black
   - Check if it starts a down word:
     - Cell above is black OR at top edge
     - AND cell below exists and is not black
   - If starts across OR down: assign next number
3. Numbers increment sequentially (1, 2, 3, ...)
4. Each cell gets at most one number

### Examples

**Example 1: Auto-number grid**
```bash
curl -X POST http://localhost:5000/api/number \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [
      ["R","A","T"],
      ["#","T","#"],
      ["C","A","T"]
    ]
  }'
```

**Example 2: Validate user numbering**
```bash
curl -X POST http://localhost:5000/api/number \
  -H "Content-Type: application/json" \
  -d '{
    "grid": [["R","A","T"],["#","T","#"],["C","A","T"]],
    "user_numbering": {"(0,0)": 1, "(0,1)": 2, "(2,0)": 3}
  }'
```

---

## 3. Convention Normalization

### Endpoint
```
POST /api/normalize
```

### Purpose
Normalize crossword entries according to standard conventions (e.g., "Tina Fey" → "TINAFEY").

### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
    "text": "Tina Fey"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Entry to normalize |

**Validation Rules:**
- `text` must not be empty
- `text` length must be 1-50 characters
- `text` should contain only letters, spaces, hyphens, apostrophes

### Response

**Success (200 OK):**
```json
{
    "original": "Tina Fey",
    "normalized": "TINAFEY",
    "rule": {
        "type": "two_word_names",
        "description": "Remove space between words, capitalize all",
        "pattern": "^[A-Z][a-z]+ [A-Z][a-z]+$",
        "examples": [
            {
                "input": "Tracy Jordan",
                "output": "TRACYJORDAN"
            },
            {
                "input": "Real Madrid",
                "output": "REALMADRID"
            },
            {
                "input": "Mad Men",
                "output": "MADMEN"
            }
        ]
    },
    "alternatives": [],
    "confidence": "high"
}
```

**With Alternatives:**
```json
{
    "original": "La haine",
    "normalized": "LAHAINE",
    "rule": {
        "type": "title_with_article",
        "description": "Remove space after article (La/Le/The)",
        "pattern": "^(La|Le|The|A|An) ",
        "examples": [
            {
                "input": "La haine",
                "output": "LAHAINE"
            },
            {
                "input": "The Office",
                "output": "THEOFFICE"
            }
        ]
    },
    "alternatives": [
        {
            "form": "LA HAINE",
            "note": "Keep space for very long entries (15+ letters)",
            "confidence": "low"
        }
    ],
    "confidence": "high"
}
```

**Rule Types:**

| Rule Type | Pattern | Example |
|-----------|---------|---------|
| `two_word_names` | Two capitalized words | Tina Fey → TINAFEY |
| `title_with_article` | Starts with La/Le/The/A/An | La haine → LAHAINE |
| `hyphenated` | Contains hyphen | self-aware → SELFAWARE |
| `apostrophe` | Contains apostrophe | driver's → DRIVERS |
| `default` | No special pattern | Any Text → ANYTEXT |

**Confidence Levels:**
- `"high"`: Clear rule match, standard case
- `"medium"`: Rule matches but edge case possible
- `"low"`: Ambiguous, alternatives likely

**Error Responses:**

**400 Bad Request - Empty Text:**
```json
{
    "error": {
        "code": "EMPTY_TEXT",
        "message": "Text cannot be empty",
        "details": {}
    }
}
```

**400 Bad Request - Text Too Long:**
```json
{
    "error": {
        "code": "TEXT_TOO_LONG",
        "message": "Text exceeds maximum length of 50 characters",
        "details": {
            "received_length": 63,
            "max_length": 50
        }
    }
}
```

### Examples

**Example 1: Two-word name**
```bash
curl -X POST http://localhost:5000/api/normalize \
  -H "Content-Type: application/json" \
  -d '{"text": "Tina Fey"}'
```

**Example 2: Title with article**
```bash
curl -X POST http://localhost:5000/api/normalize \
  -H "Content-Type: application/json" \
  -d '{"text": "La haine"}'
```

**Example 3: Hyphenated word**
```bash
curl -X POST http://localhost:5000/api/normalize \
  -H "Content-Type: application/json" \
  -d '{"text": "self-aware"}'
```

---

## 4. Health Check

### Endpoint
```
GET /health
```

### Purpose
Verify server is running and responsive.

### Request

**No body required.**

### Response

**Success (200 OK):**
```json
{
    "status": "healthy",
    "timestamp": "2024-11-18T10:30:00Z",
    "version": "1.0.0",
    "services": {
        "onelook_api": "available",
        "wordlists": "loaded"
    }
}
```

**Degraded (200 OK with warnings):**
```json
{
    "status": "degraded",
    "timestamp": "2024-11-18T10:30:00Z",
    "version": "1.0.0",
    "services": {
        "onelook_api": "unavailable",
        "wordlists": "loaded"
    },
    "warnings": [
        "OneLook API is not responding, pattern search will use local only"
    ]
}
```

### Example

```bash
curl http://localhost:5000/health
```

---

## Error Handling

### Standard Error Response Format

All errors follow this format:

```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable message",
        "details": {
            /* context-specific details */
        }
    }
}
```

### HTTP Status Codes

| Status | Usage |
|--------|-------|
| 200 | Success (or degraded success with warnings) |
| 400 | Bad Request (validation error) |
| 404 | Not Found (resource doesn't exist) |
| 500 | Internal Server Error (unexpected error) |
| 503 | Service Unavailable (temporary failure) |

### Common Error Codes

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `INVALID_PATTERN` | 400 | Pattern format is invalid |
| `PATTERN_TOO_LONG` | 400 | Pattern exceeds max length |
| `WORDLIST_NOT_FOUND` | 404 | Requested wordlist doesn't exist |
| `INVALID_GRID` | 400 | Grid format is invalid |
| `INVALID_GRID_SIZE` | 400 | Grid size not supported |
| `INVALID_CELL_VALUE` | 400 | Grid contains invalid character |
| `EMPTY_TEXT` | 400 | Text input is empty |
| `TEXT_TOO_LONG` | 400 | Text exceeds max length |
| `ONELOOK_UNAVAILABLE` | 503 | OneLook API is down |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## CORS Configuration

### Allowed Origins
- `http://localhost:5000` (same origin)
- `http://127.0.0.1:5000` (localhost alias)

### Allowed Methods
- `GET`, `POST`, `OPTIONS`

### Allowed Headers
- `Content-Type`, `Authorization` (for future use)

### Example Preflight Response

**Request:**
```
OPTIONS /api/pattern HTTP/1.1
Origin: http://localhost:5000
Access-Control-Request-Method: POST
Access-Control-Request-Headers: Content-Type
```

**Response:**
```
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: http://localhost:5000
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
Access-Control-Max-Age: 3600
```

---

## Rate Limiting

### Current Implementation
**No rate limiting** for MVP (local use only).

### Future Considerations
If deployed online:
- 100 requests/hour per IP
- 1000 requests/day per IP
- OneLook API: 1 request/second (respect their limits)

---

## Versioning

### Current Version
**v1.0.0** (MVP)

### Versioning Strategy
- **Major version** (X.0.0): Breaking API changes
- **Minor version** (1.X.0): New features, backward compatible
- **Patch version** (1.0.X): Bug fixes

### Future Versioning
If API changes needed, use URL versioning:
- `/api/v1/pattern` (current)
- `/api/v2/pattern` (future breaking changes)

---

## Testing the API

### Using curl

**Pattern search:**
```bash
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{"pattern": "?I?A"}' | jq
```

**Numbering:**
```bash
curl -X POST http://localhost:5000/api/number \
  -H "Content-Type: application/json" \
  -d '{"grid": [["R","A","T"],["#","T","#"],["C","A","T"]]}' | jq
```

**Normalize:**
```bash
curl -X POST http://localhost:5000/api/normalize \
  -H "Content-Type: application/json" \
  -d '{"text": "Tina Fey"}' | jq
```

### Using Python

```python
import requests

# Pattern search
response = requests.post('http://localhost:5000/api/pattern', json={
    'pattern': '?I?A',
    'max_results': 10
})
print(response.json())

# Numbering
response = requests.post('http://localhost:5000/api/number', json={
    'grid': [['R','A','T'],['#','T','#'],['C','A','T']]
})
print(response.json())

# Normalize
response = requests.post('http://localhost:5000/api/normalize', json={
    'text': 'Tina Fey'
})
print(response.json())
```

---

## Appendix: Data Formats

### Grid JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["grid"],
  "properties": {
    "grid": {
      "type": "array",
      "items": {
        "type": "array",
        "items": {
          "type": "string",
          "pattern": "^[A-Z#.]$"
        }
      }
    },
    "user_numbering": {
      "type": "object",
      "patternProperties": {
        "^\\(\\d+,\\d+\\)$": {
          "type": "integer",
          "minimum": 1
        }
      }
    }
  }
}
```

### Word List File Format

```
# personal.txt
# One word per line, uppercase
# Lines starting with # are comments

RASPBERRIES
EVERYTHING
CANYONING
YOGA
GREEN
```
