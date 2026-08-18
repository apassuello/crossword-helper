# M1 Task 8 (F2) — Server-Authoritative Numbering + Validation Violations — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development / executing-plans to implement task-by-task. Steps use checkbox (`- [ ]`) syntax.
> **STATUS: FINAL — reviewed 2026-07-13 (correctness 10/10 confirmed; quality ready-after-fixes) + owner decisions + quality punch-list + advisor integration-hardening all applied. Ready to implement.** Expands Task 8 of `docs/superpowers/plans/2026-07-12-m1-constructors-bench.md:446-457`.
> **Convention:** signatures/contracts/short snippets only — implementer agents write full bodies. Test steps may show concrete assertions.

**Branch:** `feature/m1-constructors-bench` · **HEAD:** `116bda5` · **Repo:** `/Users/apa/projects/crossword-helper`

## Decisions applied (owner, 2026-07-13)
- **Short-word check:** deliver it via a NEW independent run-length scan `_scan_short_words` inside `validate_structural` — bypasses the dead `_check_minimum_word_length`/`get_word_slots` path (do NOT touch `get_word_slots`). C delivers connectivity + short-word.
- **Adaptive autofill:** SHIP AS-IS — adaptive black-square additions are a genuine structural change and correctly trigger renumber+revalidate. No autofill bypass.
- **handle_error bug:** defensive workaround in Task A (catch locally); pre-existing 3-site bug logged as a follow-up (trust-ledger §E), NOT fixed here.
- **Commits:** 4 TDD-sized commits (A/B/C/D), squashable at merge.

---

## Goal
After every **structural** grid edit (black-square toggle, size change, load/import): (1) optimistically renumber locally for instant display, (2) POST `/api/number` and reconcile server-wins, (3) POST `/api/grid/validate` in parallel and surface `violations` in the ToolRail. Letter edits **never** renumber. Replaces client-only numbering (`src/App.jsx:126-167`); extends `/api/grid/validate` with structural checks (D1:C).

## Architecture
```
Structural edit (isBlack/size change)
  → useNumbering detects via structural signature (size + isBlack layout only)
  → localNumber(grid) [pure] → setGrid(optimistic) SYNCHRONOUSLY + unverified=true   ← instant paint
  → 150ms debounce
  → POST /api/number (CLI strings) ─┐  both independent, one shared request token
  → POST /api/grid/validate         ─┘
  → numberGrid resolve → applyNumbering(gridRef.current, resp.numbering) [server wins] → setGrid + numbering + unverified=false
  → validateGrid resolve → violations = [...warnings, ...suggestions]
```
Backend: `/api/grid/validate` (`backend/api/grid_routes.py:185-262`) gains a `GridValidator`-backed structural pass merged into the existing response. No new endpoint.

## Tech Stack
Backend: Flask (`backend/api/grid_routes.py`) + CLI core in-process (`cli/src/core/{grid,validator}.py`); pytest + Flask test client. Frontend: React hook (`src/hooks/useNumbering.js`), vitest + `@testing-library/react` (`renderHook`/`act`/fake timers), `src/api/{client,gridCodec}.js`.

## Global Constraints
1. **CLI strings on the wire.** Payloads to `/api/number` + `/api/grid/validate` are `gridCodec.toCliStrings(grid)` (`gridCodec.js:31-39`); `Grid.from_dict` calls `cell.isalpha()` (`grid.py:343`) — dict cells raise. New tightened contract for `/api/grid/validate`, matching `/api/number`.
2. **Server wins.** Reconcile always applies `/api/number`'s response over the optimistic pass via `applyNumbering` (`gridCodec.js:65-77`).
3. **Letter edits never renumber.** Structural: hook fires only when `(size, isBlack-layout)` signature changes.
4. **Latency accepted deviation.** <80ms budget unmeetable over subprocess (~120–180ms). Optimistic local pass is the UX guarantee.
5. **Zero new endpoint surface.** `/api/grid/validate` extended in place (D1:C).
6. **`doc.numbering` stays unparenthesized `"row,col"`** (`ExportPanel.jsx:80`, `App.jsx:575-576`) — NOT the server's `"(r,c)"` (`gridCodec.js:58`). See Task C DD3.
7. **Violations are advisory + LIVE, not a gate.** `valid`/violations go non-clean on most mid-construction grids (transient short runs, disconnection while placing black squares), and adaptive fill is the noisiest moment. This is intended, but the surface is a live nag, not a final check — Task D smoke MUST confirm it reads as advisory, not "broken." Muting violations during an active fill is a Task-11 option (see Follow-ups).

