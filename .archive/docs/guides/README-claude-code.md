# Crossword Helper

Local web application for crossword puzzle construction assistance.

## Features

**Pattern Matcher**
- Find words matching crossword patterns (e.g., `?I?A`)
- Searches OneLook API + local word lists
- Scores results by crossword-ability

**Numbering Validator**
- Auto-number grids using standard rules
- Validate user numbering
- Visual grid display

**Convention Helper**
- Normalize multi-word entries
- Explain rules with examples
- Common cases handled automatically

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start server (auto-opens browser)
python run.py

# Or use Claude Code commands
claude setup           # Initial setup
claude test-all        # Run tests
```

## Usage

1. **Start the server**: `python run.py`
2. **Open browser**: http://localhost:5000 (auto-opens)
3. **Use the tools**:
   - Pattern Matcher: Enter `?I?A` style patterns
   - Numbering Validator: Upload grid JSON or paste
   - Convention Helper: Enter multi-word phrases

## Development

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=backend --cov-report=html

# Lint code
pylint backend/

# Format code
black backend/
```

## Project Structure

```
backend/
  core/           # Business logic (pure functions)
  api/            # Flask routes (HTTP wrappers)
  data/           # External integrations

frontend/
  static/         # CSS, JS, images
  templates/      # HTML

tests/
  unit/           # Fast, isolated tests
  integration/    # API endpoint tests
  fixtures/       # Test data

data/
  wordlists/      # Word list files
```

## API Endpoints

**POST /api/pattern**
```json
{"pattern": "?I?A"}
→ {"results": [{"word": "VISA", "score": 85}]}
```

**POST /api/number**
```json
{"grid": [["R","A",...], ...]}
→ {"numbering": {"(0,0)": 1}, "validation": {"is_valid": true}}
```

**POST /api/normalize**
```json
{"text": "Tina Fey"}
→ {"normalized": "TINAFEY", "rule": {...}}
```

## Word Lists

Word lists live in `data/wordlists/`:

- `standard.txt` - Common crossword fill
- `personal.txt` - Your custom words

Format: One word per line, uppercase, `#` for comments.

## Grid JSON Format

```json
{
  "size": 15,
  "grid": [
    ["R", "A", "S", "#", "Y", "O", "G", "A"],
    ["#", "#", "#", "B", "#", "#", "#", "#"]
  ]
}
```

Grid cells: `"A-Z"` = letter, `"#"` = black, `"."` = empty

## Integration with Crosshare

This tool complements Crosshare.org:

1. Brainstorm theme/words (Claude.ai)
2. **Pattern matching** (this tool)
3. Grid editing (Crosshare)
4. **Validation** (this tool)
5. Clue writing (Claude.ai)
6. Export (Crosshare)

## Testing

```bash
# All tests
pytest tests/

# Specific test
pytest tests/unit/test_pattern_matcher.py -v

# With output
pytest tests/ -s

# Coverage report
pytest tests/ --cov=backend --cov-report=html
open htmlcov/index.html
```

## Troubleshooting

**Port already in use:**
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9
```

**Import errors:**
```bash
# Ensure dependencies installed
pip install -r requirements.txt

# Check Python version (needs 3.9+)
python --version
```

**OneLook API timeout:**
- Check internet connection
- Tool falls back to local word lists automatically

## License

MIT
