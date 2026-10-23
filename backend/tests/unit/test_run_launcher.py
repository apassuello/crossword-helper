"""Launcher tests for run.py and backend/app.py's __main__ block.

novice-readiness spec 0.2.4 §5 (I6, SERVE-1): debug is off unless FLASK_DEBUG=1,
the port comes from PORT, and run.py explains a port that is already in use.
"""

import os
import runpy
import socket
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from backend.app import app as flask_app

ROOT = Path(__file__).resolve().parents[3]
RUN_PY = ROOT / "run.py"
APP_PY = ROOT / "backend" / "app.py"


@pytest.fixture
def clean_env(monkeypatch):
    for name in ("FLASK_DEBUG", "PORT", "WERKZEUG_RUN_MAIN"):
        monkeypatch.delenv(name, raising=False)
    # run.py probes the port before app.run; keep patched-run cases independent
    # of whatever is listening on this machine.
    monkeypatch.setattr(socket.socket, "bind", lambda self, addr: None)
    return monkeypatch


def _run_run_py():
    with mock.patch.object(flask_app, "run") as run:
        runpy.run_path(str(RUN_PY), run_name="__main__")
    return run.call_args.kwargs


def _run_app_py():
    with mock.patch("flask.Flask.run") as run:
        runpy.run_path(str(APP_PY), run_name="__main__")
    return run.call_args.kwargs


@pytest.fixture(params=[_run_run_py, _run_app_py], ids=["run.py", "app.py"])
def launch(request):
    return request.param


def test_defaults(clean_env, launch):
    kw = launch()
    assert (kw["host"], kw["port"], kw["debug"]) == ("localhost", 5000, False)


def test_flask_debug_1_turns_debug_on(clean_env, launch):
    clean_env.setenv("FLASK_DEBUG", "1")
    assert launch()["debug"] is True


def test_flask_debug_0_is_off(clean_env, launch):
    clean_env.setenv("FLASK_DEBUG", "0")
    assert launch()["debug"] is False


def test_port_env_is_an_int(clean_env, launch):
    clean_env.setenv("PORT", "5057")
    port = launch()["port"]
    assert port == 5057 and isinstance(port, int)


def test_non_integer_port_propagates(clean_env):
    clean_env.setenv("PORT", "abc")
    with pytest.raises(ValueError):
        _run_run_py()


def _held_socket():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen()
    return s, s.getsockname()[1]


def _env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in ("FLASK_DEBUG", "PORT")}
    env.update(extra)
    return env


@pytest.mark.parametrize("debug", [None, "1"], ids=["debug-off", "debug-on"])
def test_port_in_use_is_explained(debug):
    held, port = _held_socket()
    try:
        extra = {"PORT": str(port)}
        if debug:
            extra["FLASK_DEBUG"] = debug
        proc = subprocess.run(
            [sys.executable, str(RUN_PY)],
            cwd=str(ROOT),
            env=_env(**extra),
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        held.close()
    out = proc.stdout + proc.stderr
    assert f"Port {port} is in use. Start with PORT=<other> python3 run.py" in out
    assert "Traceback" not in out
    assert proc.returncode == 1


def test_probe_ignores_time_wait_leftovers():
    """A port whose last connection is in TIME_WAIT is free for werkzeug (it
    binds with SO_REUSEADDR); the probe must agree, not report 'in use'."""
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen()
    port = srv.getsockname()[1]
    cli = socket.create_connection(("127.0.0.1", port))
    conn, _ = srv.accept()
    conn.close()  # active close on the server side leaves TIME_WAIT on port
    cli.close()
    srv.close()
    with mock.patch.object(flask_app, "run") as run:
        os.environ["PORT"] = str(port)
        try:
            runpy.run_path(str(RUN_PY), run_name="__main__")
        finally:
            del os.environ["PORT"]
    assert run.call_args.kwargs["port"] == port


def test_reloader_child_skips_the_probe(clean_env):
    """In the reloader child the parent already holds the port."""
    clean_env.setenv("WERKZEUG_RUN_MAIN", "true")
    probes = []
    clean_env.setattr(socket.socket, "bind", lambda self, addr: probes.append(addr))
    _run_run_py()
    assert probes == []


def test_other_oserror_propagates(clean_env):
    def boom(self, addr):
        raise OSError(13, "Permission denied")

    clean_env.setattr(socket.socket, "bind", boom)
    with pytest.raises(OSError) as exc:
        _run_run_py()
    assert exc.value.errno == 13
