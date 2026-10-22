# Fresh-Install Reproduction Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to run this plan task-by-task in ONE session — the browser tabs and the running server carry across tasks, so a fresh subagent per task would lose them. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproduce, on a macOS environment with nothing installed, every failure a fresh user of this app can hit by following `README.md`, and record each one with evidence in a results log — without fixing anything.

**Architecture:** Three trees that never mix: the main checkout (read-only), this QA worktree (plan + results log), and sandbox clones under `/private/tmp/crossword-fresh` where everything runs under a stripped `env -i` environment. Two environments: E1 (CPython 3.13.7 + Node 22 LTS) carries the full walkthrough; E2 (the Xcode CLT `/usr/bin/python3` 3.9.6) carries setup plus a CLI smoke. The UI is driven in the host Chrome through the Chrome MCP.

**Tech Stack:** bash 3.2, `uv` (download only), nodejs.org tarball, `curl`, `lsof`, `screencapture`, Chrome MCP (`mcp__claude-in-chrome__*`), Docker (conditional control only).

**Spec:** `docs/superpowers/specs/2026-10-22-fresh-install-reproduction-design.md` — every expected value and every rule below traces to a numbered section of it.

## Global Constraints

Copied from the spec; every task's requirements include this section.

- **Reproduce only** (spec §3.2): no fixes; no edits to code in any tree; no commits other than the results log and its evidence index on this branch; no pushes; no issues filed; no auto-memory writes.
- **Three trees** (§1.7): `MAIN=/Users/apa/projects/crossword-helper` is read-only and its HEAD is never changed by this session. `W=/Users/apa/projects/crossword-helper/.claude/worktrees/qa-fresh-install-2026-10-22` is this worktree. `SB=/private/tmp/crossword-fresh` is the sandbox. Every command uses absolute paths. Never `cd` into `$MAIN`.
- **Sandbox invocation** (§1.5): every sandbox command runs through `$SB/e1.sh '<command>'` or `$SB/e2.sh '<command>'` (Task 1 creates them), which exec `/usr/bin/env -i HOME=$SB/home PATH=<node>/bin:<python>/bin:/usr/bin:/bin:/usr/sbin:/sbin TERM=xterm LANG=en_US.UTF-8 /bin/bash -c`.
- **Versions** (§1.3, §1.4): E1 = CPython `3.13.7`, Node `22` LTS (exact patch resolved at run time and recorded). E2 = `/usr/bin/python3` (`3.9.6`), same Node.
- **Case record** (§3.3): every case is appended to the log in the exact block form of Task 0, Step 4, with verdict ∈ {PASS, FAIL, BLOCKED, NOT-IMPLEMENTED, UNSPECIFIED, NOT-TESTABLE}, severity ∈ {S1, S2, S3, S4, —}, known ∈ {`#<issue>`, `I<n>`, —}.
- **Expected is quoted, never invented** (§3.3, §3.4): from `README.md:<line>`, `docs/api/openapi.yaml:<line>` or a UI label. No source → verdict UNSPECIFIED, severity —.
- **Evidence** (§3.4): return codes read from a redirect on their own line (`cmd > file 2>&1; rc=$?`); HTTP status + body excerpt; for layout cases the DOM measurement JSON of Task 6; PNGs via `screencapture -x` best-effort.
- **Caps** (§3.5): CLI `fill` at 60 s unless the README's own command says otherwise; UI autofill 3 minutes; ≤ 2 retries per browser action, then BLOCKED.
- **Incremental log** (§3.6): each case saved before the next starts. `pytest` runs alone (Task 13), never beside a server.
- **Log hygiene** (§4.1): measured values only inside fenced blocks under the command that produced them; prose never restates a count; `scripts/docs-check.sh` rc 0 before every commit — run it from `$W` *after* `git add`, because its `live_docs()` is `git ls-files` and an unstaged file is never scanned.
- **Known findings to tag, not rediscover** (§2.9): `#18` symmetry rule has four implementations (backend vs cli) · `#19` theme suggestions validated against a grid missing the blacks; panel never re-analyses · `#20` Apply-All swallows per-word errors, reports "skipped due to conflicts" · `#21` state-store/pause-flag lifecycle (registry leak, no GC, unvalidated task ids) · `#26` beam search never observes a pause when one iteration outlasts the run · `#28` resumed repair fill cannot be paused · `#29` resume dereferences `result.grid` behind a None check that does not return · `#36` beam exact-resume reachable only via a legacy state file · `#37` adaptive stuck-slot detection dead for repair/beam/hybrid · `#38` resume route reports 200 "Resume completed" when the CLI failed · `#39` `fill` dereferences `result.total_slots` before the None-guard (non-JSON path). Inventory discrepancies (code read 2026-10-22, not executed): `I1` pause/resume has no UI wiring · `I2` Clues tool is a placeholder (`src/App.jsx`, "Arrives in a later task") · `I3` web import stores a `WORD;50` line as the literal word `WORD;50` (`backend/api/wordlist_routes.py` import route uppercases, never splits) · `I4` the two CLI loaders disagree on the `word,50` form (`cli/src/fill/word_list.py` `parse_line` splits `,`; `cli/src/cli.py` `_load_wordlist_words` splits only `;`) · `I5` `url` import returns 501 though `openapi.yaml` documents it · `I6` `/wordlists/import` and `/wordlists/search` share POST with `/wordlists/<path:name>`; precedence unverified at runtime · `I7` `WordList.from_file` prefers the sibling `.pkl` when its mtime ≥ the `.txt`'s · `I8` client methods with no caller: pauseFill, resumeFill, getFillState, listFillStates, deleteFillState, cleanupFillStates, editSummary, normalize, getConstraints, themeValidate, searchWordlists.

