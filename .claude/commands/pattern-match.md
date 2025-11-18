# Pattern Match Command

Quick pattern matching for crossword fill.

## Usage

```bash
claude pattern-match "?I?A"
```

## Arguments

- `$ARGUMENTS`: Pattern to search (e.g., `?I?A`, `????E?`)

## Steps

1. Parse pattern from `$ARGUMENTS`
2. Validate pattern (must contain at least one `?`)
3. Import PatternMatcher from backend.core.pattern_matcher
4. Create instance with default word lists (personal + standard)
5. Run search
6. Display top 20 results with scores
7. Highlight top recommendation (score > 80)

## Example Output

```
Searching for pattern: ?I?A

Top matches (from 127 results):

 1. VISA    (score: 85) ⭐ Recommended
 2. PITA    (score: 82)
 3. DIVA    (score: 78)
 4. VIDA    (score: 75)
 5. FILA    (score: 72)
...

Top pick: VISA (highest crossword-ability score)
```

## Error Handling

- Invalid pattern (no wildcards): Show error, suggest format
- No results found: Suggest broader pattern
- OneLook API timeout: Note fallback to local lists
