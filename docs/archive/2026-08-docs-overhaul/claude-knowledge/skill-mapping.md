# Skill Mapping Reference

**Quick reference for which skill to use for each task.**

---

## Testing Skills

### `python-testing-patterns`
**When:** Writing pytest tests (unit or integration)
**Triggers:** "pytest", "unit test", "integration test", "mock", "fixture"
**Example prompts:**
- "Write pytest unit tests for the CLIAdapter class"
- "Create fixtures for grid test data"
- "Mock the subprocess call in this test"

### `javascript-testing-patterns`
**When:** Writing vitest/React tests
**Triggers:** "vitest", "React Testing Library", "component test", "MSW"
**Example prompts:**
- "Write vitest tests for the GridEditor component"
- "Test user interactions with React Testing Library"
- "Mock this axios API call with MSW"

### `e2e-testing-patterns`
**When:** Writing end-to-end integration tests
**Triggers:** "end-to-end", "e2e", "user journey", "integration"
**Example prompts:**
- "Create end-to-end tests for the autofill workflow"
- "Test the complete user journey from grid creation to export"
- "Verify integration between frontend and backend"

### `test-driven-development`
**When:** Implementing features with TDD approach
**Triggers:** "TDD", "test-first", "red-green-refactor"
**Example prompts:**
- "Use TDD to implement a new grid rotation endpoint"
- "Write failing tests first for the theme validation feature"
- "Red-green-refactor approach for pattern matching optimization"

### `test-fixing`
**When:** Debugging failing tests
**Triggers:** "test failure", "failing test", "test regression"
**Example prompts:**
- "Fix the failing integration test for autofill"
- "Debug why this pytest test is timing out"
- "This test worked before, now it's failing - fix it"

---

## Development Skills

### `python-development`
**When:** Writing Python code (backend or CLI)
**Triggers:** "Python", "async", "NumPy", "Flask"
**Example prompts:**
- "Implement this Python async function"
- "Optimize this NumPy algorithm"
- "Add type hints to this module"

### `react-state-management`
**When:** Working with React components and state
**Triggers:** "React", "useState", "useEffect", "component"
**Example prompts:**
- "Manage complex state in this React component"
- "Use useEffect to fetch data from the API"
- "Optimize re-renders with useMemo"

### `nextjs-app-router-patterns`
**When:** NOT APPLICABLE (this project uses Vite, not Next.js)

### `fastapi-templates`
**When:** Adding Flask API endpoints (adaptable to Flask)
**Triggers:** "API endpoint", "Flask route", "RESTful"
**Example prompts:**
- "Create a RESTful endpoint following best practices"
- "Implement request validation for this Flask route"
- "Add async route handler for this endpoint"

### `async-python-patterns`
**When:** Working with async/await in Python
**Triggers:** "async", "await", "asyncio", "concurrent"
**Example prompts:**
- "Convert this function to async/await"
- "Handle concurrent subprocess calls"
- "Implement async progress tracking"

---

## Debugging Skills

### `systematic-debugging`
**When:** Debugging ANY issue (highest priority)
**Triggers:** "debug", "error", "failure", "crash", "root cause"
**Example prompts:**
- "Debug this test failure systematically"
- "Find the root cause of this subprocess timeout"
- "Trace this error through the stack"
- "The autofill is crashing - debug systematically"

### `error-debugging`
**When:** Analyzing errors in logs or traces
**Triggers:** "error message", "stack trace", "logs", "exception"
**Example prompts:**
- "Search logs for this error pattern"
- "Analyze this stack trace"
- "Identify where this error originates"

---

## Workflow Skills

### `brainstorming`
**When:** Starting ANY new feature (use FIRST, before coding)
**Triggers:** "design", "explore", "options", "approach"
**Example prompts:**
- "Brainstorm the design for a grid rotation feature"
- "Explore API structure for theme word management"
- "Consider trade-offs between CSP and Beam Search"

### `verification-before-completion`
**When:** Before claiming work is done (ALWAYS use)
**Triggers:** "complete", "done", "finished", "ready"
**Example prompts:**
- "Verify all tests pass before committing"
- "Check that the implementation is complete"
- "Ensure no regressions were introduced"
- "I'm done with this feature - verify it's complete"

### `requesting-code-review`
**When:** Before creating PR or committing major changes
**Triggers:** "code review", "PR", "pull request", "commit"
**Example prompts:**
- "Perform self-code-review on these changes"
- "Prepare PR description for the rotation feature"
- "Check code quality before creating PR"

### `receiving-code-review`
**When:** Processing code review feedback
**Triggers:** "review feedback", "comments", "suggestions"
**Example prompts:**
- "Process this code review feedback"
- "The reviewer suggests refactoring - evaluate if it's needed"
- "Implement review comments systematically"

### `feature-planning`
**When:** Planning multi-step feature implementation
**Triggers:** "plan", "feature", "implementation steps"
**Example prompts:**
- "Plan the implementation steps for grid rotation"
- "Create a feature plan for pause/resume functionality"
- "Break down this feature into tasks"

### `git-pushing`
**When:** Preparing to push code
**Triggers:** "git push", "commit", "PR"
**Example prompts:**
- "Prepare to push the rotation feature"
- "Create commit messages for these changes"
- "Ready to push - verify everything is correct"

---

## Documentation Skills

### `openapi-spec-generation`
**When:** Documenting API endpoints
**Triggers:** "API docs", "OpenAPI", "endpoint documentation"
**Example prompts:**
- "Generate OpenAPI spec for the new rotation endpoint"
- "Document the theme validation API"
- "Create API reference for wordlist endpoints"

### `architecture-decision-records`
**When:** Documenting architectural decisions
**Triggers:** "architecture", "ADR", "design decision"
**Example prompts:**
- "Write an ADR for choosing subprocess over direct integration"
- "Document the decision to use trie-based pattern matching"
- "Create ADR for the pause/resume state management approach"

---

## Project-Specific Skill Usage

### Adding New API Endpoint
1. `brainstorming` - Design endpoint first
2. `test-driven-development` - Write failing test
3. `python-development` - Implement Flask route
4. `python-testing-patterns` - Write unit tests
5. `verification-before-completion` - Verify all tests pass

### Fixing Bug
1. `systematic-debugging` - Find root cause
2. `test-fixing` - Add regression test
3. `python-development` or `react-state-management` - Fix the bug
4. `verification-before-completion` - Verify fix and no regressions

### Adding React Component
1. `brainstorming` - Design component API
2. `react-state-management` - Implement component
3. `javascript-testing-patterns` - Write component tests
4. `verification-before-completion` - Verify tests pass

### Debugging Integration Test
1. `systematic-debugging` - Debug each layer (Frontend → API → CLI)
2. `error-debugging` - Analyze error messages
3. `test-fixing` - Fix the test or the code
4. `verification-before-completion` - Verify fix

---

## Anti-Pattern: Skill NOT Used

**DON'T:**
- Start coding without `brainstorming` first
- Claim work is done without `verification-before-completion`
- Debug randomly without `systematic-debugging`
- Write tests without `test-driven-development` or `python-testing-patterns`
- Push code without `git-pushing` or `requesting-code-review`

**DO:**
- ALWAYS use `brainstorming` before implementing features
- ALWAYS use `systematic-debugging` when encountering errors
- ALWAYS use `verification-before-completion` before claiming done
- ALWAYS use `test-driven-development` for new features

---

**Last Updated:** January 2026
