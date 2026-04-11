# Autofill Algorithm Audit Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Systematically test all 3 autofill algorithms (repair, hybrid, beam) across 15x15 and 21x21 grids (empty + partial), with all flag combinations, using foreign wordlists that trigger the int8 overflow bug — to verify stability and correctness.

**Architecture:** Each test = one CLI subprocess call. Agent per batch runs tests in parallel, logs results to a shared report file.

**Tech Stack:** Python CLI (`python -m cli.src.cli fill`), bash

---

## Test Matrix

### Grids (6 total)

| ID | File | Size | State |
|----|------|------|-------|
| G1 | `example_15x15.json` | 15x15 | Empty (189 cells) |
| G2 | `example_15x15_partial_early.json` | 15x15 | Partial (125/189 filled) |
| G3 | `example_15x15_partial_mid.json` | 15x15 | Partial (137/192 filled) |
| G4 | `example_21x21.json` | 21x21 | Empty (369 cells) |
| G5 | `example_21x21_template_custom.json` | 21x21 | Empty (363 cells) |
| G6 | `example_21x21_filled_themed.json` | 21x21 | Fully filled (363/363) — tests re-fill behavior |

### Algorithms (3)

| ID | Flag |
|----|------|
| A1 | `--algorithm repair` |
| A2 | `--algorithm hybrid` |
| A3 | `--algorithm beam` |

### Option Combinations (6)

| ID | Flags | Description |
|----|-------|-------------|
| O1 | _(none)_ | Baseline — no extras |
| O2 | `--cleanup` | Post-fill cleanup only |
| O3 | `--partial-fill` | Partial fill only |
| O4 | `--partial-fill --cleanup` | Partial fill + cleanup |
| O5 | `--adaptive` | Adaptive black squares only |
| O6 | `--adaptive --partial-fill --cleanup` | All options combined |

### Common Parameters

```
--timeout 600
--min-score 10
--json-output
--allow-nonstandard
--wordlists data/wordlists/comprehensive.txt
--wordlists data/wordlists/themed/foreign_words.txt
--wordlists data/wordlists/themed/foreign_classics.txt
--wordlists data/wordlists/core/crosswordese.txt
--wordlists data/wordlists/themed/expressions_and_slang.txt
```

### Full Matrix

6 grids × 3 algorithms × 6 option combos = **108 test runs**

That's too many for 10-min timeouts. Prioritize:

**Priority 1 — Must run (18 tests):** All grids × all algorithms × baseline (O1)
**Priority 2 — Flag coverage (18 tests):** G1 + G2 + G4 × all algorithms × O2-O4
**Priority 3 — Adaptive (9 tests):** G1 + G2 + G4 × all algorithms × O5
**Priority 4 — Kitchen sink (9 tests):** G1 + G2 + G4 × all algorithms × O6

**Total: 54 tests** (manageable with parallelism and shorter timeouts for partial grids)

---

## Execution

### Task 1: Create Test Runner Script

**Files:**
- Create: `scripts/audit_autofill.sh`

**Step 1: Write the script**

