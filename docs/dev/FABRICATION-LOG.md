# Fabrication Log

**Version 1.1.0** · docs-overhaul audit 2026-08-15 · source sweep 2026-08-16

---

## AI READING INSTRUCTION

Read `[SPEC]` and `[BUG]` blocks for authoritative facts.
Read `[NOTE]` only if additional context is needed.
`[?]` blocks are unverified.

---

## 1. Purpose

**[SPEC]**
- Record of factual claims found asserted in this repo that were false against the code.
- Scope of the 2026-08-15 pass: `.md` documentation + three confirmed source files.
- Scope of the 2026-08-16 pass: every tracked `.py` file under `cli/` and `backend/` —
  module/class/function docstrings, `#` comments, and Click `help=`/`epilog=` strings.
  Reproduce the file set with:

      git ls-files '*.py' | grep -E '^(cli|backend)/'

**[NOTE]**
This file exists because the 2026-08 audit found that source-code comments carried the *same*
fabrications as the documentation. That breaks the usual tie-breaker — "check the docs against the
code" silently fails when the code's own prose is wrong. Audits must treat code comments as
claims to verify, not as ground truth.

---

## 2. The originating error

**[SPEC]**
- Claim: the wordlist contains "454k+ words".
- Reality: `data/wordlists/comprehensive.txt` contains **44,024** words (`wc -l`).
- Off by ~10x. Propagated into two `CLAUDE.md` files, `ALGORITHM_DEEP_DIVE.md`, `DEVELOPMENT.md`,
  and three source files, none of which had ever been re-checked against the file.

---

## 3. Fixed 2026-08-15

**[SPEC]**

| File | Line | Was | Now |
|---|---|---|---|
| `cli/src/fill/trie_pattern_matcher.py` | 5 | "10-50x faster pattern matching" | complexity statement, no multiplier |
| `cli/src/fill/trie_pattern_matcher.py` | 23 | "Performance comparison (454k word list)" + per-query ms | complexity + pointer to the benchmark |
| `cli/src/fill/trie_pattern_matcher.py` | 51 | "454k words: ~2-3 seconds" | build-cost note, no figure |
| `cli/tests/performance/benchmark_algorithms.py` | 236 | "full comprehensive ~454k words" | "Full comprehensive wordlist" |

---

## 4. Source sweep — 2026-08-16

**[SPEC]**
- All tracked `.py` files under `cli/` and `backend/` were read. 167 claims were extracted and
  adjudicated. Outcome by bucket:

| Bucket | Count | Disposition |
|---|---|---|
| FALSE (contradicts the code) | 35 raised, **22 sustained** | rewritten |
| NEEDS_REWRITE (figure with no reproducing command, incl. unverifiable) | 85 | rewritten |
| TRUE_WITH_REPRO (true and already names its command) | 25 | left alone |
| SELF_REPRODUCING (figure the test itself measures and asserts) | 22 | left alone |

- 12 FALSE verdicts were overturned by an adversarial pass and **not** changed.
  Grounds, all previously seen in the 2026-08-15 audit: text citing external literature
  (`iterative_repair.py` cites Ginsberg 1990 for candidate-count figures — that is a report of
  published work, not a measurement of this repo); section-header labels naming a scoring band
  rather than asserting a measurement (`black_square_suggester.py` `FACTOR N (0-100)`).
- 37 files were modified. The change is comment- and docstring-only; verified mechanically by
  parsing each file before and after, stripping docstring nodes, and comparing the ASTs.

**[SPEC] Findings that are code defects, not prose defects.** Both were verified first-hand,
not taken from the audit's report. Neither was fixed by this sweep — the sweep changed comments
only — and both are recorded here as open:

- **[BUG] `cli/src/fill/pause_controller.py`** — the documented 100 ms rate limit on pause checks
  is never applied. `should_pause()` calls `self.pause_file.exists()` unconditionally at the top;
  the interval block below it runs only in the not-paused branch and returns `False` either way,
  so it gates nothing. `_check_interval` is dead. The solver calls this in its inner loop, so it
  makes one filesystem `stat()` per iteration rather than at most ten per second.
