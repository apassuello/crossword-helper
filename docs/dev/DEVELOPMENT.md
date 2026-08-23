# Development Guide

**Version 3.0.0**
**Document Type:** Developer Onboarding & Workflow Guide

---

## AI READING INSTRUCTION

Read `[SPEC]` and `[BUG]` blocks for authoritative facts.
Read `[NOTE]` only if additional context is needed.
`[?]` blocks are unverified.

This document covers **onboarding, the day-to-day dev loop, and debugging gotchas only**.
It does not duplicate reference material that lives elsewhere:

- System design, directory layout, component responsibilities → `docs/ARCHITECTURE.md`
- CLI command reference → `docs/specs/CLI_SPEC.md`
- HTTP API reference → `docs/api/API_REFERENCE.md`
- Test strategy and suite organization → `docs/ops/TESTING.md`

Any number in this document that a command can print (test counts, wordlist sizes, coverage
percentages) is deliberately omitted — run the command instead. Numbers go stale; commands don't.

---

## Overview

**[SPEC]**
Crossword Helper is a crossword construction toolkit: a Click-based CLI (`cli/`) holds all
business logic, and a Flask backend (`backend/`) wraps it via `subprocess.run()` for the React
frontend (`src/`). See `docs/ARCHITECTURE.md` for the full rationale and diagrams.

- Backend: Python, Flask 3.0, Click 8.1
- Frontend: React 18, Vite 5, SCSS, Axios
- Algorithms: NumPy, CSP w/ backtracking, Beam Search, trie-based pattern matching

---

## Getting Started

### Prerequisites

