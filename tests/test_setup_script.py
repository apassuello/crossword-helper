"""Tests for setup.sh and package.json install behaviour.

novice-readiness spec 0.2.4 §5 (#49): setup installs from the lock file with
``npm ci`` and package.json declares the Node floor the README names.
"""

import json
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_package_json_declares_node_floor():
    pkg = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    assert pkg["engines"]["node"] == ">=18"


def test_setup_script_uses_npm_ci_not_npm_install():
    text = (REPO_ROOT / "setup.sh").read_text(encoding="utf-8")
    assert "npm ci" in text
    assert "npm install" not in text


# --- Prerequisite checks (novice-readiness spec 0.2.4 §5 (SETUP-MISSING)) ---
#
# Harness: ``setup.sh`` is copied into ``tmp_path`` (it derives ``venv/`` from
# its own location) and run with ``PATH`` set to a directory holding only
# ``make_path``'s shims plus symlinks to the few system tools the script's
# check phase needs. Reused by the pip-check tests: pass shims as keyword arguments to ``make_path``.


STOP_MARKER = "SHIM-STOP-AFTER-CHECKS"
SYSTEM_TOOLS = ("dirname", "tail", "cat")

PY_MISSING = "Missing: python3 3.9 or later — install from https://python.org/downloads"
NODE_MISSING = "Missing: node 18 or later — install from https://nodejs.org"
NPM_MISSING = "Missing: npm (installed with Node.js 18 or later)" " — install from https://nodejs.org"


def _write_shim(path: Path, body: str) -> None:
    path.write_text("#!/bin/bash\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def python_shim(major: int, minor: int) -> str:
    """Answer the three ``python3 -c`` probes; stop at ``python3 -m venv``."""
    return (
        'if [ "$1" = "-m" ]; then echo "%s"; exit 97; fi\n'
        'case "$2" in\n'
        '  *"{sys.version_info.major}.{"*) echo "%d.%d";;\n'
        '  *"version_info.major)"*) echo "%d";;\n'
        '  *"version_info.minor)"*) echo "%d";;\n'
        "esac\n" % (STOP_MARKER, major, minor, major, minor)
    )


def node_shim(major: int) -> str:
    return 'case "$1" in\n' '  --version) echo "v%d.0.0";;\n' '  -e) echo "%d";;\n' "esac\n" % (major, major)


def make_path(tmp_path: Path, **tools: str) -> str:
    """Build a PATH directory: system symlinks plus one shim per ``tools`` entry.

    ``make_path(tmp, python3=python_shim(3, 9))`` -- a tool left out is absent.
    """
    bindir = tmp_path / "shimbin"
    bindir.mkdir()
    for name in SYSTEM_TOOLS:
        real = shutil.which(name)
        assert real, name
        (bindir / name).symlink_to(real)
    for name, body in tools.items():
        _write_shim(bindir / name, body)
    return str(bindir)


def run_setup(tmp_path: Path, path: str):
    project = tmp_path / "project"
    project.mkdir()
    shutil.copy(REPO_ROOT / "setup.sh", project / "setup.sh")
    result = subprocess.run(
        [shutil.which("bash"), "setup.sh"],
        cwd=project,
        env={"PATH": path, "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
    )
    return result, project


NPM_OK = 'echo "npm shim"\n'


@pytest.mark.parametrize(
    "tools, expected",
    [
        pytest.param({}, PY_MISSING, id="no-python3"),
        pytest.param({"python3": python_shim(3, 8)}, PY_MISSING, id="python-3.8"),
        pytest.param({"python3": python_shim(3, 9)}, NODE_MISSING, id="no-node"),
        pytest.param(
            {"python3": python_shim(3, 9), "node": node_shim(16)},
            NODE_MISSING,
            id="node-16",
        ),
        pytest.param(
            {"python3": python_shim(3, 9), "node": node_shim(18)},
            NPM_MISSING,
            id="no-npm",
        ),
    ],
)
def test_failing_check_prints_one_missing_line(tmp_path, tools, expected):
    result, project = run_setup(tmp_path, make_path(tmp_path, **tools))
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert expected in output
    assert output.count("Missing:") == 1
    assert "Error:" not in output
    assert not (project / "venv").exists()
    assert not (project / "node_modules").exists()


def test_checks_pass_and_script_proceeds(tmp_path):
    path = make_path(tmp_path, python3=python_shim(3, 9), node=node_shim(18), npm=NPM_OK)
    result, _ = run_setup(tmp_path, path)
    output = result.stdout + result.stderr
    assert "Missing:" not in output
    assert "[ok] Python 3.9" in output
    assert "[ok] Node.js v18" in output
    assert STOP_MARKER in output  # reached ``python3 -m venv``, where the shim stops
