# Mermaid Diagram Reference Guide

Complete reference for the three professional Mermaid diagrams created to visualize the Crossword Helper architecture.

---

## Overview

Three diagrams visualize different aspects of the system architecture:

1. **System Component Diagram** - High-level system structure (Frontend → Backend → CLI)
2. **Autofill Data Flow Diagram** - Sequence of events during autofill operation
3. **Backend Architecture Diagram** - Internal structure of Flask backend

---

## Diagram 1: System Component Diagram

### Purpose
Shows the three-tier architecture: React Frontend → Flask Backend → CLI Tool, with external resources.

### Visual Structure
```
┌─ User's Browser (React Frontend)
├─ Flask Backend (API + CLIAdapter)
├─ CLI Tool (Commands + Core Modules)
└─ External Resources (Wordlists, State, Progress)
```

### Key Components Shown

**Frontend Layer:**
- React application (Vite build)
- 4 main UI components: Grid Editor, Autofill Panel, Wordlist Manager, Pattern Matcher
- Uses HTTP + Server-Sent Events to communicate with backend

**Backend Layer:**
- API Layer: 6 Flask blueprints handling 20+ endpoints
- CLIAdapter: Subprocess manager for executing CLI commands
- Receives requests, validates, delegates to CLI

**CLI Layer:**
- Click commands (8 total): new, fill, pattern, number, normalize, validate, wordlists, export
- Core modules: Grid Engine, Autofill, Pattern Matching, Word List, Export
- Single source of truth for all business logic

**External Resources:**
- Wordlists: 454k+ words in TSV format
- State Files: Gzipped JSON for pause/resume
- Progress Files: Real-time status updates

### Data Flow Direction
- User → Frontend: User interactions
- Frontend → Backend: HTTP + SSE (REST API calls + progress streaming)
- Backend → CLI: subprocess.run() with JSON stdin/stdout
- CLI → Files: Read/write wordlists, state, progress

### Color Coding
- **Blue** = Frontend/Browser layer
- **Orange** = Backend/API layer
- **Purple** = Core logic/CLI layer
- **Green** = Data storage layer

### What It Shows
✅ Three-tier separation of concerns
✅ CLI as single source of truth
✅ Integration points between components
✅ External dependencies
✅ Communication protocols (HTTP, subprocess, file I/O)

### What It Doesn't Show
❌ Specific endpoint names (see Backend diagram for that)
❌ Autofill algorithm details (see Data Flow diagram)
❌ Internal module dependencies

---

## Diagram 2: Autofill Data Flow (Sequence Diagram)

### Purpose
Shows the complete sequence of events when user initiates autofill, from UI click through progress updates to completion.

### Visual Structure
```
User → Frontend → Backend → CLI Process ↔ Filesystem
(with parallel progress monitoring and SSE streaming)
```

### Sequence Phases

**Phase 1: User Initiation**
1. User clicks "Start Autofill" button
2. Frontend collects: algorithm, wordlists, timeout, min_score, theme entries
3. Frontend sends POST /api/fill with grid data

**Phase 2: Backend Preparation**
4. Backend receives request
5. Backend validates: grid format, parameters, wordlist paths
6. Backend spawns subprocess with CLI command

**Phase 3: CLI Execution Begins**
7. CLI loads grid from JSON
8. CLI loads wordlists into trie (454k words)
9. CLI initializes Beam Search algorithm
10. CLI enters autofill loop:
    - Select empty slot (Most Constrained Variable heuristic)
    - Pattern match to get candidate words
    - Score candidates (Least Constraining Value heuristic)
    - Try top candidate
    - Check constraints using AC-3
    - Write progress file (every 100 iterations)
    - Check for pause signal

**Phase 4: Progress Monitoring (Parallel)**
- Backend monitors progress file every 500ms
- Sends SSE updates to frontend: iteration count, slots filled, time
- Frontend updates UI: progress bar, statistics, elapsed time

**Phase 5: Completion**
- **Success Path:**
  - CLI finishes filling grid
  - Returns filled grid JSON
  - Backend sends final SSE: `status: complete`
  - Frontend displays filled grid, updates state

- **Failure Path:**
  - CLI timeout OR unfillable slot found
  - Returns problematic slots list
  - Backend sends SSE: `status: error`
  - Frontend highlights unfillable regions, suggests fixes

### Key Details Shown

**Data Passed:**
- Request: `{grid, algorithm, wordlists, timeout, min_score, theme_entries}`
- Progress: `{iteration, slots_filled, total_slots, time_elapsed}`
- Result: `{filled_grid}` or `{error, problematic_slots}`

