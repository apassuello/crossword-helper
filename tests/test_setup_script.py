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
# Harness: ``setup.sh`` is copied into a ``make_project`` dir under ``tmp_path`` (it
# derives ``venv/`` from its own location) and run with ``PATH`` set to a directory
# holding only ``make_path``'s shims plus symlinks to the few system tools the script
# needs. Reused by the pip-check tests: pass shims as keyword arguments to
# ``make_path``; pre-create ``venv/`` between ``make_project`` and ``run_setup``.


STOP_MARKER = "SHIM-STOP-AFTER-CHECKS"
PIP_MARKER = "SHIM-PIP-REACHED"
SYSTEM_TOOLS = ("dirname", "tail", "cat", "mkdir", "chmod", "rm")

PY_MISSING = "Missing: python3 3.9 or later — install from https://python.org/downloads"
NODE_MISSING = "Missing: node 18 or later — install from https://nodejs.org"
NPM_MISSING = "Missing: npm (installed with Node.js 18 or later) — install from https://nodejs.org"
VENV_MISSING = "Install python3-venv (for example: sudo apt install python3-venv), then run ./setup.sh again"

# Body of a ``venv/bin/pip`` shim: prove the script got past the venv block.
PIP_SHIM_BODY = 'echo "%s"; exit 97\n' % PIP_MARKER

# What the ``python3 -m venv`` shim does with the target directory ($3).
VENV_STOP = 'echo "%s"; exit 97\n' % STOP_MARKER
VENV_NO_PIP_EXIT_0 = 'mkdir -p "$3/bin"; exit 0\n'
VENV_NO_PIP_EXIT_1 = 'mkdir -p "$3/bin"; exit 1\n'
VENV_WITH_PIP = (
    'mkdir -p "$3/bin"\n'
    "printf '#!/bin/bash\\n%s' > \"$3/bin/pip\"\n"
    'chmod +x "$3/bin/pip"\n' % PIP_SHIM_BODY.replace("\n", "")
)

NPM_OK = 'echo "npm shim"\n'


def _write_shim(path: Path, body: str) -> None:
    path.write_text("#!/bin/bash\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def python_shim(major: int, minor: int, venv: str = VENV_STOP) -> str:
    """Answer the three ``python3 -c`` probes; ``python3 -m venv`` runs ``venv``."""
    return (
        'if [ "$1" = "-m" ]; then\n%s fi\n'
        'case "$2" in\n'
        '  *"{sys.version_info.major}.{"*) echo "%d.%d";;\n'
        '  *"version_info.major)"*) echo "%d";;\n'
        '  *"version_info.minor)"*) echo "%d";;\n'
        "esac\n" % (venv, major, minor, major, minor)
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


def make_project(tmp_path: Path) -> Path:
    """Create the project dir holding a copy of ``setup.sh``; callers may seed ``venv/``."""
    project = tmp_path / "project"
    project.mkdir()
    shutil.copy(REPO_ROOT / "setup.sh", project / "setup.sh")
    return project


def make_venv(project: Path, with_pip: bool) -> None:
    """Seed ``project/venv`` as an earlier run would have left it."""
    (project / "venv" / "bin").mkdir(parents=True)
    if with_pip:
        _write_shim(project / "venv" / "bin" / "pip", PIP_SHIM_BODY)


def run_setup(project: Path, path: str):
    return subprocess.run(
        [shutil.which("bash"), "setup.sh"],
        cwd=project,
        env={"PATH": path, "HOME": str(project.parent)},
        capture_output=True,
        text=True,
    )


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
    project = make_project(tmp_path)
    result = run_setup(project, make_path(tmp_path, **tools))
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert expected in output
    assert output.count("Missing:") == 1
    assert "Error:" not in output
    assert not (project / "venv").exists()
    assert not (project / "node_modules").exists()


def test_checks_pass_and_script_proceeds(tmp_path):
    path = make_path(tmp_path, python3=python_shim(3, 9), node=node_shim(18), npm=NPM_OK)
    result = run_setup(make_project(tmp_path), path)
    output = result.stdout + result.stderr
    assert "Missing:" not in output
    assert "[ok] Python 3.9" in output
    assert "[ok] Node.js v18" in output
    assert STOP_MARKER in output  # reached ``python3 -m venv``, where the shim stops


# --- venv/bin/pip check (novice-readiness spec 0.2.4 §5 (venv)) ---


def _venv_run(tmp_path, venv_body=VENV_STOP, seed=None):
    """Run setup.sh past the checks; ``seed`` is None, "no-pip" or "pip"."""
    path = make_path(tmp_path, python3=python_shim(3, 9, venv_body), node=node_shim(18), npm=NPM_OK)
    project = make_project(tmp_path)
    if seed:
        make_venv(project, with_pip=(seed == "pip"))
    result = run_setup(project, path)
    return result, result.stdout + result.stderr, project


@pytest.mark.parametrize(
    "venv_body, seed",
    [
        pytest.param(VENV_NO_PIP_EXIT_0, None, id="created-without-pip"),
        pytest.param(VENV_NO_PIP_EXIT_1, None, id="venv-fails-leaves-partial"),
        pytest.param(VENV_STOP, "no-pip", id="existing-without-pip"),
    ],
)
def test_venv_without_pip_is_removed_and_names_the_package(tmp_path, venv_body, seed):
    result, output, project = _venv_run(tmp_path, venv_body, seed)
    assert result.returncode == 1, output
    assert VENV_MISSING in output
    assert PIP_MARKER not in output
    assert not (project / "venv").exists()


def test_existing_venv_with_pip_continues(tmp_path):
    result, output, project = _venv_run(tmp_path, seed="pip")
    assert "Installing Python dependencies" in output
    assert PIP_MARKER in output
    assert VENV_MISSING not in output
    assert (project / "venv" / "bin" / "pip").exists()


def test_created_venv_with_pip_continues(tmp_path):
    result, output, project = _venv_run(tmp_path, VENV_WITH_PIP)
    assert "Virtual environment created" in output
    assert PIP_MARKER in output
    assert VENV_MISSING not in output
    assert (project / "venv" / "bin" / "pip").exists()


# --- npm ci failure (novice-readiness spec 0.2.6 §5) ---

NPM_CI_ERROR = "npm ERR! package.json and package-lock.json are not in sync"
# The error comes first and a log-path line last, as npm prints them: ``tail -1`` kept only the latter.
NPM_CI_FAILS = (
    'if [ "$1" = "ci" ]; then echo "%s" >&2; echo "npm ERR! A complete log is in /x/debug.log" >&2; exit 1; fi\n'
    'echo "npm shim"\n' % NPM_CI_ERROR
)


def test_failing_npm_ci_shows_its_error_and_stops(tmp_path):
    path = make_path(tmp_path, python3=python_shim(3, 9), node=node_shim(18), npm=NPM_CI_FAILS)
    project = make_project(tmp_path)
    (project / "venv" / "bin").mkdir(parents=True)
    _write_shim(project / "venv" / "bin" / "pip", "exit 0\n")
    result = run_setup(project, path)
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert NPM_CI_ERROR in output
    assert "[ok] Node.js dependencies installed" not in output
    assert "Building frontend" not in output
