# Fresh-install reproduction run — 2026-10-22

## Header

- Clone target sha: <filled in Task 2>
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
| R1 | 19–21 | `chmod +x setup.sh` / `./setup.sh` is the one-time setup | Task 4 | |
| R2 | 23–25 | `source venv/bin/activate` then `python3 run.py` runs the app | Task 5 | |
| R3 | 26 | "Open http://localhost:5000" | Task 5 | |
| R4 | 46–51 | dev mode: `python3 run.py` + `npm run dev`, open :3000 | Task 5 | |
| R5 | 62 | `pattern "C?T" -w data/wordlists/comprehensive.txt --json-output` | Task 10 | |
| R6 | 64 | "11x11, 15x15, and 21x21 templates included" | Task 2 | |
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
| R19 | setup.sh:67 | "Frontend built to frontend/dist/" | Task 4 | |
| R20 | 105 | the Resources PDF link resolves | Task 2 | |

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
