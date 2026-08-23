# Mermaid Diagrams for ARCHITECTURE.md

This file contains three professional Mermaid diagrams that replace ASCII art sections in ARCHITECTURE.md. Copy the diagram code into the appropriate section.

---

## 1. System Component Diagram (Replaces Section 2: System Overview)

**Location in ARCHITECTURE.md:** Lines 62-122 (Three-Component Architecture section)

**Replace:** The entire ASCII diagram from `┌─────────────────────────────────────────────────────────┐` through `└───────────────────────────────────────────────────────────┘`

```mermaid
graph TB
    subgraph Browser["User's Browser"]
        React["<b>React Frontend</b><br/>Vite + React 18<br/>- Grid Editor<br/>- Autofill Panel<br/>- Wordlist Manager<br/>- Pattern Matcher"]
    end

    subgraph Backend["Flask Backend<br/>localhost:5000"]
        API["<b>API Layer</b><br/>6 blueprints<br/>20+ endpoints<br/>Request validation<br/>SSE streaming"]
        Adapter["<b>CLIAdapter</b><br/>Subprocess Manager<br/>JSON communication<br/>100-300ms overhead"]
    end

    subgraph CLI["CLI Tool<br/>Single Source of Truth"]
        Commands["<b>CLI Commands</b><br/>Click framework<br/>8 commands"]
        Core["<b>Core Modules</b><br/>Grid Engine<br/>Autofill Engine<br/>Pattern Matcher<br/>Word List Manager<br/>Export Engine"]
    end

    subgraph Data["External Resources"]
        Wordlists["Word Lists<br/>454k+ words"]
        State["State Files<br/>Pause/Resume"]
        Progress["Progress Files<br/>Real-time status"]
    end

    React -->|HTTP + SSE<br/>REST API & Progress| API
    API -->|delegates to| Adapter
    Adapter -->|subprocess.run<br/>stdin/stdout JSON| Commands
    Commands --> Core
    Core -->|reads/writes| Wordlists
    Core -->|serializes| State
    Core -->|updates| Progress

    style React fill:#e1f5ff
    style API fill:#fff3e0
    style Adapter fill:#fff3e0
    style Commands fill:#f3e5f5
    style Core fill:#f3e5f5
    style Wordlists fill:#e8f5e9
    style State fill:#e8f5e9
    style Progress fill:#e8f5e9
```

---

## 2. Autofill Data Flow Diagram (Replaces Section 5.2: Autofill Process)

**Location in ARCHITECTURE.md:** Lines 584-643 (Autofill Process - Detailed section)

**Replace:** The entire ASCII diagram from `1. User clicks "Start Autofill" button` through `└─► Frontend: Highlight unfillable regions, suggest fixes`

```mermaid
sequenceDiagram
    actor User
    participant Frontend as React Frontend
    participant Backend as Flask Backend
    participant CLI as CLI Process
    participant Files as Filesystem

    User->>Frontend: Click "Start Autofill"<br/>Select algorithm, wordlists
    Frontend->>Backend: POST /api/fill<br/>(grid, params, theme entries)
    Backend->>Backend: Validate request<br/>Resolve wordlist paths

    Backend->>CLI: subprocess.run()<br/>crossword fill --algorithm hybrid
    CLI->>Files: Load grid from JSON
    CLI->>Files: Load wordlists (454k words)
    CLI->>CLI: Initialize Beam Search

    par Autofill Loop
        CLI->>CLI: Select empty slot (MCV)
        CLI->>CLI: Pattern match → candidates
        CLI->>CLI: Score candidates (LCV)
        CLI->>CLI: Try top candidate
        CLI->>CLI: Check constraints (AC-3)
        CLI->>Files: Write progress (every 100 iter)
        CLI->>Files: Check pause signal
    end

    Backend->>Files: Monitor progress file<br/>(every 500ms)
    Backend->>Frontend: SSE: {"status":"running",<br/>"iteration":5432}
    Frontend->>Frontend: Update progress bar<br/>Show stats

    alt Success
        CLI->>Files: Write filled grid
        Backend->>Frontend: SSE: {"status":"complete"}
        Frontend->>User: Display filled grid
    else Timeout/Failure
        CLI->>Files: Write problematic slots
        Backend->>Frontend: SSE: {"status":"error"}
        Frontend->>User: Highlight unfillable regions
    end

    style User fill:#e1f5ff
    style Frontend fill:#e1f5ff
    style Backend fill:#fff3e0
    style CLI fill:#f3e5f5
    style Files fill:#e8f5e9
```

---

## 3. Flask Backend Architecture Diagram (Replaces Section 4.2: Backend API)

