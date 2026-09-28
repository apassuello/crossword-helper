# Governance Recurrence Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Intercept the recurring failure "prose asserts a fact about another artifact, nothing binds them, the artifact moves" at the two points where a mechanism can reach it, and close the open re-pin proof.

**Architecture:** Two probes first, then a gate, then at most two implementations. Phase 1 measures rather than builds, because both candidate mechanisms have an undecided predicate: fix 1's field has no known home until `prepare-handoff`'s emitter is read, and fix 2's matcher has a false-positive source (`refine`, `assess`, `mask`, `pattern` are English words as well as `def`s) that no replay of `7b0060c` would expose. The gate may narrow fix 2 to path-existence only, or drop it.

**Tech Stack:** POSIX sh / bash (guards), Markdown skills (`context-tools` plugin), git, pytest + pre-commit (existing gates).

**Spec:** **None exists.** See *Spec Baseline* below — this is a deliberate, bounded exception, not an omission.

---

## Spec Baseline — read before executing

`superpowers:writing-plans` requires a ratified spec and forbids planning against an unwritten design. There is none here. Rather than invent one, the plan is split:

- **Phase 1 and Phase 3 tasks author no behavior.** They read source, count matches, annotate a gitignored artifact, and run existing gates with existing commands. Nothing in them is a design choice, so they are plannable now and traceable to artifacts that already exist.
- **Phase 2 tasks author behavior** — a new blocking guard and a new handoff field. Their contracts are **deliberately absent**, because T0 and T1 determine them. Writing normative tables for them now would be exactly the failure the rule guards against.

**The gate between phases is a spec-writing step, not a checkpoint.** T2 and T3 do not begin until a spec amendment exists, is committed, and has been reviewed by Arthur.

**Diagnosis this plan implements:** https://claude.ai/artifact/2D7PDGU7cn8MtukvwXdEAW
**Evidence base:** `.handoff/artifacts/2026-09-19-decision-archaeology/` (report §03/§05/§06/§07/§08), `.handoff/2026-09-14-fable-review.md`.

---

## Global Constraints

- **Python floor 3.9** — module-level type aliases use `typing.Union`, never `|`.
- **No AI attribution in commit trailers.** The user-scope `block-claude-coauthor` hook rejects them.
- **Never push.** Arthur performs every remote publish. Stop at the commit.
- **Never `--no-verify`.** Let pre-commit run.
- **No counts, timings or pass rates in docs or docstrings** — `docs-check.sh` enforces this; name the command that proves it instead.
- **A guard's own source is in its own scope.** Any guard added here must pass itself, proven red-then-green **on the tracked file** — `live_code()` enumerates via `git ls-files`, so a `/tmp` copy tests nothing.
- **Quote every glob** in shell commands; zsh aborts the whole command on an unmatched unquoted glob and the abort is only visible on stderr. Never `2>/dev/null` a search whose null you intend to cite.
- **`--cached` precedes the pattern** in `git grep`, or git parses it as a revision and the count silently returns 0 for every input.
- **`\w` is unsupported in `git grep -E`.** Use explicit character classes.
- **Read `$?` on its own line** after redirecting, never after a pipe.

---

## File Structure

| Path | Repo | Responsibility |
|---|---|---|
| `scripts/check-guards.sh` | crossword-helper | Guards 1–3 today; host for fix 2 if the gate approves it |
| `.claude/CLAUDE.md` | crossword-helper | Anti-Patterns section; gains at most one entry |
| `docs/superpowers/specs/2026-09-19-doc-reference-guard.md` | crossword-helper | **New** — the spec T2 needs, written at the gate |
| `.handoff/artifacts/2026-09-19-decision-archaeology/phase1-digest.md` | crossword-helper (gitignored) | Retraction markers (T4) |
| `data/research/.../presentation/_build/applied_gate.py` | crossword-helper (gitignored) | `PIN`; re-pinned once at T6 |
| `plugins/context-tools/scripts/resolve-cursor-citations.sh` | claude-dotfiles | Cursor resolver; has a test harness |
| `plugins/context-tools/scripts/test-resolve-cursor-citations.sh` | claude-dotfiles | That harness — the RED/GREEN precedent for T3 |
| `plugins/context-tools/skills/prepare-handoff/SKILL.md` | claude-dotfiles | Entry emitter; §"Capture verifiable state" :51, §"Optional fields" :111 |
| `plugins/context-tools/skills/catchup/SKILL.md` | claude-dotfiles | Consumer; step 6 already compares a header sha to HEAD |
| `plugins/context-tools/handoff-grammar.md` | claude-dotfiles | Shared field grammar — must stay in sync with both skills |

