# Documentation Truth Guards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the 2026-09-20 documentation truth pass from a one-off cleanup into a standing rule
set (Tier 1) plus two mechanical predicates (Tier 2), so the claim classes it fixed cannot silently
return.

**Architecture:** Tier 1 amends one existing `.claude/CLAUDE.md` anti-pattern and adds three new
ones. Tier 2 adds two predicates to the **existing** `scripts/docs-check.sh` rather than creating a
sibling script, because that script already owns the live-surface definition, the exclusion regex,
the inline escape hatch, the violation-count pattern and the CI wiring the predicates need.

**Tech Stack:** POSIX-ish bash under zsh, `git ls-files`, `grep -E`; no new dependencies.

**Spec:** *None exists — see "Spec Baseline Exception" below. This plan is the durable record.*

---

## Spec Baseline Exception — read before planning further work on this

`superpowers:writing-plans` requires a plan to derive from a spec. There is no spec for this work.
The decision to build Tier 1 + Tier 2 was ratified by Arthur on 2026-09-20, but that ratification is
recorded **only** in `.handoff/progress.md`, which `.gitignore:123` excludes from the repository.

That is `.claude/CLAUDE.md`'s own "Recording a decision only in auto-memory" anti-pattern one
generalization out: the primary record of a ratified decision sits where `git grep`, the
gitignore-honouring recursive `grep`, `check-guards.sh` and `docs-check.sh` are all structurally
blind to it.

**This plan document is therefore the promoted, tracked primary for Tier 1 and Tier 2.** It is not a
substitute for a spec and does not author new behaviour: every rule below is traceable to the
ratified record or to a measurement cited inline. Where this plan *does* depart from that record, the
departure is called out explicitly in "Corrections to the inherited record" and needs a ruling
before the affected task runs.

## Global Constraints

- Every change must leave `./scripts/docs-check.sh` at rc 0 and `./scripts/check-guards.sh --full-tree`
  at rc 0. Read each rc on its own line from a redirect — not through a pipe.
- `.claude/CLAUDE.md` is itself inside `live_docs()`, so **the Tier 1 entries are scanned by the guard
  they describe.** Any entry quoting a banned figure needs a line-scoped `<!-- docs-check: allow (reason) -->`.
- Do not duplicate the comment block at `scripts/check-guards.sh:121-163`. It is Guard 3's designated
  primary; cite it, never restate it.
- No AI attribution trailers in commits.
- Never push. Stop at the commit.

---

## Corrections to the inherited record

Four claims in `.handoff/progress.md` §"Next session's job" were checked against the tree and do not
hold. Each is corrected here; the corrected value is what the tasks below use.

| # | Inherited claim | Measured | Consequence |
|---|---|---|---|
| C1 | live surface is **18 files** | **17** per `live_docs()`; 18 only if `docs/dev/FABRICATION-LOG.md` is counted, which `docs-check.sh:21` deliberately excludes | Two competing definitions of "the live surface". Tasks reuse `live_docs()`. |
| C2 | predicates measured **236 cited / 35 flagged** on the post-archive surface | `cd75876`'s own message states the archive took cited paths **236 → 147** and dead ones **35 → 19** | The recipe carries **pre-archive** figures. Re-measure; inherit nothing. |
| C3 | "Both land green, so any future firing is signal" | **FALSE — measured 2026-09-20.** Independent re-measurement: predicate 1 **276 cited / 28 flagged / 0 true**; predicate 2 **500 extracted / 64 flagged / 0 true**. Applying every exclusion the recipe names does not reach zero. | Neither predicate lands green. The "Decision" section below applies and blocking is not available as specified. |
| C4 | Tier 2 is a new `scripts/doc-predicates.sh` <!-- docs-check: allow (names the rejected filename; it must not resolve) --> | `docs-check.sh` already owns all five facilities the predicates need | A sibling script gives the live-surface definition two homes, violating Tier 1 rule 3 in the same change set that introduces it. |

`cd75876`'s message also contradicts itself: it states dead paths fell "35 -> 19" while also stating
"19 of the 35 dead path citations were in these eight files", which would leave 16. Neither figure
may be inherited; Task 2 measures.

---

## Tier 1 — five ratified rules become four edits, not five entries

The ratified record lists five rules. Rule 1 is a generalization of an entry that already exists, and
rules 3 and 4 are one family. Adding five entries would put rule 1's content in two places — the
failure rule 3 names.

