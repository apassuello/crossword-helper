/**
 * useNumbering — server-authoritative numbering + validation (Task 8B pure
 * helpers + Task 8C hook).
 *
 * The PURE building blocks (Task 8B): `localNumber` is the optimistic
 * client-side pass fired immediately on a structural edit for instant paint,
 * before the server's `/api/number` response (always wins on reconcile — see
 * gridCodec.applyNumbering) lands. `numberingMapFromGrid` derives the exposed
 * `"row,col"` map; `structuralSigOf` is the change detector.
 *
 * The HOOK (Task 8C): `useNumbering` wraps those helpers, detecting structural
 * changes via `structuralSigOf` and driving the optimistic → server-reconcile
 * flow under a shared request token with a 150ms debounce.
 *
 * The pure functions here are immutable (no input mutation), mirroring
 * gridCodec.applyNumbering's contract.
 *
 * Cell shape (frontend canonical): { letter, isBlack, number, isError, isThemeLocked, ... }
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api/client';
import { toCliStrings, applyNumbering } from '../api/gridCodec';
import { allSlots } from './useGridGeometry';

/**
 * Optimistic client-side numbering pass. Builds the set of word-start cells
 * from `allSlots` (across/down slot[0].cells[0]) rather than reimplementing
 * the legacy isStartOfAcrossWord/isStartOfDownWord predicates — this
 * guarantees the numbering agrees with `slotAt(...).number` by construction.
 *
 * Immutable: returns a brand-new grid (new rows, new cell objects); the
 * input `grid` is never mutated.
 *
 * @param {object[][]} grid
 * @returns {{ grid: object[][], numbering: Record<string, number> }}
 *   `numbering` keys are unparenthesized "row,col" strings (see plan Global
 *   Constraint 6 — NOT the server's "(r,c)" form).
 */
export function localNumber(grid) {
  const { across, down } = allSlots(grid);
  const starts = new Set();
  for (const s of [...across, ...down]) {
    const [r, c] = s.cells[0];
    starts.add(`${r},${c}`);
  }

  const numbering = {};
  let currentNumber = 1;

  const newGrid = grid.map((row, r) =>
    row.map((cell, c) => {
      const key = `${r},${c}`;
      if (starts.has(key)) {
        const n = currentNumber++;
        numbering[key] = n;
        return { ...cell, number: n };
      }
      return { ...cell, number: null };
    })
  );

  return { grid: newGrid, numbering };
}

/**
 * Extract a `{"row,col": number}` numbering map from a grid's `.number`
 * fields (e.g. after the server's `/api/number` response has been applied
 * via gridCodec.applyNumbering). Cells with no number are omitted.
 *
 * @param {object[][]} grid
 * @returns {Record<string, number>}
 */
export function numberingMapFromGrid(grid) {
  return Object.fromEntries(
    grid.flatMap((row, r) =>
      row.flatMap((cell, c) =>
        cell.number != null ? [[`${r},${c}`, cell.number]] : []
      )
    )
  );
}

/**
 * Structural signature of a grid: size + isBlack layout ONLY. Mirrors
 * App's `contentSigOf` shape but deliberately excludes `.letter` and every
 * derived field (`.number`, `.isError`, `.isThemeLocked`, ...) — renumbering
 * must fire on black-square/size changes only, never on letter edits
 * (plan Global Constraint 3).
 *
 * @param {number} size
 * @param {object[][]|null} grid
 * @returns {string|null}
 */
export function structuralSigOf(size, grid) {
  if (!grid) return null;
  return JSON.stringify({
    size,
    cells: grid.map((row) => row.map((c) => c.isBlack)),
  });
}

const DEBOUNCE_MS = 150;

