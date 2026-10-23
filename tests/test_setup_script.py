"""Tests for setup.sh and package.json install behaviour.

novice-readiness spec 0.2.4 §5 (#49): setup installs from the lock file with
``npm ci`` and package.json declares the Node floor the README names.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_package_json_declares_node_floor():
    pkg = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    assert pkg["engines"]["node"] == ">=18"


def test_setup_script_uses_npm_ci_not_npm_install():
    text = (REPO_ROOT / "setup.sh").read_text(encoding="utf-8")
    assert "npm ci" in text
    assert "npm install" not in text