| Ratified rule | Disposition | Target |
|---|---|---|
| 1. Never write a value a command can produce | **amend** the existing entry | `.claude/CLAUDE.md:63` |
| 2. Cite identifiers, never line numbers | new entry, **scope corrected** (see below) | new |
| 3. One primary per fact | new entry, merged with rule 4 | new |
| 4. Designating a primary is a verification event | merged into rule 3's entry | new |
| 5. A document describing finished work leaves the live tree | new entry | new |

### Rule 2 is false as stated and must be narrowed

`.claude/CLAUDE.md` contains nine line-number citations. Seven of them point at targets with **no
enclosing symbol to cite instead** — a comment block (`scripts/check-guards.sh:121`), `.gitignore`
entries (`:106`, `:123`), a banned figure inside a comment (`docs-check.sh:26`), markdown prose
(`ALGORITHM_DEEP_DIVE.md:287-288`). One pair (`backend/tests/unit/test_routes.py` lines 415 and 655)
is load-bearing *because* the identifier is duplicated — the line number is the only thing that
distinguishes the two `TestFillWithProgress` classes, which is the entire defect.

A rule reading "never line numbers" would flag all nine and be right about at most two, and would be
violated by the file that states it — `CLAUDE.md:193`, "the guard must pass the guard".

**Narrowed form the tasks implement:** cite the identifier **where one exists**; `file:line` is
reserved for targets with no enclosing symbol, and for the case where the identifier is ambiguous by
construction.

---

## Task 1: Tier 1 — amend rule 1's existing entry

**Files:**
- Modify: `.claude/CLAUDE.md:63-65`

**Contract — the amended entry keeps the existing two-line shape:**

```
❌ <trigger> → ✅ <remedy>
Why: <mechanism>, <first-hand evidence>.
```

**Behavioral criteria:**
- The trigger generalizes from the current "counts, timings or `"FIXED"`" to any value a command can
  produce, without losing the existing `docs/dev/FABRICATION-LOG.md` pointer.
- The entry gains one first-hand instance from this session: `cd75876`'s message states dead cited
  paths fell "35 -> 19" and, four lines later, that "19 of the 35 dead path citations were in these
  eight files" — which leaves 16. One commit message, two incompatible numbers, both written by hand
  where a command could have produced one. (The 17-vs-18 surface count is *not* the exhibit to use:
  that is two definitions of the live surface, a different failure.)
- The entry must not quote a figure matching any pattern in `docs-check.sh`'s `BANNED` array, or must
  carry a line-scoped allow comment with a reason.
- Entry stays within the file's existing density — two to five lines, matching its neighbours.

**Normative cases** — the amended entry must satisfy every row:

| condition | required outcome |
|---|---|
| `grep -c 'FABRICATION-LOG' .claude/CLAUDE.md` | ≥ 1 (pointer survives the amendment) |
| `./scripts/docs-check.sh; echo $?` | `0` |
| number of `^❌` lines in the file | unchanged from before this task |

- [ ] **Step 1: Record the pre-state**

Run, reading each rc on its own line:
```bash
grep -c '^❌' .claude/CLAUDE.md
./scripts/docs-check.sh > /tmp/dc-before.log 2>&1; echo "rc=$?"
```

- [ ] **Step 2: Amend the entry**

Rewrite `.claude/CLAUDE.md:63-65` to the contract above.

- [ ] **Step 3: Verify**

```bash
grep -c '^❌' .claude/CLAUDE.md
./scripts/docs-check.sh > /tmp/dc-after.log 2>&1; echo "rc=$?"
./scripts/check-guards.sh --full-tree > /tmp/cg.log 2>&1; echo "rc=$?"
```
Expected: entry count unchanged, both rc `0`.

- [ ] **Step 4: Commit**

```bash
git add .claude/CLAUDE.md
git commit -m "docs(claude-md): generalize the derivable-value rule to any command-producible value"
```

---

## Task 2: Tier 1 — three new anti-pattern entries

**Files:**
- Modify: `.claude/CLAUDE.md` (append three entries to the Anti-Patterns section, before `## Extensibility` at `:246`)

**Interfaces:**
- Consumes: the narrowed rule-2 scope defined above.
- Produces: the rule text Task 4's predicates are justified by; Task 3 cites rule 3 for its placement decision.

