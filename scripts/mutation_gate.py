#!/usr/bin/env python3
"""Certify that a mutation makes a named test fail at its own assert line.

Not a CI gate -- mutations are never committed. This is what an agent runs when
it closes a review finding by *adding a test*, to turn "test added" into
evidence. It assumes the mutation has already been made by hand in the working
tree and reverts it when done.

Each check below exists because the claim it guards was false at least once on
the decisions-16-17 branch (2026-09-10). See the module's tests.
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath

# `--tb=line` prints "<path>:<line>: <ExcType>: <msg>" -- except for a bare
# assert carrying no message, which pytest rewrites and prints as the bare
# expression: "<path>:<line>: assert 999 == 1". Both forms must parse, or every
# message-less assertion reads as "no failure".
TB_LINE = re.compile(r"^(?P<path>.+?):(?P<lineno>\d+): (?P<detail>.+)$")
EXC_TYPE = re.compile(r"^(?P<exc>[A-Za-z_][\w.]*): (?P<msg>.*)$", re.DOTALL)


class GateError(Exception):
    """The gate cannot reach a verdict. Never raised to mean 'mutation bad'."""


@dataclass(frozen=True)
class Failure:
    """One line of pytest `--tb=line` output: the deepest frame of a failure."""

    path: str
    lineno: int
    exc_type: str
    message: str = ""


def parse_tb_line(output):
    """Failures described by pytest `--tb=line` output, in reported order."""
    failures = []
    for line in output.splitlines():
        match = TB_LINE.match(line.strip())
        if match is None:
            continue
        detail = match.group("detail").strip()
        typed = EXC_TYPE.match(detail)
        if detail.startswith("assert ") or detail == "assert":
            exc_type, message = "AssertionError", detail
        elif typed:
            exc_type, message = typed.group("exc"), typed.group("msg")
        else:
            continue  # a separator or prose line, not a failure
        failures.append(
            Failure(
                path=match.group("path"),
                lineno=int(match.group("lineno")),
                exc_type=exc_type,
                message=message,
            )
        )
    return failures


def assert_linenos(test_path, test_name):
    """Line numbers of the `assert` statements inside one test function.

    `test_name` is the node-id tail: "test_x" or "TestClass::test_x". The lineno
    of a multi-line assert is its *first* line, which is what pytest reports.
    """
    leaf = test_name.split("::")[-1]
    tree = ast.parse(open(test_path).read())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == leaf:
            return {n.lineno for n in ast.walk(node) if isinstance(n, ast.Assert)}
    raise GateError(f"no test function named {leaf!r} in {test_path}")


# Exit codes. Each rejection gets its own, so a caller can tell *why* the gate
# refused without parsing prose -- and so the gate's own tests can pin them.
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NO_MUTATION = 2
EXIT_BASELINE_NOT_GREEN = 3
EXIT_NOT_COLLECTED = 4
EXIT_SURVIVED = 5
EXIT_NOT_ASSERTION_ERROR = 6
EXIT_WRONG_LINE = 7
EXIT_REVERT_FAILED = 8


@dataclass(frozen=True)
class RunResult:
    """One pytest invocation: how many tests ran, and what failed."""

    selected: int
    failures: list

    @property
    def passed(self):
        return self.selected > 0 and not self.failures


@dataclass(frozen=True)
class Outcome:
    code: int
    reason: str


def _same_file(a, b):
    return os.path.abspath(a) == os.path.abspath(b)


def verdict(baseline, mutated, target_path, target_linenos):
    """Decide whether the mutation is evidence for the target test.

    The order is load-bearing: a test that never ran cannot be said to have
    passed or failed, and a test that was already red proves nothing when it
    goes red again.
    """
    if baseline.selected != 1 or mutated.selected != 1:
        return Outcome(
            EXIT_NOT_COLLECTED,
            f"target selected {baseline.selected} time(s) at baseline and "
            f"{mutated.selected} under mutation; expected exactly 1. A marker "
            f"in pytest.ini's addopts can deselect it silently.",
        )
    if baseline.failures:
        first = baseline.failures[0]
        return Outcome(
            EXIT_BASELINE_NOT_GREEN,
            f"target is already failing without the mutation "
            f"({first.exc_type} at {first.path}:{first.lineno}); "
            f"its failure under mutation would prove nothing.",
        )
    if not mutated.failures:
        return Outcome(
            EXIT_SURVIVED,
            "target still passes with the mutation applied; it does not " "detect this defect.",
        )

    failure = mutated.failures[0]
    if failure.exc_type != "AssertionError":
        return Outcome(
            EXIT_NOT_ASSERTION_ERROR,
            f"target failed with {failure.exc_type} at {failure.path}:"
            f"{failure.lineno}, not AssertionError -- the mutation crashed "
            f"before the assertion was reached.",
        )
    if not _same_file(failure.path, target_path) or failure.lineno not in target_linenos:
        owned = ", ".join(str(n) for n in sorted(target_linenos)) or "none"
        return Outcome(
            EXIT_WRONG_LINE,
            f"AssertionError at {failure.path}:{failure.lineno}, which is not "
            f"one of the target's own assert lines ({owned}).",
        )
    return Outcome(
        EXIT_OK,
        f"AssertionError at {failure.path}:{failure.lineno}, an assert " f"statement of the target test.",
    )


COUNTS = re.compile(r"(\d+) (passed|failed|error|errors)\b")
PATCH_DIR = Path(os.environ.get("MUTATION_GATE_PATCH_DIR", tempfile.gettempdir())) / "mutation-gate"
TEST_DIR_PARTS = {"tests", "test"}


def parse_counts(output):
    """How many tests actually ran, from pytest's summary line.

    Deselected, skipped and uncollected tests did not run and are not counted --
    that distinction is the whole point: `1 deselected` must not read as a pass.
    """
    for line in reversed(output.splitlines()):
        matches = COUNTS.findall(line)
        if matches:
            return sum(int(n) for n, _ in matches)
    return 0


def is_test_path(path):
    """Whether `path` is test code, by this repo's own pytest.ini conventions."""
    parts = PurePosixPath(path).parts
    name = parts[-1]
    return (name.startswith("test_") and name.endswith(".py")) or bool(TEST_DIR_PARTS.intersection(parts[:-1]))


