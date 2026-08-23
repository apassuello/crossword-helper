# Setup Command

Initialize project structure and dependencies.

## Usage

```bash
claude setup
```

## Arguments

None

## Steps

1. Create directory structure:
   ```
   backend/
     core/, api/, data/
   frontend/
     static/css/, static/js/, static/img/, templates/
   data/
     wordlists/
   tests/
     unit/, integration/, fixtures/
   ```

2. Create initial files:
   - `backend/__init__.py`, `backend/core/__init__.py`, etc.
   - `requirements.txt` with dependencies:
     ```
     Flask==3.0.0
     Flask-CORS==4.0.0
     requests==2.31.0
     pytest==7.4.0
     pytest-cov==4.1.0
     pylint==3.0.0
     ```
   - `run.py` entry point
   - `.gitignore` for Python projects

3. Create sample word lists:
   - `data/wordlists/standard.txt` (common crossword fill)
   - `data/wordlists/personal.txt` (empty, for user to populate)

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Verify setup:
   - Check all directories created
   - Check dependencies installed
   - Run basic import tests

## Example Output

```
Setting up crossword-helper project...

✓ Created directory structure
✓ Created __init__.py files
✓ Created requirements.txt
✓ Created run.py entry point
✓ Created .gitignore
✓ Created sample word lists

Installing dependencies...
✓ Flask 3.0.0
✓ Flask-CORS 4.0.0
✓ requests 2.31.0
✓ pytest 7.4.0
✓ pytest-cov 4.1.0
✓ pylint 3.0.0

Verifying setup...
✓ All imports successful
✓ Flask app can be created
✓ Word lists accessible

Setup complete! Next steps:
1. Populate data/wordlists/personal.txt with your words
2. Start implementing backend/core/ modules
3. Run tests: pytest tests/
4. Start server: python run.py
```

## Error Handling

- Directory exists: Ask if should overwrite or skip
- Pip install fails: Show which package failed, suggest manual install
- Import errors: Show detailed error, suggest checking Python version (3.9+)