**Contract — each of the three entries uses the file's existing shape:**

```
❌ <trigger> → ✅ <remedy>
Why: <mechanism>, <first-hand evidence>.
```

**Behavioral criteria, per entry:**

*Entry A — line citations.* Trigger is citing a line number for a target that **has** a name; remedy
is citing the identifier, with `file:line` reserved for targets with no enclosing symbol. Evidence:
issue #21 cited `state_manager.py:403` for a function that is in fact `cleanup_old_states`; `:403` is
`list_states`' docstring. Mechanism: a line number is invalidated by any edit above it; an identifier
is invalidated only by a rename, which `grep` finds.

**Write this entry naming `cleanup_old_states`, not its current line.** Quoting `:403` is correct —
that is the erroneous citation being reported. Giving the *right* answer as another line number would
violate the rule in the sentence that states it.

*Entry B — primaries.* Trigger is a fact with two homes, **and** designating a primary without
re-deriving its values. Remedy is one primary per fact, treating designation as a verification event.
Evidence: `scripts/check-guards.sh` was designated Guard 3's primary while asserting that `7b0060c`
removed 18 names; it removed 17. Mechanism: a primary carrying a false value is worse than two
copies, because every other site now points at it.

*Entry C — finished work.* Trigger is leaving a document describing completed work on the live
surface; remedy is moving it under `docs/archive/`. Evidence: `cd75876` archived eight completed
plans and the dead-path citations fell without a word of prose being edited. Mechanism: a stale plan
is the document class that most reliably contradicts its own outcome.

**Normative cases:**

| condition | required outcome |
|---|---|
| count of `^❌` lines after this task | exactly three more than after Task 1 |
| each new entry contains the literal `→ ✅` | true |
| `./scripts/docs-check.sh; echo $?` | `0` |
| `./scripts/check-guards.sh --full-tree; echo $?` | `0` |
| Entry A's own text cites a line number | permitted **only** where it names a target with no symbol |

- [ ] **Step 1: Write the three entries**

Append to the Anti-Patterns section, above `## Extensibility`. Match the surrounding entries' density
and voice — read three neighbours first.

- [ ] **Step 2: Self-check Entry A against itself**

Entry A is the one entry whose rule governs its own text. Re-read it and confirm every `file:line` it
contains names a target with no enclosing symbol. If one does not, convert it to an identifier
citation. This is the `CLAUDE.md:193` "the guard must pass the guard" check, applied by hand because
no predicate covers prose.

- [ ] **Step 3: Verify**

```bash
grep -c '^❌' .claude/CLAUDE.md
./scripts/docs-check.sh > /tmp/dc.log 2>&1; echo "rc=$?"
./scripts/check-guards.sh --full-tree > /tmp/cg.log 2>&1; echo "rc=$?"
```

- [ ] **Step 4: Commit**

```bash
git add .claude/CLAUDE.md
git commit -m "docs(claude-md): add line-citation, primary-designation and finished-work rules"
```

---

## Task 3: Tier 2 — predicate 1, cited path resolves

**Files:**
- Modify: `scripts/docs-check.sh`

**Interfaces:**
- Consumes: `live_docs()` (`docs-check.sh:23`) and `EXCLUDE` (`:21`) — reuse, do not re-derive.
  Reusing them is what keeps the live-surface definition single-homed per Task 2's Entry B.
- Produces: `check_cited_paths`, called from the script's main body alongside the existing link and
  banned-claim checks.

**Contract — shell function surface. Input comes from arguments, never from an internal enumeration:**

```bash
check_cited_paths "$@"   # $@ = file paths to scan; appends violations to "$MARKER"
strip_fences <file>      # emits the file with ``` / ~~~ fenced blocks removed
```

`main` calls it as `check_cited_paths $(live_docs)`; `--selftest` calls it with the fixture path.
This matters: `live_docs()` is `git ls-files`, so a temp fixture is invisible to it and a function
that enumerates internally cannot be self-tested. **`docs-check.sh` parses no arguments today and CI
invokes it bare (`test.yml:151`) — bare must remain the default behaviour.**

**Extraction — pinned verbatim. Do not re-derive; the measured counts depend on these exact forms:**

```
# span extraction (both predicates)
`([^`\n]+)`
# predicate 1: the WHOLE span, path-safe charset only
^[A-Za-z0-9_./-]+\.(py|sh|js|jsx|mjs|ts|tsx|yml|yaml|ini|cfg|toml)$
```

