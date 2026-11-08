"""Launcher tests for run.py and backend/app.py's __main__ block.

novice-readiness spec 0.2.4 §5 (I6, SERVE-1): debug is off unless FLASK_DEBUG=1,
the port comes from PORT, and run.py explains a port that is already in use.
"""

import errno
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
    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, addr: errno.ECONNREFUSED)
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


def test_empty_port_is_unset(clean_env, launch):
    """novice-readiness spec 0.2.6 §5: the Vite proxy treats PORT="" as unset."""
    clean_env.setenv("PORT", "")
    assert launch()["port"] == 5000


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


def _probe_in_use(family, bind_addr):
    if not socket.has_ipv6 and family == socket.AF_INET6:
        pytest.skip("host has no IPv6")
    held = socket.socket(family)
    try:
        held.bind((bind_addr, 0))
    except OSError:
        held.close()
        pytest.skip(f"cannot bind {bind_addr}")
    held.listen()
    port = held.getsockname()[1]
    try:
        proc = subprocess.run(
            [sys.executable, str(RUN_PY)],
            cwd=str(ROOT),
            env=_env(PORT=str(port)),
            capture_output=True,
            text=True,
            timeout=15,
        )
    finally:
        held.close()
    out = proc.stdout + proc.stderr
    assert f"Port {port} is in use. Start with PORT=<other> python3 run.py" in out
    assert proc.returncode == 1


def test_wildcard_ipv4_listener_is_in_use():
    """macOS lets a localhost bind succeed beside a 0.0.0.0 listener (AirPlay
    Receiver's case); the probe must still report the port in use."""
    _probe_in_use(socket.AF_INET, "0.0.0.0")


def test_wildcard_ipv6_listener_is_in_use():
    _probe_in_use(socket.AF_INET6, "::")


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


# --- #117: warn when the frontend build is older than its source -------------
#
# Contract rulings R1-R9 and cases N1-N9 / W1-W5 are in the task contract. The
# message is transcribed here, not imported, so the tests pin its value.

STALE_MESSAGE = "Frontend build is older than src/ -- run npm run build"

OLD = 500_000
BUILD = 1_000_000
NEW = 2_000_000


def _touch(path, mtime, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    os.utime(path, (mtime, mtime))
    return path


def _tree(root, *, build=BUILD, src=OLD, index=OLD, vite=OLD, nested=OLD):
    """Build a fake checkout; a None mtime leaves that file out."""
    if build is not None:
        _touch(root / "frontend" / "dist" / "index.html", build)
    if src is not None:
        _touch(root / "src" / "a.js", src)
    if nested is not None:
        _touch(root / "src" / "components" / "x" / "y.jsx", nested)
    if index is not None:
        _touch(root / "index.html", index)
    if vite is not None:
        _touch(root / "vite.config.js", vite)
    return root


def _is_stale(root):
    import run

    return run.frontend_build_is_stale(root)


def test_n1_src_newer_than_build_is_stale(tmp_path):
    assert _is_stale(_tree(tmp_path, src=NEW)) is True


def test_n2_build_newer_than_every_source_is_fresh(tmp_path):
    assert _is_stale(_tree(tmp_path)) is False


def test_n3_no_dist_is_not_stale(tmp_path):
    assert _is_stale(_tree(tmp_path, build=None, src=NEW)) is False


def test_n4_dist_without_index_html_is_not_stale(tmp_path):
    _tree(tmp_path, build=None, src=NEW)
    (tmp_path / "frontend" / "dist").mkdir(parents=True)
    assert _is_stale(tmp_path) is False


def test_n5_root_index_html_newer_is_stale(tmp_path):
    assert _is_stale(_tree(tmp_path, index=NEW)) is True


def test_n6_vite_config_newer_is_stale(tmp_path):
    assert _is_stale(_tree(tmp_path, vite=NEW)) is True


def test_n7_nested_source_newer_is_stale(tmp_path):
    assert _is_stale(_tree(tmp_path, nested=NEW)) is True


def test_n8_equal_mtimes_are_not_stale(tmp_path):
    assert _is_stale(_tree(tmp_path, src=BUILD, index=BUILD, vite=BUILD, nested=BUILD)) is False


def test_n9_no_sources_at_all_is_not_stale(tmp_path):
    root = _tree(tmp_path, src=None, nested=None, index=None, vite=None)
    assert _is_stale(root) is False


def test_message_constant_equals_the_contract_literal():
    import run

    assert run.STALE_FRONTEND_MESSAGE == STALE_MESSAGE


# W rows: the real run.py source is copied into a temp root so that its own
# location (R2) is a tree the test controls; the real checkout is never read
# for staleness and never modified. `backend` still resolves via PYTHONPATH /
# sys.path from the repo.


def _stale_root(tmp_path, *, stale=True):
    root = tmp_path / "checkout"
    _tree(root, src=NEW if stale else OLD)
    (root / "run.py").write_text(RUN_PY.read_text())
    return root


def _empty_cwd(tmp_path):
    cwd = tmp_path / "empty-cwd"
    cwd.mkdir()
    return cwd


def _run_copy_in_process(root, cwd, monkeypatch):
    monkeypatch.chdir(cwd)
    with mock.patch.object(flask_app, "run"):
        runpy.run_path(str(root / "run.py"), run_name="__main__")


def test_w1_stale_root_prints_the_message_once(clean_env, tmp_path, capsys):
    root = _stale_root(tmp_path)
    _run_copy_in_process(root, _empty_cwd(tmp_path), clean_env)
    assert capsys.readouterr().out.count(STALE_MESSAGE) == 1


def test_w2_fresh_root_prints_no_message(clean_env, tmp_path, capsys):
    root = _stale_root(tmp_path, stale=False)
    _run_copy_in_process(root, _empty_cwd(tmp_path), clean_env)
    assert STALE_MESSAGE not in capsys.readouterr().out


def test_w3_reloader_child_does_not_print_the_message(clean_env, tmp_path, capsys):
    clean_env.setenv("WERKZEUG_RUN_MAIN", "true")
    root = _stale_root(tmp_path)
    _run_copy_in_process(root, _empty_cwd(tmp_path), clean_env)
    assert STALE_MESSAGE not in capsys.readouterr().out


def _run_copy_with_held_port(root, cwd):
    held, port = _held_socket()
    try:
        proc = subprocess.run(
            [sys.executable, str(root / "run.py")],
            cwd=str(cwd),
            env=_env(PORT=str(port), PYTHONPATH=str(ROOT)),
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        held.close()
    return proc, port


def test_w4_stale_root_with_held_port_warns_then_reports_the_port(tmp_path):
    root = _stale_root(tmp_path)
    proc, port = _run_copy_with_held_port(root, _empty_cwd(tmp_path))
    assert STALE_MESSAGE in proc.stdout
    port_msg = f"Port {port} is in use. Start with PORT=<other> python3 run.py"
    assert port_msg in proc.stdout
    assert proc.stdout.index(STALE_MESSAGE) < proc.stdout.index(port_msg)
    assert "Traceback" not in proc.stdout + proc.stderr
    assert proc.returncode == 1


def test_w5_root_comes_from_run_py_location_not_cwd(tmp_path):
    root = _stale_root(tmp_path)
    cwd = _empty_cwd(tmp_path)
    assert list(cwd.iterdir()) == []
    proc, _ = _run_copy_with_held_port(root, cwd)
    assert STALE_MESSAGE in proc.stdout
