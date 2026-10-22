# Fresh-install reproduction run — 2026-10-22

## Header

- Clone target sha: 4678406 (local main; clones come from the main checkout, not origin)
- `origin/main` sha and `$MAIN` HEAD are in the fence below. origin/main lags local main until Arthur pushes; the friend's reinstall gets origin.
- E1 python: CPython 3.13.7 (cpython-3.13.7-macos-aarch64-none, uv download only)
- E1 node: node-v22.23.4-darwin-arm64.tar.gz (SHA-256 verified against SHASUMS256.txt)
- README line numbers checked against the table below: R5 is at line 62 (table said 61–62) and R19's quoted string is at `setup.sh:67` (table said 66); the table is corrected accordingly.

```
$ git -C $MAIN rev-parse --short HEAD
4678406
$ git -C $MAIN ls-remote --heads origin main
2f399496be0817d05a21947ba2261478a9494508	refs/heads/main
$ sw_vers -productVersion
26.5.2
$ /usr/bin/python3 --version
Python 3.9.6
$ /bin/bash --version | head -1
GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25)
```

## P0 — README claims

| # | README line | Claim (quoted) | Verified by | Verdict |
|---|---|---|---|---|
| R1 | 19–21 | `chmod +x setup.sh` / `./setup.sh` is the one-time setup | Task 4 | PASS |
| R2 | 23–25 | `source venv/bin/activate` then `python3 run.py` runs the app | Task 5 | PASS |
| R3 | 26 | "Open http://localhost:5000" | Task 5 | PASS |
| R4 | 46–51 | dev mode: `python3 run.py` + `npm run dev`, open :3000 | Task 5 | PASS |
| R5 | 62 | `pattern "C?T" -w data/wordlists/comprehensive.txt --json-output` | Task 10 | FAIL (I7) |
| R6 | 64 | "11x11, 15x15, and 21x21 templates included" | Task 2 | PASS |
| R7 | 65–67 | the `fill data/grids/example_15x15.json … -t 180 --min-score 30 -o filled.json` command | Task 10 | PASS |
| R8 | 70 | `validate puzzle.json` | Task 10 | PASS |
| R9 | 73 | `new --size 15 -o puzzle.json` | Task 10 | PASS |
| R10 | 76 | `export filled.json --format html -o puzzle.html` | Task 10 | PASS |
| R11 | 82–84 | `pytest` runs backend + CLI tests | Task 13 | FAIL (3 tests; cause below) |
| R12 | 86–87 | `npm test` runs the frontend tests | Task 13 | PASS (watch mode, does not exit) |
| R13 | 89–91 | `npm run test:coverage` | Task 13 | PASS (watch mode, does not exit) |
| R14 | 31–32 | "interactive editing with keyboard shortcuts, symmetry enforcement, and auto-numbering" | Task 8 | PASS |
| R15 | 33–34 | pattern `C?T` "gives CAT, COT, CUT, etc." | Task 9 | PASS |
| R16 | 35–36 | autofill "using CSP with backtracking, beam search, or iterative repair; supports theme word locking" | Task 7 | FAIL (A2, A4, A5, A7; A6 passes) |
| R17 | 37–38 | "ships with 44k curated words; upload your own or combine multiple lists" | Tasks 6, 9 | FAIL (CACHE-1) |
| R18 | 39 | "Export -- HTML format" | Task 9 | PASS |
| R19 | setup.sh:67 | "Frontend built to frontend/dist/" | Task 4 | PASS |
| R20 | 105 | the Resources PDF link resolves | Task 2 | PASS |

## Cases

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

### ENV-1 — E1 clean environment (CPython 3.13.7 + Node 22)
- Phase: P-ENV · Env: E1 · Viewport: —
- Steps: 1. `uv python install 3.13.7` with `UV_PYTHON_INSTALL_DIR` under the sandbox. 2. Download Node 22 tarball, verify SHA-256, unpack. 3. Write the sandbox E1 wrapper script and run the probe through it.
- Expected: "python3 --version prints Python 3.13.7; which -a python3 node npm print only paths under $SB/tools" (plan Task 1 criteria, spec §1.3–§1.5)
- Observed: Every criterion holds except the literal "only paths under $SB/tools": `which -a python3` also lists `/usr/bin/python3` as its second entry, behind the E1 interpreter. The plan's own mandated PATH includes `/usr/bin`, so the criterion contradicts the plan; the first resolution is the E1 interpreter and the stub is shadowed. `uv` is absent. Env contains exactly HOME, LANG, PATH, PWD, SHLVL, TERM, _.
- Evidence: evidence/ENV-1.log · evidence/ENV-1-uv.log · evidence/ENV-1-sha.log
- Verdict: PASS · Severity: — · Known: —

```
node-v22.23.4-darwin-arm64.tar.gz: OK
Python 3.13.7
/private/tmp/crossword-fresh/tools/python/cpython-3.13.7-macos-aarch64-none/bin/python3
/usr/bin/python3
/private/tmp/crossword-fresh/tools/node/bin/node
/private/tmp/crossword-fresh/tools/node/bin/npm
Package Version
------- -------
pip     24.3.1
v22.23.4
HOME=/private/tmp/crossword-fresh/home
_=/usr/bin/env
HOME=/private/tmp/crossword-fresh/home
LANG=en_US.UTF-8
PATH=/private/tmp/crossword-fresh/tools/node/bin:/private/tmp/crossword-fresh/tools/python/cpython-3.13.7-macos-aarch64-none/bin:/usr/bin:/bin:/usr/sbin:/sbin
PWD=/private/tmp/crossword-fresh/tools
SHLVL=1
TERM=xterm
uv absent (good)
```

### ENV-2 — E2 clean environment (Xcode CLT /usr/bin/python3 + Node 22)
- Phase: P-ENV · Env: E2 · Viewport: —
- Steps: 1. Write the sandbox E2 wrapper script (PATH without the E1 python segment). 2. Run the probe through it.
- Expected: "python3 --version prints Python 3.9.6 and which python3 prints /usr/bin/python3" (plan Task 1 criteria, spec §1.4)
- Observed: Python 3.9.6 at /usr/bin/python3; node under the sandbox tools; HOME is the sandbox home; uv absent.
- Evidence: evidence/ENV-2.log
- Verdict: PASS · Severity: — · Known: —

```
Python 3.9.6
/usr/bin/python3
/private/tmp/crossword-fresh/tools/node/bin/node
/private/tmp/crossword-fresh/tools/node/bin/npm
v22.23.4
HOME=/private/tmp/crossword-fresh/home
uv absent (good)
```

### CLONE-1 — Clones of main are clean
- Phase: P-Clone · Env: host · Viewport: —
- Steps: 1. `git clone --branch main` of the main checkout into the E1 and E2 sandbox directories. 2. Read HEAD and `git status --short` of the E1 clone.
- Expected: UNSPECIFIED (spec §1.2: both clones at the recorded main sha, clean)
- Observed: Both clones report the same sha, equal to the main checkout's HEAD in the header; the E1 clone's status listing is empty.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
E1 clone: 4678406   E2 clone: 4678406
dirty entries in E1 clone: 0
```

### CLONE-2 — Shipped templates and Resources PDF present (R6, R20)
- Phase: P0 · Env: host · Viewport: —
- Steps: 1. `ls -l` the three example grids and the PDF in the E1 clone.
- Expected: "11x11, 15x15, and 21x21 templates included" (README.md:64); Resources link to docs/resources/art-of-construction.pdf (README.md:105)
- Observed: All three template files and the PDF exist and are non-empty.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
-rw-r--r--  1 apa  wheel    1495 Oct 22 11:05 /private/tmp/crossword-fresh/crossword-helper/data/grids/example_11x11.json
-rw-r--r--  1 apa  wheel    2687 Oct 22 11:05 /private/tmp/crossword-fresh/crossword-helper/data/grids/example_15x15.json
-rw-r--r--  1 apa  wheel    5135 Oct 22 11:05 /private/tmp/crossword-fresh/crossword-helper/data/grids/example_21x21.json
-rw-r--r--  1 apa  wheel  381224 Oct 22 11:05 /private/tmp/crossword-fresh/crossword-helper/docs/resources/art-of-construction.pdf
```

### CLONE-3 — Wordlist cache mtimes in a fresh clone (I7 evidence)
- Phase: P0 · Env: host · Viewport: —
- Steps: 1. `stat` the .txt and sibling .pkl of two shipped lists, plus the byte size of the scored list.
- Expected: UNSPECIFIED (evidence for the cache-preference variable, spec §2.4; used by Tasks 7 and 11)
- Observed: Each .pkl carries the same mtime, to the second, as its .txt, so the rule "prefer .pkl when its mtime >= the .txt's" (I7) selects the .pkl on a fresh clone.
- Evidence: —
- Verdict: UNSPECIFIED · Severity: — · Known: I7

```
2026-10-22T11:05:50 /private/tmp/crossword-fresh/crossword-helper/data/wordlists/comprehensive.txt
2026-10-22T11:05:50 /private/tmp/crossword-fresh/crossword-helper/data/wordlists/comprehensive.pkl
2026-10-22T11:05:51 /private/tmp/crossword-fresh/crossword-helper/data/wordlists/top_100k.txt
2026-10-22T11:05:51 /private/tmp/crossword-fresh/crossword-helper/data/wordlists/top_100k.pkl
 6590415 /private/tmp/crossword-fresh/crossword-helper/data/wordlists/comprehensive_scored.txt
```

### FIX-1 — Upload fixtures F1-F9 built
- Phase: P-Fixtures · Env: host · Viewport: —
- Steps: 1. Write F1-F9 with printf/head/cp. 2. Verify sizes, line endings, encoding and byte-identity of F9.
- Expected: UNSPECIFIED (plan Task 3 contents table)
- Observed: F5 has CRLF terminators, F7 is UTF-8, F8 is zero bytes, F9 is byte-identical to the scored list.
- Evidence: evidence/FIX-1.log
- Verdict: PASS · Severity: — · Known: —

```
      19 /private/tmp/crossword-fresh/fixtures/F1-plain-lf.txt
      28 /private/tmp/crossword-fresh/fixtures/F2-scored-semicolon.txt
      28 /private/tmp/crossword-fresh/fixtures/F3-scored-comma.txt
      29 /private/tmp/crossword-fresh/fixtures/F4-csv-header.csv
      22 /private/tmp/crossword-fresh/fixtures/F5-crlf.txt
     227 /private/tmp/crossword-fresh/fixtures/F6-dict.dict
      19 /private/tmp/crossword-fresh/fixtures/F7-nonascii.txt
       0 /private/tmp/crossword-fresh/fixtures/F8-empty.txt
 6590415 /private/tmp/crossword-fresh/fixtures/F9-large.txt
 6590787 total
/private/tmp/crossword-fresh/fixtures/F5-crlf.txt:     ASCII text, with CRLF line terminators
/private/tmp/crossword-fresh/fixtures/F7-nonascii.txt: Unicode text, UTF-8 text
00000000: 4150 504c 450d 0a42 4552 5259 0d0a 4348  APPLE..BERRY..CH
00000010: 4552 5259 0d0a                           ERRY..
F9 identical
```

### SETUP-1 — README setup commands on E1 (R1)
- Phase: P1-setup · Env: E1 · Viewport: —
- Steps: 1. From the clone root under the E1 wrapper: `chmod +x setup.sh` then `./setup.sh`, timed.
- Expected: "chmod +x setup.sh" / "./setup.sh" as the one-time setup (README.md:19-21)
- Observed: Exit code 0; setup ran to "Setup complete". The frontend build printed Dart Sass "legacy-js-api" deprecation warnings (cosmetic, no failure).
- Evidence: evidence/SETUP-1.log
- Verdict: PASS · Severity: S4 (build-time deprecation noise) · Known: —

```
rc=0 (read on its own line after the timed subshell)
18:DEPRECATION WARNING [legacy-js-api]: The legacy JS API is deprecated and will be removed in Dart Sass 2.0.0.
22:DEPRECATION WARNING [legacy-js-api]: The legacy JS API is deprecated and will be removed in Dart Sass 2.0.0.
$SB/e1.sh "cd $C && chmod +x setup.sh && ./setup.sh"  8.52s user 3.33s system 36% cpu 32.159 total
```

### SETUP-2 — Post-conditions of setup (R19)
- Phase: P1-setup · Env: E1 · Viewport: —
- Steps: 1. `venv/bin/python --version`, `venv/bin/pip list`, `npm ls --depth=0`, `ls -l frontend/dist/index.html`.
- Expected: "Frontend built to frontend/dist/" (setup.sh:67)
- Observed: venv uses the E1 interpreter; pytest, coverage and pytest-cov are installed by setup (relevant to R11/R13); vitest and its coverage plugin are in the npm tree; frontend/dist/index.html exists.
- Evidence: evidence/SETUP-2.log
- Verdict: PASS · Severity: — · Known: —