The anchored whole-span form is required. The unanchored substring variant extracted 320 and the
"any leading chars" variant 291, both swallowing shell commands
(`` `grep -n 'id:' .pre-commit-config.yaml` ``), globs and ellipsis-truncated paths as if they were
citations. The anchored form measured 276.

**Fenced blocks are stripped before extraction.** The measured numbers assume it. This needs a
line-based state toggle on ``` and `~~~` — `grep` alone cannot track fence state across lines.

**Behavioral criteria:**
- Flags a span when its basename resolves in **no tracked file**.
- Resolution is `git ls-files -- "*/$base" "$base"`, **never a filesystem `find`.** A `find` resolves
  any basename present in a sibling worktree, `node_modules` or build output — `.claude/worktrees/`
  holds a second checkout of this repo, so a doc citing a file deleted on this branch would pass.
  This is the mirror image of predicate 2's stale-`.pyc` hazard; see "Implementation requirement".
- Honours a line-scoped `docs-check: allow` escape hatch. **This is not a shared facility** — the
  hatch is a `grep -v 'docs-check: allow'` inside the BANNED loop at `docs-check.sh:116`, and the
  link check at `:72-82` does not honour it. Each predicate adds its own `grep -v`.
- Emits a `==> Checking cited paths resolve` header, matching `:72` and `:87`.

**Exclusions — shared by both predicates, defined once.** Each removes a measured class; the counts
are predicate 1 / predicate 2 from the 2026-09-20 measurement.

| # | Exclusion | Rule — pinned, not a category | Removes |
|---|---|---|---|
| E2 | `docs/superpowers/plans/` | a plan names files it is about to create; forward reference is what a plan *is*. Self-limiting — Entry C moves each plan off the live surface when done | 12 / 10 |
| E3 | `docs/resources/SOURCES.md` | a bibliography indexing *other* codebases; its filenames and identifiers belong to those repos | 1 / 10 |
| E4 | drop tokens matching `^[0-9a-f]{7,40}$` | predicate 2's pattern matches any commit sha starting with a letter | – / 18 |
| E5 | **predicate 2's search scope is `git grep -F -q -- "$id" -- ':!*.md'`** — the whole tracked tree except Markdown, not `cli backend` | a name defined in `pytest.ini`, `.pre-commit-config.yaml` or `src/` is a real reference, not a dead one. Stated as the search command so two implementers converge; the earlier "stdlib, config keys, external tooling" phrasing was a category nobody could apply | – / 15 |

E2–E3 are file-scoped and apply to both predicates. E4–E5 apply to predicate 2 only.

**E1 was dropped.** Excluding decision tables' "what it beat" columns needs markdown column parsing
in bash and removes exactly one flag (`queue_order`, at
`docs/superpowers/specs/2026-09-07-domain-capabilities-design.md:49`). That one site gets a
`docs-check: allow` instead — the mechanism this ruling chose anyway.

**E5 was verified not to break the positive control.** Broadening the scope could have made
`hamming_distance_at_crossings` resolve somewhere and stop firing. Measured 2026-09-20: it is absent
from the tracked tree outside `*.md` as well as from `cli backend`, so the control fires under both
scopes. Re-run that check if the scope is ever changed again.
- Uses `grep`'s nonzero-on-no-match as control flow — `docs-check.sh:13` sets `-uo pipefail` with
  **no** `-e` precisely for this. Do not add `-e`.

**Normative cases:**

| doc content on a live-doc line | required verdict |
|---|---|
| `` `cli/src/fill/autofill.py` `` | pass — resolves |
| `` `cli/src/fill/inverted_index.py` `` | FLAG — no such file | <!-- docs-check: allow (positive control; must not resolve) -->
| `` `inverted_index.py` <!-- docs-check: allow (known gap, see #C1b) --> `` | suppressed |
| a span inside a `docs/archive/` file | never examined — outside `live_docs()` |
| a span inside a ``` fenced block | never examined — stripped by the fence pre-pass |
| `` `*.py` `` (a glob, not a path) | pass — anchored charset rejects `*` |
| `` `grep -n 'id:' .pre-commit-config.yaml` `` (a command) | pass — anchored charset rejects spaces and quotes |
| a basename present only in `.claude/worktrees/` | **FLAG** — `git ls-files` does not see it |