**Subprocess Command:**
```
crossword fill /tmp/grid_abc123.json \
  --algorithm hybrid \
  --wordlists /data/wordlists/comprehensive.txt \
  --timeout 300 \
  --min-score 30 \
  --progress-file /tmp/progress_abc123.json \
  --json-output
```

**Parallel Streams:**
- Main: CLI fills grid
- Monitor: Backend reads progress file, streams to frontend
- Signal: Pause signal file checked every 100 iterations

### Color Coding
- **Blue** = User/Frontend
- **Orange** = Backend server
- **Purple** = CLI subprocess
- **Green** = Filesystem operations

### What It Shows
✅ Complete request/response cycle
✅ Parallel progress monitoring with SSE
✅ File I/O operations during execution
✅ Both success and failure paths
✅ Timing of progress updates

### What It Doesn't Show
❌ Details of CSP/Beam Search algorithm
❌ Constraint propagation logic
❌ Word scoring algorithms
❌ Pause/resume mechanism (see separate doc: PAUSE_RESUME_ARCHITECTURE.md)

---

## Diagram 3: Flask Backend Architecture

### Purpose
Shows the internal structure of the Flask backend: 6 blueprints (API routes) and core layer modules with their dependencies.

### Visual Structure
```
API Layer (6 Blueprints)
    ↓
Core Layer (5 Adapter/Helper Modules)
    ↓
Data Layer (File I/O)
```

### API Layer (Request Handlers)

**routes.py** (Core Endpoints)
- `POST /api/pattern` - Pattern search
- `POST /api/number` - Grid numbering
- `POST /api/normalize` - Convention normalization
- `POST /api/fill` - Autofill grid
- `GET /api/health` - Health check

**grid_routes.py** (Grid Management)
- `POST /api/grid/update` - Update grid cells
- `POST /api/grid/suggest-black-squares` - Strategic black square suggestions
- `POST /api/grid/validate` - Validate grid constraints

**theme_routes.py** (Theme Entry Handling)
- `POST /api/theme/place` - Place theme words
- `POST /api/theme/lock` - Lock/unlock theme entries
- `GET /api/theme/analyze` - Analyze theme compatibility

**pause_resume_routes.py** (Pause/Resume Operations)
- `POST /api/fill/pause` - Pause running autofill
- `POST /api/fill/resume` - Resume with edits
- `GET /api/fill/states` - List saved states
- `GET /api/fill/state/:id` - Get state details
- `POST /api/fill/state/:id/edit-summary` - Analyze edits
- `DELETE /api/fill/state/:id` - Delete state

**wordlist_routes.py** (Word List Management)
- `GET /api/wordlists` - List available wordlists
- `POST /api/wordlists/upload` - Upload custom wordlist
- `GET /api/wordlists/:name/stats` - Get wordlist statistics
- `POST /api/wordlists/:name/add-word` - Add word to list

**progress_routes.py** (Real-Time Streaming)
- `GET /api/progress/:task_id` - SSE stream for progress updates

### Core Layer (Business Logic)

**CLIAdapter** (Central Integration Point)
- Executes CLI commands via subprocess
- Methods: `pattern()`, `number()`, `fill()`, `fill_with_resume()`
- Used by: routes, grid_routes, theme_routes, pause_resume_routes
- Returns: Parsed JSON from CLI

**EditMerger** (Grid Edit Validation)
- Validates user edits made during pause
- Runs AC-3 constraint propagation
- Detects unsolvable constraints
- Used by: pause_resume_routes
- Returns: Valid edits or error messages

**ThemePlacer** (Theme Word Placement)
- Suggests optimal positions for theme words
- Analyzes grid connectivity
- Used by: theme_routes
- Returns: Placement suggestions with scores

**BlackSquareSuggester** (Black Square Recommendations)
- Suggests strategic "cheater squares"
- Resolves unfillable regions
- Maintains symmetry
- Used by: grid_routes
- Returns: Sorted suggestions with impact scores

**WordlistResolver** (Path Resolution)
- Resolves wordlist names to file paths
- Validates wordlist existence
- Used by: wordlist_routes, routes, all others needing wordlist access
- Returns: Full filesystem paths

### Data Layer (File I/O)

**File I/O Operations:**
- Wordlist loading (read TSV files)
- Progress streaming (read/write progress JSON)
- State persistence (serialize/deserialize algorithm state)
- User uploads (validate and store wordlist files)

### Dependencies Shown

**Vertical Dependencies (Top to Bottom):**
- API routes delegate to core modules
- Core modules coordinate file I/O
- File I/O handles persistence

