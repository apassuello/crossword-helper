# Create Test Command

Scaffold a new test file with boilerplate code.

## Usage

```bash
claude create-test <test_type> <name>
```

## Arguments

- `<test_type>` (required): Type of test (`unit` or `integration`)
- `<name>` (required): Test module name (e.g., `pattern_matcher`, `api`)

## Steps

1. Determine test file path:
   - Unit test: `tests/unit/test_<name>.py`
   - Integration test: `tests/integration/test_<name>.py`

2. Check if file exists:
   - If exists: Ask user if they want to overwrite
   - If not: Proceed to create

3. Generate test scaffold based on type:

   **For unit tests:**
   ```python
   """
   Unit tests for <name>.
   """
   import pytest
   from backend.core.<name> import <ClassName>

   @pytest.fixture
   def <name>_instance():
       """Fixture for <ClassName> instance."""
       return <ClassName>()

   class Test<ClassName>:
       """Test suite for <ClassName>."""

       def test_basic_functionality(self, <name>_instance):
           """Test basic functionality."""
           # Arrange

           # Act

           # Assert
           assert True  # Replace with actual test

       def test_error_handling(self, <name>_instance):
           """Test error handling."""
           with pytest.raises(ValueError):
               # Code that should raise error
               pass
   ```

   **For integration tests:**
   ```python
   """
   Integration tests for <name> API.
   """
   import pytest
   import json

   class Test<Name>API:
       """Test suite for <name> API endpoints."""

       def test_endpoint_success(self, client):
           """Test successful API call."""
           # Arrange
           payload = {}

           # Act
           response = client.post('/api/<name>',
                                 data=json.dumps(payload),
                                 content_type='application/json')

           # Assert
           assert response.status_code == 200
           data = response.get_json()
           assert 'results' in data

       def test_endpoint_validation(self, client):
           """Test input validation."""
           # Arrange
           payload = {}  # Invalid payload

           # Act
           response = client.post('/api/<name>',
                                 data=json.dumps(payload),
                                 content_type='application/json')

           # Assert
           assert response.status_code == 400
           data = response.get_json()
           assert 'error' in data
   ```

4. Write file to appropriate location

5. Display next steps:
   - File location
   - How to run the test
   - Suggest filling in test cases

## Examples

```bash
# Create unit test for pattern matcher
claude create-test unit pattern_matcher

# Create integration test for API routes
claude create-test integration routes
```

## Example Output

```
Creating unit test for pattern_matcher...

✓ Created: tests/unit/test_pattern_matcher.py

Test scaffold includes:
  - Fixture for PatternMatcher instance
  - Test class: TestPatternMatcher
  - Sample test methods (replace with actual tests)

Next steps:
  1. Open: tests/unit/test_pattern_matcher.py
  2. Replace placeholder assertions with real tests
  3. Add more test methods as needed
  4. Run: pytest tests/unit/test_pattern_matcher.py -v

Test template follows AAA pattern:
  - Arrange: Set up test data
  - Act: Execute code under test
  - Assert: Verify expected behavior
```

## Test Templates

### Unit Test Template (AAA Pattern)

```python
def test_method_name(self, fixture):
    """Test description."""
    # Arrange - Set up test data
    input_data = "test"
    expected_output = "TEST"

    # Act - Execute code under test
    actual_output = fixture.method(input_data)

    # Assert - Verify expected behavior
    assert actual_output == expected_output
```

### Integration Test Template

```python
def test_endpoint_name(self, client):
    """Test API endpoint."""
    # Arrange
    payload = {"field": "value"}

    # Act
    response = client.post('/api/endpoint',
                          data=json.dumps(payload),
                          content_type='application/json')

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data['field'] == expected_value
```

## Best Practices

Generated tests follow these patterns:

1. **AAA Pattern**: Arrange, Act, Assert
2. **One assertion per test**: Focus on single behavior
3. **Descriptive names**: `test_pattern_search_with_wildcards`
4. **Fixtures**: Reusable test setup
5. **Error cases**: Test both success and failure paths

## Error Handling

- Invalid test type: "Test type must be 'unit' or 'integration'"
- File exists: "File already exists. Overwrite? (y/n)"
- Invalid name: "Name must be valid Python identifier"
- Directory not found: "Tests directory not found. Run from project root"