- [ ] **Step 1: Write the failing check**

Add a fixture doc under a temp path and a `--selftest` branch that asserts the predicate both fires
on a known-dead path and stays silent on a live one. Neither sibling script has a self-test; this one
needs it, because `CLAUDE.md:182` requires measured true/false counts before a guard lands.

- [ ] **Step 2: Run it and confirm it fails for the right reason**

```bash
./scripts/docs-check.sh --selftest > /tmp/st.log 2>&1; echo "rc=$?"
```
Expected: nonzero, because `check_cited_paths` does not exist yet. Confirm the failure is the absent
function, not a broken fixture.

- [ ] **Step 3: Implement**

- [ ] **Step 4: Measure over the real tree before wiring it in**

```bash
./scripts/docs-check.sh --selftest > /tmp/st.log 2>&1; echo "rc=$?"
```
Then count total extracted and total flagged across `live_docs()`, and classify **every** flagged item
TRUE or FALSE by hand. Record both counts in the commit message. A null result here proves nothing
until a positive control fires — run one.

Expect roughly eleven survivors after the exclusions, in the three irreducible classes. If the
number is far off, the exclusions are wrong — diagnose before annotating, because an annotation
hides a bad exclusion permanently.

- [ ] **Step 5: Annotate the irreducible survivors**

For each survivor, read the surrounding prose and confirm the documentation is correct as written.
Then add a line-scoped `<!-- docs-check: allow (reason) -->` naming *which* class it is — negative
assertion, forward reference, or historical record. A survivor that does not fit one of the three is
a **true positive**: fix the doc instead, and say so in the commit message.

- [ ] **Step 6: Wire it in blocking, verify the tree is clean**

```bash
./scripts/docs-check.sh > /tmp/dc.log 2>&1; echo "rc=$?"
```
Expected `0`. A nonzero rc here means an unannotated survivor remains — do not annotate it to make
the gate pass without first applying Step 5's test.

- [ ] **Step 7: Commit**

```bash
git add scripts/docs-check.sh docs/
git commit -m "feat(docs-check): flag cited code paths that resolve nowhere"
```

---

## Task 4: Tier 2 — predicate 2, cited identifier exists

**Files:**
- Modify: `scripts/docs-check.sh`

**Interfaces:**
- Consumes: `live_docs()`, `EXCLUDE`, and Task 3's `--selftest` harness.
- Produces: `check_cited_identifiers`.

**Contract — same argument and fence conventions as Task 3:**

```bash
check_cited_identifiers "$@"   # $@ = file paths to scan; appends violations to "$MARKER"
```

**Extraction — pinned verbatim:**

```
# the WHOLE span must be exactly one identifier token
^[a-z_][a-z0-9_]{4,}$
```

The anchor is load-bearing. The unanchored substring form matched **3016** times — it re-extracts
fragments of every path citation and dotted module path in the corpus — against 500 for the anchored
form. An implementer who drops the `^…$` builds a different guard from the one measured.

**Behavioral criteria:**
- Flags a span when `git grep -F -q -- "$id" -- ':!*.md'` finds nothing (exclusion E5).
- The looser "no surviving `def`/`class`" form is **rejected** — it flagged 136 of 224 on the
  pre-archive surface and is unusable. Do not implement it.
- Applies E2, E3, E4 and its own `grep -v` escape hatch, exactly as Task 3.
- Existence check is `git grep`, **never a filesystem grep.** See "Implementation requirement" —
  this is what makes the positive control fire.

**Normative cases:**

| span | required verdict |
|---|---|
| `` `canonical_words` `` | pass — defined in `cli/src/domain/wordorder.py` |
| `` `hamming_distance_at_crossings` `` | **FLAG — mandatory positive control.** If this does not fire, the predicate is worthless regardless of its false-positive count. |
| `` `queue_order` `` in a decision table's "what it beat" column | suppressed — deliberately names something that does not exist |

- [ ] **Step 1: Extend the self-test with the positive control**

The control must assert that `hamming_distance_at_crossings` flags. Also assert the check is
`git grep`-based: a test that passes under `find -exec grep` has not tested the thing — see
"Implementation requirement" below.

