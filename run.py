"""
Flask application launcher script.

Starts the development server for the Crossword Construction Helper web
application on localhost. The port is the PORT environment variable (default
5000). Debug mode is off unless FLASK_DEBUG=1.

novice-readiness spec 0.2.4 §5 (I6, SERVE-1)
"""

import errno
import os
import socket
import sys

from backend.app import app


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
        _check_port_free("localhost", port)
    app.run(host="localhost", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
