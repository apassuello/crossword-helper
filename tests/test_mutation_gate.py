"""Tests for scripts/mutation_gate.py.

The gate certifies that a mutation made a named test fail *at its own assert
line*. It is only trustworthy if it rejects the ways that claim can be false,
so the cases below are the three failures recorded on the decisions-16-17
branch (2026-09-10), plus the deselect trap found while designing it.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import mutation_gate as mg  # noqa: E402

# `--tb=line` output, captured verbatim from a real pytest run.
GENUINE = (
    "=================================== FAILURES ==================================\n"
    "/tmp/probe/test_probe.py:6: AssertionError: target assertion\n"
    "=========================== short test summary info ===========================\n"
    "FAILED test_probe.py::test_genuine_assert - AssertionError: target assertion\n"
)
UPSTREAM_CRASH = (
    "=================================== FAILURES ==================================\n"
    "/tmp/probe/test_probe.py:2: TypeError: unsupported operand type(s) for &: "
    "'int' and 'NoneType'\n"
)


class TestParseTbLine:
    def test_extracts_path_line_and_exception_type(self):
        failures = mg.parse_tb_line(GENUINE)
        assert len(failures) == 1
        failure = failures[0]
        assert failure.path == "/tmp/probe/test_probe.py"
        assert failure.lineno == 6
        assert failure.exc_type == "AssertionError"

    def test_reads_the_exception_type_of_an_upstream_crash(self):
        failures = mg.parse_tb_line(UPSTREAM_CRASH)
        assert len(failures) == 1
        failure = failures[0]
        assert failure.exc_type == "TypeError"
        assert failure.lineno == 2

    def test_reads_a_bare_assert_that_carries_no_message(self):
        # pytest names the exception type only when the assert has a message.
        # A bare `assert x == y` is printed as the rewritten expression alone,
        # so matching on the literal "AssertionError" misses every one of them.
        bare = "=================================== FAILURES ==================\n" "/repo/tests/test_t.py:5: assert 999 == 1\n"
        failures = mg.parse_tb_line(bare)
        assert len(failures) == 1
        failure = failures[0]
        assert failure.exc_type == "AssertionError"
        assert failure.lineno == 5

    def test_returns_empty_when_nothing_failed(self):
        assert mg.parse_tb_line("4 passed in 0.01s\n") == []


class TestAssertLinenos:
    def test_reports_the_assert_lines_of_the_named_test_only(self, tmp_path):
        src = tmp_path / "test_sample.py"
        src.write_text(
            "def test_alpha():\n"
            "    assert 1 == 1\n"
            "\n"
            "def test_beta():\n"
            "    x = 2\n"
            "    assert x == 2\n"
            "    assert x != 3\n"
        )
        assert mg.assert_linenos(str(src), "test_beta") == {6, 7}

    def test_finds_a_test_nested_in_a_class(self, tmp_path):
        src = tmp_path / "test_cls.py"
        src.write_text("class TestThing:\n" "    def test_inner(self):\n" "        assert True\n")
        assert mg.assert_linenos(str(src), "TestThing::test_inner") == {3}

    def test_reports_the_first_line_of_a_multiline_assert(self, tmp_path):
        # pytest reports the statement's *start* line; AST must agree, or the
        # own-assert-line check is off by however tall the assert is.
        src = tmp_path / "test_multi.py"
        src.write_text(
            "def test_multiline():\n" "    a = 1\n" "    assert (\n" "        a\n" "        == 99\n" "    ), 'multi'\n"
        )
        assert mg.assert_linenos(str(src), "test_multiline") == {3}

    def test_raises_when_the_named_test_is_absent(self, tmp_path):
        src = tmp_path / "test_none.py"
        src.write_text("def test_other():\n    assert True\n")
        with pytest.raises(mg.GateError, match="test_missing"):
            mg.assert_linenos(str(src), "test_missing")


def run(selected=1, failures=()):
    return mg.RunResult(selected=selected, failures=list(failures))


def failure_at(lineno, exc_type="AssertionError", path="/repo/tests/test_t.py"):
    return mg.Failure(path=path, lineno=lineno, exc_type=exc_type)


TARGET = "/repo/tests/test_t.py"
OWN_ASSERTS = {214, 218}


class TestVerdict:
    def test_accepts_an_assertion_failure_at_the_targets_own_line(self):
        outcome = mg.verdict(
            baseline=run(),
            mutated=run(failures=[failure_at(214)]),
            target_path=TARGET,
            target_linenos=OWN_ASSERTS,
        )
        assert outcome.code == 0

    def test_rejects_a_baseline_that_is_not_green(self):
        # The real case: a test written against `propagate` instead of `refine`
        # failed under the *unfixed* code, for an unrelated reason.
        outcome = mg.verdict(
            baseline=run(failures=[failure_at(214)]),
            mutated=run(failures=[failure_at(214)]),
            target_path=TARGET,
            target_linenos=OWN_ASSERTS,
        )
        assert outcome.code == mg.EXIT_BASELINE_NOT_GREEN

    def test_rejects_a_crash_that_happens_before_the_assertion(self):
        # The real case: a mutation deleting a None guard crashed on
        # `None & ndarray` upstream, so the assertion never ran.
        outcome = mg.verdict(
            baseline=run(),
            mutated=run(failures=[failure_at(87, "TypeError", "/repo/cli/src/domain/p.py")]),
            target_path=TARGET,
            target_linenos=OWN_ASSERTS,
        )
        assert outcome.code == mg.EXIT_NOT_ASSERTION_ERROR

    def test_rejects_an_assertion_that_fires_somewhere_else(self):
        # AssertionError, but raised by an `assert` inside production code --
        # right exception type, wrong origin.
        outcome = mg.verdict(
            baseline=run(),
            mutated=run(failures=[failure_at(87, "AssertionError", "/repo/cli/src/domain/p.py")]),
            target_path=TARGET,
            target_linenos=OWN_ASSERTS,
        )
        assert outcome.code == mg.EXIT_WRONG_LINE

    def test_rejects_an_assertion_on_a_line_the_target_does_not_own(self):
        outcome = mg.verdict(
            baseline=run(),
            mutated=run(failures=[failure_at(999)]),
            target_path=TARGET,
            target_linenos=OWN_ASSERTS,
        )
        assert outcome.code == mg.EXIT_WRONG_LINE

    def test_rejects_a_mutation_that_did_not_make_the_test_fail(self):
        outcome = mg.verdict(
            baseline=run(),
            mutated=run(),
            target_path=TARGET,
            target_linenos=OWN_ASSERTS,
        )
        assert outcome.code == mg.EXIT_SURVIVED

    def test_rejects_a_target_that_was_never_collected(self):
        # The deselect trap: pytest.ini's `-m "not slow"` silently deselects a
        # slow-marked test chosen by node id -- 0 selected, and no failure.
        outcome = mg.verdict(
            baseline=run(selected=0),
            mutated=run(selected=0),
            target_path=TARGET,
            target_linenos=OWN_ASSERTS,
        )
        assert outcome.code == mg.EXIT_NOT_COLLECTED

    def test_rejects_a_target_with_no_assert_statements_at_all(self):
        outcome = mg.verdict(
            baseline=run(),
            mutated=run(failures=[failure_at(214)]),
            target_path=TARGET,
            target_linenos=set(),
        )
        assert outcome.code == mg.EXIT_WRONG_LINE

    def test_every_rejection_has_its_own_exit_code(self):
        codes = [
            mg.EXIT_BASELINE_NOT_GREEN,
            mg.EXIT_NOT_ASSERTION_ERROR,
            mg.EXIT_WRONG_LINE,
            mg.EXIT_SURVIVED,
            mg.EXIT_NOT_COLLECTED,
            mg.EXIT_NO_MUTATION,
            mg.EXIT_REVERT_FAILED,
        ]
        assert len(set(codes)) == len(codes)
        assert 0 not in codes


class TestParseCounts:
    @pytest.mark.parametrize(
        "summary, expected",
        [
            ("1 failed in 0.00s", 1),
            ("2 failed in 0.00s", 2),
            ("1 passed in 0.01s", 1),
            ("3 passed, 1 failed in 0.02s", 4),
            ("1 error in 0.04s", 1),
            # The deselect trap: nothing ran, so nothing can be concluded.
            ("1 deselected in 0.01s", 0),
            ("no tests ran in 0.00s", 0),
        ],
    )
    def test_counts_only_tests_that_actually_ran(self, summary, expected):
        assert mg.parse_counts(summary) == expected


# --- end to end, against a real git repository ----------------------------

SOURCE = "def value():\n    return 1\n"
TEST = "from src import value\n\n\ndef test_value():\n    assert value() == 1\n"


@pytest.fixture
def repo(tmp_path):
    """A committed two-file repo: one source file, one test that covers it."""
    import subprocess

    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    (tmp_path / "src.py").write_text(SOURCE)
    (tmp_path / "test_src.py").write_text(TEST)
    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    git("add", "-A")
    git("commit", "-qm", "init")
    return tmp_path


def gate(repo, *extra):
    return mg.main(
        ["--test", "test_src.py::test_value", "--mutate", "src.py", *extra],
        repo_root=str(repo),
    )


class TestEndToEnd:
    def test_accepts_a_mutation_the_test_detects(self, repo):
        (repo / "src.py").write_text("def value():\n    return 999\n")
        assert gate(repo) == mg.EXIT_OK

    def test_restores_the_working_tree_afterwards(self, repo):
        (repo / "src.py").write_text("def value():\n    return 999\n")
        gate(repo)
        assert (repo / "src.py").read_text() == SOURCE

    def test_refuses_when_no_mutation_was_made(self, repo):
        # The real case: a finding shipped with no mutation at all.
        assert gate(repo) == mg.EXIT_NO_MUTATION

    def test_refuses_a_mutation_the_test_does_not_detect(self, repo):
        (repo / "src.py").write_text("def value():\n    return 1  # noop\n")
        assert gate(repo) == mg.EXIT_SURVIVED

    def test_refuses_a_mutation_that_crashes_before_the_assertion(self, repo):
        # The real case: `None & ndarray` raised upstream of the assert.
        (repo / "src.py").write_text("def value():\n    return None & 1\n")
        assert gate(repo) == mg.EXIT_NOT_ASSERTION_ERROR

    def test_refuses_when_the_baseline_is_already_red(self, repo):
        # The real case: a test that failed under the unfixed code anyway.
        (repo / "test_src.py").write_text("from src import value\n\n\ndef test_value():\n    assert value() == 7\n")
        (repo / "src.py").write_text("def value():\n    return 999\n")
        assert gate(repo) == mg.EXIT_BASELINE_NOT_GREEN

    def test_refuses_when_an_unrelated_source_file_is_also_dirty(self, repo):
        (repo / "src.py").write_text("def value():\n    return 999\n")
        (repo / "other.py").write_text("stray = 1\n")
        assert gate(repo) == mg.EXIT_NO_MUTATION

    def test_leaves_an_uncommitted_test_file_alone(self, repo):
        # The common shape: the new test is uncommitted too. Reverting it would
        # delete the very thing being validated.
        new_test = repo / "test_new.py"
        new_test.write_text("def test_new():\n    assert True\n")
        (repo / "src.py").write_text("def value():\n    return 999\n")
        gate(repo)
        assert new_test.exists()

    def test_saves_the_working_diff_before_touching_anything(self, repo):
        (repo / "src.py").write_text("def value():\n    return 999\n")
        gate(repo)
        saved = list(mg.PATCH_DIR.glob("mutation-gate-*.patch"))
        assert saved, "no recovery patch was written"
        assert "return 999" in max(saved, key=lambda p: p.stat().st_mtime).read_text()


class TestSelfMutationGuard:
    def test_refuses_to_be_pointed_at_its_own_source(self, repo):
        # The gate reads pytest's output with its own parse_tb_line. Mutating
        # that function breaks the reading as well as the reading's subject, so
        # the gate reports SURVIVED for a mutation the test does detect. It
        # cannot be its own instrument; measured 2026-09-11.
        gate_src = Path(mg.__file__).resolve()
        code = mg.main(
            ["--test", "test_src.py::test_value", "--mutate", str(gate_src)],
            repo_root=str(repo),
        )
        assert code == mg.EXIT_USAGE

    def test_names_the_workaround_in_its_message(self, repo):
        gate_src = Path(mg.__file__).resolve()
        mg.main(
            ["--test", "test_src.py::test_value", "--mutate", str(gate_src)],
            repo_root=str(repo),
        )
        report = max(mg.PATCH_DIR.glob("*.report"), key=lambda p: p.stat().st_mtime)
        assert "copy" in report.read_text().lower()
