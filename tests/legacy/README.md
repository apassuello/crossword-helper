# Legacy Validation Scripts

This directory contains legacy validation scripts from the project's development phases. These are **not pytest tests** - they are standalone validation scripts that were used during development to verify specific features and refactorings.

## Files

- **test_integration_quick.py** - Quick integration test for Phase 3 refactoring
  - Validates basic component integration
  - Runs beam search filling with short timeout
  - Standalone script (not pytest)

- **test_phase3_refactoring.py** - Comprehensive Phase 3 architecture tests
  - Tests import structure and backward compatibility
  - Memory optimization validation
  - Real-life grid filling tests
  - Standalone validation script

- **test_phase4_5_fixes.py** - Phase 4.5 fixes validation
  - Validates stopping condition fixes
  - Tests chronological backtracking
  - Threshold-diverse value ordering tests
  - Standalone validation script

- **test_theme_entries.py** - Theme entries feature validation
  - Validates theme word handling
  - Standalone validation script

## Usage

These scripts can be run directly:

```bash
python tests/legacy/test_integration_quick.py
python tests/legacy/test_phase3_refactoring.py
# etc.
```

**Note**: These scripts are not run by `pytest` and are not part of the CI/CD pipeline. They are preserved for historical reference and manual validation if needed.

## Migration

The behaviors tested by these scripts are now covered by proper pytest tests in:
- `backend/tests/integration/` - Backend integration tests
- `backend/tests/unit/` - Backend unit tests
- `cli/tests/integration/` - CLI integration tests
- `cli/tests/unit/` - CLI unit tests