---

### Task 0: Preflight and log skeleton

**Files:**
- Create: `docs/dev/qa/2026-10-22-fresh-install-run.md` (the log, `$LOG`)
- Create: `/private/tmp/crossword-fresh/` tree (§1.1)

**Interfaces:**
- Produces: `$LOG` with the header and the P0 claims table; the case block format every later task appends in.

**Behavioral criteria:**
- The session's cwd is `$W` (`git rev-parse --show-toplevel` prints exactly `$W`) and the branch is `qa/fresh-install-2026-10-22`.
- `$MAIN`'s HEAD is recorded and is never changed later; `origin/main` is read with `git ls-remote --heads`, never with `git fetch`.
- The log header carries (§4.1): clone target sha (filled in Task 2), the `origin/main` sha and the sentence "origin/main lags local main until Arthur pushes; the friend's reinstall gets origin", `sw_vers -productVersion`, `/usr/bin/python3 --version`, and placeholders `E1 python: <filled in Task 1>` / `E1 node: <filled in Task 1>` that Task 1 replaces.
- The P0 claims table (§2.1) lists every README claim to be verified, each with the task that verifies it and an empty verdict cell.

- [ ] **Step 1: Confirm the tree and load the browser tools**

```bash
W=/Users/apa/projects/crossword-helper/.claude/worktrees/qa-fresh-install-2026-10-22
MAIN=/Users/apa/projects/crossword-helper
cd "$W" && git rev-parse --show-toplevel && git branch --show-current && git status --short | wc -l
git -C "$MAIN" rev-parse --short HEAD   # record; never change it
git -C "$MAIN" ls-remote --heads origin main
sw_vers -productVersion; /usr/bin/python3 --version; /bin/bash --version | head -1
```

Expected: toplevel is `$W`; branch `qa/fresh-install-2026-10-22`; `0` dirty files. Then `ToolSearch` with `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__read_network_requests,mcp__claude-in-chrome__read_console_messages,mcp__claude-in-chrome__file_upload,mcp__claude-in-chrome__resize_window,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp` and call `tabs_context_mcp` once. If the Chrome extension is not connected, stop and tell Arthur; nothing in P3 can run.

- [ ] **Step 2: Create the sandbox tree**

```bash
SB=/private/tmp/crossword-fresh
mkdir -p "$SB/home" "$SB/tools" "$SB/fixtures" "$SB/evidence" && ls -la "$SB"
```

- [ ] **Step 3: Write the log header**

Create `$LOG` = `$W/docs/dev/qa/2026-10-22-fresh-install-run.md` with: title `# Fresh-install reproduction run — 2026-10-22`; a `## Header` section holding the values from Step 1 in one fenced block (commands and their output), plus the sentence about `origin/main` from the criteria; a `## P0 — README claims` section with this table, verdict cells empty:

| # | README line | Claim (quoted) | Verified by |
|---|---|---|---|
| R1 | 19–21 | `chmod +x setup.sh` / `./setup.sh` is the one-time setup | Task 4 |
| R2 | 23–25 | `source venv/bin/activate` then `python3 run.py` runs the app | Task 5 |
| R3 | 26 | "Open http://localhost:5000" | Task 5 |
| R4 | 46–51 | dev mode: `python3 run.py` + `npm run dev`, open :3000 | Task 5 |
| R5 | 61–62 | `pattern "C?T" -w data/wordlists/comprehensive.txt --json-output` | Task 10 |
| R6 | 64 | "11x11, 15x15, and 21x21 templates included" | Task 2 |
| R7 | 65–67 | the `fill data/grids/example_15x15.json … -t 180 --min-score 30 -o filled.json` command | Task 10 |
| R8 | 70 | `validate puzzle.json` | Task 10 |
| R9 | 73 | `new --size 15 -o puzzle.json` | Task 10 |
| R10 | 76 | `export filled.json --format html -o puzzle.html` | Task 10 |
| R11 | 82–84 | `pytest` runs backend + CLI tests | Task 13 |
| R12 | 86–87 | `npm test` runs the frontend tests | Task 13 |
| R13 | 89–91 | `npm run test:coverage` | Task 13 |
| R14 | 31–32 | "interactive editing with keyboard shortcuts, symmetry enforcement, and auto-numbering" | Task 8 |
| R15 | 33–34 | pattern `C?T` "gives CAT, COT, CUT, etc." | Task 9 |
| R16 | 35–36 | autofill "using CSP with backtracking, beam search, or iterative repair; supports theme word locking" | Task 7 |
| R17 | 37–38 | "ships with 44k curated words; upload your own or combine multiple lists" | Tasks 6, 9 |
| R18 | 39 | "Export -- HTML format" | Task 9 |
| R19 | 66 (setup.sh) | "Frontend built to frontend/dist/" | Task 4 |
| R20 | 105 | the Resources PDF link resolves | Task 2 |