```
Python 3.13.7
Package            Version
------------------ ----------
black              26.10.1
blinker            1.9.0
certifi            2026.10.19
cfgv               3.5.0
charset-normalizer 3.5.2
click              8.1.7
coverage           7.16.2
distlib            0.4.4
execnet            2.1.2
filelock           4.2.4
flake8             7.4.1
Flask              3.0.0
Flask-Cors         4.0.0
identify           2.6.20
idna               3.20
iniconfig          2.3.1
isort              9.0.2
itsdangerous       2.2.0
Jinja2             3.1.6
markdown-it-py     4.2.0
MarkupSafe         3.0.4
mccabe             0.7.0
mdurl              0.1.2
mypy_extensions    1.1.0
nodeenv            1.11.0
numpy              2.5.4
packaging          26.3
pathspec           1.1.1
pip                26.2.2
platformdirs       4.13.5
pluggy             1.7.0
pre_commit         4.7.0
pycodestyle        2.15.0
pyflakes           4.0.3
Pygments           2.21.0
pytest             7.4.3
pytest-asyncio     0.23.2
pytest-cov         4.1.0
pytest-mock        3.12.0
pytest-xdist       3.5.0
python-discovery   1.6.4
pytokens           0.4.1
PyYAML             6.0.3
requests           2.31.0
rich               13.7.0
ruff               0.17.1
urllib3            2.8.0
virtualenv         21.14.12
Werkzeug           3.1.9
crossword-helper@1.0.0 /private/tmp/crossword-fresh/crossword-helper
├── @fontsource-variable/fraunces@5.2.9
├── @fontsource-variable/jetbrains-mono@5.2.8
├── @fontsource-variable/work-sans@5.2.8
├── @testing-library/jest-dom@6.9.1
├── @testing-library/react@14.3.1
├── @testing-library/user-event@14.6.1
├── @vitejs/plugin-react@4.7.0
├── @vitest/coverage-v8@1.6.1
├── @vitest/ui@1.6.1
├── classnames@2.5.1
├── jsdom@23.2.0
├── msw@2.12.7
├── react-dom@18.3.1
├── react-hot-toast@2.6.0
├── react@18.3.1
├── sass@1.97.1
├── vite@5.4.21
└── vitest@1.6.1

-rw-r--r--  1 apa  wheel  1107 Oct 22 11:07 frontend/dist/index.html
```

### SERVE-0 — Ports 5000 and 3000 free before start
- Phase: P2-serve · Env: host · Viewport: —
- Steps: 1. `lsof -nP -iTCP:5000 -sTCP:LISTEN` and the same for 3000 before starting any server.
- Expected: UNSPECIFIED (pre-check; a foreign listener on 5000 would be an S1 finding)
- Observed: Neither port had a listener on this host. This does not exercise the macOS AirPlay-Receiver-on-5000 case; that case is NOT-TESTABLE here because the setting is off.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

### SERVE-1 — Production mode serves the SPA and API (R2, R3)
- Phase: P2-serve · Env: E1 · Viewport: —
- Steps: 1. `source venv/bin/activate` then `python3 run.py` under the E1 wrapper, in the background. 2. `GET /` and `GET /api/health` with curl.
- Expected: "python3 run.py" then "Open http://localhost:5000" (README.md:23-26)
- Observed: Server healthy within 2 s; `GET /` returns 200 text/html containing `<div id="root">`; `/api/health` returns 200 application/json. The server runs in Flask debug mode (Werkzeug debugger active, with a PIN) and prints the development-server warning.
- Evidence: evidence/SERVE-run.log
- Verdict: PASS · Severity: S4 (debug mode on by default in run.py output) · Known: —

```
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/ ; grep -c "<div id=\"root\">"
200 / 1 match
 * Serving Flask app 'backend.app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://localhost:5000
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 832-053-023
127.0.0.1 - - [22/Oct/2026 11:08:38] "GET /api/health HTTP/1.1" 200 -
```

### SERVE-2 — Dev mode on :3000 with API proxy (R4)
- Phase: P2-serve · Env: E1 · Viewport: —
- Steps: 1. With Flask up, `npm run dev` in the background. 2. curl `http://localhost:3000/` and `http://localhost:3000/api/health`. 3. Stop the dev server, leave Flask up.
- Expected: "npm run dev" ... "Open http://localhost:3000" (README.md:46-54)
- Observed: `/` returns 200; `/api/health` through the proxy returns 200 with the health JSON. Vite reports its listen address as 127.0.0.1, not localhost; curl reached it via localhost, the browser case is re-checked in L16.
- Evidence: evidence/SERVE-dev.log
- Verdict: PASS · Severity: — · Known: —

```
> vite


  VITE v5.4.21  ready in 78 ms

  ➜  Local:   http://127.0.0.1:3000/
DEPRECATION WARNING [legacy-js-api]: The legacy JS API is deprecated and will be removed in Dart Sass 2.0.0.
```

