# Contributing

**Version 1.0.0** · 2026-08-15

---

## AI READING INSTRUCTION

Read `[SPEC]` and `[BUG]` blocks for authoritative facts.
Read `[NOTE]` only if additional context is needed.
`[?]` blocks are unverified.

---

## 1. Setup

**[SPEC]**
```bash
pip install -r requirements.txt
npm install
pre-commit install          # black, isort, ruff, flake8 run on commit
```

Run the app (two terminals):
```bash
python run.py               # Flask backend  -> :5000
npm run dev                 # Vite dev server -> :3000 (proxies /api to :5000)
```

---

## 2. Architecture rule

**[SPEC]**
- All crossword logic lives in `cli/`. The backend is a thin HTTP wrapper that shells out to it.
- A new capability is added to the CLI **first**, then exposed via `backend/core/cli_adapter.py`,
  then routed in `backend/api/`, then wired in `src/`.
- Do not implement crossword logic in `backend/` or `src/`. Two implementations will diverge.

---

## 3. Tests

**[SPEC]**
```bash
pytest                                   # default suite (slow tests deselected)
pytest -m slow                           # slow suite only
pytest --cov=backend --cov=cli           # with coverage
npx vitest run                           # frontend
npm run build                            # must stay clean
```

Markers registered in `pytest.ini`: `slow`, `integration`, `unit`.

**[BUG] Tests that spawn CLI subprocesses run ~4x slower under coverage**
- Symptom: subprocess-spawning tests time out only in the `--cov` CI job, not locally.
- Cause: `pytest-cov` installs a `.pth` that runs `pytest_cov.embed.init()` in *every* Python
  subprocess when `COV_CORE_SOURCE` is set.
- Fix: scrub `COV_CORE_*` from the child environment (monkeypatch) before spawning.
- Do not diagnose this as "slow CI runners" — that misdiagnosis cost three CI attempts.

---

## 4. Documentation rules

**[SPEC]**
- **No derivable state in prose.** If a command produces the number, print the command, not the
  number. Banned in living docs: test counts, pass rates, coverage %, wordlist sizes, `Status:
  Complete`, `✅ FIXED`. CI enforces this. <!-- docs-check: allow -->
- Living docs in `docs/` follow HADS (`[SPEC]` / `[NOTE]` / `[BUG]` / `[?]` blocks + AI manifest).
- `.claude/CLAUDE.md` follows the claude-meta template instead, and stays under 80 lines.
- Unverified claims go in a `[?]` block. Never assert them as fact.
- Timing or size figures in **code comments** need the command that reproduces them, or state
  complexity instead. See `docs/dev/FABRICATION-LOG.md` for why this rule exists.
- Dated historical records are archival. Do not "correct" them — archive them.

---

## 5. Commits and branches

**[SPEC]**
- Branch: `type/short-description`.
- Commit: `type(scope): imperative description` — e.g. `fix(ci): widen CLI subprocess timeout`.
- Types in use: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- Before pushing: `pytest`, `npm run build`, and let pre-commit run (do not `--no-verify`).

---

## 6. Changelog

- 1.0.0 (2026-08-15) — written during the docs overhaul. Replaces an 18-line stub that had been
  archived unwritten ("Content will be populated shortly").
