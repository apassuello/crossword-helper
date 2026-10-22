# Fresh-install reproduction — design

Ratified in chat by Arthur on 2026-10-22 after an advisor review; the review's three design
changes are folded in (§1.7 tree separation, §2.4 the cache variable, §2.3 the port pre-check).
This file transcribes the ratified design; it does not redesign it. Two additions were made at
plan-writing time and are marked **AMENDMENT** (§3.3) — they await Arthur's review.

## 0. Purpose and scope

A friend installed the app on macOS by following `README.md` and found it unusable: word-list
upload refused "the format of the file content", the list display was unusable (the box not
visible in the window, no scrolling), autofill did not work, and "many, many things" did not work.
Arthur will have them wipe everything and reinstall from scratch, so the target to reproduce is
exactly *fresh macOS, README verbatim*.

This design produces (a) a reproduction run on an environment with nothing installed, exercising
every user-facing capability, and (b) a results log that a later triage sitting turns into issues.

**Reproduce only.** Out of scope: fixing anything; filing issues; the doc-truth Tier 3/4 work;
pause/resume as a *UI* feature — it is not wired (the client methods in `src/api/client.js`
have no caller and `src/components/bench/AutofillPanel.jsx` defers it), so it is a CLI and API
item only.

## 1. Environment

1.1 **Sandbox root.** A directory outside every git checkout, which must outlive two sessions:

```
SB=/private/tmp/crossword-fresh
  $SB/home                 becomes HOME for every sandbox command
  $SB/tools/python         CPython for E1, obtained with uv (uv itself is never on the run PATH)
  $SB/tools/node           Node from the nodejs.org darwin-arm64 tarball (no nvm, no brew)
  $SB/crossword-helper     the E1 clone
  $SB/crossword-helper-e2  the E2 clone
  $SB/fixtures             the word-list upload fixtures (§2.6)
  $SB/evidence             screenshots, logs, measurements
```

1.2 **Clone.** `git clone --branch main` from the local main checkout, never from GitHub. The
log header records the clone's sha and the fact that `origin/main` is still at `2f39949` until
Arthur pushes — the friend's reinstall will get origin.

1.3 **E1 — primary, full walkthrough.** CPython **3.13.7** and Node **22 LTS** (exact version
resolved at run time from `https://nodejs.org/dist/latest-v22.x/` and recorded). A Mac user who
installed Python this year.

1.4 **E2 — floor, setup and CLI smoke only.** The Xcode Command Line Tools interpreter at
`/usr/bin/python3`, which is **3.9.6** on this Mac — the Mac that installed nothing — with the
same Node.

1.5 **Invocation.** Every sandbox command runs under

```
/usr/bin/env -i HOME=$SB/home PATH=<node>/bin:<python>/bin:/usr/bin:/bin:/usr/sbin:/sbin \
    TERM=xterm LANG=en_US.UTF-8 /bin/bash -c '<command>'
```

so it sees the stock bash 3.2.57, no `PYTHONPATH`, no `VIRTUAL_ENV`, no `NODE_OPTIONS`, no
`~/.npm` or pip caches, no global site-packages. `setup.sh` uses no construct beyond bash 3.2
(checked 2026-10-22 by grep for the bash-4-only forms: associative arrays, mapfile and readarray,
case-modification expansions, the |& pipe — none present).

1.6 **Docker control.** `debian:bookworm-slim` with `python3`, `python3-venv` and Node 22 from
nodesource. Run **only** for a setup-phase step that fails in E1, to label the failure
*macOS-only* or *everywhere*. Never the walkthrough.

1.7 **Three trees, never confused.** The main checkout at `/Users/apa/projects/crossword-helper`
is read-only for the QA session and its HEAD is never changed by it. The QA worktree (branch
`qa/fresh-install-2026-10-22`) holds the plan and the results log. The sandbox clones are where
anything runs. Every path in the plan is absolute. No auto-memory writes from the worktree — the
memory store is keyed by cwd and a worktree write lands in an orphan store.

## 2. What gets exercised

2.1 **P0 — README verbatim.** Every command block in Quick Start, Development Mode, CLI Usage and
Running Tests is executed as written, in order, and every factual claim beside them is checked:
the three grid templates, "Frontend built to frontend/dist/", "Open http://localhost:5000", the
Features list, the Resources link.

2.2 **P1 — `./setup.sh`** on E1 and E2: return code, stderr, wall time; afterwards the venv,
`pip list`, `npm ls --depth=0`, and the built `frontend/dist/index.html` are captured.

2.3 **P2 — serve.** Pre-check `lsof -nP -iTCP:5000 -sTCP:LISTEN` first: on macOS the AirPlay
Receiver binds port 5000 when enabled, and `run.py` hardcodes the port. Then `python3 run.py`:
`GET /` is 200 with `<div id="root">`, `GET /api/health` is 200 JSON. Then development mode once
(`npm run dev` with the Flask server up, port 3000 proxying `/api`) to see whether the modes
differ.

