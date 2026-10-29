"""
Unit tests for ThemePlacer.
"""

from backend.core.placement_validation import validate_placement
from backend.core.theme_placer import ThemePlacer


class TestThemePlacer:
    """Test suite for theme word placement suggester."""

    def test_initialization(self):
        """Test ThemePlacer initialization."""
        placer = ThemePlacer(15)
        assert placer.grid_size == 15
        assert len(placer.grid) == 15
        assert len(placer.grid[0]) == 15
        assert placer.placed_words == []

    def test_validate_theme_words(self):
        """Test theme word validation."""
        placer = ThemePlacer(15)

        # Valid words
        result = placer.validate_theme_words(["HELLO", "WORLD"])
        assert result["valid"] is True
        assert len(result["errors"]) == 0

        # Too long word
        result = placer.validate_theme_words(["THISWORDISTOOLONGFORTHEGRID"])
        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert "Too long" in result["errors"][0]

        # Too short word
        result = placer.validate_theme_words(["HI"])
        assert result["valid"] is False
        assert "Too short" in result["errors"][0]

        # Non-alphabetic
        result = placer.validate_theme_words(["HELLO123"])
        assert result["valid"] is False
        assert "non-alphabetic" in result["errors"][0]

    def test_single_word_placement(self):
        """Test placement suggestions for a single word."""
        placer = ThemePlacer(15)
        results = placer.suggest_placements(["HELLO"])

        assert len(results) == 1
        assert results[0]["word"] == "HELLO"
        assert results[0]["length"] == 5

        # Should have suggestions
        suggestions = results[0]["suggestions"]
        assert len(suggestions) > 0
        assert suggestions[0]["word"] == "HELLO"
        assert "row" in suggestions[0]
        assert "col" in suggestions[0]
        assert suggestions[0]["direction"] in ["across", "down"]
        assert suggestions[0]["score"] > 0
        assert suggestions[0]["reasoning"] != ""

    def test_multiple_word_placement_no_overlaps(self):
        """Test that multiple words get different placement suggestions."""
        placer = ThemePlacer(21)  # Larger grid for more options

        # Use words of different lengths to ensure variety
        words = ["CELEBRATION", "HAPPINESS", "FAMILY", "JOY"]
        results = placer.suggest_placements(words)

        assert len(results) == len(words)

        # Collect top placements
        placements = []
        for result in results:
            if result["suggestions"]:
                top = result["suggestions"][0]
                assert "WARNING" not in top["reasoning"]
                placements.append((top["row"], top["col"], top["direction"]))

        # Every word is listed with a plan placement on a 21x21 grid
        assert len(placements) == len(words), "Every word should be listed with a suggestion"

        # Check that positions are diverse (not all in same row/col)
        rows = [p[0] for p in placements]
        cols = [p[1] for p in placements]

        # At least 2 different rows and columns should be used
        assert len(set(rows)) >= 2, "Placements should use different rows"
        assert len(set(cols)) >= 2, "Placements should use different columns"

    def test_placement_with_existing_grid(self):
        """Test placement suggestions with existing grid content."""
        placer = ThemePlacer(15)

        # Create a grid with a single existing letter, positioned so it
        # intersects APPLE's 2nd letter ('P') at the grid's standard
        # horizontally-centered slot (row 6, col 5): every suggestion is now
        # gated through the applier's own validator (issue #15), so the
        # fixture must give the suggester a genuinely valid, well-scoring
        # intersection rather than relying on a placement that only *looks*
        # symmetric.
        existing_grid = [["." for _ in range(15)] for _ in range(15)]
        existing_grid[6][6] = "P"

        results = placer.suggest_placements(["APPLE"], existing_grid=existing_grid)

        assert len(results) == 1
        suggestions = results[0]["suggestions"]
        assert len(suggestions) > 0

        # Check if intersection is detected when APPLE is placed across at
        # (6, 5), intersecting the existing 'P' at (6, 6)
        found_intersection = False
        for sugg in suggestions:
            if "Intersects" in sugg["reasoning"]:
                found_intersection = True
                break

        # Should find at least one placement that intersects with existing word
        assert found_intersection, "Should detect possible intersections with existing content"

    def test_apply_placement(self):
        """Test applying a placement to the internal grid."""
        placer = ThemePlacer(15)

        placement = {"word": "HELLO", "row": 7, "col": 5, "direction": "across"}

        placer.apply_placement(placement)

        # Check that word was placed in grid
        assert placer.grid[7][5] == "H"
        assert placer.grid[7][6] == "E"
        assert placer.grid[7][7] == "L"
        assert placer.grid[7][8] == "L"
        assert placer.grid[7][9] == "O"

        # Check that placement was tracked
        assert len(placer.placed_words) == 1
        assert placer.placed_words[0] == placement

    def test_scoring_prefers_centered_placements(self):
        """Test that centered placements get higher scores."""
        placer = ThemePlacer(15)

        # Create two placements: one centered, one at edge
        centered = {"row": 7, "col": 5, "direction": "across", "word": "HELLO"}
        edge = {"row": 0, "col": 0, "direction": "across", "word": "HELLO"}

        score_centered = placer._score_placement(centered, "HELLO")
        score_edge = placer._score_placement(edge, "HELLO")

        assert score_centered > score_edge, "Centered placement should score higher"

    def test_diversity_in_large_grid(self):
        """Test that many theme words spread across a large grid."""
        placer = ThemePlacer(21)

        # 15 theme words as mentioned in the problem
        theme_words = [
            "ANNIVERSARY",
            "HAPPINESS",
            "CELEBRATION",
            "MEMORIES",
            "TOGETHER",
            "FAMILY",
            "FRIENDS",
            "JOURNEY",
            "BLESSING",
            "GRATITUDE",
            "CHERISH",
            "FOREVER",
            "JOYFUL",
            "SPECIAL",
            "MILESTONE",
        ]

        results = placer.suggest_placements(theme_words)

        # Count successful placements (without overlaps)
        placed_count = 0
        positions = []

        for result in results:
            if result["suggestions"]:
                top = result["suggestions"][0]
                assert "WARNING" not in top["reasoning"]
                placed_count += 1
                positions.append((top["row"], top["col"]))

        # Should place at least 10 words successfully
        assert placed_count >= 10, f"Should place at least 10 words, got {placed_count}"

        # Check for reasonable distribution
        if placed_count >= 10:
            rows = [p[0] for p in positions]
            cols = [p[1] for p in positions]

            # Should use a good spread of the grid
            assert max(rows) - min(rows) > 5, "Words should spread vertically"
            assert max(cols) - min(cols) > 5, "Words should spread horizontally"

    def test_overlap_detection(self):
        """Test that placer avoids overlapping with existing placements."""
        placer = ThemePlacer(15)

        # Place first word
        placement1 = {"word": "HELLO", "row": 7, "col": 5, "direction": "across"}
        placer.apply_placement(placement1)

        # Get suggestions for second word
        results = placer.suggest_placements(["WORLD"])
        suggestions = results[0]["suggestions"]

        # Suggestions are checked against the grid as it is (HELLO included):
        # none may conflict with it, and none may carry a WARNING (TH4 removed
        # the "WARNING: Overlaps" fallback).
        assert suggestions
        for sugg in suggestions:
            assert "WARNING" not in sugg["reasoning"]
            assert validate_placement(placer.grid, {**sugg, "word": "WORLD"}) == []

    def test_intersection_scoring(self):
        """Test that intersections are detected and contribute to scoring."""
        placer = ThemePlacer(15)

        # Place "HELLO" horizontally at row 7, columns 5-9
        # H(7,5), E(7,6), L(7,7), L(7,8), O(7,9)
        placement1 = {"word": "HELLO", "row": 7, "col": 5, "direction": "across"}
        placer.apply_placement(placement1)

        # Check that intersection count works
        # Place "BELL" vertically through the 'L' at column 7
        # If we place at (5,7), we get: B(5,7), E(6,7), L(7,7), L(8,7)
        # This should intersect with HELLO's L at (7,7)
        placement_with_intersection = {
            "row": 5,
            "col": 7,
            "direction": "down",
            "word": "BELL",
        }

        # Place at column 2 should have no intersection
        placement_no_intersection = {
            "row": 5,
            "col": 2,
            "direction": "down",
            "word": "BELL",
        }

        intersections_good = placer._count_intersections(placement_with_intersection, "BELL")
        intersections_bad = placer._count_intersections(placement_no_intersection, "BELL")

        # Should detect the 'L' intersection at (7,7)
        assert intersections_good == 1, f"Should detect one intersection, got {intersections_good}"
        assert intersections_bad == 0, "Should detect no intersections"