**No test harness exists for `check-guards.sh`.** Verified: no tracked file *executes* it against fixtures. (An earlier form of this sentence said only the script and `.github/workflows/test.yml` name it; `git grep -l check-guards` returns ten files, including `.pre-commit-config.yaml` and `CONTRIBUTING.md`, which invoke or describe it but do not test it.) T2's RED/GREEN is therefore a staged-fixture cycle, not a test file.

---

# Phase 1 — Probes

Both tasks are reading-sized. Run them **inline**, not via subagent: each returns a number that decides the next step, and a fresh-context agent's report would need re-verification anyway (`feedback_verify_agent_claims`).

### Task 0: Read the handoff toolchain and locate the field seam

**Files:**
- Read: `plugins/context-tools/scripts/resolve-cursor-citations.sh` (claude-dotfiles)
- Read: `plugins/context-tools/skills/prepare-handoff/SKILL.md` §51 "Capture verifiable state (on demand)", §111 "Optional fields"
- Read: `plugins/context-tools/skills/catchup/SKILL.md` step 6 (freshness check) and step 7 (base-branch sanity)
- Read: `plugins/context-tools/handoff-grammar.md`

**Interfaces:**
- Produces: the answers T3's contract is built from. T3 does not start without them.

**Questions this task must answer, in writing:**

1. **Who computes fields?** `Branch:`, `Working tree:` and `Build:` appear in entries. Does `prepare-handoff` instruct the *model* to run commands and transcribe, or does a script emit them? Name the mechanism and the file:line.
2. **Where does `catchup` compare a claimed value to a live one?** Step 6 compares a header sha to `git rev-parse HEAD`. Is that prose instruction or resolver code? If code, which function in `resolve-cursor-citations.sh`?
3. **Is there a project-level extension point?** A cross-project plugin cannot carry a crossword-helper-specific `PIN` grep. Does the toolchain support per-project config, a hook, or a convention (e.g. a repo-local file the skill reads)? If none exists, that absence is the finding.
4. **What does `handoff-grammar.md` require of a new field?** Field naming, required-vs-optional placement, and which of the three documents must be edited together to avoid drift.
5. **What does `test-resolve-cursor-citations.sh` cover, and how is it invoked?** This is the RED/GREEN precedent for T3.
6. **Where does the `[DISTILL]` promotion filter live?** The 08:55Z distill dropped 7 of 21 markers as already covered and merged 4 into 2, so a filter exists somewhere. Name the file that holds it — the `handoff-distill` skill, or `.claude/CLAUDE.md`. This decides T5's single edit target; writing the rule into both is the drift this plan exists to stop.

**Acceptance criteria:**
- Each of the six questions answered with a file:line citation, not a summary.
- Question 3 answered explicitly `yes, <mechanism>` or `no extension point exists` — an ambiguous answer blocks T3.
- No edits to any file. This task is read-only.

**Deliverable:** findings appended to this plan under *Gate Findings* below.

- [x] **Step 1:** Read the four files above, plus whichever file holds the distill filter. Do not skim `handoff-grammar.md` — it is the sync contract.
- [x] **Step 2:** Write the six answers with citations into *Gate Findings*.
- [x] **Step 3:** No commit. This task produces plan text only.

---

### Task 1: Measure the doc-reference matcher before any guard exists

**Files:**
- Read: `scripts/check-guards.sh:121-205` (Guard 3, the pattern being generalized)
- Write: `<scratchpad>/t1-matcher-measurement.md` (not in the repo)

**Interfaces:**
- Produces: the false-positive counts that decide whether T2 exists, and in which of three forms.

**Why this task exists.** Guard 3 matches with `grep -rnw` — bare word-match. That is safe against the research bundle because its citations are distinctive names inside `data-symbol=` attributes. Tracked `.md` is prose, and `cli/src/domain/` defines `refine`, `assess`, `mask`, `restrict` and `pattern`. Deleting `refine` makes it genuinely extinct, and every sentence reading "refine the estimate" would fire. Replaying `7b0060c`'s seventeen removed names **understates** this, because those names are distinctive — so the replay is the second control, not the first.

**Two corpora, both required:**

| Corpus | Definition | What it measures |
|---|---|---|
| **A — saturation control** | Every current `def`/`class` name in `cli/` + `backend/`, dunders excluded, treated as if deleted | The true false-positive baseline |
| **B — historical replay** | The 17 names removed by `7b0060c` | Comparability with Guard 3's published 1-true/0-false figure |

**Two matchers, both required:**

| Matcher | Predicate |
|---|---|
| **word** | Guard 3's current form — the symbol as a whole word, anywhere in the file |
| **backtick** | The symbol inside a backtick span, optionally dot-qualified, terminated by a backtick or an open paren: `` `([A-Za-z_][A-Za-z0-9_]*\.)*SYM(`|\() `` |

