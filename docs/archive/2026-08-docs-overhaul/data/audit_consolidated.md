# Autofill Audit Results — Fri Mar 20 15:10:51 CET 2026

## Parameters (all tests)
```
Timeout: 600s, Min Score: 10, Allow Nonstandard: yes
Wordlists: comprehensive.txt, foreign_words.txt, foreign_classics.txt, crosswordese.txt, expressions_and_slang.txt
```

## Batch 1: Baseline (no extra flags)
| Grid | Algo | success | Slots | Fill% | Problematic | Time |
|------|------|---------|-------|-------|-------------|------|
| 15x15_early_beam | | False | 5/39 | 12% | 39 | 64.1s |
| 15x15_early_hybrid | | False | 71/71 | 100% | 16 | 54.0s |
| 15x15_early_repair | | False | 71/71 | 100% | 18 | 60.0s |
| 15x15_empty_beam | | False | 78/78 | 100% | 10 | 108.5s |
| 15x15_empty_hybrid | | False | 78/78 | 100% | 2 | 54.1s |
| 15x15_empty_repair | | True | 78/78 | 100% | 0 | 1.2s |
| 15x15_mid_beam | | False | 15/48 | 31% | 46 | 600.7s |
| 15x15_mid_hybrid | | False | 71/71 | 100% | 7 | 54.0s |
| 15x15_mid_repair | | True | 71/71 | 100% | 0 | 23.6s |
| 21x21_empty_beam | | EMPTY | - | - | - | - |
| 21x21_empty_hybrid | | EMPTY | - | - | - | - |
| 21x21_empty_repair | | EMPTY | - | - | - | - |

## Batch 2: Flag combos (15x15 empty + partial)
| Grid | Algo | Flags | success | Slots | Fill% | Problematic | Time |
|------|------|-------|---------|-------|-------|-------------|------|
| 15x15_beam_O2 | | | False | 78/78 | 100% | 7 | 61.3s |
| 15x15_beam_O3 | | | False | 78/78 | 100% | 7 | 58.1s |
| 15x15_beam_O4 | | | False | 78/78 | 100% | 6 | 65.5s |
| 15x15_hybrid_O2 | | | True | 78/78 | 100% | 0 | 0.0s |
| 15x15_hybrid_O3 | | | False | 78/78 | 100% | 1 | 54.0s |
| 15x15_hybrid_O4 | | | True | 78/78 | 100% | 0 | 0.0s |
| 15x15_repair_O2 | | | True | 78/78 | 100% | 0 | 0.0s |
| 15x15_repair_O3 | | | True | 78/78 | 100% | 0 | 1.3s |
| 15x15_repair_O4 | | | True | 78/78 | 100% | 0 | 0.0s |
| 15x15partial_beam_O2 | | | False | 5/39 | 12% | 39 | 75.6s |
| 15x15partial_hybrid_O2 | | | True | 71/71 | 100% | 0 | 0.0s |
| 15x15partial_hybrid_O3 | | | False | 71/71 | 100% | 14 | 54.1s |
| 15x15partial_hybrid_O4 | | | EMPTY | - | - | - | - |
| 15x15partial_repair_O2 | | | False | 61/71 | 85% | 10 | 0.0s |
| 15x15partial_repair_O3 | | | False | 71/71 | 100% | 14 | 60.1s |
| 15x15partial_repair_O4 | | | False | 68/71 | 95% | 3 | 0.0s |

## Batch 3/4: Adaptive + all options (from task notifications)
Results captured from SSE task outputs — see individual task files.

## Missing: 21x21 tests (all), 15x15 partial flag combos (most)