# ---------------------------------------------------------------------------
# TH4 (novice-readiness spec 0.2.16 section 4 item 4): suggestions are found on
# the user's grid as it is, independently per word, and the first suggestions
# form a joint plan checked with the apply step's own conflict check + blacks.
# ---------------------------------------------------------------------------

import json  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_11 = ["OBSERVATION", "MIRRORIMAGE", "PERFORMANCE"]


@pytest.fixture
def client():
    from backend.app import app

    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _example_11_grid():
    return json.loads((REPO_ROOT / "data" / "grids" / "example_11x11.json").read_text())["grid"]


def _suggest_via_route(client, words, grid):
    resp = client.post(
        "/api/theme/suggest-placements",
        json={"theme_words": words, "grid_size": len(grid), "existing_grid": grid},
    )
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["suggestions"]


def _apply_firsts_in_order(client, grid, results):
    """Apply each listed word's suggestions[0] through the apply route, in
    response order, feeding each reply's grid forward. Returns [(word, ok)]."""
    outcome = []
    current = grid
    for entry in results:
        s = entry["suggestions"][0]
        resp = client.post(
            "/api/theme/apply-placement",
            json={
                "grid": current,
                "placement": {"word": entry["word"], "row": s["row"], "col": s["col"], "direction": s["direction"]},
            },
        )
        ok = resp.status_code == 200
        if ok:
            current = resp.get_json()["grid"]
        outcome.append((entry["word"], ok))
    return outcome