**Citation corpus for both:** `git ls-files '*.md'` — explicit file list. Do **not** use `grep -r`; the recursive form is a ugrep wrapper that honours `.gitignore` and would silently skip tracked-but-ignored paths differently than intended.

**Measured drivers (2026-09-19), so the executor sizes this correctly:** corpus A is **2,303** names; the citation corpus is **163** files / **79,060** lines. At that scale the word matcher will produce a large hit count *by construction* — `get`, `run`, `main`, `pattern`, `mask`, `add`, `save`, `load` are all real `def`s and all ordinary English. That is the baseline, not a surprise. **Do not adjudicate per name.** Build one combined pattern per matcher rather than looping 2,303 greps, report the aggregate comparison, and hand-review only the **backtick matcher's hit files** — that set is what a guard would actually block on and is the one unknown here.

**Behavioral criteria for the measurement:**
- Report, per (corpus × matcher), the count of names with ≥1 hit and the total hit count.
- List every hit file for corpus A / backtick, since that set is what a guard would actually block on.
- Separately tally hits whose file is `.claude/CLAUDE.md`, `CONTRIBUTING.md`, or `docs/dev/FABRICATION-LOG.md`. **These name deleted symbols on purpose** — `apply_diversity_bonus`, `get_slot_by_id`, `mutation_gate.py` appear in `Why:` paragraphs by design. They are a distinct false-positive class from the English-word collisions and may warrant an exclusion rather than a rethink.
- Repeat the same two tallies for the **path-existence sibling**: every `[A-Za-z0-9_./-]+\.(py|sh|js|jsx)` path cited in tracked `.md` that does not exist on disk. `scripts/mutation_gate.py` (deleted in `15f1dc1`, named deliberately) is a known member — confirm whether it is the only one.
- Every command that produces a null must be run without `2>/dev/null` and its stderr shown, per Global Constraints.

**Acceptance criteria:**
- A table with all four (corpus × matcher) cells populated, plus the deliberate-mention tally and the path-existence tally.
- The command used for each cell reproduced verbatim, so the numbers are re-runnable.
- **No recommendation in the file.** The probe reports; the gate rules.

- [x] **Step 1:** Extract corpus A. Names only, dunders excluded, sorted unique.
- [x] **Step 2:** Extract corpus B from `git show --stat 7b0060c` / its diff.
- [x] **Step 3:** Run both matchers over both corpora against `git ls-files '*.md'`. Record counts and hit files.
- [x] **Step 4:** Run the deliberate-mention tally and the path-existence tally.
- [x] **Step 5:** Write the table with verbatim commands to the scratchpad file.
- [x] **Step 6:** No commit — the measurement lives outside the repo until the gate rules.

---

# ▸ GATE — spec, then decide

Do not proceed to Phase 2 until all four hold:

1. **T0's question 3 is answered unambiguously.** If no project-level extension point exists, T3's design changes shape entirely (a generic field, or a documented convention rather than a mechanism) and must be re-proposed to Arthur before implementation.
2. **T1's numbers are in front of Arthur**, with the three-way ruling made explicitly: **symbol + path** · **path-only, symbol dropped** · **neither, close fix 2**.
   The repo's own rule governs the ruling — *"adopting a guard because it reads right → run it over the tree and count true vs false before it lands"*, and *"a guard noisy enough to distrust only teaches everyone to reach for the escape hatch."* Scattered false positives mean **rethink, not `docs-check: allow`**.
   No numeric threshold is pinned here on purpose: choosing one is a design decision, and pre-committing to it would be authoring spec inside a plan.
3. **A spec exists** at `docs/superpowers/specs/2026-09-19-doc-reference-guard.md` covering whatever survived — blocking predicate, exclusions, non-coverage, and the measured true/false counts, in the shape of Guard 3's own comment block.
4. **Arthur has reviewed the spec.** Per `superpowers:writing-plans`, an unreviewed amendment is a requirement nobody ratified.

## Gate Findings

### T0 — handoff toolchain (complete, 2026-09-19)

**Q1 · Who computes fields?** *Prose instruction to the model, not a script.*
`skills/prepare-handoff/SKILL.md:51` §"Capture verifiable state (on demand)": *"Run these only for fields you're actually writing, and embed the **actual output** — never paraphrase."* Field list at `:111-117`: `Worktree`, `Branch`, `Base`, `Build`, `Working tree`, `Stash`, `Blockers / waits`.
**The load-bearing consequence:** the never-paraphrase rule already exists, and it binds **fields only**. The 10:29Z failure was a claim in the *cursor*, which the grammar defines as free prose. It was never in that rule's scope.

