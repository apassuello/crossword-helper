"""Unit tests for backend.api.validators."""

import pytest

from backend.api.validators import (
    validate_fill_request,
    validate_grid_request,
    validate_normalize_request,
    validate_pattern_request,
)


class TestValidatePatternRequest:
    """Tests for validate_pattern_request."""

    def test_valid_minimal(self):
        data = {"pattern": "C?T"}
        assert validate_pattern_request(data) is data

    def test_valid_with_all_optional_fields(self):
        data = {"pattern": "C?T", "wordlists": ["a.txt", "b.txt"], "max_results": 50}
        assert validate_pattern_request(data) is data

    def test_empty_data_raises(self):
        with pytest.raises(ValueError, match="Request body is required"):
            validate_pattern_request({})

    def test_none_data_raises(self):
        with pytest.raises(ValueError, match="Request body is required"):
            validate_pattern_request(None)

    def test_missing_pattern_raises(self):
        with pytest.raises(ValueError, match="'pattern' is required"):
            validate_pattern_request({"wordlists": ["a.txt"]})

    def test_pattern_wrong_type_raises(self):
        with pytest.raises(ValueError, match="'pattern' must be string"):
            validate_pattern_request({"pattern": 123})

    def test_wordlists_wrong_type_raises(self):
        with pytest.raises(ValueError, match="'wordlists' must be array"):
            validate_pattern_request({"pattern": "C?T", "wordlists": "a.txt"})

    def test_wordlists_non_string_element_raises(self):
        with pytest.raises(ValueError, match="'wordlists' must contain strings"):
            validate_pattern_request({"pattern": "C?T", "wordlists": ["a.txt", 42]})

    def test_max_results_wrong_type_raises(self):
        with pytest.raises(ValueError, match="'max_results' must be integer"):
            validate_pattern_request({"pattern": "C?T", "max_results": "ten"})

    def test_max_results_zero_raises(self):
        with pytest.raises(ValueError, match="'max_results' must be 1-100"):
            validate_pattern_request({"pattern": "C?T", "max_results": 0})

    def test_max_results_over_100_raises(self):
        with pytest.raises(ValueError, match="'max_results' must be 1-100"):
            validate_pattern_request({"pattern": "C?T", "max_results": 101})

    def test_max_results_boundary_1(self):
        assert validate_pattern_request({"pattern": "A", "max_results": 1})

    def test_max_results_boundary_100(self):
        assert validate_pattern_request({"pattern": "A", "max_results": 100})


class TestValidateGridRequest:
    """Tests for validate_grid_request."""

    def _grid(self, size=5):
        return [["" for _ in range(size)] for _ in range(size)]

    def test_valid_minimal(self):
        data = {"size": 5, "grid": self._grid()}
        assert validate_grid_request(data) is data

    def test_valid_with_numbering(self):
        data = {"size": 5, "grid": self._grid(), "numbering": {"1": [0, 0]}}
        assert validate_grid_request(data) is data

    def test_empty_data_raises(self):
        with pytest.raises(ValueError, match="Request body is required"):
            validate_grid_request({})

    def test_none_data_raises(self):
        with pytest.raises(ValueError, match="Request body is required"):
            validate_grid_request(None)

    def test_missing_size_raises(self):
        with pytest.raises(ValueError, match="'size' is required"):
            validate_grid_request({"grid": self._grid()})

    def test_size_wrong_type_raises(self):
        with pytest.raises(ValueError, match="'size' must be integer"):
            validate_grid_request({"size": "15", "grid": self._grid()})

    def test_size_below_min_raises(self):
        with pytest.raises(ValueError, match="'size' must be between 3 and 50"):
            validate_grid_request({"size": 2, "grid": self._grid()})

    def test_size_above_max_raises(self):
        with pytest.raises(ValueError, match="'size' must be between 3 and 50"):
            validate_grid_request({"size": 51, "grid": self._grid()})

    def test_size_boundary_3(self):
        data = {"size": 3, "grid": self._grid(3)}
        assert validate_grid_request(data) is data

    def test_size_boundary_50(self):
        data = {"size": 50, "grid": self._grid(2)}
        assert validate_grid_request(data) is data

    def test_missing_grid_raises(self):
        with pytest.raises(ValueError, match="'grid' is required"):
            validate_grid_request({"size": 5})

    def test_grid_wrong_type_raises(self):
        with pytest.raises(ValueError, match="'grid' must be array"):
            validate_grid_request({"size": 5, "grid": "not-a-grid"})

    def test_grid_not_2d_raises(self):
        with pytest.raises(ValueError, match="'grid' must be 2D array"):
            validate_grid_request({"size": 5, "grid": ["flat", "list"]})

    def test_numbering_wrong_type_raises(self):
        with pytest.raises(ValueError, match="'numbering' must be object"):
            validate_grid_request({"size": 5, "grid": self._grid(), "numbering": [1]})


class TestValidateNormalizeRequest:
    """Tests for validate_normalize_request."""

    def test_valid(self):
        data = {"text": "Hello World"}
        assert validate_normalize_request(data) is data

    def test_empty_data_raises(self):
        with pytest.raises(ValueError, match="Request body is required"):
            validate_normalize_request({})

    def test_none_data_raises(self):
        with pytest.raises(ValueError, match="Request body is required"):
            validate_normalize_request(None)

    def test_missing_text_raises(self):
        with pytest.raises(ValueError, match="'text' is required"):
            validate_normalize_request({"other": "x"})

    def test_text_wrong_type_raises(self):
        with pytest.raises(ValueError, match="'text' must be string"):
            validate_normalize_request({"text": 42})

    def test_text_empty_string_raises(self):
        with pytest.raises(ValueError, match="'text' cannot be empty"):
            validate_normalize_request({"text": ""})

    def test_text_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="'text' cannot be empty"):
            validate_normalize_request({"text": "   "})

    def test_text_over_100_chars_raises(self):
        with pytest.raises(ValueError, match="'text' must be at most 100 characters"):
            validate_normalize_request({"text": "A" * 101})

    def test_text_exactly_100_chars(self):
        data = {"text": "A" * 100}
        assert validate_normalize_request(data) is data


