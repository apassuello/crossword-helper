# Crossword Construction Helper

Crossword puzzle construction toolkit: React frontend, Flask backend, Python CLI.

> **No status claims in this file.** Test counts, pass rates, phase-completion and version-status
> statements go stale silently, then get asserted as fact into every session. For current state run
> `pytest` and read `git log`. CI enforces this — do not re-add them.

**Stack**: Python 3.9+ · Flask 3.0 · Click · NumPy · React 18 · Vite 5 · SCSS
**Build**: pip + npm · **Test**: pytest + vitest

---

## Commands

```bash
python run.py                  # Flask backend -> :5000
npm run dev                    # Vite dev server -> :3000 (proxies /api to :5000)
npm run build                  # must stay clean
pytest                         # default suite; slow tests deselected
pytest -m slow                 # slow suite
npx vitest run                 # frontend tests
python -m cli.src.cli --help   # 14 CLI commands; --help per command is authoritative
```

---

## Architecture

**The CLI is the single source of truth.** All crossword logic lives in `cli/`. The backend is a
thin HTTP wrapper that shells out to it via `backend/core/cli_adapter.py` — that adapter is the
integration seam and the place bugs hide.

```
src/ (React) --HTTP+SSE--> backend/ (Flask) --subprocess--> cli/ (logic)
```

Add capability CLI-first, then adapter, then route, then UI.

---

## Code Patterns

- **New capability**: CLI command → `cli_adapter.py` method → Flask route → React. Never skip a layer.
- **Autofill**: CSP (`fill/autofill.py`), beam search (`fill/beam_search/`), iterative repair
  (`fill/iterative_repair.py`, the `--algorithm` default), and a `hybrid` of beam+repair.
- **Pattern matching**: `fill/pattern_matcher.py` (regex) and `fill/trie_pattern_matcher.py` (trie).
- **Pause/resume**: file-based IPC. CLI serializes solver state to gzipped JSON; resume applies user
  edits as locked cells and continues from that position.
- **Seam tests**: the backend↔CLI boundary needs a contract test on argv acceptance plus one real
  subprocess e2e. Mocks on both sides hide breakage — that is how pause/resume shipped broken.

---

## Anti-Patterns

❌ Crossword logic in `backend/` or `src/` → ✅ implement in `cli/`, expose via the adapter
Why: two implementations diverge; the CLI is the contract.

❌ Mocking both sides of the backend↔CLI seam → ✅ one real-subprocess e2e
Why: a green suite once coexisted with pause/resume broken end to end.

❌ Quoting counts, timings or "FIXED" in docs or docstrings → ✅ name the command that proves it
Why: source docstrings claimed a "454k word" list; the file has ~44k. See `docs/dev/FABRICATION-LOG.md`.

❌ Gating a liveness check on an iteration counter → ✅ gate it on elapsed time
Why: `iterations % N == 0` bounds latency only if an iteration is cheap. Pause was polled that way
on both solver paths; a beam iteration on a blank 15x15 outlasts the whole run, so `iterations`
reached 1 in 20s and the pause flag was never read (#26). `autofill.py` already learned this for
timeouts — "checking only every 100 iterations let slow-running grids overrun the timeout budget,
since iteration count alone does not track wall-clock time".

---

## Extensibility

- **Skills** (`.claude/skills/`): `crossword-domain` — NYT grid rules, symmetry, entry conventions.
- **Hooks**: `.pre-commit-config.yaml` runs black, isort, ruff, flake8 on commit. Formatting and
  linting are enforced there — do not add style rules to this file.

---

## Git & Docs

- Branch `type/short-description`; commit `type(scope): imperative description`.
- Before pushing: `pytest`, `npm run build`, let pre-commit run (never `--no-verify`).
- `docs/README.md` is the navigation index; `CONTRIBUTING.md` holds setup and full conventions.
- Living docs under `docs/` use HADS blocks; unverified claims go in `[?]`, never asserted as fact.