**Q2 · Where does catchup compare claimed vs live?** *Prose, in the skill body.*
`skills/catchup/SKILL.md` step 6 (freshness check) instructs the model to compare a header sha or `Branch:` field against `git rev-parse HEAD`. Not resolver code. `resolve-cursor-citations.sh` resolves **citations only** — paths, basenames, line liveness — never claimed values.

**Q3 · Project-level extension point?** ***No extension point exists.***
`resolve-cursor-citations.sh` (293 lines, `find_by_name` / `looks_numeric` / `line_text` / `entry_at` / `header_kind` / `cursor_at` / `main`) has no config file, no hook, no project-customization surface. A search for `config|project|hook|custom|extend|source` returns one comment about `~/.claude/projects/` paths and nothing else.
**Per the plan, this blocks T3 as specified.** See *T3 re-proposal* below.

**Q4 · What does a new field require?** *Four-column declaration.*
`handoff-grammar.md` §Consumers is a table whose columns are `prepare-handoff` · `catchup` · `handoff-distill` · `resolve-cursor-citations.sh`, one row per grammar element. Adding an element means adding its row **and** editing each skill the row marks. That table is the sync contract.

**Q5 · Test harness.** `scripts/test-resolve-cursor-citations.sh` (445 lines) — hand-rolled shell: `ok()`/`fail()`/`expect()`/`reject()` helpers at `:18-29`, a fixture log at `:39`, invoked directly. Cases are `# ---` banner-delimited. This is the RED/GREEN precedent for anything touching the resolver.

**Q6 · Where does the `[DISTILL]` filter live?** `skills/handoff-distill/SKILL.md` **Step 2: Filter and classify** (`:34`), with Step 2.5 dedup against existing memory and docs (`:65`).
**Consequence: T5 changes repo.** The rule belongs in `handoff-distill/SKILL.md` Step 2 in **claude-dotfiles**, not `.claude/CLAUDE.md` in crossword-helper.

### T0 finding — the grammar already rejects line-number citations

`handoff-grammar.md:128-135` §Citation: *"A line number may accompany an identifier but never replaces it: an identifier survives edits made above it, `file.py:236` does not. Canonical: `build_system.py` / `_load_section()`. Forbidden: a bare `build_system.py:236`."*

This is the same principle that ruled line-number matching out of T2 — identifiers survive reformats, line numbers don't — reached independently in a different subsystem. Convergent, and worth citing in T2's spec rather than re-deriving.

### T3 re-proposal — for Arthur, per the plan's stop condition

A crossword-helper-specific `Pin:` field cannot land in a cross-project plugin, and no extension point exists to carry it. But Q1 exposed a project-agnostic fix that is strictly better:

> **Extend the "embed the actual output — never paraphrase" discipline from fields to cursor claims.** A cursor sentence asserting the *current value* of something — a pin, a version, a count, a config setting — carries the command output that establishes it, exactly as `Build:` and `Working tree:` already must.

Lands in `handoff-grammar.md` §Cursor block (writer's contract) + `prepare-handoff/SKILL.md` §51. No project specificity, no extension point, no resolver change. Would have caught 10:29Z: *"still off `2bfc2fa` … this session made no commits so the drift is unchanged"* is a value claim with no output behind it, and running `grep ^PIN` to satisfy the rule surfaces `4b3cbf0` immediately.

**Not implemented. Awaiting Arthur's ruling.**

### T1 — matcher measurement (complete, 2026-09-19)

Probe script: `<scratchpad>/t1-probe.sh`, output `<scratchpad>/t1-out.txt`. Corpora: **A** = 2303 current `def`/`class` names in `cli/`+`backend/`, dunders excluded. **B′** = the 15 of `7b0060c`'s 17 removed names that are genuinely name-extinct today. Citation corpus: `git ls-files '*.md'` = 163 files (25 after `docs-check.sh`'s `CODE_EXCLUDE`).

| | word matcher | backtick matcher |
|---|---|---|
| **A** saturation, no exclusion | 492 names / 20363 rows | 366 / 908 |
| **A** saturation, `CODE_EXCLUDE` applied | 252 / 5888 | **213 / 464** |
| **B′** historical replay, no exclusion | 8 / 21 | 8 / 14 |
| **B′** historical replay, `CODE_EXCLUDE` applied | **1 / 1** | **1 / 1** |

**B′ with exclusion is a single row, identical under both matchers:**
`.claude/CLAUDE.md:apply_diversity_bonus` — a deliberate mention inside a `Why:` paragraph.
**That is 0 true positives and 1 false positive.** Guard 3 earned its place at 1 true / 0 false on the same commit. This is the inverse.

