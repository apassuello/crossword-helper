"""Root conftest: test-wide fixtures that must apply before anything spawns a child."""

import os

import pytest

# pytest-cov bootstraps coverage inside subprocesses through these variables: its
# .pth file runs at interpreter startup and activates only when COV_CORE_SOURCE is
# set. The parent's own measurement is started by the plugin in-process and does
# not read them, so clearing them disables child instrumentation only.
_SUBPROCESS_COVERAGE_VARS = (
    "COV_CORE_SOURCE",
    "COV_CORE_CONFIG",
    "COV_CORE_DATAFILE",
    "COV_CORE_CONTEXT",
    "COVERAGE_PROCESS_START",
)


@pytest.fixture(scope="session", autouse=True)
def _disable_subprocess_coverage():
    """Stop coverage from instrumenting the CLI subprocesses these tests spawn.

    Only the 3.12 matrix job passes --cov, and pytest-cov propagates that into
    every child. Measured on the 5x5 fill in cli/tests/integration/
    test_fill_pause_resume.py: 0.96s of solver time and 1.92s wall uninstrumented,
    4.35s and 34.16s under coverage -- roughly a 17x tax on a process the tests
    then bound with wall-clock budgets. That combination made 3.12 the only job
    where those budgets could expire, twice, for reasons unrelated to the code
    under test.

    Children are spawned by product code as well (backend/core/cli_adapter.py,
    backend/api/routes.py), not only by tests, so this clears the environment for
    the whole session rather than passing env= at each of the call sites.

    The cost is honest and deliberate: lines executed only inside a spawned CLI
    stop counting toward the coverage total. Coverage of cli/ comes overwhelmingly
    from tests that import the modules directly; what is lost is subprocess
    double-counting of paths those tests already cover.
    """
    saved = {var: os.environ.pop(var) for var in _SUBPROCESS_COVERAGE_VARS if var in os.environ}
    yield
    os.environ.update(saved)
