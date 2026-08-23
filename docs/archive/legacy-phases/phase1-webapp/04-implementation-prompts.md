# Claude Code Implementation Prompt - Crossword Helper

## How to Use This Prompt

**Important:** This is a COMPLETE specification. Read ALL attached documents before starting:
1. `01-architecture-document.md` - System design and technology choices
2. `02-api-specification.md` - Complete API contracts
3. `03-implementation-specification.md` - Detailed component requirements

**Implementation Approach:**
- Build incrementally in 4 phases
- Test after each phase
- Don't proceed to next phase until tests pass
- Ask for approval between phases if uncertain

---

## PROJECT OVERVIEW

You are implementing a **local web application** for crossword puzzle construction assistance. The system helps solve three specific pain points:

1. **Pattern Matching** - Find words matching patterns like `?I?A` (4-letter words with I as 2nd letter, A as 4th)
2. **Grid Numbering** - Automatically number crossword grids using standard rules, or validate user's numbering
3. **Convention Handling** - Normalize multi-word entries according to crossword conventions (e.g., "Tina Fey" → "TINAFEY")

**Technology Stack:**
- Backend: Flask 3.0+ (Python 3.9+)
- Frontend: Vanilla HTML/CSS/JavaScript (no frameworks)
- Data: File-based word lists
- Testing: pytest

**Target Deployment:** Local development server (localhost:5000)

**Users:** Technical user (expert developer) + non-technical user (partner)

---

## PHASE 1: PROJECT SETUP & BACKEND CORE (2-3 hours)

### Step 1.1: Initialize Project Structure

Create the following directory structure:

```
crossword-helper/
├── backend/
│   ├── __init__.py
│   ├── app.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── pattern_matcher.py
│   │   ├── numbering.py
│   │   ├── conventions.py
│   │   └── scoring.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── validators.py
│   │   └── errors.py
│   └── data/
│       ├── __init__.py
│       ├── onelook_client.py
│       └── wordlist_manager.py
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   │   └── main.css
│   │   ├── js/
│   │   │   ├── app.js
│   │   │   ├── pattern.js
│   │   │   ├── numbering.js
│   │   │   └── conventions.js
│   │   └── img/
│   └── templates/
│       └── index.html
├── data/
│   └── wordlists/
│       ├── standard.txt
│       └── personal.txt
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   └── __init__.py
│   └── integration/
│       └── __init__.py
├── .claude/
│   └── CLAUDE.md
├── run.py
├── requirements.txt
├── README.md
└── .gitignore
```

### Step 1.2: Create Configuration Files

**`requirements.txt`:**
```
flask==3.0.0
flask-cors==4.0.0
requests==2.31.0
pytest==7.4.0
pytest-cov==4.1.0
```

**`.gitignore`:**
```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.pytest_cache/
.coverage
htmlcov/
.DS_Store
```

**`run.py`:**
```python
"""Application entry point."""
from backend.app import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True
    )
```

### Step 1.3: Implement Core Services

**CRITICAL:** Follow the exact interfaces and algorithms specified in `03-implementation-specification.md`.

Implement in this order:

1. **`backend/core/scoring.py`** - Word scoring algorithms
2. **`backend/data/wordlist_manager.py`** - Word list loading
3. **`backend/data/onelook_client.py`** - OneLook API client
4. **`backend/core/pattern_matcher.py`** - Pattern matching logic
5. **`backend/core/numbering.py`** - Numbering validator
6. **`backend/core/conventions.py`** - Convention helper

**For each component:**
- Implement exact class interface from specification
- Follow the specified algorithms (especially numbering algorithm)
- Include comprehensive docstrings
- Add type hints (from typing module)

### Step 1.4: Create Sample Word Lists

**`data/wordlists/standard.txt`:**
```
# Standard crossword fill words
# One word per line, uppercase

AREA
VISA
PITA
DIVA
YOGA
GREEN
BANANA
MEOW
CAT
DOG
TONE
AREA
EARL
RIOT
OATS
NEAT
STAR
```

**`data/wordlists/personal.txt`:**
```
# Personal word list
# Add your custom words here

RASPBERRIES
EVERYTHING
CANYONING
KIWI
```

### Step 1.5: Write Unit Tests

**`tests/conftest.py`:**
```python
"""Pytest configuration and fixtures."""
import pytest
from backend.app import create_app

@pytest.fixture
def app():
    """Create test Flask application."""
    app = create_app(testing=True)
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def sample_grid_3x3():
    """Sample 3×3 grid for testing."""
    return [
        ['R', 'A', 'T'],
        ['#', 'T', '#'],
        ['C', 'A', 'T']
    ]

@pytest.fixture
def sample_grid_9x9():
    """Sample 9×9 grid for testing."""
    # Create a simple 9×9 grid
    return [
        ['R','A','S','P','#','Y','O','G','A'],
        ['#','T','#','#','B','#','#','#','L'],
        ['C','A','T','#','#','#','D','O','G'],
        ['#','#','#','M','E','O','W','#','#'],
        ['#','B','#','#','#','#','#','#','#'],
        ['#','A','#','S','T','A','R','#','#'],
        ['#','N','#','#','#','#','#','E','#'],
        ['#','A','#','#','#','#','#','A','#'],
        ['#','#','#','#','#','#','#','T','#']
    ]
```