---

## Task A — Backend: extend `/api/grid/validate` with structural checks (D1:C)

### Files
- Modify: `cli/src/core/validator.py` (new `validate_structural` + new private `_scan_short_words`)
- Modify: `backend/api/grid_routes.py:185-262` (`validate_grid` handler)
- Modify: `cli/tests/unit/test_validator.py` (add `import pytest` if absent — currently missing; new test class)
- Create: `backend/tests/unit/test_grid_routes.py` (no prior coverage)

### DD1 — Input contract: CLI-strings only
Existing word-count/black-density path is shape-agnostic (`black_square_suggester._is_black_cell:280-285` handles dict OR `"#"`), so requiring CLI strings for the new `Grid.from_dict` path doesn't break it. `api.validateGrid` (`client.js:124-126`) is the only caller and has ZERO App callers today (App's `validateGrid` refs all resolve to the local stub `:235`). **Guard: wrap the ENTIRE structural block (`Grid.from_dict` + `validate_structural`) in `try/except Exception` — NOT just `(ValueError, AttributeError)`.** This local catch is the SOLE thing keeping the path off the broken `handle_error(...default_status=)` fallback (§E), and `Grid.from_dict`/`_scan_short_words` can throw outside those two types (IndexError/KeyError on malformed input); any uncaught type would hit the broken fallback and reproduce the exact double-`TypeError` we're avoiding. On failure → degrade structural check to empty errors + `logger.warning` (preserves "always 200").