class TestTH4JointPlan:
    def test_row1_every_word_lists_a_suggestion(self, client):
        results = _suggest_via_route(client, EXAMPLE_11, _example_11_grid())
        assert [r["word"] for r in results if not r["suggestions"]] == []

    def test_row2_apply_all_places_two_and_third_is_rejected(self, client):
        grid = _example_11_grid()
        results = _suggest_via_route(client, EXAMPLE_11, grid)
        outcome = _apply_firsts_in_order(client, grid, [r for r in results if r["suggestions"]])
        assert [ok for _, ok in outcome] == [True, True, False], outcome

    def test_row3_reversed_input_still_places_two(self, client):
        grid = _example_11_grid()
        results = _suggest_via_route(client, list(reversed(EXAMPLE_11)), grid)
        assert [r["word"] for r in results if not r["suggestions"]] == []
        outcome = _apply_firsts_in_order(client, grid, results)
        assert [ok for _, ok in outcome] == [True, True, False], outcome

    def test_row4_plan_honours_blacks_the_apply_step_writes(self, client):
        # 7x7, every cell black except: row 1 "C . . . E . #" and col 5 rows 0-3,
        # plus a row-6 slot for OWL and a 'Z' at (5,6).
        # CRANE's only placement is row 1 cols 0-4; its right boundary (1,5) is
        # empty, so applying it writes a black at (1,5). DOGS's only placement
        # is down col 5 rows 0-3 and needs (1,5) as a letter. A placer that
        # commits letters only (the pre-fix behaviour) lists CRANE, DOGS, OWL
        # in length order, so apply-in-order places CRANE, rejects DOGS and
        # places OWL; the plan must instead list the rejected word last.
        g = [["#"] * 7 for _ in range(7)]
        for c in (1, 2, 3, 5):
            g[1][c] = "."
        g[1][0], g[1][4] = "C", "E"
        for r in (0, 2, 3):
            g[r][5] = "."
        for c in (0, 1, 2):
            g[6][c] = "."
        g[5][6] = "Z"
        results = _suggest_via_route(client, ["CRANE", "DOGS", "OWL"], g)
        assert [r["word"] for r in results if not r["suggestions"]] == []
        outcome = _apply_firsts_in_order(client, g, results)
        assert [ok for _, ok in outcome] == [True, True, False], outcome
        assert {w for w, ok in outcome if not ok} <= {"CRANE", "DOGS"}

    def test_row5_word_that_fits_nowhere_gets_no_suggestions_and_no_warning(self, client):
        g = [["#"] * 5 for _ in range(5)]
        for c in (0, 1, 2):
            g[2][c] = "."
        results = _suggest_via_route(client, ["ZEBRA", "CAT"], g)
        by_word = {r["word"]: r["suggestions"] for r in results}
        assert by_word["ZEBRA"] == []
        assert len(by_word["CAT"]) >= 1
        assert "WARNING" not in json.dumps(results)

    def test_row5_dict_format_grid_is_read_like_string_format(self, client):
        g = [[{"letter": "", "isBlack": True} for _ in range(5)] for _ in range(5)]
        for c in (0, 1, 2):
            g[2][c] = {"letter": "", "isBlack": False}
        results = _suggest_via_route(client, ["ZEBRA", "CAT"], g)
        by_word = {r["word"]: r["suggestions"] for r in results}
        assert by_word["ZEBRA"] == []
        assert len(by_word["CAT"]) >= 1
        assert "WARNING" not in json.dumps(results)

    def test_scores_stay_clamped_and_no_duplicate_placements(self, client):
        results = _suggest_via_route(client, EXAMPLE_11, _example_11_grid())
        for r in results:
            keys = [(s["row"], s["col"], s["direction"]) for s in r["suggestions"]]
            assert len(keys) == len(set(keys))
            assert all(0 <= s["score"] <= 100 for s in r["suggestions"])

    def test_plan_search_is_bounded_and_deterministic(self):
        import time

        grid = json.loads((REPO_ROOT / "data" / "grids" / "example_15x15.json").read_text())["grid"]
        words = ["HOUSE", "MOUSE", "LEMON", "RIVER", "CLOUD"]
        t0 = time.perf_counter()
        first = ThemePlacer(15).suggest_placements(words, existing_grid=grid)
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.0, elapsed
        assert ThemePlacer(15).suggest_placements(words, existing_grid=grid) == first


