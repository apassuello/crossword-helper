"""
Theme word placement suggester.

Analyzes theme words and suggests optimal placements in the grid
with symmetry, balance, and intersection considerations.
"""

from typing import Dict, List, Optional, Tuple

from backend.core.placement_validation import _cell_state, apply_checked_placement, validate_placement

# Joint plan (spec 0.2.16 section 4 item 4): each word contributes its best K
# candidates to the plan search, and the search stops expanding after
# _PLAN_NODE_LIMIT nodes (keeping the best plan found so far), so the cost is
# bounded whatever the grid and word count.
PLAN_CANDIDATES_PER_WORD = 8
_PLAN_NODE_LIMIT = 20000

# Largest theme list the suggester accepts (spec 0.2.17 section 4 item 4).
# Two reasons, both measured rather than assumed:
# (1) Depth: the plan search in _plan_placements recurses one frame per
#     submitted word, even a word with no candidates, so a list near Python's
#     default recursion limit (1000) raised RecursionError and the route
#     answered 500. 50 sits far under that limit.
# (2) Latency: the TH4 review measured about 0.8 s for 40 long words on a
#     21x21 grid at the node cap, and ranking cost grows with every word.
MAX_THEME_WORDS = 50


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

    Strategy (spec 0.2.16 section 4 item 4):
    1. Sort words by length (longest first)
    2. Rank each word's placements on the grid as it is, independently of the
       other theme words (symmetry, intersections with letters already on the
       grid, position, diversity across the grid)
    3. Choose a joint plan, one placement per word, that places the most words
       when applied in turn, then the highest total score (_plan_placements)
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
            List of dicts, one per word, each containing top suggestions.
            Plan members (see _plan_placements) come first, in plan order,
            each led by its plan placement; the words the plan leaves out
            follow with their independent best.
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

        # Every word is judged against the grid exactly as the user has it:
        # nothing is committed to self.grid between words. A candidate must
        # pass the apply step's own conflict check (issue #15); a word with no
        # surviving candidate gets no suggestions — no fallback is fabricated.
        ranked: List[List[Tuple[Dict, int]]] = []
        for idx, (word, _) in enumerate(words_sorted):
            placements = [p for p in self._generate_placements(word) if not validate_placement(self.grid, p)]
            scored = [(p, self._score_placement_with_diversity(p, word, idx)) for p in placements]
            scored.sort(key=lambda x: x[1], reverse=True)  # stable: ties keep scan order
            ranked.append(scored)

        plan = self._plan_placements(ranked)

        members = [i for i in range(len(words_sorted)) if plan[i] is not None]
        others = [i for i in range(len(words_sorted)) if plan[i] is None]

        results = []
        for i in members + others:
            word, word_len = words_sorted[i]
            chosen = [plan[i]] if plan[i] is not None else []
            rest = [item for item in ranked[i] if item[0] is not plan[i][0]] if plan[i] is not None else ranked[i]
            top = (chosen + rest)[:max_suggestions_per_word]

            suggestions = []
            for placement, score in top:
                suggestions.append(
                    ThemePlacementSuggestion(
                        word=word,
                        row=placement["row"],
                        col=placement["col"],
                        direction=placement["direction"],
                        # Reported scores stay in the documented 0-100
                        # range; raw ranking scores (see
                        # _score_placement_with_diversity) may exceed 100
                        # via diversity bonuses before this clamp.
                        score=max(0, min(100, score)),
                        reasoning=self._generate_reasoning(placement, score, word),
                    ).to_dict()
                )
            results.append({"word": word, "length": word_len, "suggestions": suggestions})

        return results

    def _plan_placements(self, ranked: List[List[Tuple[Dict, int]]]) -> List[Optional[Tuple[Dict, int]]]:
        """
        Choose one placement per word (or none) so the most words are placed
        when applied in turn, then the highest total score.

        Each step is checked and applied on a working copy with
        apply_checked_placement — the same conflict check and the same black
        squares the apply route writes — so a placement whose blacks or twins
        would block a later word is seen here. Candidates are each word's top
        PLAN_CANDIDATES_PER_WORD by score; ties resolve to the first plan found
        (candidates tried best-first, "place" before "skip"), so the result is
        deterministic.
        """
        n = len(ranked)
        cands = [r[:PLAN_CANDIDATES_PER_WORD] for r in ranked]
        # Upper bound on the score still obtainable from words i.. (best candidate each).
        suffix_max = [0] * (n + 1)
        for i in range(n - 1, -1, -1):
            suffix_max[i] = suffix_max[i + 1] + (cands[i][0][1] if cands[i] else 0)

        best: Dict = {"count": -1, "score": -1, "plan": [None] * n}
        nodes = [0]

        def dfs(i: int, grid: List[List], count: int, score: int, chosen: List[Optional[Tuple[Dict, int]]]) -> None:
            nodes[0] += 1
            if i == n:
                if (count, score) > (best["count"], best["score"]):
                    best["count"], best["score"], best["plan"] = count, score, list(chosen)
                return
            if nodes[0] > _PLAN_NODE_LIMIT and best["count"] >= 0:
                return
            reachable = count + sum(1 for c in cands[i:] if c)
            if reachable < best["count"]:
                return
            if reachable == best["count"] and score + suffix_max[i] <= best["score"]:
                return
            for item in cands[i]:
                trial = [row[:] for row in grid]
                conflicts, _ = apply_checked_placement(trial, item[0])
                if conflicts:
                    continue
                chosen.append(item)
                dfs(i + 1, trial, count + 1, score + item[1], chosen)
                chosen.pop()
            chosen.append(None)
            dfs(i + 1, grid, count, score, chosen)
            chosen.pop()

        dfs(0, [row[:] for row in self.grid], 0, 0, [])
        return best["plan"]

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
        """Check if word fits at position without letter or black-square conflicts."""
        for i in range(len(word)):
            r, c = (row, col + i) if direction == "across" else (row + i, col)
            state, letter = _cell_state(self.grid, r, c)
            if state == "black" or (state == "letter" and letter != word[i]):
                return False
        return True

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

        # NOTE: this raw score is used for RANKING only and may exceed 100;
        # reported suggestion scores are clamped to 0-100 where suggestions
        # are built (suggest_placements).
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
        # FACTOR 1: Symmetry (0-20 points)
        # ===============================
        if self._is_centered(row, col, word_len, direction):
            score += 20

        # ===============================
        # FACTOR 2: Intersections (0-20 points)
        # ===============================
        intersections = self._count_intersections(placement, word)
        score += min(20, intersections * 10)

        # ===============================
        # FACTOR 3: Position Preference (0-15 points)
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
        # FACTOR 5: Spacing from placed words (inert, constant +10)
        # ===============================
        # self.placed_words stays empty while suggesting, because every word is
        # ranked against the grid as it is (spec 0.2.16 section 4 item 4), so
        # the distance below is always 999 and this adds the same 10 points to
        # every placement. It does not affect ranking order; it is kept so
        # the reported scores do not shift.
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

    def _count_intersections(self, placement: Dict, word: str) -> int:
        """Count how many letters intersect with placed words."""
        count = 0
        row = placement["row"]
        col = placement["col"]
        direction = placement["direction"]

        for i in range(len(word)):
            r, c = (row, col + i) if direction == "across" else (row + i, col)
            state, letter = _cell_state(self.grid, r, c)
            if state == "letter" and letter == word[i]:
                count += 1

        return count

    def _min_distance_to_placed_words(self, placement: Dict) -> int:
        """
        Minimum Manhattan distance to any word in self.placed_words.

        placed_words is filled only by apply_placement, which suggest_placements
        does not call, so during suggestion this returns 999.
        """
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

        if len(theme_words) > MAX_THEME_WORDS:
            errors.append(f"Too many theme words: {len(theme_words)} (maximum {MAX_THEME_WORDS})")

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