**Create tests in `tests/unit/`:**

1. `test_pattern_matcher.py` - Test pattern matching, scoring
2. `test_numbering.py` - Test auto-numbering, validation
3. `test_conventions.py` - Test normalization rules
4. `test_wordlist_manager.py` - Test file loading
5. `test_onelook_client.py` - Test API client (with mocks)

**Reference the test examples in `03-implementation-specification.md` Section 5.**

### Phase 1 Success Criteria

Run tests:
```bash
pytest tests/unit/ -v
```

**All unit tests must pass before proceeding to Phase 2.**

---

## PHASE 2: API LAYER (1-2 hours)

### Step 2.1: Implement Flask App Factory

**`backend/app.py`:**
```python
"""Flask application factory."""
from flask import Flask, send_from_directory
from flask_cors import CORS
from backend.api.routes import api
import os

def create_app(testing=False):
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    # Configuration
    app.config['TESTING'] = testing
    
    # CORS (allow localhost)
    CORS(app, origins=['http://localhost:5000', 'http://127.0.0.1:5000'])
    
    # Register API blueprint
    app.register_blueprint(api, url_prefix='/api')
    
    # Serve frontend
    @app.route('/')
    def index():
        return send_from_directory('../frontend/templates', 'index.html')
    
    @app.route('/static/<path:path>')
    def serve_static(path):
        return send_from_directory('../frontend/static', path)
    
    return app
```

### Step 2.2: Implement API Routes

**`backend/api/errors.py`:**
```python
"""Error handling utilities."""
from flask import jsonify

def handle_error(code: str, message: str, status: int, details: dict = None):
    """
    Format error response consistently.
    
    Args:
        code: Error code (e.g., 'INVALID_PATTERN')
        message: Human-readable message
        status: HTTP status code
        details: Optional additional context
    
    Returns:
        Flask response tuple (json, status)
    """
    response = {
        'error': {
            'code': code,
            'message': message
        }
    }
    
    if details:
        response['error']['details'] = details
    
    return jsonify(response), status
```

**`backend/api/validators.py`:**
```python
"""Request validation functions."""

def validate_pattern_request(data: dict) -> dict:
    """Validate pattern search request."""
    if not data:
        raise ValueError("Request body is required")
    
    if 'pattern' not in data:
        raise ValueError("Field 'pattern' is required")
    
    if not isinstance(data['pattern'], str):
        raise ValueError("Field 'pattern' must be string")
    
    # Add remaining validation from specification
    
    return data

def validate_grid_request(data: dict) -> dict:
    """Validate grid request."""
    # Implement per specification
    pass

def validate_normalize_request(data: dict) -> dict:
    """Validate normalize request."""
    # Implement per specification
    pass
```

**`backend/api/routes.py`:**

Implement all three endpoints following the exact contracts in `02-api-specification.md`:

1. `POST /api/pattern` - Pattern search
2. `POST /api/number` - Numbering validation
3. `POST /api/normalize` - Convention normalization

**CRITICAL:** Keep routes thin - just validation, delegation, and formatting. No business logic.

### Step 2.3: Write Integration Tests

**Create tests in `tests/integration/`:**

1. `test_api_pattern.py` - Test pattern endpoint
2. `test_api_numbering.py` - Test numbering endpoint
3. `test_api_conventions.py` - Test normalize endpoint

**Reference test examples in `03-implementation-specification.md` Section 5.**

### Phase 2 Success Criteria

Run tests:
```bash
pytest tests/ -v
```

**All tests (unit + integration) must pass.**

Test manually with curl:
```bash
# Start server
python run.py

# Test pattern endpoint
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{"pattern": "?I?A"}' | jq
```

---

## PHASE 3: FRONTEND (2-3 hours)

### Step 3.1: Create HTML Structure

**`frontend/templates/index.html`:**

Implement the complete HTML structure from `03-implementation-specification.md` Section 4.1.

**Requirements:**
- Semantic HTML5
- Accessibility (ARIA labels, proper heading hierarchy)
- Three tool sections (Pattern Matcher, Numbering Validator, Convention Helper)
- Proper form elements with labels

### Step 3.2: Implement CSS Styling

**`frontend/static/css/main.css`:**

Implement mobile-first responsive design:

1. **Base mobile styles** (default)
2. **Desktop styles** (@media min-width: 768px)
3. **Loading states** (.loading, .spinner)
4. **Error states** (.error)
5. **Success states** (.success)

**Reference styling requirements in `03-implementation-specification.md` Section 4.2.**

**Design Principles:**
- Clean, minimal aesthetic (inspired by Crosshare)
- Good contrast for readability
- Clear visual hierarchy
- Responsive layout (mobile-first)

### Step 3.3: Implement JavaScript Components

**`frontend/static/js/app.js`:**
```javascript
/**
 * Main application initialization
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('Crossword Helper loaded');
    
    // Initialize components
    initPatternMatcher();
    initNumberingValidator();
    initConventionHelper();
});

/**
 * Show error message in container
 */
function showError(container, message) {
    container.innerHTML = `<div class="error">❌ ${message}</div>`;
}

/**
 * Show loading state in container
 */
function showLoading(container, message = 'Loading...') {
    container.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>${message}</p>
        </div>
    `;
}
```

**`frontend/static/js/pattern.js`:**

Implement pattern matcher component following the example in `03-implementation-specification.md` Section 4.3.

**Requirements:**
- Fetch API for HTTP requests
- Loading states (disable button, show spinner)
- Error handling (display user-friendly messages)
- Result rendering (table with word, score, quality, source)
- Clear button to reset
- Enter key support

**`frontend/static/js/numbering.js`:**

Implement numbering validator component (similar structure to pattern.js).

**`frontend/static/js/conventions.js`:**

Implement convention helper component (similar structure to pattern.js).

### Step 3.4: Test Frontend

**Manual Testing Checklist:**

1. **Pattern Matcher:**
   - [ ] Enter pattern `?I?A`, click Search
   - [ ] Results appear in table
   - [ ] Loading spinner shows during search
   - [ ] Error displayed for invalid pattern (e.g., `ABCD`)
   - [ ] Clear button resets input and results
   - [ ] Enter key triggers search

2. **Numbering Validator:**
   - [ ] Paste grid JSON, click Validate
   - [ ] Numbering displayed
   - [ ] Grid info shown
   - [ ] Errors displayed if present

3. **Convention Helper:**
   - [ ] Enter "Tina Fey", click Normalize
   - [ ] Shows "TINAFEY" with rule explanation
   - [ ] Examples displayed

4. **Mobile Responsive:**
   - [ ] Resize browser to 360px width
   - [ ] Layout adjusts properly
   - [ ] All buttons accessible
   - [ ] Text readable

5. **Error Handling:**
   - [ ] Stop server, try search → error displayed
   - [ ] Invalid JSON → error displayed
   - [ ] Network timeout → error displayed

### Phase 3 Success Criteria

**All three tools functional in browser:**
- Pattern matching works
- Numbering validation works
- Convention normalization works
- Mobile responsive
- Error handling clear

---

## PHASE 4: DOCUMENTATION & POLISH (1 hour)

### Step 4.1: Create README

**`README.md`:**
```markdown
# Crossword Helper

Local web application for crossword puzzle construction assistance.

## Features

- **Pattern Matcher**: Find words matching crossword patterns (e.g., `?I?A`)
- **Numbering Validator**: Auto-number grids or validate existing numbering
- **Convention Helper**: Normalize entries according to crossword conventions

## Quick Start

### Prerequisites

- Python 3.9+
- pip

### Installation

```bash
# Clone repository
git clone <repo-url>
cd crossword-helper

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Start server
python run.py

# Open browser to http://localhost:5000
```

## Usage

### Pattern Matcher

1. Enter a pattern using `?` for wildcards (e.g., `?I?A`)
2. Click "Search"
3. Results show matching words with scores

**Example Patterns:**
- `?I?A` - 4-letter word with I as 2nd letter, A as 4th
- `???E?` - 5-letter word with E as 4th letter
- `?A?P?E?R?E?` - 11-letter word with specific letters

### Numbering Validator

1. Paste grid JSON in textarea
2. Click "Validate"
3. View auto-numbering and validation results

**Grid JSON Format:**
```json
{
    "grid": [
        ["R", "A", "T"],
        ["#", "T", "#"],
        ["C", "A", "T"]
    ]
}
```

### Convention Helper

1. Enter phrase to normalize (e.g., "Tina Fey")
2. Click "Normalize"
3. View normalized form with rule explanation

## Development

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=backend --cov-report=html
```

### Project Structure

```
crossword-helper/
├── backend/        # Flask API
├── frontend/       # HTML/CSS/JS
├── data/          # Word lists
└── tests/         # Test suite
```

## Word Lists

Add custom words to `data/wordlists/personal.txt`:

```
# One word per line, uppercase
RASPBERRIES
EVERYTHING
```

## API Documentation

See API specification in `docs/api-spec.md`.

## License

MIT License
```

### Step 4.2: Create CLAUDE.md