2.4 **P3 — UI walkthrough** in the host Chrome, every tool on the tool rail, in this order: Lists
(bugs 2 and 1), Autofill, Grid, then Search, Theme, Import, Export, Clues, and the top bar. At two
viewports: 1440×900 and 1024×768. Clues is a placeholder in `src/App.jsx` and is recorded as
NOT-IMPLEMENTED, not FAIL. **The word-list cache is an explicit variable:** `WordList.from_file`
prefers a sibling `.pkl` whenever its mtime is at least the `.txt`'s, both caches are tracked, and
on a fresh clone both files carry checkout time — so which loader runs is checkout-order luck,
and the tracked caches were built on an earlier Python. Autofill runs three ways: cache as
cloned, cache removed, cache regenerated by `build-cache` under E1's Python.

2.5 **P4 — CLI**, all 15 commands in E1's venv: `--help`, then one realistic invocation each,
the README's five first and verbatim. `fill` also runs the three cache variants of §2.4.
Pause/resume through the file-IPC path.

2.6 **Bug-1 fixtures**, each uploaded through the Lists tool and then read back through
`GET /api/wordlists` and the per-list route: plain LF words · `WORD;50` · `word,50` · CSV with a
`word,score` header · CRLF · the first twenty lines of the shipped `.dict` · non-ASCII (`CAFÉ`) ·
an empty file · the 6,590,415-byte `comprehensive_scored.txt`. For each: what the UI showed, the
request body, status and response from the network log, and what was stored.

2.7 **P5 — API only.** The routes with no UI caller, called with `curl` and the request body
`docs/api/openapi.yaml` documents, expected status taken from the same file.

2.8 **P6 — E2** repeats P1, then `--help` on every command and one `fill` smoke.

2.9 **Declared known findings.** The open issues #18 #19 #20 #21 #26 #28 #29 #36 #37 #38 #39
and the eight code-read discrepancies from the 2026-10-22 inventory are handed to the session as
*expected observations* to confirm, refute and tag — not rediscover.

## 3. Execution rules

3.1 **Session.** A separate Claude Code session, cwd the QA worktree, model Sonnet, tools Bash
plus the Chrome MCP. It executes the plan with `superpowers:executing-plans` — one session, so the
browser and server state carry across tasks.

3.2 **Reproduce only.** No fixes; no edits to code in any of the three trees; no commits other
than the results log and its evidence index on the QA branch; no pushes; no issues filed; no
memory writes.

3.3 **Case record.** Every case records: ID · phase/env/viewport · steps · expected, *quoted* from
`README.md`, `docs/api/openapi.yaml` or the UI's own label, with its source · observed · evidence
path(s) · verdict · severity · known-finding tag. Verdicts: **PASS**, **FAIL**, **BLOCKED** (an
earlier failure prevented the case), **NOT-IMPLEMENTED** (the code or UI says so). **AMENDMENT
(plan-writing, 2026-10-22):** two escape slots, so the schema does not force a judgement the
sources do not support — **UNSPECIFIED** (no README, OpenAPI or UI text states the expectation;
the observation is recorded without a pass/fail) and **NOT-TESTABLE** (no fixture or external
resource exists; the reason is recorded). Severity: **S1** cannot install or run · **S2** a
feature is unusable · **S3** wrong result · **S4** cosmetic.

3.4 **Evidence.** For layout cases a DOM measurement (bounding rect, `scrollHeight`,
`clientHeight`, computed `overflow-y`, viewport size) pasted as JSON, plus a best-effort
`screencapture -x` PNG — if macOS refuses the capture, note it once and continue. For commands,
stdout/stderr and the return code read from a redirect. For HTTP, status and a body excerpt.

3.5 **Failure handling.** A setup-phase failure gets the Docker label (§1.6), then the *minimal*
workaround is applied and recorded as its own finding so the walkthrough still runs. `fill` is
capped at 60 s on the CLI and 3 minutes in the UI; a hang is a FAIL with evidence, never a retry
loop. At most two retries per browser action, then BLOCKED with a note.

3.6 **Ordering and isolation.** The log is written incrementally — each case saved before the
next starts. `pytest` runs alone, never beside the server or the walkthrough.

## 4. Output

4.1 **Results log**, tracked, on the QA branch:

```
docs/dev/qa/2026-10-22-fresh-install-run.md
```

It is a live doc for `scripts/docs-check.sh`, so: every measured value sits in a fenced block
under the command that produced it; prose never restates a count; the log passes `docs-check.sh`
before each commit. The header records the clone sha, the `origin/main` gap, E1/E2 versions and
the macOS version.

4.2 **Evidence** under `$SB/evidence`, copied at close-out to `.handoff/artifacts/2026-10-22-fresh-install/`
(gitignored; screenshots do not belong in git).

4.3 **Close-out.** A verdict/severity summary generated by a command over the log, the
known-finding tags applied, `docs-check.sh` green, final commit, stop. Triage is a separate
sitting with Arthur: cluster, order by severity, he files or allows the issues, and the
post-M1 rows D1/D2/D3 are folded in.

## 5. Artefacts and hand-off

The plan is `docs/superpowers/plans/2026-10-22-fresh-install-reproduction.md`, written with
`superpowers:writing-plans`, on branch `qa/fresh-install-2026-10-22` checked out at
`.claude/worktrees/qa-fresh-install-2026-10-22`. Arthur opens a second Claude Code session in that
worktree on Sonnet and runs `superpowers:executing-plans` on the plan.