- [ ] **Step 2: Run it; confirm it fails for the right reason**
- [ ] **Step 3: Implement**
- [ ] **Step 4: Measure, classify every flag TRUE/FALSE, record both counts**

Predicate 2's 64 flags were all removable by exclusion — SHAs (18), cross-repo (10), bibliography
(10), config/stdlib vocabulary (17), external tooling (6), decision-table placeholder (1). If
survivors remain after the exclusions, classify before annotating.

- [ ] **Step 5: Annotate any irreducible survivors**, same test as Task 3 Step 5.
- [ ] **Step 6: Wire it in blocking, verify rc 0**
- [ ] **Step 7: Commit**

```bash
git add scripts/docs-check.sh docs/
git commit -m "feat(docs-check): flag cited identifiers absent from cli/ and backend/"
```

---

## Task 5: Retire this plan from the live surface

Entry C in Task 2 says a document describing finished work leaves the live tree. This plan is such a
document the moment Task 4 commits, and it is inside `live_docs()`.

- [ ] **Step 1:** `git mv docs/superpowers/plans/2026-09-20-doc-truth-guards.md docs/archive/completed-plans/`
- [ ] **Step 2:** `./scripts/docs-check.sh > /tmp/dc.log 2>&1; echo "rc=$?"` — expected `0`; the move
      must not break a relative link.
- [ ] **Step 3:** Commit.

Before moving it, promote anything still load-bearing into the entries themselves or into
`scripts/docs-check.sh`'s comment header. Archiving is not a substitute for designating a primary.

---

## Decision required before Tasks 3 and 4 — measured 2026-09-20

Predicate 1: **276 cited / 28 flagged / 0 true.** Predicate 2: **500 extracted / 64 flagged / 0 true.**
`CLAUDE.md:182` rejected a guard at four-to-one false-to-true. These are 28-to-0 and 64-to-0.

### Why tightening extraction cannot fix this

The flags sort into eight classes. Five are removable by extraction rules; **three are irreducible**,
because each is a case where correct documentation *must* name something that does not resolve.

| Class | Count (P1 / P2) | Removable? |
|---|---|---|
| Commit SHAs — `[a-z_][a-z0-9_]{4,}` matches any sha starting with a letter | – / 18 | yes — `^[0-9a-f]{7,40}$` |
| Cross-repo citations (claude-dotfiles, named as such in the citing doc's own table) | 12 / 10 | yes — `docs/superpowers/plans/` exclusion |
| External bibliography (`docs/resources/SOURCES.md` indexes *other* codebases) | 1 / 10 | yes — per-file carve-out |
| Config keys, stdlib and generic vocabulary (`testpaths`, `isabs`, `psutil`) | – / 17 | yes — scope or allowlist |
| Gitignored external tooling (`applied_gate` and friends) | – / 6 | yes — scope |
| **Negative assertions** — the doc's point is that the file is absent: `` `setup.py` `` ×2, `` `.gitlab-ci.yml` ``, and `ARCHITECTURE.md:166`'s four modules under "None of that exists in the shipped tree" <!-- docs-check: allow (this row names absent files in order to explain why naming absent files is correct) --> | ~7 / – | **no** |
| **Forward references** — a spec names modules the build order lists as not-yet-built (C1b, C6) | 3 / – | **no** |
| **Historical records** — `DEVELOPMENT.md:270`'s changelog correctly records a filename fixed at v3.0.0 and deleted afterwards (task #16) | 1 / – | **no** |

Documenting an absence, specifying unbuilt work, and recording history all require naming a
non-resolving thing. No regex distinguishes those from a stale citation, because the difference is in
the surrounding prose, not the span. This is the same structural limit already recorded for the
paraphrase class: "a script can verify every existing citation resolves; no glob finds an absence."

**This section demonstrated the point on itself.** Naming the negative-assertion examples above made
*this plan* flag on predicate 1, and the row needed the very escape hatch the class argues for. That
is the strongest available evidence that the class is irreducible: a document explaining why the
predicate misfires cannot be written without making it misfire.

### Ruled: tighten **and** annotate, then land blocking (Arthur, 2026-09-20)

Both predicates land as blocking checks. Getting there has two halves, and the order matters:

1. **Tighten extraction** — implement the five removable exclusions. Removes 51 of the 92 flags.
2. **Annotate the irreducible sites** — roughly eleven one-time
   `<!-- docs-check: allow (reason) -->` comments at sites that are *correct as written*, using the
   line-scoped hatch that already exists at `docs-check.sh:116`.

Afterwards the predicates read zero and any future firing is genuine signal.

**What this ruling beat.** Landing non-blocking was rejected as deferring the question at the cost of
changing `docs-check.sh`'s exit contract. A checked-in baseline of all 92 was rejected because it
records no reason per site and leaves the three irreducible classes undiagnosed. Parking Tier 2
entirely was rejected despite the 0-true-positive measurement — the value is regression prevention,
which the measurement cannot speak to either way.

**Correction to the number this ruling was taken on.** The ruling was presented with "~11 escape
hatches". Pinning E5 as a search scope rather than a category shows that is too low: E5 resolves 15
of predicate 2's 23 by broadening, leaving 8 (`xfail` ×2, `isabs`, `psutil`, `pstats`, `selftest`,
`page_gate`, plus `queue_order` from the dropped E1). Predicate 1's irreducible survivors are 11
itemized, and agent 2's table leaves ~4 of its 28 un-itemized, so 11–15.

