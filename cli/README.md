# Crossword CLI

**Version 2.0.0** · 2026-08-16

---

## AI READING INSTRUCTION

Read `[SPEC]` and `[BUG]` blocks for authoritative facts.
Read `[NOTE]` only if additional context is needed.
`[?]` blocks are unverified.

---

## 1. What this is

**[SPEC]**
- The crossword construction engine. All puzzle logic lives here.
- The Flask backend is a thin wrapper that invokes these commands via subprocess,
  so this CLI is the single source of truth for behaviour.
- Full command reference: `docs/specs/CLI_SPEC.md`. Per-command truth: `--help`.

---

## 2. Invocation

**[SPEC]**
There is no installed `crossword` entrypoint and no `setup.py`. Run as a module
from the repository root:

```bash
python -m cli.src.cli --help          # list all commands
python -m cli.src.cli <command> --help # authoritative options for one command
```

Dependencies come from the repo-root `requirements.txt`; `cli/requirements.txt`
lists the CLI-only subset.

---

## 3. Layout

**[SPEC]**

| Package | Contents |
|---|---|
| `src/core/` | grid structure (NumPy), numbering, validation, scoring, entry conventions |
| `src/fill/` | autofill algorithms, pattern matchers, wordlist handling, pause/resume state |
| `src/export/` | export (HTML) |

`src/cli.py` is a flat module, not a package.

---

## 4. Capabilities

**[SPEC]**
- Autofill: CSP with backtracking + AC-3 (`fill/autofill.py`), beam search
  (`fill/beam_search/`), iterative repair (the `--algorithm` default), and a beam+repair hybrid.
- Pattern matching: regex (`fill/pattern_matcher.py`) and trie
  (`fill/trie_pattern_matcher.py`).
- Pause/resume: solver state serialises to gzipped JSON; resume applies user edits
  as locked cells and continues from the saved position.
- Export: **HTML only.** PDF, `.puz` and JSON export do not exist.

**[NOTE]**
An earlier version of this file described a Clue Manager (`src/clues/`), a `src/cli/`
package, PDF/`.puz`/JSON export, and an `interactive` command. None were ever built.
The file was written at project scaffold time and never revised. See
`docs/dev/FABRICATION-LOG.md` for the wider pattern.

---

## 5. Development

**[SPEC]**
```bash
pytest cli/tests/ -q      # CLI suite
black cli/src/            # formatting (also enforced by pre-commit)
```

Benchmarks are manual scripts, not pytest tests — see `cli/tests/performance/README.md`.
That directory is the only place timing figures belong; do not quote them elsewhere.

---

## 6. Changelog

- 2.0.0 (2026-08-16) — rewritten against the actual codebase. The previous version
  described a scaffold that had been superseded in every particular.