Then a `## Cases` section, empty. Record the README line numbers you actually see — if they differ from the table, correct the table and say so in the header.

- [ ] **Step 4: Pin the case block format**

Add, under `## Cases`, this comment block verbatim; every later case is appended below it in exactly this shape:

```
<!-- case block format — copy exactly
### <ID> — <title>
- Phase: <P0..P6-name> · Env: <E1|E2|host|docker> · Viewport: <1440×900|1024×768|—>
- Steps: 1. … 2. …
- Expected: "<quoted text>" (<README.md:NN | docs/api/openapi.yaml:NN | UI label "…">) — or UNSPECIFIED
- Observed: <one or two sentences; details in the fence below>
- Evidence: evidence/<ID>.png · evidence/<ID>.json · evidence/<ID>.log (whichever exist)
- Verdict: <PASS|FAIL|BLOCKED|NOT-IMPLEMENTED|UNSPECIFIED|NOT-TESTABLE> · Severity: <S1|S2|S3|S4|—> · Known: <#NN|I<n>|—>
(fenced command + output, when there is one)
-->
```

- [ ] **Step 5: Commit the skeleton**

```bash
cd "$W" && git add docs/dev/qa/2026-10-22-fresh-install-run.md && scripts/docs-check.sh > /tmp/dc.log 2>&1; rc=$?; echo "docs-check rc=$rc"; tail -3 /tmp/dc.log
```

Only if `rc=0`: `git commit -m "qa(fresh-install): log skeleton with README claims table"`. Otherwise fix the log and re-run.

---

### Task 1: Build E1 and E2 environments

**Files:**
- Create: `/private/tmp/crossword-fresh/tools/python/…`, `/private/tmp/crossword-fresh/tools/node/`, `/private/tmp/crossword-fresh/e1.sh`, `/private/tmp/crossword-fresh/e2.sh`

**Interfaces:**
- Produces: `$SB/e1.sh '<cmd>'` and `$SB/e2.sh '<cmd>'` — run one bash command string under the respective clean environment (§1.5). Later tasks never invoke `python3`, `node`, `npm` or `./setup.sh` any other way.

**Behavioral criteria (§1.3–§1.5):**
- Under `e1.sh`: `python3 --version` prints `Python 3.13.7`; `which -a python3 node npm` print only paths under `$SB/tools`; `python3 -m pip list` shows at most `pip` (and `setuptools` if bundled); `node --version` prints a `v22.` version; `echo $HOME` prints `$SB/home`; `env | sort` contains exactly `HOME`, `PATH`, `TERM`, `LANG`, `PWD`, `SHLVL`, `_` and nothing else.
- Under `e2.sh`: `python3 --version` prints `Python 3.9.6` and `which python3` prints `/usr/bin/python3`; node as above.
- The Node tarball's SHA-256 is verified against `SHASUMS256.txt` before extraction.
- `uv` appears in no PATH under either script.

- [ ] **Step 1: Obtain CPython 3.13.7 with uv (download only)**

```bash
SB=/private/tmp/crossword-fresh
UV_PYTHON_INSTALL_DIR="$SB/tools/python" uv python install 3.13.7 > "$SB/evidence/ENV-1-uv.log" 2>&1; rc=$?; echo "rc=$rc"; tail -3 "$SB/evidence/ENV-1-uv.log"
ls "$SB/tools/python/"
```

Expected: `rc=0`; one directory named like `cpython-3.13.7-macos-aarch64-none`. Record the exact name as `PYDIR`.

- [ ] **Step 2: Obtain Node 22 LTS from nodejs.org, verify, unpack**

```bash
cd "$SB/tools" && curl -fsSLO https://nodejs.org/dist/latest-v22.x/SHASUMS256.txt
TARBALL=$(grep -o 'node-v22\.[0-9]*\.[0-9]*-darwin-arm64\.tar\.gz' SHASUMS256.txt | head -1); echo "$TARBALL"
curl -fsSLO "https://nodejs.org/dist/latest-v22.x/$TARBALL"
grep " $TARBALL\$" SHASUMS256.txt | shasum -a 256 -c -; echo "shasum rc=$?"
tar -xzf "$TARBALL" && mv "${TARBALL%.tar.gz}" node && ls node/bin
```

Expected: `shasum rc=0` and `…: OK`; `node/bin` contains `node`, `npm`, `npx`. Record `$TARBALL` as the E1 node version.

- [ ] **Step 3: Write the two environment scripts**

Write `$SB/e1.sh` (and `$SB/e2.sh` identical except that its PATH omits the python segment):

```bash
#!/bin/bash
# e1.sh — run ONE command string under the E1 clean environment (spec §1.5)
SB=/private/tmp/crossword-fresh
PYDIR=<the directory recorded in Step 1>
exec /usr/bin/env -i HOME="$SB/home" PATH="$SB/tools/node/bin:$SB/tools/python/$PYDIR/bin:/usr/bin:/bin:/usr/sbin:/sbin" TERM=xterm LANG=en_US.UTF-8 /bin/bash -c "$1"
```

`chmod +x` both.

- [ ] **Step 4: Verify every criterion and record ENV-1 / ENV-2**

