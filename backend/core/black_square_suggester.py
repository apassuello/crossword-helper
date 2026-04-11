"""
Strategic black square placement suggester.

Analyzes problematic slots and suggests optimal black square placements
to resolve stuck autofill situations while maintaining grid quality.
"""

from typing import Dict, List


class BlackSquareSuggestion:
    """A single black square placement suggestion."""

    def __init__(
        self,
        position: int,
        row: int,
        col: int,
        score: int,
        reasoning: str,
        left_length: int,
        right_length: int,
        symmetric_position: Dict,
        new_word_count: int,
        constraint_reduction: int,
    ):
        self.position = position
        self.row = row
        self.col = col
        self.score = score
        self.reasoning = reasoning
        self.left_length = left_length
        self.right_length = right_length
        self.symmetric_position = symmetric_position
        self.new_word_count = new_word_count
        self.constraint_reduction = constraint_reduction

    def to_dict(self):
        return {
            "position": self.position,
            "row": self.row,
            "col": self.col,
            "score": self.score,
            "reasoning": self.reasoning,
            "left_length": self.left_length,
            "right_length": self.right_length,
            "symmetric_position": self.symmetric_position,
            "new_word_count": self.new_word_count,
            "constraint_reduction": self.constraint_reduction,
        }


class BlackSquareSuggester:
    """
    Suggests strategic black square placements ("cheater squares").

    Uses multi-factor scoring to find optimal positions that:
    - Split problematic slots into fillable lengths
    - Maintain rotational symmetry
    - Keep word count in acceptable range
    - Reduce constraint conflicts
    """

    def __init__(self, grid_size: int = 15):
        self.grid_size = grid_size
        # Standard word count ranges for common grid sizes
        self.word_count_ranges = {
            11: (60, 68),
            13: (66, 74),
            15: (72, 78),
            17: (80, 88),
            21: (90, 100),
        }

    def suggest_placements(self, grid: List[List], problematic_slot: Dict, max_suggestions: int = 3) -> List[Dict]:
        """
        Suggest black square placements for a problematic slot.

        Args:
            grid: Current grid state (list of lists)
            problematic_slot: Dict with 'row', 'col', 'direction', 'length', 'pattern'
            max_suggestions: Number of suggestions to return

        Returns:
            List of BlackSquareSuggestion dicts
        """
        slot_length = problematic_slot["length"]

        # Don't suggest for short slots
        if slot_length < 6:
            return []

        candidates = []

        # Try each position (skip first and last)
        for pos in range(1, slot_length - 1):
            score = self._score_position(grid, problematic_slot, pos)

            if score > 0:  # Only include viable positions
                suggestion = self._create_suggestion(grid, problematic_slot, pos, score)
                candidates.append(suggestion)

        # Sort by score descending
        candidates.sort(key=lambda x: x.score, reverse=True)

        # Return top N as dicts
        return [s.to_dict() for s in candidates[:max_suggestions]]

    def _score_position(self, grid: List[List], slot: Dict, position: int) -> int:
        """
        Score a candidate black square position.

        Scoring factors (0-1000 scale):
        - Length balance: Prefer even splits
        - Ideal range: 3-7 letter words
        - Symmetry: Must maintain rotational symmetry
        - Word count: Stay within standard range
        - Constraint reduction: How many conflicts resolved
        - Unchecked squares: Avoid creating them
        """
        score = 0

        # Calculate resulting lengths
        left_len = position
        right_len = slot["length"] - position - 1

        # ===================================
        # FACTOR 1: Length Balance (0-100)
        # ===================================
        balance = abs(left_len - right_len)
        balance_score = 100 - (balance * 10)
        score += max(0, balance_score)

        # ===================================
        # FACTOR 2: Ideal Length Range (0-100)
        # ===================================
        # Sweet spot: 3-7 letters
        if 3 <= left_len <= 7:
            score += 50
        if 3 <= right_len <= 7:
            score += 50

        # Strong penalty for 1-2 letter words
        if left_len < 3 or right_len < 3:
            score -= 500  # Almost always reject

        # ===================================
        # FACTOR 3: Symmetry (0-200)
        # ===================================
        symmetric_pos = self._get_symmetric_position(grid, slot, position)

        if self._can_place_symmetric_black(grid, symmetric_pos):
            score += 200  # Critical bonus
        else:
            score -= 1000  # Reject if breaks symmetry

        # ===================================
        # FACTOR 4: Word Count (0-100)
        # ===================================
        current_word_count = self._count_words(grid)
        new_word_count = current_word_count + 2  # Split adds 1 net word

        min_words, max_words = self.word_count_ranges.get(self.grid_size, (70, 80))  # Default

        if min_words <= new_word_count <= max_words:
            score += 100
        elif new_word_count > max_words:
            score -= (new_word_count - max_words) * 20
        elif new_word_count < min_words:
            score += (min_words - new_word_count) * 10

        # ===================================
        # FACTOR 5: Constraint Reduction (0-200)
        # ===================================
        constraint_reduction = self._estimate_constraint_reduction(slot, position)
        score += constraint_reduction * 40

        # ===================================
        # FACTOR 6: Unchecked Squares (0-50)
        # ===================================
        unchecked_penalty = self._count_unchecked_created(grid, slot, position)
        score -= unchecked_penalty * 25

        return max(0, score)

    def _get_symmetric_position(self, grid: List[List], slot: Dict, position: int) -> Dict:
        """Calculate the rotationally symmetric position."""
        row = slot["row"]
        col = slot["col"]
        direction = slot["direction"]

        if direction == "across":
            # Black square at (row, col + position)
            # Symmetric is at (grid_size-1-row, grid_size-1-(col+position))
            sym_row = self.grid_size - 1 - row
            sym_col = self.grid_size - 1 - (col + position)
        else:  # down
            # Black square at (row + position, col)
            # Symmetric is at (grid_size-1-(row+position), grid_size-1-col)
            sym_row = self.grid_size - 1 - (row + position)
            sym_col = self.grid_size - 1 - col

        return {"row": sym_row, "col": sym_col}

    def _can_place_symmetric_black(self, grid: List[List], sym_pos: Dict) -> bool:
        """Check if symmetric position can have a black square."""
        row = sym_pos["row"]
        col = sym_pos["col"]

        # Check bounds
        if not (0 <= row < self.grid_size and 0 <= col < self.grid_size):
            return False

        # Check if position is already black (that's okay)
        if self._is_black(grid, row, col):
            return True

        # Check if position is empty (can place black)
        cell = grid[row][col]
        if isinstance(cell, dict):
            return not cell.get("letter") and not cell.get("isThemeLocked", False)
        else:
            # String format
            return cell in ["", "."]

    def _is_black(self, grid: List[List], row: int, col: int) -> bool:
        """Check if cell is a black square."""
        cell = grid[row][col]
        if isinstance(cell, dict):
            return cell.get("isBlack", False)
        else:
            return cell == "#"

    def _count_words(self, grid: List[List]) -> int:
        """Count total words in grid (across + down)."""
        count = 0

        # Count across words
        for row in grid:
            in_word = False
            word_len = 0
            for cell in row:
                is_black = self._is_black_cell(cell)
                if not is_black:
                    if not in_word:
                        in_word = True
                        word_len = 1
                    else:
                        word_len += 1
                else:
                    if in_word and word_len >= 3:
                        count += 1
                    in_word = False
                    word_len = 0
            if in_word and word_len >= 3:
                count += 1

        # Count down words
        for col in range(len(grid[0])):
            in_word = False
            word_len = 0
            for row in range(len(grid)):
                is_black = self._is_black_cell(grid[row][col])
                if not is_black:
                    if not in_word:
                        in_word = True
                        word_len = 1
                    else:
                        word_len += 1
                else:
                    if in_word and word_len >= 3:
                        count += 1
                    in_word = False
                    word_len = 0
            if in_word and word_len >= 3:
                count += 1

        return count

    def _is_black_cell(self, cell) -> bool:
        """Helper to check if a cell is black (handles both formats)."""
        if isinstance(cell, dict):
            return cell.get("isBlack", False)
        else:
            return cell == "#"

    def _estimate_constraint_reduction(self, slot: Dict, position: int) -> int:
        """
        Estimate how much this placement reduces constraints.

        Higher values = more constraint relief.
        """
        # Simple heuristic: longer words have more constraints
        # Splitting reduces total constraint load
        original_length = slot["length"]
        left_len = position
        right_len = original_length - position - 1

        # Constraint count roughly proportional to length squared
        original_constraints = original_length**2
        new_constraints = (left_len**2) + (right_len**2)

        reduction = original_constraints - new_constraints

        # Normalize to 0-5 range
        return min(5, reduction // 20)

    def _count_unchecked_created(self, grid: List[List], slot: Dict, position: int) -> int:
        """
        Count unchecked squares that would be created.

        Unchecked = letter that appears in only one word (bad in crosswords).
        """
        # Simplified: assume black square at edge creates unchecked
        # More sophisticated version would check actual crossing words

        left_len = position
        right_len = slot["length"] - position - 1

        unchecked = 0

        # If either segment is very short, likely creates unchecked
        if left_len < 3:
            unchecked += 1
        if right_len < 3:
            unchecked += 1

        return unchecked

    def _create_suggestion(self, grid: List[List], slot: Dict, position: int, score: int) -> BlackSquareSuggestion:
        """Create a BlackSquareSuggestion object."""
        left_len = position
        right_len = slot["length"] - position - 1

        # Calculate actual grid position
        if slot["direction"] == "across":
            black_row = slot["row"]
            black_col = slot["col"] + position
        else:  # down
            black_row = slot["row"] + position
            black_col = slot["col"]

        # Get symmetric position
        sym_pos = self._get_symmetric_position(grid, slot, position)

        # Count words after placement
        new_word_count = self._count_words(grid) + 2

        # Estimate constraint reduction
        constraint_reduction = self._estimate_constraint_reduction(slot, position)

        # Generate reasoning
        reasoning = self._generate_reasoning(left_len, right_len, score, new_word_count, constraint_reduction)

        return BlackSquareSuggestion(
            position=position,
            row=black_row,
            col=black_col,
            score=score,
            reasoning=reasoning,
            left_length=left_len,
            right_length=right_len,
            symmetric_position=sym_pos,
            new_word_count=new_word_count,
            constraint_reduction=constraint_reduction,
        )

    def _generate_reasoning(
        self,
        left_len: int,
        right_len: int,
        score: int,
        new_word_count: int,
        constraint_reduction: int,
    ) -> str:
        """Generate human-readable reasoning."""
        reasons = []

        # Balance
        if abs(left_len - right_len) <= 1:
            reasons.append(f"Balanced split ({left_len}+{right_len} letters)")
        else:
            reasons.append(f"Split into {left_len}+{right_len} letters")

        # Ideal range
        if 3 <= left_len <= 7 and 3 <= right_len <= 7:
            reasons.append("Both lengths in sweet spot (3-7)")
        elif 3 <= left_len <= 7 or 3 <= right_len <= 7:
            reasons.append("One length in sweet spot")

        # Word count
        min_words, max_words = self.word_count_ranges.get(self.grid_size, (70, 80))
        if min_words <= new_word_count <= max_words:
            reasons.append(f"Word count {new_word_count} (within range)")
        elif new_word_count > max_words:
            reasons.append(f"⚠️ Word count {new_word_count} (over {max_words})")

        # Constraint reduction
        if constraint_reduction >= 3:
            reasons.append(f"High constraint reduction ({constraint_reduction})")
        elif constraint_reduction > 0:
            reasons.append(f"Some constraint reduction ({constraint_reduction})")

        # Symmetry (always maintained if suggestion exists)
        reasons.append("Maintains symmetry")

        return ", ".join(reasons)


def validate_grid_for_black_squares(grid: List[List], grid_size: int) -> Dict:
    """
    Validate if grid is suitable for black square suggestions.

    Returns:
        Dict with 'valid', 'errors', 'warnings'
    """
    errors = []
    warnings = []

    # Check grid size
    if len(grid) != grid_size or len(grid[0]) != grid_size:
        errors.append(f"Grid size mismatch: expected {grid_size}×{grid_size}")

    # Count current black squares
    black_count = sum(
        1 for row in grid for cell in row if (isinstance(cell, dict) and cell.get("isBlack", False)) or cell == "#"
    )

    # Typical max black squares: ~16% of grid
    max_black = grid_size * grid_size * 0.16
    if black_count > max_black:
        warnings.append(f"High black square count ({black_count}). " "Adding more may reduce grid quality.")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
