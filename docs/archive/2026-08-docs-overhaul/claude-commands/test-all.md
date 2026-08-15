# Test All Command

Run full test suite with coverage report.

## Usage

```bash
claude test-all
```

## Arguments

None (runs all tests)

## Steps

1. Run pytest with coverage:
   ```bash
   pytest tests/ --cov=backend --cov-report=term --cov-report=html -v
   ```

2. Display summary:
   - Total tests run
   - Pass/fail counts
   - Coverage percentages by module
   - Link to HTML coverage report

3. If any failures:
   - Show which tests failed
   - Display failure messages
   - Suggest running specific failed tests with `-vv` for details

## Example Output

```
Running full test suite...

========================= test session starts ==========================
platform linux -- Python 3.9.7, pytest-7.4.0, pluggy-1.3.0

tests/unit/test_pattern_matcher.py::test_simple_pattern PASSED    [ 5%]
tests/unit/test_pattern_matcher.py::test_scoring PASSED           [10%]
tests/unit/test_numbering.py::test_3x3_grid PASSED                [15%]
...

========================== 48 passed in 2.34s ==========================

Coverage Summary:
  backend/core/pattern_matcher.py    94%
  backend/core/numbering.py          92%
  backend/core/conventions.py        89%
  backend/api/routes.py              85%
  backend/data/onelook_client.py     78%
  
  TOTAL                              87%

✓ Coverage target met (>85%)

HTML coverage report: htmlcov/index.html
```

## Error Handling

- Test failures: Show which tests failed, suggest fixes
- Coverage below target: List modules needing more tests
- Import errors: Show missing dependencies, suggest `pip install -r requirements.txt`