```bash
$SB/e1.sh 'python3 --version; which -a python3 node npm; python3 -m pip list; node --version; echo HOME=$HOME; env | sort; command -v uv || echo "uv absent (good)"' > "$SB/evidence/ENV-1.log" 2>&1; rc=$?; echo "rc=$rc"; cat "$SB/evidence/ENV-1.log"
$SB/e2.sh 'python3 --version; which python3 node npm; node --version; echo HOME=$HOME; command -v uv || echo "uv absent (good)"' > "$SB/evidence/ENV-2.log" 2>&1; rc=$?; echo "rc=$rc"; cat "$SB/evidence/ENV-2.log"
```

Append cases `ENV-1` and `ENV-2` to `$LOG` (Phase P-ENV, Env E1/E2); replace the two header placeholders with the recorded versions. Verdict PASS only if every criterion above holds; otherwise FAIL S1 and stop — nothing downstream is a fresh-install measurement without a clean environment.

- [ ] **Step 5: Commit**

`git add` the log, `scripts/docs-check.sh` (read `rc`), then `git commit -m "qa(fresh-install): E1/E2 environments verified"`.

---

### Task 2: Clone and data fidelity

**Files:**
- Create: `/private/tmp/crossword-fresh/crossword-helper` (E1 clone), `/private/tmp/crossword-fresh/crossword-helper-e2` (E2 clone)

**Behavioral criteria (§1.2, §2.1 R6/R20, §2.4):**
- Both clones come from `$MAIN`, branch `main`; the sha is recorded in the log header.
- The clone contains `data/grids/example_11x11.json`, `example_15x15.json`, `example_21x21.json` (R6), `data/wordlists/comprehensive.txt`, `comprehensive.pkl`, `top_100k.pkl`, `comprehensive_scored.txt` (6,590,415 bytes), and `docs/resources/art-of-construction.pdf` (R20).
- The mtimes of `comprehensive.txt` and `comprehensive.pkl` in the fresh clone are recorded to the second — this is the §2.4 cache-preference evidence.

- [ ] **Step 1: Clone twice**

```bash
git clone --quiet --branch main /Users/apa/projects/crossword-helper "$SB/crossword-helper" && git -C "$SB/crossword-helper" rev-parse --short HEAD
git clone --quiet --branch main /Users/apa/projects/crossword-helper "$SB/crossword-helper-e2" && git -C "$SB/crossword-helper-e2" rev-parse --short HEAD
```

- [ ] **Step 2: Measure the shipped data**

```bash
C="$SB/crossword-helper"
ls -l "$C"/data/grids/example_11x11.json "$C"/data/grids/example_15x15.json "$C"/data/grids/example_21x21.json "$C"/docs/resources/art-of-construction.pdf
stat -f '%Sm %N' -t '%Y-%m-%dT%H:%M:%S' "$C"/data/wordlists/comprehensive.txt "$C"/data/wordlists/comprehensive.pkl "$C"/data/wordlists/top_100k.txt "$C"/data/wordlists/top_100k.pkl
wc -c "$C"/data/wordlists/comprehensive_scored.txt
git -C "$C" status --short | wc -l
```

Append `CLONE-1` (clone sha + clean status), `CLONE-2` (R6, R20 — PASS if all files present), `CLONE-3` (the mtime fence; verdict UNSPECIFIED — it is evidence for Task 7/11, not a pass/fail). Fill R6 and R20 in the claims table. Commit as in Task 1 Step 5 with message `qa(fresh-install): clones and shipped-data check`.

---

### Task 3: Fixtures for the word-list upload cases

**Files:**
- Create: `/private/tmp/crossword-fresh/fixtures/F1-plain-lf.txt` … `F9-large.txt`

**Behavioral criteria (§2.6):** the nine files have exactly these contents (`\n` = LF, `\r\n` = CRLF):

| file | contents |
|---|---|
| `F1-plain-lf.txt` | `APPLE\nBERRY\nCHERRY\n` |
| `F2-scored-semicolon.txt` | `APPLE;50\nBERRY;40\nCHERRY;30\n` |
| `F3-scored-comma.txt` | `apple,50\nberry,40\ncherry,30\n` |
| `F4-csv-header.csv` | `word,score\napple,50\nberry,40\n` |
| `F5-crlf.txt` | `APPLE\r\nBERRY\r\nCHERRY\r\n` |
| `F6-dict.dict` | the first 20 lines of `$C/data/wordlists/spreadthewordlist_caps.dict` |
| `F7-nonascii.txt` | `CAFÉ\nNAÏVE\nÜBER\n` (UTF-8) |
| `F8-empty.txt` | zero bytes |
| `F9-large.txt` | a byte-identical copy of `$C/data/wordlists/comprehensive_scored.txt` |

- [ ] **Step 1: Write them with printf / head / cp (not an editor, so line endings are exact)**

- [ ] **Step 2: Verify**

```bash
cd "$SB/fixtures" && wc -c F*.* && file F5-crlf.txt F7-nonascii.txt && xxd F5-crlf.txt | head -2 && cmp F9-large.txt "$C/data/wordlists/comprehensive_scored.txt" && echo "F9 identical"
```

Expected: F5 reported with CRLF line terminators; F7 UTF-8; F8 0 bytes; `F9 identical`. Append `FIX-1` with the fence. No commit needed (fixtures live in the sandbox); the case goes into the next commit.

---

### Task 4: P1 — `./setup.sh` on E1

