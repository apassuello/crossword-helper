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
| Grid | | |
| New: SAVE-NAMED | | |
| Grid guards | | |
| New: CL-CLEAN-GUARD | | |
| New: PORT | PASS | PORT |
| New: SETUP-MISSING | PASS | SETUP-MISSING |
| New: CLEAN-PREV | PASS | CLEAN-PREV |
| New: MACOS | PASS | MACOS |
| New: F-WORKFLOW | PASS on `494ddb8` | F-WORKFLOW |
| New: F-TOUR | PASS on `494ddb8` (FAIL on `e4e881e`, #91) | F-TOUR, F-TOUR re-run |
| New: F-IMPORT | PASS on `494ddb8` | I1, I2, I3, I4, I5, I6 |
| New: F-EDIT | | |
| New: F-THEME-LOAD | | |
| New: F-LISTS | | |
| New: F-SEARCH | | |
| New: F-EXPORT | | |
| New: F-RESTORE | | |
| New: F-FEEDBACK | | |
| Hidden | | |
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
| New: SAVE-SIZE | | |
| New: SAVE-TABS | | |
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