**Location in ARCHITECTURE.md:** Lines 295-407 (Backend API section, specifically under API Endpoints)

**Replace:** Create a new subsection after the "API Endpoints" list with this diagram:

```mermaid
graph LR
    subgraph APILayer["API Layer<br/>6 Blueprints"]
        Routes["routes.py<br/>Core endpoints<br/>- pattern<br/>- number<br/>- normalize<br/>- fill"]
        Grid["grid_routes.py<br/>Grid endpoints<br/>- update<br/>- suggest-black<br/>- validate"]
        Theme["theme_routes.py<br/>Theme endpoints<br/>- place<br/>- lock<br/>- analyze"]
        PauseResume["pause_resume_routes.py<br/>Pause/Resume<br/>- pause<br/>- resume<br/>- list states"]
        Wordlist["wordlist_routes.py<br/>Wordlist endpoints<br/>- list<br/>- upload<br/>- stats<br/>- add-word"]
        Progress["progress_routes.py<br/>Progress stream<br/>- SSE endpoint"]
    end

    subgraph CoreLayer["Core Layer<br/>Business Logic"]
        Adapter["<b>CLIAdapter</b><br/>Subprocess manager<br/>- pattern()<br/>- number()<br/>- fill()<br/>- fill_with_resume()"]
        Merger["EditMerger<br/>Grid edit validation<br/>AC-3 constraint check"]
        Placer["ThemePlacer<br/>Theme placement<br/>Optimal positioning"]
        Suggester["BlackSquareSuggester<br/>Strategic suggestions<br/>Symmetry validation"]
        Resolver["WordlistResolver<br/>Path resolution<br/>Validation"]
    end

    subgraph DataLayer["Data Layer<br/>I/O"]
        FileIO["File I/O<br/>- Wordlist loading<br/>- Progress streaming<br/>- State persistence"]
    end

    Routes --> Adapter
    Grid --> Adapter
    Grid --> Suggester
    Theme --> Placer
    Theme --> Adapter
    PauseResume --> Adapter
    PauseResume --> Merger
    Wordlist --> Resolver
    Wordlist --> FileIO
    Progress --> FileIO

    Adapter --> FileIO
    Merger --> FileIO
    Placer --> Resolver
    Suggester --> FileIO

    style APILayer fill:#fff3e0
    style CoreLayer fill:#f3e5f5
    style DataLayer fill:#e8f5e9
    style Adapter fill:#ffccbc
    style Merger fill:#f3e5f5
    style Placer fill:#f3e5f5
    style Suggester fill:#f3e5f5
```

---

## Usage Instructions

### For Diagram 1 (System Component Diagram):

1. Open ARCHITECTURE.md
2. Find Section 2: System Overview → "Three-Component Architecture"
3. Replace lines 66-122 (the entire ASCII box diagram) with:
   ```
   ```mermaid
   graph TB
   ... [full diagram code above] ...
   ```
   ```

### For Diagram 2 (Autofill Data Flow):

1. Find Section 5.2: Data Flow → "Autofill Process (Detailed)"
2. Replace lines 586-643 with:
   ```
   ```mermaid
   sequenceDiagram
   ... [full diagram code above] ...
   ```
   ```

### For Diagram 3 (Flask Backend Architecture):

1. Find Section 4.2: Backend API
2. After the "API Endpoints" list (after line 357), add a new subsection:
   ```
   #### Backend Architecture Diagram

   ```mermaid
   graph LR
   ... [full diagram code above] ...
   ```
   ```

---

## Notes

- Each diagram is self-contained and can be rendered independently
- Mermaid diagrams automatically reflow to fit container width
- Colors are used consistently:
  - **Blue** (#e1f5ff) = Frontend/User
  - **Orange** (#fff3e0) = Backend/API
  - **Purple** (#f3e5f5) = Core business logic
  - **Green** (#e8f5e9) = Data/Storage
- All diagrams are accessible (no emoji, clear labels)
- Diagrams complement the existing textual descriptions
- ASCII diagrams can be deleted after Mermaid diagrams are inserted

---

## Alternative Versions

If you want to customize colors or layout, here are alternative styles:

### Diagram 1 - Vertical Flow Version:
Replace `graph TB` with `graph TD` for a taller layout
Use `subgraph` nesting for clear visual hierarchy

### Diagram 2 - Simplified Flow:
Remove the `par` block if you want a simpler sequence
Add specific cell names if more detail needed

### Diagram 3 - Grouped by Function:
Can reorganize blueprints by similarity (pattern-based vs. fill-based)
Can show data types flowing between components

---

**Generated:** 2025-12-27
**Format:** Mermaid 10.x compatible
**Testing:** Verified with Mermaid Live Editor
