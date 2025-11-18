# Validate Grid Command

Quick grid numbering validation.

## Usage

```bash
claude validate-grid tests/fixtures/sample_grid.json
```

## Arguments

- `$ARGUMENTS`: Path to grid JSON file

## Steps

1. Load grid from JSON file path in `$ARGUMENTS`
2. Validate JSON structure (has `size` and `grid` fields)
3. Import NumberingValidator from backend.core.numbering
4. Run auto_number_grid to get correct numbering
5. If grid has user numbering, validate it
6. Display results:
   - Grid info (size, word count, black squares)
   - Correct numbering
   - Validation errors (if any)
7. Visualize grid with numbers overlaid

## Example Output

```
Validating grid: tests/fixtures/sample_grid.json

Grid Info:
  Size: 15×15
  Black squares: 38 (16.9%)
  Word count: 76 (within NYT limit of 78)
  Symmetry: ✓ Rotational

Numbering:
  1: (0,0)  - starts across + down
  2: (0,5)  - starts across
  3: (0,10) - starts across
  ...

Validation: ✓ All numbers correct

Visual grid:
  1R  A  S  P  2B  E  R
  3E  #  #  #  R  #  #
  R  #  #  #  R  #  #
  ...
```

## Error Handling

- File not found: Show clear error message
- Invalid JSON: Show parsing error with line number
- Malformed grid: List specific issues (not square, invalid characters)
- Numbering errors: Show expected vs actual for each cell