**[SPEC]**
- Python 3.9+ (repo's `pyproject.toml` targets `py39`; this machine runs 3.12)
- Node.js 18+, npm 9+
- Git

### Setup

**[SPEC]**
```bash
git clone <repository-url>
cd crossword-helper

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt   # backend + CLI deps (CLI has no separate requirements.txt)
npm install                       # frontend deps
```

**[?]** No `setup.py`/`pyproject.toml` `[project]` table or console-script entry point exists
for the CLI — `pip install -e .` does **not** produce a global `crossword` command. Invoke the
CLI directly instead:
```bash
python -m cli.src.cli --help
# or
python cli/crossword --help
```

### Verify Installation

**[SPEC]**
```bash
python -c "from backend.app import app; print('Backend OK')"
npm run build                     # should complete without errors
pytest backend/tests/unit/ -v     # should run and report pass/fail counts
```

---

## Running the Dev Servers

**[SPEC]**
```bash
# Terminal 1 — Flask backend (debug mode, auto-reload; see run.py)
python run.py                     # → http://localhost:5000

# Terminal 2 — Vite dev server (HMR)
npm run dev                       # → http://localhost:3000, proxies /api/* to :5000
```

Production build: `npm run build` (outputs to `frontend/dist/`), then `python run.py` serves the
built frontend from Flask directly — no second terminal needed.

**[NOTE]** `run.py` hardcodes `host='localhost', debug=True`. There is no separate
production-mode launcher in this repo; if you need a non-debug run, edit `run.py` or set
`app.debug = False` before `app.run()`.

---

## Project Structure

**[SPEC]** Full directory tree, module responsibilities, and the "why" behind the layout live in
`docs/ARCHITECTURE.md` — this file does not repeat it (a second copy is how the old version of
this document drifted: it had 6 API blueprints where the real count is 7, 8 CLI commands where
the real count is 14, and five React component filenames that don't exist in `src/components/`).

The one thing worth stating here because it changes your day-to-day: **the CLI is the only place
business logic belongs.** `backend/api/*.py` routes should stay thin — validate the request, call
`CLIAdapter`, return JSON. If you're writing crossword logic (grid, scoring, fill algorithms) in
`backend/`, it's in the wrong layer.

---

## Development Workflow

### Test loop

**[SPEC]**
```bash
pytest backend/tests/unit/ -v          # fast, isolated — run this constantly
pytest -m "not slow"                   # default suite (this is pytest.ini's addopts)
pytest                                  # everything, including slow-marked tests
pytest path/to/test_file.py::test_name -vv   # single test, verbose
```
`pytest.ini` sets `testpaths = backend/tests cli/tests tests` and `addopts = -v -m "not slow"` —
there is no coverage flag baked into `addopts`; pass `--cov=backend --cov=cli` explicitly when
you want a coverage report.

### Format and lint

**[SPEC]** Config lives in `pyproject.toml` (line-length 127, not Black's 88 default) and is
enforced by the real `.pre-commit-config.yaml` in the repo root (black, isort, ruff).
```bash
black .
ruff check --fix .
pre-commit install        # one-time, wires the above into git commit
```

**[?]** No ESLint or Prettier config file exists anywhere in the repo despite older drafts of
this document showing one — JS/JSX is currently unformatted-by-tooling. Frontend tests run via
`npm run test` (Vitest), not the "React Testing Library (future)" note from an earlier draft.

### Branching / PRs

**[NOTE]** Standard feature-branch flow: branch off `main`, commit, push, open a PR. Nothing
project-specific here beyond what your normal git workflow already does — this document used to
carry a generic branching/PR-checklist tutorial; it added no information a new contributor
doesn't already have from using git and GitHub.

---

## Debugging & Gotchas

**[BUG] CLI subprocess not found**
- Symptom: `subprocess.CalledProcessError` / `FileNotFoundError` from `CLIAdapter`, or `crossword: command not found` at a shell.
- Cause: there is no installed `crossword` console script (see Setup above).
- Fix: invoke via `python -m cli.src.cli ...` or `python cli/crossword ...`, or set the path `CLIAdapter` uses explicitly rather than relying on `$PATH`.

**[BUG] `ImportError: cannot import name 'app' from 'backend.app'`**
- Cause: project root not on `PYTHONPATH`, or backend not run from the repo root.
- Fix: run commands from the repo root, or `export PYTHONPATH="${PYTHONPATH}:$(pwd)"`.

**[BUG] `OSError: [Errno 48] Address already in use`**
- Cause: a previous `python run.py` (port 5000) or `npm run dev` (port 3000) is still running.
- Fix: `lsof -i :5000` (or `:3000`), `kill -9 <PID>`, or change the port in `run.py` / `vite.config.js`.

**[BUG] CORS errors from the Vite dev server**
- Symptom: `Access to XMLHttpRequest blocked by CORS policy` when the frontend calls the backend directly instead of through the Vite proxy.
- Cause: `backend/app.py` configures `flask_cors.CORS` for known dev origins; hitting the backend from an unexpected origin/port bypasses that allowlist. Also check you're using `npm run dev` (which proxies `/api/*`) rather than opening the built frontend against a mismatched backend port.

**[BUG] `npm install` fails partway**
- Fix: `npm cache clean --force`, delete `node_modules` and `package-lock.json`, `npm install` again.

**[NOTE]** For interactive debugging, `pdb`/`ipdb` breakpoints in Python and Chrome DevTools /
React DevTools on the frontend work exactly as they do in any Flask + React project — there is
nothing crossword-helper-specific about how to set a breakpoint, so it isn't repeated here.

---

## Adding a New Feature

**[NOTE]** The standard shape — CLI command → `CLIAdapter` method → Flask route → React component
— is already spelled out with a worked (hypothetical) example in the project root `CLAUDE.md`
under "Adding a New API Endpoint." This document previously carried a second, much longer version
of the same walkthrough (~600 lines, building a hypothetical "black square suggestions" feature)
that duplicated it almost line-for-line. It's been removed rather than kept in parallel — two
copies of the same tutorial drift, and one already had gone stale. If you extend that CLAUDE.md
example, keep its file paths and function names explicitly hypothetical; don't let them read as
claims that those exact files exist.

---

## Working with Wordlists

**[SPEC]** Wordlist files are one word per line, uppercase, no header, no score column —
verified against `data/wordlists/comprehensive.txt`. This differs from an older draft of this
document, which described a tab-separated `WORD  SCORE  SOURCE` format that does not match any
wordlist file actually in the repo. The scored variant that does exist,
`comprehensive_scored.txt`, uses `WORD;SCORE` (semicolon-delimited), documented in its own
header comment.

```bash
# Add a wordlist: drop a .txt file (one word per line, uppercase) into data/wordlists/
# The backend/frontend wordlist selector picks it up automatically — no code change needed.
```

For wordlist size, provenance, and filtering criteria, see `data/wordlists/README.md` — it's a
dated, self-contained record and shouldn't be re-summarized (and re-staled) here.

---

## Performance

**[NOTE]** An earlier draft of this document carried benchmark tables (grid-fill times, API
response targets, "10-50x faster" pattern-matching claims) and profiler tutorials as if they were <!-- docs-check: allow -->
current, verified numbers. None were reproducible from a cited command or benchmark script, so
they've been cut rather than re-asserted. If you need real numbers, profile the specific path
you care about:
```bash
python -m cProfile -o /tmp/profile.out -m cli.src.cli fill puzzle.json -w <wordlist> -t 60
```
and read `/tmp/profile.out` with `pstats`. Don't trust a number in prose that a command could
have produced instead.

---

## Troubleshooting

Covered above under **Debugging & Gotchas**. If you hit something not listed there, check
`docs/ARCHITECTURE.md` and `docs/ops/TESTING.md` before assuming it's undocumented — this
section used to duplicate the gotchas list a second time under a different heading; the two
copies had already started to diverge.

---

## Resources

**[SPEC]**
- `docs/ARCHITECTURE.md` — system design
- `docs/api/API_REFERENCE.md`, `docs/api/openapi.yaml` — HTTP API
- `docs/specs/CLI_SPEC.md` — CLI reference (the only file left in `docs/specs/`; `BACKEND_SPEC.md`
  and `FRONTEND_SPEC.md` were moved to `.archive/docs/`)
- `docs/ops/TESTING.md` — test strategy

**[?]** An earlier draft's "Community" section pointed to a Slack channel and team email as
placeholders with no actual values filled in, plus a generic list of external tutorial links
(Real Python, React docs, Wikipedia). Removed as orphaned boilerplate rather than corrected —
there was nothing project-specific to correct it into.

---

## Changelog

- **3.0.0** — Full rewrite to HADS format. Cut ~3,900 lines of generic tooling tutorials
  (PEP 8/ESLint/pdb walkthroughs, IDE config dumps), a full directory-tree/config duplicate of
  `docs/ARCHITECTURE.md`, a fabricated benchmark/performance section, a fabricated bug-fix
  narrative referencing a test file that doesn't exist, and a ~600-line duplicated "adding a
  feature" tutorial. Corrected stale counts (7 API blueprints not 6, 14 CLI commands not 8),
  wrong filenames (`trie_pattern_matcher.py`, `WordListPanel.jsx`, `ThemeWordsPanel.jsx`,
  `BlackSquareSuggestions.jsx`, `ProgressIndicator.jsx`), a fabricated wordlist TSV format, and a
  fabricated `pip install -e .` / `crossword` console-script claim. Removed all embedded test
  counts and pass-rate claims — run `pytest` instead.
- **2.0.0 / 1.0.0** — Prior versions carried conflicting version numbers in header vs. footer;
  not reconstructable as a real history, so not preserved as an archival record.