**`.claude/CLAUDE.md`:**

Copy the exact content from the CLAUDE.md template in `03-implementation-specification.md`.

**This is critical** - CLAUDE.md defines project patterns and must be accurate.

### Step 4.3: Final Testing & Polish

1. **Run full test suite:**
```bash
pytest tests/ -v --cov=backend
```

2. **Check test coverage:**
```bash
# Should be >85%
```

3. **Manual browser testing:**
   - Test all three tools
   - Test error scenarios
   - Test mobile viewport
   - Check console for errors

4. **Code quality:**
```bash
# If you have pylint installed
pylint backend/

# Should score >8/10
```

5. **Fix any issues found**

### Phase 4 Success Criteria

- ✅ All tests pass (>85% coverage)
- ✅ README complete
- ✅ CLAUDE.md accurate
- ✅ No console errors
- ✅ Mobile responsive
- ✅ Non-technical user can use without help

---

## FINAL DELIVERABLES

After completing all 4 phases, you should have:

1. **Working web application** at http://localhost:5000
2. **Complete test suite** (unit + integration)
3. **Documentation** (README, API spec, CLAUDE.md)
4. **All three tools functional:**
   - Pattern Matcher
   - Numbering Validator
   - Convention Helper
5. **Mobile responsive design**
6. **Error handling** comprehensive

---

## IMPORTANT NOTES

### Code Quality Standards

**Follow these patterns:**

✅ **DO:**
- Keep routes thin (delegate to services)
- Use type hints
- Write comprehensive docstrings
- Handle errors gracefully
- Test thoroughly
- Follow DRY principle

❌ **DON'T:**
- Put business logic in routes
- Ignore errors (always handle)
- Skip tests
- Use global variables
- Hardcode values

### Testing Guidelines

**Test pyramid:**
- Most tests at unit level (fast, specific)
- Fewer integration tests (slower, broader)
- Manual testing for UI/UX

**Coverage targets:**
- Service layer (core/): >90%
- API layer: >80%
- Overall: >85%

### Performance Targets

- Pattern search: <1 second
- Numbering validation: <100ms
- Convention normalize: <50ms
- Page load: <500ms

### Browser Support

Test in:
- Chrome (latest)
- Firefox (latest)
- Safari (latest)

Viewport sizes:
- Mobile: 360px width
- Tablet: 768px width
- Desktop: 1200px width

---

## TROUBLESHOOTING

### Common Issues

**Issue: Import errors**
- Solution: Ensure `__init__.py` files in all packages
- Check Python path: `export PYTHONPATH="${PYTHONPATH}:$(pwd)"`

**Issue: CORS errors in browser**
- Solution: Check `flask-cors` is installed and configured
- Verify origins in `app.py`

**Issue: OneLook API timeout**
- Solution: This is expected behavior, app should fallback to local
- Check logs for warning message

**Issue: Tests failing**
- Solution: Read error messages carefully
- Check fixtures in `conftest.py`
- Ensure test data files exist

**Issue: Frontend not loading**
- Solution: Check Flask static file serving
- Verify paths in `app.py`
- Check browser console for 404 errors

---

## GETTING HELP

If you encounter issues:

1. **Check the specifications:**
   - Architecture document for design decisions
   - API specification for endpoint contracts
   - Implementation spec for detailed requirements

2. **Review error messages:**
   - Read the full error (don't just skim)
   - Check file paths and imports
   - Verify data formats

3. **Test incrementally:**
   - Don't wait until everything is built
   - Test each component as you build it
   - Run tests frequently

4. **Ask for clarification:**
   - If a requirement is unclear
   - If you're unsure which approach to take
   - Before making major architectural changes

---

## SUCCESS CHECKLIST

Before considering the project complete:

### Backend
- [ ] All service classes implemented with correct interfaces
- [ ] All API endpoints working per specification
- [ ] Unit tests pass (>85% coverage)
- [ ] Integration tests pass
- [ ] Error handling comprehensive
- [ ] OneLook API integration with fallback

### Frontend
- [ ] Three tools fully functional
- [ ] Mobile responsive design
- [ ] Loading states visible
- [ ] Error messages user-friendly
- [ ] No console errors
- [ ] Keyboard navigation works

### Documentation
- [ ] README explains setup clearly
- [ ] CLAUDE.md accurate and complete
- [ ] API specification matches implementation
- [ ] Comments in code where needed

### Quality
- [ ] All tests pass
- [ ] No linting errors (if using linter)
- [ ] Performance targets met
- [ ] Non-technical user can use without help

---

## START IMPLEMENTATION

**To begin:**

1. Read all three specification documents completely
2. Start with Phase 1 (setup + backend core)
3. Test after each component
4. Only proceed to next phase when tests pass
5. Ask for approval if uncertain about approach

Good luck! 🚀
