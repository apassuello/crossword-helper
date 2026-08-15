# Fabrication Log

**Version 1.0.0** · docs-overhaul audit · 2026-08-15

---

## AI READING INSTRUCTION

Read `[SPEC]` and `[BUG]` blocks for authoritative facts.
Read `[NOTE]` only if additional context is needed.
`[?]` blocks are unverified.

---

## 1. Purpose

**[SPEC]**
- Record of factual claims found asserted in this repo that were false against the code.
- Scope of the 2026-08 pass: `.md` documentation + the source docstrings confirmed below.
- A **full** docstring audit of `cli/` and `backend/` was NOT performed. Section 4 is the backlog.

**[NOTE]**
This file exists because the 2026-08 audit found that source-code comments carried the *same*
fabrications as the documentation. That breaks the usual tie-breaker — "check the docs against the
code" silently fails when the code's own prose is wrong. Future audits must treat code comments as
claims to verify, not as ground truth.

---

## 2. The originating error

**[SPEC]**
- Claim: the wordlist contains "454k+ words".
- Reality: `data/wordlists/comprehensive.txt` contains **44,024** words (`wc -l`).
- Off by ~10x. Propagated into two `CLAUDE.md` files, `ALGORITHM_DEEP_DIVE.md`, `DEVELOPMENT.md`,
  and three source files, none of which had ever been re-checked against the file.

---

## 3. Fixed in this pass

**[SPEC]**

| File | Line | Was | Now |
|---|---|---|---|
| `cli/src/fill/trie_pattern_matcher.py` | 5 | "10-50x faster pattern matching" | complexity statement, no multiplier |
| `cli/src/fill/trie_pattern_matcher.py` | 23 | "Performance comparison (454k word list)" + per-query ms | complexity + pointer to the benchmark |
| `cli/src/fill/trie_pattern_matcher.py` | 51 | "454k words: ~2-3 seconds" | build-cost note, no figure |
| `cli/tests/performance/benchmark_algorithms.py` | 236 | "full comprehensive ~454k words" | "Full comprehensive wordlist" |

**[NOTE]**
Line 5 was not in the original list of three confirmed sites. It was fixed anyway because leaving
"10-50x faster" four lines above a docstring stating that no timing figures are quoted would have
been self-contradictory — the fix would have introduced a new defect.

---

## 4. Backlog — not audited, do not trust

**[?]**
- `cli/src/fill/pause_controller.py:44` — `# Check at most every 100ms`. Reads like an accurate
  comment on `self._check_interval = 0.1`, but was not verified against runtime behaviour.
- Every other performance/timing claim in `cli/` and `backend/` docstrings. No systematic sweep ran.
- Any remaining "10-50x", "~Nms", or capacity figure in source comments should be treated as
  unverified until measured.

**[SPEC]**
- Rule for future work: a timing or size figure in a comment is only permitted if it names the
  command that reproduces it. Otherwise state complexity, or state nothing.

---

## 5. Changelog

- 1.0.0 (2026-08-15) — created during the docs-overhaul audit; 4 sites fixed, backlog recorded.
