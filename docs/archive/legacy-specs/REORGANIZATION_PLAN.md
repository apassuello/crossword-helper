# Documentation Reorganization Plan

**Goal**: Organize documentation to support 3-phase development approach:
1. Phase 1: Flask Web App (simple helper tool)
2. Phase 2: CLI Tool (comprehensive crossword builder)
3. Phase 3: Integration (web app interfaces with CLI backend)

---

## Current State Analysis

### Files at Repository Root (should be in crossword-helper/)

**Phase 1 - Web App Docs:**
- `CLAUDE.md` - Web app architecture overview
- `README-claude-code.md` - Quick start for web app
- `02-api-specification.md` - REST API contracts
- `04-frontend-implementation-guide.md` - Complete frontend code

**Phase 2 - CLI Tool Docs:**
- `ARCHITECTURE.md` - Comprehensive CLI tool architecture
- `SPECIFICATIONS.md` - Detailed technical specifications
- `01-architecture.md` - Duplicate/alternate version?
- `pattern-match.md` - CLI command spec
- `validate-grid.md` - CLI command spec

**General/Setup:**
- `setup.md` - Initial setup instructions
- `test-all.md` - Testing command
- `custom-instructions-claude-ai.md` - AI assistant configuration

**To DELETE:**
- `clf_c02_questions.json` - AWS certification (unrelated)
- `clf_c02_questions.md` - AWS certification (unrelated)
- `clf_c02_questions_answers.md` - AWS certification (unrelated)
- `clf_c02_questions_questions.md` - AWS certification (unrelated)
- `.DS_Store` - macOS system file

**Duplicates (at root and in crossword-helper/):**
- `requirements.txt` - Keep in crossword-helper/ only
- `run.py` - Keep in crossword-helper/ only

---

## Target Structure

```
/home/user/untitled_project/
└── crossword-helper/
    │
    ├── README.md
    │   Updated with 3-phase roadmap overview
    │
    ├── docs/
    │   ├── ROADMAP.md
    │   │   Master project plan with all 3 phases
    │   │
    │   ├── phase1-webapp/
    │   │   ├── README.md
    │   │   │   Phase 1 overview and objectives
    │   │   ├── 01-architecture.md
    │   │   │   (from CLAUDE.md - web app architecture)
    │   │   ├── 02-api-specification.md
    │   │   │   (from 02-api-specification.md)
    │   │   ├── 03-frontend-guide.md
    │   │   │   (from 04-frontend-implementation-guide.md)
    │   │   └── 04-implementation-checklist.md
    │   │       Step-by-step implementation tasks
    │   │
    │   ├── phase2-cli/
    │   │   ├── README.md
    │   │   │   Phase 2 overview and objectives
    │   │   ├── 01-architecture.md
    │   │   │   (from ARCHITECTURE.md - CLI architecture)
    │   │   ├── 02-specifications.md
    │   │   │   (from SPECIFICATIONS.md)
    │   │   ├── 03-commands.md
    │   │   │   Consolidation of pattern-match.md, validate-grid.md
    │   │   └── 04-implementation-checklist.md
    │   │       Step-by-step implementation tasks
    │   │
    │   ├── phase3-integration/
    │   │   ├── README.md
    │   │   │   Phase 3 overview
    │   │   ├── 01-refactoring-plan.md
    │   │   │   How to refactor web app to use CLI backend
    │   │   ├── 02-api-evolution.md
    │   │   │   How API changes from direct implementation to CLI wrapper
    │   │   └── 03-implementation-checklist.md
    │   │       Step-by-step refactoring tasks
    │   │
    │   └── guides/
    │       ├── testing.md
    │       │   (from test-all.md + additional testing strategy)
    │       ├── development-workflow.md
    │       │   Daily development practices
    │       └── troubleshooting.md
    │           Common issues and solutions
    │
    ├── .claude/
    │   ├── CLAUDE.md
    │   │   Combined guide for AI assistants (all phases)
    │   └── commands/
    │       ├── setup.md
    │       │   (from setup.md)
    │       ├── test-all.md
    │       │   (from test-all.md)
    │       ├── pattern-match.md
    │       │   (from pattern-match.md - for Phase 2)
    │       └── validate-grid.md
    │           (from validate-grid.md - for Phase 2)
    │
    ├── backend/
    ├── frontend/
    ├── tests/
    ├── data/
    ├── requirements.txt
    ├── run.py
    ├── .gitignore
    └── pytest.ini
```

---

## File Mapping

