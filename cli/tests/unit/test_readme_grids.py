"""Guard for #107: every grid the README cites must pass ``validate``.

The README is a claim about files; this pins the claim. It uses the same
check as ``python -m cli.src.cli validate``: ``Grid.from_dict(strict_size=True)``
then ``GridValidator.validate_all``.
"""

import json
import re
from pathlib import Path

import pytest
from src.core.grid import Grid
from src.core.validator import GridValidator

REPO_ROOT = Path(__file__).resolve().parents[3]
README = REPO_ROOT / "README.md"
_CITE = re.compile(r"data/grids/[A-Za-z0-9_.\-]+\.json")


def _cited():
    return sorted(set(_CITE.findall(README.read_text(encoding="utf-8"))))


def test_readme_cites_at_least_one_grid():
    assert _cited(), "README.md cites no data/grids/<name>.json path"


@pytest.mark.parametrize("rel", _cited())
def test_cited_grid_passes_validate(rel):
    path = REPO_ROOT / rel
    assert path.is_file(), f"README cites {rel} but it does not exist"
    data = json.loads(path.read_text(encoding="utf-8"))
    grid = Grid.from_dict(data, strict_size=True)
    is_valid, errors = GridValidator.validate_all(grid)
    assert is_valid is True, f"{rel} fails validate: {errors}"
