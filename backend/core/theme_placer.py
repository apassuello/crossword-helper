"""
Theme word placement suggester.

Analyzes theme words and suggests optimal placements in the grid
with symmetry, balance, and intersection considerations.
"""

from typing import Dict, List, Optional


class ThemePlacementSuggestion:
    """A single placement suggestion for a theme word."""

    def __init__(self, word: str, row: int, col: int, direction: str, score: int, reasoning: str):
        self.word = word
        self.row = row
        self.col = col
        self.direction = direction
        self.score = score
        self.reasoning = reasoning

    def to_dict(self):
        return {
            "word": self.word,
            "row": self.row,
            "col": self.col,
            "direction": self.direction,
            "score": self.score,
            "reasoning": self.reasoning,
        }


class ThemePlacer:
    """
    Suggests optimal placements for theme words in crossword grids.

    Strategy:
    1. Sort words by length (longest first)
    2. Place longest word centered horizontally (symmetric)
    3. Find intersecting placements for remaining words
    4. Maximize spacing and symmetry
    """

    def __init__(self, grid_size: int):
        self.grid_size = grid_size
        self.grid = [["" for _ in range(grid_size)] for _ in range(grid_size)]
        self.placed_words = []

    def suggest_placements(
        self,
        theme_words: List[str],
        existing_grid: Optional[List[List]] = None,
        max_suggestions_per_word: int = 3,
    ) -> List[Dict]:
        """
        Suggest placements for all theme words.

        Args:
            theme_words: List of theme words to place
            existing_grid: Optional existing grid content (list of lists)
            max_suggestions_per_word: Number of suggestions to return per word

        Returns:
            List of dicts, one per word, each containing top suggestions
        """
        # Initialize grid from existing if provided
        if existing_grid:
            # Normalize the grid: convert '.' to empty string for consistency
            self.grid = []
            for row in existing_grid:
                normalized_row = []
                for cell in row:
                    if cell == ".":
                        normalized_row.append("")
                    else:
                        normalized_row.append(cell)
                self.grid.append(normalized_row)

        # Sort words by length (longest first)
        words_sorted = sorted([(w.upper(), len(w)) for w in theme_words], key=lambda x: x[1], reverse=True)

        results = []

        # Track which cells are occupied to avoid overlaps
        occupied_cells = set()
        for row_idx, row in enumerate(self.grid):
            for col_idx, cell in enumerate(row):
                if cell and cell not in ("", ".", None):
                    occupied_cells.add((row_idx, col_idx))

        for idx, (word, word_len) in enumerate(words_sorted):
            # Generate all possible placements
            placements = self._generate_placements(word)

            # Filter out placements that overlap with already placed words (except valid intersections)
            valid_placements = []
            for p in placements:
                if not self._has_invalid_overlap(p, word, occupied_cells):
                    valid_placements.append(p)

            # If no valid placements due to overlaps, include all and note in reasoning
            if not valid_placements:
                valid_placements = placements

            # Score each placement with diversity factor based on word index
            scored_placements = [(p, self._score_placement_with_diversity(p, word, idx)) for p in valid_placements]

            # Sort by score and take top N
            scored_placements.sort(key=lambda x: x[1], reverse=True)
            top_placements = scored_placements[:max_suggestions_per_word]

            # Convert to suggestion objects
            suggestions = []
            best_placement = None

            for placement, score in top_placements:
                # Check if this placement overlaps with already placed words
                has_overlap = self._has_invalid_overlap(placement, word, occupied_cells)

                reasoning = self._generate_reasoning(placement, score, word)
                if has_overlap:
                    reasoning = f"WARNING: Overlaps with placed words. {reasoning}"

                suggestions.append(
                    ThemePlacementSuggestion(
                        word=word,
                        row=placement["row"],
                        col=placement["col"],
                        direction=placement["direction"],
                        score=score,
                        reasoning=reasoning,
                    ).to_dict()
                )

                # Track the best non-overlapping placement
                if not has_overlap and best_placement is None:
                    best_placement = placement

            results.append({"word": word, "length": word_len, "suggestions": suggestions})

            # Apply the best placement to the grid to avoid future overlaps
            # Only apply if we have a valid non-overlapping placement
            if best_placement:
                self.apply_placement(best_placement)
                # Update occupied cells
                row = best_placement["row"]
                col = best_placement["col"]
                direction = best_placement["direction"]
                for i in range(word_len):
                    if direction == "across":
                        occupied_cells.add((row, col + i))
                    else:
                        occupied_cells.add((row + i, col))

        return results

    def _generate_placements(self, word: str) -> List[Dict]:
        """Generate all valid placements for a word."""
        placements = []
        word_len = len(word)

        # Try all positions and directions
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                # Across
                if col + word_len <= self.grid_size:
                    if self._fits(word, row, col, "across"):
                        placements.append(
                            {
                                "row": row,
                                "col": col,
                                "direction": "across",
                                "word": word,
                            }
                        )

                # Down
                if row + word_len <= self.grid_size:
                    if self._fits(word, row, col, "down"):
                        placements.append({"row": row, "col": col, "direction": "down", "word": word})

        return placements

    def _fits(self, word: str, row: int, col: int, direction: str) -> bool:
        """Check if word fits at position without conflicts."""
        word_len = len(word)

        for i in range(word_len):
            if direction == "across":
                cell = self.grid[row][col + i]
            else:  # down
                cell = self.grid[row + i][col]

            # Check for conflicts
            # Empty cells can be '', '.', or None
            if cell and cell not in ("", ".", None) and cell != word[i]:
                return False

        return True

    def _has_invalid_overlap(self, placement: Dict, word: str, occupied_cells: set) -> bool:
        """
        Check if placement has invalid overlap with occupied cells.
        Valid overlaps are when the same letter appears at the intersection.
        """
        row = placement["row"]
        col = placement["col"]
        direction = placement["direction"]
        word_len = len(word)

        for i in range(word_len):
            if direction == "across":
                cell_pos = (row, col + i)
            else:
                cell_pos = (row + i, col)

            if cell_pos in occupied_cells:
                # Check if it's a valid intersection (same letter)
                r, c = cell_pos
                existing_letter = self.grid[r][c]
                if existing_letter != word[i]:
                    return True  # Invalid overlap - different letters
        return False  # No invalid overlap

    def _score_placement_with_diversity(self, placement: Dict, word: str, word_index: int) -> int:
        """
        Score a placement with diversity factor to spread words across the grid.

        Args:
            placement: The placement to score
            word: The word being placed
            word_index: Index of this word in the sorted list (0 = longest)
        """
        # Start with base scoring
        base_score = self._score_placement(placement, word)

        # Add diversity bonus based on word index and position
        diversity_score = 0
        row = placement["row"]
        col = placement["col"]
        direction = placement["direction"]

        # Divide grid into regions (quadrants + center)
        third = self.grid_size // 3

        # First word (longest) prefers center
        if word_index == 0:
            if third <= row < 2 * third and third <= col < 2 * third:
                diversity_score = 20
        # Second word prefers top/bottom thirds
        elif word_index == 1:
            if row < third or row >= 2 * third:
                diversity_score = 15
        # Third word prefers left/right thirds
        elif word_index == 2:
            if col < third or col >= 2 * third:
                diversity_score = 15
        # Subsequent words get bonus for being away from center
        else:
            distance_from_center = max(abs(row - self.grid_size // 2), abs(col - self.grid_size // 2))
            diversity_score = min(15, distance_from_center)

        # Alternate between horizontal and vertical preferences
        if word_index % 2 == 0 and direction == "across":
            diversity_score += 5
        elif word_index % 2 == 1 and direction == "down":
            diversity_score += 5

        return base_score + diversity_score

    def _score_placement(self, placement: Dict, word: str) -> int:
        """
        Score a placement based on multiple factors.

        Returns score 0-100.
        """
        score = 50  # Base score

        row = placement["row"]
        col = placement["col"]
        direction = placement["direction"]
        word_len = len(word)

        # ===============================
        # FACTOR 1: Symmetry (0-20 points) - Reduced from 30
        # ===============================
        if self._is_centered(row, col, word_len, direction):
            score += 20
        elif self._is_symmetric(row, col, word_len, direction):
            score += 10

        # ===============================
        # FACTOR 2: Intersections (0-20 points)
        # ===============================
        intersections = self._count_intersections(placement, word)
        score += min(20, intersections * 10)

        # ===============================
        # FACTOR 3: Position Preference (0-15 points) - Reduced from 20
        # ===============================
        # Moderate preference for middle positions (not too strong)
        if direction == "across":
            # Prefer rows near middle but with gentler gradient
            distance_from_middle = abs(row - self.grid_size // 2)
            position_score = 15 - (distance_from_middle * 1.5)
            score += max(0, position_score)
        else:  # down
            # Prefer cols near middle but with gentler gradient
            distance_from_middle = abs(col - self.grid_size // 2)
            position_score = 15 - (distance_from_middle * 1.5)
            score += max(0, position_score)

        # ===============================
        # FACTOR 4: Length Consideration (0-10 points)
        # ===============================
        # Longer words get bonus for centered placement
        if word_len >= self.grid_size * 0.6:  # 60% of grid
            if self._is_centered(row, col, word_len, direction):
                score += 10

        # ===============================
        # FACTOR 5: Spacing (0-10 points)
        # ===============================
        # Bonus for good spacing from other theme words
        min_distance = self._min_distance_to_placed_words(placement)
        if min_distance > 4:
            score += 10
        elif min_distance > 2:
            score += 5

        # ===============================
        # PENALTIES
        # ===============================
        # Penalty for edge placements (avoid edges for long words)
        if word_len > 8:
            if row == 0 or row == self.grid_size - 1:
                score -= 10
            if col == 0 or col == self.grid_size - 1:
                score -= 10

        return max(0, min(100, score))

    def _is_centered(self, row: int, col: int, word_len: int, direction: str) -> bool:
        """Check if placement is centered in the grid."""
        if direction == "across":
            # Horizontally centered
            expected_col = (self.grid_size - word_len) // 2
            expected_row = self.grid_size // 2
            return col == expected_col and abs(row - expected_row) <= 1
        else:  # down
            # Vertically centered
            expected_row = (self.grid_size - word_len) // 2
            expected_col = self.grid_size // 2
            return row == expected_row and abs(col - expected_col) <= 1

    def _is_symmetric(self, row: int, col: int, word_len: int, direction: str) -> bool:
        """Check if placement maintains rotational symmetry."""
        # Rotational symmetry: (r, c) ↔ (grid_size-1-r, grid_size-1-c)
        center = self.grid_size // 2

        if direction == "across":
            # Check if row is symmetric
            return abs(row - center) == abs((self.grid_size - 1 - row) - center)
        else:  # down
            # Check if col is symmetric
            return abs(col - center) == abs((self.grid_size - 1 - col) - center)

    def _count_intersections(self, placement: Dict, word: str) -> int:
        """Count how many letters intersect with placed words."""
        count = 0
        row = placement["row"]
        col = placement["col"]
        direction = placement["direction"]

        for i in range(len(word)):
            if direction == "across":
                cell = self.grid[row][col + i]
            else:
                cell = self.grid[row + i][col]

            if cell and cell == word[i]:
                count += 1

        return count

    def _min_distance_to_placed_words(self, placement: Dict) -> int:
        """Calculate minimum distance to any already placed word."""
        if not self.placed_words:
            return 999  # No placed words yet

        min_dist = 999
        row = placement["row"]
        col = placement["col"]

        for placed in self.placed_words:
            # Calculate Manhattan distance
            dist = abs(row - placed["row"]) + abs(col - placed["col"])
            min_dist = min(min_dist, dist)

        return min_dist

    def _generate_reasoning(self, placement: Dict, score: int, word: str) -> str:
        """Generate human-readable reasoning for the suggestion."""
        reasons = []

        row = placement["row"]
        col = placement["col"]
        direction = placement["direction"]
        word_len = len(word)

        # Check what contributed to score
        if self._is_centered(row, col, word_len, direction):
            reasons.append("Centered placement (symmetric)")
        elif self._is_symmetric(row, col, word_len, direction):
            reasons.append("Symmetric positioning")

        intersections = self._count_intersections(placement, word)
        if intersections > 0:
            reasons.append(f"Intersects {intersections} letters")

        if direction == "across":
            if abs(row - self.grid_size // 2) <= 2:
                reasons.append("Good horizontal position")
        else:
            if abs(col - self.grid_size // 2) <= 2:
                reasons.append("Good vertical position")

        if word_len >= self.grid_size * 0.6:
            reasons.append(f"Long word ({word_len} letters)")

        if not reasons:
            reasons.append("Valid placement")

        return ", ".join(reasons)

    def apply_placement(self, placement: Dict):
        """Apply a placement to the internal grid (for multi-word analysis)."""
        word = placement["word"]
        row = placement["row"]
        col = placement["col"]
        direction = placement["direction"]

        # Place word in grid
        for i, letter in enumerate(word):
            if direction == "across":
                self.grid[row][col + i] = letter
            else:
                self.grid[row + i][col] = letter

        # Track placed word
        self.placed_words.append(placement)

    def validate_theme_words(self, theme_words: List[str]) -> Dict:
        """
        Validate theme words before placement.

        Returns:
            Dict with 'valid', 'errors', 'warnings'
        """
        errors = []
        warnings = []

        for word in theme_words:
            word_clean = word.strip().upper()

            # Check length
            if len(word_clean) > self.grid_size:
                errors.append(f"{word}: Too long for {self.grid_size}×{self.grid_size} grid")
            elif len(word_clean) < 3:
                errors.append(f"{word}: Too short (minimum 3 letters)")

            # Check characters
            if not word_clean.isalpha():
                errors.append(f"{word}: Contains non-alphabetic characters")

            # Warnings for very long words
            if len(word_clean) > self.grid_size * 0.8:
                warnings.append(f"{word}: Very long ({len(word_clean)} letters), may be hard to place")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
