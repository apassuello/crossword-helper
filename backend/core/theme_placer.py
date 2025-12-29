"""
Theme word placement suggester.

Analyzes theme words and suggests optimal placements in the grid
with symmetry, balance, and intersection considerations.
"""

from typing import List, Dict, Optional


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
            'word': self.word,
            'row': self.row,
            'col': self.col,
            'direction': self.direction,
            'score': self.score,
            'reasoning': self.reasoning
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
        self.grid = [['' for _ in range(grid_size)] for _ in range(grid_size)]
        self.placed_words = []

    def suggest_placements(
        self,
        theme_words: List[str],
        existing_grid: Optional[List[List]] = None,
        max_suggestions_per_word: int = 3
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
            self.grid = [row[:] for row in existing_grid]

        # Sort words by length (longest first)
        words_sorted = sorted(
            [(w.upper(), len(w)) for w in theme_words],
            key=lambda x: x[1],
            reverse=True
        )

        results = []

        for word, word_len in words_sorted:
            # Generate all possible placements
            placements = self._generate_placements(word)

            # Score each placement
            scored_placements = [
                (p, self._score_placement(p, word))
                for p in placements
            ]

            # Sort by score and take top N
            scored_placements.sort(key=lambda x: x[1], reverse=True)
            top_placements = scored_placements[:max_suggestions_per_word]

            # Convert to suggestion objects
            suggestions = []
            for placement, score in top_placements:
                reasoning = self._generate_reasoning(placement, score, word)
                suggestions.append(
                    ThemePlacementSuggestion(
                        word=word,
                        row=placement['row'],
                        col=placement['col'],
                        direction=placement['direction'],
                        score=score,
                        reasoning=reasoning
                    ).to_dict()
                )

            results.append({
                'word': word,
                'length': word_len,
                'suggestions': suggestions
            })

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
                    if self._fits(word, row, col, 'across'):
                        placements.append({
                            'row': row,
                            'col': col,
                            'direction': 'across',
                            'word': word
                        })

                # Down
                if row + word_len <= self.grid_size:
                    if self._fits(word, row, col, 'down'):
                        placements.append({
                            'row': row,
                            'col': col,
                            'direction': 'down',
                            'word': word
                        })

        return placements

    def _fits(self, word: str, row: int, col: int, direction: str) -> bool:
        """Check if word fits at position without conflicts."""
        word_len = len(word)

        for i in range(word_len):
            if direction == 'across':
                cell = self.grid[row][col + i]
            else:  # down
                cell = self.grid[row + i][col]

            # Check for conflicts
            if cell and cell != word[i]:
                return False

        return True

    def _score_placement(self, placement: Dict, word: str) -> int:
        """
        Score a placement based on multiple factors.

        Returns score 0-100.
        """
        score = 50  # Base score

        row = placement['row']
        col = placement['col']
        direction = placement['direction']
        word_len = len(word)

        # ===============================
        # FACTOR 1: Symmetry (0-30 points)
        # ===============================
        if self._is_centered(row, col, word_len, direction):
            score += 30
        elif self._is_symmetric(row, col, word_len, direction):
            score += 15

        # ===============================
        # FACTOR 2: Intersections (0-20 points)
        # ===============================
        intersections = self._count_intersections(placement, word)
        score += min(20, intersections * 10)

        # ===============================
        # FACTOR 3: Position Preference (0-20 points)
        # ===============================
        # Prefer middle rows for across, middle cols for down
        if direction == 'across':
            # Prefer rows near middle (0, 7, 14 for 15x15)
            distance_from_middle = abs(row - self.grid_size // 2)
            position_score = 20 - (distance_from_middle * 2)
            score += max(0, position_score)
        else:  # down
            # Prefer cols near middle
            distance_from_middle = abs(col - self.grid_size // 2)
            position_score = 20 - (distance_from_middle * 2)
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
        if direction == 'across':
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

        if direction == 'across':
            # Check if row is symmetric
            return abs(row - center) == abs((self.grid_size - 1 - row) - center)
        else:  # down
            # Check if col is symmetric
            return abs(col - center) == abs((self.grid_size - 1 - col) - center)

    def _count_intersections(self, placement: Dict, word: str) -> int:
        """Count how many letters intersect with placed words."""
        count = 0
        row = placement['row']
        col = placement['col']
        direction = placement['direction']

        for i in range(len(word)):
            if direction == 'across':
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
        row = placement['row']
        col = placement['col']

        for placed in self.placed_words:
            # Calculate Manhattan distance
            dist = abs(row - placed['row']) + abs(col - placed['col'])
            min_dist = min(min_dist, dist)

        return min_dist

    def _generate_reasoning(self, placement: Dict, score: int, word: str) -> str:
        """Generate human-readable reasoning for the suggestion."""
        reasons = []

        row = placement['row']
        col = placement['col']
        direction = placement['direction']
        word_len = len(word)

        # Check what contributed to score
        if self._is_centered(row, col, word_len, direction):
            reasons.append("Centered placement (symmetric)")
        elif self._is_symmetric(row, col, word_len, direction):
            reasons.append("Symmetric positioning")

        intersections = self._count_intersections(placement, word)
        if intersections > 0:
            reasons.append(f"Intersects {intersections} letters")

        if direction == 'across':
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
        word = placement['word']
        row = placement['row']
        col = placement['col']
        direction = placement['direction']

        # Place word in grid
        for i, letter in enumerate(word):
            if direction == 'across':
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

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
