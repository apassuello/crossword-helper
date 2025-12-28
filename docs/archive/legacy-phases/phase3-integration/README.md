# Phase 3: Integration

**Goal:** Refactor web app to use CLI backend for shared implementation

**Timeline:** 1 week
**Complexity:** Medium
**Status:** ⏸️ Waiting for Phases 1 & 2 completion

---

## Overview

Integrate Phases 1 and 2 by refactoring the web app (Phase 1) to use the CLI tool (Phase 2) as its backend.

**Benefits:**
- Single source of truth for all logic
- Autofill becomes available in web UI
- No code duplication
- Easier maintenance

---

## Approach

### Before Integration
```
Web App: Direct implementations
CLI Tool: Separate implementations
→ Two codebases doing similar things
```

### After Integration
```
Web App: Calls CLI tool via subprocess
CLI Tool: Single implementation
→ One codebase, two interfaces (web + CLI)
```

---

## New Feature

**Autofill in Web UI:**
- New endpoint: `POST /api/fill`
- Frontend component with progress tracking
- WebSocket or polling for real-time updates
- Cancel/pause controls

---

## Documentation

Will be created after Phase 2 completion:
- `01-refactoring-plan.md` - How to refactor web app
- `02-api-evolution.md` - API changes needed
- `03-implementation-checklist.md` - Step-by-step tasks

---

## Status

**⏸️ Waiting for Phase 2 completion**

Documentation will be written after Phase 2 is done and we understand the exact CLI interfaces.