#### The finding that closes fix 2's symbol half

The motivating defect was **never detectable by either predicate.** `docs/ALGORITHM_DEEP_DIVE.md:346` pre-fix read:

> `- Diversity metric: Hamming distance at crossing positions between candidate states`

`git show 3a40b28^:docs/ALGORITHM_DEEP_DIVE.md | grep -c 'hamming_distance_at_crossings'` returns **0**. The symbol name appears nowhere in the file. The doc described the *behaviour* in English and never cited the *symbol*, so no symbol-reference guard — word, backtick or otherwise — could have seen it.

This is report §08's structural limit arriving in a new place: *"a script can verify every existing citation resolves; no glob can find a site that should cite a decision and doesn't."* A doc that paraphrases code without naming it is that case exactly.

#### Path-existence sibling — unusable as specified

427 distinct code paths cited in backticks across tracked `.md`; **292 do not resolve from repo root.** That number is a predicate artifact, not a finding: most citations are bare basenames (`autofill.py`, `cli.py`, `App.jsx`) or partial relative paths (`beam_search/state.py`) that exist elsewhere in the tree. Repairing the predicate to "basename resolves anywhere" reintroduces precisely the ambiguity Guard 3's own comment documents — six classes define `order_values` in one file, so a citation of a survivor reads exactly like a true hit.

*(Measurement note: `grep -oH` emitted one `Binary file docs/archive/COMPACTION_GUIDE.md matches` line into the token stream; it falls inside `CODE_EXCLUDE` and affects no excluded-corpus figure.)*

#### Probe's recommendation

**None — per this task's acceptance criteria the probe reports and the gate rules.** The three-way ruling is Arthur's.

---

# Phase 2 — Implementation

**Contracts deferred by design.** Both tasks are dispatched to `implement` agents on **Sonnet, effort medium** (`feedback_orchestrate_dont_edit_inline`; Opus is not warranted — neither is safety-critical nor an ambiguous refactor). Each brief is written from the gate's spec, not from this plan.

### Task 2: The doc-reference guard — ❌ **CLOSED at the gate, 2026-09-19 (Arthur)**

**Ruling: close entirely.** Both the symbol half and the path-existence sibling are dropped. No guard is built.

**Why, so this is not re-derived.** T1 measured the candidate at **0 true / 1 false** on the only historical corpus available, against Guard 3's 1 true / 0 false on the same commit. Decisive beyond the ratio: the defect that motivated the whole fix — `docs/ALGORITHM_DEEP_DIVE.md:346`'s description of `hamming_distance_at_crossings` — was **structurally undetectable**. `git show 3a40b28^:docs/ALGORITHM_DEEP_DIVE.md | grep -c 'hamming_distance_at_crossings'` returns `0`; the line described the behaviour in English and never named the symbol. A symbol-reference guard has no anchor on a doc that paraphrases rather than cites.

**The class this belongs to.** Report §08's structural limit — *"no glob can find a site that should cite a decision and doesn't"* — is not confined to decisions. Prose that paraphrases code is the same unreachable shape. **Documentation-paraphrase drift is now a named member of the out-of-scope set below**, not an open problem awaiting a better predicate.

Applying the repo's own rules: *"adopting a guard pattern because it reads right → run it over the tree and count true vs false before it lands"* — done, and it failed — and *"a guard noisy enough to distrust only teaches everyone to reach for the escape hatch."*

<details><summary>Original contract sketch, retained for the record</summary>

**Files (if it survives the gate):**
- Modify: `scripts/check-guards.sh` (new guard beside Guard 3, sharing its extraction and extinction test)
- Modify: `.claude/CLAUDE.md` — at most **one** Anti-Patterns entry, per fix 3's bar
- Modify: `docs/superpowers/specs/2026-09-19-doc-reference-guard.md` — record the as-built measured counts

**Pinned now, independent of the gate:**
- The guard reuses Guard 3's removed-symbol extraction and its **name-extinction** condition. Extinction is what makes the rule measurable rather than noisy; a form matching the bare identifier fires on three of `7b0060c`'s eighteen names where only one is real.
- The guard's comment block carries what Guard 3's does: genesis, mechanism, **measured true/false counts from T1**, explicit non-coverage, and the `--cached`-before-pattern warning.
- **RED/GREEN is a staged-fixture cycle**, since no harness exists: stage a commit deleting a `def` that a tracked `.md` names under the approved predicate → guard **blocks**; remove the naming → guard **passes**. Proven on the tracked file, never a `/tmp` copy.
- The guard must pass itself. Its own comment block will name symbols to explain the rule — if that trips it, the rule is wrong, not the comment. This is the `ff8e561` lesson: the inverted guard immediately caught the comment written to explain the inversion.

