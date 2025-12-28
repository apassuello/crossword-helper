# CLI Integration Quick Reference

## Backend Usage Guide

### Setup
```python
from backend.core.cli_adapter import CLIAdapter
from pathlib import Path

# Initialize adapter (auto-finds CLI)
adapter = CLIAdapter()

# Get project root for paths
project_root = Path(__file__).parent.parent
```

### Pattern Search
```python
# Search for words matching pattern
results = adapter.pattern(
    pattern="?R?SS",  # Use ? for wildcards
    wordlist_paths=[
        str(project_root / "data/wordlists/core/standard.txt"),
        str(project_root / "data/wordlists/comprehensive.txt")
    ],
    max_results=20,
    algorithm="trie"  # or "regex"
)

# Results structure:
# {
#   "results": [
#     {"word": "CROSS", "score": 65, "source": "standard", ...}
#   ],
#   "meta": {"total_found": 5, "pattern": "?R?SS", ...}
# }
```

### Text Normalization
```python
# Normalize according to crossword conventions
result = adapter.normalize("Tina Fey")

# Result structure:
# {
#   "original": "Tina Fey",
#   "normalized": "TINAFEY",
#   "rule": {"type": "two_word_names", ...},
#   "alternatives": []
# }

# Use cached version for better performance
from backend.core.cli_adapter import normalize_cached
result = normalize_cached("self-aware")  # Cached after first call
```

### Grid Numbering
```python
# Auto-number a grid
grid_data = {
    "size": 15,
    "grid": [["", "#", ...], ...]  # 15x15 array
}

result = adapter.number(
    grid_data=grid_data,
    allow_nonstandard=False  # Set True for non-11/15/21 grids
)

# Result structure:
# {
#   "numbering": {"(0,0)": 1, "(0,3)": 2, ...},
#   "grid_info": {"size": [15, 15], "word_count": 76, ...}
# }
```

### Grid Autofill
```python
# Fill a crossword grid
grid_data = {
    "size": 15,
    "grid": [...]  # Include black squares (#) and any preset letters
}

result = adapter.fill(
    grid_data=grid_data,
    wordlist_paths=[
        str(project_root / "data/wordlists/comprehensive.txt")
    ],
    timeout_seconds=300,  # 5 minutes max
    min_score=30,         # Quality threshold (1-100)
    algorithm="hybrid"    # Best quality: "hybrid", fastest: "trie"
)

# Result structure:
# {
#   "grid": [["A", "B", "C", ...], ...],  # Filled grid
#   "size": 15,
#   "black_squares": [...]
# }
```

## Important Path Notes

### ⚠️ Always Use Absolute Paths
The CLI runs from `/cli` directory, so relative paths won't work correctly.

```python
# ❌ BAD - Relative path
adapter.pattern("?AT", wordlist_paths=["data/wordlists/standard.txt"])

# ✅ GOOD - Absolute path
from pathlib import Path
wordlist = Path.cwd() / "data" / "wordlists" / "standard.txt"
adapter.pattern("?AT", wordlist_paths=[str(wordlist)])
```

### Wordlist Locations
```
data/wordlists/
├── core/
│   ├── standard.txt        # Basic words (48 words)
│   ├── common_3_letter.txt # Common 3-letter fills
│   └── crosswordese.txt    # Classic crossword words
├── comprehensive.txt        # Full dictionary
├── comprehensive_filtered.txt # Cleaned version
├── top_50k.txt             # Most common 50k words
└── external/               # Third-party lists
```

## Algorithm Selection

| Algorithm | Speed | Quality | Use Case |
|-----------|-------|---------|----------|
| `regex` | Slow | Good | Small grids, simple patterns |
| `trie` | Fast | Good | Standard CSP solving |
| `beam` | Medium | Better | Quality over speed |
| `repair` | Medium | Better | Fixing partial fills |
| `hybrid` | Slow | Best | Production puzzles |

**Notes**:
- `hybrid` requires timeout ≥ 30 seconds
- `trie` is best default for most cases
- Use `regex` only for testing (slow on large wordlists)

## Error Handling

```python
from subprocess import TimeoutExpired, CalledProcessError

try:
    result = adapter.fill(grid_data, wordlists, timeout_seconds=60)
except TimeoutExpired:
    # Fill took too long
    return {"error": "Autofill timeout", "suggestion": "Try simpler pattern"}
except CalledProcessError as e:
    # CLI command failed
    return {"error": f"CLI error: {e.stderr}"}
except ValueError as e:
    # Invalid input or JSON parsing error
    return {"error": str(e)}
```

## Performance Tips

1. **Cache normalize calls** - Use `normalize_cached()` for repeated normalizations
2. **Reuse adapter instance** - Create once and reuse (use `get_adapter()`)
3. **Use appropriate timeouts** - Don't set unnecessarily long timeouts
4. **Choose right algorithm** - `trie` for speed, `hybrid` for quality
5. **Preprocess wordlists** - Use `build-cache` command for large lists

## Testing the Integration

```bash
# Quick health check
python -c "from backend.core.cli_adapter import get_adapter; print('CLI available:', get_adapter().health_check())"

# Test pattern search
python -c "
from backend.core.cli_adapter import get_adapter
from pathlib import Path
adapter = get_adapter()
result = adapter.pattern('T?ST', [str(Path.cwd() / 'data/wordlists/core/standard.txt')])
print(f'Found {len(result['results'])} matches')
"

# Test full pipeline
python backend/test_cli_integration.py
```

## Common Issues

### Issue: "CLI executable not found"
**Solution**: Ensure `/cli/cli/crossword` exists and is executable
```bash
chmod +x cli/cli/crossword
```

### Issue: "No matches found" for pattern
**Solution**: Check wordlist path is absolute and file exists
```python
wordlist_path = Path(wordlist_path).absolute()
assert wordlist_path.exists(), f"Wordlist not found: {wordlist_path}"
```

### Issue: Progress messages in output
**Solution**: CLI adapter already filters stderr, but check JSON parsing
```python
# The adapter handles this, but if calling directly:
result = subprocess.run(cmd, capture_output=True, text=True)
json_output = result.stdout  # Ignore result.stderr
```

### Issue: Timeout on small grids
**Solution**: Use `trie` algorithm instead of `hybrid` for quick fills
```python
# For testing or small grids:
adapter.fill(grid, wordlists, algorithm="trie", timeout_seconds=10)