**Files:**
- Modify (sandbox only): `/private/tmp/crossword-fresh/crossword-helper/` gains `venv/`, `node_modules/`, `frontend/dist/`

**Behavioral criteria (§2.2, R1, R19):**
- The README's two lines are run verbatim under `e1.sh`, from the clone root, with wall time and rc captured.
- Post-conditions recorded: `venv/bin/python --version`, `venv/bin/pip list` (fenced), `npm ls --depth=0` (fenced), `ls -l frontend/dist/index.html`.
- A non-zero rc is FAIL S1, then: run the Docker control of Task 15 for the same step, record its label (macOS-only / everywhere), apply the *minimal* workaround that lets setup finish, and record the workaround as its own case `SETUP-WA-<n>` with what was changed and why (§3.5). Workarounds live only in the sandbox.

- [ ] **Step 1: Run setup verbatim**

```bash
C="$SB/crossword-helper"
( time $SB/e1.sh "cd $C && chmod +x setup.sh && ./setup.sh" ) > "$SB/evidence/SETUP-1.log" 2>&1; rc=$?; echo "rc=$rc"; tail -15 "$SB/evidence/SETUP-1.log"
```

- [ ] **Step 2: Post-conditions**

```bash
$SB/e1.sh "cd $C && venv/bin/python --version && venv/bin/pip list && npm ls --depth=0; ls -l frontend/dist/index.html" > "$SB/evidence/SETUP-2.log" 2>&1; rc=$?; echo "rc=$rc"; cat "$SB/evidence/SETUP-2.log"
```

- [ ] **Step 3: Record and commit**

Append `SETUP-1` (rc, time, stderr excerpt; R1 verdict) and `SETUP-2` (post-conditions; R19 verdict — note that `setup.sh` prints "Frontend built to frontend/dist/": PASS only if the file exists). Fill R1 and R19. Commit `qa(fresh-install): P1 setup on E1`.

---

### Task 5: P2 — serve, both modes

**Behavioral criteria (§2.3, R2, R3, R4):**
- Pre-check: `lsof -nP -iTCP:5000 -sTCP:LISTEN` and `-iTCP:3000` recorded before any server starts. A listener on 5000 that is not ours is a finding `SERVE-0` (FAIL S1, Known —, with the process name) and the AirPlay note.
- Production mode: the README's lines (`source venv/bin/activate` then `python3 run.py`) under `e1.sh`, in the background with its output redirected to `$SB/evidence/SERVE-run.log`. Then: `GET /` → status 200 and the body contains `<div id="root">`; `GET /api/health` → 200 and `Content-Type: application/json`. Status codes are read with `curl -s -o /dev/null -w '%{http_code}'`.
- Dev mode: with the Flask server still up, `npm run dev` in the background (output to `$SB/evidence/SERVE-dev.log`); `GET http://localhost:3000/` → 200; `GET http://localhost:3000/api/health` → 200 (the proxy). Then stop the dev server; **leave the Flask server running** for P3.

- [ ] **Step 1: Port pre-check** — record `SERVE-0`.
- [ ] **Step 2: Start Flask** (Bash `run_in_background`): `$SB/e1.sh "cd $C && source venv/bin/activate && python3 run.py"`. Wait until `curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/api/health` prints `200` or 30 s pass.
- [ ] **Step 3: Probe** — `curl -s -D - http://localhost:5000/ | head -20` and `curl -s -D - http://localhost:5000/api/health`; record `SERVE-1` (R2, R3).
- [ ] **Step 4: Dev mode** — start, probe both URLs, stop `npm run dev`; record `SERVE-2` (R4).
- [ ] **Step 5: Commit** `qa(fresh-install): P2 serve`.

---

### Task 6: P3 — Lists tool (bugs 2 and 1)

**Behavioral criteria (§2.4, §2.6, R17):**
- Browser: a new tab at `http://localhost:5000/`, window resized to 1440×900 with `resize_window`; the Lists tool selected from the tool rail (`ToolRail.jsx` labels it "Lists").
- Layout evidence for every "display" case is the JSON returned by this measurement, run with `javascript_tool` against the element that contains the list rows (locate it with `find`/`read_page`; put its selector in the JSON):

```js
// reference measurement — EL is the list container element you located
(() => { const el = EL; const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
  return JSON.stringify({selector: "<how you found it>", viewport: [innerWidth, innerHeight],
    rect: {x: r.x, y: r.y, w: r.width, h: r.height}, scrollHeight: el.scrollHeight,
    clientHeight: el.clientHeight, overflowY: cs.overflowY, visibleInViewport: r.bottom <= innerHeight && r.right <= innerWidth}); })()
```

  "The box is not visible" (bug 2) is a FAIL when `visibleInViewport` is false or `rect.h` is 0; "can't scroll" is a FAIL when `scrollHeight > clientHeight` and `overflowY` is `visible` or `hidden`, or when a wheel/scroll event does not change `el.scrollTop`.
- Upload evidence for every fixture: the UI's visible response (toast/error text, quoted); the network entry for `POST /api/wordlists/import` from `read_network_requests` (status, request body excerpt, response body excerpt); then `curl -s http://localhost:5000/api/wordlists` and `curl -s http://localhost:5000/api/wordlists/imports/<name>` fenced. Expected for the request shape is `docs/api/openapi.yaml` (the `/wordlists/import` operation — quote its request schema and the 400 text); the *format* behaviour has no documented expectation → verdict UNSPECIFIED with the observation, except F8 (empty) where the OpenAPI 400 text is the expectation.
- Prefer DOM-level actions (`find` → click by ref, `form_input`, `file_upload`) over coordinate clicks; the `computer` tool's coordinates are in screenshot-pixel space.

