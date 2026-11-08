"""
Flask application launcher script.

Starts the development server for the Crossword Construction Helper web
application on localhost. The port is the PORT environment variable (default
5000). Debug mode is off unless FLASK_DEBUG=1. At startup it warns, without
building, when frontend/dist is older than the frontend sources.

novice-readiness spec 0.2.4 §5 (I6, SERVE-1)
"""

import errno
import os
import socket
import sys
from pathlib import Path

from backend.app import app

STALE_FRONTEND_MESSAGE = "Frontend build is older than src/ -- run npm run build"


def frontend_build_is_stale(root):
    """True if frontend/dist/index.html is older than the frontend sources.

    Issue #117. Sources are every file under <root>/src/ plus
    <root>/index.html and <root>/vite.config.js; a missing source is skipped.
    Stale means the build file exists and the newest source mtime is strictly
    greater than its mtime. No build file (dist/ missing or without index.html)
    is not stale; when dist/ is missing, backend/app.py index() says the
    frontend is unbuilt.
    """
    root = Path(root)
    build = root / "frontend" / "dist" / "index.html"
    if not build.is_file():
        return False
    sources = [root / "index.html", root / "vite.config.js"]
    sources.extend(p for p in (root / "src").rglob("*") if p.is_file())
    newest = max((p.stat().st_mtime_ns for p in sources if p.is_file()), default=None)
    return newest is not None and newest > build.stat().st_mtime_ns


def _check_port_free(host, port):
    """Exit 1 with a one-line explanation if the port is already taken.

    Werkzeug catches the bind OSError itself and calls sys.exit(1), so none ever
    reaches this script from app.run; probe the port first. SO_REUSEADDR matches
    werkzeug's own bind, so a port in TIME_WAIT is not reported as in use.
    """
    # A listener on the wildcard (0.0.0.0 or ::) does not make a bind to localhost
    # fail on macOS (AirPlay Receiver holds :5000 that way), so also connect over
    # both loopbacks: anything accepting there, whatever its bind address, is in use.
    for family, addr in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            peer = socket.socket(family, socket.SOCK_STREAM)
        except OSError:
            continue  # no IPv6 on this host
        try:
            peer.settimeout(1)
            if peer.connect_ex((addr, port)) == 0:
                print(f"Port {port} is in use. Start with PORT=<other> python3 run.py")
                sys.exit(1)
        finally:
            peer.close()
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind((host, port))
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            raise
        print(f"Port {port} is in use. Start with PORT=<other> python3 run.py")
        sys.exit(1)
    finally:
        probe.close()


if __name__ == "__main__":
    # novice-readiness spec 0.2.6 §5: an empty PORT is unset, as in the Vite proxy
    port = int(os.environ.get("PORT") or "5000")
    # With FLASK_DEBUG=1 werkzeug's reloader re-executes this file in a child
    # while its parent holds the socket; only the parent probes.
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        # Issue #117: the root is this file's directory, not the cwd; warn before
        # the port probe, so a port already in use does not hide the warning
        # (the parent only, like the probe, so FLASK_DEBUG=1 prints it once)
        if frontend_build_is_stale(Path(__file__).resolve().parent):
            print(STALE_FRONTEND_MESSAGE)
        _check_port_free("localhost", port)
    app.run(host="localhost", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