```bash
#!/usr/bin/env bash
# Autofill algorithm audit runner
# Usage: ./scripts/audit_autofill.sh

set -euo pipefail

GRIDS_DIR="data/grids"
RESULTS_DIR="/tmp/autofill_audit_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

WORDLISTS=(
  "--wordlists data/wordlists/comprehensive.txt"
  "--wordlists data/wordlists/themed/foreign_words.txt"
  "--wordlists data/wordlists/themed/foreign_classics.txt"
  "--wordlists data/wordlists/core/crosswordese.txt"
  "--wordlists data/wordlists/themed/expressions_and_slang.txt"
)
WL="${WORDLISTS[*]}"

COMMON="--timeout 600 --min-score 10 --json-output --allow-nonstandard $WL"

run_test() {
  local grid="$1"
  local algo="$2"
  local opts="$3"
  local label="$4"
  local grid_base=$(basename "$grid" .json)
  local outfile="$RESULTS_DIR/${grid_base}__${algo}__${label}.json"
  local logfile="$RESULTS_DIR/${grid_base}__${algo}__${label}.log"

  echo "[$label] Running: $grid_base / $algo / $opts"
  local start_time=$(date +%s)

  # Copy grid to temp to avoid overwriting
  local tmpgrid=$(mktemp /tmp/audit_grid_XXXXX.json)
  cp "$grid" "$tmpgrid"

  set +e
  python -m cli.src.cli fill "$tmpgrid" \
    --algorithm "$algo" \
    $opts \
    $COMMON \
    -o "$outfile" \
    2>"$logfile"
  local rc=$?
  set -e

  local end_time=$(date +%s)
  local elapsed=$((end_time - start_time))

  # Parse result
  local success="UNKNOWN"
  if [ $rc -eq 0 ] && [ -f "$outfile" ]; then
    success=$(python -c "
import json, sys
try:
    with open('$outfile') as f:
        d = json.load(f)
    s = d.get('success', False)
    filled = sum(1 for r in d.get('grid',[]) for c in r if c not in ('#','.',''))
    total = sum(1 for r in d.get('grid',[]) for c in r if c != '#')
    pct = int(100*filled/total) if total else 0
    print(f'{'OK' if s else 'PARTIAL'}|{filled}/{total}|{pct}%')
except: print('PARSE_ERROR')
" 2>/dev/null || echo "PARSE_ERROR")
  elif [ $rc -ne 0 ]; then
    success="CRASH(rc=$rc)"
    # Capture stderr snippet
    if [ -f "$logfile" ]; then
      head -5 "$logfile" >> "$RESULTS_DIR/crashes.log" 2>/dev/null
    fi
  fi

  rm -f "$tmpgrid"

  echo "${grid_base}|${algo}|${label}|${success}|${elapsed}s|rc=${rc}" >> "$RESULTS_DIR/summary.csv"
  echo "  → $success (${elapsed}s, rc=$rc)"
}

echo "=== Autofill Algorithm Audit ==="
echo "Results: $RESULTS_DIR"
echo ""

# --- BATCH 1: Priority 1 — Baseline (O1), all grids × all algorithms ---
echo "--- Batch 1: Baseline (no extra flags) ---"
for grid in \
  "$GRIDS_DIR/example_15x15.json" \
  "$GRIDS_DIR/example_15x15_partial_early.json" \
  "$GRIDS_DIR/example_15x15_partial_mid.json" \
  "$GRIDS_DIR/example_21x21.json" \
  "$GRIDS_DIR/example_21x21_template_custom.json" \
  "$GRIDS_DIR/example_21x21_filled_themed.json"; do
  for algo in repair hybrid beam; do
    run_test "$grid" "$algo" "" "baseline" &
  done
done
wait
echo ""

# --- BATCH 2: Priority 2 — cleanup/partial flags, subset of grids ---
echo "--- Batch 2: Flag combinations ---"
for grid in \
  "$GRIDS_DIR/example_15x15.json" \
  "$GRIDS_DIR/example_15x15_partial_early.json" \
  "$GRIDS_DIR/example_21x21.json"; do
  for algo in repair hybrid beam; do
    run_test "$grid" "$algo" "--cleanup" "cleanup" &
    run_test "$grid" "$algo" "--partial-fill" "partial" &
    run_test "$grid" "$algo" "--partial-fill --cleanup" "partial_cleanup" &
  done
done
wait
echo ""

# --- BATCH 3: Adaptive ---
echo "--- Batch 3: Adaptive ---"
for grid in \
  "$GRIDS_DIR/example_15x15.json" \
  "$GRIDS_DIR/example_15x15_partial_early.json" \
  "$GRIDS_DIR/example_21x21.json"; do
  for algo in repair hybrid beam; do
    run_test "$grid" "$algo" "--adaptive" "adaptive" &
  done
done
wait
echo ""

# --- BATCH 4: Kitchen sink ---
echo "--- Batch 4: All options ---"
for grid in \
  "$GRIDS_DIR/example_15x15.json" \
  "$GRIDS_DIR/example_15x15_partial_early.json" \
  "$GRIDS_DIR/example_21x21.json"; do
  for algo in repair hybrid beam; do
    run_test "$grid" "$algo" "--adaptive --partial-fill --cleanup" "all_opts" &
  done
done
wait

echo ""
echo "=== SUMMARY ==="
echo "Grid|Algorithm|Options|Result|Time|RC"
cat "$RESULTS_DIR/summary.csv" | sort
echo ""
echo "Results saved to: $RESULTS_DIR"

if [ -f "$RESULTS_DIR/crashes.log" ]; then
  echo ""
  echo "=== CRASHES ==="
  cat "$RESULTS_DIR/crashes.log"
fi
```

**Step 2: Make executable and run**

```bash
chmod +x scripts/audit_autofill.sh
./scripts/audit_autofill.sh
```

Note: This runs all 54 tests with parallelism within each batch. Each batch waits for all tests to complete before starting the next. Each test has a 10-min timeout. Total wall time depends on parallelism but should be ~20-40 minutes.

**Step 3: Review summary.csv**

Expected outcomes:
- **All tests:** rc=0 (no crashes — validates int8 fix)
- **Baseline on empty grids:** OK or PARTIAL with high fill %
- **Baseline on partial grids:** OK with higher fill % than input
- **Cleanup tests:** May show lower fill count (removed invalid words)
- **Partial fill tests:** May stop early with PARTIAL status
- **Beam on 21x21:** May timeout — beam is slow on large grids
- **Fully filled grid (G6):** Should return quickly with OK

Crash (rc≠0) on ANY test = regression or unfixed bug.

### Task 2: Analyze Results

**Step 1: Parse summary.csv into a readable report**

Group by:
1. **Crashes** — any rc≠0 → investigate logfile for stack trace
2. **Algorithm comparison** — for same grid+options, compare fill % and time across repair/hybrid/beam
3. **Flag impact** — for same grid+algorithm, compare baseline vs each flag combo
4. **Grid size impact** — 15x15 vs 21x21 fill rates and times

**Step 2: Save report to `docs/plans/autofill-audit-results.md`**

### Task 3: Fix Any Crashes Found

For each crash:
1. Read the `.log` file for the stack trace
2. Identify root cause (likely more int8 overflow locations, or algorithm bugs with specific flag combos)
3. Fix and re-run just that test to verify

### Task 4: Commit

```bash
git add scripts/audit_autofill.sh docs/plans/autofill-audit-results.md
# Plus any bug fixes
git commit -m "test(autofill): audit all algorithms across grid sizes and option combos"
```

---

## Key Risks

1. **Parallelism + memory:** Running 6-18 CLI processes simultaneously may exhaust RAM (each uses 100-500MB). If OOM, reduce parallelism to 3 at a time.
2. **Beam on 21x21:** Known to be very slow. May timeout at 600s. This is expected, not a bug.
3. **Adaptive + beam:** `--adaptive` may not be implemented for beam algorithm — could crash or be silently ignored.
4. **Partial fill + beam:** Same concern — flag may only apply to repair/hybrid.
5. **Cleanup + beam:** `--cleanup` requires iterative_repair engine — need to verify it works when primary algorithm is beam.
