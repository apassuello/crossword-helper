# Novice-readiness acceptance run — 2026-10-26

Spec: `docs/superpowers/specs/2026-10-23-novice-readiness-design.md` §6 (0.2.20). Plan: Phase 8 of
`docs/superpowers/plans/2026-10-23-novice-readiness.md`. Case-block format and method from
`docs/dev/qa/2026-10-22-fresh-install-run.md`.

## Header

- Sha under test: `e4e881e` (origin/main after PR #90). Every clone checks out exactly that sha.
- Sha moved (2026-10-26): F-TOUR failed at `e4e881e` (#91); the fix merged as `494ddb8` (PR #92), which also
  carries this branch's Task 8.1 README, so README and code under test are one sha from here. The 8.3 rows
  above ran on `e4e881e`; F-TOUR's re-run and every row after it run on a fresh clone of `494ddb8`
  (`clone2-494ddb8.txt`, `setup.sh` rc 0 in `SETUP-494ddb8.log`).
- F-WORKFLOW theme list (owner 2026-10-26): a list whose Apply All placements do not abut each other, so the
  workflow past autofill is exercised; the first list (PUZZLE/CROSSWORD/ANAGRAM) hits #19 defect 3, shown in
  F-TOUR's re-run. The list was chosen by an API dry run of suggest + apply against the black pattern, not by
  a browser run, so the 127.0.0.1:5000 storage was untouched.
- Export downloads (owner 2026-10-26): allowed for F-WORKFLOW and F-EXPORT; each file is copied into the
  evidence dir and compared with the grid.
- Platform: macOS only, on this Mac, sandboxed (owner 2026-10-25; spec 0.2.20). E1 = Homebrew `python3` and
  `node`/`npm`/`npx`, reached through `$SB/bin` (symlinks to those four binaries only) under `env -i` by
  `$SB/e1.sh`. Under E1, `pip3` resolves to `/usr/bin/pip3`, since `$SB/bin` links no `pip3`; ENV-1 probe in
  the evidence dir (`env1-probe.txt`).
- README under test for F-TOUR and F-WORKFLOW: this branch's `README.md` (Task 8.1, docs-only on top of
  `e4e881e`); the code under test is `e4e881e`.
- Viewport method (ENV-3): functional cases run top-level on `http://127.0.0.1:5000`; layout cases are measured
  inside a same-origin iframe sized exactly 1440×900 and 1024×768, reading the iframe's own
  `innerWidth`/`innerHeight`, as L3 and L4 of the 2026-10-22 run did.
- Evidence: `.handoff/artifacts/2026-10-26-novice-readiness/` in the main checkout (gitignored).
- 5xx oracle (owner 2026-10-26, over the plan's "read with the browser tool's ... network logs"): the E1 server's
  request log is the source for 5xx counts; the browser tool's count is pasted beside it. Reason: on F-TOUR the
  browser tool logged a 503 for an SSE request the server log records as 200 (1 of 2 searches); see F-TOUR.
- Before the run (Task 8.2 Step 2b): the browser storage of `http://127.0.0.1:5000` and `http://localhost:3000`
  was backed up to the evidence dir and cleared; `4678406` was cloned, set up under E1, served, and one grid
  saved; its folder was then deleted and the browser storage kept (`old-setup.log`, `clean-prev-old-storage.json`,
  `clean-slate.txt`). Fixture F7 rebuilt (`FIX-F7.txt`).

```
$ git rev-parse --short origin/main
e4e881e
$ git ls-remote --heads origin main
e4e881e57e273bbcfaaf7193dfedc7c6fc550af8	refs/heads/main
$ git -C <clone> rev-parse --short HEAD
e4e881e
$ sw_vers -productVersion
26.5.2
$ /bin/bash --version | head -1
GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25)
$ e1.sh "python3 --version; node --version; npm --version"
Python 3.14.3
v26.7.0
11.19.0
$ readlink $SB/bin/python3 $SB/bin/node
/opt/homebrew/bin/python3
/opt/homebrew/bin/node
```

## Coverage

One row per §6 Area, copied from the spec by command; Verdict filled by Tasks 8.3–8.7.

| Area | Verdict | Cases run |
|---|---|---|
| Install | PASS | SETUP-1, SETUP-2, SETUP-3, SERVE-1 |
| New: ZIP | PASS (README `analyze` example: UNSPECIFIED) | ZIP, ZIP-analyze |
| Grid | PASS on `494ddb8` | G1, G3, G8, G9 |
| New: SAVE-NAMED | PASS on `494ddb8` | SAVE-NAMED |
| Grid guards | PASS on `494ddb8` | SR-PLACE, CL-CLEAR |
| New: CL-CLEAN-GUARD | PASS on `494ddb8` | CL-CLEAN-GUARD |
| New: PORT | PASS | PORT |
| New: SETUP-MISSING | PASS | SETUP-MISSING |
| New: CLEAN-PREV | PASS | CLEAN-PREV |
| New: MACOS | PASS | MACOS |
| New: F-WORKFLOW | PASS on `494ddb8` | F-WORKFLOW |
| New: F-TOUR | PASS on `494ddb8` (FAIL on `e4e881e`, #91) | F-TOUR, F-TOUR re-run |
| New: F-IMPORT | PASS on `494ddb8` | I1, I2, I3, I4, I5, I6 |
| New: F-EDIT | PASS on `494ddb8` | E1, E2, E3, E4, E5, E6, E7, E8, E9, E10, E11 |
| New: F-THEME-LOAD | PASS on `494ddb8` | T1, T2, T3 |
| New: F-LISTS | PASS on `494ddb8` (default-selection wording: ruling asked) | L1, L2, L3, L4, L5, L6, L7 |
| New: F-SEARCH | PASS on `494ddb8` | S1, S2, S3, S4 |
| New: F-EXPORT | PASS on `494ddb8` (HTML and Text on manual export; automated clicks saved no file, instrument fault) | X1, X2, X3, X4, X5, X6, X7 |
| New: F-RESTORE | PASS on `494ddb8` | R1, R2 |
| New: F-FEEDBACK | | |
| Hidden | PASS on `494ddb8` (#53 and #54 still open though their symptoms are gone) | CL1, A-SBS, EXPORT-HIDE |
| New: TH2b | | |
| New: TH3 | | |
| New: TH4 | | |
| New: TH5 | | |
| New: UNDO | | |
| Autofill | | |
| Lists, CLI | | |
| New: AF-LOCK | | |
| New: AF-BLOCK | | |
| New: AF-BLOCK-LEN | | |
| New: AF-DEFAULTS | | |
| New: AF-SUB2 | | |
| New: AF-REFILL | | |
| New: AF-LOCKED-CROSS | | |
| New: AF-GATE | | |
| New: AF-OFFLIST | | |
| New: AF-NOLISTS | | |
| New: AF-VERIFY-STALE | | |
| New: AF-SAVE-RUN | | |
| New: SAVE-SIZE | PASS on `494ddb8` | SAVE-SIZE (Open saved and reload) |
| New: SAVE-TABS | PASS on `494ddb8` | SAVE-TABS |
| New: PROV-SAME | | |
| New: FULL-GRID | | |

## Cases
### MACOS — setup.sh under macOS bash 3.2, wheels on Python 3.14, :5000 before any server
- Phase: 8.3 · Env: E1 · Viewport: —
- Steps: 1. `lsof` of :5000. 2. `head -1 setup.sh`, `/bin/bash --version`, `bash` as E1 resolves it. 3. SETUP-1 with its output kept, `grep -c 'Building wheel'` on it. 4. Because `setup.sh:83` runs `pip install ... --quiet`, which hides pip's build lines, the grep is vacuous: also `pip install --dry-run --ignore-installed --only-binary=:all: -r requirements.txt`, with the control `--only-binary=:all: pyyaml==5.3.1` (no 3.14 wheel), and a verbose reinstall's build-line count.
- Expected: `head -1 setup.sh` and `/bin/bash --version` pasted and setup completes under that bash; `grep -c 'Building wheel'` reads 0 (wheels only); `lsof` of :5000 pasted, and where :5000 is free the log says the in-use path is covered by PORT
- Observed:

```
$ lsof -nP -iTCP:5000 -sTCP:LISTEN
lsof rc=1
$ head -1 setup.sh
#!/usr/bin/env bash
$ /bin/bash --version
GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25)
$ e1.sh "command -v bash; bash --version | head -1"
/bin/bash
GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25)
$ grep -c 'Building wheel' SETUP-1.log
0
$ pip install --dry-run --only-binary=:all: -r requirements.txt (tail)
Would install Flask-3.0.0 Flask-Cors-4.0.0 Jinja2-3.1.6 MarkupSafe-3.0.4 PyYAML-6.0.3 Pygments-2.21.0 Werkzeug-3.1.9 black-26.10.1 blinker-1.9.0 certifi-2026.10.23 cfgv-3.5.0 charset-normalizer-3.5.2 click-8.1.7 coverage-7.17.0 distlib-0.4.4 execnet-2.1.2 filelock-4.2.4 flake8-7.4.1 identify-2.6.20 idna-3.20 iniconfig-2.3.1 isort-9.0.2 itsdangerous-2.2.0 markdown-it-py-4.2.0 mccabe-0.7.0 mdurl-0.1
$ control: --only-binary=:all: pyyaml==5.3.1
ERROR: Could not find a version that satisfies the requirement pyyaml==5.3.1 (from versions: 6.0.3)
ERROR: No matching distribution found for pyyaml==5.3.1
$ verbose reinstall, lines matching 'Building wheel|Running setup.py'
0
```

- Evidence: `MACOS-pre.txt`, `SETUP-1.log`, `MACOS-wheels-only.log`, `MACOS-wheels-only-control.log`, `MACOS-verbose-buildcount.txt`
- Verdict: PASS · Severity: — · Known: instrument: the spec's `grep -c 'Building wheel'` cannot fail under `setup.sh`'s `--quiet`; the wheels-only dry run, which its control shows can fail, carries the criterion. `:5000` is free on this Mac (`lsof` rc=1), so the in-use path is covered by PORT. The verbose reinstall replaced the venv's packages with the same versions.

### SETUP-1 — setup.sh on a fresh clone under E1
- Phase: 8.3 · Env: E1 · Viewport: —
- Steps: `$SB/e1.sh "cd <clone> && chmod +x setup.sh && time ./setup.sh"`, exit code read on its own line.
- Expected: Setup completes
- Observed:

```
  Terminal 2: npm run dev
  Then open http://localhost:3000

real	0m7.123s
user	0m6.585s
sys	0m2.778s
SETUP-1 rc=0 (read on its own line, see the session's command output)
```

- Evidence: `SETUP-1.log`
- Verdict: PASS · Severity: — · Known: 7.1 s real: the pip and npm caches in `$SB/home` came from the previous install (Task 8.2 Step 2b), as a friend's home keeps them

### SETUP-2 — installed environment
- Phase: 8.3 · Env: E1 · Viewport: —
- Steps: `venv/bin/python --version`, `venv/bin/pip list`, `npm ls --depth=0`, `ls -l frontend/dist/index.html`.
- Expected: venv, Python packages, node modules and the built frontend exist
- Observed:

```
$ venv/bin/python --version
Python 3.14.3
$ python3 --version (E1)
Python 3.14.3
crossword-helper@1.0.0 /private/tmp/claude-501/-Users-apa-projects-crossword-helper/***/scratchpad/p8sb.Y6J6/e1/crossword-helper
$ ls -l frontend/dist/index.html
-rw-r--r--@ 1 apa  wheel  1107 Oct 26 08:42 frontend/dist/index.html
```

- Evidence: `SETUP-2.txt`
- Verdict: PASS · Severity: — · Known: —

### SETUP-3 — the tree stays clean
- Phase: 8.3 · Env: E1 · Viewport: —
- Steps: `git status --short` and `git diff --stat` in the clone after setup.
- Expected: both empty
- Observed:

```
$ git status --short
$ git diff --stat
end
```

- Evidence: `SETUP-3.txt`
- Verdict: PASS · Severity: — · Known: —

### SERVE-1 — the app serves with debug off
- Phase: 8.3 · Env: E1 · Viewport: —
- Steps: `source venv/bin/activate`, `python3 run.py` in the background, `curl` of `/` and `/api/health`, the server banner.
- Expected: 200 with `<div id="root">`; health ok; no "Debugger is active", no PIN
- Observed:

```
$ curl -s -o /dev/null -w %{http_code} http://127.0.0.1:5000/
200
$ curl -s http://127.0.0.1:5000/ | grep -c "<div id=\"root\">"
1
$ curl -s http://127.0.0.1:5000/api/health
{"architecture":"cli-backend","components":{"api_server":"ok","cli_adapter":"ok"},"status":"healthy","version":"2.0.0"}

$ server banner
 * Serving Flask app 'backend.app'
 * Debug mode: off
[31m[1mWARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.[0m
 * Running on http://localhost:5000
[33mPress CTRL+C to quit[0m
127.0.0.1 - - [26/Oct/2026 08:43:17] "GET /api/health HTTP/1.1" 200 -
127.0.0.1 - - [26/Oct/2026 08:43:17] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [26/Oct/2026 08:43:17] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [26/Oct/2026 08:43:17] "GET /api/health HTTP/1.1" 200 -
$ grep -cE "Debugger is active|Debugger PIN" banner
0
```

- Evidence: `SERVE-1.txt`
- Verdict: PASS · Severity: — · Known: —

### CLEAN-PREV — fresh install over a cleaned previous install
- Phase: 8.3 · Env: E1 · Viewport: —
- Steps: Task 8.2 Step 2b (storage of 127.0.0.1:5000 and localhost:3000 backed up and cleared; `4678406` set up, served, one grid `OLDSAVE` saved; its folder deleted, browser storage kept), then the fresh clone, SETUP-1, SERVE-1, and the app opened at `http://127.0.0.1:5000` with console tracking started before the load.
- Expected: Setup builds a new `venv/` whose `venv/bin/python --version` equals E1's `python3 --version`; `which -a python3 node npm npx pip3` under E1 pasted; the app loads with no blank page and its console-error count pasted; each of the old version's saved entries opens or is reported in a plain message, never a crash
- Observed:

```
== which -a python3 node npm npx pip3
$SB/bin/python3
/usr/bin/python3
$SB/bin/node
$SB/bin/npm
$SB/bin/npx
/usr/bin/pip3
which rc=0
$ venv/bin/python --version
Python 3.14.3
$ python3 --version (E1)
Python 3.14.3
home = /opt/homebrew/opt/python@3.14/bin
version = 3.14.3
executable = /opt/homebrew/Cellar/python@3.14/3.14.3_1/Frameworks/Python.framework/Versions/3.14/bin/python3.14
old storage keys (4678406): ["crossword_saved_grid","xw_theme","crossword_symmetry_enabled"]
new storage keys after load (e4e881e): ["crossword_saved_grids","xw_theme","crossword_symmetry_enabled"]
banner: Restored "Saved grid" (saved 2026-10-26 08:37); Open saved row: Saved grid 15×15 · 2026-10-26 08:37 Open Delete; grid shows OLDSAVE
console errors from load: 0 (read_console_messages, onlyErrors, tracking started before navigation)
```

- Evidence: `old-setup.log`, `clean-prev-old-storage.json`, `clean-slate.txt`, `env1-probe.txt`, `SETUP-2.txt`, `CLEAN-PREV-venv.txt`, `clean-prev-new-storage.json`, `CLEAN-PREV-restored.jpg`, `old-serve.log`
- Verdict: PASS · Severity: — · Known: the old version saved under `crossword_saved_grid` (singular); the new one migrated it into `crossword_saved_grids` and removed the old key. `pip3` under E1 is `/usr/bin/pip3` (only four tools are linked); setup never calls it. The old version served with the Werkzeug debugger on (`old-serve.log`: `Debugger is active!`).

### ZIP — a Download-ZIP extract, following the README
- Phase: 8.3 · Env: E1 · Viewport: —
- Steps: `git archive --format=zip` of `e4e881e`, `unzip` into an empty directory, `chmod -x setup.sh`, then the README's `chmod +x setup.sh && ./setup.sh`, its `pattern` and `fill` examples verbatim, `python3 run.py`, and in the browser Search `C?T`.
- Expected: Setup completes; the examples run; Search for `C?T` returns CAT, COT and CUT; `chmod +x` alone is enough
- Observed:

```
$ ls -l setup.sh (as extracted)
-rwxr-xr-x  1 apa  wheel  3972 Oct 26 08:23 $SB/zip/extract/crossword-helper-e4e881e/setup.sh
$ chmod -x setup.sh (GitHub ZIP does not reliably keep the mode)
ZIP setup rc=0
pattern rc=0
fill rc=0
-rw-r--r--  1 apa  wheel  2734 Oct 26 08:44 $SB/zip/extract/crossword-helper-e4e881e/filled.json
pattern: CAT/COT/CUT hits in the JSON output: CAT=1 COT=1 CUT=1
browser Search C?T: 7 results, CAT, COT and CUT present (DOM read of `.result-item`)
```

- Evidence: `ZIP.txt`, `ZIP-setup.log`, `ZIP-pattern.txt`, `ZIP-fill.txt`
- Verdict: PASS · Severity: — · Known: `ZIP.txt` also holds a traceback from my own result parser (the last output line is not JSON); the raw output was read instead

### ZIP-analyze — the README `analyze` example
- Phase: 8.3 · Env: E1 · Viewport: —
- Steps: Look for an `analyze` example in README "CLI Usage".
- Expected: the spec's ZIP row names a README `analyze` example
- Observed:

```
README "CLI Usage" examples: pattern, fill, validate, new, export. `git log -S'cli.src.cli analyze' -- README.md`: no commit.
```

- Evidence: README.md
- Verdict: UNSPECIFIED · Severity: — · Known: the spec row names an example the README never had; reported to Arthur

### PORT — PORT, a port in use, and the Vite proxy
- Phase: 8.3 · Env: E1 · Viewport: —
- Steps: (a) hold :5000, `PORT=5057 python3 run.py`; (c) `PORT=5057 npm run dev`, `curl :3000/api/health`; (b) hold 5057, `PORT=5057 python3 run.py`, plainly and with `FLASK_DEBUG=1`.
- Expected: the app serves on the other port; the in-use case prints `Port <n> is in use. Start with PORT=<other> python3 run.py`, no traceback
- Observed:

```
=== PORT (a): :5000 held, PORT=5057
$ lsof :5000
Python  6760  apa    3u  IPv4 0x3c9087f22106dc76      0t0  TCP 127.0.0.1:5000 (LISTEN)
{"architecture":"cli-backend","components":{"api_server":"ok","cli_adapter":"ok"},"status":"healthy","version":"2.0.0"}
 * Running on http://localhost:5057
=== PORT (c): Vite proxy with the same PORT
{"architecture":"cli-backend","components":{"api_server":"ok","cli_adapter":"ok"},"status":"healthy","version":"2.0.0"}
 200
=== PORT (b): PORT=5057 while 5057 is in use
Port 5057 is in use. Start with PORT=<other> python3 run.py
exit=1
=== PORT (b, debug): FLASK_DEBUG=1 PORT=5057 while 5057 is in use (Task 1.4 Step 6)
Port 5057 is in use. Start with PORT=<other> python3 run.py
exit=1
=== SETUP-MISSING (FLASK_DEBUG=1): debug on only when asked
 * Running on http://localhost:5000
=== end; listeners on 5000/5057/3000:
```

- Evidence: `PORT.txt`
- Verdict: PASS · Severity: — · Known: —

### SETUP-MISSING — setup.sh with each tool absent; debug only with FLASK_DEBUG=1
- Phase: 8.3 · Env: E1 · Viewport: —
- Steps: `setup.sh` under `env -i` with a PATH lacking python3 (symlinks of `/usr/bin` without `python3*`), node, then npm; `FLASK_DEBUG=1 python3 run.py`.
- Expected: each prints `Missing: <tool> <minimum version> — install from <url>` and exits 1; debug is off unless `FLASK_DEBUG=1`
- Observed:

```
=== SETUP-MISSING: python3 absent
=== Crossword Helper Setup ===
Missing: python3 3.9 or later — install from https://python.org/downloads
exit=1
=== SETUP-MISSING: node absent
=== Crossword Helper Setup ===
Missing: node 18 or later — install from https://nodejs.org
exit=1
=== SETUP-MISSING: npm absent
=== Crossword Helper Setup ===
Missing: npm (installed with Node.js 18 or later) — install from https://nodejs.org
exit=1
=== clone after the three runs
status rc=0
 * Debug mode: off
=== SETUP-MISSING (FLASK_DEBUG=1): debug on only when asked
 * Debug mode: on
 * Debugger is active!
 * Debug mode: off
```

- Evidence: `SETUP-MISSING.txt`, `PORT.txt`, `SERVE-1.txt`
- Verdict: PASS · Severity: — · Known: npm's line carries "(installed with Node.js 18 or later)" in place of a bare minimum version, as `setup.sh` ships it


### F-TOUR — README "Using the app", followed literally (stopped at the Autofill step)
- Phase: 8.5a · Env: E1 (clone `e4e881e`, `python3 run.py` from `$SB/e1.sh`) · Browser: Chrome at `http://127.0.0.1:5000`, inner 1920×907
- Deviation from "literally": the README says "Open http://localhost:5000"; the run uses `http://127.0.0.1:5000` because plan 8.5a Step 1 binds that origin (a separate localStorage origin from `localhost:5000`).
- Pre-run: 127.0.0.1:5000 storage cleared with no backup (`8.5a-clean-storage.txt`); first load wrote `xw_theme`, `crossword_symmetry_enabled`, cleared again, reloaded.
- Steps and observed:
  - Grid, type letters: clicked the top-left square, typed `CAT` → C, A, T in row 1; Filled 1.3%.
  - `Black square` button on row 3 col 5, Space on row 6 col 1, `.` on row 8 col 9, `Symmetry` on → each placed with its mirror: `Total225 | Black6·2.7% | Filled1.4% | Words39`.
  - `Symmetry` off (class `on` removed), Space on row 2 col 2 → no mirror: `Total225 | Black7·3.1% | Filled1.4% | Words39`.
  - New grid `11×11` over letters → "Replace the current grid? Unsaved changes are lost." `Replace` / `Cancel`; Replace → `Total121 | Black0·0.0% | Filled0.0% | Words22`, `Undo` disabled.
  - `21×21` → `Total441 | Black0·0.0% | Filled0.0% | Words42`; `15×15` → `Total225 | Black0·0.0% | Filled0.0% | Words30` (empty grids, no confirm).
  - `Open saved` → one entry `15×15 2026-10-26 09:04` with `Open` and `Delete`.
  - Lists: panel shows the shipped lists; README's `Upload` is the submit button inside the `📤 Upload Wordlist` form (buttons: `Cancel Upload · [file] · Upload · Cancel`).
  - Search: `C?T`, Comprehensive Dictionary ticked by default, `Search` → `Results (7)`: CAT, CIT, COT, CRT, CST, CDT, …
  - Theme: `Choose File` with `fixture-theme-workflow.txt` (PUZZLE, CROSSWORD, ANAGRAM) → "Loaded Words (3)"; `Apply All Best Placements` → toast "Applied 3 theme words successfully!", three words on the grid with lock marks: `Total225 | Black6·2.7% | Filled10.0% | Words42`.
  - **Autofill, as written ("The tool rail on the left switches between tools"):** with the Theme panel open, clicking `Autofill` in the rail (coordinate click, ref click and DOM `.click()`) changes nothing visible: the rail's `on` class stays on `Theme`, the Theme Words panel stays over the inspector. Only after the panel's `×` does the Autofill panel show (rail `on`: `Autofill,Symmetry`). Source: `src/App.jsx` `selectTool` — Theme is an overlay, any other rail id sets `currentTool` underneath it, and `ToolRail` is passed `tool={showThemePanel ? 'theme' : currentTool}`. The README names no `×` step.
- Console errors so far: browser tool, onlyErrors → "No console errors or exceptions found for this tab."
- Network so far: 33 `/api/` requests in the browser tool's log, one with a 5xx: `GET /api/progress/4c27cd42-…` statusCode 503 (the `C?T` search's progress stream). The server log has the same request as 200 (`serve-8.5a.log` line 40); Resource Timing reports it as `initiatorType "other"`, `responseStatus 0`; a curl replay of the search returns `200 OK`, `text/event-stream`. `stream_progress` (`backend/api/progress_routes.py`) has no 503 path (its only error return is 404 "Task not found"). Control: a second in-browser `C?T` search → browser tool `GET /api/progress/1dd9b02f-…` statusCode 200, server log line 76 200. So 1 of 2 browser-tool 503s against 2 of 2 server 200s for the same requests. (The control cleared the browser tool's network log; the 33-entry list above was read before that.)
- **Contamination, from 09:08 on:** the server log holds requests this run did not make while the driver was in the shell: `POST /api/fill/with-progress` 202 at 09:08:25 (plus `/api/progress/c46682d2-…`, validate, number), Lists-panel content views of `foreign_classics`, `foreign_words` and `demo_words` at 09:08:37–49, two grid writes at 09:09:21–22. The grid then showed `Total225 | Black10·4.4% | Filled10.2% | Words48` (four black squares not placed by this run). The browser viewport also changed size three times during the run (1440×813 → 1440×757 → 1568×741 screenshot frames). Another person was using the same tab (Arthur, confirmed 2026-10-26); no observation after 09:08 is attributed to this run's actions.
- Evidence: `8.5a-clean-storage.txt`, `serve-8.5a.log`, `fixture-theme-workflow.txt`, `F-TOUR-autofill-click-under-theme.png`, `F-TOUR-after-theme-close.jpg`
- Instrument note: the browser tool's key name `period` does not type `.`; the key text `.` does.
- Verdict: FAIL (owner 2026-10-26: FAIL, filed and fixed in Phase 6, row re-run cold) · Severity: minor (the `×` is visible, nothing is lost) · Known: none filed (`gh issue list --state all` for "theme panel", "overlay", "rail", "Theme Words"); nearest is #50 item 3, the Theme panel covering the top bar, fixed in `b303186`, a different defect

### F-TOUR — README "Using the app", followed literally (re-run cold on `494ddb8`, after #91)
- Phase: 8.5a · Env: E1, fresh clone of `494ddb8` (`clone2-494ddb8.txt`, `SETUP-494ddb8.log`), served by `$SB/e1.sh` · Browser: Chrome at `http://127.0.0.1:5000`, a tab group of this run's own (no other tab drove the origin), served bundle hash `zj6fU8fZ` (the same hash as the #91 branch build driven before the merge)
- Deviation from "literally": `127.0.0.1:5000` in place of the README's `localhost:5000`, as in the first run (plan ENV-3).
- Pre-run: storage cleared from `/api/health` before the app loaded (`F-TOUR2-clean-storage.txt`: 3 keys → 0, no IndexedDB).
- Steps and observed:
  - Grid, type letters: top-left square, `CAT` → `letters: "CAT" | Total225 | Black0·0.0% | Filled1.3% | Words30`.
  - `Black square`, Space, `.` with `Symmetry` on → `Total225 | Black6·2.7% | Filled1.4% | Words39` (each with its mirror); `Symmetry` off (`xw-tool-btn xw-tool-btn-small `), Space → `Total225 | Black7·3.1% | Filled1.4% | Words39`; back on (`... on`).
  - `11×11` → "Replace the current grid? Unsaved changes are lost." → Replace → `Total121 | Black0·0.0% | Filled0.0% | Words22 | undoDisabled=true`; `21×21` → `Total441 | ... | Words42 | confirm=false`; `15×15` → `Total225 | ... | Words30 | confirm=false`.
  - `Open saved` with no save stored → the list renders empty and nothing else changes (observation below).
  - Lists: rail `on` `["Lists","Symmetry"]`, "Word List Management"; `📤 Upload Wordlist` form buttons `Cancel Upload · [file] · Upload · Cancel`.
  - Search `C?T`, Comprehensive Dictionary ticked by default → `Results (7)`.
  - Theme `Choose File` (`fixture-theme-workflow.txt`) → `Loaded Words (3)`; `Apply All Best Placements` → "Applied 3 theme words successfully!", `Total225 | Black6·2.7% | Filled10.0% | Words42`, letters `ANAGRAMCROSSWORDPUZZLE`, panel open, rail `["Theme","Symmetry"]`.
  - **Autofill (the #91 step):** rail `Autofill` with the Theme panel open → `{"panel":false,"railOn":["Autofill","Symmetry"],"startAutofill":true,"header":"Autofill · 40 empty slots, 2 theme words"}` (`F-TOUR2-autofill-rail-closes-theme.jpg`).
  - `Start Autofill` (Repair, 5 min, Comprehensive Dictionary): busy state 7 ms after the click ("Starting autofill… / 0% / Cancel"); result within 3 s: "No word fits the highlighted letters." with `Reset`, column 8 highlighted. Server: `POST /api/fill/with-progress` 202, progress 200.
  - Import: `Upload File`, `Paste JSON`, "Choose JSON file". Export: "JSON (for reimport) / HTML (printable) / Text (simple) / Preview / Export"; `Preview` (JSON) → `{ "size": 15, "grid": [ ...`.
  - `Undo` → `Total225 | Black0·0.0% | Filled0.0% | Words30`, no letters (the whole Apply All); `Redo` → `Black6·2.7% | Filled10.0% | Words42`, `ANAGRAMCROSSWORDPUZZLE`. Cmd+Z and Cmd+Shift+Z, focus on BODY: the same two states.
  - `Verify words` → "4 of 18 words flagged — 1 invalid: PUZZLE; 3 unfillable: RP______, _______SZ______, ANAGRAMSZ______" (PUZZLE is not in `comprehensive.txt`; ANAGRAM and CROSSWORD are).
  - `Clean grid` → "Nothing removed: theme-locked letters are kept."
  - `Save grid` → "Name this grid", suggested `15×15 2026-10-26 10:00` → `Save` → status "saved locally · just now"; `Open saved` → `15×15 2026-10-26 10:00 / 15×15 · 2026-10-26 10:04 / Open / Delete`.
  - `Open` → "Replace the current grid? Unsaved changes are lost." → Replace → `undoDisabled:true, redoDisabled:true`, grid restored (`Black6·2.7% | Filled10.0% | Words42`).
- Theme placement: Apply All placed ANAGRAM down column 8 with no black square after its M, so the down entry runs through CROSSWORD's S and PUZZLE's Z (grid read from the page; `#` black, `.` empty):

```
 1 .......A.......
 2 .......N.......
 3 .......A.......
 4 .......G.......
 5 .......R.......
 6 .......A.......
 7 ....#..M...#...
 8 ..#CROSSWORD#..
 9 ...#PUZZLE#....
10 ...............
```

  ANAGRAM is the first 7 letters of a 15-letter entry, which is why the Autofill header counts 2 theme words (`getThemeEntries` counts only fully theme-locked slots) and why autofill and Verify report column 8. The first run produced the same placement from the same fixture. This is #19 defect 3, ruled out of scope (spec §4 item 4, §1 keeps #19's backend half stretch).
- Observation (no spec text; not judged): `Open saved` with nothing saved renders an empty list and no message, so the click shows no response. Saves exist only after `Save grid` or the 30 s autosave (`AUTOSAVE_MS`), which the first run's slower pace reached and this one did not.
- Console errors: browser tool, onlyErrors → "No console errors or exceptions found for this tab."
- 5xx (header ruling): server log 0 of 55 requests (`serve-F-TOUR2.log`); browser tool 1, `GET /api/progress/7eb849ef-…` 503 on the `C?T` search, which the server log records as 200.
- Evidence: `F-TOUR2-clean-storage.txt`, `clone2-494ddb8.txt`, `SETUP-494ddb8.log`, `serve-F-TOUR2.log`, `F-TOUR2-autofill-rail-closes-theme.jpg`
- Verdict: PASS · Severity: — · Known: #19 defect 3 (theme word abutting fill), out of scope

### F-WORKFLOW — the whole basic workflow from the README and visible controls (`494ddb8`)
- Phase: 8.5a · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, this run's own tab group
- Pre-run: storage cleared from `/api/health` (3 keys → 0), app reloaded; console and network logs cleared. Fixture `fixture-theme-workflow2.txt` (CROSSWORD, ENIGMA, REBUS, all in `comprehensive.txt`); black pattern copied by hand from `data/grids/example_15x15.json` (36 squares).
- Steps and observed:
  - W1 New grid `15×15` → `Total225 | Black0·0.0% | Filled0.0% | Words30`, no confirm (empty grid).
  - W2 Black squares, `Symmetry` on (`... on`): 18 squares via click + `.`, mirrors placed → `Total225 | Black36·16.0% | Filled0.0% | Words78`, the example's pattern.
  - W3 Theme `Choose File` → `Loaded Words (3)`.
  - W4 `Apply All Best Placements` → toasts "Applied "CROSSWORD" to grid!", "Applied "ENIGMA" to grid!", "Applied "REBUS" to grid!"; `Total225 | Black38·16.9% | Filled10.7% | Words82` (2 boundary blacks added). ENIGMA down column 10 rows 1-6, REBUS across row 7 cols 11-15, CROSSWORD across row 8 cols 4-12, each ended by a black square or the edge.
  - W5 Fill one slot from Search: selected 1-Across (r1c1); rail `Search` closed nothing and showed "Selected: Row 1, Col 1 (across)" / "Click a word to fill it in the grid"; pattern `?????` → `Results (50)`; clicked the first result → row 1 `AEONS....E.....`, Filled 13.4%.
  - W6 `Start Autofill` (header "Autofill · 78 empty slots, 3 theme words"; Repair, 5 min, Comprehensive Dictionary): busy 7 ms after the click; "Repairing: 8 conflicts left / 85% / Cancel" at 5 s; ended before 141 s with "Filled 80/80 slots — 8 entries may be invalid (use Verify Words to check)", `Keep fill` / `Reset`. `Keep fill` → `Filled100.0%`, theme words unchanged.
  - W7 `Verify words` → "8 of 80 words flagged — 8 invalid: EAEN, OSRS, NRECE, RPYRO, ABEIT, NSSS, SENRR, ELANH", flagged letters red (`F-WORKFLOW-verify.jpg`).
  - W8 `Clean grid` → "Clean will remove 34 letters" / `Clean` / `Cancel` → `Clean` → "Removed 8 invalid words (37 cells cleared), kept 72 valid words"; `Filled81.8%` (153 letters of 187: 34 removed, as the confirm said; the toast's 37 counts kept theme-locked letters, #78).
  - W9 `Undo` → `Filled100.0%`; `Redo` → `Filled81.8%`, 153 letters.
  - W10 `Save grid` → "Name this grid", typed `Workflow theme grid` → `Save` → "saved locally · just now"; storage `[{"name":"Workflow theme grid","savedAt":"2026-10-26T09:18:19.991Z"}]`.
  - W11 Reload → "Restored "Workflow theme grid" (saved 2026-10-26 10:18)" with `Start blank`; grid string identical to the one read before the reload.
  - W12 `Open saved` → `Workflow theme grid / 15×15 · 2026-10-26 10:18 / Open / Delete` → `Open` → "Replace the current grid? Unsaved changes are lost." → `Replace` → identical grid, `Undo` disabled.
  - W13 Export JSON, HTML, Text → toasts "Generating JSON file...", "Generating HTML file...", "Generating TEXT file..."; `~/Downloads/crossword.json`, `.html`, `.txt` (copied as `F-WORKFLOW-export.*`). JSON grid vs the screen: letters and blanks match, 38 blacks, 153 letters; text == JSON; HTML 225 cells == JSON.
- Console errors: browser tool, onlyErrors → "No console errors or exceptions found for this tab."
- 5xx (header ruling): server log 0 of 55 requests in the F-WORKFLOW window (`serve-F-WORKFLOW.log`); browser tool 0 of 40 `/api/` requests (its log after the W11 reload).
- Observations (not judged against a criterion): `Keep fill` is not named in the README but is the visible next step; W12's confirm says "Unsaved changes are lost" when the grid open is the save itself, unchanged; opening it shows no message, and the grid does not visibly change.
- Evidence: `fixture-theme-workflow2.txt`, `serve-F-WORKFLOW.log`, `F-WORKFLOW-verify.jpg`, `F-WORKFLOW-export.json`, `F-WORKFLOW-export.html`, `F-WORKFLOW-export.txt`
- Verdict: PASS · Severity: — · Known: #78 (Clean's toast count)

### F-IMPORT — Upload File and Paste JSON, replace confirm, malformed input (`494ddb8`)
- Phase: 8.5a · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, this run's own tab group
- Pre-run: storage cleared from `/api/health` (`localStorage.length` 3 → 0; keys `crossword_saved_grids`, `xw_theme`, `crossword_symmetry_enabled`), app reloaded; console and network logs cleared. This clears the earlier F-WORKFLOW row's save "Workflow theme grid" (that row is recorded PASS with its evidence), so an empty `Open saved` is expected here. Server log start line 216. Fixtures: `example_11x11.json`, `example_15x15.json`, `example_21x21.json` copied from the clone's `data/grids/`; own fixtures `fixture-malformed-truncated.json` (first 300 bytes of `example_11x11.json`) and `fixture-malformed-paste.txt` ("this is not JSON at all, just words").
- Steps and observed (the grid is read from the page's SVG: size from its width, black squares from the filled `rect`s, letters from its `text` nodes; each compared with the file's `grid` rows joined by `|`):
  - I1 Import tab → `Upload File` → `example_11x11.json` → Preview "Size: 11×11 / Cells: 121 / Filled: 0" → `Import Grid` (grid was blank, no confirm). Page: size 11, 20 black squares; file: size 11, 20 `#`; row strings identical (`True`). Stats `Total 121 | Black 20·16.5% | Filled 0.0% | Words 44`.
  - I2 `example_15x15.json` uploaded over the 11x11 (20 blacks, no letters): `Import Grid` → "Replace the current grid? Unsaved changes are lost." with `Replace` / `Cancel`. `Cancel` → grid unchanged (11, 20 blacks). `Import Grid` again → `Replace` → "Processing..." at 1 ms, grid changed by 318 ms. Page: size 15, 36 blacks; file: 15, 36 `#`; identical (`True`). Stats `Total 225 | Black 36·16.0% | Filled 0.0% | Words 78`. The confirm also appears over a grid that holds only black squares (criterion silent on that case; recorded, not judged).
  - I3 Clicked cell (r1,c1), typed `CAT` → row 1 `CAT..#....#....`, `Filled 1.6%`. Uploaded `example_21x21.json` → Preview "Size: 21×21 / Cells: 441 / Filled: 0" → `Import Grid` → "Replace the current grid? Unsaved changes are lost." → `Cancel` → grid unchanged (size 15, row 1 `CAT..#....#....`) → `Import Grid` → `Replace` → "Processing..." at 2 ms, grid by 317 ms. Page: size 21, 72 blacks; file: 21, 72 `#`; identical (`True`); the letters are gone (`Filled 0.0%`, `Total 441 | Black 72·16.3% | Words 144`).
  - I4 `Paste JSON` with the 11x11 file's content (same data, whitespace compacted) → `Validate JSON` → Preview "Size: 11×11 / Cells: 121 / Filled: 0" → `Import Grid` → the same replace confirm (grid was the 21x21 with blacks) → `Replace` → "Processing..." 303 ms, grid by 617 ms. Page: size 11, 20 blacks; identical to the file (`True`).
  - I5 Typed `HI` (cells r1c2, r1c3): grid `.HI#...#...|...#...#...|...........|###....#...|......#....|...#...#...|....#......|...#....###|...........|...#...#...|...#...#...`, `Total 121 | Black 20·16.5% | Filled 2.0% | Words 44`. Uploaded `fixture-malformed-truncated.json` → the panel shows "Error:" "Failed to parse file: Unexpected end of JSON input", no Preview, no `Import Grid` button; the grid read back is identical to the grid before (`same: true`).
  - I6 `Paste JSON` with "this is not JSON at all, just words" → `Validate JSON` → "Error:" "Invalid JSON: Unexpected token 'h', "this is not"... is not valid JSON"; no `Import Grid` button; grid read back identical to before (`same: true`), same stats `Filled 2.0%` (`F-IMPORT-malformed-paste.jpg`).
- Console errors: browser tool, onlyErrors → "No console errors or exceptions found for this tab."
- 5xx (header ruling): server log 0 of 29 requests in the window (start line 216, `serve-F-IMPORT.log`; the log helper: `requests: 29 5xx: 0 4xx: 0`); browser tool 0 of 16 `/api/` requests.
- F-FEEDBACK notes: upload and paste show a Preview at once (within 2 s); `Import Grid` over a non-blank grid shows the replace confirm at 1 ms; `Replace` shows "Processing..." within 3 ms and the grid changes within 0.65 s; an import over a blank grid changes the grid with no message. Errors: "Failed to parse file: Unexpected end of JSON input" and "Invalid JSON: Unexpected token 'h', "this is not"... is not valid JSON" — a plain "Error:" heading, no stack trace, raw JSON or HTTP code, but the browser's own parser wording follows the plain prefix.
- Observations (not judged against a criterion): the replace confirm also shows when the grid has black squares and no letters; both error texts carry the JS parser's message after the prefix. The first Upload File import (I1) was not preceded by a confirm because the grid was entirely blank.
- Evidence: `fixture-malformed-truncated.json`, `fixture-malformed-paste.txt`, `serve-F-IMPORT.log`, `F-IMPORT-malformed-paste.jpg`
- Verdict: PASS · Severity: — · Known: —

### F-EDIT — typing, keys, black squares with Symmetry on and off, undo and redo (`494ddb8`)
- Phase: 8.5a · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, this run's own tab group
- Pre-run: continues in the F-IMPORT tab and storage (no clean start needed; every case starts from `New grid`); console and network logs cleared; server log start line 249. The grid is read from the page's SVG (size, black squares, letters, the selected cell by its accent outline, the direction by the accent-tinted word cells), the stats line from the page text, and the numbers shown are compared with the numbers computed from the page's own black squares (a 2-or-more-letter entry start gets the next number).
- Hint line read from the page: "Type letters · Arrows move · Space or . black square · Enter switch direction · Tab next word · Backspace clear". Spec §3.9 read: one letter, one black-square toggle together with its mirror, are each one undo step; keys Cmd/Ctrl+Z, Cmd/Ctrl+Shift+Z, Ctrl+Y.
- Steps and observed:
  - E1 `New grid` `11×11` over a grid with letters and blacks → a replace confirm, `Replace` → `Total 121 | Black 0·0.0% | Filled 0.0% | Words 22`, `Undo` and `Redo` disabled; `Symmetry` on.
  - E2 Clicked r1c1, typed `CAT` → row 1 `CAT........`, selection r1c4 across, `Filled 2.5%`.
  - E3 `Backspace` on the empty r1c4 → selection r1c3, nothing cleared (`Filled 2.5%`); `Backspace` again on `T` → row 1 `CA.........`, `Filled 1.7%`, selection stays r1c3.
  - E4 Arrows from r1c3 (across): ArrowDown → r2c3 down; ArrowRight → r2c4 across; ArrowUp → r1c4 down; ArrowLeft → r1c3 across. `Enter` → r1c3 down (direction switched, cell unchanged). `Tab` → r1c4 down (next word start; focus stays on the grid).
  - E5 `Space` on r3c3 with Symmetry on → blacks r3c3 and r9c9 (the mirror), `Black 2·1.7%`, `Words 26`; numbering 25 shown, 25 expected, 0 mismatches. `Cmd+Z` → no blacks, `Words 22`, `Undo` and `Redo` both enabled; `Cmd+Shift+Z` → r3c3 and r9c9 back, `Redo` disabled.
  - E6 One step at a time: from `CAT` + clear-`T` + black pair, `Cmd+Z` twice → black pair gone and `T` back (`CAT........`, `Filled 2.5%`); a third `Cmd+Z` → `CA.........` (`Filled 1.7%`); `Ctrl+Y` → `CAT`. Each press moved exactly one edit.
  - E7 Typed after undo: clicked r5c6, `.` → blacks r5c6 and r7c6, `Black 2·1.7%`, `Words 25`, and `Redo` became disabled (the redo stack was dropped).
  - E8 Symmetry toggled off (button loses `on`; `localStorage` `crossword_symmetry_enabled` `false`): `.` on r2c2 → blacks r2c2, r5c6, r7c6 only (no mirror), `Black 3·2.5%`, `Words 25`. `Cmd+Z` → r2c2 gone only; `Cmd+Shift+Z` → back; `Space` on r2c2 → removed alone (`Black 2·1.7%`).
  - E9 Symmetry toggled on (`localStorage` `true`): `Space` on black r5c6 → both r5c6 and r7c6 removed (`Black 0·0.0%`, `Words 22`); `Cmd+Z` → both back (`Black 2`); `Cmd+Shift+Z` → both gone.
  - E10 `New grid` `15×15` over letters → replace confirm "Replace the current grid? Unsaved changes are lost.", `Replace` → `Total 225 | Black 0·0.0% | Filled 0.0% | Words 30`, `Undo` and `Redo` disabled. Typed `HELLO` at r1c1 → `Filled 2.2%`, selection r1c6 across. ArrowDown → r2c6 down, `Enter` → r2c6 across. `.` on r4c4 → blacks r4c4 and r12c12, `Black 2·0.9%`, `Words 34`, numbering 33 shown, 33 expected, 0 mismatches. `Cmd+Z` → no blacks, `Words 30`, 29 numbers, 0 mismatches; `Cmd+Shift+Z` → both back, `Words 34`, 33 numbers, 0 mismatches.
  - E11 `New grid` `21×21` over letters → the same confirm, `Replace` → `Total 441 | Black 0·0.0% | Filled 0.0% | Words 42`, `Undo` and `Redo` disabled. Typed `WORD` at r1c1 → `Filled 0.9%`, selection r1c5. `Space` on r6c6 → blacks r6c6 and r16c16, `Black 2·0.5%`, `Words 46`, numbering 45 shown, 45 expected, 0 mismatches. `Cmd+Z` → no blacks, `Words 42`, 41 numbers, 0 mismatches; `Cmd+Z` → `WOR`, `Filled 0.7%`; `Cmd+Shift+Z` twice → `WORD` and both blacks back, `Words 46`, 45 numbers, 0 mismatches. `Ctrl+Z` → no blacks (`Black 0·0.0%`); `Ctrl+Shift+Z` → both blacks back, `Redo` disabled.
- Console errors: browser tool, onlyErrors → "No console errors or exceptions found for this tab."
- 5xx (header ruling): server log 0 of 54 requests in the window (start line 249, `serve-F-EDIT.log`; the log helper: `requests: 54 5xx: 0 4xx: 0`); browser tool 0 of 54 `/api/` requests (`/api/number`, `/api/grid/validate`, `/api/health`, all 200).
- F-FEEDBACK notes: typing, arrows, `Enter`, `Tab`, `Backspace`, black squares, undo and redo all change the grid and the stats line at once (same read after the key, well under 2 s); `New grid` over content shows the replace confirm at once, then the new grid on `Replace`. No message or toast appears for any of them and none is needed beyond the grid change. No error message arose.
- Observations (not judged against a criterion): `Backspace` on an empty cell moves back one cell without clearing; the browser tool's `period` key name did not reach the app (the `.` key typed as text did), a tool artefact, not an app defect; the `Black square` tool button in the Grid panel was not driven here (the key path was). The first 11×11 `New grid` confirm text was not read in E1 (a script error preceded the read); the 15×15 and 21×21 ones are quoted above.
- Evidence: `serve-F-EDIT.log`
- Verdict: PASS · Severity: — · Known: —

### F-THEME-LOAD — theme file with lowercase, blank and duplicate lines; a file with an invalid word (`494ddb8`)
- Phase: 8.5a · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, this run's own tab (new tab, same Chrome group)
- Pre-run: storage cleared from `/api/health` (`localStorage.length` 3 → 0; keys `crossword_saved_grids`, `xw_theme`, `crossword_symmetry_enabled`), app reloaded; console and network logs cleared. This clears the earlier rows' saved grids (those rows are recorded with their evidence). Server log start line 309 (the file had 305 lines before an API-only dry run of the fixture words, which added 4). Both cases run on a `New grid` `15×15` (Grid rail, `15×15`: `Total 225 | Black 0·0.0% | Filled 0.0% | Words 30`). Fixtures `fixture-theme-load-a.txt` (lines: `crossword`, an empty line, `PUZZLE`, `ANAGRAM`, `PUZZLE`) and `fixture-theme-load-b.txt` (the same five lines plus `AB` and `INTERNATIONALIZATION`, 20 letters).
- Steps and observed:
  - T1 (a) Theme rail → `Choose File` → `theme-load-a.txt`. Panel: `Loaded Words (3)` listing `CROSSWORD (9)`, `PUZZLE (6)`, `ANAGRAM (7)` — read from the page text: uppercase, each once (the lowercase `crossword` shown as `CROSSWORD`, the duplicate `PUZZLE` once, the blank line gone). `Placement Suggestions` appeared with `CROSSWORD (9 letters)` first: "Row 7, Col 3 (across)", "100/100", "Centered placement (symmetric), Good horizontal position, Long word (9 letters)".
  - T2 (a) Clicked the first `✓ Apply This Placement` (CROSSWORD, "Row 7, Col 3 (across)"). Toast: `Applied "CROSSWORD" to grid!`; stats `Total 225 | Black 2·0.9% | Filled 4.0% | Words 34`. Grid read from the SVG: letters `CROSSWORD` in row 8, columns 4-12 (the suggestion's row and column are 0-based). Theme-lock mark: `CrosswordGrid.jsx` draws a folded-corner `path` (`fill="var(--accent)"`) only for `cell.isThemeLocked && !cell.isBlack`; in the DOM exactly 9 cells carry that path: r8c4:C r8c5:R r8c6:O r8c7:S r8c8:S r8c9:W r8c10:O r8c11:R r8c12:D — the 9 letters of the word and no other cell.
  - T3 (b) With that grid and the three words loaded, `Choose File` → `theme-load-b.txt`. Message shown in the panel under the file name, as two lines: `AB: Too short (minimum 3 letters)` and `INTERNATIONALIZATION: Too long for 15×15 grid`; the toast read: `Invalid theme words: AB: Too short (minimum 3 letters)`. Panel below the message still reads `Loaded Words (3)` `CROSSWORD (9)` `PUZZLE (6)` `ANAGRAM (7)`, the same list as in T1, and the grid keeps its theme-locked CROSSWORD (`Filled 4.0%` before and after); the suggestions were fetched again for the same three words.
- Console errors: browser tool, onlyErrors → "No console errors or exceptions found for this tab."
- 5xx (header ruling): server log 0 of 25 requests in the window (start line 309, `serve-F-THEME-LOAD.log`; the log helper: `requests: 25 5xx: 0 4xx: 0`); browser tool 0 of 11 `/api/` requests, all 200 (`/api/theme/upload` twice, `suggest-placements` twice, `apply-placement` once).
- F-FEEDBACK notes: `Choose File` shows the loaded list and the suggestions within the 1.5 s of my first read (the read was after a fixed wait, so a tighter bound was not measured); `Apply This Placement` shows the toast `Applied "CROSSWORD" to grid!` and the grid change by the 1.2 s read; the invalid-file message appears in the panel and as a toast within the 1.5 s read. Error wording is plain: `AB: Too short (minimum 3 letters)`, `INTERNATIONALIZATION: Too long for 15×15 grid`; no stack trace, raw JSON or HTTP code.
- Observations (not judged against a criterion): the toast names only the first invalid word (`AB`) while the panel lists both; the criterion's "nothing loads" is read as "the loaded list is unchanged", since a list was already loaded from (a); the panel keeps the old list rather than clearing it.
- Evidence: `fixture-theme-load-a.txt`, `fixture-theme-load-b.txt`, `serve-F-THEME-LOAD.log`
- Verdict: PASS · Severity: — · Known: —

### F-LISTS — Lists panel, Show Stats, upload with Preview, Add Words, tick in Search and Autofill, delete (`494ddb8`)
- Phase: 8.5a · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, this run's own tab
- Pre-run: storage cleared from `/api/health` (`localStorage.length` 3 → 0; keys `crossword_saved_grids`, `xw_theme`, `crossword_symmetry_enabled`), app reloaded; console log cleared before the reload, the network log cleared after it. Server log start line 337 (window = lines 338 on, `serve-F-LISTS.log`). Fixture `fixture-lists-upload.txt`: `QWERTYZEBRA`, `FLIBBERTY`, `moonpie`, `SKYLARK`, `CATNIPS` (plain ASCII).
- Unique-word proof, one command over the clone's `data/wordlists/` by explicit path (`-rixc`, whole line, case-insensitive; only files with a non-zero count are shown), then the substring form (`-rilc`, which prints a count per file) for `QWERTYZEBRA`:
```
== QWERTYZEBRA
(non-zero files above)
== AAAMAP        (control: a word seen in the head of comprehensive.txt)
.../data/wordlists/comprehensive.txt:1
.../data/wordlists/raw/top_200k.txt:1
.../data/wordlists/raw/comprehensive_intl.txt:1
(non-zero files above)
== substring QWERTYZEBRA: every one of the 17 files printed `:0`, rc=1
```
  The control word is found in three files; the unique word in none. The whole-line form cannot match a `WORD;score` line, which is why the substring form was also run (also 0 everywhere).
- Steps and observed:
  - L1 Lists rail → "Word List Management", `Upload Wordlist`, category buttons, and `ALL WORDLISTS (6)`: Comprehensive Dictionary, Classic Crosswordese, Expressions & Slang, Foreign Classics, Foreign Words, Demo Words. Default selection read from the checkboxes: Search tab — only `Comprehensive Dictionary` ticked (the other five unticked); Autofill tab, `WORD LISTS`, `BUILT-IN` / `CUSTOM` — the same, only `Comprehensive Dictionary` ticked. The code default is `useState(['comprehensive'])` in `PatternMatcher.jsx`. See Observations for the criterion's wording.
  - L2 Clicked `Classic Crosswordese` → the card shows `Show Stats` and `Add Words`; clicked `Show Stats` → the button became `Hide Stats` and the card reads "Words that appear frequently in crossword puzzles / Category: core / Words: 431 / Difficulty: medium / Words (431)" followed by the words `ERA ERE ERR EEL ATE ALE ALI ARE AGE ADO ASP END ...`. The file has 431 distinct non-comment, non-blank lines (`sort -u | wc -l` → 431; 437 before dedup).
  - L3 `Upload Wordlist` → form with `Wordlist Name:` (prefilled `lists-upload`) and `Select File:`; chose the fixture → "Selected: lists-upload.txt (0.0 KB)" → `Upload` → `Preview`: "5 valid words" / "0 skipped" and the words `QWERTYZEBRA FLIBBERTY MOONPIE SKYLARK CATNIPS` (the lowercase `moonpie` shown in uppercase) with `Confirm` / `Cancel`. `Confirm` → `ALL WORDLISTS (7)`, new card `Lists-Upload` with tags `custom`, `uploaded`; its detail: "Uploaded from lists-upload.txt / Category: custom / Words: 5 / Words (5)": `CATNIPS FLIBBERTY MOONPIE QWERTYZEBRA SKYLARK`.
  - L4 `Add Words` → `Add Words to List` with a textarea "Enter words (one per line)"; entered `ZEBRAFINCH` and `quokka` → `Add Words to List` → "Words: 7 / Words (7)": `CATNIPS FLIBBERTY MOONPIE QUOKKA QWERTYZEBRA SKYLARK ZEBRAFINCH`.
  - L5 Search tab: the new list is in the selector, unticked, as `Lists-Upload (7 words)`; ticked it (Comprehensive still ticked). Pattern `QWERTYZEBRA` → `Results (1)`: `QWERTYZEBRA`, score `47`, source `lists-upload`, `11 letters`. Unticked Comprehensive (only `Lists-Upload (7 words)` ticked) → `Results (1)`, the same result. Control: only `Comprehensive Dictionary` ticked, same pattern → "No matching words found".
  - L6 Autofill tab: the selector, under `CUSTOM`, lists `Lists-Upload (7)`, unticked; ticking it gives ticked = `Comprehensive Dictionary`, `Lists-Upload (7)`.
  - L7 Lists tab, the `Lists-Upload` card selected, native `window.confirm` stubbed immediately before the `Delete` click (the native dialog blocks the browser extension; the stub records the message and returns true): `window.__confirms` → `["Delete wordlist \"custom/lists-upload\"? This cannot be undone."]`. After: `ALL WORDLISTS (6)`, no `Lists-Upload` card. Search selector: six lists, no `Lists-Upload`; Autofill selector: six lists, no `Lists-Upload` (the box ticked in L6 is gone with it); `GET /api/wordlists/custom/lists-upload` → 404; the clone's `data/wordlists/custom/` lists only `demo_words.txt`.
- Console errors: browser tool, onlyErrors → "No console errors or exceptions found for this tab."
- 5xx (header ruling): server log 0 of 41 requests in the window (`requests: 41 5xx: 0 4xx: 1`; the one 4xx is my own deliberate `GET /api/wordlists/custom/lists-upload` → 404 in L7, after the delete); browser tool: 2 of 31 `/api/` requests reported 503, both `GET /api/progress/<id>` (SSE) that the server log records as 200 (the known tool artefact).
- F-FEEDBACK notes: file choice shows "Selected: lists-upload.txt (0.0 KB)" at once; `Upload` shows the `Preview` (counts and words) within the 1.5 s read; `Confirm` adds the card, `Words (5)` and the count (7) within 2 s, with no toast; `Add Words to List` updates `Words: 7` within 1.8 s, no toast; `Delete` asks the confirm (stubbed, message captured) and the card is gone within 2 s, no toast. Search shows `Results (1)` or "No matching words found" within 2 s. No error arose.
- Observations (not judged against a criterion): (1) the criterion says "the shipped lists are shown and selected by default": all six shipped lists are shown, but only one, Comprehensive Dictionary, is ticked by default, in both Search and Autofill; read as "a default selection is in force", this passes, read as "all six ticked" it would not — the orchestrator is asked to rule on the wording. (2) the uploaded list's name was derived from the file name (`lists-upload`) and shown as `Lists-Upload`; the upload form's `Wordlist Name:` was prefilled and not edited. (3) a newly uploaded list is unticked in Search and Autofill until the user ticks it. (4) `Show Stats` shows the same fields (Category, Words, Difficulty) that the card already carries; the toggle changes only its label to `Hide Stats`. (5) the delete message names the path `custom/lists-upload`, not the display name.
- Evidence: `fixture-lists-upload.txt`, `serve-F-LISTS.log`
- Verdict: PASS · Severity: — · Known: —

### F-SEARCH — default lists: `C?T`, a 6-letter all-`?` pattern, a no-match pattern, placing a result (`494ddb8`)
- Phase: 8.5a · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, this run's own tab
- Pre-run: storage cleared from `/api/health` (`localStorage.length` 2 → 0; keys `xw_theme`, `crossword_symmetry_enabled`; the earlier row's list was already deleted and no grid was saved), app reloaded to the default blank 15×15 grid (`Total 225 | Black 0·0.0% | Filled 0.0% | Words 30`); console log cleared before the reload, network log after it. Server log start line 381 (window = lines 382 on, `serve-F-SEARCH.log`).
- Default lists, read from the Search tab's checkboxes: ticked = `Comprehensive Dictionary`; unticked = `Classic Crosswordese (431 words)`, `Expressions & Slang`, `Foreign Classics`, `Foreign Words`, `Demo Words`.
- Steps and observed (each result list read from the page's `.result-item` elements; the script checks every displayed word against the pattern as a regex, `?` → `[A-Z]`, anchored, so length is checked too):
  - S1 Pattern `C?T` → `Results (7)`: `CAT, CIT, COT, CRT, CST, CDT, CUT`; mismatches against the pattern and length: 0. Independent count on the list file: `grep -ixE 'C[A-Z]T(;.*)?' data/wordlists/comprehensive.txt` → `CAT CDT CIT COT CRT CST CUT`, the same seven.
  - S2 Pattern `??????` → `Results (50)`, 50 items, lengths found `[6]`, mismatches: 0 (first six: `ARENOT, ARIOSE, ARISEN, ARISTO, ARNIES, ARTIES`). The list file holds 7329 six-letter words (`grep -icE '^[A-Z]{6}(;.*)?$'`); the code passes `maxResults: 50` (`PatternMatcher.jsx:73`), so the panel shows 50 of them under the header `Results (50)`.
  - S3 Pattern `Q?Z??` → no `Results` header and no result items; the panel shows the message "No matching words found" (read from the page text beside `Min Score: 0`). The file holds 0 words matching `^Q[A-Z]Z[A-Z]{2}`.
  - S4 Place a result: clicked cell r1c1 (blank grid) → "Selected: Row 1, Col 1 (across)" / "Click a word to fill it in the grid", the slot being row 1, 15 cells. Grid before: 15 rows of 15 `.`. Pattern `???????????????` (15) → `Results (50)`, mismatches 0, first `BURSTINTOFLAMES`, `DRAWINGTOACLOSE`, `GATHERINGCLOUDS`. Clicked the second result, `DRAWINGTOACLOSE`. Grid after, read from the SVG: row 1 `DRAWINGTOACLOSE`; rows 2-15 all `...............`; 15 letters in the grid, all in that slot; stats `Total 225 | Black 0·0.0% | Filled 6.7% | Words 30`; no black square touched. No toast (toast elements read empty).
- Console errors: browser tool, onlyErrors → "No console errors or exceptions found for this tab."
- 5xx (header ruling): server log 0 of 20 requests in the window (`requests: 20 5xx: 0 4xx: 0`); browser tool 2 of 10 `/api/` requests reported 503, both `GET /api/progress/<id>` that the server log records as 200 (the known tool artefact).
- F-FEEDBACK notes: each search shows `Results (N)` or "No matching words found" within the 2.5 s of my fixed-wait read (a tighter bound was not measured); clicking a result changes the grid by the 1.2 s read, with no toast or message. No error arose.
- Observations (not judged against a criterion): (1) the Results header reads `Results (50)` for the 6-letter pattern although 7329 words match, so a user cannot tell from the header that the list is capped at 50 (same for the 15-letter pattern); (2) selecting a cell does not copy the slot's pattern into the Search field (it still held `Q?Z??` after the click, until I typed the new pattern); (3) the grid was a 15-letter slot, a placement over a longer slot than a typical entry.
- Evidence: `serve-F-SEARCH.log`
- Verdict: PASS · Severity: — · Known: —

### F-EXPORT — Preview and Export of JSON, HTML and Text, JSON round trip (`494ddb8`)
- Phase: 8.5a · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, this run's own tabs (two, one after the other)
- Pre-run: storage cleared from `/api/health` (`localStorage.length` 3 → 0; keys `crossword_saved_grids`, `xw_theme`, `crossword_symmetry_enabled`), app reloaded; console and network logs cleared. Server log start line 406 (window = lines 407-465, `serve-F-EXPORT.log`). Grid: `New grid` `11×11`; black squares with `Symmetry` on (2 placed by `.` plus mirrors, 4 squares); theme fixture `fixture-theme-export.txt` (`crossword`, `PUZZLE`, `ANAGRAM`) via `Choose File`, then the first `Apply This Placement` (CROSSWORD, "Row 5, Col 1 (across)"), which also added 2 boundary blacks; letters `CAT` (row 2) and `ARENA` (row 9) typed with real key events.
- Grid read from the page before export (`#` black, `.` blank): `...#.......` / `CAT........` / `...........` / `...........` / `#..........` / `#CROSSWORD#` / `..........#` / `...........` / `..ARENA....` / `...........` / `.......#...`; stats `Total 121 | Black 6·5.0% | Filled 14.8% | Words 26`; theme-lock marks (folded-corner path, as F-THEME-LOAD read them) on exactly r6c2..r6c10 `CROSSWORD`.
- Steps and observed:
  - X1 JSON `Preview`: a `pre` block holding the JSON text (`size` 11, `grid` rows, `numbering`; keys `["size","grid","numbering"]`, 1856 chars); its grid rows equal the page's rows (script: `previewMatchesPage: true`). `Export` → toast `Generating JSON file...`. `ls -lt ~/Downloads | head` after it: `-rw-r--r--@  1 apa  staff  1856 Oct 26 11:20 crossword (1).json` (new, by mtime; `cmp` with `F-EXPORT-export.json` identical).
  - X2 HTML `Preview`: the panel shows `HTML preview not available - use Export to download`. `Export` clicked twice (once by `.click()`, once by a real click at the button) → toast `Generating HTML file...` the first time. **No new file appeared in `~/Downloads`**: the `ls -lt ~/Downloads | head` after each attempt, 3 s and then 6 s later, lists only `crossword (1).json`, `iris-bridge-return-2026-10-26.bundle` (10:43), `crossword.txt` and `crossword.html` (both 10:19), `crossword.json` (10:19); `find ~ -newermt '2026-10-26 11:21'` for `crossword*` or `*.crdownload` found nothing. The same was repeated after a reload and in a second fresh tab.
  - X3 Text `Preview`, read from its `pre`: `Crossword Puzzle (11×11)` then 11 lines of `_ _ _ ■ _ ...` (script `F-EXPORT-cmp.txt`: it equals the JSON rows, `text preview == json rows: True`). `Export` (`.click()` and a real click) → toast `Generating TEXT file...`; again **no new file** in `~/Downloads`.
  - X4 Content check of the one file received, `F-EXPORT-export.json`, against the page grid (script `F-EXPORT-cmp.txt`): `json rows == page rows: True`; `letters 17 blacks 6 blanks 98`; keys `['size','grid','numbering']`; `'lock' in raw: False`. HTML and Text could not be compared as files (not delivered); the Text preview equals the JSON, the HTML has no preview.
  - X5 Round trip: reload (restore from autosave: `Restored "11×11 2026-10-26 11:20" (saved 2026-10-26 11:20)` with `Start blank`, grid and the 9 lock marks identical), `New grid` `11×11` → in-page modal `Replace the current grid? Unsaved changes are lost.` / `Replace` / `Cancel` → `Replace` → empty grid (0 non-blank cells, `Black 0·0.0%`). Import → `Upload File` with `crossword (1).json`: panel shows `Preview` `Size: 11×11` `Cells: 121` `Filled: 17`; `Import Grid` → grid rows equal the pre-export rows (`eq: true`), `Black 6·5.0% | Filled 14.8% | Words 26`; theme-lock marks: none (0 of the 9). Locks did not survive, which the plan allows.
  - X6 README `Known Limitations` (quoted from `/Users/apa/projects/crossword-helper-p8/README.md`, this branch's copy; it differs from `494ddb8` only in the Task 8.1 tour): "A JSON export keeps the letters and black squares but not which words are theme-locked, so after importing it the theme words can be overwritten; `Save grid` keeps the locks."
  - X7 Re-run of X2 and X3 by hand (owner, 2026-10-26, own clicks on `Export` in a `127.0.0.1:5000` tab on the same grid; no Chrome prompt reported), after the FAIL below was first committed as `bfef2d0`. `ls -lt ~/Downloads | head`, pasted: `-rw-r--r--@  1 apa  staff  1856 Oct 26 11:35 crossword (2).json`, `-rw-r--r--@  1 apa  staff  2677 Oct 26 11:36 crossword (1).html`, then `-rw-r--r--@  1 apa  staff  2677 Oct 26 16:13 crossword (2).html`, `-rw-r--r--@  1 apa  staff  1856 Oct 26 16:13 crossword (3).json`, `-rw-r--r--@  1 apa  staff  292 Oct 26 16:13 crossword (1).txt`. `cmp`: `crossword (2).json` == `crossword (1).json` (X1, == page rows in X4); `crossword (3).json` == `crossword (2).json`; `crossword (2).html` == `crossword (1).html`. Script over the files: HTML `html rows 11 cells 121`, `html rows == json rows: True`; Text first line `'Crossword Puzzle (11×11)'`, `text rows 11 text rows == json rows: True`.
- Console errors: browser tool, onlyErrors (second tab) → "No console errors or exceptions found for this tab."
- 5xx (header ruling): server log 0 of 59 requests in the F-EXPORT window (`requests: 59 5xx: 0 4xx: 0`; the export is client-side, no `/api/` export request exists); browser tool: the second tab's `/api/` log was empty (no `/api/` request after its load), the first tab's log showed 17 `/api/` requests, all 200.
- F-FEEDBACK notes: `Preview` (JSON, HTML, Text) shows its result within the 1.5 s read; `Export` shows the toast `Generating JSON file...` / `Generating HTML file...` / `Generating TEXT file...` within 0.4 s, then the app gives no confirmation that a file was saved (on the agent's automated clicks the HTML and Text exports showed the same "Generating" toast and produced no file, with no message that it failed; on the owner's clicks in X7 each produced its file); the upload shows the `Preview` stats within 1.2 s; `Import Grid` changes the grid within 1.2 s; `New grid` asks the in-page confirm and clears the grid within 0.9 s. No error message appeared.
- Observations: (1) Instrument fault, not an app defect: after the first download in the agent's tab, its later automated `Export` clicks from `127.0.0.1:5000` saved no file, while the owner's manual clicks on the same code saved all three formats (X7), as F-WORKFLOW's exports did. The exact browser mechanism is not established (Chrome's multiple-downloads block, whose prompt the browser tool cannot see or answer, is suspected; the owner reported no prompt). The app code (`ExportPanel.jsx` `downloadFile`: Blob, anchor `download`, 500 ms `setTimeout`) is the same for all three formats. (2) The app shows no failure or success message after `Export` beyond `Generating ... file...`. (3) Autosave restored the grid with its locks across a reload (relevant to F-RESTORE).
- Evidence: `fixture-theme-export.txt`, `serve-F-EXPORT.log`, `F-EXPORT-cmp.txt`, `F-EXPORT-export.json`, `F-EXPORT-manual-export.json`, `F-EXPORT-manual-export.html`, `F-EXPORT-manual-export.txt` (X7; X2 and X3 delivered no file)
- Verdict: PASS (on X7's manual exports; first committed FAIL in `bfef2d0` on X2 and X3, reclassified as an instrument fault) · Severity: — · Known: —

### F-RESTORE — reload and `Open saved` of a named save with letters, black squares and a theme lock (`494ddb8`)
- Phase: 8.5a · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, this run's own tab (new tab, closed at the end)
- Pre-run: storage cleared from `/api/health` (`localStorage.length` 3 → 0; keys `crossword_saved_grids`, `xw_theme`, `crossword_symmetry_enabled`), app reloaded; console log cleared. Server log start line 1340 (window = lines 1341-1380, `serve-F-RESTORE.log`). Fixture `fixture-theme-restore.txt` (`crossword`, `PUZZLE`, `ANAGRAM`).
- Build: `New grid` `11×11` (the 15×15 default replaced, no confirm on the empty grid); black square at row 1, column 4 by `.` with `Symmetry` on (mirror at row 11, column 8); Theme rail `Choose File` → `Loaded Words (3)`; first `Apply This Placement` (ANAGRAM, "Row 2, Col 5 (down)") → toast `Applied ANAGRAM to grid` (added boundary blacks at row 2 and row 10, column 6); letters `CAT` (row 1) and `ARENA` (row 11) typed with real key events (the `.` black square was sent as a dispatched `keydown` on the grid container, which the app's handler accepted). Stats `Total 121 | Black 4·3.3% | Filled 12.8% | Words 26`.
- Snapshot (`#` black, `.` blank, read from the SVG: a cell is black when its fill rect carries the shadow filter; locked when it has the folded-corner `path`): `CAT#.......` / `.....#.....` / `.....A.....` / `.....N.....` / `.....A.....` / `.....G.....` / `.....R.....` / `.....A.....` / `.....M.....` / `.....#.....` / `ARENA..#...`; locked cells `r3c6 r4c6 r5c6 r6c6 r7c6 r8c6 r9c6` (ANAGRAM, 7). `Save grid` → "Name this grid" prompt prefilled `11×11 2026-10-26 16:30`, replaced by typing `Restore theme grid` → `Save` → header "saved locally · just now". Storage entry: name `Restore theme grid`, `savedAt` `2026-10-26T15:30:24.960Z`, size 11, 7 cells with `isThemeLocked` in the saved grid.
- Steps and observed:
  - R1 Path 1, reload: the panel read `Restored "Restore theme grid" (saved 2026-10-26 16:30)` with `Start blank`. Script comparison of the read-back with the snapshot literal: `rowsEqual: true`, `locksEqual: true`; read-back rows and locks identical to the snapshot above (`gs` 121 cells, locks `r3c6 ... r9c6`).
  - R2 Path 2: `New grid` `15×15` → in-page modal "Replace the current grid? Unsaved changes are lost." / `Replace` / `Cancel` → `Replace` → empty 15×15 (`Total 225 | Black 0·0.0% | Filled 0.0%`, 0 locks). `Open saved` → "Restore theme grid / 11×11 · 2026-10-26 16:30 / Open / Delete" → `Open`: **no confirm appeared** (the grid was empty, as with `New grid` at W1) and the grid became 11×11 at once. Script comparison: `rowsEqual: true`, `locksEqual: true`; stats `Total 121 | Black 4·3.3% | Filled 12.8% | Words 26`; `Undo` disabled.
- Console errors: browser tool, onlyErrors → "No console errors or exceptions found for this tab."
- 5xx (header ruling): server log 0 of 40 requests in the window (`requests: 40 5xx: 0 4xx: 0`; `/api/health` 10, `validate` 7, `number` 7, `theme/upload` 1, `suggest-placements` 2, `apply-placement` 1). Browser tool: its network log was started only after the row (first call at the end), so it reported no `/api/` requests; the server log is the count.
- F-FEEDBACK notes: `Apply This Placement` → toast and grid change by the first read (about 1.2 s); `Save grid` → prompt at once, header "saved locally · just now" after `Save` within 0.8 s; reload shows the restore message at once (read after 1 s); `New grid` modal and clear within 0.6 s; `Open` replaces the grid within 0.6 s but shows **no message** that a save was opened. No error message appeared.
- Observations (not judged against a criterion): (1) The `Open` of a save onto an empty grid asks nothing and says nothing; W12 of F-WORKFLOW showed the confirm when the grid held letters. (2) The default name offered by `Save grid` is `11×11 <date time>`, local time (16:30) while `savedAt` stores UTC (15:30). (3) The synthetic `.` keydown instead of a real key press is the only non-real input; every letter went through real key events.
- Evidence: `fixture-theme-restore.txt`, `serve-F-RESTORE.log`
- Verdict: PASS · Severity: — · Known: —

### G1 — New 15×15 grid from the Grid tool (`494ddb8`)
- Phase: 8.5 · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, this row's own tab (closed at the end). The G1, G3, G8 and G9 blocks share one tab, one server-log window and one console read (stated in each).
- Pre-run: storage cleared from `/api/health` (`localStorage.length` 3 → 0; keys `crossword_saved_grids`, `xw_theme`, `crossword_symmetry_enabled`), then `http://127.0.0.1:5000/` loaded. Server log start line 1389 (window = lines 1390-1435, `serve-Grid.log`, shared by G1/G3/G8/G9). Case definition read from `2026-10-22-fresh-install-run.md` `### G1` (then NOT-IMPLEMENTED: "There is no control to create a new grid or choose another size").
- Steps and observed:
  - Grid panel text read from the page: "Grid / Black square / New grid / 11×11 / 15×15 / 21×21 / Saved grids / Open saved". Stats on load `Total 225 Black 0·0.0% Filled 0.0% Words 30`.
  - Clicked `11×11` → `Total 121 Black 0·0.0% Filled 0.0% Words 22`; clicked `15×15` → `Total 225 Black 0·0.0% Filled 0.0% Words 30`. No confirm appeared (the grid was empty). The grid SVG's `aria-label` after `15×15`: "15 by 15 crossword grid".
- Console errors: see the end of G9 (one read for the area).
- 5xx: see G9.
- F-FEEDBACK notes: `11×11` and `15×15` each changed the grid and the stats line by the first read (0.7 s wait); no message or toast, none needed; no error arose.
- Observations: the 2026-10-22 finding (no control to create a grid) no longer holds: the `New grid` group with three sizes is in the Grid panel.
- Evidence: `serve-Grid.log`
- Verdict: PASS · Severity: — · Known: —

### G3 — Place a black square, discoverable (`494ddb8`)
- Phase: 8.5 · Env: E1, the `494ddb8` clone · Browser: same tab as G1 · Pre-run: continues G1's tab and storage; case definition read from `### G3` of the 2026-10-22 log (then FAIL: "Nothing in the page names it").
- Steps and observed:
  - Visible hint line read from the page: "Type letters · Arrows move · Space or . black square · Enter switch direction · Tab next word · Backspace clear". The Grid panel shows a `Black square` button, read as `disabled=true` before any cell is selected (the first button list: "Black square [disabled]").
  - Real click on a cell (row 3, column 3) → `Black square` read `disabled=false`. Clicked it (DOM `.click()`): `Total 225 Black 0·0.0% … Words 30` → `Total 225 Black 2·0.9% Filled 0.0% Words 34`; black squares read from the SVG (cells whose fill rect carries the `blacksq` shadow filter) `["r3c3","r13c13"]` (the 180° mirror, `Symmetry` on); `Undo` became enabled.
  - Key path: real click on another cell, typed `.` with the computer tool's type action → black squares `["r3c3","r6c8","r10c8","r13c13"]`, `Black 4·1.8% Words 38` (r6c8 and its mirror r10c8).
- Console errors / 5xx: see G9.
- F-FEEDBACK notes: the `Black square` click and the `.` key each changed the grid and stats within the first read (0.6 s wait); no message, none needed. No error arose.
- Observations: the control is discoverable two ways on the page (the button, the hint line); it is greyed until a cell is selected and offers no text saying why (a novice who opens the panel first sees a disabled button with no hint beside it; the hint line is below the grid). Not judged against the criterion.
- Evidence: `serve-Grid.log`
- Verdict: PASS · Severity: — · Known: —

### G8 — No Heatmap toggle (`494ddb8`)
- Phase: 8.5 · Env: E1, the `494ddb8` clone · Browser: same tab as G1 · Pre-run: continues G1's tab; case definition read from `### G8` of the 2026-10-22 log (then FAIL, Known I8: an inert `Heatmap` toggle).
- Steps and observed:
  - Full button list read from the page on load (text, `aria-label` or title): `Undo`, `Redo`, `Verify words`, `Clean grid`, `Save grid`, `◑` (Toggle theme), `Grid`, `Search`, `Autofill`, `Theme`, `Lists`, `Import`, `Export`, `Symmetry`, `Black square`, `11×11`, `15×15`, `21×21`, `Open saved`. No `Heatmap`.
  - For each rail panel (Grid, Search, Autofill, Theme, Lists, Import, Export) the page text was tested with `/heat/i` after opening it: `false` for all seven. Elements with a `title` or `aria-label` matching `/heat/i`: 0.
  - Server log window: no `/api/constraints` request (the window's requests: `/api/health`, `/api/grid/validate`, `/api/number`, `/api/wordlists`, assets).
- Console errors / 5xx: see G9.
- F-FEEDBACK notes: no grid or server action in this case.
- Evidence: `serve-Grid.log`
- Verdict: PASS · Severity: — · Known: —

### G9 — Save, reload, grid persists, restore message (`494ddb8`)
- Phase: 8.5 · Env: E1, the `494ddb8` clone · Browser: same tab as G1 · Pre-run: continues G1's tab; case definition read from `### G9` of the 2026-10-22 log (then FAIL: blank grid after reload, no restore control).
- Steps and observed:
  - Grid before saving: `15×15`, black squares `["r3c3","r6c8","r10c8","r13c13"]`, real click on row 1 column 1 and typed `CAT` → stats `Total 225 Black 4·1.8% Filled 1.4% Words 38`.
  - `Save grid` → an in-page "Name this grid" prompt, text input prefilled `15×15 2026-10-26 16:35`, buttons `Save` / `Cancel`. The header already read `saved locally · just no…` while the prompt was open (autosave). `Save` → header "saved locally · just now". `localStorage` `crossword_saved_grids`: 1 entry, `["15×15 2026-10-26 16:35",15,"2026-10-26T15:35:38.837Z"]` (name, size, savedAt).
  - Reload (`http://127.0.0.1:5000/`): the page shows `Restored "15×15 2026-10-26 16:35" (saved 2026-10-26 16:35)` with a `Start blank` button and a close `×`. Read back from the SVG: letters `CAT`, black squares `["r3c3","r6c8","r10c8","r13c13"]`, stats `Total 225 Black 4·1.8% Filled 1.4% Words 38`, identical to before the save.
- Console errors (one read for G1-G9, cleared at row start, read after the reload): browser tool, onlyErrors → "No console errors or exceptions found for this tab." (the tool had started tracking after the row's first page load, which it notes.)
- 5xx (header ruling): server log 0 of 46 requests in the window (start line 1389, `serve-Grid.log`; `requests: 46 5xx: 0 4xx: 0`: `/api/health` 13, `/api/wordlists` 9, `/api/grid/validate` 6, `/api/number` 6, `/` 2, assets). Browser tool: its network log was first read after the row and reported "No requests matching \"/api/\" found for this tab", so the server log is the count.
- F-FEEDBACK notes: `Save grid` opens the name prompt at once; after `Save` the header reads "saved locally · just now" within 0.8 s (no toast); after the reload the restore message is on the page by the first read (1.2 s); no error message appeared.
- Observations: (1) the header shows `saved locally · just now` already before `Save` is pressed in the name prompt, because autosave runs; the explicit Save only adds a named entry. (2) The restore message is the only sign that a reload restored a saved grid; `Start blank` is the way out.
- Evidence: `serve-Grid.log`
- Verdict: PASS · Severity: — · Known: —

### CL1 — No Clues tool in the rail (`494ddb8`)
- Phase: 8.5 · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, a new tab for the Hidden row (closed at the end); the CL1, A-SBS and EXPORT-HIDE blocks share that tab, one server-log window and one console read (stated in each).
- Pre-run: storage as left by the Grid row (one saved grid, restored on load); console log cleared. Server log start line 1435 (window = lines 1436-1437, `serve-Hidden.log`). Case definition read from `### CL1` of the 2026-10-22 log (then NOT-IMPLEMENTED, Known I2: a `Clue list` panel reading "Arrives in a later task.").
- Steps and observed:
  - Rail buttons read from the page by title: `Grid`, `Search`, `Autofill`, `Theme`, `Lists`, `Import`, `Export` (plus the top-bar `Undo`, `Redo`, `Verify words`, `Clean grid`, toggle theme). No `Clues`.
  - Buttons, links and tabs whose text, title or `aria-label` matches `/clue/i`: none (empty list).
  - Open issue #53 ("Clues tool is a placeholder ("Arrives in a later task") that no open issue tracks") describes the 2026-10-22 state, a placeholder panel; on `494ddb8` the control is absent, which is what the criterion asks, so #53's symptom is not reproducible as written.
- Console errors / 5xx: see EXPORT-HIDE.
- F-FEEDBACK notes: no grid or server action in this case.
- Observations: #53 is open although the placeholder is gone from the rail; the orchestrator may want to say whether the issue should be closed or re-pointed.
- Evidence: `serve-Hidden.log`
- Verdict: PASS · Severity: — · Known: #53 (symptom no longer present)

### A-SBS — No "Suggest Black Square" button in the Autofill panel (`494ddb8`)
- Phase: 8.5 · Env: E1, the `494ddb8` clone · Browser: same tab as CL1 · Pre-run: continues CL1's tab; case definition read from `### A-SBS` of the 2026-10-22 log (then NOT-IMPLEMENTED: a button disabled with the tooltip "lands in Task 20").
- Steps and observed:
  - Opened the `Autofill` rail panel; its text read from the page: "Autofill · 38 empty slots / OPTIONS / Algorithm / Repair (Recommended) / Hybrid (Beam + Repair) / Beam Search / Classic CSP / Timeout / 1 min / 2 min / 5 min / 10 min / 30 min / Min Score: 30 / Adaptive mode / Partial fill / Cleanup invalid words / WORD LISTS / BUILT-IN / Comprehensive Dictionary / Classic Crosswordese (431) / Expressions & Slang / Foreign Classics / Foreign Words / CUSTOM / Demo Words / Start Autofill".
  - Buttons on the page whose text matches `/black/i` while this panel is open: `[]` (the Grid panel's `Black square` is not rendered with it).
  - Open issue #54 ("Suggest Black Square" is a permanently disabled button pointing at Task 20 of an archived plan) describes the 2026-10-22 state; on `494ddb8` there is no such button.
- Console errors / 5xx: see EXPORT-HIDE.
- F-FEEDBACK notes: opening the panel changed the page at once (read after 0.6 s); no server action.
- Observations: as for #53, #54 is open though its symptom is gone from the UI; its server routes were not probed here.
- Evidence: `serve-Hidden.log`
- Verdict: PASS · Severity: — · Known: #54 (symptom no longer present)

### EXPORT-HIDE — Export panel shows no PDF, `.puz`, "Include clues" (`494ddb8`)
- Phase: 8.5 · Env: E1, the `494ddb8` clone · Browser: same tab as CL1 · Pre-run: continues CL1's tab. New case, defined by the plan row (no carried block).
- Steps and observed: opened the `Export` rail panel. Panel text read from the page: "Export Grid / Export Format / JSON (for reimport) / HTML (printable) / Text (simple) / Preview / Export / Format Information / JSON / Complete grid data that can be reimported into this tool / HTML / Printable webpage with styled grid / Text / Simple text representation using ■ for black squares".
  - `select` options read from the DOM: `[json=JSON (for reimport), html=HTML (printable), text=Text (simple)]`.
  - `input[type=checkbox]` count in the panel: 0 (no "Include clues" checkbox).
  - Tests on the page text: `/pdf/i` false, `/\.puz|puz\b/i` false, `/include clues/i` false, `/clue/i` false. The Format Information list has three entries (JSON, HTML, Text).
- Console errors (one read for CL1, A-SBS, EXPORT-HIDE; cleared at the row's start): browser tool, onlyErrors → "No console errors or exceptions found for this tab."
- 5xx (header ruling): server log 0 of 2 requests in the window (start line 1435, `serve-Hidden.log`; `requests: 2 5xx: 0 4xx: 0`: `/api/health` 1, `/api/wordlists` 1). The browser tool's network log was not read for this row; the server log is the count.
- F-FEEDBACK notes: opening the panel changed the page at once; no server action, no error message.
- Observations: none beyond the above.
- Evidence: `serve-Hidden.log`
- Verdict: PASS · Severity: — · Known: —

### SAVE-SIZE — A 21×21 save restores at its own size with its letters (`494ddb8`)
- Phase: 8.5 · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, this row's own tab (closed at the end of the Save group). Criterion (plan 8.5, spec S3): "The saved grid restores at its own size, with its letters".
- Pre-run: storage cleared from `/api/health` (`localStorage.length` 3 → 0; keys `crossword_saved_grids`, `xw_theme`, `crossword_symmetry_enabled`), then `http://127.0.0.1:5000/` loaded. Server log start line 1447 (window = lines 1448-1485, `serve-SAVE-SIZE.log`). The browser tool's console tracking started only at the row's end (first call), so the console read covers the reload only; two other tabs on this origin (ids 1893513492, 1893513494, not created by this row) were open throughout and not touched.
- Steps and observed:
  - `21×21` clicked on an empty 15×15 (no confirm). Selected cell r1c1 (DOM click on the cell's `rect`; a coordinate click and a click on the cell's `g` did not select it), typed `SIZEGRID` with the computer tool's type action, selected r21c21 and typed `Q`. Read from the SVG: `n` 21, letters `r1c1 S, r1c2 I, r1c3 Z, r1c4 E, r1c5 G, r1c6 R, r1c7 I, r1c8 D, r21c21 Q` (9 letters), black squares none, `Total 441 Black 0·0.0% Filled 2.0% Words 42`. This read is the "saved grid" literal the later reads are compared with.
  - `Save grid` → prompt input prefilled `21×21 2026-10-26 16:41`; replaced with `Size test 21`, `Save` → header "saved locally · just now". `crossword_saved_grids`: `[["Size test 21",21,"2026-10-26T15:41:24.944Z"]]` (name, size, savedAt).
  - `11×11` → in-page modal "Replace the current grid? Unsaved changes are lost." (it appeared although the grid had just been saved) → `Replace` → `n` 11, 0 letters, `Total 121 Black 0·0.0% Filled 0.0% Words 22`; stored entry unchanged (string equal to the one read after Save).
  - Path A, Open saved: `Open saved` listed "Size test 21 / 21×21 · 2026-10-26 16:41 / Open / Delete"; `Open` (no confirm, the grid was empty) → by script: `n` 21 equals saved 21, letters object equal to the saved literal (`true`), black squares equal (`true`), `Total 441 Black 0·0.0% Filled 2.0% Words 42`.
  - `11×11` again → modal → `Replace` → `n` 11, 0 letters, `Total 121 …`; stored entry unchanged (`crossword_saved_grids` still `[["Size test 21",21,"2026-10-26T15:41:24.944Z"]]`).
  - Path B, reload of `http://127.0.0.1:5000/`: the page read `Restored "Size test 21" (saved 2026-10-26 16:41)`; by script `n` 21, letters equal to the saved literal (`true`), `n === 21` (`true`), no black squares, `Total 441 Black 0·0.0% Filled 2.0% Words 42`.
- Console errors: browser tool, onlyErrors → "No console errors or exceptions found for this tab." (tracking began at the end of the row, see Pre-run).
- 5xx (header ruling): server log 0 of 38 requests in the window (`requests: 38 5xx: 0 4xx: 0`: `/api/health` 14, `/api/grid/validate` 6, `/api/number` 6, assets). Browser tool: "No requests matching \"/api/\" found for this tab" (its tracking began after the actions).
- F-FEEDBACK notes: `21×21`, `11×11`+`Replace`, `Open` each changed the grid and stats by the first read (0.8-1.0 s); `Save` → header "saved locally · just now" within 0.9 s; reload shows `Restored "Size test 21" (saved 2026-10-26 16:41)` at once; `Open` shows no message that a save was opened (as in F-RESTORE). No error message appeared.
- Observations (not judged against a criterion): (1) `New grid` asks for the replace confirm on a grid that was just saved, because it holds letters. (2) A coordinate click and a click on the cell's `g` did not select a cell in this tab; the cell `rect` DOM click worked (tool-side, not a finding).
- Evidence: `serve-SAVE-SIZE.log`
- Verdict: PASS · Severity: — · Known: —

### SAVE-TABS — Two tabs on one saved grid: the second save forks `<name> (copy)` (`494ddb8`)
- Phase: 8.5 · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, two tabs of this row: tab 1 (the SAVE-SIZE tab, reloaded) and tab 2 (created for this row, closed at its end). Criterion (plan 8.5, spec S4): "The second save forks `<name> (copy)`; neither tab's work is lost".
- Pre-run: storage as left by SAVE-SIZE (one entry, `Size test 21`); console log cleared on tab 1 at row start (tab 2's tracking began at the end). Server log start line 1495 (window = lines 1496-1510, `serve-SAVE-TABS.log`).
- Steps and observed:
  - Both tabs loaded `http://127.0.0.1:5000/`; each read `Restored "Size test 21" (saved 2026-10-26 16:41)` and the same 9 letters (`SIZEGRID` in row 1, `Q` at r21c21); stored `[["Size test 21",21,"2026-10-26T15:41:24.944Z"]]`.
  - Tab 1: selected r3c1 (DOM click on the cell `rect`), typed `AAA` (real key events). Header "unsaved changes". `Save grid` → prompt prefilled `Size test 21` → `Save`: header "saved locally · just now" (read 4 times over 1.6 s), no other message and no name-collision confirm; stored `[["Size test 21",21,"2026-10-26T15:44:37.364Z"]]` (savedAt changed).
  - Tab 2 (still holding the 16:41 state): selected r5c1, typed `BBB`; header "unsaved changes". `Save grid` → prompt prefilled `Size test 21` → `Save`. Page text read 5 times over 2 s (filtering for `saved|unsaved|copy|conflict|another tab|changed|replace`): only "Saved grids // Open saved"; no message, no confirm, and the header status line was **absent** (header text: `Undo | Redo | Verify words | Clean grid | Save grid | ◑`). Stored afterwards.
  - `crossword_saved_grids` names/size/savedAt, as read: `[["Size test 21 (copy)",21,"2026-10-26T15:44:45.048Z"],["Size test 21",21,"2026-10-26T15:44:37.364Z"]]`; ids `cdb1432f-d24a-42fd-8cc2-38d37a927047` (copy) and `95623e67-8679-42b7-be50-f8d3b7319437`. Tab 2's `Open saved` listed: "Size test 21 (copy) / 21×21 · 2026-10-26 16:44 / Open / Delete / Size test 21 / 21×21 · 2026-10-26 16:44 / Open / Delete".
  - Each entry's grid read from storage (letters by cell): `Size test 21` has `SIZEGRID`, `r3c1 A, r3c2 A, r3c3 A`, `r21c21 Q` (tab 1's edit, no `B`); `Size test 21 (copy)` has `SIZEGRID`, `r5c1 B, r5c2 B, r5c3 B`, `r21c21 Q` (tab 2's edit, no `A`). Neither edit is lost; neither entry holds both.
  - Tab 1 afterwards: header "saved locally · just now", grid still carries `AAA` and no `B`.
- Console errors: browser tool, onlyErrors, tab 1 and tab 2 → each "No console errors or exceptions found for this tab." (tab 2's tracking began at the end of the row).
- 5xx (header ruling): server log 0 of 15 requests in the window (`requests: 15 5xx: 0 4xx: 0`: `/api/health` 7, `/api/grid/validate` 1, `/api/number` 1, assets). Browser tool: not read for `/api/` (tracking not started before the actions); the server log is the count.
- F-FEEDBACK notes: tab 1's `Save` → "saved locally · just now" within 0.4 s. Tab 2's `Save` forked a new entry with **no visible feedback**: no message that the grid was saved under another name, no status line, no toast, read for 2 s; the user finds out only by opening `Open saved` and seeing `Size test 21 (copy)`. No error message appeared.
- Observations (not judged against a criterion; the criterion asks that the second save forks and neither work is lost, both met): (1) the fork is silent, which a novice would read as a save that overwrote the first tab's work, or as nothing happening; the header status line was empty in tab 2 after the fork. (2) The stored `savedAt` of the two entries differ by 8 s, the interval between the two `Save` clicks.
- Evidence: `serve-SAVE-TABS.log`
- Verdict: PASS · Severity: — · Known: —

### SAVE-NAMED — Autosave one entry per grid, name prompt only on Save, Open confirm, Delete confirm, quota text (`494ddb8`)
- Phase: 8.5 · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, the SAVE-TABS tab 1 (closed at the end of this row). Criterion (plan 8.5): "Autosave keeps one entry per grid; the name prompt appears only on Save; Open asks the confirm; the quota text shows on an explicit Save".
- Pre-run: storage cleared from `/api/health` (`localStorage.length` 3 → 0; keys `crossword_saved_grids`, `xw_theme`, `crossword_symmetry_enabled`), then `http://127.0.0.1:5000/` loaded; console log cleared at row start. Server log start line 1516 (window = lines 1517-1561, `serve-SAVE-NAMED.log`). A `MutationObserver` on the page counted every appearance of a text input (the name prompt is the only one on screen) as one count of the prompt counter.
- Steps and observed:
  - Autosave, grid 1 (15×15): typed `ONE` at r1c1 (real key events). Header "unsaved changes" on every read for 4 s; `crossword_saved_grids` empty. After 15.5 s of polling the entry appeared (autosave interval is 30 s per spec §3.4): `[["15×15 2026-10-26 16:47",15,"2026-10-26T15:47:06.635Z","7f53e743","ONE"]]` (name, size, savedAt, id prefix, letters in the saved grid), header "saved locally · just now", prompt counter 0.
  - Further edit: typed `TWO` at r2c1; after 30.1 s the same entry id `7f53e743` read `["15×15 2026-10-26 16:47",15,"2026-10-26T15:47:41.617Z","7f53e743","ONETWO"]` (one entry, name kept, savedAt advanced); prompt counter still 0.
  - Grid 2: `15×15` → modal "Replace the current grid? Unsaved changes are lost." → `Replace` → empty grid; typed `SECOND` at r1c1; after 30.1 s two entries: `[["15×15 2026-10-26 16:48",15,"2026-10-26T15:48:18.267Z","806f4fa7","SECOND"],["15×15 2026-10-26 16:47",15,"2026-10-26T15:47:41.617Z","7f53e743","ONETWO"]]` (one entry per grid, ids differ); prompt counter 0.
  - `Save grid` → "Name this grid" text input prefilled `15×15 2026-10-26 16:48`; prompt counter 0 → 1. Typed `Second grid`, `Save` → header "saved locally · just now"; entries `[["Second grid",15,"2026-10-26T15:48:23.663Z","806f4fa7","SECOND"],["15×15 2026-10-26 16:47",15,"2026-10-26T15:47:41.617Z","7f53e743","ONETWO"]]` (same id `806f4fa7` renamed in place, still two entries).
  - Reload of `http://127.0.0.1:5000/`: no text input on the page (count 0), no "Name this grid"; page read `Restored "Second grid" (saved 2026-10-26 16:48)`. So the prompt appeared only on `Save grid`: autosave (three writes, none prompted) and reload produced none.
  - Open confirm: typed `X` at r10c1 (header "unsaved changes"), `Open saved` listed two rows each with `Open` / `Delete`; clicked `Open` on `15×15 2026-10-26 16:47` → in-page modal text: "Replace the current grid? Unsaved changes are lost." with `Replace` / `Cancel`; `Replace` → grid letters `r1c1 O, r1c2 N, r1c3 E, r2c1 T, r2c2 W, r2c3 O` (the ONETWO save), header status line absent.
  - Delete confirm: before clicking, `window.confirm` was replaced with a recorder returning `false` (as a check that the dialog is not native) and `[role=dialog]` queried: `false`; `Delete` on `Second grid` → in-page text `Delete "Second grid"?` with `Delete` / `Cancel` shown in the saved-grids list; `window.__confirms` read `[]` (the native confirm was never called, so the modal is in-page and no stub was needed). `Cancel` → confirm gone, storage names `["Second grid","15×15 2026-10-26 16:47"]` (kept). `Delete` again → `Delete "Second grid"?` → confirm's `Delete` → storage `[["15×15 2026-10-26 16:47",15,"2026-10-26T15:47:41.617Z","7f53e743","ONETWO"]]`; list "Saved grids / Open saved / 15×15 2026-10-26 16:47 / 15×15 · 2026-10-26 16:47 / Open / Delete"; the open grid (ONETWO) stayed on the page.
  - Quota (last): `localStorage` before the fill: `length` 3, 28592 characters. Filled with filler keys `zz_fill_0..15` (1,000,000 / 100,000 / 10,000 / 1,000 / 100 / 10 / 1-character values, each size until `setItem` threw): 16 keys, 5,214,130 value characters; total of key plus value characters 5,242,872 (10,485,744 bytes at two bytes per character); `localStorage.length` 19. Error thrown by the next 1-character write: `QuotaExceededError: Failed to execute 'setItem' on 'Storage': Setting the value of 'zz_fill_16' exceeded the quota.` Then `Save grid`, typed the name `Quota test grid with a deliberately longer name`, `Save`: a banner read (6 reads over 2.4 s, unchanged) "Could not save: browser storage is full. Delete a saved grid or export this one." with a `×`; storage unchanged (same entries, none named `Quota test grid …`); the name input stayed open with the typed name.
  - Storage cleared after the quota step (rule 8) from `/api/health`: `localStorage.length` 19 → 0 (non-filler keys `crossword_saved_grids`, `crossword_symmetry_enabled`, `xw_theme`; 16 filler keys); after loading `http://127.0.0.1:5000/` `length` 2 (`xw_theme`, `crossword_symmetry_enabled`).
- Console errors: browser tool, onlyErrors → "No console errors or exceptions found for this tab." (the tab's tracking spanned the row; each navigation resets it).
- 5xx (header ruling): server log 0 of 45 requests in the window (`requests: 45 5xx: 0 4xx: 0`: `/api/health` 21, `/api/grid/validate` 3, `/api/number` 3, assets). Browser tool: not read for `/api/` (no network call needed for this row).
- F-FEEDBACK notes: autosave writes show "saved locally · just now" in the header with no toast; a typed letter changes the grid at once. `Save grid` → prompt at once; `Save` → status within 0.9 s. `Open` → the replace confirm at once, grid replaced within 1 s, no message that a save was opened. `Delete` → confirm at once; Cancel and Delete each updated the list within 0.7-0.9 s. The quota failure shows the banner within the first read (0.4 s): "Could not save: browser storage is full. Delete a saved grid or export this one." — plain language, no stack trace, no raw JSON, no HTTP code; it names the two ways out.
- Observations (not judged against a criterion): (1) The first autosave appeared 15.5 s into my polling, which began about 4 s after typing, so roughly 20 s after the first edit rather than 30 s (spec §3.4 says a 30 s autosave); the two later autosaves came 30.07 s after the edit. Timing was not read from the app, so this is not judged. (2) The Open confirm wording ("Replace the current grid? Unsaved changes are lost.") is the same as New grid's and does not name the save being opened. (3) After a failed explicit Save the name prompt stays open with the typed name. (4) `Delete`'s confirm is shown inside the list above the row, with `Delete` as the first button in DOM order.
- Evidence: `serve-SAVE-NAMED.log`
- Verdict: PASS · Severity: — · Known: —

### SR-PLACE — Place a Search result across a black square and a theme-locked cell (`494ddb8`)
- Phase: 8.5 · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, this row's own tab (id 1893513507, closed at the end of CL-CLEAN-GUARD); tab 1893513492, not created by this row, was open throughout and not touched. Criterion (plan 8.5, Grid guards): "Protected cells unchanged".
- Pre-run: storage cleared from `/api/health` (`localStorage.length` 2 → 0; keys `xw_theme`, `crossword_symmetry_enabled`), then `http://127.0.0.1:5000/` loaded; console log first read at row start. Server log start line 1576 (window = lines 1577-1616, `serve-SR-PLACE.log`). Fixture `fixture-theme-grid-guards.txt` (one word, `ENIGMA`). Cells below are read from the SVG (`r<row>c<col>`, 1-based; a locked cell carries the accent triangle `path`, a black square has `rect` fill `var(--ink)`).
- Steps and observed:
  - Theme `Choose File` (the file-upload tool) → `Loaded Words (1)`, suggestion "ENIGMA (6 letters) / Row 7, Col 8 (across) / 100/100 / Good horizontal position". `Apply This Placement` → by the DOM: ENIGMA at r8c9-r8c14, all six cells locked, and black squares added at r8c8, r8c15 and r8c1 (the panel's "Row 7, Col 8" is the DOM's row 8, col 9 less one: the panel counts from 0, the grid numbers from 1; see Observations).
  - Black squares r5c10 and r11c10 placed by DOM click + `.` typed (Symmetry on, mirrors r11c6, r5c6). Black squares read: `5,6 5,10 8,1 8,8 8,15 11,6 11,10` (7; stats `Total 225 | Black 7·3.1%`). Column 10 is now a down slot r6c10-r10c10 (5 cells), bounded by blacks at r5c10 and r11c10, with the locked `N` at r8c10.
  - Search panel, r7c10 selected, `Enter` → "Selected: Row 7, Col 10 (down)"; pattern `?????`, second `Search` button → `Results (50)`, first result `AEONS` (third letter `O`, the locked cell holds `N`).
  - Placement 1, selected r7c10 (mid-slot): grid before (rows joined by `/`) `.............../.............../.............../.............../.....#...#...../.............../.............../#......#ENIGMA#/.............../.............../.....#...#...../.............../.............../.............../...............`; clicked the `AEONS` result → after `.............../.............../.............../.............../.....#...#...../.............../.........A...../#......#ENIGMA#/.........O...../.........N...../.....#...#...../.............../.............../.............../...............`. Changed cells: `r7c10 . → A`, `r9c10 . → O`, `r10c10 . → N`. The word was written from the selected cell: `A` r7, `E` skipped over the locked `N` at r8, `O` r9, `N` r10, and the `S` that would fall on the black r11c10 was not written. Locked cells before `8,9E 8,10N 8,11I 8,12G 8,13M 8,14A`, after the same; black squares before and after the same seven.
  - Placement 2, selected r6c10 (slot start): before = placement 1's result; clicked `AEONS` again → after `.............../.............../.............../.............../.....#...#...../.........A...../.........E...../#......#ENIGMA#/.........N...../.........S...../.....#...#...../.............../.............../.............../...............`. Changed cells: `r6c10 . → A`, `r7c10 A → E`, `r9c10 O → N`, `r10c10 N → S`; r8c10 stayed the locked `N` though the word's third letter is `O`. Locked cells after `8,9E 8,10N 8,11I 8,12G 8,13M 8,14A` (6, unchanged); black squares after `5,6 5,10 8,1 8,8 8,15 11,6 11,10` (7, unchanged); `Total 225 | Black 7·3.1% | Filled 4.6%`.
  - Message: none. The toast stack was empty on reads 0.25-2.0 s after each click and on a read after the row; the page text held no "locked" or "skipped" wording. The UI did not stop me choosing a result that differs at the locked cell; it placed the word around the locked cell.
- Console errors: browser tool, onlyErrors → "No console errors or exceptions found for this tab." (tracking started at the row's first call).
- 5xx (header ruling): server log 0 of 40 requests in the window (`requests: 40 5xx: 0 4xx: 0`: `/api/health` 17, `/api/grid/validate` 4, `/api/number` 4, `/api/theme/suggest-placements` 4, `/api/theme/upload` 1, `/api/theme/apply-placement` 1, `/api/wordlists` 1, `/api/progress/` 1, assets; the progress GET is not from this row's tab as far as I could tell, tab 1893513492 being open). Browser tool: "No requests matching \"/api/\" found for this tab" (its tracking began after the actions).
- F-FEEDBACK notes: `Apply This Placement` changed the grid at once (first read 0.8 s); each Search result click changed the grid by the first read (1.2 s), the header showed "unsaved changes"; no toast or message for either placement, including the one that kept the locked letter in place of the word's `O` and the one that dropped the `S` over the black square. No error message appeared.
- Observations (not judged against a criterion): (1) A result placed over a slot with a locked cell silently keeps the locked letter, so the grid holds a word that is not the chosen result (placement 2 left r6c10-r10c10 reading `A, E, N(locked), N, S` = `AENNS`, not `AEONS`), with no message; a novice cannot tell the word was altered. (2) A result is written from the selected cell, not the slot start: placement 1 started at `r7`, dropped letters past the black square and left `r6` empty. (3) The Theme panel's "Row 7, Col 8" is the zero-based position of what the grid shows as row 8, col 9.
- Evidence: `serve-SR-PLACE.log`, `fixture-theme-grid-guards.txt`
- Verdict: PASS · Severity: — · Known: —

### CL-CLEAR — Verify flags cells, retype them, Clean (`494ddb8`)
- Phase: 8.5 · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, the SR-PLACE tab (id 1893513507). Criterion (plan 8.5, Grid guards): "no red cells after \"Grid is clean\"".
- Pre-run: storage cleared from `/api/health` (`localStorage.length` 3 → 0; keys `crossword_saved_grids`, `xw_theme`, `crossword_symmetry_enabled`), then `http://127.0.0.1:5000/` loaded; console first read was at SR-PLACE's start and not reset. Server log start line 1616 (the line count after SR-PLACE; window = lines 1617-1634, `serve-CL-CLEAR.log`, which therefore includes the storage-clear page and the reload). Red = a letter `text` with `fill="var(--danger)"` (the same cells carry `var(--ink)` before Verify).
- Steps and observed:
  - Black square r1c6 placed by DOM click + `.` (mirror r15c10). Selected r1c1, typed `ZQXJV` (real key events): row 1 `ZQXJV#........./`; slot r1c1-r1c5 is a 5-cell across slot. Red cells: 0.
  - `Verify words` → letters `r1c1 Z`, `r1c2 Q`, `r1c3 X`, `r1c4 J`, `r1c5 V` read red (5 red cells). The Verify message was not captured: my read came 2.5 s after the click and the toast had gone, so I quote none.
  - Selected r1c1, typed `ABOUT` over them: row 1 `ABOUT#........./`; red cells read: `1,1A 1,2B 1,3O 1,4U 1,5T` (5; the red marks survive retyping).
  - `Clean grid` → no confirm (no `[role=dialog]` in 10 reads over 3 s); toast, first read 0.3 s: "Grid is clean — all words are valid!×". Red cells read after it: 0 (`[]`); grid unchanged, row 1 `ABOUT#........./`.
  - #79 (red slots crossing a removed word stay red) does not apply here: Clean removed no word; the retyped slot crossed no filled slot.
- Console errors: browser tool, onlyErrors → "No console errors or exceptions found for this tab."
- 5xx (header ruling): server log 0 of 18 requests in the window (`requests: 18 5xx: 0 4xx: 0`: `/api/health` 6, `/api/grid/verify-words` 1, `/api/grid/clean` 1, `/api/grid/validate` 2, `/api/number` 2, assets). Browser tool: "No requests matching \"/api/\" found for this tab" (tracking began after the actions).
- F-FEEDBACK notes: `Verify words` marked the letters red within 2.5 s (first read); `Clean grid` showed the toast "Grid is clean — all words are valid!" at the first read (0.3 s) and the red marks went at once. Retyping left the old red marks on the new letters, so a novice sees valid-looking `ABOUT` in red until Clean. No error message appeared.
- Observations (not judged against a criterion): the case was driven on a grid whose invalid word crossed nothing, which is the case the criterion names; the #79 crossing case is not exercised by this row.
- Evidence: `serve-CL-CLEAR.log`
- Verdict: PASS · Severity: — · Known: —

### CL-CLEAN-GUARD — Clean's confirm count, Cancel, and accepted Clean with a theme-locked word (`494ddb8`)
- Phase: 8.5 · Env: E1, the `494ddb8` clone · Browser: Chrome at `http://127.0.0.1:5000`, the SR-PLACE tab (id 1893513507, closed at the end of this row); tab 1893513492, not created by this row, was open throughout and not touched. Criterion (plan 8.5): "The confirm shows `Clean will remove N letters` with `N` equal to the non-theme-locked letters in the slots Clean flags (Clean blanks every cell of a flagged slot, so a crossing letter counts too); Cancel changes nothing, including `isError`; accepting removes those letters and every theme-locked letter is unchanged".
- Pre-run: storage cleared from `/api/health` (`localStorage.length` 3 → 0; keys `crossword_saved_grids`, `xw_theme`, `crossword_symmetry_enabled`), then `http://127.0.0.1:5000/` loaded; console first read was at SR-PLACE's start and not reset. Server log start line 1645 (window = lines 1646-1682, `serve-CL-CLEAN-GUARD.log`). Fixture `fixture-theme-grid-guards.txt` (`ENIGMA`). Cells are read from the SVG as in SR-PLACE; a red letter is a `text` with `fill="var(--danger)"`.
- Steps and observed:
  - Setup: Theme upload of `fixture-theme-grid-guards.txt` (file-upload tool), `Apply This Placement` → ENIGMA locked at r8c9-r8c14 (blacks r8c1, r8c8, r8c15). Black squares by DOM click + `.` at r1c6, r5c10, r11c10, r4c1 (Symmetry on adds the mirrors). Typed with real key events: `ZQXJV` in r1c1-r1c5; `A` r2c1, `P` r3c1 (so the down slot r1c1-r3c1 reads `ZAP` and crosses `ZQXJV` at the `Z`); `Q` r6c10, `X` r7c10, `J` r9c10, `Z` r10c10 (the down slot r6c10-r10c10 reads `QXNJZ` across the locked `N` at r8c10). Grid, rows joined by `/`: `ZQXJV#........./A............../P............../#............../.....#...#...../.........Q...../.........X...../#......#ENIGMA#/.........J...../.........Z...../.....#...#...../..............#/.............../.............../.........#.....`; `Total 225 | Black 11·4.9% | Filled 7.9%` (17 letters).
  - `Verify words` → toast "3 of 19 words flagged — 2 invalid: ZQXJV, QXNJZ; 1 unfillable: X______________×". Red letters read (10): r1c1 Z, r1c2 Q, r1c3 X, r1c4 J, r1c5 V, r6c10 Q, r7c10 X, r8c10 N (a locked cell), r9c10 J, r10c10 Z.
  - `N` computed before reading the confirm, by script from the DOM. Slots = maximal runs of 3 or more non-black cells; flagged = the three slots whose cell pattern equals the Verify toast's words (`ZQXJV` across r1, `QXNJZ` down c10 from r6, `X______________` down c3 from r1). Letters in the union of flagged slots: `1,1Z 1,2Q 1,3X 1,4J 1,5V 6,10Q 7,10X 8,10N^ 9,10J 10,10Z` (`^` = theme-locked); non-locked among them = **9** (`N = 9`). The `Z` at r1c1 is shared with the valid, unflagged `ZAP`: it counts once, as a letter of `ZQXJV`; `A` and `P` are not in a flagged slot and do not count.
  - `Clean grid` → in-page text "Clean will remove 9 letters" with `Clean` / `Cancel` (no native dialog; no `[role=dialog]`). Confirm 9 == computed N 9.
  - Cancel: snapshot taken before `Clean grid` (grid string, red list, lock list, letter count, stats) and after `Cancel`: `JSON.stringify` of the two snapshots equal (`true`); red list unchanged (the same 10 letters, `8,10N^` included); confirm gone; no toast.
  - Accept: `Clean grid` → "Clean will remove 9 letters" again → `Clean`. Toast, first read 0.25 s: "Removed 3 invalid words (10 cells cleared), kept 2 valid words×". Grid after: `.....#........./A............../P............../#............../.....#...#...../.............../.............../#......#ENIGMA#/.............../.............../.....#...#...../..............#/.............../.............../.........#.....`; diff against the pre-Clean grid by script: exactly 9 cells changed, all letter → blank: r1c1 Z, r1c2 Q, r1c3 X, r1c4 J, r1c5 V, r6c10 Q, r7c10 X, r9c10 J, r10c10 Z. Theme-locked letters after: `8,10N 8,11I 8,12G 8,13M 8,14A 8,9E`, equal to those before (`true`); `ENIGMA` still reads across r8. `Filled 7.9%` → `3.7%`, letters 17 → 8. `A` (r2c1) and `P` (r3c1), in no flagged slot, stayed.
  - Residual red after the accepted Clean: one letter, `8,10N` (the locked `N` of the removed `QXNJZ`); no other red cell.
- Known: #78 — the toast counts "10 cells cleared" (9 removed plus the kept locked `N`); the confirm said 9 and 9 were removed; not a FAIL. #79 — the locked `N` stays red after Clean though the slot crossing it was blanked; not the criterion.
- Console errors: browser tool, onlyErrors → "No console errors or exceptions found for this tab."
- 5xx (header ruling): server log 0 of 37 requests in the window (`requests: 37 5xx: 0 4xx: 0`: `/api/health` 9, `/api/grid/clean` 2, `/api/grid/validate` 6, `/api/number` 6, `/api/grid/verify-words` 1, `/api/theme/suggest-placements` 5, `/api/theme/upload` 1, `/api/theme/apply-placement` 1, assets). Browser tool: `/api/` network log not read (tracking was never started on this tab).
- F-FEEDBACK notes: `Verify words` toast within 0.25 s of the click; `Clean grid` → confirm within 0.5-0.6 s; `Cancel` closed it with no message (and no change) within 0.8 s; accepted `Clean` → toast at the first read (0.25 s) and the letters gone at once. The toast "Removed 3 invalid words (10 cells cleared), kept 2 valid words" is plain language; no stack trace, raw JSON or bare HTTP code. The "1 unfillable: X______________" fragment in the Verify toast is not plain language (an underscore pattern for a 15-cell slot).
- Observations (not judged against a criterion): (1) "Removed 3 invalid words" counts the unfillable `X______________` slot as a third word although only two words were typed; the confirm's 9 letters are unaffected by it. (2) The locked `N` stays red after Clean, so after the guard works the grid still shows a red theme letter, as in #79.
- Evidence: `serve-CL-CLEAN-GUARD.log`, `fixture-theme-grid-guards.txt`
- Verdict: PASS · Severity: — · Known: #78 (toast count), #79 (residual red)