class TestValidateFillRequest:
    """Tests for validate_fill_request."""

    def _grid(self, size=5):
        return [["" for _ in range(size)] for _ in range(size)]

    def _valid(self, **overrides):
        base = {"grid": self._grid(), "size": 5}
        base.update(overrides)
        return base

    def test_valid_minimal(self):
        data = self._valid()
        assert validate_fill_request(data) is data

    def test_valid_with_all_optional(self):
        data = self._valid(
            wordlists=["a.txt"],
            timeout=60,
            min_score=30,
            theme_entries={"(0,0,across)": "CAT"},
        )
        assert validate_fill_request(data) is data

    def test_empty_data_raises(self):
        with pytest.raises(ValueError, match="Request body is required"):
            validate_fill_request({})

    def test_none_data_raises(self):
        with pytest.raises(ValueError, match="Request body is required"):
            validate_fill_request(None)

    def test_missing_grid_raises(self):
        with pytest.raises(ValueError, match="'grid' is required"):
            validate_fill_request({"size": 5})

    def test_grid_wrong_type_raises(self):
        with pytest.raises(ValueError, match="'grid' must be array"):
            validate_fill_request({"grid": "x", "size": 5})

    def test_grid_not_2d_raises(self):
        with pytest.raises(ValueError, match="'grid' must be 2D array"):
            validate_fill_request({"grid": ["flat"], "size": 5})

    def test_missing_size_raises(self):
        with pytest.raises(ValueError, match="'size' is required"):
            validate_fill_request({"grid": self._grid()})

    def test_size_wrong_type_raises(self):
        with pytest.raises(ValueError, match="'size' must be integer"):
            validate_fill_request(self._valid(size="5"))

    def test_size_below_min_raises(self):
        with pytest.raises(ValueError, match="'size' must be between 3 and 50"):
            validate_fill_request(self._valid(size=2))

    def test_size_above_max_raises(self):
        with pytest.raises(ValueError, match="'size' must be between 3 and 50"):
            validate_fill_request(self._valid(size=51))

    def test_wordlists_wrong_type_raises(self):
        with pytest.raises(ValueError, match="'wordlists' must be array"):
            validate_fill_request(self._valid(wordlists="a.txt"))

    def test_wordlists_non_string_element_raises(self):
        with pytest.raises(ValueError, match="'wordlists' must contain strings"):
            validate_fill_request(self._valid(wordlists=["a.txt", 99]))

    def test_wordlists_empty_raises(self):
        with pytest.raises(ValueError, match="must contain at least one word list"):
            validate_fill_request(self._valid(wordlists=[]))

    def test_timeout_wrong_type_raises(self):
        with pytest.raises(ValueError, match="'timeout' must be integer"):
            validate_fill_request(self._valid(timeout=60.5))

    def test_timeout_below_min_raises(self):
        with pytest.raises(ValueError, match="'timeout' must be between 10 and 1800"):
            validate_fill_request(self._valid(timeout=9))

    def test_timeout_above_max_raises(self):
        with pytest.raises(ValueError, match="'timeout' must be between 10 and 1800"):
            validate_fill_request(self._valid(timeout=1801))

    def test_timeout_boundary_10(self):
        assert validate_fill_request(self._valid(timeout=10))

    def test_timeout_boundary_1800(self):
        assert validate_fill_request(self._valid(timeout=1800))

    def test_min_score_wrong_type_raises(self):
        with pytest.raises(ValueError, match="'min_score' must be integer"):
            validate_fill_request(self._valid(min_score="high"))

    def test_min_score_below_min_raises(self):
        with pytest.raises(ValueError, match="'min_score' must be between 0 and 100"):
            validate_fill_request(self._valid(min_score=-1))

    def test_min_score_above_max_raises(self):
        with pytest.raises(ValueError, match="'min_score' must be between 0 and 100"):
            validate_fill_request(self._valid(min_score=101))

    def test_min_score_boundary_0(self):
        assert validate_fill_request(self._valid(min_score=0))

    def test_min_score_boundary_100(self):
        assert validate_fill_request(self._valid(min_score=100))

    def test_theme_entries_wrong_type_raises(self):
        with pytest.raises(ValueError, match="'theme_entries' must be object"):
            validate_fill_request(self._valid(theme_entries=["CAT"]))

    def test_theme_entries_non_string_value_raises(self):
        with pytest.raises(ValueError, match="Theme entry values must be strings"):
            validate_fill_request(self._valid(theme_entries={"(0,0,across)": 123}))

    def test_theme_entries_key_missing_parens_raises(self):
        with pytest.raises(ValueError, match="must be in format"):
            validate_fill_request(self._valid(theme_entries={"0,0,across": "CAT"}))

    def test_theme_entries_key_wrong_parts_raises(self):
        with pytest.raises(ValueError, match="must have format"):
            validate_fill_request(self._valid(theme_entries={"(0,0)": "CAT"}))

    def test_theme_entries_key_too_many_parts_raises(self):
        with pytest.raises(ValueError, match="must have format"):
            validate_fill_request(
                self._valid(theme_entries={"(0,0,across,extra)": "CAT"})
            )