/**
 * useNumbering — the Task 8C hook. Server-authoritative numbering + validation,
 * layered on the pure helpers above (plan Task 8/F2, DD1–DD3 + concurrency
 * contract).
 *
 * On every STRUCTURAL grid edit (size or isBlack layout change — never a letter
 * edit; see structuralSigOf / plan Global Constraint 3):
 *   1. Optimistic paint — `localNumber(grid)` → `setGrid` SYNCHRONOUSLY +
 *      `unverified=true`, for instant display before any round-trip (DD2).
 *   2. After a 150ms debounce, fire `/api/number` and `/api/grid/validate`
 *      together under ONE shared request token (`++tokenRef.current`). Rapid
 *      edits within the window coalesce to a single call pair.
 *   3. Each async branch first guards `if (token !== tokenRef.current) return;`
 *      so an out-of-order/stale resolution can neither reconcile nor toast.
 *
 * `gridRef.current` is refreshed every render and read at resolution time, so a
 * letter typed mid-flight survives the reconcile (applyNumbering rewrites only
 * `.number`, plan Global Constraint 2 — server wins on numbers). The paren-key
 * `applyNumbering` stays internal; `numbering` is exposed as the unparenthesized
 * `"row,col"` map via `numberingMapFromGrid` (DD3).
 *
 * `unverified` tracks the numbering call ONLY (independent `.then`s, never
 * Promise.all): a numbering rejection keeps the optimistic numbers, flips
 * `unverified` true and toasts; a validation resolution surfaces
 * `violations = [...warnings, ...suggestions]`.
 *
 * @param {{grid: object[][]|null, gridSize: number, setGrid: (g: object[][]) => void, pushToast: (t: {kind: string, message: string}) => void}} params
 * @returns {{numbering: Record<string, number>, violations: string[], unverified: boolean}}
 */
export function useNumbering({ grid, gridSize, setGrid, pushToast }) {
  const [numbering, setNumbering] = useState({});
  const [violations, setViolations] = useState([]);
  const [unverified, setUnverified] = useState(false);

  // Latest grid, read at resolution time so a mid-flight letter edit survives.
  const gridRef = useRef(grid);
  gridRef.current = grid;

  // Monotonic request token — the newest structural edit always wins.
  const tokenRef = useRef(0);

  const sig = useMemo(() => structuralSigOf(gridSize, grid), [gridSize, grid]);

  useEffect(() => {
    // Null sig = empty/initial grid: nothing to number, do not fire.
    if (sig === null) return undefined;

    // Bump the token PER EDIT (not at fire time): a later structural edit must
    // invalidate an already-in-flight prior call even when that prior timer has
    // ALREADY fired (its cleanup no-ops). Bumping inside the setTimeout would
    // leave tokenRef stale until timer2 fires, letting call1 wrongly reconcile
    // onto grid2 and falsely clear `unverified`. Newest edit always wins.
    const token = ++tokenRef.current;

    // 1. Optimistic paint — synchronous, before the debounce or any request.
    setGrid(localNumber(gridRef.current).grid);
    setUnverified(true);

    // 2. Debounced server reconcile + validation. The cleanup-clear coalesces
    //    rapid structural edits into a single fire; the captured `token` guards
    //    each async branch against a superseding edit.
    const handle = setTimeout(() => {
      const cliGrid = toCliStrings(gridRef.current);

      // Numbering — server wins; tracks `unverified`.
      api.numberGrid({ size: gridSize, grid: cliGrid }).then(
        (resp) => {
          if (token !== tokenRef.current) return;
          const reconciled = applyNumbering(gridRef.current, resp.numbering || {});
          setGrid(reconciled);
          setNumbering(numberingMapFromGrid(reconciled));
          setUnverified(false);
        },
        () => {
          if (token !== tokenRef.current) return;
          setUnverified(true); // keep the optimistic numbers on-screen
          pushToast({ kind: 'error', message: 'Renumbering failed — showing local numbers.' });
        }
      );

      // Validation — independent; surfaces advisory violations.
      api.validateGrid({ grid: cliGrid, gridSize }).then(
        (resp) => {
          if (token !== tokenRef.current) return;
          setViolations([...(resp.warnings || []), ...(resp.suggestions || [])]);
        },
        () => {
          if (token !== tokenRef.current) return;
          pushToast({ kind: 'error', message: 'Grid validation failed.' });
        }
      );
    }, DEBOUNCE_MS);

    return () => clearTimeout(handle);
    // Fires ONLY on structural-signature change; grid/gridSize/setGrid/pushToast
    // are read via ref or are stable — see the concurrency contract above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sig]);

  return { numbering, violations, unverified };
}

export default useNumbering;
