"""Unit tests for the parse-wordlist CLI command (spec 2026-10-22 basics-first, section 4, O4)."""

import json
import os
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_parse(tmp_path, content, extra=None):
    path = tmp_path / "list.txt"
    path.write_text(content, encoding="utf-8")
    cmd = [sys.executable, "-m", "cli.src.cli", "parse-wordlist", str(path), "--json-output"] + (extra or [])
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
    return r


def parse(tmp_path, content):
    r = run_parse(tmp_path, content)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_scored_word_is_uppercased_with_score(tmp_path):
    assert parse(tmp_path, "APPLE;50\n") == {"words": [{"word": "APPLE", "score": 50}], "skipped": []}
    assert parse(tmp_path, "grape,40\n")["words"] == [{"word": "GRAPE", "score": 40}]


def test_plain_word_has_null_score(tmp_path):
    assert parse(tmp_path, "apple\n")["words"] == [{"word": "APPLE", "score": None}]


def test_malformed_score_skipped(tmp_path):
    out = parse(tmp_path, "apple,x\n")
    assert out["words"] == []
    assert out["skipped"] == [{"line": 1, "text": "apple,x", "reason": "malformed score"}]


def test_overflowing_score_skipped_and_other_words_kept(tmp_path):
    out = parse(tmp_path, "DOG;1e999\nCAT;50\n")
    assert out["words"] == [{"word": "CAT", "score": 50}]
    assert out["skipped"] == [{"line": 1, "text": "DOG;1e999", "reason": "malformed score"}]


def test_accented_word_accepted(tmp_path):
    """novice-readiness spec 0.2.12 section 4 (L11): the fold, not the accented spelling, is what loads."""
    assert parse(tmp_path, "CAFÉ\n")["words"] == [{"word": "CAFE", "score": None}]


@pytest.mark.parametrize(
    "line, word, score",
    [
        ("CAFÉ", "CAFE", None),
        ("NAÏVE", "NAIVE", None),
        ("ÜBER", "UBER", None),
        ("café", "CAFE", None),
        ("CAFÉ;50", "CAFE", 50),
        ("CAFE\u0301", "CAFE", None),
        ("\uff23\uff21\uff34", "CAT", None),
    ],
)
def test_fold_rows(tmp_path, line, word, score):
    out = parse(tmp_path, line + "\n")
    assert out["words"] == [{"word": word, "score": score}]
    assert out["skipped"] == []


def test_duplicate_detected_after_fold(tmp_path):
    out = parse(tmp_path, "CAFE\nCAFÉ\n")
    assert out["words"] == [{"word": "CAFE", "score": None}]
    assert out["skipped"] == []


@pytest.mark.parametrize("line", ["STRAßE", "ÆON", "BJØRN", "ΑΒΓ"])
def test_unfoldable_letters_skipped_not_letters_only(tmp_path, line):
    out = parse(tmp_path, line + "\n")
    assert out["words"] == []
    assert out["skipped"] == [{"line": 1, "text": line, "reason": "not letters only"}]


def test_bare_sharp_s_is_classified_by_length_first(tmp_path):
    """PD-L6: a bare ß is too short; length is classified before letters."""
    assert parse(tmp_path, "ß\n")["skipped"] == [{"line": 1, "text": "ß", "reason": "length outside 3-21"}]


def test_too_short_skipped(tmp_path):
    assert parse(tmp_path, "AB\n")["skipped"] == [{"line": 1, "text": "AB", "reason": "length outside 3-21"}]


def test_too_long_skipped(tmp_path):
    out = parse(tmp_path, "A" * 22 + "\n")
    assert out["skipped"][0]["reason"] == "length outside 3-21"


def test_not_letters_skipped(tmp_path):
    assert parse(tmp_path, "ONE TWO\n")["skipped"] == [{"line": 1, "text": "ONE TWO", "reason": "not letters only"}]


def test_length_classified_before_letters(tmp_path):
    assert parse(tmp_path, "A1\n")["skipped"][0]["reason"] == "length outside 3-21"


def test_blank_and_comment_lines_ignored_but_counted_in_line_numbers(tmp_path):
    out = parse(tmp_path, "# header\n\ncat\n   \nAB\n")
    assert out["words"] == [{"word": "CAT", "score": None}]
    assert out["skipped"] == [{"line": 5, "text": "AB", "reason": "length outside 3-21"}]


def test_skipped_text_is_stripped(tmp_path):
    assert parse(tmp_path, "   AB  \n")["skipped"][0]["text"] == "AB"


def test_duplicates_keep_first_occurrence_case_insensitive(tmp_path):
    out = parse(tmp_path, "cat;10\nCAT;99\ndog\n")
    assert out["words"] == [{"word": "CAT", "score": 10}, {"word": "DOG", "score": None}]
    assert out["skipped"] == []


def test_missing_file_is_click_usage_error(tmp_path):
    cmd = [sys.executable, "-m", "cli.src.cli", "parse-wordlist", str(tmp_path / "nope.txt"), "--json-output"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
    assert r.returncode == 2
    assert "does not exist" in r.stderr
