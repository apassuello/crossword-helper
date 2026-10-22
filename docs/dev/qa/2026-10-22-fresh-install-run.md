# Fresh-install reproduction run — 2026-10-22

## Header

- Clone target sha: <filled in Task 2>
- `origin/main` sha and `$MAIN` HEAD are in the fence below. origin/main lags local main until Arthur pushes; the friend's reinstall gets origin.
- E1 python: <filled in Task 1>
- E1 node: <filled in Task 1>
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