- **[BUG] `cli/src/fill/beam_search/evaluation/state_evaluator.py`** — the documented score ranges
  are wrong in both directions. `word_score` is documented `1-100`; computed scores are clamped to
  `[1, 150]` (`word_list.py`) and file-supplied scores are used unclamped, so values above 100 and
  equal to 0 both occur. Reproduce the upper end with:

      python3 -c "import sys; sys.path.insert(0,'cli/src'); from fill.word_list import WordList; print(WordList()._score_word('RELATIONSHIPS'))"

  which prints `121`. `compute_score` is documented `0.0-100.0` and applies no clamp, so it
  inherits the overflow. Separately, `risk_penalty` is documented as a multiplier in `[0.70, 1.0]`
  but is applied once per risky slot without reset, so it compounds — two severe-risk slots give
  0.49.

**[SPEC] `backend/tests/integration/test_theme_priority.py`** — `TestThemeEntriesCLICanary`
carried a `KNOWN BROKEN` note claiming `--theme-entries` does not preserve theme words. The flag
works; the test's fixture was wrong. It built a 5x5 grid with no black squares and asked the flag
to place the 3-letter entry `CAT` at `(0,0,across)`, a 5-letter slot, so the CLI rejected the
entry and the run ended before any locking happened. Fixed by making that slot 3 cells wide.
Confirmed to discriminate: with the flag the fill preserves `CAT`, without it the solver
overwrites row 0. The test is `slow`-marked, so `pytest` deselects it by default
(`pytest.ini:8`) and CI has never run it — that is why a test asserting a false claim about a
working feature survived.

---

## 5. What the sweep did not change, and why

**[SPEC]**
- A figure the test itself measures and asserts is *self-reproducing*: the test is the command
  that reproduces it, so it satisfies the rule in §6. Deleting such a figure would delete a spec.
- Dated historical records are archival. A comment recording what was true on a date is not a
  false claim about today, and must not be "corrected".
- Hypotheticals and worked examples are not assertions about this repo.

**[?] Limits of the 2026-08-16 audit itself.** Recorded because an audit's own output is a claim
like any other:
- The bucket counts in §4 do not sum cleanly: 22 sustained plus 12 overturned is 34, against 35
  FALSE verdicts raised, and at least one site
  (`cli/src/fill/beam_search/beam/manager.py:197`) was adjudicated twice with opposite outcomes.
  Cause: a defect in the audit harness grouped some files under two different path spellings, so
  two independent reviews ran on the same file. The applied edit at that site complies with §6
  under either verdict, but the totals are approximate and should be read as such.
- The agents reported a count of files read and found claim-free that exceeds the number of `.py`
  files that exist under `cli/` and `backend/`. That number is not reliable and is deliberately
  not recorded here.
- The sweep rewrote one docstring into a *new* false claim — asserting that `--theme-entries` had
  been fixed and was covered by a passing canary. Running the canary disproved it (see §4). Every
  claim an audit writes is itself unverified until run.

---

## 6. Standing rule

**[SPEC]**
- A timing or size figure in a comment is only permitted if it names the command that reproduces
  it. Otherwise state complexity, or state nothing.
- Correctness is not sufficient. A figure that is true but names no reproducing command still
  violates this rule, because nothing stops it going stale.
- Never replace a number with a vaguer adjective ("much faster", "very large"). That is the same
  defect with the evidence removed.

---

## 7. Backlog

**[?]**
- Non-Python comment surfaces have not been swept: `src/**/*.{js,jsx}`, `*.scss`, `*.yml`.
- String literals that are user-facing product copy (API response messages, error text) were
  held out of scope. `backend/api/grid_routes.py` asserts a "~16-18%" black-square standard in a
  suggestion message; the figure is conventional crossword guidance but is not sourced anywhere
  in this repo, including `.claude/skills/crossword-domain.md`.

---

## 8. Changelog

- 1.1.0 (2026-08-16) — full sweep of `cli/` + `backend/` Python comments and docstrings;
  22 false claims corrected, 85 unreproducible figures rewritten, 47 left alone; three defects
  recorded as `[BUG]`.
- 1.0.0 (2026-08-15) — created during the docs-overhaul audit; 4 sites fixed, backlog recorded.
