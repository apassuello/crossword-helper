"""Real-subprocess e2e: CLIAdapter.parse_wordlist runs the actual CLI (no mocks)."""

from pathlib import Path

from backend.core.cli_adapter import CLIAdapter

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_parse_wordlist_through_real_cli(tmp_path):
    f = tmp_path / "import.txt"
    f.write_text("# c\napple;50\ngrape,40\nAB\napple;1\nONE TWO\nfoo,x\n", encoding="utf-8")

    adapter = CLIAdapter(cli_path=str(PROJECT_ROOT / "cli" / "crossword"))
    result = adapter.parse_wordlist(str(f))

    assert result == {
        "words": [{"word": "APPLE", "score": 50}, {"word": "GRAPE", "score": 40}],
        "skipped": [
            {"line": 4, "text": "AB", "reason": "length outside 3-21"},
            {"line": 6, "text": "ONE TWO", "reason": "not letters only"},
            {"line": 7, "text": "foo,x", "reason": "malformed score"},
        ],
    }