CAPPED_WORDS = ["MYNBIQP", "MZJPLSG", "QEJEYDT", "ZIRWZTE", "JDXCVKP", "RDLNKTU", "GRPOQIB", "ZRACXMW", "ZVUATPK", "HXKWCGS"]


class TestPlanNodeCap:
    def test_capped_plan_search_still_returns_a_valid_plan_and_suggests_every_fitting_word(self, monkeypatch):
        """Spec 0.2.16 section 4 item 4: past the node budget the search keeps the best plan found so far."""
        import backend.core.theme_placer as theme_placer

        calls = {"n": 0}
        real = theme_placer.apply_checked_placement

        def spy(grid, placement):
            calls["n"] += 1
            return real(grid, placement)

        monkeypatch.setattr(theme_placer, "apply_checked_placement", spy)

        # (i) the cap path was taken: tightening the limit strictly reduces the
        # search work, which only happens if the cap branch cuts the search.
        monkeypatch.setattr(theme_placer, "_PLAN_NODE_LIMIT", 1000)
        ThemePlacer(7).suggest_placements(CAPPED_WORDS)
        looser_calls = calls["n"]
        monkeypatch.setattr(theme_placer, "_PLAN_NODE_LIMIT", 1)
        calls["n"] = 0
        results = ThemePlacer(7).suggest_placements(CAPPED_WORDS)
        assert calls["n"] < looser_calls, (calls["n"], looser_calls)

        # (iii) every word fits somewhere on an empty 7x7, so every word is suggested.
        assert [r["word"] for r in results if not r["suggestions"]] == []

        # (ii) plan members come first; their first suggestions apply in turn
        # with no conflicts. The plan is non-trivial: several words, not none.
        grid = [[""] * 7 for _ in range(7)]
        applied = 0
        for entry in results:
            s = entry["suggestions"][0]
            conflicts, _ = real(grid, {"word": entry["word"], "row": s["row"], "col": s["col"], "direction": s["direction"]})
            if conflicts:
                break
            applied += 1
        assert applied >= 4, applied


