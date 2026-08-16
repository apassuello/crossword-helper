"""Contract test: openapi.yaml is authoritative for the HTTP surface.

This exists because API_REFERENCE.md and openapi.yaml were both hand-maintained
descriptions of the same API, with no mechanism keeping either honest. They
drifted: the 2026-08 audit found openapi.yaml missing 10 live endpoints.

The fix is not "be more careful" - it is this test. If a route is added to Flask
without being added to the spec, CI fails.
"""

import re

import yaml

from backend.app import create_app

SPEC_PATH = "docs/api/openapi.yaml"

# openapi.yaml's servers[].url ends in /api, so its paths are relative to that.
API_PREFIX = "/api"


def _live_api_paths():
    """Every /api route registered on the real Flask app, normalised to spec form."""
    app = create_app()
    paths = set()
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith(API_PREFIX):
            continue
        # Flask "<task_id>" / "<int:n>" -> OpenAPI "{task_id}" / "{n}"
        p = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", rule.rule)
        paths.add(p[len(API_PREFIX) :] or "/")
    return paths


def _spec_paths():
    with open(SPEC_PATH) as fh:
        spec = yaml.safe_load(fh)
    return set(spec.get("paths", {}) or {})


def test_openapi_documents_every_live_route():
    """Every live /api route must appear in openapi.yaml."""
    missing = sorted(_live_api_paths() - _spec_paths())
    assert not missing, "Routes live in Flask but absent from openapi.yaml:\n  " + "\n  ".join(missing)


def test_openapi_documents_no_dead_routes():
    """Every documented path must correspond to a real route."""
    dead = sorted(_spec_paths() - _live_api_paths())
    assert not dead, "Paths in openapi.yaml with no matching Flask route:\n  " + "\n  ".join(dead)
