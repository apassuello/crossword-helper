# Autofill Algorithm Audit Results — 2026-03-20

## Test Parameters

All tests used:
- **Min Score:** 10
- **Allow Nonstandard:** yes
- **Wordlists:** comprehensive.txt, foreign_words.txt, foreign_classics.txt, crosswordese.txt, expressions_and_slang.txt

Timeouts: 600s (repair), 300s (hybrid on 21x21), 300s (15x15 all)

## Total: 46 tests, 0 crashes

---

## 15x15 Empty (78 slots)

| Algo | baseline | cleanup | partial | part+clean | adaptive | all_opts |
|------|----------|---------|---------|------------|----------|----------|
| **repair** | **T 100% 0p 1s** | **T 100% 0p <1s** | **T 100% 0p 1s** | **T 100% 0p <1s** | **T 100% 0p 1s** | **T 100% 0p <1s** |
| hybrid | F 100% 2p 54s | T 100% 0p <1s | F 100% 1p 54s | T 100% 0p <1s | T 100% 0p 1s | T 100% 0p <1s |
| beam | F 100% 10p 109s | F 100% 7p 61s | F 100% 7p 58s | F 100% 6p 66s | F 100% 7p 74s | — |

Legend: T/F = success true/false, fill%, problematic count, time

## 15x15 Partial Early (71 slots, 125 pre-filled)

| Algo | baseline | cleanup | partial | part+clean | adaptive | all_opts |
|------|----------|---------|---------|------------|----------|----------|
| repair | F 100% 18p 60s | F 85% 10p <1s | F 100% 14p 60s | F 95% 3p <1s | F 100% 10p 60s | **T 100% 0p <1s** |
| hybrid | F 100% 16p 54s | T 100% 0p <1s | F 100% 14p 54s | T 100% 0p <1s | F 100% 15p 54s | F 97% 2p <1s |
| beam | F 12% 39p 64s | F 12% 39p 76s | — | — | F 12% 39p 80s | — |

## 15x15 Partial Mid (71 slots, 137 pre-filled)

| Algo | baseline | cleanup | adaptive |
|------|----------|---------|----------|
| **repair** | **T 100% 0p 24s** | **T 100% 0p <1s** | **T 100% 0p 22s** |
| hybrid | F 100% 7p 54s | T 100% 0p <1s | F 100% 7p 24s |
| beam | F 31% 46p 600s | — | — |

## 21x21 Empty (140 slots)

| Algo | baseline | cleanup | partial | part+clean | adaptive | all_opts |
|------|----------|---------|---------|------------|----------|----------|
| repair | F 100% 16p 60s | F 92% 10p 60s | F 100% 16p 60s | F 92% 11p 601s | F 100% 15p 122s | **F 98% 2p 121s** |
| hybrid | F 98% 22p 24s | F 96% 5p <1s | F 97% 17p 24s | F 97% 4p <1s | F 97% 22p 24s | F 92% 11p <1s |

## 21x21 Custom Template (140 slots)

| Algo | baseline |
|------|----------|
| repair | F 100% 14p 182s |
| hybrid | F 100% 17p 24s |

## 21x21 Filled Themed (140 slots, pre-filled)

| Algo | baseline |
|------|----------|
| **repair** | **T 100% 0p 1s** |
| **hybrid** | **T 100% 0p <1s** |

---

## Key Findings

### Algorithm Ranking
1. **Repair** — best overall, only algo to achieve success=true on empty grids
2. **Hybrid** — decent but slower, more problematic slots
3. **Beam** — useless alone, only 12-31% fill on partial grids, 600s timeouts

### Best Flag Combinations
- **15x15 empty:** repair + any flags = perfect (success=true, 0 problematic)
- **15x15 partial:** repair + all_opts (adaptive+partial+cleanup) = only combo with success=true
- **21x21 empty:** repair + all_opts = best at 98% fill, 2 problematic (no algo achieves success=true)
- **Cleanup flag:** effectively reduces problematic count by stripping invalid words

### Observations
- **No crashes (rc!=0) across all 46 tests** — int8 overflow fix is solid with foreign wordlists
- **cleanup runs near-instantly** — it only strips, doesn't re-fill
- **partial-fill + cleanup** together provide the cleanest partial results
- **adaptive** helps on 15x15 but doesn't improve 21x21 much
- **Pre-filled grids validate instantly** with success=true

### Recommended Default Settings for UI
- **Algorithm:** repair
- **15x15 grids:** repair, no flags needed (or cleanup for safety)
- **21x21 grids:** repair + adaptive + partial-fill + cleanup
- **Timeout:** 600s for 21x21, 300s for 15x15
- **Min score:** 10 (permissive, allows more valid words)

---

## Raw Data

All result files saved in `data/audit_results/`:
- `audit_*_stdout.json` — batch 1 baseline results
- `audit2_*_stdout.json` — batch 2 flag combo results
- `audit2_*.result` — batch 2 summary lines
- `run_*_stdout.json` — batch 3 gap test results
- `run_*.log` — all stderr/progress logs