Cases, in this order:

| ID | what | expected source |
|---|---|---|
| L1 | Lists tool opens; the lists shown equal the names from `GET /api/wordlists` | UI label "Lists"; API |
| L2 | open `top_50k` (or the first shipped list): entries and stats render | UI |
| L3 | measurement JSON at 1440×900; scroll the list with a wheel event; `scrollTop` changes | §2.4 |
| L4 | same at 1024×768 | §2.4 |
| L5–L13 | upload F1…F9 (one case each, `L5`=F1 … `L13`=F9) | openapi `/wordlists/import` |
| L14 | edit an uploaded list (add a word, save) → readback shows it | UI |
| L15 | delete that list → gone from `GET /api/wordlists` | UI |
| L16 | the same L1–L3 once against `http://localhost:3000/` with dev mode up (start it as in Task 5 Step 4, stop after) | §2.3 "whether the modes differ" |

- [ ] **Step 1: Open the tab, resize, select Lists** — screenshot to `$SB/evidence/L1.png` via `screencapture -x` (best-effort).
- [ ] **Step 2: L1–L4** — each with its measurement fence and PNG.
- [ ] **Step 3: L5–L13** — before each upload, reload the page so `read_network_requests` starts clean; after each, capture network + curl readback.
- [ ] **Step 4: L14–L16.**
- [ ] **Step 5: Commit** `qa(fresh-install): P3 Lists` — the log must be saved after *each* case, not only here (§3.6).

---

### Task 7: P3 — Autofill tool (bug 3) with the cache variable

**Behavioral criteria (§2.4, R16):**
- A grid is loaded first through the Import tool from `$C/data/grids/example_11x11.json` (`file_upload`); the grid tool shows an 11×11 grid.
- "Autofill works" means: after Run, a progress indication appears, the run ends within 3 minutes, and every white cell of the grid contains a letter (count via `javascript_tool` over the SVG cells: white cells with empty text = 0). The expectation text is R16.
- Each algorithm offered by the panel is run once on the 11×11 grid; the panel's own option labels are the names recorded.
- Cancel: start a run on `example_15x15.json`, cancel within 5 s; the UI returns to the idle state and no further progress events arrive (`read_network_requests` shows the SSE closed).
- Theme locking (R16 "supports theme word locking"): via the Theme tool upload three words that fit the 11×11 grid, suggest, apply one; then autofill; the applied word is unchanged afterwards.
- Cache variants (§2.4): A9 = default run after `rm $C/data/wordlists/*.pkl` (server restarted so no in-memory cache survives); A10 = after `$SB/e1.sh "cd $C && source venv/bin/activate && python -m cli.src.cli build-cache data/wordlists/comprehensive.txt"` regenerated it (record the command's rc and the new file's size). Record `SERVE-run.log` excerpts for each run — any traceback is evidence.

| ID | what |
|---|---|
| A1 | import `example_11x11.json`; grid renders 11×11 |
| A2 | autofill, panel defaults; filled within 3 min |
| A3 | cancel mid-run on `example_15x15.json` |
| A4…A6 | one run per algorithm option (record the option labels; extend to A7 if there are four) |
| A8 | theme-locked autofill |
| A9 | A2 again with the `.pkl` files removed |
| A10 | A2 again with the cache regenerated |

- [ ] **Step 1: A1–A3.**
- [ ] **Step 2: A4–A6 (A7 if four options).**
- [ ] **Step 3: A8.**
- [ ] **Step 4: A9, A10** (restart the server each time; re-check `/api/health`).
- [ ] **Step 5: Commit** `qa(fresh-install): P3 Autofill`.

---

### Task 8: P3 — Grid tool and top bar

**Behavioral criteria (§2.4, R14):** the UI's own labels are the expectation where the README is silent. Keyboard interaction uses the `computer` tool's `key`/`type` actions on the focused cell.

| ID | what | expected |
|---|---|---|
| G1 | create a new 15×15 grid from the Grid tool (or state NOT-IMPLEMENTED if no control exists; then load `example_15x15.json` via Import) | UI |
| G2 | click a cell, type `CAT` → the three cells show C, A, T; arrow keys move the cursor; Backspace clears | R14 "keyboard shortcuts" |
| G3 | place a black square (find the control or key from the UI; if none is discoverable, FAIL S2 "no discoverable way") | UI |
| G4 | with the symmetry toggle ON, blackening (r,c) also blackens (14−r,14−c); OFF → only (r,c) | R14 "symmetry enforcement" |
| G5 | numbering updates after G3/G4 | R14 "auto-numbering" |
| G6 | top-bar Verify → a result appears; network shows `POST /api/grid/verify-words` 200 | UI label "Verify" |
| G7 | top-bar Clean → `POST /api/grid/clean` 200 and the grid changes or a message says nothing to clean | UI label "Clean" |
| G8 | heatmap toggle changes cell rendering | UI |
| G9 | Save, reload the page → the grid persists | UI label "Save" |
| G10 | health indicator shows the server up; theme toggle flips light/dark and persists across reload | UI |

