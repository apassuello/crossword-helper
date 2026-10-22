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
| R5 | 62 | `pattern "C?T" -w data/wordlists/comprehensive.txt --json-output` | Task 10 | |
| R6 | 64 | "11x11, 15x15, and 21x21 templates included" | Task 2 | PASS |
| R7 | 65–67 | the `fill data/grids/example_15x15.json … -t 180 --min-score 30 -o filled.json` command | Task 10 | |
| R8 | 70 | `validate puzzle.json` | Task 10 | |
| R9 | 73 | `new --size 15 -o puzzle.json` | Task 10 | |
| R10 | 76 | `export filled.json --format html -o puzzle.html` | Task 10 | |
| R11 | 82–84 | `pytest` runs backend + CLI tests | Task 13 | |
| R12 | 86–87 | `npm test` runs the frontend tests | Task 13 | |
| R13 | 89–91 | `npm run test:coverage` | Task 13 | |
| R14 | 31–32 | "interactive editing with keyboard shortcuts, symmetry enforcement, and auto-numbering" | Task 8 | |
| R15 | 33–34 | pattern `C?T` "gives CAT, COT, CUT, etc." | Task 9 | |
| R16 | 35–36 | autofill "using CSP with backtracking, beam search, or iterative repair; supports theme word locking" | Task 7 | |
| R17 | 37–38 | "ships with 44k curated words; upload your own or combine multiple lists" | Tasks 6, 9 | |
| R18 | 39 | "Export -- HTML format" | Task 9 | |
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