# ---------------------------------------------------------------------------
# Spec 0.2.17 section 4 item 4: a theme list over MAX_THEME_WORDS is refused.
# The plan search recurses one frame per word, so an unbounded list raised
# RecursionError (HTTP 500) on the suggest route.
# ---------------------------------------------------------------------------


def _distinct_words(n):
    import itertools
    import string

    return ["".join(t) for t in itertools.islice(itertools.product(string.ascii_uppercase, repeat=3), n)]


class TestMaxThemeWords:
    def test_over_the_cap_is_invalid_and_names_both_numbers(self):
        from backend.core.theme_placer import MAX_THEME_WORDS

        words = _distinct_words(1100)
        result = ThemePlacer(7).validate_theme_words(words)
        assert result["valid"] is False
        assert f"Too many theme words: 1100 (maximum {MAX_THEME_WORDS})" in result["errors"]

    def test_exactly_the_cap_is_valid_and_gets_suggestions(self):
        from backend.core.theme_placer import MAX_THEME_WORDS

        words = _distinct_words(MAX_THEME_WORDS)
        placer = ThemePlacer(7)
        assert placer.validate_theme_words(words)["valid"] is True
        results = placer.suggest_placements(words)
        assert len(results) == MAX_THEME_WORDS

    def test_one_over_the_cap_is_invalid(self):
        from backend.core.theme_placer import MAX_THEME_WORDS

        result = ThemePlacer(7).validate_theme_words(_distinct_words(MAX_THEME_WORDS + 1))
        assert result["valid"] is False

    def test_suggest_route_returns_400_with_the_cap_error_not_500(self, client):
        resp = client.post("/api/theme/suggest-placements", json={"theme_words": _distinct_words(1100), "grid_size": 7})
        assert resp.status_code == 400, resp.get_data(as_text=True)[:200]
        assert any("Too many theme words" in e for e in resp.get_json()["validation"]["errors"])

    def test_validate_route_reports_the_cap_error(self, client):
        resp = client.post("/api/theme/validate", json={"theme_words": _distinct_words(1100), "grid_size": 7})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["valid"] is False
        assert any("Too many theme words" in e for e in body["errors"])

    def test_upload_route_reports_the_cap_error(self, client):
        resp = client.post("/api/theme/upload", json={"content": "\n".join(_distinct_words(1100)), "grid_size": 7})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["validation"]["valid"] is False
        assert any("Too many theme words" in e for e in body["validation"]["errors"])


def test_suggestions_never_abut_an_existing_letter():
    """Regression: a letter next to a word was treated like a black square, so
    CAT was suggested at row 3 cols 0-2 against an S at col 3 (reads CATS...)."""
    from backend.core.theme_placer import ThemePlacer

    grid = [["." for _ in range(7)] for _ in range(7)]
    grid[3][3] = "S"
    results = ThemePlacer(7).suggest_placements(["CAT"], existing_grid=grid, max_suggestions_per_word=500)
    cells = {
        (s["row"], s["col"] + 3) if s["direction"] == "across" else (s["row"] + 3, s["col"]) for s in results[0]["suggestions"]
    }
    before = {
        (s["row"], s["col"] - 1) if s["direction"] == "across" else (s["row"] - 1, s["col"]) for s in results[0]["suggestions"]
    }
    assert results[0]["suggestions"]
    assert (3, 3) not in cells | before
