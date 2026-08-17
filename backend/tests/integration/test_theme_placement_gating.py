"""
Regression + characterization tests for gating ThemePlacer suggestions
through the applier's own placement validation (issue #15, backend half).

Root cause (established, not re-derived here): ThemePlacer._is_symmetric was
a tautology that credited every candidate with "Symmetric positioning",
independent of whether the applier would actually accept it. On an empty
15x15, the top suggestion for PYTHON/CROSSWORD/PUZZLE alike sat on the
symmetry axis and was rejected by apply-placement.
"""

import pytest


def _empty_grid(size=15):
    return [[{"letter": "", "isBlack": False} for _ in range(size)] for _ in range(size)]


@pytest.fixture
def app_client():
    """Create Flask test client."""
    from backend.app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def _suggest(app_client, words, grid_size=15):
    response = app_client.post(
        "/api/theme/suggest-placements",
        json={"theme_words": words, "grid_size": grid_size},
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()["suggestions"]


def _apply(app_client, suggestion, grid_size=15):
    return app_client.post(
        "/api/theme/apply-placement",
        json={
            "grid": _empty_grid(grid_size),
            "placement": {
                "word": suggestion["word"],
                "row": suggestion["row"],
                "col": suggestion["col"],
                "direction": suggestion["direction"],
            },
        },
    )


class TestNoSuggestionIsRejectedByApplier:
    """Acceptance test #1 from the task-3 brief: the regression criterion."""

    def test_every_suggestion_for_every_word_is_accepted(self, app_client):
        results = _suggest(app_client, ["PYTHON", "CROSSWORD", "PUZZLE"])
        assert results, "suggest-placements returned no words"

        rejected = []
        for word_result in results:
            assert word_result["suggestions"], f"{word_result['word']} got no suggestions at all"
            for suggestion in word_result["suggestions"]:
                response = _apply(app_client, suggestion)
                if response.status_code != 200:
                    rejected.append(
                        {
                            "word": word_result["word"],
                            "suggestion": suggestion,
                            "status": response.status_code,
                            "body": response.get_json(),
                        }
                    )

        assert not rejected, f"{len(rejected)} suggestion(s) rejected by apply-placement: {rejected}"


class TestNoUnsubstantiatedSymmetryClaim:
    """Characterization lock (acceptance test #3): the ThemePlacer tautology
    must never again credit a placement as symmetric unless the applier's
    real validator agrees.
    """

    def test_symmetry_reasoning_implies_applier_accepts(self, app_client):
        results = _suggest(app_client, ["PYTHON", "CROSSWORD", "PUZZLE"])

        unsubstantiated = []
        for word_result in results:
            for suggestion in word_result["suggestions"]:
                if "symmetric" not in suggestion["reasoning"].lower():
                    continue
                response = _apply(app_client, suggestion)
                if response.status_code != 200:
                    unsubstantiated.append({"word": word_result["word"], "suggestion": suggestion})

        assert not unsubstantiated, (
            "Suggestion(s) claimed symmetry in their reasoning but were rejected " f"by apply-placement: {unsubstantiated}"
        )
