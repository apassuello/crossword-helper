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
| Install | | |
| New: ZIP | | |
| Grid | | |
| New: SAVE-NAMED | | |
| Grid guards | | |
| New: CL-CLEAN-GUARD | | |
| New: PORT | | |
| New: SETUP-MISSING | | |
| New: CLEAN-PREV | | |
| New: MACOS | | |
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
