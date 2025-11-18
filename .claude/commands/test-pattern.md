# Test Pattern Command

Quick test for pattern matching functionality.

## Usage

```bash
claude test-pattern <pattern> [wordlists...]
```

## Arguments

- `<pattern>` (required): Pattern to test (e.g., `?I?A`, `????ING`)
- `[wordlists...]` (optional): Wordlists to search (default: `standard`)

## Steps

1. Validate pattern format:
   - Length: 3-20 characters
   - Characters: A-Z and ? only
   - Uppercase

2. Run pattern search:
   ```bash
   # Using curl to test API endpoint
   curl -X POST http://localhost:5000/api/pattern \
     -H "Content-Type: application/json" \
     -d '{"pattern": "<pattern>", "wordlists": ["<wordlists>"]}'
   ```

3. Display results:
   - Top 10 matching words
   - Score for each word
   - Source (onelook/local)
   - Total found count
   - Query time

4. If no server running:
   - Show error: "Development server not running"
   - Suggest: "Run `claude dev-server` first"

## Examples

```bash
# Test simple pattern
claude test-pattern ?I?A

# Test with multiple wordlists
claude test-pattern ????ING standard personal

# Test complex pattern
claude test-pattern ??X??
```

## Example Output

```
Testing pattern: ?I?A

Results (showing 10 of 127):
  1. VISA     (score: 78, source: onelook)
  2. PITA     (score: 75, source: local)
  3. DIVA     (score: 73, source: onelook)
  4. IDEA     (score: 70, source: local)
  5. SIVA     (score: 68, source: local)
  ...

Query time: 245ms
Sources searched: onelook, standard
```

## Error Handling

- Pattern too short: "Pattern must be at least 3 characters"
- Pattern too long: "Pattern must be at most 20 characters"
- Invalid characters: "Pattern can only contain A-Z and ?"
- Server not running: "Start dev server with `claude dev-server`"
- No results: "No matches found. Try broader pattern with more ?"
