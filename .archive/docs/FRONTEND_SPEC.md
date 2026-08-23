# Frontend Specification

**Version:** 2.0.0
**Last Updated:** December 27, 2025
**Status:** Production Ready
**Architecture:** React 18 + Vite 5 SPA
**Integration:** Flask Backend (localhost:5000)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Technology Stack](#technology-stack)
3. [Architecture Overview](#architecture-overview)
4. [Project Structure](#project-structure)
5. [Component Hierarchy](#component-hierarchy)
6. [State Management](#state-management)
7. [Core Components](#core-components)
8. [API Integration](#api-integration)
9. [User Interactions](#user-interactions)
10. [Styling System](#styling-system)
11. [Progress Tracking](#progress-tracking)
12. [Performance Optimization](#performance-optimization)
13. [Accessibility](#accessibility)
14. [Build & Development](#build--development)
15. [Testing Strategy](#testing-strategy)
16. [Deployment](#deployment)
17. [Code Examples](#code-examples)
18. [Best Practices](#best-practices)

---

## Executive Summary

### Purpose

The Crossword Helper frontend is a **single-page React application** that provides an intuitive web interface for constructing, filling, and managing crossword puzzles. It serves as the visual layer over a Flask backend that delegates to a CLI tool for all business logic.

### Key Features

- **Interactive Grid Editor** - Visual crossword grid with keyboard navigation
- **Real-time Autofill** - CSP-based automated puzzle filling with progress tracking
- **Pattern Matching** - Search 454k+ words by pattern (e.g., `?A?E`)
- **Theme Word Management** - Upload and place custom theme entries
- **Wordlist Management** - Browse and manage curated word collections
- **Import/Export** - JSON, HTML, and text format support
- **Pause/Resume** - Interrupt and resume long-running operations
- **Responsive Design** - Mobile-first approach with desktop optimization

### Target Users

1. **Expert Constructor** - Needs precise control and advanced features
2. **Non-Technical Partner** - Prefers visual interface over CLI commands
3. **Mobile User** - Works on tablet or small screen devices

### Design Philosophy

**Progressive Enhancement:**
- Core functionality works without JavaScript (static export)
- Enhanced experience with React interactivity
- Real-time updates via Server-Sent Events

**Component Composition:**
- Small, focused, reusable components
- Single Responsibility Principle
- Props-down, events-up data flow

**Performance First:**
- Virtual DOM for grid rendering optimization
- Lazy loading for heavy components
- Debounced API calls for search
- Memoization for expensive computations

---

## Technology Stack

### Core Dependencies

```json
{
  "react": "^18.2.0",              // UI library
  "react-dom": "^18.2.0",          // DOM rendering
  "axios": "^1.6.2",               // HTTP client
  "classnames": "^2.3.2",          // Dynamic CSS classes
  "react-hot-toast": "^2.6.0"      // Toast notifications
}
```

### Development Dependencies

```json
{
  "@vitejs/plugin-react": "^4.2.1",  // Vite React plugin
  "sass": "^1.69.5",                  // SCSS preprocessor
  "vite": "^5.0.8"                    // Build tool
}
```

### Browser Support

- **Modern Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile**: iOS Safari 14+, Chrome Android 90+
- **Not Supported**: IE11 (uses modern ES2020+ features)

### JavaScript Features Used

- ES2020 syntax (optional chaining, nullish coalescing)
- React Hooks (useState, useEffect, useCallback, useRef)
- EventSource API (Server-Sent Events)
- LocalStorage API (state persistence)
- FileReader API (file uploads)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────┐
│            Browser (User's Device)               │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │    React Application (SPA)             │    │
│  │                                         │    │
│  │  ┌──────────────────────────────────┐ │    │
│  │  │   App.jsx (Root Component)       │ │    │
│  │  │   - Global state management      │ │    │
│  │  │   - Tool routing                 │ │    │
│  │  │   - SSE connection management    │ │    │
│  │  └──────┬───────────────────────────┘ │    │
│  │         │                              │    │
│  │    ┌────▼─────┐  ┌──────────┐         │    │
│  │    │ Main     │  │  Side    │         │    │
│  │    │ Panel    │  │  Panel   │         │    │
│  │    │          │  │          │         │    │
│  │    │ Grid     │  │ Pattern  │         │    │
│  │    │ Editor   │  │ Matcher  │         │    │
│  │    │          │  │ Autofill │         │    │
│  │    │          │  │ Import   │         │    │
│  │    │          │  │ Export   │         │    │
│  │    │          │  │ Wordlists│         │    │
│  │    └──────────┘  └──────────┘         │    │
│  └─────────────────────────────────────────┘   │
└──────────────┬──────────────────────────────────┘
               │
               │ HTTP + SSE
               │ (axios + EventSource)
               │
┌──────────────▼──────────────────────────────────┐
│        Flask Backend (localhost:5000)           │
│        - REST API endpoints                     │
│        - SSE progress streaming                 │
│        - CLI subprocess delegation              │
└─────────────────────────────────────────────────┘
```

### Component Architecture Pattern

**Container/Presentational Split:**
- `App.jsx` - Smart container with state and logic
- Component files - Presentational with props interface
- Hooks - Reusable stateful logic (e.g., `useSSEProgress`)

**Data Flow:**
```
User Action → Event Handler → State Update → Re-render → DOM Update
     ↓
API Request → Backend → CLI Tool → Response → State Update
```

### Routing Strategy

**Single-Page Navigation:**
- No React Router (simple tool routing via state)
- `currentTool` state variable determines active panel
- Header buttons switch tools
- URL does not change (could add hash routing later)

**Why No Router:**
- Only 6 tools, no deep nesting
- No need for shareable URLs yet
- Simpler state management
- Faster development and maintenance

---

## Project Structure

```
src/
├── main.jsx                    # React entry point
├── App.jsx                     # Root component (569 lines)
├── components/                 # All UI components
│   ├── AutofillPanel.jsx       # Autofill controls (710 lines)
│   ├── AutofillPanel.scss
│   ├── BlackSquareSuggestions.jsx  # Cheater square suggestions
│   ├── BlackSquareSuggestions.scss
│   ├── ExportPanel.jsx         # Grid export (223 lines)
│   ├── ExportPanel.scss
│   ├── GridEditor.jsx          # Interactive grid (324 lines)
│   ├── GridEditor.scss
│   ├── ImportPanel.jsx         # Grid import (372 lines)
│   ├── ImportPanel.scss
│   ├── PatternMatcher.jsx      # Word search (353 lines)
│   ├── PatternMatcher.scss
│   ├── ProgressIndicator.jsx   # Progress UI (100 lines)
│   ├── ProgressIndicator.scss
│   ├── ThemeWordsPanel.jsx     # Theme word placement (291 lines)
│   ├── ThemeWordsPanel.scss
│   ├── ToolPanel.jsx           # Grid editor tools (100 lines)
│   ├── ToolPanel.scss
│   ├── WordListPanel.jsx       # Wordlist management (500+ lines)
│   └── WordListPanel.scss
├── hooks/                      # Custom React hooks
│   ├── useProgress.js          # Generic progress tracking
│   └── useSSEProgress.js       # SSE-based progress hook (94 lines)
├── styles/                     # Global styles
│   ├── index.scss              # Global resets and utilities (127 lines)
│   └── App.scss                # App layout styles (118 lines)
└── utils/                      # Utility functions
```

### File Naming Conventions

- **Components**: PascalCase (e.g., `GridEditor.jsx`)
- **Styles**: Same name as component with `.scss` extension
- **Hooks**: camelCase with `use` prefix (e.g., `useSSEProgress.js`)
- **Utilities**: camelCase (e.g., `gridHelpers.js`)

### Component Co-location

Each component includes:
- `.jsx` file - React component logic
- `.scss` file - Component-specific styles
- No test files yet (future: `.test.jsx` files)

---

## Component Hierarchy

### Visual Hierarchy

```
App
├── Toaster (react-hot-toast)
├── header.app-header
│   ├── div.header-brand
│   │   ├── h1: "Crossword Helper"
│   │   └── span.version: "v2.0 Advanced"
│   └── div.header-tools
│       ├── button: Grid Editor
│       ├── button: Pattern Search
│       ├── button: Autofill
│       ├── button: Import
│       ├── button: Export
│       ├── button: Word Lists
│       └── button: Theme Words
├── div.app-body
│   ├── div.main-panel
│   │   └── GridEditor
│   │       ├── svg.grid-svg (interactive grid)
│   │       ├── input.hidden-input (keyboard capture)
│   │       └── div.grid-instructions
│   └── div.side-panel
│       ├── ToolPanel (when currentTool === 'edit')
│       ├── PatternMatcher (when currentTool === 'pattern')
│       ├── AutofillPanel (when currentTool === 'autofill')
│       │   ├── ProgressIndicator
│       │   └── BlackSquareSuggestions (modal)
│       ├── ImportPanel (when currentTool === 'import')
│       ├── ExportPanel (when currentTool === 'export')
│       └── WordListPanel (when currentTool === 'wordlists')
└── ThemeWordsPanel (overlay when showThemePanel === true)
```

### Component Relationships

**Parent → Child Data Flow:**
```javascript
App
├─ grid (state) → GridEditor (prop)
├─ onToggleBlack (callback) → GridEditor (prop)
├─ onStartAutofill (callback) → AutofillPanel (prop)
├─ autofillProgress (state) → AutofillPanel (prop)
└─ currentTaskId (state) → AutofillPanel (prop)
```

**Child → Parent Events:**
```javascript
GridEditor
├─ onSelectCell() → App.setSelectedCell()
├─ onToggleBlack() → App.toggleBlackSquare()
└─ onSetLetter() → App.setLetter()

AutofillPanel
├─ onStartAutofill() → App.handleAutofill()
└─ onCancelAutofill() → App.handleCancelAutofill()

PatternMatcher
└─ onSelectWord() → App.handlePatternSelect()

ImportPanel
└─ onImport() → App.handleGridImport()
```

---

## State Management

### Global State (App.jsx)

The root component manages all application state using React hooks:

```javascript
// Grid State
const [gridSize, setGridSize] = useState(15);
const [grid, setGrid] = useState(null);
const [numbering, setNumbering] = useState({});
const [validationErrors, setValidationErrors] = useState([]);

// UI State
const [selectedCell, setSelectedCell] = useState(null);
const [currentTool, setCurrentTool] = useState('edit');
const [showThemePanel, setShowThemePanel] = useState(false);

// Autofill State
const [autofillProgress, setAutofillProgress] = useState(null);
const [currentTaskId, setCurrentTaskId] = useState(null);
const eventSourceRef = React.useRef(null);
```

### Grid Data Structure

Each cell in the grid is an object:

```javascript
{
  letter: 'A',           // '' for empty, A-Z for filled
  isBlack: false,        // true for black squares
  number: 1,             // clue number (or null)
  isError: false,        // validation error flag
  isHighlighted: false,  // UI highlight state
  isThemeLocked: false   // theme entry lock flag
}
```

**Grid representation:**
```javascript
grid: [
  [ {cell}, {cell}, {cell}, ... ],  // row 0
  [ {cell}, {cell}, {cell}, ... ],  // row 1
  ...
]
```

### State Update Patterns

**Immutable Updates:**
```javascript
// ✅ CORRECT: Create new array/object
const newGrid = [...grid.map(row => [...row])];
newGrid[row][col].letter = 'A';
setGrid(newGrid);

// ❌ WRONG: Mutate existing state
grid[row][col].letter = 'A';
setGrid(grid);
```

**Deep Copy for Nested State:**
```javascript
const newGrid = grid.map((row, r) =>
  row.map((cell, c) => {
    if (r === targetRow && c === targetCol) {
      return { ...cell, isThemeLocked: !cell.isThemeLocked };
    }
    return { ...cell };
  })
);
```

### Local Component State

Components manage their own UI state:

```javascript
// PatternMatcher.jsx
const [pattern, setPattern] = useState('');
const [results, setResults] = useState([]);
const [loading, setLoading] = useState(false);
const [sortBy, setSortBy] = useState('score');

// AutofillPanel.jsx
const [options, setOptions] = useState({
  minScore: 50,
  timeout: 300,
  algorithm: 'beam'
});
```

### Derived State

Computed values from state (not stored):

```javascript
// Calculate grid statistics on render
function calculateGridStats(grid) {
  let blackSquares = 0;
  let filledCells = 0;

  grid.forEach(row => {
    row.forEach(cell => {
      if (cell.isBlack) blackSquares++;
      else if (cell.letter) filledCells++;
    });
  });

  return { blackSquares, filledCells, fillPercent: ... };
}
```

### State Persistence

**LocalStorage for Resume:**
```javascript
// Save paused autofill task ID
localStorage.setItem('paused_autofill_task', taskId);

// Retrieve on mount
useEffect(() => {
  const savedTaskId = localStorage.getItem('paused_autofill_task');
  if (savedTaskId) {
    fetchPausedState(savedTaskId);
  }
}, []);
```

**Grid Save/Load:**
```javascript
// Save to localStorage
const gridData = {
  size: gridSize,
  grid: grid.map(row => row.map(cell => ({
    letter: cell.letter || '',
    isBlack: cell.isBlack || false,
    isThemeLocked: cell.isThemeLocked || false
  }))),
  timestamp: new Date().toISOString()
};
localStorage.setItem('crossword_saved_grid', JSON.stringify(gridData));
```

### Why No Redux/MobX?

**Simple state tree:**
- Single root component manages all state
- No deeply nested components
- Props drilling is minimal (2-3 levels max)
- useState + callbacks sufficient

**Future considerations:**
- If component tree grows to 5+ levels, consider Context API
- If multiple pages added, consider React Router + state library
- Current approach: YAGNI (You Ain't Gonna Need It)

---

## Core Components

### 1. App Component

**File:** `src/App.jsx` (569 lines)
**Role:** Root container managing all application state and routing

**Responsibilities:**
- Initialize and manage grid state
- Handle tool switching
- Coordinate API calls
- Manage SSE connections
- Grid numbering calculation
- Symmetry enforcement

**Key State:**
```javascript
{
  grid: Cell[][],           // 2D array of cell objects
  gridSize: number,         // 11, 15, 21, etc.
  selectedCell: {           // Currently selected cell
    row: number,
    col: number,
    direction: 'across' | 'down'
  },
  currentTool: string,      // 'edit', 'pattern', 'autofill', etc.
  autofillProgress: {       // Autofill status
    status: 'running' | 'complete' | 'error' | 'paused',
    progress: number,       // 0-100
    message: string
  }
}
```

**Key Methods:**

```javascript
// Grid initialization
const initializeGrid = (size) => {
  const newGrid = Array(size).fill(null).map(() =>
    Array(size).fill(null).map(() => ({
      letter: '', isBlack: false, number: null,
      isError: false, isHighlighted: false, isThemeLocked: false
    }))
  );
  setGrid(newGrid);
  updateNumbering(newGrid);
};

// Symmetry enforcement
const toggleBlackSquare = (row, col) => {
  const newGrid = [...grid.map(row => [...row])];
  newGrid[row][col].isBlack = !newGrid[row][col].isBlack;

  // Apply rotational symmetry
  const symRow = gridSize - 1 - row;
  const symCol = gridSize - 1 - col;
  newGrid[symRow][symCol].isBlack = newGrid[row][col].isBlack;

  setGrid(newGrid);
  updateNumbering(newGrid);
};

// Automatic numbering
const updateNumbering = (gridData) => {
  const numbers = {};
  let currentNumber = 1;

  for (let row = 0; row < gridData.length; row++) {
    for (let col = 0; col < gridData[row].length; col++) {
      if (gridData[row][col].isBlack) continue;

      const needsNumber = (
        isStartOfAcrossWord(gridData, row, col) ||
        isStartOfDownWord(gridData, row, col)
      );

      if (needsNumber) {
        numbers[`${row},${col}`] = currentNumber;
        gridData[row][col].number = currentNumber;
        currentNumber++;
      }
    }
  }

  setNumbering(numbers);
};
```

**SSE Connection Management:**

```javascript
const handleAutofill = async (options) => {
  // Start autofill
  const response = await fetch('/api/fill/with-progress', {
    method: 'POST',
    body: JSON.stringify({ grid, options })
  });

  const { task_id } = await response.json();
  setCurrentTaskId(task_id);

  // Connect to SSE
  const eventSource = new EventSource(`/api/progress/${task_id}`);
  eventSourceRef.current = eventSource;

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    setAutofillProgress({
      status: data.status,
      progress: data.progress,
      message: data.message
    });

    // Update grid incrementally if provided
    if (data.data?.grid) {
      updateGridFromCLIFormat(data.data.grid);
    }

    // Close on completion
    if (data.status === 'complete' || data.status === 'error') {
      eventSource.close();
      eventSourceRef.current = null;
    }
  };
};
```

### 2. GridEditor Component

**File:** `src/components/GridEditor.jsx` (324 lines)
**Role:** Interactive SVG-based crossword grid

**Features:**
- Click to select cell
- Keyboard navigation (arrows, Tab)
- Letter entry with auto-advance
- Black square toggle (Shift+Click or Space)
- Theme lock toggle (Right-click or Ctrl+L)
- Word highlighting
- Symmetry visualization
- Cell numbering display

**Rendering Strategy:**

```javascript
// SVG-based rendering for precision
<svg width={svgWidth} height={svgHeight}>
  {/* Grid cells */}
  {grid.map((row, rowIdx) =>
    row.map((cell, colIdx) => (
      <g key={`${rowIdx}-${colIdx}`}>
        {/* Cell background */}
        <rect
          x={x} y={y}
          width={CELL_SIZE} height={CELL_SIZE}
          fill={getCellFill(cell, isFocused, isHighlighted)}
          onClick={(e) => handleCellClick(rowIdx, colIdx, e)}
          onContextMenu={(e) => handleCellRightClick(rowIdx, colIdx, e)}
        />

        {/* Cell number */}
        {cell.number && (
          <text x={x + 2} y={y + 10} fontSize="10">
            {cell.number}
          </text>
        )}

        {/* Cell letter */}
        {cell.letter && (
          <text x={x + CELL_SIZE/2} y={y + CELL_SIZE/2 + 6} fontSize="20">
            {cell.letter}
          </text>
        )}

        {/* Theme lock icon */}
        {cell.isThemeLocked && <LockIcon />}
      </g>
    ))
  )}

  {/* Symmetry indicator */}
  {hoveredCell && (
    <line
      x1={hoveredX} y1={hoveredY}
      x2={symmetryX} y2={symmetryY}
      stroke="rgba(156, 39, 176, 0.3)"
      strokeDasharray="5,5"
    />
  )}
</svg>
```

**Keyboard Handling:**

```javascript
const handleKeyDown = (e) => {
  if (!focusedCell) return;

  const { row, col } = focusedCell;

  // Navigation
  if (e.key === 'ArrowUp' && row > 0) {
    setFocusedCell({ row: row - 1, col });
  } else if (e.key === 'ArrowDown' && row < gridSize - 1) {
    setFocusedCell({ row: row + 1, col });
  }
  // ... similar for ArrowLeft, ArrowRight

  // Letter entry
  else if (/^[A-Za-z]$/.test(e.key)) {
    onSetLetter(row, col, e.key);
    // Auto-advance to next cell
    if (col < gridSize - 1) {
      setFocusedCell({ row, col: col + 1 });
    }
  }

  // Black square toggle
  else if (e.key === ' ' || e.key === '.') {
    onToggleBlack(row, col);
  }

  // Clear cell
  else if (e.key === 'Backspace' || e.key === 'Delete') {
    onSetLetter(row, col, '');
    if (e.key === 'Backspace' && col > 0) {
      setFocusedCell({ row, col: col - 1 });
    }
  }

  // Jump to next word
  else if (e.key === 'Tab') {
    e.preventDefault();
    moveToNextWord(row, col, !e.shiftKey);
  }
};
```

**Performance Optimization:**

```javascript
// Use React.memo to prevent unnecessary re-renders
export default React.memo(GridEditor);

// Memoize expensive calculations
const highlightedCells = useMemo(() => {
  return getHighlightedCells(selectedCell, grid);
}, [selectedCell, grid]);

// Use refs for SVG element (avoid re-creating)
const svgRef = useRef(null);
const inputRef = useRef(null);
```

### 3. AutofillPanel Component

**File:** `src/components/AutofillPanel.jsx` (710 lines)
**Role:** Autofill configuration and progress monitoring

**Features:**
- Algorithm selection (regex, trie, beam)
- Wordlist selection (multiple)
- Minimum score threshold
- Timeout configuration
- Adaptive mode (auto black squares)
- Theme entry detection and locking
- Pause/Resume functionality
- Progress visualization
- Black square suggestions

**Options State:**

```javascript
const [options, setOptions] = useState({
  minScore: 50,                    // Minimum word quality (0-100)
  preferPersonalWords: true,       // Boost custom wordlists
  timeout: 300,                    // Seconds before giving up
  wordlists: ['comprehensive'],    // Active wordlists
  algorithm: 'beam',               // regex, trie, or beam
  adaptiveMode: false,             // Auto place black squares
  maxAdaptations: 3                // Max auto black squares
});
```

**Theme Entry Detection:**

```javascript
// Extract theme-locked words from grid
const getThemeEntries = () => {
  const themeEntries = {};

  for (let row = 0; row < grid.length; row++) {
    for (let col = 0; col < grid[row].length; col++) {
      const cell = grid[row][col];

      if (cell.isThemeLocked && !cell.isBlack && cell.letter) {
        // Check if start of across word
        const isStartAcross = (col === 0 || grid[row][col - 1].isBlack);
        if (isStartAcross) {
          const word = extractWord(row, col, 'across');
          if (!word.includes('.') && word.length > 1) {
            themeEntries[`(${row},${col},across)`] = word;
          }
        }

        // Check if start of down word
        const isStartDown = (row === 0 || grid[row - 1][col].isBlack);
        if (isStartDown) {
          const word = extractWord(row, col, 'down');
          if (!word.includes('.') && word.length > 1) {
            themeEntries[`(${row},${col},down)`] = word;
          }
        }
      }
    }
  }

  return themeEntries;
};
```

**Pause/Resume Logic:**

```javascript
// Pause autofill
const handlePause = async () => {
  const response = await fetch(`/api/fill/pause/${currentTaskId}`, {
    method: 'POST'
  });

  if (response.ok) {
    localStorage.setItem('paused_autofill_task', currentTaskId);
    toast.success('Pause requested - waiting for autofill to stop...');
  }
};

// Resume autofill
const handleResume = async () => {
  const gridArray = grid.map(row =>
    row.map(cell => cell.letter ? [cell.letter] : ['.'])
  );

  const response = await fetch('/api/fill/resume', {
    method: 'POST',
    body: JSON.stringify({
      task_id: pausedTaskId,
      edited_grid: gridArray,
      options: options
    })
  });

  if (response.status === 409) {
    // User edits created unsolvable grid
    toast.error('Cannot resume: Your edits create an unsolvable grid.');
    return;
  }

  const { new_task_id } = await response.json();
  onStartAutofill({ ...options, resumeTaskId: new_task_id });
};
```

### 4. PatternMatcher Component

**File:** `src/components/PatternMatcher.jsx` (353 lines)
**Role:** Pattern-based word search

**Features:**
- Pattern input with wildcards (`?`)
- Algorithm selection (regex vs trie)
- Multiple wordlist selection
- Result sorting (score, alpha, length)
- Score filtering
- Letter quality highlighting
- Progress tracking via SSE

**Search Flow:**

```javascript
const searchPattern = async () => {
  // Start search with progress tracking
  const initResponse = await axios.post('/api/pattern/with-progress', {
    pattern: pattern.toUpperCase(),
    max_results: 50,
    wordlists: selectedWordlists,
    algorithm: algorithm
  });

  const { task_id } = initResponse.data;

  // Connect to SSE for progress updates
  searchProgress.connect(task_id);
};

// Watch for search completion
useEffect(() => {
  if (searchProgress.status === 'complete') {
    // Fetch final results
    const response = await axios.post('/api/pattern', {
      pattern, wordlists, algorithm
    });

    let results = response.data.results;

    // Sort and filter
    if (sortBy === 'score') {
      results.sort((a, b) => b.score - a.score);
    }
    if (filterMinScore > 0) {
      results = results.filter(r => r.score >= filterMinScore);
    }

    setResults(results);
  }
}, [searchProgress.status]);
```

**Letter Quality Rendering:**

```javascript
const renderLetterQuality = (word) => {
  const commonLetters = new Set('EARIOTNS');
  const uncommonLetters = new Set('JQXZ');

  return word.split('').map((letter, idx) => {
    let className = 'letter';
    if (commonLetters.has(letter)) className += ' common';
    else if (uncommonLetters.has(letter)) className += ' uncommon';

    return <span key={idx} className={className}>{letter}</span>;
  });
};
```

### 5. ThemeWordsPanel Component

**File:** `src/components/ThemeWordsPanel.jsx` (291 lines)
**Role:** Upload and place custom theme words

**Features:**
- .txt file upload
- Word validation (length, uniqueness)
- Placement suggestions (API-generated)
- Interactive placement preview
- Apply placement to grid

**File Upload Flow:**

```javascript
const handleFileSelect = (e) => {
  const file = e.target.files[0];

  // Validate file type
  if (!file.name.endsWith('.txt')) {
    toast.error('Please select a .txt file');
    return;
  }

  // Read file
  const reader = new FileReader();
  reader.onload = (event) => {
    const content = event.target.result;
    uploadToBackend(content);
  };
  reader.readAsText(file);
};

const uploadToBackend = async (content) => {
  const response = await fetch('/api/theme/upload', {
    method: 'POST',
    body: JSON.stringify({
      content: content,
      grid_size: gridSize
    })
  });

  const data = await response.json();

  if (!data.validation.valid) {
    setValidationErrors(data.validation.errors);
    return;
  }

  setThemeWords(data.words);

  // Auto-analyze placements
  await analyzePlacements(data.words);
};
```

**Placement Suggestions:**

```javascript
const analyzePlacements = async (words) => {
  const response = await fetch('/api/theme/suggest-placements', {
    method: 'POST',
    body: JSON.stringify({
      theme_words: words,
      grid_size: gridSize,
      existing_grid: grid,
      max_suggestions: 3
    })
  });

  const data = await response.json();
  setSuggestions(data.suggestions);

  // Suggestions format:
  // [
  //   {
  //     word: "BIRTHDAY",
  //     suggestions: [
  //       { row: 0, col: 3, direction: "across", score: 85, reasoning: "..." },
  //       { row: 7, col: 0, direction: "down", score: 72, reasoning: "..." }
  //     ]
  //   }
  // ]
};
```

### 6. ImportPanel Component

**File:** `src/components/ImportPanel.jsx` (372 lines)
**Role:** Import grids from JSON files or clipboard

**Features:**
- File upload (.json)
- Paste JSON text
- Format validation
- Preview before import
- Error reporting

**Validation Logic:**

```javascript
const validateImportedData = (data) => {
  // Check required fields
  if (!data.size || !data.grid) {
    throw new Error('Missing "size" or "grid" fields');
  }

  // Validate size
  const size = parseInt(data.size);
  if (isNaN(size) || size < 3 || size > 25) {
    throw new Error(`Invalid grid size: ${data.size}`);
  }

  // Validate grid dimensions
  if (data.grid.length !== size) {
    throw new Error(`Grid height doesn't match size`);
  }

  // Validate cell format
  for (let row = 0; row < size; row++) {
    for (let col = 0; col < size; col++) {
      const cell = data.grid[row][col];
      if (typeof cell !== 'string') {
        throw new Error(`Invalid cell at (${row}, ${col})`);
      }
      if (cell !== '#' && cell !== '.' && !/^[A-Z]$/.test(cell)) {
        throw new Error(`Invalid cell value: "${cell}"`);
      }
    }
  }

  return { size, grid: data.grid, numbering: data.numbering || {} };
};
```

**Format Conversion:**

```javascript
// Convert CLI format to frontend format
const convertGridFormat = (cliGrid, size) => {
  const frontendGrid = [];

  for (let row = 0; row < size; row++) {
    const frontendRow = [];
    for (let col = 0; col < size; col++) {
      const cliCell = cliGrid[row][col];
      const cell = {
        letter: '',
        isBlack: false,
        number: null,
        isError: false,
        isHighlighted: false
      };

      if (cliCell === '#') {
        cell.isBlack = true;
      } else if (cliCell !== '.' && cliCell !== '') {
        cell.letter = cliCell;
      }

      frontendRow.push(cell);
    }
    frontendGrid.push(frontendRow);
  }

  return frontendGrid;
};
```

### 7. ExportPanel Component

**File:** `src/components/ExportPanel.jsx` (223 lines)
**Role:** Export grids to various formats

**Features:**
- JSON export (for reimport)
- HTML export (printable)
- Text export (simple representation)
- Preview before download
- Client-side file generation

**Export Implementations:**

```javascript
// JSON export
const exportJSON = () => {
  const gridData = {
    size: gridSize,
    grid: grid.map(row => row.map(cell =>
      cell.isBlack ? '#' : (cell.letter || '.')
    )),
    numbering: numbering
  };

  const json = JSON.stringify(gridData, null, 2);
  downloadFile('crossword.json', json, 'application/json');
};

// HTML export
const generateHTML = (gridData) => {
  let html = `<!DOCTYPE html>
<html>
<head>
  <title>Crossword Puzzle</title>
  <style>
    .grid { border-collapse: collapse; }
    .grid td { width: 30px; height: 30px; border: 1px solid #333; }
    .grid td.black { background: #333; }
  </style>
</head>
<body>
  <table class="grid">`;

  for (let row = 0; row < gridData.size; row++) {
    html += '<tr>';
    for (let col = 0; col < gridData.size; col++) {
      const cell = gridData.grid[row][col];
      const number = gridData.numbering[`${row},${col}`];

      if (cell === '#') {
        html += '<td class="black"></td>';
      } else {
        html += `<td>`;
        if (number) html += `<span class="number">${number}</span>`;
        if (cell !== '.') html += cell;
        html += '</td>';
      }
    }
    html += '</tr>';
  }

  html += '</table></body></html>';
  return html;
};

// Text export
const generateText = (gridData) => {
  let text = `Crossword Puzzle (${gridData.size}×${gridData.size})\n\n`;

  for (let row = 0; row < gridData.size; row++) {
    for (let col = 0; col < gridData.size; col++) {
      const cell = gridData.grid[row][col];
      text += cell === '#' ? '■ ' : cell === '.' ? '_ ' : cell + ' ';
    }
    text += '\n';
  }

  return text;
};

// File download helper
const downloadFile = (filename, content, mimeType) => {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};
```

### 8. ProgressIndicator Component

**File:** `src/components/ProgressIndicator.jsx` (100 lines)
**Role:** Reusable progress display

**Props:**
```javascript
{
  type: 'bar' | 'spinner',    // Visual style
  progress: number,            // 0-100 percentage
  message: string,             // Status text
  size: 'small' | 'medium' | 'large',
  color: 'primary' | 'success' | 'warning' | 'danger'
}
```

**Rendering:**

```javascript
function ProgressIndicator({ type, progress, message, size, color }) {
  if (type === 'spinner') {
    return (
      <div className={`progress-spinner ${size} ${color}`}>
        <div className="spinner-icon"></div>
        {message && <p className="spinner-message">{message}</p>}
      </div>
    );
  }

  return (
    <div className={`progress-bar-container ${size}`}>
      <div className="progress-bar-track">
        <div
          className={`progress-bar-fill ${color}`}
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="progress-info">
        <span className="progress-message">{message}</span>
        <span className="progress-percent">{Math.round(progress)}%</span>
      </div>
    </div>
  );
}
```

### 9. WordListPanel Component

**File:** `src/components/WordListPanel.jsx` (500+ lines)
**Role:** Manage word collections

**Features:**
- List all wordlists
- View wordlist contents
- Create new wordlists
- Update existing wordlists
- Delete wordlists
- Import from file
- Statistics display

---

## API Integration

### HTTP Client Setup

**Axios Configuration:**

```javascript
import axios from 'axios';

// Base URL configured in vite.config.js proxy
// Development: http://localhost:3000/api → http://localhost:5000/api
// Production: /api (same origin)

// No special axios instance needed - using default
```

### API Call Patterns

**Pattern 1: Simple POST Request**

```javascript
const response = await axios.post('/api/pattern', {
  pattern: 'C?T',
  max_results: 50,
  wordlists: ['comprehensive']
});

const results = response.data.results;
```

**Pattern 2: Fetch with Progress (SSE)**

```javascript
// Step 1: Initiate task
const initResponse = await fetch('/api/pattern/with-progress', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ pattern, wordlists })
});

const { task_id } = await initResponse.json();

// Step 2: Connect to SSE for progress
const eventSource = new EventSource(`/api/progress/${task_id}`);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  updateProgress(data);

  if (data.status === 'complete') {
    eventSource.close();
    fetchFinalResults();
  }
};
```

**Pattern 3: Error Handling**

```javascript
try {
  const response = await axios.post('/api/pattern', { pattern });
  setResults(response.data.results);
} catch (error) {
  if (error.response) {
    // Server error (4xx, 5xx)
    const errorMsg = error.response.data.error || 'Request failed';
    toast.error(errorMsg);
  } else if (error.request) {
    // Network error
    toast.error('Network error - is the server running?');
  } else {
    // Client error
    toast.error(`Error: ${error.message}`);
  }
}
```

### Request/Response Formats

**Pattern Search:**

```javascript
// Request
POST /api/pattern
{
  "pattern": "C?T",
  "max_results": 50,
  "wordlists": ["comprehensive"],
  "algorithm": "trie"
}

// Response
{
  "results": [
    { "word": "CAT", "score": 95, "source": "comprehensive" },
    { "word": "COT", "score": 82, "source": "comprehensive" }
  ],
  "meta": {
    "total_found": 127,
    "query_time_ms": 245
  }
}
```

**Grid Autofill:**

```javascript
// Request
POST /api/fill/with-progress
{
  "size": 15,
  "grid": [
    ["A", ".", ".", ...],
    ["#", ".", ".", ...],
    ...
  ],
  "wordlists": ["comprehensive"],
  "timeout": 300,
  "min_score": 50,
  "algorithm": "beam",
  "theme_entries": {
    "(0,0,across)": "BIRTHDAY",
    "(7,0,down)": "CELEBRATION"
  }
}

// Response
{
  "task_id": "abc123xyz"
}

// SSE Progress Events
data: {"status":"running","progress":25,"message":"Filled 15/60 slots"}
data: {"status":"running","progress":50,"message":"Filled 30/60 slots","data":{"grid":[...]}}
data: {"status":"complete","progress":100,"data":{"grid":[...],"success":true}}
```

### SSE Progress Tracking

**useSSEProgress Hook:**

```javascript
// src/hooks/useSSEProgress.js
export function useSSEProgress() {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const eventSourceRef = useRef(null);

  const connect = useCallback((taskId) => {
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Create SSE connection
    const eventSource = new EventSource(`/api/progress/${taskId}`);
    eventSourceRef.current = eventSource;

    setStatus('running');

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setProgress(data.progress || 0);
      setMessage(data.message || 'Processing...');
      setStatus(data.status || 'running');

      if (data.status === 'complete' || data.status === 'error') {
        eventSource.close();
        eventSourceRef.current = null;
      }
    };

    eventSource.onerror = () => {
      setStatus('error');
      setMessage('Connection error');
      eventSource.close();
    };
  }, []);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  return { progress, status, message, connect, disconnect };
}
```

**Usage in Components:**

```javascript
function PatternMatcher() {
  const searchProgress = useSSEProgress();

  const searchPattern = async () => {
    const response = await axios.post('/api/pattern/with-progress', {...});
    const { task_id } = response.data;

    // Connect to progress stream
    searchProgress.connect(task_id);
  };

  return (
    <div>
      {searchProgress.status === 'running' && (
        <ProgressIndicator
          type="bar"
          progress={searchProgress.progress}
          message={searchProgress.message}
        />
      )}
    </div>
  );
}
```

### Caching Strategy

**No caching currently implemented**, but future considerations:

```javascript
// Pattern: Cache API responses in memory
const cache = new Map();

const fetchWithCache = async (url, options) => {
  const cacheKey = `${url}:${JSON.stringify(options)}`;

  if (cache.has(cacheKey)) {
    return cache.get(cacheKey);
  }

  const response = await fetch(url, options);
  const data = await response.json();

  cache.set(cacheKey, data);

  // Clear cache after 5 minutes
  setTimeout(() => cache.delete(cacheKey), 5 * 60 * 1000);

  return data;
};
```

---

## User Interactions

### Keyboard Shortcuts

**Grid Editor:**

| Shortcut | Action |
|----------|--------|
| `A-Z` | Enter letter in focused cell |
| `Arrow Keys` | Navigate between cells |
| `Tab` | Jump to next word start |
| `Shift+Tab` | Jump to previous word start |
| `Space` or `.` | Toggle black square |
| `Backspace` | Clear cell and move back |
| `Delete` | Clear cell |
| `Shift+Click` | Toggle black square |
| `Right-Click` | Toggle theme lock |
| `Ctrl/Cmd+L` | Toggle theme lock on focused cell |

**Pattern Matcher:**

| Shortcut | Action |
|----------|--------|
| `Enter` | Trigger search |

### Mouse Interactions

**Grid Editor:**
- **Click** - Select cell for editing
- **Shift+Click** - Toggle black square
- **Right-Click** - Toggle theme lock
- **Hover** - Show symmetry indicator

**Pattern Results:**
- **Click word** - Fill into selected grid position

**Theme Suggestions:**
- **Hover suggestion** - Preview placement on grid
- **Click Apply** - Lock word into grid

### Touch Interactions (Mobile)

**Grid:**
- **Tap** - Select cell
- **Long press** - Toggle black square
- **Two-finger tap** - Toggle theme lock

**Responsive Breakpoints:**
```scss
// Desktop: Side panel (400px width)
@media (min-width: 1200px) {
  .app-body { flex-direction: row; }
  .side-panel { width: 400px; }
}

// Tablet: Stacked layout
@media (max-width: 1200px) {
  .app-body { flex-direction: column; }
  .side-panel { width: 100%; }
}

// Mobile: Compact header
@media (max-width: 768px) {
  .header-tools {
    .tool-btn { font-size: 0.875rem; padding: 0.5rem; }
  }
}
```

### Form Interactions

**Auto-advance in Grid:**
```javascript
// After entering letter, move to next cell
if (/^[A-Za-z]$/.test(e.key)) {
  onSetLetter(row, col, e.key);
  if (col < gridSize - 1) {
    setFocusedCell({ row, col: col + 1 });
  } else if (row < gridSize - 1) {
    setFocusedCell({ row: row + 1, col: 0 });
  }
}
```

**Debounced Search:**
```javascript
// Wait for user to stop typing before searching
const debouncedSearch = useMemo(
  () => debounce((pattern) => searchPattern(pattern), 500),
  []
);

const handlePatternChange = (e) => {
  setPattern(e.target.value);
  debouncedSearch(e.target.value);
};
```

### Feedback Mechanisms

**Toast Notifications:**
```javascript
import toast from 'react-hot-toast';

// Success
toast.success('Grid saved successfully!');

// Error
toast.error('Failed to load wordlist');

// Warning
toast('No results found', { icon: '⚠️' });

// Custom duration
toast.error('Connection timeout', { duration: 5000 });
```

**Visual Feedback:**
- Cell highlights on hover
- Word highlights on selection
- Progress bars for long operations
- Spinners for loading states
- Error borders on invalid input

---

## Styling System

### SCSS Architecture

**Global Styles:**
```scss
// src/styles/index.scss
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto;
  font-size: 14px;
  color: #333;
}

// Typography
h1 { font-size: 2rem; }
h2 { font-size: 1.5rem; }
h3 { font-size: 1.2rem; }

// Utilities
.text-center { text-align: center; }
.mt-1 { margin-top: 0.5rem; }
```

**Component Styles:**
```scss
// src/components/GridEditor.scss
.grid-editor {
  display: flex;
  flex-direction: column;
  gap: 1rem;

  .grid-container {
    position: relative;

    .grid-svg {
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .grid-cell {
      cursor: pointer;
      transition: fill 0.2s ease;

      &:hover {
        opacity: 0.8;
      }
    }
  }
}
```

### Design Tokens

**Colors:**
```scss
// Primary gradient
$primary-start: #667eea;
$primary-end: #764ba2;

// Status colors
$success: #4caf50;
$warning: #ff9800;
$error: #f44336;
$info: #2196f3;

// Neutrals
$gray-100: #f8f9fa;
$gray-200: #e9ecef;
$gray-300: #dee2e6;
$gray-800: #333;

// Theme lock color
$theme-lock: #7b1fa2;
```

**Spacing:**
```scss
$spacing-xs: 0.25rem;  // 4px
$spacing-sm: 0.5rem;   // 8px
$spacing-md: 1rem;     // 16px
$spacing-lg: 1.5rem;   // 24px
$spacing-xl: 2rem;     // 32px
```

**Typography:**
```scss
$font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI';
$font-mono: 'JetBrains Mono', 'Courier New', monospace;

$font-size-sm: 0.875rem;  // 14px
$font-size-md: 1rem;      // 16px
$font-size-lg: 1.25rem;   // 20px
```

### Component Styling Patterns

**BEM Naming:**
```scss
.autofill-panel {
  // Block

  &__options {
    // Element
  }

  &--loading {
    // Modifier
  }
}
```

**Nested Selectors:**
```scss
.grid-editor {
  .grid-container {
    .grid-svg {
      // 3 levels max
    }
  }
}
```

**Responsive Mixins:**
```scss
@mixin mobile {
  @media (max-width: 768px) { @content; }
}

@mixin tablet {
  @media (max-width: 1200px) { @content; }
}

.component {
  width: 400px;

  @include tablet {
    width: 100%;
  }
}
```

### Animations

**Keyframes:**
```scss
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

**Usage:**
```scss
.side-panel {
  animation: slideInUp 0.3s ease;
}

.loading-spinner {
  animation: pulse 1.5s ease-in-out infinite;
}
```

### Custom Scrollbars

```scss
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;

  &:hover {
    background: #555;
  }
}
```

---

## Progress Tracking

### SSE Architecture

**Server-Sent Events Flow:**

```
Frontend                     Backend                     CLI Tool
   │                            │                            │
   │  POST /api/fill/with-progress                          │
   ├───────────────────────────>│                            │
   │                            │  subprocess.Popen(cli)     │
   │                            ├───────────────────────────>│
   │  { task_id: "abc123" }     │                            │
   │<───────────────────────────┤                            │
   │                            │                            │
   │  EventSource /api/progress/abc123                      │
   ├───────────────────────────>│                            │
   │                            │  Read progress.json        │
   │                            ├──┐                         │
   │  data: {progress: 10}      │  │                         │
   │<───────────────────────────┤<─┘                         │
   │                            │                            │
   │                            │  Read progress.json        │
   │                            ├──┐                         │
   │  data: {progress: 50}      │  │                         │
   │<───────────────────────────┤<─┘                         │
   │                            │                            │
   │                            │  CLI completes             │
   │                            │<───────────────────────────┤
   │  data: {status: "complete"}│                            │
   │<───────────────────────────┤                            │
   │  Connection closed         │                            │
```

### Progress Update Types

**Running Updates:**
```json
{
  "status": "running",
  "progress": 45,
  "message": "Filled 27/60 slots (beam search)",
  "data": {
    "grid": [...],  // Incremental grid updates
    "slots_filled": 27,
    "total_slots": 60,
    "current_slot": "(3,5,across)"
  }
}
```

**Complete:**
```json
{
  "status": "complete",
  "progress": 100,
  "message": "Successfully filled 60/60 slots!",
  "data": {
    "grid": [...],
    "success": true,
    "slots_filled": 60,
    "total_slots": 60,
    "fill_percentage": 100,
    "time_elapsed": 45.2
  }
}
```

**Partial Fill:**
```json
{
  "status": "complete",
  "progress": 75,
  "message": "Partial: 45/60 slots (75%)",
  "data": {
    "grid": [...],
    "success": false,
    "slots_filled": 45,
    "total_slots": 60,
    "fill_percentage": 75,
    "suggestions": [
      {
        "type": "add_black_square",
        "location": "(7,8)",
        "reasoning": "Isolates difficult slot (7,5,across)"
      }
    ]
  }
}
```

**Paused:**
```json
{
  "status": "paused",
  "progress": 60,
  "message": "Autofill paused - state saved",
  "data": {
    "grid": [...],
    "slots_filled": 36,
    "total_slots": 60
  }
}
```

**Error:**
```json
{
  "status": "error",
  "progress": 0,
  "message": "No valid words found for slot (5,3,across) pattern ?X?Q?Z?",
  "data": {
    "error_type": "no_candidates",
    "slot": "(5,3,across)",
    "pattern": "?X?Q?Z?"
  }
}
```

### Incremental Grid Updates

**Why Incremental Updates:**
- Show progress visually as grid fills
- User can see algorithm in action
- Better UX for long-running operations

**Implementation:**

```javascript
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  // Apply incremental grid updates
  if (data.data?.grid && data.status === 'running') {
    const newGrid = grid.map((row, r) =>
      row.map((cell, c) => {
        const cliCell = data.data.grid[r][c];
        if (cliCell === '#') {
          return { ...cell, isBlack: true };
        } else if (cliCell !== '#' && cliCell !== '.') {
          return { ...cell, letter: cliCell };
        }
        return { ...cell };
      })
    );
    setGrid(newGrid);
  }
};
```

### Progress Persistence

**LocalStorage for Resume:**

```javascript
// Save task ID when autofill starts
useEffect(() => {
  if (currentTaskId) {
    localStorage.setItem('current_autofill_task', currentTaskId);
  }
}, [currentTaskId]);

// Check for paused task on mount
useEffect(() => {
  const savedTaskId = localStorage.getItem('paused_autofill_task');
  if (savedTaskId) {
    fetchPausedState(savedTaskId);
  }
}, []);
```

---

## Performance Optimization

### React Performance

**Memoization:**

```javascript
// Memoize expensive calculations
const gridStats = useMemo(() => {
  return calculateGridStats(grid);
}, [grid]);

// Memoize callbacks
const handleCellClick = useCallback((row, col) => {
  // ... logic
}, [grid, selectedCell]);

// Memoize components
export default React.memo(GridEditor, (prevProps, nextProps) => {
  return prevProps.grid === nextProps.grid &&
         prevProps.selectedCell === nextProps.selectedCell;
});
```

**Avoid Unnecessary Re-renders:**

```javascript
// ❌ BAD: Creates new object on every render
<Component options={{ minScore: 50 }} />

// ✅ GOOD: Use state or useMemo
const options = useMemo(() => ({ minScore: 50 }), []);
<Component options={options} />
```

**Key Props for Lists:**

```javascript
// Always provide stable keys
{results.map((result, idx) => (
  <div key={result.id}> {/* ✅ Stable ID */}
    {result.word}
  </div>
))}

// ❌ BAD: Index as key (unstable on sort)
{results.map((result, idx) => (
  <div key={idx}>...</div>
))}
```

### Bundle Optimization

**Vite Build Configuration:**

```javascript
// vite.config.js
export default defineConfig({
  build: {
    outDir: 'frontend/dist',
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'utils': ['axios', 'classnames']
        }
      }
    }
  }
});
```

**Code Splitting (Future):**

```javascript
// Lazy load heavy components
const WordListPanel = React.lazy(() => import('./components/WordListPanel'));

function App() {
  return (
    <Suspense fallback={<Loading />}>
      <WordListPanel />
    </Suspense>
  );
}
```

### Rendering Performance

**Virtual Scrolling (Future):**

For large wordlist displays:

```javascript
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={400}
  itemCount={results.length}
  itemSize={35}
  width="100%"
>
  {({ index, style }) => (
    <div style={style}>{results[index].word}</div>
  )}
</FixedSizeList>
```

**Debouncing:**

```javascript
import { debounce } from 'lodash-es';

const debouncedSearch = useMemo(
  () => debounce((pattern) => searchPattern(pattern), 300),
  []
);
```

### Network Performance

**Request Deduplication:**

```javascript
// Avoid duplicate requests
const requestCache = new Map();

const fetchWithDedup = async (url, options) => {
  const key = `${url}:${JSON.stringify(options)}`;

  if (requestCache.has(key)) {
    return requestCache.get(key);
  }

  const promise = fetch(url, options).then(r => r.json());
  requestCache.set(key, promise);

  return promise;
};
```

### Memory Management

**Cleanup Event Listeners:**

```javascript
useEffect(() => {
  const eventSource = new EventSource(url);

  return () => {
    eventSource.close(); // Cleanup on unmount
  };
}, [url]);
```

**Clear Large State:**

```javascript
// Clear results when switching tools
useEffect(() => {
  return () => {
    setResults([]); // Cleanup on unmount
  };
}, []);
```

---

## Accessibility

### Semantic HTML

```jsx
// Use semantic elements
<header className="app-header">
  <h1>Crossword Helper</h1>
  <nav>
    <button>Pattern Search</button>
  </nav>
</header>

<main className="app-body">
  <section className="main-panel">
    <GridEditor />
  </section>
  <aside className="side-panel">
    <PatternMatcher />
  </aside>
</main>
```

### ARIA Labels

```jsx
<button
  aria-label="Toggle black square"
  onClick={() => onToggleBlack(row, col)}
>
  ⬛
</button>

<input
  type="text"
  aria-label="Pattern search"
  placeholder="Enter pattern (e.g., C?T)"
/>

<div
  role="progressbar"
  aria-valuenow={progress}
  aria-valuemin={0}
  aria-valuemax={100}
>
  {progress}%
</div>
```

### Keyboard Navigation

**Focus Management:**

```javascript
// Auto-focus input when cell selected
useEffect(() => {
  if (focusedCell && inputRef.current) {
    inputRef.current.focus();
  }
}, [focusedCell]);

// Trap focus in modal
const trapFocus = (e) => {
  const focusableElements = modal.querySelectorAll(
    'button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );

  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];

  if (e.key === 'Tab') {
    if (e.shiftKey && document.activeElement === firstElement) {
      e.preventDefault();
      lastElement.focus();
    } else if (!e.shiftKey && document.activeElement === lastElement) {
      e.preventDefault();
      firstElement.focus();
    }
  }
};
```

**Skip Links (Future):**

```jsx
<a href="#main-content" className="skip-link">
  Skip to main content
</a>

<main id="main-content">
  <GridEditor />
</main>
```

### Color Contrast

**WCAG AA Compliant:**
- Text: 4.5:1 contrast ratio
- Large text: 3:1 contrast ratio
- UI components: 3:1 contrast ratio

```scss
// Good contrast examples
.success-badge {
  background: #4caf50;  // Green
  color: #fff;          // White (7.8:1 contrast)
}

.error-message {
  background: #f44336;  // Red
  color: #fff;          // White (6.2:1 contrast)
}
```

### Screen Reader Support

```jsx
// Announce dynamic content changes
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
>
  {autofillProgress?.message}
</div>

// Hide decorative images
<svg aria-hidden="true">
  <LockIcon />
</svg>

// Describe interactive elements
<button
  aria-label={`Cell ${row + 1}, ${col + 1}. ${cell.letter || 'Empty'}. ${cell.isBlack ? 'Black square' : ''}`}
>
  {cell.letter}
</button>
```

---

## Build & Development

### Development Server

**Start Dev Server:**
```bash
npm run dev
# → Vite dev server at http://localhost:3000
# → Proxies /api requests to http://localhost:5000
```

**Vite Configuration:**

```javascript
// vite.config.js
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'frontend/dist',
    emptyOutDir: true,
  },
});
```

### Hot Module Replacement

**HMR Enabled by Default:**
- Edit React component → instant update (preserves state)
- Edit SCSS → instant style update
- Edit config → full page reload

**HMR Boundaries:**
```javascript
// Component accepts HMR
if (import.meta.hot) {
  import.meta.hot.accept();
}
```

### Production Build

**Build for Production:**
```bash
npm run build
# → Creates optimized bundle in frontend/dist/
# → Minified JS, CSS, and assets
# → Source maps for debugging
```

**Build Output:**
```
frontend/dist/
├── index.html
├── assets/
│   ├── index-[hash].js      # Main bundle
│   ├── index-[hash].css     # Styles
│   └── vendor-[hash].js     # Dependencies
└── favicon.ico
```

### Environment Variables

**Vite Environment:**

```bash
# .env.development
VITE_API_URL=http://localhost:5000

# .env.production
VITE_API_URL=/api
```

**Usage:**
```javascript
const apiUrl = import.meta.env.VITE_API_URL;
```

### Build Optimization

**Chunking Strategy:**
- React/React-DOM → separate vendor chunk
- Component code → main bundle
- SCSS → extracted CSS file

**Tree Shaking:**
- Vite automatically removes unused code
- Use ES modules for better tree shaking
- Avoid `export *` patterns

---

## Testing Strategy

### Current State

**No tests currently implemented** (manual testing only)

### Future Testing Plan

**Unit Tests (React Testing Library):**

```javascript
// GridEditor.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import GridEditor from './GridEditor';

test('renders grid with correct size', () => {
  const grid = createEmptyGrid(15);
  render(<GridEditor grid={grid} gridSize={15} />);

  const cells = screen.getAllByRole('cell');
  expect(cells).toHaveLength(225); // 15x15
});

test('handles cell click', () => {
  const onSelectCell = jest.fn();
  render(<GridEditor onSelectCell={onSelectCell} />);

  fireEvent.click(screen.getByTestId('cell-0-0'));
  expect(onSelectCell).toHaveBeenCalledWith({ row: 0, col: 0 });
});

test('toggles black square on shift+click', () => {
  const onToggleBlack = jest.fn();
  render(<GridEditor onToggleBlack={onToggleBlack} />);

  fireEvent.click(screen.getByTestId('cell-0-0'), { shiftKey: true });
  expect(onToggleBlack).toHaveBeenCalledWith(0, 0);
});
```

**Integration Tests:**

```javascript
// App.integration.test.jsx
test('complete autofill workflow', async () => {
  render(<App />);

  // Switch to autofill panel
  fireEvent.click(screen.getByText('Autofill'));

  // Configure options
  fireEvent.change(screen.getByLabelText('Minimum Score'), {
    target: { value: '70' }
  });

  // Start autofill
  fireEvent.click(screen.getByText('Start Autofill'));

  // Wait for completion
  await waitFor(() => {
    expect(screen.getByText(/Successfully filled/)).toBeInTheDocument();
  });
});
```

**E2E Tests (Cypress/Playwright - Future):**

```javascript
// cypress/e2e/autofill.cy.js
describe('Autofill Feature', () => {
  it('fills grid successfully', () => {
    cy.visit('http://localhost:3000');

    // Navigate to autofill
    cy.contains('Autofill').click();

    // Configure and start
    cy.get('input[type="range"]').invoke('val', 70).trigger('change');
    cy.contains('Start Autofill').click();

    // Wait for progress
    cy.contains('Successfully filled', { timeout: 60000 });

    // Verify grid is filled
    cy.get('.grid-cell').should('contain', /[A-Z]/);
  });
});
```

### Test Coverage Goals

- **Unit Tests**: 80%+ coverage of components
- **Integration Tests**: Key user workflows
- **E2E Tests**: Critical paths (autofill, import/export)

---

## Deployment

### Static Hosting

**Build for Production:**
```bash
npm run build
# → Creates frontend/dist/ with static files
```

**Serve Static Files:**

Option 1: Flask serves frontend
```python
# backend/app.py
@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend/dist', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend/dist', path)
```

Option 2: Nginx serves frontend
```nginx
server {
    listen 80;

    location / {
        root /var/www/crossword-helper/frontend/dist;
        try_files $uri /index.html;
    }

    location /api {
        proxy_pass http://localhost:5000;
    }
}
```

### Environment Configuration

**Development:**
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:5000`
- Vite proxy handles API requests

**Production:**
- Frontend: Served from `frontend/dist`
- Backend: Same origin `/api`
- No CORS needed

### CDN Considerations (Future)

**Asset Optimization:**
- Upload static assets to CDN
- Update `base` in vite.config.js
- Configure cache headers

```javascript
// vite.config.js
export default defineConfig({
  base: 'https://cdn.example.com/crossword/',
  build: {
    rollupOptions: {
      output: {
        assetFileNames: 'assets/[name]-[hash][extname]'
      }
    }
  }
});
```

---

## Code Examples

### Example 1: Creating a New Component

```javascript
// src/components/NewFeature.jsx
import React, { useState, useCallback } from 'react';
import './NewFeature.scss';

function NewFeature({ grid, onUpdate }) {
  const [localState, setLocalState] = useState(null);

  const handleAction = useCallback(() => {
    // Component logic
    onUpdate(newData);
  }, [grid, onUpdate]);

  return (
    <div className="new-feature">
      <h2>New Feature</h2>
      <button onClick={handleAction}>Do Something</button>
    </div>
  );
}

export default NewFeature;
```

```scss
// src/components/NewFeature.scss
.new-feature {
  padding: 1rem;

  h2 {
    margin-bottom: 1rem;
  }

  button {
    background: #667eea;
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 6px;

    &:hover {
      background: #5568d3;
    }
  }
}
```

### Example 2: Adding API Integration

```javascript
// Add to App.jsx or component
const handleNewFeature = async () => {
  try {
    const response = await axios.post('/api/new-feature', {
      grid: grid,
      options: { ... }
    });

    const result = response.data;

    // Update state
    setGrid(result.updated_grid);
    toast.success('Feature applied successfully!');

  } catch (error) {
    const errorMsg = error.response?.data?.error || 'Request failed';
    toast.error(errorMsg);
  }
};
```

### Example 3: Adding SSE Progress

```javascript
// Use the useSSEProgress hook
import { useSSEProgress } from '../hooks/useSSEProgress';

function MyComponent() {
  const progress = useSSEProgress();

  const startLongOperation = async () => {
    // Start operation
    const response = await axios.post('/api/operation/with-progress', {...});
    const { task_id } = response.data;

    // Connect to progress stream
    progress.connect(task_id);
  };

  return (
    <div>
      <button onClick={startLongOperation}>Start</button>

      {progress.status === 'running' && (
        <ProgressIndicator
          type="bar"
          progress={progress.progress}
          message={progress.message}
        />
      )}
    </div>
  );
}
```

### Example 4: Adding Keyboard Shortcut

```javascript
// In GridEditor or other component
useEffect(() => {
  const handleKeyDown = (e) => {
    // Ctrl+S to save
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      handleSave();
    }

    // Ctrl+Z to undo
    if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
      e.preventDefault();
      handleUndo();
    }
  };

  window.addEventListener('keydown', handleKeyDown);

  return () => {
    window.removeEventListener('keydown', handleKeyDown);
  };
}, [handleSave, handleUndo]);
```

---

## Best Practices

### Component Design

**1. Single Responsibility**
```javascript
// ✅ GOOD: One component, one job
function CellRenderer({ cell }) {
  return <td>{cell.letter}</td>;
}

function GridRenderer({ grid }) {
  return (
    <table>
      {grid.map(row => (
        row.map(cell => <CellRenderer cell={cell} />)
      ))}
    </table>
  );
}

// ❌ BAD: Component does too much
function MegaComponent() {
  // Handles grid, autofill, export, import, etc.
}
```

**2. Props vs State**
```javascript
// Props: Data passed from parent
function Child({ value, onChange }) {
  return <input value={value} onChange={onChange} />;
}

// State: Local component data
function Parent() {
  const [value, setValue] = useState('');
  return <Child value={value} onChange={setValue} />;
}
```

**3. Composition over Inheritance**
```javascript
// ✅ GOOD: Compose with children
function Panel({ title, children }) {
  return (
    <div className="panel">
      <h2>{title}</h2>
      {children}
    </div>
  );
}

<Panel title="Options">
  <OptionList />
</Panel>

// ❌ BAD: Class inheritance
class OptionsPanel extends Panel {
  // Complex inheritance chain
}
```

### State Management

**1. Lift State Up**
```javascript
// ✅ GOOD: Shared state in parent
function App() {
  const [grid, setGrid] = useState(null);
  return (
    <>
      <GridEditor grid={grid} onChange={setGrid} />
      <AutofillPanel grid={grid} />
    </>
  );
}

// ❌ BAD: Duplicate state in children
function GridEditor() {
  const [grid, setGrid] = useState(null); // ❌
}
function AutofillPanel() {
  const [grid, setGrid] = useState(null); // ❌ Duplicate!
}
```

**2. Immutable Updates**
```javascript
// ✅ GOOD: Create new objects
const newGrid = grid.map(row => [...row]);
newGrid[0][0] = { ...newGrid[0][0], letter: 'A' };
setGrid(newGrid);

// ❌ BAD: Mutate existing
grid[0][0].letter = 'A';
setGrid(grid); // React won't detect change
```

**3. Derived State**
```javascript
// ✅ GOOD: Calculate on render
const totalCells = grid.length * grid.length;
const blackCells = grid.flat().filter(c => c.isBlack).length;

// ❌ BAD: Store calculated values
const [totalCells, setTotalCells] = useState(0);
const [blackCells, setBlackCells] = useState(0);
// Now you have to keep these in sync!
```

### Performance

**1. Memoization**
```javascript
// ✅ Use for expensive calculations
const gridStats = useMemo(() => {
  return calculateComplexStats(grid);
}, [grid]);

// ❌ Don't overuse for simple operations
const doubled = useMemo(() => value * 2, [value]); // Overkill
```

**2. Event Handlers**
```javascript
// ✅ GOOD: useCallback for passed callbacks
const handleClick = useCallback(() => {
  onUpdate(grid);
}, [grid, onUpdate]);

// ❌ BAD: Inline function (re-creates every render)
<button onClick={() => onUpdate(grid)}>
```

**3. Keys in Lists**
```javascript
// ✅ GOOD: Stable unique keys
{items.map(item => (
  <Item key={item.id} data={item} />
))}

// ❌ BAD: Index as key
{items.map((item, idx) => (
  <Item key={idx} data={item} />
))}
```

### Error Handling

**1. Try-Catch for Async**
```javascript
const fetchData = async () => {
  try {
    const response = await axios.get('/api/data');
    setData(response.data);
  } catch (error) {
    if (error.response) {
      toast.error(error.response.data.error);
    } else {
      toast.error('Network error');
    }
  }
};
```

**2. Error Boundaries (Future)**
```javascript
class ErrorBoundary extends React.Component {
  state = { hasError: false };

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error('Error:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return <h1>Something went wrong.</h1>;
    }
    return this.props.children;
  }
}
```

### Code Organization

**1. File Structure**
```
components/
├── GridEditor/           # ✅ Component folder
│   ├── index.jsx
│   ├── GridEditor.scss
│   └── GridEditor.test.jsx
└── PatternMatcher.jsx    # ✅ Single file for simple components
```

**2. Import Order**
```javascript
// 1. External dependencies
import React, { useState } from 'react';
import axios from 'axios';

// 2. Internal components
import GridEditor from './components/GridEditor';
import PatternMatcher from './components/PatternMatcher';

// 3. Styles
import './App.scss';

// 4. Utilities
import { calculateStats } from './utils/gridHelpers';
```

**3. Named Exports vs Default**
```javascript
// ✅ Default export for main component
export default GridEditor;

// ✅ Named exports for utilities
export { calculateStats, validateGrid };
```

---

## Appendices

### A. Common Patterns Reference

**Pattern 1: Controlled Input**
```javascript
const [value, setValue] = useState('');
<input value={value} onChange={(e) => setValue(e.target.value)} />
```

**Pattern 2: Conditional Rendering**
```javascript
{isLoading ? <Spinner /> : <Content />}
{error && <ErrorMessage error={error} />}
{items.length > 0 && <List items={items} />}
```

**Pattern 3: Event Handlers**
```javascript
const handleClick = (e) => {
  e.preventDefault();
  // Logic
};
```

### B. Troubleshooting Guide

**Issue: Grid not updating**
- Check if you're mutating state directly
- Ensure `setGrid()` receives new array/object
- Verify keys in lists are stable

**Issue: SSE not connecting**
- Check if backend is running (localhost:5000)
- Verify task_id is correct
- Check browser console for errors
- Ensure EventSource API is supported

**Issue: Styles not applying**
- Check SCSS syntax errors
- Verify class names match
- Clear browser cache
- Check CSS specificity conflicts

### C. Migration Notes

**From Class Components to Hooks:**
```javascript
// Before (Class)
class MyComponent extends React.Component {
  state = { count: 0 };

  componentDidMount() {
    // Setup
  }

  render() {
    return <div>{this.state.count}</div>;
  }
}

// After (Hooks)
function MyComponent() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    // Setup
  }, []);

  return <div>{count}</div>;
}
```

---

## Glossary

- **CSP** - Constraint Satisfaction Problem (autofill algorithm)
- **SSE** - Server-Sent Events (real-time progress streaming)
- **HMR** - Hot Module Replacement (instant code updates)
- **SPA** - Single Page Application
- **CLI** - Command Line Interface
- **SCSS** - Sassy CSS (CSS preprocessor)
- **BEM** - Block Element Modifier (CSS naming convention)
- **ARIA** - Accessible Rich Internet Applications

---

## Changelog

### Version 2.0.0 (December 27, 2025)
- Complete frontend specification documented
- All components catalogued and explained
- Architecture patterns defined
- Best practices established
- Code examples provided

### Version 1.0.0 (December 21, 2025)
- Initial React application implemented
- Basic grid editor and tools
- API integration complete

---

**Document Status:** Complete and comprehensive
**Next Review:** When major features are added
**Maintained By:** Development Team
**Related Documents:**
- [ARCHITECTURE.md](/Users/apa/projects/untitled_project/crossword-helper/docs/ARCHITECTURE.md)
- [API_REFERENCE.md](/Users/apa/projects/untitled_project/crossword-helper/docs/api/API_REFERENCE.md)
- [BACKEND_SPEC.md](/Users/apa/projects/untitled_project/crossword-helper/docs/specs/BACKEND_SPEC.md)
