# Crossword Helper System - Architecture Document

## Executive Summary

**System Type:** Local web application for crossword puzzle construction assistance  
**Primary Users:** Technical user (expert) + non-technical user (partner)  
**Deployment:** Local development server (localhost:5000)  
**Timeline:** 10-12 hours development time  

**Core Purpose:** Assist crossword construction by solving three specific pain points:
1. Pattern matching (finding words that fit `?I?A` patterns)
2. Grid numbering (automatic numbering and validation)
3. Convention handling (normalizing multi-word entries like "Tina Fey" → "TINAFEY")

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   USER'S BROWSER                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Frontend (Single Page Application)               │  │
│  │  - HTML/CSS/JS (Vanilla, no framework)           │  │
│  │  - Three tool components                          │  │
│  │  - Responsive design (mobile-first)               │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────────────┘
                       │ HTTP/JSON
                       │ (fetch API)
┌──────────────────────▼───────────────────────────────────┐
│            FLASK BACKEND (localhost:5000)                 │
│  ┌───────────────────────────────────────────────────┐  │
│  │  API Layer (routes.py)                            │  │
│  │  - POST /api/pattern                              │  │
│  │  - POST /api/number                               │  │
│  │  - POST /api/normalize                            │  │
│  │  - Error handling, CORS                           │  │
│  └─────────────────────┬─────────────────────────────┘  │
│                        │ delegates to                     │
│  ┌─────────────────────▼─────────────────────────────┐  │
│  │  Service Layer (core/*.py)                        │  │
│  │  - PatternMatcher: search, score                  │  │
│  │  - NumberingValidator: auto_number, validate      │  │
│  │  - ConventionHelper: normalize, explain           │  │
│  └─────────────────────┬─────────────────────────────┘  │
│                        │ uses                             │
│  ┌─────────────────────▼─────────────────────────────┐  │
│  │  Data Layer (data/*.py)                           │  │
│  │  - OneLookClient: API integration                 │  │
│  │  - WordListManager: file loading                  │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│                EXTERNAL RESOURCES                         │
│  - OneLook API (pattern matching data)                   │
│  - Local word lists (data/wordlists/*.txt)               │
└───────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

#### Frontend Layer
**Technology:** Vanilla HTML/CSS/JavaScript  
**Responsibilities:**
- Render three tool interfaces (Pattern Matcher, Numbering Validator, Convention Helper)
- Handle user input validation (client-side)
- Make API calls via fetch()
- Display results with proper formatting
- Show loading states and errors
- Mobile-responsive layout

**Why Vanilla JS:**
- Only 3 components (React overhead unjustified)
- No build step needed
- Faster development for this scope
- Lighter weight (~50KB vs ~500KB)

#### API Layer
**Technology:** Flask routes  
**Responsibilities:**
- Parse HTTP requests (JSON)
- Validate request format
- Delegate to service layer
- Format responses (JSON)
- Handle errors with appropriate status codes
- CORS configuration

**Why Thin Layer:**
- Keep business logic testable
- Enable service reuse (could add CLI later)
- Clear separation of concerns

#### Service Layer
**Technology:** Pure Python classes  
**Responsibilities:**
- Pattern matching logic
- Numbering algorithm
- Convention rules application
- Word scoring
- No HTTP concerns (testable in isolation)

**Why Separate:**
- Unit testable without HTTP
- Reusable across interfaces
- Clear business logic

#### Data Layer
**Technology:** Python clients/managers  
**Responsibilities:**
- External API calls (OneLook)
- File I/O (word lists)
- Error handling (timeouts, fallbacks)
- Optional caching

**Why Separate:**
- Swap implementations easily
- Mock for testing
- Handle external failures gracefully

---

## Technology Stack

### Backend Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | Python 3.9+ | Expert familiarity, rich ecosystem |
| **Web Framework** | Flask 3.0+ | Simpler than FastAPI for synchronous I/O-bound work |
| **Testing** | pytest | Industry standard, excellent fixtures |
| **HTTP Client** | requests | Mature, simple API for OneLook calls |
| **Type Hints** | Python typing | Better IDE support, self-documenting |

**Not using:**
- **FastAPI:** Async unnecessary (I/O-bound, not CPU-bound)
- **Django:** Too heavy for simple API server
- **SQLAlchemy:** No database in MVP (file-based)

### Frontend Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **HTML** | Semantic HTML5 | Accessibility, SEO-friendly |
| **CSS** | Vanilla CSS3 | No preprocessor needed for this scope |
| **JavaScript** | ES6+ (fetch, async/await) | Modern, clean, no transpiling |
| **Bundler** | None | Serve static files directly |

**Not using:**
- **React/Vue:** 3 components don't justify framework overhead
- **TypeScript:** Adds build complexity, diminishing returns
- **Sass/Less:** CSS3 variables sufficient
- **Webpack/Vite:** No bundling needed

### Data Storage

| Type | Solution | Rationale |
|------|----------|-----------|
| **Word Lists** | Text files (.txt) | Simple, editable, version-controllable |
| **Configuration** | Python config.py | No external config needed |
| **Cache** | In-memory (optional) | OneLook results caching |

**Phase 2 (optional):**
- SQLite for search history, user preferences
- Migration path designed but not implemented in MVP

---

## Design Patterns

### Service Pattern
**Pattern:** Each business domain has a service class with pure methods.

**Example:**
```python
class PatternMatcher:
    def __init__(self, wordlists: List[str]):
        self.wordlists = wordlists
    
    def search(self, pattern: str, max_results: int = 20) -> List[Tuple[str, int]]:
        """
        Pure business logic, no HTTP concerns.
        Returns: List of (word, score) tuples
        """
        pass
```

**Benefits:**
- Testable without HTTP server
- Reusable in other interfaces
- Clear contracts

### Repository Pattern
**Pattern:** Data access abstracted behind interfaces.

**Example:**
```python
class WordListManager:
    def load(self, name: str) -> List[str]:
        """Load word list from file or cache"""
        pass

class OneLookClient:
    def search(self, pattern: str) -> List[str]:
        """Query OneLook API with fallback"""
        pass
```

**Benefits:**
- Swap implementations (files → database)
- Mock for testing
- Handle external failures

### Error Handling Pattern
**Pattern:** Graceful degradation, never crash.

**Example:**
```python
try:
    onelook_results = onelook_client.search(pattern, timeout=5)
except (Timeout, RequestException):
    onelook_results = []  # Fallback to local only
    logger.warning("OneLook API unavailable, using local wordlists")

# Merge with local results
all_results = merge_results(onelook_results, local_results)
```

**Benefits:**
- System works even if OneLook down
- User sees some results, not crash
- Logged for debugging

---

## API Design

### RESTful Conventions

**Endpoints:**
- `POST /api/pattern` - Pattern search (POST because body needed)
- `POST /api/number` - Numbering validation (POST because grid data)
- `POST /api/normalize` - Convention normalization (POST because text transformation)

**Why all POST:**
- All require request bodies
- Semantic fit (transformations, not resource retrieval)
- JSON request bodies cleaner than query params

### Response Format Standard

**Success Response:**
```json
{
    "data": { /* actual results */ },
    "meta": {
        "query_time_ms": 245,
        "version": "1.0"
    }
}
```

**Error Response:**
```json
{
    "error": {
        "code": "INVALID_PATTERN",
        "message": "Pattern must contain at least one ?",
        "details": {
            "received": "ABCD",
            "expected": "?I?A"
        }
    }
}
```

**Benefits:**
- Consistent structure across endpoints
- Machine-readable error codes
- Helpful error details

---

## Security Considerations

### Threat Model

**In Scope:**
- Local development environment
- Trusted users (you and partner)
- Private network (localhost)

**Out of Scope:**
- Public internet exposure
- Authentication/authorization
- SQL injection (no database)
- XSS attacks (no user-generated HTML)

### Security Measures

**Input Validation:**
- Pattern length limits (max 50 chars)
- Grid size limits (max 21×21)
- Request size limits (max 1MB)

**Rate Limiting:**
- OneLook API: respect their limits (1 req/sec)
- No need for user rate limiting (local)

**CORS:**
- Allow localhost origins only
- Prevents accidental public exposure

---

## Performance Requirements

### Response Time Targets

| Endpoint | Target | Rationale |
|----------|--------|-----------|
| Pattern search | <1 second | User waiting, needs instant feedback |
| Numbering validation | <100ms | Pure computation, should be instant |
| Convention normalize | <50ms | Simple string operations |

### Scalability Considerations

**Current Scale:**
- 1-2 concurrent users
- ~100 requests/hour max
- Word lists <10,000 words

**Designed For:**
- Single machine, no clustering
- In-memory caching sufficient
- No database indexing needed

**Future Scale (if deployed):**
- Could handle 10-100 users with current design
- Add Redis for shared caching
- Add rate limiting per user

---

## Testing Strategy

### Test Pyramid

```
       /\
      /E2E\         2 tests (critical user flows)
     /____\
    /      \
   /  INT   \       5 tests (API endpoints)
  /__________\
 /            \