</details>

---

### Task 3: Cursor value-claims carry their output — ✅ **re-proposal ratified, 2026-09-19 (Arthur)**

**Repo:** `claude-dotfiles`, own branch, own commit. Separate from every crossword-helper commit.

**The failure it closes, stated exactly:** the 08:55Z session re-pinned `applied_gate.py` to `4b3cbf0` and did not record it; the 10:29Z session wrote *"still off `2bfc2fa` … this session made no commits so the drift is unchanged."* That is a **sound inference under a wrong model** — `PIN` is gitignored, so "no commits" does not imply "PIN unchanged." The fix must make the writer *run a command* rather than reason, which is why the mechanism matters more than the wording.

**Files:**
- Modify: `plugins/context-tools/handoff-grammar.md` §Cursor block, "Writer's contract" paragraph
- Modify: `plugins/context-tools/skills/prepare-handoff/SKILL.md` §"Capture verifiable state (on demand)" (`:51`)

**Repo:** `claude-dotfiles`, branch `chore/cursor-value-claims`, own commit.

**The rule to add, in the writer's own terms:**
> A cursor sentence asserting the **current value** of something — a pin, a version, a count, a config setting, a file's contents — carries the command output that establishes it, exactly as `Build:` and `Working tree:` already must. Inference from other facts is not output: "no commits landed, so X is unchanged" is a claim about X and needs X's command.

**Behavioral criteria:**
- The rule lives in **both** files and says the same thing in each: `handoff-grammar.md` states it as the Cursor block's writer's contract; `prepare-handoff/SKILL.md:51` states it as an instruction, extending the existing *"embed the actual output — never paraphrase"* sentence rather than duplicating it.
- `handoff-grammar.md`'s §Consumers table gains no new row — this constrains an existing element (cursor block), it does not add one. **Do not invent a new grammar element.**
- No change to `resolve-cursor-citations.sh`, `catchup/SKILL.md`, or `handoff-distill/SKILL.md`. The rule binds the writer; nothing machine-verifies it.
- The worked example is the real one, named as such: the 2026-09-19 10:29Z crossword-helper entry claimed *"still off `2bfc2fa` … this session made no commits so the drift is unchanged"* while `PIN` already read `4b3cbf0`. The inference was sound and the conclusion false, because `PIN` is gitignored and "no commits" does not constrain it.
- **Do not** add a project-specific `PIN` command anywhere. The rule is generic by construction.

**Verification:** prose-only change, no resolver edit, so `test-resolve-cursor-citations.sh` is unaffected — but run it once to confirm it still passes. The substantive proof is that both files state the rule consistently and neither contradicts the existing field guidance.

- [x] **Complete** — `95a2a08` on claude-dotfiles `chore/cursor-value-claims`, *"docs(context-tools): require output for cursor value-claims"*. Two files, +11/−2. `test-resolve-cursor-citations.sh` 78 passed / 0 failed.

**As built, verified against the diff rather than the report:** `handoff-grammar.md` extends the Cursor-block writer's contract in the grammar's descriptive register (*"carries the command output that establishes it … Inference from an adjacent fact is not output"*); `prepare-handoff/SKILL.md:51` extends the existing never-paraphrase sentence in the instruction register, and generalises the motivating case (*"a gitignored file (a `PIN`, for instance) can drift with no commit at all"*) without naming a project-specific command. `§Consumers` intact at 8 data rows, no new element. `resolve-cursor-citations.sh`, `catchup/SKILL.md` and `handoff-distill/SKILL.md` untouched. No AI attribution trailers.

**Review deviation, recorded deliberately:** no task-reviewer subagent was dispatched. The diff is 11 lines of prose, read end to end by the controller and checked against every criterion above. `superpowers:subagent-driven-development` says never skip task review; the user-scope Deliberation Budget says *"already know the answer from reading → don't spawn"* and *"meta-work must cost less than the work it guards."* The Budget governs, per "user instructions take precedence over skills". Flagged to Arthur at the time, not applied silently.

---

# Phase 3 — Hygiene

Independent of the gate. T4 and T5 can run at any time; **T6 runs last, once.**

### Task 4: Retract the overturned findings inside the digest

**Files:**
- Modify: `.handoff/artifacts/2026-09-19-decision-archaeology/phase1-digest.md` (gitignored — **no commit**)

**Why.** The digest's per-record `drift:` flags are Phase-1 raw, not adjudicated. Six records carry `c=YES` and one `a=YES` — the seven raised claims. Four were refuted. Only the `SURVIVING DRIFT FINDINGS` block at the tail says so, 200+ lines later, and report §05 retracts R3 separately. Anyone following the entry's own instruction — *"read the lineage summaries first"* — picks up dead findings as live. This session did exactly that this morning.