### ENV-3 — Browser viewport cannot be set to the plan's sizes
- Phase: P3-lists · Env: host · Viewport: —
- Steps: 1. the browser tool's window-resize action to 1440x900, twice. 2. Read `innerWidth/innerHeight/outerWidth/devicePixelRatio` from the page on localhost and on 127.0.0.1.
- Expected: UNSPECIFIED (plan Task 6: window resized to 1440x900)
- Observed: The resize call reports success but does not change the window. On `localhost` Chrome holds a stored 75% page zoom for that host, so the CSS viewport is far larger than the window; on `127.0.0.1` the zoom is 100% and the viewport equals the window. Neither is 1440x900. Method deviation (test method only, nothing measured differently): functional cases run top-level on `127.0.0.1:5000`; layout cases L3 and L4 are measured inside a same-origin iframe sized exactly 1440x900 and 1024x768 (the iframe's own `innerWidth/innerHeight` are the CSS viewport) and also top-level. The README says to open localhost; the zoom stored for that host is the user's own setting and was not changed.
- Evidence: —
- Verdict: NOT-TESTABLE · Severity: — · Known: —

```
localhost:5000     inner [2400,1389] outer [1800,1042] screen [1800,1169] dpr 1.5
127.0.0.1:5000     inner [1800,1042] outer [1800,1042] dpr 2
```

### L1 — Lists tool opens; lists shown equal GET /api/wordlists
- Phase: P3-lists · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Open `http://127.0.0.1:5000/`. 2. Click the Lists tool-rail button. 3. Compare the list names in the DOM, in order, with `GET /api/wordlists`.
- Expected: UI label "Lists"; the names from the API
- Observed: The Lists tool opens ("Word List Management", category buttons, "Upload Wordlist"). The names shown match the API names exactly, in the same order (the heading "All Wordlists" carries the total).
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

### L2 — Opening a list renders entries and a stats control
- Phase: P3-lists · Env: E1 · Viewport: 1800×1042
- Steps: 1. Click "Top 50K" in the list.
- Expected: UI (list contents shown; buttons "Show Stats", "Add Words")
- Observed: A detail card appears with the list's name, a words heading, word chips, and the "Show Stats" / "Add Words" buttons.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

### L3 — Lists box visibility and scrolling at 1440×900
- Phase: P3-lists · Env: E1 · Viewport: 1440×900 (iframe, see ENV-3)
- Steps: 1. Load the app in a 1440x900 iframe, open Lists. 2. Measure `.wordlist-list` and its scroll container. 3. Wheel-scroll 5 ticks over the sidebar.
- Expected: "The box is not visible" is FAIL when visibleInViewport is false (plan Task 6 criteria); "can't scroll" is FAIL when the wheel does not change scrollTop. The expectation that the list be usable is UNSPECIFIED in the README.
- Observed: On load the `.wordlist-list` box starts below the bottom edge of its scrolling container (`.sidebar`), so none of the list is visible until the user scrolls the sidebar; the category buttons take the container's whole initial view. `.wordlist-list` itself has overflow visible and no scroll of its own. The wheel over the sidebar does scroll it and the list then comes into view, so "can't scroll" does not reproduce here; "box not visible on open" does.
- Evidence: evidence/L3.json
- Verdict: FAIL · Severity: S2 · Known: —

```json
{"case":"L3","method":"same-origin iframe sized 1440x900 on http://127.0.0.1:5000/api/health, app loaded at /","viewport":[1440,900],
 "list":{"selector":".wordlist-list","rect":{"x":1037,"y":632,"w":339,"h":1234},"scrollHeight":1234,"clientHeight":1234,"overflowY":"visible","visibleInViewport":false},
 "scroll_container":{"selector":".sidebar","rect":{"x":1013,"y":170,"w":395,"h":372},"scrollHeight":1733,"clientHeight":372,"overflowY":"auto"},
 "panel":{"selector":".wordlist-panel","rect":{"x":981,"y":54,"w":459,"h":780},"scrollHeight":804,"clientHeight":780,"overflowY":"hidden"},
 "wheel":{"before_sidebar_scrollTop":0,"after_5_ticks_scrollTop":500,"list_top_after":132,"sidebar_bottom":542}}
```

### L4 — Lists box visibility at 1024×768
- Phase: P3-lists · Env: E1 · Viewport: 1024×768 (iframe, see ENV-3)
- Steps: 1. As L3 at 1024x768.
- Expected: as L3
- Observed: Same defect with less room: the scrolling container is shorter than at 1440x900 and the list starts far below its bottom edge, so no list entry is visible on open. The "Upload Wordlist" button is visible.
- Evidence: evidence/L4.json
- Verdict: FAIL · Severity: S2 · Known: —

```json
{"case":"L4","method":"same-origin iframe sized 1024x768","viewport":[1024,768],
 "list":{"selector":".wordlist-list","rect":{"x":701,"y":632,"w":259,"h":1295},"scrollHeight":1295,"clientHeight":1295,"overflowY":"visible","visibleInViewport":false},
 "scroll_container":{"selector":".sidebar","rect":{"x":677,"y":170,"w":315,"h":244},"scrollHeight":1794,"clientHeight":244,"overflowY":"auto"},
 "panel":{"selector":".wordlist-panel","rect":{"x":645,"y":54,"w":379,"h":648},"scrollHeight":672,"clientHeight":648,"overflowY":"hidden"},"uploadBtnVisible":true}
```

### L5 — Upload F1 (plain, LF)
- Phase: P3-lists · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Reload, open Lists, click "Upload Wordlist". 2. Name `qa-f1`, choose F1-plain-lf.txt. 3. Click "Upload". 4. Read the network entry and `curl` the readback.
- Expected: "File Format: Plain text file with one word per line" (UI label in the upload form)
- Observed: POST /api/wordlists/import returns 201; the new list appears under the custom category with its three words, one per line, matching the file.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
GET /api/wordlists/custom/qa-f1 -> word_count=3 words=["APPLE", "BERRY", "CHERRY"]
POST /api/wordlists/import 201
```

### L6 — Upload F2 (APPLE;50 semicolon-scored)
- Phase: P3-lists · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Reload, open Lists, click "Upload Wordlist". 2. Name `qa-f2`, choose F2-scored-semicolon.txt. 3. Click "Upload". 4. Read the network entry and `curl` the readback.
- Expected: UNSPECIFIED (format behaviour is not documented; the form says one word per line)
- Observed: Accepted with 201, but each line is stored as one literal word including the `;50` suffix; the score is not parsed. The shipped scored list uses this very form, so a user uploading a list like it gets words that can never match a grid slot.
- Evidence: —
- Verdict: UNSPECIFIED · Severity: — · Known: I3

```
GET /api/wordlists/custom/qa-f2 -> word_count=3 words=["APPLE;50", "BERRY;40", "CHERRY;30"]
POST /api/wordlists/import 201
```

### L7 — Upload F3 (apple,50 comma-scored)
- Phase: P3-lists · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Reload, open Lists, click "Upload Wordlist". 2. Name `qa-f3`, choose F3-scored-comma.txt. 3. Click "Upload". 4. Read the network entry and `curl` the readback.
- Expected: UNSPECIFIED
- Observed: Accepted with 201; lowercase input is uppercased and the `,50` suffix is kept inside the word. The comma form is the one the CLI word-list loader (I4) splits but the web import does not.
- Evidence: —
- Verdict: UNSPECIFIED · Severity: — · Known: I3

```
GET /api/wordlists/custom/qa-f3 -> word_count=3 words=["APPLE,50", "BERRY,40", "CHERRY,30"]
POST /api/wordlists/import 201
```

### L8 — Upload F4 (.csv with header)
- Phase: P3-lists · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Reload, open Lists, click "Upload Wordlist". 2. Name `qa-f4`, choose F4-csv-header.csv. 3. Click "Upload". 4. Read the network entry and `curl` the readback.
- Expected: "Select File (.txt)" (UI label)
- Observed: The form refuses the file client-side: the red message "Please select a .txt file" appears, the Upload button stays disabled, and no request is sent to the server (a fetch wrapper recorded none; the network tool listed none).
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
UI message: Please select a .txt file
no POST /api/wordlists/import issued
```

### L9 — Upload F5 (CRLF)
- Phase: P3-lists · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Reload, open Lists, click "Upload Wordlist". 2. Name `qa-f5`, choose F5-crlf.txt. 3. Click "Upload". 4. Read the network entry and `curl` the readback.
- Expected: "File Format: Plain text file with one word per line" (UI label in the upload form)
- Observed: Accepted with 201; the three words are stored clean, with no carriage return left on any word.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
GET /api/wordlists/custom/qa-f5 -> word_count=3 words=["APPLE", "BERRY", "CHERRY"]
POST /api/wordlists/import 201
```

### L10 — Upload F6 (.dict)
- Phase: P3-lists · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Reload, open Lists, click "Upload Wordlist". 2. Name `qa-f6`, choose F6-dict.dict. 3. Click "Upload". 4. Read the network entry and `curl` the readback.
- Expected: "Select File (.txt)" (UI label)
- Observed: Refused client-side with "Please select a .txt file"; no request sent. Note the repository itself ships `.dict` lists, so the one dictionary format the project uses cannot be uploaded through the UI.
- Evidence: —
- Verdict: PASS · Severity: S4 · Known: —

```
UI message: Please select a .txt file
no POST /api/wordlists/import issued
```

### L11 — Upload F7 (non-ASCII)
- Phase: P3-lists · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Reload, open Lists, click "Upload Wordlist". 2. Name `qa-f7`, choose F7-nonascii.txt. 3. Click "Upload". 4. Read the network entry and `curl` the readback.
- Expected: UNSPECIFIED
- Observed: Accepted with 201; the accented words are stored with their accents (CAFÉ, NAÏVE, ÜBER). Whether a solver can ever place them is not stated anywhere in the README.
- Evidence: —
- Verdict: UNSPECIFIED · Severity: — · Known: —

```
GET /api/wordlists/custom/qa-f7 -> word_count=3 words=["CAF\u00c9", "NA\u00cfVE", "\u00dcBER"]
POST /api/wordlists/import 201
```

### L12 — Upload F8 (empty file)
- Phase: P3-lists · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Reload, open Lists, click "Upload Wordlist". 2. Name `qa-f8`, choose F8-empty.txt. 3. Click "Upload". 4. Read the network entry and `curl` the readback.
- Expected: "Bad request (validation error)" as the 400 response of POST /wordlists/import (docs/api/openapi.yaml:2218); the operation requires a `name` and takes `content`, "Newline-separated words" (docs/api/openapi.yaml:1312)
- Observed: The UI submits the empty file and the server answers 201, creating a list with zero words that then appears in the list. The API does the same for `"content": ""`; only a request with no `content` and no `url` gets 400. An empty upload is accepted silently instead of being rejected.
- Evidence: evidence/L12-L13-curl.log
- Verdict: FAIL · Severity: S3 · Known: —

```
--- F8 readback
{
  "metadata": {
    "category": "custom",
    "description": "Uploaded from F8-empty.txt",
    "key": "custom/qa-f8",
    "name": "Qa-F8",
    "source": "direct_import",
    "tags": [
      "custom",
      "uploaded"
    ],
    "word_count": 0
  },
  "words": []
}
POST /api/wordlists/import 201 (UI)
```

### L13 — Upload F9 (scored list, large)
- Phase: P3-lists · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Reload, open Lists, click "Upload Wordlist". 2. Name `qa-f9`, choose F9-large.txt. 3. Click "Upload". 4. Read the network entry and `curl` the readback.
- Expected: UNSPECIFIED
- Observed: Accepted with 201 within a few seconds and the list appears; every stored word still carries its `;score` suffix, so the upload of the project's own scored list yields a list of words that cannot match a slot. The list also renders in the browser without error.
- Evidence: evidence/L12-L13-curl.log
- Verdict: UNSPECIFIED · Severity: — · Known: I3

```
{"category": "custom", "description": "Uploaded from F9-large.txt", "key": "custom/qa-f9", "name": "Qa-F9", "source": "direct_import", "tags": ["custom", "uploaded"], "word_count": 453988}
['AAA;50', 'AAAADVISOR;11', 'AAAAH;7']
semicolon-bearing words: 453988 of 453988
POST /api/wordlists/import 201 (browser-measured upload to list shown: 2.8 s)
```

### L14 — Edit an uploaded list (add a word)
- Phase: P3-lists · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Open Lists, select the uploaded F1 list. 2. Click "Add Words", type DAMSON in the textarea, click "Add Words to List". 3. Read the network entries and `curl` the list.
- Expected: UI label "Add Words to List"; the added word is present on readback
- Observed: PUT returns 200, the detail card shows the new word, and the API readback and the on-disk file both contain it.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
PUT /api/wordlists/custom/qa-f1 200
GET /api/wordlists/custom/qa-f1 -> words=["APPLE", "BERRY", "CHERRY", "DAMSON"] word_count=4
```

### L15 — Delete the uploaded list
- Phase: P3-lists · Env: E1 · Viewport: 1800×1042
- Steps: 1. Stub the page's native confirm dialog to return true (test-harness only; the source is unchanged, and a native dialog would block the browser session). 2. Click "Delete" on the F1 list. 3. Check the list, the API and the disk.
- Expected: UI label "Delete"; the list is gone from GET /api/wordlists
- Observed: The confirm text read "Delete wordlist "custom/qa-f1"? This cannot be undone." DELETE returns 200; the list disappears from the panel, the list API, a direct GET (404), and the custom directory on disk. The un-stubbed confirm path was not exercised.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
DELETE /api/wordlists/custom/qa-f1 200
GET /api/wordlists/custom/qa-f1 -> 404
```

### L16 — Lists tool against the dev server on :3000
- Phase: P3-lists · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. Start `npm run dev` with Flask up. 2. Open `http://localhost:3000/` (README URL) and `http://127.0.0.1:3000/`. 3. Repeat L1 (names vs API), the L3 measurement, and the wheel test. 4. Stop the dev server.
- Expected: "Open http://localhost:3000" (README.md:54); the production-mode behaviour from L1-L3 ("whether the modes differ", spec §2.3)
- Observed: The README's localhost URL loads the app even though Vite reports it listens on 127.0.0.1. The list names match the API; the layout is the same as production mode: `.wordlist-list` starts below the bottom of its scrolling container and is invisible on open, and the wheel over the sidebar scrolls it into view. The modes do not differ.
- Evidence: evidence/SERVE-dev-L16.log
- Verdict: FAIL · Severity: S2 · Known: —

```json
{"viewport":[1800,986],"namesMatchApi":true,
 "list":{"selector":".wordlist-list","rect":{"x":1397,"y":632,"w":339,"h":2203},"overflowY":"visible"},
 "scroll_container":{"selector":".sidebar","rect":{"x":1373,"y":170,"w":395,"h":458},"scrollHeight":2702,"clientHeight":458,"overflowY":"auto"},
 "wheel":{"after_5_ticks_scrollTop":500,"list_top_after":132}}
```

### A1 — Import example_11x11 through the Import tool
- Phase: P3-autofill · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Import tool, "Choose JSON file", select the 11x11 example. 2. Read the preview. 3. Click "Import Grid".
- Expected: UI label "Import Grid"; "Select a .json file exported from this tool"
- Observed: The preview reads size 11x11 with a cell count and "Filled: 0"; after "Import Grid" the app switches to the Grid tool and shows an 11x11 grid with black squares (SVG with one group per cell).
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
preview: Size 11x11, Cells 121, Filled 0
svg cell groups: 121 ; black cells: 20 ; white cells: 101
```

### A2 — Autofill with panel defaults on the 11x11 grid
- Phase: P3-autofill · Env: E1 · Viewport: 1800×1042
- Steps: 1. Open Autofill; leave the defaults (Repair, 5 min, Min Score 50, Comprehensive Dictionary). 2. Click "Start Autofill". 3. Poll the SVG for empty white cells and the panel status for 3 minutes, then keep watching to the run's own end. 4. Click Cancel at the end.
- Expected: "fill grids using CSP with backtracking, beam search, or iterative repair" (README.md:35-36); autofill works = run ends within 3 minutes and every white cell holds a letter (plan Task 7 criteria)
- Observed: The run does not finish within 3 minutes and the grid is not filled: after the cap the grid still has empty white cells, the status reads "Filling" with a progress bar pinned at 90 from the first second, and the grid flickers between partial and cleared states. The server-side run ends at about its 5-minute timeout with conflicts left; the browser never notices: the panel keeps the running state and the Cancel button, with the last message "Repairing: 4 conflicts left", until the user clicks Cancel ("Cancelled by user"). The grid keeps a partial fill.
- Evidence: evidence/A2.log · evidence/SERVE-run.log
- Verdict: FAIL · Severity: S1 · Known: —

```
A2 timeline (fill id c65ddc8d-..., repair, timeout 300 s, min score 50, list Comprehensive Dictionary, grid example_11x11)
11:21:06 POST /api/fill/with-progress -> 202 ; GET /api/progress/<id> (SSE) opened
t+49s   cells: white=101 empty=64 black=20  progress "Filling ... slots", bar 90
t+63s   cells: white=101 empty=101  (grid cleared again; letters flash then clear)
t+100s  empty=64 ; t+130s empty=70
t+186s  empty=70 ; message "Filling: 3/44 slots (4500 steps)" ; bar 90   <- 3-minute cap reached, run still going
t+308s  empty=24 ; message "Repairing: 4 conflicts left" ; bar 90 ; CLI process (cli/crossword fill --timeout 300 --algorithm repair) already exited
11:26:18 GET /api/progress/<id> -> 404 ("Task not found")   (server-side task gone)
UI still shows running state + Cancel button; click Cancel -> "Cancelled by user / Reset"; grid keeps empty=24
```

### A-SBS — "Suggest Black Square" button in the Autofill panel
- Phase: P3-autofill · Env: E1 · Viewport: 1800×1042
- Steps: 1. Open Autofill. 2. Inspect the "Suggest Black Square" button.
- Expected: UI label "Suggest Black Square"
- Observed: The button is disabled with the tooltip "lands in Task 20": a visible control for a capability that is not wired up. The server has routes for suggesting and applying black squares (probed in P5).
- Evidence: —
- Verdict: NOT-IMPLEMENTED · Severity: S3 · Known: —

```
button: text="Suggest Black Square" title="lands in Task 20" disabled=true
```

### A3 — Cancel a run on the 15x15 grid
- Phase: P3-autofill · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Import the 15x15 example, open Autofill, start with the defaults. 2. Click Cancel 3 s later. 3. Check the panel, the network and the process list.
- Expected: UI label "Cancel"; the UI returns to idle and progress events stop (plan Task 7 criteria)
- Observed: The panel returns to idle ("Cancelled by user" with a Reset button) and the Autofill button is back; the cancel route returns 200 and the solver process is gone. The event stream is not shown closed by the browser tool; the server log shows no further progress requests. Separately, Cancel on an already-finished run (the one in A2) calls the same route and gets 404, yet the UI still announces "Cancelled by user".
- Evidence: evidence/A3.log
- Verdict: PASS · Severity: — · Known: —

```
A3 repair on example_15x15 (defaults), Cancel clicked 3 s after Start
status at 3 s: "Stripped 0 blocking words | 30%"
POST /api/fill/with-progress 202 -> POST /api/fill/cancel/<id> 200 -> UI "Cancelled by user / Reset"
server log: CLI process failed with return code -15 (SIGTERM from cancel); no cli/crossword process left afterwards
GET /api/progress/<id> is reported 503 by the browser tool but 200 in the server log (tool artefact for an event stream)
```

### A4 — Autofill, option "Repair (Recommended)"
- Phase: P3-autofill · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Import the 11x11 example, open Autofill. 2. Select the algorithm option and the panel's 2 min timeout (a panel option, chosen so the run ends on its own inside the cap; every other setting is the panel default). 3. Start and let the page sample the grid and status every 5 s.
- Expected: "fill grids using CSP with backtracking, beam search, or iterative repair" (README.md:35-36); autofill works = the run ends within 3 minutes and every white cell holds a letter (plan Task 7 criteria)
- Observed: The run ends on its own at its timeout with the terminal message "Partial: 20/44 slots (45%) - Lower minimum score (currently 50)" and the grid still has empty white cells. The UI reaches its idle state this time. The progress bar sits at 90 from about 20 s on while only the message changes.
- Evidence: evidence/A4.log
- Verdict: FAIL · Severity: S1 · Known: —

```
A4 repair, timeout 2 min (panel option), Comprehensive Dictionary, min score 50
s=5    empty=79  Filling: 3/44 slots (1500 steps) | 30%
s=20   empty=64  Filling: 4/44 slots (2500 steps) | 90%
s=65   empty=64  Filling: 4/44 slots (4000 steps) | 90%
s=110  empty=64  Filling: 4/44 slots (6000 steps) | 90%
s=120  empty=101 Repairing 5 invalid words | 90%
s=125  empty=24  Partial: 20/44 slots (45%) - Lower minimum score (currently 50) | Reset   (run ended, UI idle)
```

### A5 — Autofill, option "Hybrid (Beam + Repair)"
- Phase: P3-autofill · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Import the 11x11 example, open Autofill. 2. Select the algorithm option and the panel's 2 min timeout (a panel option, chosen so the run ends on its own inside the cap; every other setting is the panel default). 3. Start and let the page sample the grid and status every 5 s.
- Expected: "fill grids using CSP with backtracking, beam search, or iterative repair" (README.md:35-36); autofill works = the run ends within 3 minutes and every white cell holds a letter (plan Task 7 criteria)
- Observed: Same outcome as Repair: it ends at its timeout with "Partial: 20/44 slots (45%)" and 24 white cells left empty. The two algorithms land on the identical partial result.
- Evidence: evidence/A5.log
- Verdict: FAIL · Severity: S1 · Known: —

```
A5 hybrid, timeout 2 min
s=5    empty=101 Beam search: slot 1/44 | 30%
s=25   empty=68  Stripped 7 blocking words | 70%
s=45   empty=64  Filling: 4/44 slots (5500 steps) | 90%
s=85   empty=58  Filling: 5/44 slots (15500 steps) | 90%
s=120  empty=24  Partial: 20/44 slots (45%) - Lower minimum score (currently 50) | Reset
```

### A6 — Autofill, option "Beam Search"
- Phase: P3-autofill · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Import the 11x11 example, open Autofill. 2. Select the algorithm option and the panel's 2 min timeout (a panel option, chosen so the run ends on its own inside the cap; every other setting is the panel default). 3. Start and let the page sample the grid and status every 5 s.
- Expected: "fill grids using CSP with backtracking, beam search, or iterative repair" (README.md:35-36); autofill works = the run ends within 3 minutes and every white cell holds a letter (plan Task 7 criteria)
- Observed: Fills every white cell in well under the cap and ends with "Filled 44/44 slots - 5 entries may be invalid (use Verify Words to check)". The README criterion holds; the status itself warns that some placed words are not valid list words.
- Evidence: evidence/A6.log
- Verdict: PASS · Severity: S3 · Known: —

```
A6 beam, timeout 2 min
s=5    empty=101 Beam search: slot 1/44 | 30%
s=25   empty=56  Beam search: slot 18/44 | 46%
s=30   empty=4   Beam search: slot 40/44 | 91%
s=35   empty=0   Filled 44/44 slots - 5 entries may be invalid (use Verify Words to check) | Reset
```

### A7 — Autofill, option "Classic CSP"
- Phase: P3-autofill · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Import the 11x11 example, open Autofill. 2. Select the algorithm option and the panel's 2 min timeout (a panel option, chosen so the run ends on its own inside the cap; every other setting is the panel default). 3. Start and let the page sample the grid and status every 5 s.
- Expected: "fill grids using CSP with backtracking, beam search, or iterative repair" (README.md:35-36); autofill works = the run ends within 3 minutes and every white cell holds a letter (plan Task 7 criteria)
- Observed: Gives up almost immediately with "Partial: 0/44 slots (0%) - Lower minimum score (currently 50)": the first poll, within about 5 s, already shows the finished state with an untouched grid.
- Evidence: evidence/A7.log
- Verdict: FAIL · Severity: S1 · Known: —

```
A7 trie (label "Classic CSP"), timeout 2 min
s=5    empty=101 Partial: 0/44 slots (0%) - Lower minimum score (currently 50) | Reset   (run already ended)
```

### A8 — Theme-locked autofill
- Phase: P3-autofill · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Import the 11x11 example. 2. Theme tool: upload a three-word file (all 11 letters). 3. Apply one suggested placement. 4. Autofill with Beam Search (the option that completes in A6), 2 min timeout. 5. Compare the themed column before and after.
- Expected: "supports theme word locking" (README.md:36)
- Observed: The applied theme word is untouched after the run and the slot count drops by one (the themed slot is excluded); every white cell is filled. The Beam Search status again warns that some entries may be invalid. Side observation for TH2: two of the three uploaded words get "No valid placements found" although the grid has other open full-width rows.
- Evidence: evidence/A8.log
- Verdict: PASS · Severity: — · Known: —

```
A8 theme-locked autofill, 11x11, beam, timeout 2 min
Theme tool: upload T1-theme.txt (OBSERVATION, MIRRORIMAGE, PERFORMANCE) -> POST /api/theme/upload 200, POST /api/theme/suggest-placements 200
Apply first OBSERVATION suggestion (Row 0, Col 5, down) -> POST /api/theme/apply-placement 200
col 5 before apply: "..........."   after apply: "OBSERVATION"   empty white cells after apply: 90
s=5   empty=58  col5=OBSERVATION  Beam search: slot 17/43 | 45%
s=15  empty=20  col5=OBSERVATION  Beam search: slot 33/43 | 79%
s=20  empty=0   col5=OBSERVATION  Filled 43/43 slots - 6 entries may be invalid (use Verify Words to check) | Reset
```

### A9 — Autofill with the shipped .pkl caches removed
- Phase: P3-autofill · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Delete the .pkl files of the shipped lists in the sandbox clone, restart the server. 2. Run Beam and Repair on the 11x11 grid, 2 min timeout.
- Expected: as A4/A6 (README.md:35-36)
- Observed: Repair ends with the same "Partial: 20/44" as with the caches present (A4). Beam still fills the grid but takes noticeably longer than in A6 and stalls at one slot for tens of seconds first; the count of flagged entries differs from A6. The cache is not what makes Repair fail.
- Evidence: evidence/A9.log
- Verdict: FAIL · Severity: S1 · Known: I7

```
A9 .pkl files removed (comprehensive.pkl, top_100k.pkl), server restarted, 11x11, timeout 2 min
beam   : s=65  empty=0   Filled 44/44 slots - 8 entries may be invalid | Reset   (stalled at "slot 17/44 | 44%" from s=20 to s=50)
repair : s=125 empty=24  Partial: 20/44 slots (45%) - Lower minimum score (currently 50) | Reset
```

### A10 — Autofill with the cache regenerated by build-cache
- Phase: P3-autofill · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Run the CLI build-cache command on the comprehensive list (rc and size recorded). 2. Restart the server. 3. Run Beam on the 11x11 grid, 2 min timeout. (Repair was not repeated for A10; A9 already showed Repair independent of the cache.)
- Expected: as A6 (README.md:35-36)
- Observed: Beam fills the grid in about the same time as A6 with a different count of flagged entries; no cache warning or traceback appears in the server log. Whether the fill reads the cache at all is checked in the CLI cache variants (P4); see CACHE-1 for what the two cache files contain.
- Evidence: evidence/A10.log
- Verdict: PASS · Severity: — · Known: I7

```
A10 cache regenerated with build-cache (rc=0), server restarted, 11x11, timeout 2 min
beam   : s=30  empty=0   Filled 44/44 slots - 7 entries may be invalid | Reset
repair : not run for A10
server log: no cache warning, no traceback
```

### CACHE-1 — Shipped and regenerated .pkl differ from the .txt they sit beside
- Phase: P3-autofill · Env: E1 · Viewport: —
- Steps: 1. Copy the tracked comprehensive cache out of the main checkout with `git show` (read-only). 2. Load it, and the cache rebuilt in A10, with the loader's own class through the runtime import path (the wrapper script imports `src...` with `cli/` on the path). 3. Count lines of the text list.
- Expected: "ships with 44k curated words" (README.md:37-38)
- Observed: The shipped cache holds the large scored list, a list far larger than the text list it sits beside (line counts in the fence), and in a fresh clone its mtime ties the text list's, so the loader's rule "use the cache when its mtime is not older" selects it. The cache rebuilt by the CLI's own build-cache command cannot be loaded back through the runtime import path (module `cli.src` not found) and the loader's fallback only catches ValueError/FileNotFoundError, so that error is not turned into a text-list reload at that call.
- Evidence: evidence/CACHE-1.log
- Verdict: FAIL · Severity: S2 · Known: I7

```
shipped comprehensive.pkl (copy of the tracked file) loaded through the runtime import path (sys.path has cli/ so the module is "src.fill.word_list"):
orig-comprehensive.pkl LOADED 453992
comprehensive.txt line count (wc -l): 44024
pkl rebuilt by "python -m cli.src.cli build-cache data/wordlists/comprehensive.txt" (rc=0), same runtime import path:
comprehensive.pkl FAILED ModuleNotFoundError No module named 'cli.src'
sizes: shipped 19822703 bytes ; rebuilt 1780138 bytes
build-cache output tail: cache written, size reported as 1.7 MB
```

### G1 — Create a new 15×15 grid from the Grid tool
- Phase: P3-grid · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Open the app and the Grid tool; look for a control that creates a new grid or sets its size.
- Expected: UI (no label found)
- Observed: The app opens on a blank 15x15 grid, and the Grid panel offers only "Select a cell to search, or pick a tool from the rail." There is no control to create a new grid or choose another size; other sizes arrive only through the Import tool.
- Evidence: —
- Verdict: NOT-IMPLEMENTED · Severity: S3 · Known: —

### G2 — Type letters, move with arrows, clear with Backspace
- Phase: P3-grid · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Click a cell. 2. Type CAT. 3. Press ArrowLeft twice, then Backspace. 4. Type A. Read the row from the SVG after each step.
- Expected: "interactive editing with keyboard shortcuts" (README.md:31-32)
- Observed: Typing fills three consecutive cells and the cursor advances; after two ArrowLefts and Backspace only the middle letter is cleared; typing A restores it.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
row after typing CAT, arrows, Backspace: ....C.T........
row after typing A:                       ....CAT........
```

### G3 — Place a black square
- Phase: P3-grid · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Look for a control, tooltip, hint or help text for black squares. 2. Try the period key, the hash key, right-click and double-click on a selected cell.
- Expected: UI (a placement method discoverable from the page)
- Observed: The period key places a black square. Nothing in the page names it: no button, tooltip, help panel or shortcut list (the only mention is the violations text "Try adding black squares"). The hash key, right-click and double-click do nothing. The key was found by trying keys, so there is no discoverable way for a user.
- Evidence: —
- Verdict: FAIL · Severity: S2 · Known: —

```
black squares after "." on (2,2): row 2 col 2, and mirror row 12 col 12
```

### G4 — Symmetry toggle ON vs OFF
- Phase: P3-grid · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. With Symmetry on, place a black square at (2,2). 2. Switch Symmetry off, place one at (4,10).
- Expected: "symmetry enforcement" (README.md:31-32)
- Observed: ON: the black square at (2,2) also appears at (12,12), the 180-degree mirror. OFF: only (4,10) is added. The toggle button carries its on-state class accordingly.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
symmetry ON : (2,2) -> also (12,12)
symmetry OFF: (4,10) only
black cells after both: 3
```

### G5 — Numbering updates after black squares
- Phase: P3-grid · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Collect the clue-number labels from the SVG before and after the (4,10) black square. 2. Check the numbering request.
- Expected: "auto-numbering" (README.md:31-32)
- Observed: The label sequence grows when a black square is added, and the numbering route is called after each edit (server log shows the POSTs return 200).
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
labels before: 1..33   labels after: 1..35
```

### G6 — Top-bar Verify
- Phase: P3-grid · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Click "Verify words" with one filled word (CAT) on the grid.
- Expected: UI label "Verify words"
- Observed: POST /api/grid/verify-words returns 200 and a toast reads "All 4 words valid!". The grid holds one filled word, so the count in the message does not match what is on the grid (not specified anywhere).
- Evidence: —
- Verdict: PASS · Severity: S4 · Known: —

```
toast: All 4 words valid!
```

### G7 — Top-bar Clean
- Phase: P3-grid · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Click "Clean grid".
- Expected: UI label "Clean grid"
- Observed: POST /api/grid/clean returns 200, the toast says "Grid is clean — all words are valid!", and the grid is unchanged.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
toast: Grid is clean — all words are valid!
```

### G8 — Heatmap toggle changes cell rendering
- Phase: P3-grid · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Compute the fill of every cell, toggle Heatmap on, wait, compare. 2. Check the server log for a constraints request. 3. Toggle off and compare again.
- Expected: UI label "Heatmap"
- Observed: The button switches to its on state, but no cell fill changes, the SVG gains no overlay, and the server never receives a constraints request during the session. The toggle has no visible effect.
- Evidence: —
- Verdict: FAIL · Severity: S3 · Known: I8

```
cells whose fill changed with heatmap on: 0
requests to /api/constraints in the server log: 0
```

### G9 — Save, reload, grid persists
- Phase: P3-grid · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Click "Save grid" (label then reads "saved locally"). 2. Reload the page. 3. Read the grid and local storage.
- Expected: UI label "Save grid"; the page itself says "saved locally"
- Observed: The save is written (a stored grid record exists and holds the typed letters), but after a reload the editor shows a blank grid; there is no restore or load control, and the "saved" label is gone. Saved work is not reachable from the UI after a reload.
- Evidence: —
- Verdict: FAIL · Severity: S2 · Known: —

```
saved record keys: id, size, grid, numbering, symmetryEnabled, savedAt
saved row 6: ....CAT........
rows with letters or black squares after reload: none
```

### G10 — Health indicator and theme toggle
- Phase: P3-grid · Env: E1 · Viewport: 1800×1042 (see ENV-3)
- Steps: 1. Read the status text. 2. Click the theme toggle, then reload.
- Expected: UI (status "online"; theme toggle)
- Observed: The indicator reads "online" while Flask is up. The toggle flips the theme attribute light to dark and the choice survives a reload.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
data-theme: light -> dark ; after reload: dark ; stored value follows
```

### SR1 — Pattern search C?T in Comprehensive Dictionary
- Phase: P3-search · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. Open Search with its default list. 2. Enter C?T. 3. Click Search. (State of the clone: shipped caches restored, see CACHE-2.)
- Expected: "find words matching a pattern like C?T (gives CAT, COT, CUT, etc.)" (README.md:33-34)
- Observed: The results include CAT, COT and CUT, together with other three-letter strings (abbreviations such as CIT, CRT, CST) because the list behind it is large. The README claim holds.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
request: {"pattern":"C?T","wordlists":["comprehensive"],"max_results":50,"algorithm":"regex"}
results heading: Results (11)
first rows: CAT 31 · CIT 31 · COT 31 · CRT 31 · CST 31 · CET 31 · CDT 26 · CUT 26 · CWT 26 · CMT
```

### SR2 — Results list is reachable by scrolling
- Phase: P3-search · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. After SR1, measure the results container and its scrolling ancestor. 2. Wheel-scroll 10 ticks over the panel.
- Expected: §2.4 of the spec (box visible and scrollable)
- Observed: After a search the results sit far below the long wordlist checklist and outside the viewport; nothing scrolls them into view. The wheel over the panel scrolls it and the results come into view, and the results list has a scrollbar of its own. So the list scrolls, but a user sees no results until they scroll down.
- Evidence: evidence/SR2.json
- Verdict: PASS · Severity: S3 · Known: —

```
viewport [1800,986]
results container ".results-section": rect [1373,1190,387,439] visibleInViewport=false (after a search)
scroll container ".xw-inspector": overflowY=auto scrollHeight=1607 clientHeight=932
wheel 10 ticks over the panel -> scrollTop 674.5 ; results top 515, bottom 954 (inside viewport)
```

### SR3 — No-match pattern
- Phase: P3-search · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. Enter ZZQ?X, Search.
- Expected: UI (an empty-result state, no error)
- Observed: The panel shows "No matching words found"; no error toast and no uncaught error in the page.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
pattern ZZQ?X -> "No matching words found"
```

### SR4 — Search with no wordlist selected
- Phase: P3-search · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. Untick every list. 2. Enter C?T, Search.
- Expected: UNSPECIFIED
- Observed: The search still runs and returns a single result, CAT, tagged with a source called "builtin". No documentation or label explains a built-in source, and the button is not disabled with nothing selected.
- Evidence: —
- Verdict: UNSPECIFIED · Severity: — · Known: —

```
lists ticked: none
result: Results (1) | CAT | 31 | builtin | 3 letters
```

### CACHE-2 — A cache rebuilt by build-cache makes Pattern search on that list return nothing
- Phase: P3-search · Env: E1 · Viewport: —
- Steps: 1. After A10 (cache rebuilt with the CLI), run Pattern search C?T on Comprehensive Dictionary in the UI; read the final event of the progress stream. 2. Repeat the request through the API for that list and for a list with no rebuilt cache. 3. Restore the shipped caches and repeat.
- Expected: "find words matching a pattern like C?T (gives CAT, COT, CUT, etc.)" (README.md:33-34)
- Observed: With the rebuilt cache in place the UI shows "No matching words found" and the final event reports zero sources searched; the API gives the same for that list while other lists answer normally. There is no error message anywhere: the list silently drops out. With the shipped caches restored the same search returns results (SR1). The cache that the project's own build-cache command writes is the one that cannot be loaded back (see CACHE-1), and the backend does not report it.
- Evidence: evidence/CACHE-2.log
- Verdict: FAIL · Severity: S2 · Known: I7

```
with the cache rebuilt by build-cache in place:
  comprehensive: sources_searched [] total_found 0
  top_100k: sources_searched ['top_100k'] total_found 5
UI request body: {"pattern":"C?T","wordlists":["comprehensive"],"max_results":50,"algorithm":"regex"}
UI final event: Search complete: 0 results returned ; UI text: No matching words found
```

### SETUP-3 — setup leaves tracked files modified in a fresh clone
- Phase: P1-setup · Env: E1 · Viewport: —
- Steps: 1. After setup and the walkthrough so far, run `git diff --stat` in the E1 clone. (Cases run in the clone since; the lock-file change comes from setup itself.)
- Expected: UNSPECIFIED
- Observed: The lock file the repository tracks is rewritten by the install step (platform-specific fields dropped), so a clone that was clean is dirty right after the README's setup command. The word-list metadata file is also rewritten by uploads through the UI. A later `git pull` or checkout can collide with either.
- Evidence: evidence/SETUP-3.log
- Verdict: UNSPECIFIED · Severity: S4 · Known: —

```
git -C clone diff --stat after setup.sh and the walkthrough uploads (tracked files modified; the clone was clean before setup):
 data/wordlists/metadata.json | (changed by the UI list uploads)
 package-lock.json            | 51 lines removed ("libc" fields dropped by npm install)
 data/wordlists/top_100k.pkl  | (deleted for A9 and restored afterwards; not product behaviour)
```

### TH1 — Theme tool: upload a word file
- Phase: P3-theme · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. Import the 15x15 example. 2. Theme tool, choose a file containing APPLE, BERRY, CHERRY.
- Expected: UI label "Upload Theme Words" ("Upload a .txt file with one word per line")
- Observed: The three words are listed as chips with their lengths under "Loaded Words".
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
POST /api/theme/upload 200
```

### TH2 — Suggest placements on the 15x15 grid
- Phase: P3-theme · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. After TH1, read the suggestions. 2. Check every suggestion against the example grid with the API.
- Expected: UI label "Placement Suggestions"
- Observed: POST /api/theme/suggest-placements returns 200 with a non-empty list per word (CHERRY, APPLE, BERRY). Checked against the real grid, none of the returned placements crosses a black square or the border.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
POST /api/theme/suggest-placements 200
request: {"theme_words":["APPLE","BERRY","CHERRY"],"grid_size":15,"existing_grid":[... 15 rows ...]}
suggestions checked against grid blacks: 9 ; crossing a black or out of bounds: 0
```

### TH2b — Suggestions after the grid changes
- Phase: P3-theme · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. With suggestions showing, place a black square (period key) at row 5, col 10 on the grid. 2. Re-read the list. 3. Click "Apply This Placement" on the APPLE placement at row 3, col 10 (down), which passes through that cell.
- Expected: UI text "Hover over suggestions to preview on grid. Click "Apply" to lock the word."
- Observed: The suggestion list does not change after the grid edit; the placement that now runs through a black square is still offered. Applying it is refused by the server with the toast "Cannot place 'P' at (5, 10): cell is black" and the grid stays unchanged.
- Evidence: —
- Verdict: FAIL · Severity: S3 · Known: #19

```
toast: Cannot place 'P' at (5, 10): cell is black
column 10 before and after: ###..#..#......
```

### TH3 — Apply one placement, then Apply All Best Placements
- Phase: P3-theme · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. Apply the CHERRY placement at row 7, col 8 (across). 2. Click "Apply All Best Placements". 3. Read the toasts, the three apply-placement responses, and the console.
- Expected: UI label "Apply All Best Placements" ("Automatically place all theme words with their best non-conflicting positions")
- Observed: Single apply works: CHERRY appears in the row and a success toast shows. Apply All sends one request per word; the second returns 400 with the precise reason ("Cannot place 'P' at (5, 10): cell is black"), but the user sees only "Applied 2 theme words successfully! (1 skipped due to conflicts)". The reason appears only in the browser console ("Error applying placement: ApiError: Placement conflicts detected"). The message also counts the word applied a moment earlier.
- Evidence: —
- Verdict: FAIL · Severity: S3 · Known: #20

```
toasts: Applied 2 theme words successfully! (1 skipped due to conflicts)
POST /api/theme/apply-placement -> 200, 400, 200
400 body: {"applied":false,"conflicts":["Cannot place 'P' at (5, 10): cell is black"],"error":"Placement conflicts detected"}
console: Error applying placement: ApiError: Placement conflicts detected
```

### TH4 — Theme words with no suggestion on the 11x11 grid
- Phase: P3-theme · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. On the 11x11 example, upload OBSERVATION, MIRRORIMAGE, PERFORMANCE (all 11 letters). 2. Read the suggestions.
- Expected: UNSPECIFIED
- Observed: OBSERVATION gets three placements, while the other two report "No valid placements found for this word" although the grid has other open full-width rows (OBSERVATION is offered one of them). Not specified anywhere which is right.
- Evidence: evidence/A8.log
- Verdict: UNSPECIFIED · Severity: — · Known: —

### TH5 — Theme panel covers the top bar
- Phase: P3-theme · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. Open the Theme tool at this viewport. 2. Look at the top bar.
- Expected: UI (top bar controls reachable)
- Observed: The Theme panel is drawn over the right end of the top bar: the theme toggle and parts of the Verify/Clean/Save controls are hidden while the panel is open, so the theme could not be toggled until the panel was closed.
- Evidence: —
- Verdict: FAIL · Severity: S3 · Known: —

### IM1 — Import example_15x15
- Phase: P3-import · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. Import tool, choose the 15x15 example, "Import Grid".
- Expected: UI label "Import Grid"
- Observed: The 15x15 grid renders with its black squares (done repeatedly as the setup for other cases).
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

### IM2 — Import a non-JSON file
- Phase: P3-import · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. Import tool, choose the plain text fixture. 2. Read the message and the console.
- Expected: UI text "Select a .json file exported from this tool"
- Observed: A red panel reads "Error: Invalid file type. Please select a .json file."; the grid and app are unaffected and the console shows no uncaught error.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
Error: Invalid file type. Please select a .json file.
```

### IM3 — Import the NYT template
- Phase: P3-import · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. Import tool, choose the NYT template, preview, "Import Grid".
- Expected: UI label "Import Grid"
- Observed: The preview reads 15x15 with 225 cells; after import the grid renders with its black squares.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
preview: Size 15x15 | Cells 225 | Filled 0
black cells after import: 30
```

### EX1 — Export to HTML
- Phase: P3-export · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. Import the NYT template. 2. Export tool, format "HTML (printable)", Export. The download hook was intercepted so no file was saved; the generated blob was read in the page and rendered in a sandboxed frame.
- Expected: "Export -- HTML format" (README.md:39)
- Observed: The app generates a text/html document named crossword.html; its table has the same cell and black-cell counts as the grid, and rendered in a frame it shows a numbered 15x15 grid under a "Crossword Puzzle" heading. PDF and .puz are listed as "coming soon", which the README does not promise.
- Evidence: —
- Verdict: PASS · Severity: — · Known: —

```
blob type text/html ; table cells 225 ; black cells 30 ; rendered table 15 rows x 15 columns
```

### CL1 — Clues tool
- Phase: P3-clues · Env: E1 · Viewport: 1800×986 (see ENV-3)
- Steps: 1. Open the Clues tool.
- Expected: UI
- Observed: The panel shows a "Clue list" heading and the text "Arrives in a later task."
- Evidence: —
- Verdict: NOT-IMPLEMENTED · Severity: S3 · Known: I2

### CLI-help — Top-level and per-command help
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. Run the top-level help, then help for each listed command, under the E1 wrapper from the clone root.
- Expected: README.md:58 ("The CLI is the source of truth ... Activate the venv first.")
- Observed: The top-level help lists every command and each per-command help exits 0 with usage text. The command set equals the plan's list; there is no extra command.
- Evidence: evidence/CLI-help-top.log · evidence/CLI-help-all.log
- Verdict: PASS · Severity: — · Known: —

```
Usage: python -m cli.src.cli [OPTIONS] COMMAND [ARGS]...

  Crossword Builder CLI — create, fill, validate, and export crossword
  puzzles.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  analyze      Analyze grid constraints and placement impact.
  build-cache  Build binary cache file for fast wordlist loading.
  export       Export a crossword grid to various formats.
  fill         Fill a crossword grid using CSP autofill.
  import-nyt   Import an NYT crossword JSON file (doshea/nyt_crosswords...
  list-states  List all saved autofill states.
  new          Create a new empty crossword grid.
  normalize    Normalize crossword entry according to conventions.
  number       Auto-number a crossword grid.
  pattern      Find words matching a pattern.
  pause        Pause a running autofill task.
  resume       Resume autofill from a saved state file or task id.
  show         Display a crossword grid.
  validate     Validate a crossword grid against NYT standards.
--- per-command help exit codes ---
new rc=0 lines=       8
validate rc=0 lines=       7
fill rc=0 lines=      47
show rc=0 lines=       8
export rc=0 lines=      10
pattern rc=0 lines=      17
normalize rc=0 lines=      10
number rc=0 lines=      12
analyze rc=0 lines=      20
build-cache rc=0 lines=      15
pause rc=0 lines=      19
resume rc=0 lines=      41
list-states rc=0 lines=      23
import-nyt rc=0 lines=      19
```

### R5 — README pattern command, verbatim
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. From the clone root, venv active: the README's pattern command with `--json-output`. 2. Control: the same command with the sibling .pkl moved aside (restored afterwards, mtime tie re-created).
- Expected: "python -m cli.src.cli pattern \"C?T\" -w data/wordlists/comprehensive.txt --json-output" (README.md:62)
- Observed: The command exits 0 but prints "Warning: Could not load data/wordlists/comprehensive.txt: No module named 'src.fill'", loads zero words and returns zero matches, with `sources_searched` empty. A user sees a clean exit and an empty result. The shipped cache is what is unloadable under this invocation (it was written under a different module path, see CACHE-1); with the cache moved aside the same command loads the full text list and returns matches.
- Evidence: evidence/R5.log · evidence/R5-nocache.log
- Verdict: FAIL · Severity: S1 · Known: I7

```
{"type": "progress", "progress": 0, "message": "Searching for pattern \"C?T\"", "status": "running"}
{"type": "progress", "progress": 0, "message": "Loading wordlist 1/1: comprehensive.txt", "status": "running"}
Warning: Could not load data/wordlists/comprehensive.txt: No module named 'src.fill'
...
    "total_found": 0,
    "results_returned": 0,
    "sources_searched": []
  }
}
  0.05s user 0.01s system 92% cpu 0.064 total
--- control: cache moved aside ---
{"type": "progress", "progress": 30, "message": "Loaded 44024 words from 1 wordlist(s)", "status": "running"}
      "word": "CAT",
      "word": "CIT",
      "word": "COT",
      "word": "CRT",
      "word": "CST",
      "word": "CDT",
      "word": "CUT",
```

### R9 — README new command, verbatim
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. `new --size 15 -o puzzle.json`.
- Expected: "python -m cli.src.cli new --size 15 -o puzzle.json" (README.md:73)
- Observed: Exit 0; a 15x15 grid file is created.
- Evidence: evidence/R9.log
- Verdict: PASS · Severity: — · Known: —

```
✓ Created 15×15 grid: puzzle.json
  Size: 15×15
  Black squares: 0
  Ready to fill!
  0.04s user 0.01s system 93% cpu 0.059 total
```

### R8 — README validate command, verbatim (run after R9)
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. `validate puzzle.json` on the file created by R9. The README lists validate before new; run in the order that gives the file an origin.
- Expected: "python -m cli.src.cli validate puzzle.json" (README.md:70)
- Observed: Exit 0 and a validation report: valid, symmetric, connected, meets the standards.
- Evidence: evidence/R8.log
- Verdict: PASS · Severity: — · Known: —

```
============================================================
Grid Validation Report
============================================================

File: puzzle.json
Size: 15×15
Black squares: 0 (0.0%)
White squares: 225
Word count: 30 (15 across, 15 down)

Symmetric: ✓ Yes
Connected: ✓ Yes

============================================================
✓ VALID - Grid meets all standards!
✓ Meets NYT standards
```

### R7 — README fill command, verbatim (its own -t 180)
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. The README's fill command on the 15x15 example with the comprehensive list, `-t 180 --min-score 30 -o filled.json`.
- Expected: "fill data/grids/example_15x15.json -w data/wordlists/comprehensive.txt -t 180 --min-score 30 -o filled.json" (README.md:65-67)
- Observed: Exit 0; the CLI loads the full text list (the fill path reads the text file, so the cache problem of R5 does not apply), fills every slot in a few seconds, and writes filled.json.
- Evidence: evidence/R7.log
- Verdict: PASS · Severity: — · Known: —

```
Loading grid from data/grids/example_15x15.json...
Loading word lists...
  • data/wordlists/comprehensive.txt
  Loaded 44024 words
  Algorithm: repair (iterative repair)

Filling 78 empty slots...
Timeout: 180s, Min score: 30

Progress

============================================================
Autofill Results
============================================================

✓ SUCCESS - Grid filled completely!

Slots filled: 78/78
Time elapsed: 5.42s
Iterations: 9,781

============================================================
```

### R10 — README export command, verbatim
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. `export filled.json --format html -o puzzle.html`.
- Expected: "export filled.json --format html -o puzzle.html" (README.md:76)
- Observed: Exit 0; puzzle.html is written with a grid of cells (letters and black cells) and clue numbers.
- Evidence: evidence/R10.log
- Verdict: PASS · Severity: — · Known: —

```
✓ Exported to HTML: puzzle.html
$SB/e1.sh   0.05s user 0.01s system 94% cpu 0.064 total
cells in output: class="cell" 189 ; class="cell black" 36 ; class="cell-number" 73
```

### CLI-show — show a filled grid
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. `show filled.json`.
- Expected: UNSPECIFIED
- Observed: Exit 0; prints the numbered grid with letters and black cells.
- Evidence: evidence/CLI-show.log
- Verdict: PASS · Severity: — · Known: —

```
15×15 Crossword Grid
===============================
 1  2  3  4  5 ##  6  7  8  9 ## 10 11 12 13
14  A  N  E  Y ## 15  N  E  L ## 16  H  A  T
17  N  A  I  R ## 18  E  N  E ## 19  O  H  R
## ## ## 20  I 21  E  B  O  A 22 ## 23  A  E
```

### CLI-normalize — normalize "Hello, World!"
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. `normalize "Hello, World!" --json-output`.
- Expected: UNSPECIFIED (README silent; help text: "Normalize crossword entry according to conventions.")
- Observed: Exit 0 and JSON. The default rule is "remove spaces, uppercase", so the comma and the exclamation mark are kept (HELLO,WORLD!), although the result is meant as a crossword entry.
- Evidence: evidence/CLI-normalize.log
- Verdict: UNSPECIFIED · Severity: — · Known: —

```
{
  "original": "Hello, World!",
  "normalized": "HELLO,WORLD!",
  "rule": {
    "type": "default",
    "description": "Default: remove spaces, uppercase",
    "explanation": "No specific pattern matched - applying default normalization",
    "examples": [],
```

### CLI-number — number a grid
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. `number data/grids/example_15x15.json --json-output`.
- Expected: UNSPECIFIED
- Observed: Exit 0 and a JSON numbering map keyed by "(row,col)".
- Evidence: evidence/CLI-number.log
- Verdict: PASS · Severity: — · Known: —

```
{
  "numbering": {
    "(0,0)": 1,
    "(0,1)": 2,
    "(0,2)": 3,
    "(0,3)": 4,
```

### CLI-analyze — analyze a partial grid with the comprehensive list
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. `analyze data/grids/example_15x15_partial_mid.json -w data/wordlists/comprehensive.txt`.
- Expected: UNSPECIFIED (help: "Analyze grid constraints and placement impact.")
- Observed: Exit 1: the same unloadable-cache warning as R5, then "Error: no words loaded from wordlists". The command cannot be used with the shipped list in a fresh clone.
- Evidence: evidence/CLI-analyze.log
- Verdict: FAIL · Severity: S2 · Known: I7

```
Warning: Could not load data/wordlists/comprehensive.txt: No module named 'src.fill'
Error: no words loaded from wordlists
```

### CLI-build-cache — build-cache for another list
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. `build-cache data/wordlists/top_50k.txt -o <sandbox path>`.
- Expected: "Build binary cache file for fast wordlist loading." (help text)
- Observed: Exit 0; the cache file is written and the command verifies it. (The same command run on the comprehensive list is the one whose output cannot be loaded back, CACHE-1.)
- Evidence: evidence/CLI-build-cache.log
- Verdict: PASS · Severity: — · Known: —

```
Building cache for: top_50k.txt
Output: /private/tmp/crossword-fresh/top_50k.pkl

Loading wordlist...
✓ Loaded 50000 words in 0.10s
Writing cache file...
✓ Cache written in 0.02s
Verifying cache...
```

### CLI-pause-1 — pause on a task that already finished
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. Run the plan's pinned fill (15x15, comprehensive, -t 120, task id qa1, state and flag dirs in the sandbox). 2. Run `pause qa1` after 10 s.
- Expected: plan Task 10 (pause after 10 s)
- Observed: The plan's parameters finish the fill in about five seconds, before the planned pause, so a pause could not be exercised as pinned. `pause` on the finished task exits 1 with a clear message ("not running"); no state file was saved; list-states reports none.
- Evidence: evidence/CLI-fill-qa1.log · evidence/CLI-pause-finished.log
- Verdict: PASS · Severity: — · Known: —

```
✗ Task 'qa1' is not running (start a fill with --task-id qa1 first)
============================================================
Saved Autofill States (0 total)
============================================================

No saved states found.
============================================================
```

### CLI-pause-2 — pause, list-states, resume on a longer-running fill
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. Same flags on the 21x21 example (task id qa2). 2. `pause qa2` after about 12 s. 3. `list-states`. 4. `resume qa2 -t 60`. (Deviation from the pinned 15x15 input, which is too fast to pause.)
- Expected: help text for pause, list-states, resume
- Observed: Pause: the fill prints "Paused - solver state saved" and exits within a second, and a gzip state file appears. list-states shows the task with its progress. Resume loads the state and ends with a partial grid at its cap. The resumed run's own report states a much shorter elapsed time than the wall time of the run (see the timing fence).
- Evidence: evidence/CLI-pause-qa2.log · evidence/CLI-list-states-2.log · evidence/CLI-resume-qa2.log
- Verdict: PASS · Severity: S4 · Known: —

```
✓ Pause requested for task: qa2
The task will save its state and exit at the next checkpoint.
============================================================
Saved Autofill States (1 total)
============================================================

Task ID: qa2
  Timestamp: 2026-10-22T12:31:42.299940
  Grid size: 21×21
  Progress: 137/140 slots (97.9%)

--- resume ---
Loaded csp state for task 'qa2'
  Saved: 137/140 slots filled
  Wordlists (from saved state): data/wordlists/comprehensive.txt
  Loaded 44024 words

Resuming autofill...
  Algorithm: repair (fresh fill from the saved grid — exact csp position only resumes with a matching algorithm)
  Timeout: 60s
...
Slots filled 139/140 ; report "Time elapsed" far below the wall time printed by the timing wrapper (60 s wall)
```

### CLI-pause-3 — pause a resumed repair fill
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. Start `resume qa2 -t 90` in the background. 2. After 8 s run `pause qa2`. 3. Watch the process, the state file and the flag directory.
- Expected: help text for pause ("The task will save its current state and exit gracefully at the next checkpoint.")
- Observed: `pause` reports success (exit 0, "Pause requested"), but the resumed run ignores it: it keeps running to its own timeout, ends "PARTIAL", and the state file is not rewritten. The flag and pid files are removed only at the end. The pause request is acknowledged and not honoured.
- Evidence: evidence/CLI-resume-pause.log · evidence/CLI-pause-resumed.log
- Verdict: FAIL · Severity: S2 · Known: #28

```
pause rc=0: Pause requested for task: qa2
resume process still running 18 s later (99% CPU), ended at its 90 s timeout
final: PARTIAL, slots 139/140 ; state file qa2.json.gz timestamp unchanged since the first pause
```

### CLI-import-nyt — import-nyt
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. `import-nyt --help`. 2. Look for a tracked file in the doshea format (needs size rows/cols, flat grid, gridnums, clues, answers). 3. Probe with a tracked NYT-named grid that is not in that format.
- Expected: help text ("Import an NYT crossword JSON file (doshea/nyt_crosswords format)")
- Observed: No tracked file in the required format exists, so a real import could not be run. The probe with the repository's NYT-named template exits 1 with a clear, specific message naming the missing keys.
- Evidence: evidence/CLI-import-nyt.log
- Verdict: NOT-TESTABLE · Severity: — · Known: —

```
{"success": false, "error": "Missing required keys: ['gridnums', 'clues', 'answers']"}
```

### CLI-fill-pkl-cloned — fill with the cache cloned
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. `fill data/grids/example_11x11.json -w data/wordlists/comprehensive.txt -t 60 --json-output` from the clone root, venv active. State of the cache: as cloned (cache and text list share an mtime).
- Expected: "fill" (README.md:65-67); I7 cache-preference variable (spec §2.4)
- Observed: Exit 0 and a complete fill in under a second; the CLI reports the text list's word count as loaded. The fill path reads the text list, so the cache state does not change the outcome here (the cache matters to pattern and analyze, see R5, CLI-analyze, CACHE-1, CACHE-2).
- Evidence: evidence/CLI-fill-pkl-cloned.log
- Verdict: PASS · Severity: — · Known: —

```
{"type": "progress", "progress": 30, "message": "Loaded 44024 words, starting autofill", "status": "running"}
success=True empty_cells=0 slots=44/44 solver_elapsed=0.15s
```

### CLI-fill-pkl-removed — fill with the cache removed
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. `fill data/grids/example_11x11.json -w data/wordlists/comprehensive.txt -t 60 --json-output` from the clone root, venv active. State of the cache: the comprehensive .pkl deleted.
- Expected: "fill" (README.md:65-67); I7 cache-preference variable (spec §2.4)
- Observed: Exit 0 and a complete fill in under a second; the CLI reports the text list's word count as loaded. The fill path reads the text list, so the cache state does not change the outcome here (the cache matters to pattern and analyze, see R5, CLI-analyze, CACHE-1, CACHE-2).
- Evidence: evidence/CLI-fill-pkl-removed.log
- Verdict: PASS · Severity: — · Known: —

```
{"type": "progress", "progress": 30, "message": "Loaded 44024 words, starting autofill", "status": "running"}
success=True empty_cells=0 slots=44/44 solver_elapsed=0.15s
```

### CLI-fill-pkl-rebuilt — fill with the cache rebuilt
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. `fill data/grids/example_11x11.json -w data/wordlists/comprehensive.txt -t 60 --json-output` from the clone root, venv active. State of the cache: the .pkl rebuilt by build-cache.
- Expected: "fill" (README.md:65-67); I7 cache-preference variable (spec §2.4)
- Observed: Exit 0 and a complete fill in under a second; the CLI reports the text list's word count as loaded. The fill path reads the text list, so the cache state does not change the outcome here (the cache matters to pattern and analyze, see R5, CLI-analyze, CACHE-1, CACHE-2).
- Evidence: evidence/CLI-fill-pkl-rebuilt.log
- Verdict: PASS · Severity: — · Known: —

```
{"type": "progress", "progress": 30, "message": "Loaded 44024 words, starting autofill", "status": "running"}
success=True empty_cells=0 slots=44/44 solver_elapsed=0.15s
```

### CLI-fill-minscore — The UI autofill failures reproduced on the CLI, and the one flag that changes them
- Phase: P4-cli · Env: E1 · Viewport: —
- Steps: 1. The UI's own flags on the 11x11 grid (repair, allow-nonstandard) with min score 30, then 50, 60 s cap each.
- Expected: "-t 180 --min-score 30" in the README command (README.md:65-67); the autofill panel default is min score 50
- Observed: With min score 30 the grid fills completely in a fraction of a second. With min score 50, the panel's default, the run ends partial at the same slot count the UI showed in A4 and A5 ("Lower minimum score (currently 50)"). So the UI failures of A2, A4 and A5 come from the panel's default threshold being stricter than the one the README uses; the default threshold fails on the shipped template with the default list, and the progress text calls it "Partial" only after the full timeout. The elapsed time the CLI reports for the partial run is much smaller than its wall time.
- Evidence: evidence/CLI-fill-ms30.log · evidence/CLI-fill-ms50.log
- Verdict: FAIL · Severity: S2 · Known: —

```
min score 30: success=True empty_cells=0 slots=44/44 solver_elapsed=0.15s
min score 50: success=False empty_cells=24 slots=20/44 solver_elapsed=15.02s
wall time of the min-score-50 run: about 60 s (timing wrapper)
```

### API-health — GET /health
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "API healthy" (GET /health, docs/api/openapi.yaml:61); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
GET /health -> 200 (0.07 s)
{"architecture": "cli-backend", "components": {"api_server": "ok", "cli_adapter": "ok"}, "status": "healthy", "version": "2.0.0"}
```

### API-normalize — POST /normalize
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Successfully normalized entry" (POST /normalize, docs/api/openapi.yaml:165); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /normalize -> 200 (0.05 s)
{"alternatives": [], "normalized": "HELLO,WORLD!", "original": "Hello, World!", "rule": {"confidence": "medium", "description": "Default: remove spaces, uppercase", "examples": [], "explanation": "No specific pattern matched - applying default normalization", 
```

### API-pattern — POST /pattern
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Successful pattern search" (POST /pattern, docs/api/openapi.yaml:95); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON. Returns the requested matches from the comprehensive list (as-cloned caches in place).
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /pattern -> 200 (1.98 s)
{"meta": {"pattern": "C?T", "results_returned": 5, "sources_searched": ["comprehensive"], "total_found": 5}, "results": [{"length": 3, "letter_quality": {"common": 2, "regular": 1, "uncommon": 0}, "score": 31, "source": "comprehensive", "word": "CAT"}, {"lengt
```

### API-fill — POST /fill
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Grid filled successfully" (POST /fill, docs/api/openapi.yaml:200); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /fill -> 200 (0.66 s)
{"black_squares": 20, "grid": [["A", "E", "R", "#", "R", "C", "A", "#", "S", "A", "P"], ["O", "A", "K", "#", "I", "R", "S", "#", "P", "E", "A"], ["K", "N", "O", "W", "B", "Y", "H", "E", "A", "R", "T"], ["#", "#", "#", "A", "B", "I", "E", "#", "R", "A", "E"], [
```

### API-constraints — POST /constraints
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Constraint data" (POST /constraints, docs/api/openapi.yaml:1382); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /constraints -> 200 (4.53 s)
{"constraints": {"0,0": {"across_options": 14, "down_options": 1, "min_options": 1}, "0,1": {"across_options": 14, "down_options": 1, "min_options": 1}, "0,10": {"across_options": 1, "down_options": 3, "min_options": 1}, "0,11": {"across_options": 1, "down_opt
```

### API-constraints-impact — POST /constraints/impact
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Placement impact data" (POST /constraints/impact, docs/api/openapi.yaml:1454); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /constraints/impact -> 200 (4.56 s)
{"impacts": {"0,0,down": {"after": 1, "before": 1, "delta": 0, "length": 3}, "0,1,down": {"after": 1, "before": 1, "delta": 0, "length": 3}, "0,2,down": {"after": 0, "before": 1, "delta": -1, "length": 5}}, "success": true, "summary": {"crossings_eliminated": 
```

### API-theme-validate — POST /theme/validate
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Validation result" (POST /theme/validate, docs/api/openapi.yaml:587); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /theme/validate -> 200 (0.0 s)
{"errors": [], "valid": true, "warnings": []}
```

### API-wordlists-search — POST /wordlists/search
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Search results grouped by word" (POST /wordlists/search, docs/api/openapi.yaml:1265); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /wordlists/search -> 200 (0.0 s)
{"pattern": "C?T", "results": [{"sources": ["comprehensive"], "word": "CAT"}, {"sources": ["comprehensive"], "word": "CDT"}, {"sources": ["comprehensive"], "word": "CIT"}, {"sources": ["comprehensive"], "word": "COT"}, {"sources": ["comprehensive"], "word": "C
```

### API-wordlists-get-comprehensive — GET /wordlists/comprehensive
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Wordlist content and metadata" (GET /wordlists/{name}, docs/api/openapi.yaml:1093); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
GET /wordlists/comprehensive -> 200 (0.0 s)
{"metadata": {"auto_generated": false, "category": "core", "created": "2024-12-21", "description": "Complete crossword dictionary with 453,992 words from Matt Abate, Chris Jones, and custom expressions", "difficulty": "all", "filepath": "data/wordlists/compreh
```

### API-wordlists-post-create — POST /wordlists/qa-put
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Wordlist created" (POST /wordlists/{name}, docs/api/openapi.yaml:1136); success code 201
- Observed: Status 403 (differs from the documented 201); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: FAIL · Severity: — · Known: —

```
POST /wordlists/qa-put -> 403 (0.0 s)
{"builtin": true, "category": ".", "error": "Wordlist \"qa-put\" is a built-in list and cannot be overwritten. Built-in lists are read-only; create or import a custom list instead."}
```

### API-wordlists-put — PUT /wordlists/qa-put
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Wordlist updated" (PUT /wordlists/{name}, docs/api/openapi.yaml:1189); success code 200
- Observed: Status 403 (differs from the documented 200); content type application/json; valid JSON. The list created one call earlier by the documented POST (201) is refused by the documented PUT: 403 "is a built-in list and cannot be modified". The list is a top-level file, which the backend classes as built-in, so a list created through the documented create route can be neither edited nor deleted through the documented routes.
- Evidence: evidence/API-all.json
- Verdict: FAIL · Severity: S3 · Known: —

```
PUT /wordlists/qa-put -> 403 (0.0 s)
{"builtin": true, "category": ".", "error": "Wordlist \"qa-put\" is a built-in list and cannot be modified. Built-in lists are read-only; create or import a custom list instead."}
```

### API-wordlists-delete — DELETE /wordlists/qa-put
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Wordlist deleted" (DELETE /wordlists/{name}, docs/api/openapi.yaml:1220); success code 200
- Observed: Status 403 (differs from the documented 200); content type application/json; valid JSON. Same refusal as the PUT: 403, built-in. The created file stays on disk in the sandbox word-list directory.
- Evidence: evidence/API-all.json
- Verdict: FAIL · Severity: S3 · Known: —

```
DELETE /wordlists/qa-put -> 403 (0.0 s)
{"builtin": true, "category": ".", "error": "Wordlist \"qa-put\" is a built-in list and cannot be deleted. Built-in lists are read-only; create or import a custom list instead."}
```

### API-wordlists-import-url — POST /wordlists/import
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "URL import not implemented" (POST /wordlists/import, docs/api/openapi.yaml:1338); success code 501
- Observed: Status 501 (matches the documented 501); content type application/json; valid JSON. The documented 501 is returned. The UI never offers a URL import; the client method for it has no caller.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: I5

```
POST /wordlists/import -> 501 (0.0 s)
{"error": "URL import not yet implemented"}
```

### API-wordlists-import-route-precedence — POST /wordlists/import
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Wordlist imported" (POST /wordlists/import, docs/api/openapi.yaml:1323); success code 201
- Observed: Status 201 (matches the documented 201); content type application/json; valid JSON. POST /wordlists/import is handled by the import route (201 with the imports/ key), not by the create-by-name route that shares its shape; no list named "import" or "search" exists afterwards (see the note). names containing "import" or "search": []
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: I6

```
POST /wordlists/import -> 201 (0.0 s) note: I6: shares POST with the name route
{"message": "Wordlist imported successfully", "name": "imports/qa-i6", "word_count": 2}
```

### API-grid-validate — POST /grid/validate
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Grid validation results" (POST /grid/validate, docs/api/openapi.yaml:376); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /grid/validate -> 200 (0.0 s)
{"black_square_count": 36, "black_square_percentage": 16.0, "suggestions": [], "valid": true, "warnings": [], "word_count": 78, "word_count_range": [72, 78]}
```

### API-grid-suggest-black-square — POST /grid/suggest-black-square
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Suggestions generated" (POST /grid/suggest-black-square, docs/api/openapi.yaml:294); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /grid/suggest-black-square -> 200 (0.0 s)
{"message": "No viable black square positions found for this slot", "slot_info": {"col": 0, "direction": "across", "length": 5, "row": 0}, "suggestions": []}
```

### API-grid-apply-black-squares — POST /grid/apply-black-squares
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Black squares applied" (POST /grid/apply-black-squares, docs/api/openapi.yaml:332); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /grid/apply-black-squares -> 200 (0.0 s)
{"applied": true, "grid": [[".", ".", ".", ".", ".", "#", ".", ".", ".", ".", "#", ".", ".", ".", "."], [".", ".", ".", ".", ".", "#", ".", ".", ".", ".", "#", ".", ".", ".", "."], [".", ".", ".", ".", ".", "#", ".", ".", ".", ".", "#", ".", ".", ".", "."], ["
```

### API-progress-start — POST /progress/start
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Tracker created" (POST /progress/start, docs/api/openapi.yaml:982); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /progress/start -> 200 (0.0 s)
{"task_id": "3f3da127-dadf-404b-a5bb-33bb9410e9e5"}
```

### API-progress-update — POST /progress/3f3da127-dadf-404b-a5bb-33bb9410e9e5/update
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Update accepted (not proof it was delivered — see note above)" (POST /progress/{task_id}/update, docs/api/openapi.yaml:1033); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /progress/3f3da127-dadf-404b-a5bb-33bb9410e9e5/update -> 200 (0.0 s)
{"success": true}
```

### API-progress-get — GET /progress/<id>
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "SSE stream of progress events" (GET /progress/{task_id}, docs/api/openapi.yaml:958); success code 200
- Observed: Status 200 (matches the documented 200); content type text/event-stream; not JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
GET /progress/<id> -> 200 (2 s) note: first event read with curl -m 2
data: {"progress": 50, "message": "qa", "status": "running", "timestamp": 1792665650.270645}  
```

### API-fill-with-progress — POST /fill/with-progress
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Autofill task started" (POST /fill/with-progress, docs/api/openapi.yaml:234); success code 202
- Observed: Status 202 (matches the documented 202); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /fill/with-progress -> 202 (0.01 s)
{"progress_url": "/api/progress/373a5065-9c53-4749-b5c1-9872483d0de7", "task_id": "373a5065-9c53-4749-b5c1-9872483d0de7"}
```

### API-fill-pause — POST /fill/pause/373a5065-9c53-4749-b5c1-9872483d0de7
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Pause requested" (POST /fill/pause/{task_id}, docs/api/openapi.yaml:659); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON. 200 at once; the state file appears only after the solver reaches its next checkpoint (see the note for how long), and the response carries no hint of that delay.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /fill/pause/373a5065-9c53-4749-b5c1-9872483d0de7 -> 200 (0.0 s) note: state file appeared 5.6 s after the pause request (polled every 0.5 s, 20 s cap)
{"message": "Pause requested for task 373a5065-9c53-4749-b5c1-9872483d0de7", "success": true, "task_id": "373a5065-9c53-4749-b5c1-9872483d0de7"}
```

### API-fill-state — GET /fill/state/373a5065-9c53-4749-b5c1-9872483d0de7
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "State info retrieved" (GET /fill/state/{task_id}, docs/api/openapi.yaml:781); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
GET /fill/state/373a5065-9c53-4749-b5c1-9872483d0de7 -> 200 (0.0 s)
{"algorithm": "csp", "grid_preview": [["S", "A", "T", "O", "R", "I", "#", "P", "A", "Y", "U", "P", "#", "R", "A", "C", "#", "E", "A", "S", "T"], ["A", "R", "N", "I", "E", "S", "#", "L", "I", "A", "B", "O", "#", "E", "E", "R", "#", "R", "S", "T", "U"], ["N", "E
```

### API-fill-states-get — GET /fill/states
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "List of saved states" (GET /fill/states, docs/api/openapi.yaml:843); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON. Lists every state in the default state directory, which is outside the sandbox tree (the host temp directory); files left by earlier runs and by the resume route are still listed, and nothing removes them (the cleanup route is the only remover and takes an age in days).
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: #21

```
GET /fill/states -> 200 (0.0 s)
{"count": 2, "states": [{"algorithm": "csp", "grid_size": [21, 21], "iteration_count": 0, "slots_filled": 137, "task_id": "373a5065-9c53-4749-b5c1-9872483d0de7", "timestamp": "2026-10-22T12:41:05.647050", "total_slots": 140, "version": "1.0"}, {"algorithm": "c
```

### API-fill-states-post-plan-listing — POST /fill/states
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: UNSPECIFIED
- Observed: Status 405 (differs from the documented 200); content type application/json; valid JSON. The plan listed this route as POST; the spec documents GET (checked in fill-states-get). POST returns 405. This is a plan-versus-spec difference, not an app defect.
- Evidence: evidence/API-all.json
- Verdict: UNSPECIFIED · Severity: — · Known: —

```
POST /fill/states -> 405 (0.0 s) note: the plan lists this as POST; the spec documents GET
{"error": {"code": "METHOD_NOT_ALLOWED", "message": "Method not allowed"}}
```

### API-fill-edit-summary — POST /fill/edit-summary
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Edit summary" (POST /fill/edit-summary, docs/api/openapi.yaml:916); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /fill/edit-summary -> 200 (0.0 s)
{"cells_changed": 0, "cells_emptied": 366, "cells_filled": 0, "emptied_count": 0, "filled_count": 0, "modified_count": 0, "new_words": [], "partial_count": 0, "removed_words": []}
```

### API-fill-resume — POST /fill/resume
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Resume state prepared" (POST /fill/resume, docs/api/openapi.yaml:739); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON. 200 "Resume completed" with a result that reports the fill as not complete (percentage below 100, all_slots_filled false). Bad inputs (unknown wordlist, malformed edited grid) are rejected before the CLI runs, with 400 and 409, so #38 was not reproduced through them.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /fill/resume -> 200 (20.65 s)
{"message": "Resume completed", "new_task_id": "resume_c893eb1a", "original_task_id": "373a5065-9c53-4749-b5c1-9872483d0de7", "result": {"all_slots_filled": false, "fill_percentage": 97, "grid": [["S", "A", "T", "O", "R", "I", "#", "P", "A", "Y", "U", "P", "#"
```

### API-fill-cancel — POST /fill/cancel/373a5065-9c53-4749-b5c1-9872483d0de7
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Cancel request processed" (POST /fill/cancel/{task_id}, docs/api/openapi.yaml:698); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /fill/cancel/373a5065-9c53-4749-b5c1-9872483d0de7 -> 200 (0.0 s) note: run against a live task started 3 s earlier; in the sequenced run the task had already stopped and the same call returned 404 TASK_NOT_FOUND
{"message": "Autofill cancelled", "state_saved": false, "success": true, "task_id": "..."}
```

### API-fill-state-delete — DELETE /fill/state/373a5065-9c53-4749-b5c1-9872483d0de7
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "State deleted" (DELETE /fill/state/{task_id}, docs/api/openapi.yaml:809); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
DELETE /fill/state/373a5065-9c53-4749-b5c1-9872483d0de7 -> 200 (0.0 s)
{"message": "State deleted for task 373a5065-9c53-4749-b5c1-9872483d0de7", "success": true}
```

### API-fill-states-cleanup — POST /fill/states/cleanup
- Phase: P5-api · Env: E1 · Viewport: —
- Steps: 1. Build the request body from the operation's schema in docs/api/openapi.yaml. 2. Call it with curl-equivalent JSON and record status and a body excerpt.
- Expected: "Cleanup completed" (POST /fill/states/cleanup, docs/api/openapi.yaml:876); success code 200
- Observed: Status 200 (matches the documented 200); content type application/json; valid JSON.
- Evidence: evidence/API-all.json
- Verdict: PASS · Severity: — · Known: —

```
POST /fill/states/cleanup -> 200 (0.0 s)
{"deleted_count": 0, "message": "Deleted 0 old state files", "success": true}
```

### R11 — README pytest run, alone, after the walkthrough
- Phase: P0-tests · Env: E1 · Viewport: —
- Steps: 1. With no server running, `pytest` from the clone root, venv active. 2. Read the failures. 3. Restore the tracked word-list metadata file (git checkout in the sandbox clone) and rerun only the failing test file.
- Expected: "pytest" runs backend + CLI tests (README.md:82-84)
- Observed: The suite runs to the end; all but three tests pass. The three failures are in the word-list metadata test file and are caused by entries my earlier API import calls wrote into the tracked metadata file, which have no "name" field (see API-import-metadata-name). With that file restored the metadata test file passes, so on an untouched clone the failures would not appear; they show that using the documented import route breaks the repository's own invariant test. The setup step had already installed the test tools, so there is no missing-tool finding.
- Evidence: evidence/R11.log · evidence/R11-metadata-clean.log
- Verdict: FAIL · Severity: S3 · Known: —

```
========== 3 failed, 1893 passed, 82 deselected in 342.57s (0:05:42) ===========
FAILED backend/tests/integration/test_wordlist_metadata.py::TestWordlistMetadataStructure::test_all_wordlists_have_name_field
FAILED backend/tests/integration/test_wordlist_metadata.py::TestWordlistMetadataStructure::test_all_wordlists_have_required_fields
FAILED backend/tests/integration/test_wordlist_metadata.py::TestWordlistMetadataPersistence::test_metadata_json_has_no_missing_names
--- after restoring the metadata file ---
============================== 12 passed in 0.08s ==============================
```

### API-import-metadata-name — POST /wordlists/import writes a metadata entry without a name
- Phase: P0-tests · Env: E1 · Viewport: —
- Steps: 1. Import two lists through the documented route (done in P5). 2. Read the entries it added to the tracked metadata file. 3. Run the metadata tests.
- Expected: docs/api/openapi.yaml `/wordlists/import` returns 201 "Wordlist imported"; the repository's own test requires every metadata entry to have a name field
- Observed: The two imported lists were added to the metadata file with a category, description, tags and source but no name, which the repository's metadata tests reject. The UI upload path (L5-L13) wrote entries that include a name; only the API import route did not.
- Evidence: evidence/metadata-polluted.json · evidence/R11.log
- Verdict: FAIL · Severity: S3 · Known: —

```
entries added by the import route:
: {       "category": "imports",       "description": "Imported wordlist",       "tags": [         "imported"       ],       "source": "direct_import"     },     "qa-put": {       "name": "Qa-Put",       "category": ".",       "description": "User-created word
```

### R12 — README npm test
- Phase: P0-tests · Env: E1 · Viewport: —
- Steps: 1. `npm test` from the clone root. 2. After 5 minutes, observe whether it exited; kill it. 3. `npx vitest run` for a result.
- Expected: "npm test" runs the frontend tests (README.md:86-87)
- Observed: `npm test` runs every test file, prints the summary, then stays in watch mode ("Waiting for file changes") and never returns to the shell; in a script or CI that blocks forever. The one-shot form returns promptly with the same summary and exit 0. The README does not say the first form is interactive.
- Evidence: evidence/R12.log · evidence/R12-run.log
- Verdict: PASS · Severity: S4 · Known: —

```
npm test (killed after the limit):
Test Files  20 passed (20)
Tests  229 passed (229)
PASS  Waiting for file changes...
npx vitest run:
Test Files  20 passed (20)
Tests  229 passed (229)
```

### R13 — README npm run test:coverage
- Phase: P0-tests · Env: E1 · Viewport: —
- Steps: 1. `npm run test:coverage` from the clone root.
- Expected: "npm run test:coverage" (README.md:89-91)
- Observed: Runs the tests, prints a coverage table, and, like R12, then waits in watch mode instead of exiting.
- Evidence: evidence/R13.log
- Verdict: PASS · Severity: S4 · Known: —

```
Test Files  20 passed (20)
Tests  229 passed (229)
All files          |   63.03 |    81.24 |   69.31 |   63.03 |
PASS  Waiting for file changes...
```