/     UNIT     \    20+ tests (business logic)
/_______________\
```

**Why this distribution:**
- Most tests at unit level (fast, specific)
- Fewer integration tests (slower, broader)
- Minimal E2E (slowest, most brittle)

### Test Coverage Targets

| Layer | Target | Justification |
|-------|--------|---------------|
| Service layer | >90% | Core business logic, mission-critical |
| API layer | >80% | Thin wrapper, less complexity |
| Data layer | >85% | External dependencies, important |
| Overall | >85% | High confidence in correctness |

### Test Types

**Unit Tests:**
- Test each service method independently
- Mock external dependencies (OneLook API, file I/O)
- Fast execution (<1s for full suite)

**Integration Tests:**
- Test API endpoints via HTTP requests
- Use test Flask client
- Verify JSON responses

**End-to-End Tests:**
- Manual testing in browser (not automated)
- Verify all three tools work
- Test on mobile viewport

---

## Deployment Architecture

### Development Environment

**Setup:**
```bash
# Clone repository
git clone <repo-url>
cd crossword-helper

# Install dependencies
pip install -r requirements.txt

# Run server
python run.py

# Access at http://localhost:5000
```

**Requirements:**
- Python 3.9+
- pip (package manager)
- Modern browser (Chrome, Firefox, Safari)

### Production Considerations (Future)

**If deploying online:**
- Use Gunicorn (WSGI server)
- Nginx (reverse proxy)
- Let's Encrypt (SSL certificates)
- Environment variables for config
- Logging to files
- Error tracking (Sentry)

**Not needed for MVP** (local only).

---

## Monitoring and Logging

### Logging Strategy

**Log Levels:**
- `DEBUG`: Detailed info for development
- `INFO`: Normal operations (API calls, etc.)
- `WARNING`: Degraded functionality (OneLook timeout)
- `ERROR`: Unexpected failures (file not found)

**What to Log:**
- API requests (endpoint, pattern/data, response time)
- OneLook API calls (success/failure)
- Errors with stack traces
- Performance metrics (slow queries >1s)

**Where to Log:**
- Development: Console output
- Production: Rotating log files

### Monitoring (Future)

**Metrics to track:**
- Request count per endpoint
- Response time percentiles (p50, p95, p99)
- Error rates
- OneLook API availability
- Word list load times

**Tools (if needed):**
- Prometheus (metrics collection)
- Grafana (dashboards)

**Not needed for MVP.**

---

## Development Workflow

### Git Workflow

**Branch Strategy:**
```
main
  ├── feature/pattern-matcher
  ├── feature/numbering-validator
  └── feature/convention-helper