**Horizontal Dependencies (Within Core):**
- Adapter is used by most routes
- ThemePlacer uses WordlistResolver
- Merger uses FileIO for edit tracking
- Suggester uses FileIO for state inspection

### Color Coding
- **Orange** = API Layer (request handlers)
- **Purple** = Core Layer (business logic)
- **Green** = Data Layer (persistence)
- **Highlighted** = CLIAdapter (central integration point)

### What It Shows
✅ All 6 blueprints and their grouped endpoints
✅ Core module dependencies
✅ Data flow through layers
✅ Which routes use which core modules
✅ Separation of concerns

### What It Doesn't Show
❌ Specific validation rules (see validators.py)
❌ Error handling details
❌ Caching mechanisms
❌ Security implementations

---

## Reading These Diagrams

### For Understanding System Structure
1. Start with **Diagram 1: System Components**
2. Understand three-tier architecture
3. Identify key integration points

### For Debugging a Feature
1. Find feature in **Diagram 3: Backend API**
2. Trace to core module handling it
3. Understand dependencies on other modules
4. Check if Diagram 2 data flow applies

### For Performance Analysis
1. Reference **Diagram 2: Autofill Data Flow**
2. Identify which phase is slow
3. Use **Diagram 1** to understand subprocess overhead
4. Check **Diagram 3** for caching opportunities

### For Testing
1. Use **Diagram 3** to identify test boundaries
2. Mock layers shown (e.g., mock CLI subprocess)
3. Test each module independently using **Diagram 3** dependencies
4. Use **Diagram 2** for end-to-end test scenarios

---

## Integration with Existing Documentation

### Cross-References
- **System Overview (Diagram 1)** references Section 2 of ARCHITECTURE.md
- **Autofill Process (Diagram 2)** replaces Section 5.2
- **Backend API (Diagram 3)** enhances Section 4.2

### Complementary Documents
- **PAUSE_RESUME_ARCHITECTURE.md** - Details pause/resume flow (subset of Diagram 2)
- **API_SPECIFICATION.md** - Detailed endpoint contracts (referenced by Diagram 3)
- **ROADMAP.md** - Feature evolution (context for all diagrams)

### ASCII vs. Mermaid
- Original ASCII diagrams are still useful for offline reference
- Mermaid diagrams render better in web viewers
- Both provide same conceptual information
- Mermaid diagrams are easier to update

---

## Customization Guide

### Modifying Diagram 1 (System Components)

**To show more detail:**
- Expand `React["..."]` to list specific components
- Break Backend into more subgraphs (API vs Core vs Data)
- Add specific filenames for wordlist types

**To simplify:**
- Remove individual components, just show layer names
- Combine "Wordlists, State, Progress" into single "External Resources" box
- Remove internal module breakdown

### Modifying Diagram 2 (Autofill Sequence)

**To show pause/resume:**
- Add additional actor `User` for "Click Pause"
- Insert pause signal flow before completion

**To show error cases:**
- Add separate `else` path for timeout vs. unsolvable

**To simplify:**
- Remove `par` block (parallel progress monitoring)
- Remove internal CLI loop details

### Modifying Diagram 3 (Backend Architecture)

**To show all 20+ endpoints:**
- Expand blueprint subgraphs with full endpoint lists
- Use smaller font for endpoint names

**To show module relationships:**
- Add more explicit arrows showing data flow
- Add annotations (e.g., "uses LRU cache")

**To reorganize:**
- Group blueprints by function (fill-related, wordlist-related, etc.)
- Create separate "Helpers" subgraph for shared utilities

---

## Technical Notes

### Mermaid Version Compatibility
- Tested with Mermaid 10.6+ (latest)
- Works with GitHub markdown rendering
- Works with Jupyter notebooks
- Works with Sphinx documentation

### Rendering Considerations
- Diagrams responsive to container width
- All text scales appropriately
- Colors accessible (not pure white/black contrast)
- No emoji used (accessibility)

### Performance
- Diagrams render instantly (< 1s)
- No external dependencies needed
- Works in any Markdown-to-HTML renderer

---

## Version History

**Version 1.0** (2025-12-27)
- Initial diagrams created
- All three core architecture diagrams
- Reference documentation
- Customization guide

---

## Related Resources

- **ARCHITECTURE.md** - Master architecture document
- **PAUSE_RESUME_ARCHITECTURE.md** - Detailed pause/resume design
- **ADAPTIVE_FEATURES_PLAN.md** - Future feature roadmap
- **API_SPECIFICATION.md** - Detailed endpoint contracts
- **ROADMAP.md** - Development phases and timeline