### DD2 — `validate_structural`: connectivity + INDEPENDENT short-word scan (NOT `validate_all`)
`validate_all` (`validator.py:20-49`) runs FOUR checks — symmetry (`:32-34`), connectivity (`:36-38`), min-word-length (`:40-42`, **dead** — see below), black%>17% (`:44-47`). Symmetry is a user toggle (would force `valid:false` on intentionally-asymmetric grids); black% overlaps this handler's existing `suggestions` (`:242-243`, >20%, conflicting). So compose a narrower method. **Do NOT reuse `_check_minimum_word_length`** — it's dead code: `get_word_slots()` pre-filters `length>=3` in both loops (`grid.py:213`, `:242`), so `<3` slots never reach it (corroborated `test_validator.py:116-119`). Deliver short-word via a run-length check (owner decision) — but do NOT hand-roll a SECOND run-walker: an independent walker drifts from `get_word_slots` at edges (isolated single cells, border runs), so the SAME grid gets described inconsistently by numbering vs. violations (the frontend already reuses `allSlots` for exactly this reason). **Factor the run-boundary walk into a shared enumerator both consume:** add `Grid.enumerate_white_runs() -> list[(cells, length, direction)]` (the run logic currently inline in `get_word_slots`, `grid.py:200-245`, WITHOUT the `>=3` filter); refactor `get_word_slots` to `filter(length>=3)` over it — output byte-identical, add a regression test asserting `get_word_slots` is unchanged — and `_scan_short_words` to `filter(1<=length<=2)` over it. DRY + `get_word_slots`'s public output unchanged (low blast radius, honoring the owner's "no-blast-radius" intent).
```python
# cli/src/core/validator.py
@staticmethod
def validate_structural(grid: Grid) -> Tuple[bool, List[str]]:
    """Connectivity + short-word(<3) only. Excludes symmetry + black% (owned elsewhere).
    Uses _scan_short_words (fresh run-length walk), NOT the dead _check_minimum_word_length."""
    errors = []
    if not GridValidator._check_connectivity(grid):
        errors.append("Grid has isolated white square regions")
    errors.extend(GridValidator._scan_short_words(grid))
    return (len(errors) == 0, errors)

@staticmethod
def _scan_short_words(grid: Grid) -> List[str]:
    """White runs of length 1-2 (across + down). Consumes Grid.enumerate_white_runs()
    (SHARED with get_word_slots — no independent walker), filters 1<=length<=2.
    Returns human strings, e.g. '2-letter across word at (r,c)'."""
    # implementer: [f"{n}-letter {d} word at ({r},{c})" for (cells, n, d) in grid.enumerate_white_runs()
    #               if 1 <= n <= 2 for (r, c) in [cells[0]]]  — signature above is the contract.
```
"Unchecked squares" (stub's 3rd reserved check) remains OUT OF SCOPE (M2).

### DD3 — Merge shape (D1:C)
`warnings = validation.get("warnings", []) + structural_errors`; `valid = validation["valid"] and structural_valid`; HTTP 200 preserved.
**`valid`-flip is safe (verified 2026-07-13):** no consumer reads the response `valid` today — `api.validateGrid` has zero callers, App's `validateGrid` refs are the local stub (`:235`), grep found no `.valid` reader. `valid` now goes false on most mid-construction grids (transient short runs/disconnection) and feeds only the advisory `violations` list. If a FUTURE task gates on `valid` (export/save/banner), revisit this AND-tightening.

### TDD Steps
- [ ] **Step 1 (CLI, `cli/tests/unit/test_validator.py`) — add `import pytest` if missing; failing tests:**
```python
class TestValidateStructural:
    def test_isolated_region_reported(self):
        grid = Grid(11)
        for col in range(11):
            grid.set_black_square(5, col, enforce_symmetry=False)
        ok, errors = GridValidator.validate_structural(grid)
        assert ok is False and any("isolated" in e.lower() for e in errors)

    def test_clean_grid_passes(self):
        ok, errors = GridValidator.validate_structural(Grid(11))
        assert ok is True and errors == []

    def test_short_word_reported(self):   # now REAL (not xfail) — _scan_short_words bypasses the filter
        grid = Grid(11)
        grid.set_black_square(0, 2, enforce_symmetry=False)
        grid.set_black_square(0, 3, enforce_symmetry=False)   # 2-letter across run at (0,0)-(0,1)
        ok, errors = GridValidator.validate_structural(grid)
        assert ok is False and any("2" in e and "across" in e.lower() for e in errors)
```
Run: `pytest cli/tests/unit/test_validator.py -k ValidateStructural -v` → fails.
- [ ] **Step 2:** implement `validate_structural` + `_scan_short_words` (signatures above). Run → all pass.
- [ ] **Step 3 (backend, `backend/tests/unit/test_grid_routes.py`) — failing test** (client fixture per `test_constraint_routes.py:10-14`):
```python
def test_validate_merges_structural_errors(client):
    grid = [["." for _ in range(11)] for _ in range(11)]
    for col in range(11):
        grid[5][col] = "#"
    resp = client.post("/api/grid/validate", json={"grid": grid, "grid_size": 11})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["valid"] is False and any("isolated" in w.lower() for w in data["warnings"])

def test_validate_clean_grid_unaffected(client):
    grid = [["." for _ in range(11)] for _ in range(11)]
    resp = client.post("/api/grid/validate", json={"grid": grid, "grid_size": 11})
    assert resp.status_code == 200 and resp.get_json()["valid"] is True
```
Run → fails.
- [ ] **Step 4:** extend `validate_grid` (`grid_routes.py:208-258`): build `Grid.from_dict({"grid": grid, "size": grid_size}, strict_size=False)` in the try/except guard, call `validate_structural`, merge per DD3.
- [ ] **Step 5:** green (`pytest backend/tests/unit/test_grid_routes.py cli/tests/unit/test_validator.py -v`). Commit: `feat(api): extend /api/grid/validate with structural checks (F2)`

---

## Task B — Frontend: pure `localNumber` extraction

### Files
- Create: `src/hooks/useNumbering.js` (pure exports only), `src/hooks/__tests__/useNumbering.test.jsx`

### Interfaces
```
localNumber(grid) -> { grid, numbering: {"row,col": number} }   // .numbering exists for Task B standalone tests;
                                                                 // Task C derives its exposed map via numberingMapFromGrid
numberingMapFromGrid(grid) -> {"row,col": number}
structuralSigOf(size, grid) -> string|null
```
- Consumes `allSlots` (`useGridGeometry.js:82-103`). All pure/immutable (no input mutation) — mirrors `applyNumbering`.

### DD — reuse `allSlots`, don't reimplement start predicates
Legacy `isStartOfAcrossWord` (`App.jsx:153-159`) ≡ `allSlots` start condition (`useGridGeometry.js:92-98`, both directions, both exclude length-1). `localNumber` builds a `Set` of `"r,c"` start-keys from `allSlots(grid).across`/`.down` (each `slot.cells[0]`), then one row-major pass numbering cells in that set → guaranteed agreement with `slotAt(...).number`.
```js
export function localNumber(grid) {
  const { across, down } = allSlots(grid);
  const starts = new Set();
  for (const s of [...across, ...down]) { const [r, c] = s.cells[0]; starts.add(`${r},${c}`); }
  // row-major pass: assign sequential numbers where starts.has(`${r},${c}`); return { grid: <new>, numbering }
}
```

### TDD Steps
- [ ] **Step 1 — failing test.** NOTE: `gridFromRows` in `useGridGeometry.test.jsx:12-23` is a NON-exported local — duplicate the ~12-line helper into `useNumbering.test.jsx` (or extract to a shared fixture); do NOT `import` it.
```js
describe('localNumber', () => {
  it('does not mutate its input', () => {
    const grid = gridFromRows(['AB#C.', '.....', '#....', '.....', '.....']);
    const snap = JSON.stringify(grid); localNumber(grid);
    expect(JSON.stringify(grid)).toBe(snap);
  });
  it('numbers match the legacy algorithm on a sample 5x5', () => {
    const { numbering } = localNumber(gridFromRows(['.....', '.#...', '.....', '...#.', '.....']));
    expect(numbering['0,0']).toBe(1); // + full expected map
  });
  it('agrees with allSlots on every start cell', () => {
    const { numbering } = localNumber(gridWithBlackSquares);
    for (const s of [...allSlots(gridWithBlackSquares).across, ...allSlots(gridWithBlackSquares).down]) {
      const [r,c]=s.cells[0]; expect(numbering[`${r},${c}`]).toBeDefined();
    }
  });
});
```
Run → fails (module missing).
- [ ] **Step 2:** implement `localNumber`, `numberingMapFromGrid` (`Object.fromEntries` over `.number`), `structuralSigOf` (mirrors `contentSigOf` App.jsx:31-36 but size + `isBlack`-only per cell).
- [ ] **Step 3:** green. Commit: `refactor(ui): extract pure localNumber from App's client-side numbering`

---

## Task C — Frontend: `useNumbering` hook

### Files
- Modify: `src/hooks/useNumbering.js`, `src/hooks/__tests__/useNumbering.test.jsx`

### Interfaces
```
useNumbering({ grid, gridSize, setGrid, pushToast }) -> { numbering, violations, unverified }
```
- Consumes `api.numberGrid` (`client.js:120-122`), `api.validateGrid` (`:124-126`, JS shape `{grid, gridSize}`→wire `grid_size`), `toCliStrings`/`applyNumbering`, `useToasts` `pushToast({kind,message})` (`Toast.jsx:87-89`).

### DD1 — Reactive structural-signature diffing
`useEffect` keyed on memoized `structuralSig = structuralSigOf(gridSize, grid)`. Every `validate_structural` check + numbering depend only on `(size, isBlack)`, never `.letter` → letter edits leave the sig unchanged (silent); black-toggle/resize/import change it (fires). Non-adaptive autofill re-touches `.isBlack` with identical values → sig byte-identical → no fire. **Adaptive autofill (owner decision): allowed to fire** — adding black squares is a genuine structural change; renumber+revalidate is correct. No bypass. ⚠️ Safe NOW only because the SSE fill consumer is unbuilt (Task 11): during an adaptive fill the SSE loop's `setGrid` and this hook's reconcile `setGrid` become two async writers to `grid` — `gridRef` protects letters from the numbering write, but NOT the fill loop's writes from interleaving. This is a deferred two-writer race, not a resolved one. **Task-11 flag:** verify `useNumbering` doesn't race the fill loop; likely suspend the hook during an active fill.

### DD2 — Write-back: hook takes `setGrid`, returns `{numbering, violations, unverified}`
`CrosswordGrid` renders `cell.number` off `grid` (`CrosswordGrid.jsx:391-396`); letter edits copy-forward `.number` (`setLetter` App.jsx:209-211). Numbers must be baked into cells; hook writes via injected `setGrid`.

### DD3 — `numbering` stays unparenthesized `"row,col"`
`ExportPanel.jsx:80` / `App.jsx:575-576` (import `split(',')`) require `"row,col"`; `applyNumbering` requires `"(r,c)"` (`gridCodec.js:58`; CLI emits paren keys at `cli.py:969`). Decision: `applyNumbering` used ONLY internally (paren keys never leave the hook); expose `numbering` via `numberingMapFromGrid` (grid→map) — one canonical direction; Export/Import unchanged.

### Concurrency contract (implementer writes the handlers)
Fire both calls under one `token = ++tokenRef.current`; a `gridRef` updated every render (`gridRef.current = grid`) is read at resolution so a mid-flight keystroke survives (applyNumbering rewrites only `.number`). Each branch first guards `if (token !== tokenRef.current) return;`.

| call | on resolve | on reject |
|---|---|---|
| `numberGrid({size, grid: toCliStrings(local)})` | `applyNumbering(gridRef.current, resp.numbering)` → `setGrid` → derive `numbering` → `unverified=false` | `unverified=true` + error toast (keep optimistic numbers) |
| `validateGrid({grid: toCliStrings(local), gridSize})` | `violations = [...(warnings||[]), ...(suggestions||[])]` | error toast |

`unverified` tracks the numbering call only (independent `.then`s, NOT `Promise.all`).

### TDD Steps (conventions: `useHealth.test.jsx:9-21`, `useSaveMachine.test.jsx` — fake timers + `vi.spyOn(api,...)`; deferred-promise helper `const d=()=>{let r;const p=new Promise(res=>r=res);return{p,r}}`)
- [ ] **Step 1 — failing tests (all seven):**
  1. **instant paint + debounce:** structural rerender → assert `setGrid` called SYNCHRONOUSLY with optimistic numbers AND `api.numberGrid`/`api.validateGrid` `not.toHaveBeenCalled()` before advancing; after `advanceTimersByTimeAsync(150)` both called once.
  2. **server-wins (concrete):** mock `numberGrid` resolve with numbering DIFFERING from the optimistic pass; assert final grid/`numbering` reflects the SERVER values, not optimistic.
  3. **out-of-order discard (deferred promises):** two structural edits; `numberGrid` returns `d1.p` then `d2.p`; call `d2.r(second)` BEFORE `d1.r(first)`; assert final numbering == second. Assert this FAILS if the token guard is removed (guard is load-bearing).
  4. **mid-flight keystroke survives reconcile:** structural edit with a delayed `numberGrid`; before it resolves, simulate a letter-only `setGrid`/rerender (no token bump); resolve; assert the typed letter is present in the reconciled grid.
  5. **letter typing fires neither:** letter-only rerender; advance 150ms; both `api.*` `not.toHaveBeenCalled()`.
  6. **debounce coalesces:** N rapid structural edits within 150ms → exactly ONE `numberGrid` call.
  7. **failure path:** `numberGrid` rejects → `unverified===true`, grid numbers UNCHANGED from the optimistic pass, `pushToast` called `{kind:'error'}`.
Run → fails.
- [ ] **Step 2:** implement `useNumbering` (DD1-3 + concurrency contract). Full body by implementer.
- [ ] **Step 3:** green. Commit: `feat(ui): useNumbering hook — server-reconciled numbering + validation (F2)`

---

## Task D — App wiring + ToolRail violations prop + test cleanup

### Files
- Modify: `src/App.jsx`, `src/components/bench/ToolRail.jsx:86-131`, `src/components/bench/__tests__/ToolRail.test.jsx`

### Interfaces
- Consumes `useNumbering` (Task C). Produces `<ToolRail ... violations={string[]} unverified={boolean} />` (additive).

### App.jsx changes
**Remove:** `updateNumbering` (`:126-151`), `isStartOfAcrossWord` (`:153-159`), `isStartOfDownWord` (`:161-167`); `numbering` state + setters (`:42`,`:150`,`:573`); `validateGrid` stub (`:235-244`) + `setValidationErrors` (`:47`) — **removal, not revival** (violations are server-sourced); structural + letter call sites (`:120`,`:186-187`,`:583`,`:587`,`:212`,`:266`); the "reuse imported numbering" branch (`:571-584`) → `setGrid(importedGrid)`; `handleThemeWordApplied`'s `updateNumbering` (`:550`, redundant).
**Add:** `const { numbering, violations, unverified } = useNumbering({ grid, gridSize, setGrid, pushToast });` near the other hooks (`:73,85`). **Keep** `doc` (`:81-84`) reading `numbering` (now from hook). **ToolRail** (`:658`): add `violations={violations} unverified={unverified}`.

⚠️ **Import-clobber interaction (pre-existing, trust-ledger §D):** `handleGridImport` sets size then grid; the `[gridSize]` effect (`App.jsx:97-99`) re-runs `initializeGrid` and clobbers the imported grid on size-changing imports. Verify the `setGrid(importedGrid)` simplification against this; do NOT assume it survives a size change. Not fixed here (Task 12).

### ToolRail.jsx changes (`:86-131`)
Add `violations=[]`, `unverified=false` to destructured props; render a VIOLATIONS section under the GRID block (`:127-131`) only when `violations.length>0` (label + `unverified` suffix + `.xw-rail-violation` rows). No JSX shown — implement per the `.xw-rail-*` conventions in that file.

### Test cleanup + new tests
`ToolRail.test.jsx:36-41` (standalone Autofill `onSelectTool`) duplicates one iteration of the `forEach` at `:43-50` — delete it. Add 3 tests: renders violations when present; nothing extra when empty; `(unverified)` label when true.

### TDD Steps
- [ ] **Step 1:** write the 3 ToolRail violations tests (fail) + delete the duplicate.
- [ ] **Step 2:** implement ToolRail props/section.
- [ ] **Step 3:** wire `useNumbering` into App.jsx; remove all legacy code above. **Manual smoke (no App test file exists):** `npm run dev`, then — (a) toggle a black square → clue numbers update immediately (optimistic), and after ~150-300ms don't flicker/shift (reconcile agrees); (b) type a letter → numbers do NOT change; (c) resize/new grid → renumbers; (d) **import a grid of a DIFFERENT size** → confirm the imported cells survive (exercises the import-clobber risk above) and renumber; (e) with an isolated region or 2-letter word present → the ToolRail VIOLATIONS section shows the strings.
- [ ] **Step 4:** `npx vitest run` green. Commit: `feat(ui): wire server-authoritative numbering into App + ToolRail violations (F2)`

---

## Self-Review (coverage + deviations from parent plan)
Coverage vs Task 8 (`2026-07-12-...:446-457`): files, interfaces (numberGrid/validateGrid/applyNumbering/useGridGeometry/localNumber/debounce/token), Step-1 TDD list, Step-2 legacy removal + latency deviation — all mapped. **Reasoned deviations from the literal parent plan:** (1) `validate_structural` (narrower) instead of `validate_all` (excludes symmetry/black%); (2) short-word via a fresh `_scan_short_words` (parent didn't foresee `_check_minimum_word_length` is dead); (3) violations rendered in a new VIOLATIONS section rather than the literal "stats block" (`:453`); (4) `localNumber` reuses `allSlots` instead of porting the bundle `numberGrid` helper (`:453`) — equivalent + avoids a 3rd copy; (5) 4 TDD commits vs 1 (squash at merge); (6) latency `~120-180ms`.

## Follow-ups (logged, not done here)
- `handle_error(...default_status=)` bug at `grid_routes.py:121-123,180-182,260-262` vs `errors.py:10` — see trust-ledger §E ticket.
- **[Task 11]** `useNumbering` two-writer race with the autofill SSE loop (both call `setGrid` during adaptive fill) — verify no interleave corruption; likely suspend the hook during an active fill. Also decide whether to MUTE violations during a fill (Global Constraint 7).
- **[M2]** `_check_minimum_word_length` (`validator.py:107-124`) stays dead after this task; a future task can repoint it at the new `Grid.enumerate_white_runs()` so there is ONE min-word-length source of truth.

## REVIEW RESULTS (2026-07-13, two specialized reviewers)
**Correctness (adversarial, primary-source):** ALL 10 decision-driving claims CONFIRMED, no refutations (dead-code, `validate_all` 4-check scope, `validate_structural` feasibility, numbering format collision incl. `cli.py:969`, `handle_error` bug isolated to `grid_routes.py`, input-contract safety, `Grid.from_dict(strict_size)`, all test APIs, import-clobber, `allSlots` equivalence). Mechanical fixes folded in: `import pytest` (Task A Step 1), `gridFromRows` duplicate-not-import (Task B Step 1).
**Quality:** READY-AFTER-FIXES → fixes APPLIED: Task C 3 Criticals (mid-flight keystroke test, deferred-promise out-of-order, instant-paint assertion) + server-wins concrete test + failure "optimistic kept" assertion; Task D concrete smoke steps incl. import-clobber; open questions resolved into "Decisions applied"; convention trims (Task C → contract table); self-review deviations listed; latency aligned.
**Advisor integration-hardening (post-decision):** (1) `valid`-flip verified consumer-free — safe (DD3); (2) `_scan_short_words` no longer a parallel run-walker — shares `Grid.enumerate_white_runs()` with `get_word_slots` to prevent edge-drift (DD2); (3) violations flagged as advisory+live, Task D smoke confirms not-"broken" (Global Constraint 7); (4) adaptive-fire documented as a DEFERRED two-writer race, safe only because Task 11 SSE is unbuilt (Task C DD1 + Follow-ups); (5) Task A guard widened to `except Exception` since the outer error net is broken (DD1).

## FILE:LINE VERIFICATION (architect + correctness reviewer)
All prompt-supplied citations re-verified vs HEAD `116bda5`, no drift. Independently confirmed new citations: `validate_all` 4-check scope (`validator.py:20-49`), `get_word_slots` filter (`grid.py:213,242`), numbering key-format (`ExportPanel.jsx:80`,`App.jsx:575-576`,`cli.py:969`), `handle_error` mismatch (`errors.py:10`), `Grid.from_dict` (`grid.py:279`), test APIs (`Grid(11)`,`set_black_square:49`,`allSlots:82-103`), import-clobber (`App.jsx:97-99,555-595`), absence of `test_grid_routes.py`/`App*.test.jsx`.
