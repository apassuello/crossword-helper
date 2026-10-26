# Novice-readiness acceptance run — 2026-10-26

Spec: `docs/superpowers/specs/2026-10-23-novice-readiness-design.md` §6 (0.2.20). Plan: Phase 8 of
`docs/superpowers/plans/2026-10-23-novice-readiness.md`. Case-block format and method from
`docs/dev/qa/2026-10-22-fresh-install-run.md`.

## Header

- Sha under test: `e4e881e` (origin/main after PR #90). Every clone checks out exactly that sha.
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
| New: F-WORKFLOW | | |
| New: F-TOUR | | |
| New: F-IMPORT | | |
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