### DELETE (unrelated to project)
- `/clf_c02_questions.json` → DELETE
- `/clf_c02_questions.md` → DELETE
- `/clf_c02_questions_answers.md` → DELETE
- `/clf_c02_questions_questions.md` → DELETE
- `/.DS_Store` → DELETE
- `/requirements.txt` → DELETE (duplicate, keep crossword-helper/requirements.txt)
- `/run.py` → DELETE (duplicate, keep crossword-helper/run.py)

### MOVE to docs/phase1-webapp/
- `/CLAUDE.md` → `docs/phase1-webapp/01-architecture.md`
- `/02-api-specification.md` → `docs/phase1-webapp/02-api-specification.md`
- `/04-frontend-implementation-guide.md` → `docs/phase1-webapp/03-frontend-guide.md`
- `/README-claude-code.md` → Content merged into `docs/phase1-webapp/README.md`

### MOVE to docs/phase2-cli/
- `/ARCHITECTURE.md` → `docs/phase2-cli/01-architecture.md`
- `/SPECIFICATIONS.md` → `docs/phase2-cli/02-specifications.md`
- `/01-architecture.md` → Check if duplicate, merge/delete as needed
- `/pattern-match.md` → Content goes into `docs/phase2-cli/03-commands.md`
- `/validate-grid.md` → Content goes into `docs/phase2-cli/03-commands.md`

### MOVE to .claude/commands/
- `/setup.md` → `.claude/commands/setup.md`
- `/test-all.md` → `.claude/commands/test-all.md`
- `/pattern-match.md` → `.claude/commands/pattern-match.md` (copy, also in docs)
- `/validate-grid.md` → `.claude/commands/validate-grid.md` (copy, also in docs)

### CREATE NEW
- `docs/ROADMAP.md` - Master 3-phase plan
- `docs/phase1-webapp/README.md` - Phase 1 overview
- `docs/phase1-webapp/04-implementation-checklist.md` - Phase 1 tasks
- `docs/phase2-cli/README.md` - Phase 2 overview
- `docs/phase2-cli/03-commands.md` - Consolidated CLI commands
- `docs/phase2-cli/04-implementation-checklist.md` - Phase 2 tasks
- `docs/phase3-integration/README.md` - Phase 3 overview
- `docs/phase3-integration/01-refactoring-plan.md` - Integration strategy
- `docs/phase3-integration/02-api-evolution.md` - API changes
- `docs/phase3-integration/03-implementation-checklist.md` - Phase 3 tasks
- `docs/guides/testing.md` - Testing guide
- `docs/guides/development-workflow.md` - Dev practices
- `docs/guides/troubleshooting.md` - Common issues
- `.claude/CLAUDE.md` - Combined AI assistant guide (all phases)

### UPDATE
- `crossword-helper/README.md` - Add 3-phase overview

---

## Execution Order

1. **Create directory structure**
   - `docs/phase1-webapp/`
   - `docs/phase2-cli/`
   - `docs/phase3-integration/`
   - `docs/guides/`
   - `.claude/commands/`

2. **Delete unrelated files**
   - AWS certification files
   - .DS_Store
   - Root duplicates

3. **Move existing docs** (with git mv to preserve history)
   - Phase 1 docs → docs/phase1-webapp/
   - Phase 2 docs → docs/phase2-cli/
   - Command specs → .claude/commands/

4. **Create new documentation**
   - ROADMAP.md (master plan)
   - Phase READMEs
   - Implementation checklists
   - Guides

5. **Update existing files**
   - Main README.md with roadmap link
   - .claude/CLAUDE.md with all-phase guide

6. **Commit reorganization**
   - Clear commit message explaining new structure

---

## Benefits of This Structure

1. **Clear Phase Separation**: Each phase has its own directory
2. **Easy Navigation**: Developers can focus on current phase
3. **Preserved Context**: Original docs kept intact, just reorganized
4. **AI Assistant Friendly**: .claude/ directory contains all AI guidance
5. **Scalable**: Easy to add Phase 4, 5, etc. in future
6. **Version Control**: Using git mv preserves file history
7. **Single Source of Truth**: All docs in one place (docs/)

---

## Timeline Estimate

**Phase 1 (Web App)**: 3-5 days
- 3 REST endpoints
- Simple frontend
- Basic testing
- Deployable MVP

**Phase 2 (CLI Tool)**: 3-4 weeks
- Grid engine with NumPy
- CSP autofill algorithm
- Pattern matcher
- Export engines
- Comprehensive testing

**Phase 3 (Integration)**: 1 week
- Refactor web app backend
- Route API calls to CLI
- Update tests
- Performance tuning

**Total Project**: 5-6 weeks for complete system

---

## Next Steps

1. Review this plan
2. Execute reorganization
3. Implement Phase 1
4. Implement Phase 2
5. Implement Phase 3

---

**Status**: Plan created, awaiting approval to execute
