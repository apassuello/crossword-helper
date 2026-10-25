"""Real-subprocess e2e: CLIAdapter.parse_wordlist runs the actual CLI (no mocks)."""

from pathlib import Path

from backend.core.cli_adapter import CLIAdapter

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_parse_wordlist_through_real_cli(tmp_path):
    f = tmp_path / "import.txt"
    f.write_text("# c\napple;50\ngrape,40\nAB\napple;1\nONE TWO\nfoo,x\nCAFÉ;7\nSTRAßE\n", encoding="utf-8")

    adapter = CLIAdapter(cli_path=str(PROJECT_ROOT / "cli" / "crossword"))
    result = adapter.parse_wordlist(str(f))

    assert result == {
        "words": [{"word": "APPLE", "score": 50}, {"word": "GRAPE", "score": 40}, {"word": "CAFE", "score": 7}],
        "skipped": [
            {"line": 4, "text": "AB", "reason": "length outside 3-21"},
            {"line": 6, "text": "ONE TWO", "reason": "not letters only"},
            {"line": 7, "text": "foo,x", "reason": "malformed score"},
            {"line": 9, "text": "STRAßE", "reason": "not letters only"},
        ],
    }


def test_pattern_reports_unloadable_list_through_real_cli(tmp_path):
    """Spec O1 (#44): errors survive the adapter; other lists are still searched."""
    good = tmp_path / "good.txt"
    good.write_text("CAT;50\nCOT;42\n", encoding="utf-8")
    missing = str(tmp_path / "missing.txt")

    adapter = CLIAdapter(cli_path=str(PROJECT_ROOT / "cli" / "crossword"))
    result = adapter.pattern("C?T", wordlist_paths=[str(good), missing])

    assert {r["word"] for r in result["results"]} == {"CAT", "COT"}
    assert [e["wordlist"] for e in result["errors"]] == [missing]
    assert result["errors"][0]["message"]