def _git(repo, *args, check=True):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise GateError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def dirty_paths(repo):
    """Tracked-but-modified and untracked paths, ignoring anything gitignored."""
    out = _git(repo, "status", "--porcelain", "--untracked-files=all")
    paths = set()
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        # Renames read "old -> new"; the new path is the one on disk.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.add(path.strip('"'))
    return paths


def run_pytest(repo, node_id):
    """Run one pytest selection, neutralising addopts so markers cannot hide it."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", node_id, "-q", "--tb=line", "-o", "addopts=", "-p", "no:cacheprovider"],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    return RunResult(selected=parse_counts(output), failures=parse_tb_line(output)), output


def failed_test_ids(output):
    """Node ids from pytest's `FAILED ...` summary lines."""
    return [line.split(" ", 1)[1].split(" - ")[0].strip() for line in output.splitlines() if line.startswith("FAILED ")]


def _report(lines, out_path):
    text = "\n".join(lines) + "\n"
    sys.stdout.write(text)
    out_path.write_text(text)
    return text


def main(argv=None, repo_root=None):
    parser = argparse.ArgumentParser(
        prog="mutation_gate.py",
        description="Certify that an already-applied mutation makes a named "
        "test fail at its own assert line, then revert it.",
    )
    parser.add_argument("--test", required=True, help="pytest node id, e.g. path/test_x.py::TestC::test_y")
    parser.add_argument(
        "--mutate", required=True, action="append", metavar="PATH", help="repo-relative file you mutated (repeatable)"
    )
    args = parser.parse_args(argv)

    repo = Path(repo_root) if repo_root else Path(_git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
    node_id = args.test
    test_file, _, test_name = node_id.partition("::")

    PATCH_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    patch_path = PATCH_DIR / f"mutation-gate-{stamp}.patch"
    report_path = PATCH_DIR / f"mutation-gate-{stamp}.report"

    # Saved before anything is touched, so every revert below is recoverable.
    patch_path.write_text(_git(repo, "diff"))
    header = [f"recovery patch  {patch_path}"]

    # The gate reads pytest's output through its own parse_tb_line, so mutating
    # this file breaks the instrument along with its subject: a real failure
    # goes unparsed and the run reports SURVIVED. Measured 2026-09-11 against
    # the bare-assert branch. Refuse rather than misreport.
    own_source = Path(__file__).resolve()
    aimed_at_self = [m for m in args.mutate if Path(repo / m).resolve() == own_source or Path(m).resolve() == own_source]
    if aimed_at_self:
        _report(
            header
            + [
                f"GATE FAIL ({EXIT_USAGE}): --mutate names this gate's own source "
                f"({own_source}). It parses pytest output with the code you are "
                f"mutating, so it would misreport. Run a copy from outside the "
                f"tree instead: cp {own_source} /tmp/gate.py && python /tmp/gate.py ...",
            ],
            report_path,
        )
        return EXIT_USAGE

    dirty = dirty_paths(repo)
    missing = [p for p in args.mutate if p not in dirty]
    if missing:
        _report(
            header
            + [
                f"GATE FAIL ({EXIT_NO_MUTATION}): no change present in "
                f"{', '.join(missing)}. Mutate the source first; this gate reports "
                f"on a mutation you have already made.",
            ],
            report_path,
        )
        return EXIT_NO_MUTATION

    stray = sorted(p for p in dirty - set(args.mutate) if not is_test_path(p))
    if stray:
        _report(
            header
            + [
                f"GATE FAIL ({EXIT_NO_MUTATION}): non-test files are dirty besides "
                f"the mutation: {', '.join(stray)}. Commit or stash them -- the gate "
                f"cannot tell your mutation from an unrelated edit.",
            ],
            report_path,
        )
        return EXIT_NO_MUTATION

    mutation_diff = _git(repo, "diff", "--", *args.mutate)
    if not mutation_diff.strip():
        _report(
            header
            + [
                f"GATE FAIL ({EXIT_NO_MUTATION}): {', '.join(args.mutate)} is "
                f"untracked, so there is no baseline to compare against.",
            ],
            report_path,
        )
        return EXIT_NO_MUTATION

    diff_path = PATCH_DIR / f"mutation-gate-{stamp}.mutation.patch"
    diff_path.write_text(mutation_diff)

    try:
        _git(repo, "checkout", "--", *args.mutate)
        baseline, _ = run_pytest(repo, node_id)
        _git(repo, "apply", str(diff_path))
        mutated, mutated_out = run_pytest(repo, node_id)
        neighbours, neighbour_out = run_pytest(repo, test_file)
    finally:
        _git(repo, "checkout", "--", *args.mutate, check=False)

    if _git(repo, "diff", "--", *args.mutate).strip():
        _report(
            header
            + [
                f"GATE FAIL ({EXIT_REVERT_FAILED}): {', '.join(args.mutate)} still "
                f"differs from HEAD after revert. Restore it from the patch above.",
            ],
            report_path,
        )
        return EXIT_REVERT_FAILED

    try:
        linenos = assert_linenos(str(repo / test_file), test_name)
    except GateError as exc:
        _report(header + [f"GATE FAIL ({EXIT_USAGE}): {exc}"], report_path)
        return EXIT_USAGE

    outcome = verdict(baseline, mutated, str(repo / test_file), linenos)
    others = [t for t in failed_test_ids(neighbour_out) if not t.endswith(test_name)]

    body = header + [
        f"target      {node_id}",
        f"mutated     {', '.join(args.mutate)}  ({diff_path})",
        f"baseline    {'PASS' if baseline.passed else 'NOT GREEN'} " f"({baseline.selected} selected)",
        f"mutated     {len(mutated.failures)} failure(s), " f"{mutated.selected} selected",
        f"own asserts {sorted(linenos) or 'none'}",
        f"neighbours  {len(others)} other test(s) also failed"
        + (f": {', '.join(others)}" if others else "")
        + "   [reported, not enforced -- a real defect may break several]",
        f"revert      clean, tree matches HEAD at {', '.join(args.mutate)}",
        "",
        ("GATE PASS" if outcome.code == EXIT_OK else f"GATE FAIL ({outcome.code})") + f": {outcome.reason}",
    ]
    _report(body, report_path)
    return outcome.code


if __name__ == "__main__":
    sys.exit(main())