- [ ] **Step 1: G1–G5.**
- [ ] **Step 2: G6–G10.**
- [ ] **Step 3: Commit** `qa(fresh-install): P3 Grid`.

---

### Task 9: P3 — Search, Theme, Import, Export, Clues

| ID | what | expected |
|---|---|---|
| SR1 | Search tool: pick `comprehensive`, pattern `C?T`, run → results include CAT, COT, CUT | R15 |
| SR2 | the results list scrolls (measurement JSON as in Task 6) | §2.4 |
| SR3 | pattern `ZZQ?X` → an empty-result state, no error | UI |
| SR4 | run with no list selected | UNSPECIFIED |
| TH1 | Theme tool: upload `APPLE BERRY CHERRY` (the tool's own input) → words listed | UI |
| TH2 | Suggest placements → a non-empty list on `example_15x15.json`; network `POST /api/theme/suggest-placements` 200 | UI; Known #19 |
| TH3 | Apply one placement → the word appears in the grid; apply all → observe the error handling | UI; Known #20 |
| IM1 | Import `example_15x15.json` → grid renders | UI |
| IM2 | Import a non-JSON file (`F1-plain-lf.txt`) → an error message, no crash (console clean of uncaught errors via `read_console_messages`) | UI |
| IM3 | Import `nyt_2018_03_09_template.json` → renders | UI |
| EX1 | Export tool → HTML: a file downloads or HTML is shown; open it in a new tab; it renders a grid | R18 |
| CL1 | Clues tool → placeholder text | NOT-IMPLEMENTED (I2) |

- [ ] **Step 1: SR1–SR4.**
- [ ] **Step 2: TH1–TH3.**
- [ ] **Step 3: IM1–IM3, EX1, CL1.**
- [ ] **Step 4: Commit** `qa(fresh-install): P3 Search/Theme/Import/Export/Clues`. Then stop the Flask server (`kill` the background job; confirm `lsof -iTCP:5000` is empty).

---

### Task 10: P4 — CLI, all 15 commands

**Behavioral criteria (§2.5, R5, R7–R10):**
- Everything under `$SB/e1.sh "cd $C && source venv/bin/activate && …"`, exactly as the README says ("Activate the venv first").
- `CLI-help`: `python -m cli.src.cli --help` lists the commands; then `--help` for each of the 15 (`new validate fill show export pattern normalize number analyze build-cache pause resume list-states import-nyt` plus the one the top-level help shows that this list lacks, if any). rc 0 each.
- The README's five commands verbatim, in README order, from the clone root: R5 (`pattern`), R7 (`fill` with `-t 180` — the README's own cap applies, not the 60 s default), R8 (`validate puzzle.json` — run after R9 so the file exists; record that the README orders them the other way), R9 (`new`), R10 (`export`).
- One realistic invocation for each remaining command, inputs chosen from the clone's own files; the plan pins the inputs:

| ID | command |
|---|---|
| CLI-show | `show filled.json` |
| CLI-normalize | `normalize "Hello, World!" --json-output` (if `--help` shows a different argument shape, follow `--help` and record the discrepancy against the README's silence) |
| CLI-number | `number data/grids/example_15x15.json --json-output` |
| CLI-analyze | `analyze data/grids/example_15x15_partial_mid.json -w data/wordlists/comprehensive.txt` |
| CLI-build-cache | `build-cache data/wordlists/top_50k.txt -o /private/tmp/crossword-fresh/top_50k.pkl` |
| CLI-pause/resume | start `fill data/grids/example_15x15.json -w data/wordlists/comprehensive.txt -t 120 --task-id qa1 --state-dir $SB/state --pause-flag-dir $SB/flags` in the background; after 10 s `pause qa1 --pause-flag-dir $SB/flags`; then `list-states --state-dir $SB/state`; then `resume <the state file listed> --state-dir $SB/state --pause-flag-dir $SB/flags -t 60`. Known: #21, #26, #28, #29, #36, #38, #39 — tag whichever reproduces |
| CLI-import-nyt | run `import-nyt --help`; find a tracked fixture with `git -C $C ls-files | grep -i nyt`; if a NYT-format JSON exists use it, else NOT-TESTABLE with the reason |

- [ ] **Step 1: help sweep** → `CLI-help`.
- [ ] **Step 2: R5, R9, R8, R7, R10** in that run order.
- [ ] **Step 3: the remaining commands.**
- [ ] **Step 4: Commit** `qa(fresh-install): P4 CLI`.

---

### Task 11: P4 — `fill` cache variants on the CLI

**Behavioral criteria (§2.4, §2.5):** three runs of `fill data/grids/example_11x11.json -w data/wordlists/comprehensive.txt -t 60 -o /private/tmp/crossword-fresh/fill-<variant>.json --json-output`: `CLI-fill-pkl-cloned` (as cloned), `CLI-fill-pkl-removed` (after `rm $C/data/wordlists/comprehensive.pkl`), `CLI-fill-pkl-rebuilt` (after `build-cache data/wordlists/comprehensive.txt`). Record rc, wall time, and whether the output grid is complete. Before the first run, `grep -n -i 'cache\|pkl' $C/cli/src/fill/word_list.py | head` to find any log line that names which loader ran, and look for it in the output. If the variants differ in rc or completeness, that is a finding tagged `I7`.

- [ ] **Step 1: three runs.**
- [ ] **Step 2: Commit** `qa(fresh-install): P4 fill cache variants`.

---

### Task 12: P5 — API-only routes

**Behavioral criteria (§2.7):** server up again as in Task 5 Step 2. For each route below, build the request body from the schema/example in `docs/api/openapi.yaml` for that operation, call it with `curl -s -D - -H 'Content-Type: application/json'`, and record status + body excerpt; expected status is the first success code the operation documents (quote its line). Routes: `POST /api/normalize` · `POST /api/pattern` · `POST /api/fill` (with `example_11x11` and `timeout` 60) · `POST /api/constraints` · `POST /api/constraints/impact` · `POST /api/theme/validate` · `POST /api/wordlists/search` · `GET /api/wordlists/comprehensive` · `PUT /api/wordlists/qa-put` then `DELETE` it · `POST /api/wordlists/import` with `url` (expect the documented 501, Known I5) · `POST /api/grid/suggest-black-square` · `POST /api/grid/apply-black-squares` · `POST /api/grid/validate` · `POST /api/progress/start`, `GET /api/progress/<id>`, `POST /api/progress/<id>/update` · `POST /api/fill/with-progress` then `POST /api/fill/pause/<id>`, `GET /api/fill/state/<id>`, `POST /api/fill/states`, `POST /api/fill/edit-summary`, `POST /api/fill/resume`, `POST /api/fill/cancel/<id>`, `DELETE /api/fill/state/<id>`, `POST /api/fill/states/cleanup` (Known #21, #38). One case per route, IDs `API-<path with / as ->`.

- [ ] **Step 1: all routes.**
- [ ] **Step 2: stop the server; Commit** `qa(fresh-install): P5 API-only routes`.

---

### Task 13: P0 — Running Tests, alone

**Behavioral criteria (§2.1 R11–R13, §3.6):** no server running (`lsof -iTCP:5000 -iTCP:3000` empty first). Under `e1.sh` from the clone root: `pytest` (R11; record rc and the summary line in a fence — never restate counts in prose), then `npm test` (R12; if it does not exit on its own within 5 minutes it is watch mode — record that as the observation, kill it, and run `npx vitest run` to get a result), then `npm run test:coverage` (R13). If `pytest` or `vitest` is not installed by `setup.sh`, that is the finding (FAIL, S2 against R11/R12), not a reason to install it.

- [ ] **Step 1: pytest.**
- [ ] **Step 2: npm test / coverage.**
- [ ] **Step 3: Commit** `qa(fresh-install): P0 running tests`.

---

### Task 14: P6 — E2 floor

**Behavioral criteria (§2.8):** in `$SB/crossword-helper-e2` under `$SB/e2.sh`: `./setup.sh` as Task 4 (`E2-SETUP-1`, `-2`); `--help` on the top level and every command (`E2-CLI-help`); `fill data/grids/example_11x11.json -w data/wordlists/comprehensive.txt -t 60 --json-output` (`E2-fill`). Same failure handling as Task 4.

- [ ] **Step 1: setup.**
- [ ] **Step 2: help + fill.**
- [ ] **Step 3: Commit** `qa(fresh-install): P6 E2 floor`.

---

### Task 15: Docker control (conditional)

Run only when Task 4 or Task 14 Step 1 failed (§1.6). Purpose: label that one failure *macOS-only* or *everywhere*.

```bash
docker run --rm -v "$SB/crossword-helper-e2:/src:ro" debian:bookworm-slim bash -c '
  apt-get update -qq && apt-get install -y -qq python3 python3-venv python3-pip curl git ca-certificates >/dev/null 2>&1 &&
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null 2>&1 && apt-get install -y -qq nodejs >/dev/null 2>&1 &&
  cp -r /src /work && cd /work && python3 --version && node --version && ./setup.sh' > "$SB/evidence/DOCK-1.log" 2>&1; rc=$?; echo "rc=$rc"; tail -20 "$SB/evidence/DOCK-1.log"
```

Record `DOCK-1` with the label in Observed, and add the label to the failing SETUP case's Observed line. Commit `qa(fresh-install): docker control`.

---

### Task 16: Close-out

**Behavioral criteria (§4.3):**
- The P0 claims table has a verdict in every row.
- Every case block has a `Known:` value; every declared known finding that reproduced is tagged, and the ones that did not are listed under `## Declared findings not observed`.
- `## Summary` holds the output of this command, fenced:

```bash
grep -E '^- Verdict:' "$W/docs/dev/qa/2026-10-22-fresh-install-run.md" | sed -E 's/^- Verdict: ([A-Z-]+) · Severity: ([^ ]+).*/\1 \2/' | sort | uniq -c
```

- Evidence copied: `mkdir -p "$W/.handoff/artifacts/2026-10-22-fresh-install" && cp -R "$SB/evidence/." "$W/.handoff/artifacts/2026-10-22-fresh-install/"` (gitignored; nothing to commit).
- `scripts/docs-check.sh` rc 0 on the staged log; final commit `qa(fresh-install): close-out summary`. Then stop — no triage, no issues, no push.

- [ ] **Step 1: claims table and Known sweep.**
- [ ] **Step 2: summary + evidence copy.**
- [ ] **Step 3: docs-check, commit, stop.**