**Behavioral criteria:**
- Insert one line immediately beneath the `### [id]` heading of each overturned record.
- Exact marker text: `> **REFUTED** — see report §05 (corrections) / §07 (reconciled). The `drift:` flags below are Phase-1 raw, pre-refutation.`
- Applies to exactly five records:

| record | why overturned |
|---|---|
| `[R3]` | Decision 6's rationale exists in `project_applied_research_capability.md`; the evidentiary finding dissolves (report §05) |
| `[D5]` | Issue #19's body carries the round-trip-cost vs lose-your-place tradeoff verbatim (report §07) |
| `[D10]` | Two deviations reasoned in `a6f8ef2`, one in `e586eae` (report §07) |
| `[19-D4]` | Matches a disclosed carve-out; must not carry the reasoning-lost framing (report §07) |
| `[20-D1]` | Same carve-out (report §07) |

- **Do not** mark `[D7]`, `[D8]` or `[D12]` — those three survived.
- Do not edit the `drift:` lines themselves. The raw Phase-1 verdict is the record; the marker is the adjudication.

- [x] **Step 1:** Insert the five markers.
- [x] **Step 2:** Confirm exactly five `REFUTED` markers and that none sits under D7/D8/D12.
- [x] **Step 3:** No commit — the path is gitignored.

---

### Task 5: Raise the `[DISTILL]` → prose bar

**Files:** *(resolved by T0 question 6 — this task changed repo)*
- Modify: `plugins/context-tools/skills/handoff-distill/SKILL.md` §"Step 2: Filter and classify" (`:34`) — in **claude-dotfiles**, branch `chore/cursor-value-claims`.
- **Not** `.claude/CLAUDE.md`. The filter that already drops and merges markers lives in the distill skill; putting the rule in the project file would place it where the filter cannot read it, and duplicating it into both is the drift this plan exists to stop.

**Behavioral criteria:**
- The rule is added as a classification question inside Step 2's existing filter, not as a new step and not as a preamble.
- It states the honest sizing alongside the rule, so a future reader does not over-apply it: on the 23 entries present at 2026-09-19 it would have redirected roughly 4–5. Its purpose is bounding the growth rate (3 → 23 entries in 34 days against one new guard), not converting a backlog.
- **Do not** retro-apply it to existing entries; that is a separate decision and explicitly out of scope.
- No `[DISTILL]`-marker grammar change — `handoff-grammar.md` §Promotion marker (`:102`) is untouched, and the §Consumers table gains no row.

**The rule, verbatim:**
> A `[DISTILL]` marker becomes a prose entry only when it cannot become a check. Default destination is a guard.

**Honest sizing, to be recorded with the rule:** by the Part 1 classification this would have redirected roughly 4–5 of 23 entries. Its value is bounding the growth rate — 3 → 23 entries in 34 days against one new guard — not converting the backlog.

**Do not** retro-apply it to the existing 23. That is a separate decision and is not in this plan.

- [x] **Complete** — `6b0148f` on claude-dotfiles `chore/cursor-value-claims`, *"docs(context-tools): route DISTILL markers to a check before prose"*. One file, +2. Suite 78 passed / 0 failed.

**As built, verified against the diff:** a classification bullet placed immediately after Step 2's destination table — *"Could this become a check instead of prose?"* — routing a marker to a lint rule, pre-commit hook, guard script or test before prose, with the sizing (~4–5 of the 23 entries at 2026-09-19; purpose is bounding the growth rate, not converting the backlog) and the explicit no-retro-apply note. `handoff-grammar.md` and `prepare-handoff/SKILL.md` untouched, so the branch's two commits stay cleanly separable. Same review deviation as T3, on the same grounds: a two-line prose diff read in full.

---

### Task 6: Re-pin once, prove it, and close the standing note

**Files:**
- Modify: `data/research/deep-research-2026-09/presentation/_build/applied_gate.py` — `PIN` only
- Modify: the 96 reader-facing occurrences, per the standing note's sweep

**Runs last, exactly once.** Spec §11: *"The research bundle's `applied_gate` goes red on the first commit that moves `main` off its `PIN`; it is re-pinned once at session end."* Every commit in Phase 2 re-breaks it, so re-pinning between commits is wasted work.

**Current state, measured 2026-09-19 12:31:** `PIN = "4b3cbf0"` equals HEAD, tree clean, zero `2bfc2fa` occurrences outside the pinned fixture, and the new sha present in exactly the 11 files the standing note enumerates. **The sweep half is already done and proven. The gate half has never been run** — that proof has been open since this morning.