**Day-one hatches are therefore ~19–23, not 11.** The decision does not change — the reasoning that
selected it was about the *kind* of site being annotated, not the count — but the ruling's own
tripwire was written against 11 and would fire on day one. **Revised tripwire: the baseline is
whatever Task 4 Step 6 measures; growth beyond that baseline without true positives following is the
signal to revisit.** Record the measured baseline in Task 4's commit message.

**The accepted risk, recorded so it is not rediscovered as a surprise:** `CLAUDE.md:182` warns that
"a guard noisy enough to distrust only teaches everyone to reach for the escape hatch." The
judgement is that these are not noise-suppression — each marks a site where the documentation is
right and the predicate is wrong, and the hatch's free-text reason makes every one auditable.

## Implementation requirement — both predicates resolve through git, never the filesystem

| predicate | resolution command | what a filesystem check would wrongly resolve |
|---|---|---|
| 1 | `git ls-files -- "*/$base" "$base"` | a basename living only in `.claude/worktrees/`, `node_modules/` or build output |
| 2 | `git grep -F -q -- "$id" -- ':!*.md'` | a symbol surviving only in a stale gitignored `.pyc` |

Both are the same defect: the working directory contains untracked copies of things the branch has
deleted, so "does it exist?" answered against the filesystem answers a different question than the
one the doc's reader is asking.

Predicate 1's case is not hypothetical — the control run for this plan printed
`./.claude/worktrees/decision-primaries/src/components/ThemeWordsPanel.jsx` from a `find`.

Predicate 2's case: a stale gitignored bytecode cache,
`cli/src/fill/beam_search/beam/__pycache__/diversity.cpython-311.pyc`, still contains
`DiversityManager.hamming_distance_at_crossings` from a method that no longer exists in the source.
Any check that reads untracked files finds it and the positive control **silently stops firing**.

This is a trap, because it inverts the repo's other gitignore rule: the re-pin proof mandates
`find -exec grep` over `grep -r` precisely *because* the recursive wrapper honours `.gitignore`. Here
that same wrapper accidentally does the right thing and `find -exec grep` is the wrong tool. Verified
2026-09-20: `git grep` rc=1 (absent, correct); the `.pyc` contains the string twice; `.gitignore:2`
ignores `__pycache__/`.

1. **Tighten extraction until flags reach zero**, then land blocking. Best outcome; cost unknown until
   Task 3 Step 4 classifies the flags and shows whether they share a fixable shape.
2. **Land non-blocking**, borrowing `check-guards.sh`'s `NOTE —` prefix convention
   (`check-guards.sh:212-224`). **Not cheap:** that convention is its sibling's, and `docs-check.sh`
   has no non-blocking class at all — every finding writes to `$MARKER` and drives `exit 1`
   (`:124-129`). This option means adding a second output class and changing that script's exit
   contract. Honest and reversible, but it is a change to the guard's interface, not a flag.
3. **Baseline the current flags** to a checked-in allowlist so only *new* ones fire. Catches
   regressions immediately, but freezes 19+ known-bad citations as permanently acceptable.
4. **Drop predicate 1, ship predicate 2 only**, if the measurement shows their noise differs sharply.

Option 2 is the recommendation absent a measurement that makes 1 reachable.