```

**Commit Convention:**
```
feat: add pattern matcher with OneLook integration
fix: correct numbering algorithm for edge case
refactor: extract scoring logic to separate module
test: add unit tests for convention rules
docs: update README with setup instructions
```

### Development Process

**For each feature:**
1. Create feature branch
2. Write failing tests (TDD)
3. Implement feature
4. Run tests (pytest)
5. Manual browser testing
6. Commit with clear message
7. Merge to main

### Code Review Checklist

- [ ] All tests pass
- [ ] Code follows patterns in CLAUDE.md
- [ ] No anti-patterns present
- [ ] Error handling comprehensive
- [ ] Documentation updated
- [ ] Mobile responsive (for frontend)

---

## Dependencies

### Python Dependencies

```txt
flask==3.0.0          # Web framework
requests==2.31.0      # HTTP client for OneLook
pytest==7.4.0         # Testing framework
pytest-cov==4.1.0     # Coverage reporting
pylint==3.0.0         # Code linting
```

**Why minimal:**
- Fewer dependencies = fewer security issues
- Simpler deployment
- Faster installation

### Frontend Dependencies

**None.** Pure vanilla JavaScript.

**Why no dependencies:**
- No build process needed
- Faster page loads
- Simpler maintenance

---

## Maintenance Plan

### Regular Tasks

**Weekly:**
- Review error logs
- Check OneLook API changes
- Update word lists (if needed)

**Monthly:**
- Dependency updates (security patches)
- Review and refine word list scoring
- User feedback incorporation

**Quarterly:**
- Full code review
- Performance optimization
- Consider Phase 2 features

---

## Future Enhancements (Phase 2)

### Feature Roadmap

**Priority 1 (High Value):**
- Word list management UI (add/edit/delete)
- Search history (recent patterns)
- Grid visualization (show numbering on grid)

**Priority 2 (Nice to Have):**
- Crosshare JSON import/export
- Dark mode
- Keyboard shortcuts
- Offline mode (service worker)

**Priority 3 (Advanced):**
- Multi-user (deploy online)
- Collaboration features
- Clue database integration
- Auto-generate grids

### Technical Debt

**Current shortcuts:**
- No database (files only)
- No authentication
- Basic error handling
- Manual E2E testing

**When to address:**
- Database: When search history/preferences needed
- Auth: When deploying online
- Enhanced errors: Based on user feedback
- E2E automation: If maintaining long-term

---

## Appendix: Decision Log

### Why Flask over FastAPI?
- **Decision:** Use Flask
- **Reason:** Simpler for synchronous I/O-bound work
- **Trade-off:** FastAPI has better async, but not needed here
- **Date:** 2024-11-18

### Why Vanilla JS over React?
- **Decision:** Use Vanilla JavaScript
- **Reason:** Only 3 components, React overhead unjustified
- **Trade-off:** More manual DOM manipulation
- **Date:** 2024-11-18

### Why Files over SQLite for MVP?
- **Decision:** File-based word lists
- **Reason:** Simpler, editable, sufficient for MVP
- **Trade-off:** Migrate to SQLite in Phase 2 for features
- **Date:** 2024-11-18

### Why Web App over CLI?
- **Decision:** Local web application
- **Reason:** Non-technical user (partner) requirement
- **Trade-off:** 50% more dev time (10h vs 6h)
- **Benefit:** Infinite reusability
- **Date:** 2024-11-18