**Acceptance criteria — both required, neither sufficient alone:**
1. The five gates green at the new `PIN`, per the bundle README. `code-verbatim` refetches every code block at `PIN` and compares, so a green gate proves each block's quote at that sha.
2. `grep -rl <old-sha> README.md specs/ presentation/` returns nothing outside `_build/applied/fixtures/`. No gate reads the fragments, so this grep is the only proof for them. The fixture keeps its original sha deliberately and stays excluded.

**Do not** use a whole-tree `git diff` between the two shas as the test — it fires on any commit touching a file the page never quotes. Scope it: `git diff --stat <old> <new> -- cli backend src`.

- [x] **Step 1:** Done — tree clean, HEAD `4cd9fcf`.
- [x] **Step 2:** Done — `PIN = "4cd9fcf"`; 99 occurrences swept across 11 files, fixtures excluded.
- [x] **Step 3:** Done — all five green, each rc read on its own line from a redirect, never off a pipe.
  `selftest` every check fired (delta-chips · delta-digits · research-verbatim · structural · coverage) ·
  `applied` PASS 79 blocks / 135 chips / 6 sections · `page_gate` PASS ×5 · `attribution` PASS · `render` OK ×6.
  Matches the README's recorded landing baseline exactly. `code-verbatim` refetches each block at `PIN`,
  so green here proves every quoted block against the code at `4cd9fcf`.
- [x] **Step 4:** Done — zero `4b3cbf0` outside `_build/applied/fixtures/`.
  **Run with `find … -exec grep`, deliberately not `grep -rl`:** the bundle is gitignored, and the
  recursive `grep` here is a ugrep wrapper honouring `.gitignore`, so the prescribed form would return
  a clean null proving nothing. The fixture keeps its original sha on purpose and stays excluded.
- [x] **Step 5:** Confirmed — no commit; `git ls-files data/research` is empty, which is what makes
  `head != PIN or dirty` satisfiable at `applied_gate.py:395`.

**A termination note, because recording a re-pin is itself a commit.** Writing this section moved the
tree off `4cd9fcf`, so committing it moves HEAD again and the pin goes red again — the standing note's
"red on every commit, by design" applied to the bookkeeping about the re-pin. The regress terminates
because the gate's requirement is `HEAD == PIN` **at gate-run time**, not "PIN names the newest commit
forever". The sequence is therefore: land the last commit, then re-pin to it, then run the gates once.
The shas named in Steps 1–4 above record where the gates were **first** proven green; the final pin is
whatever the last commit of this session is, and is recorded in the gitignored ledger, which can be
updated without producing another commit. Do not read a later HEAD as evidence this step was skipped —
check `PIN` against `git rev-parse --short HEAD` and re-run the five gates.

---

# Owner items — not tasks

These need Arthur, not an implementer.

- ~~**Q1 — wiring trigger for the capability family.**~~ **RULED 2026-09-20 → decision 21 (`df4787e`): intentional, unwired until all six capabilities land.** Spec §12: *"no consumer, no date and no tracked item (decision 8)."* The question is whether that is intentional indefinitely. **Ruling this collapses six of regime B's nine stale rows**, which is why fix 4 waits behind it rather than leading.
- ~~**Fix 4 — default-if-unruled clause on every register row.**~~ **RATIFIED by the owner 2026-09-20 in `.handoff/post-m1-decisions.md`; every open row carries a default and the review date 2026-10-20.** Drafted *after* Q1, against whatever survives. A row with no expiry is a no-op; nine have proven it for a month.
- ~~**Q2**~~ **RULED 2026-09-20 → decision 22 (`20df13c`): the propagator makes `LCVValueOrdering` redundant; it is not ported.** Was coupled to Q1, not adjacent: report §07 gives its third option as *"record that the propagator makes `LCVValueOrdering` redundant, which is decision 6's premise and would settle it."*

---

# Out of scope, stated so it is not mistaken for an oversight

- **Fabricated verifications.** No guard catches an agent writing "verified this session" for a command it never ran — the failure report §05 calls the more dangerous of the two. Current mitigation is a briefing convention: **require the command's output pasted, not the claim**, plus `feedback_verify_agent_claims` and `context-tools:audit-subagent`. Both are advisory and both failed here. Nothing in this plan improves it.
- **Sites that *should* cite a decision and don't.** §08 declines to claim immunity and is right: a script can verify every existing citation resolves; no glob finds an absence. Structurally permanent.
- **Retro-applying fix 3 to the existing 23 anti-patterns.** Separate decision.
- **Regime B's nine rows themselves.** Blocked behind Q1 by the report's own ordering.
