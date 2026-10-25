"""
Tests for ConventionHelper.normalize through the CLI.

novice-readiness spec 0.2.12 section 4 (CLI-normalize) and section 8 PD-L7: the
default rule (no named rule matched) keeps letters only, folded as section 4
item 1 folds them (fold_letters), uppercased; input with no letter gives "".
The named rules are unchanged and checked first.
"""

import json
import re

import pytest
from click.testing import CliRunner

from cli.src.cli import cli
from cli.src.core.conventions import ConventionHelper


def _normalize(text):
    result = CliRunner().invoke(cli, ["normalize", text, "--json-output"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


# (input, normalized, rule.type). Named-rule rows pass before and after the change.
NAMED_ROWS = [
    ("Tina Fey", "TINAFEY", "two_word_names"),
    # Plan table says "The Office" -> title_with_article, but RULES checks two_word_names
    # first and "The Office" matches it; order is unchanged by this task, so pin the
    # actual rule and use an input that reaches title_with_article.
    ("The Office", "THEOFFICE", "two_word_names"),
    ("La haine", "LAHAINE", "title_with_article"),
    ("self-aware", "SELFAWARE", "hyphenated"),
    ("can't", "CANT", "apostrophe"),
]

# Inputs below match none of RULES (see test_default_inputs_match_no_named_rule).
DEFAULT_ROWS = [
    ("Hello, World!", "HELLOWORLD"),
    ("É", "E"),
    ("Zoë Müller", "ZOEMULLER"),  # ë/ü defeat two_word_names' [a-z]+
    ("123 !?", ""),
    ("", ""),
    # No NFKD decomposition: still letters after the fold, kept, then upper().
    ("Straße", "STRASSE"),  # str.upper() turns ß into SS
    ("Æon", "ÆON"),
    ("Øl", "ØL"),
    ("Œuvre", "ŒUVRE"),
]


@pytest.mark.parametrize("text,expected,rule_type", NAMED_ROWS)
def test_named_rules_unchanged(text, expected, rule_type):
    out = _normalize(text)
    assert out["normalized"] == expected
    assert out["rule"]["type"] == rule_type


@pytest.mark.parametrize("text,expected", DEFAULT_ROWS)
def test_default_rule_keeps_folded_letters_only(text, expected):
    out = _normalize(text)
    assert out["rule"]["type"] == "default"
    assert out["normalized"] == expected


@pytest.mark.parametrize("text,_expected", DEFAULT_ROWS)
def test_default_inputs_match_no_named_rule(text, _expected):
    for name, rule in ConventionHelper.RULES.items():
        assert not re.search(rule["pattern"], text), name


def test_default_description_is_letters_only():
    out = _normalize("Hello, World!")
    assert out["rule"]["description"] == "Letters only"
    assert "remove spaces" not in out["rule"]["explanation"].lower()
