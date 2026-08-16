# Crossword Data Sources Analysis

> Research and analysis of freely available crossword datasets, word lists, and clue databases.
> Produced March 2026 for the Crossword Construction Helper project.

---

## 1. Executive Summary

Seven major free crossword data sources were evaluated. Here's what's available and what matters most:

**Most useful for our app (immediate integration):**

1. **Collaborative Word List** (Crossword Nexus) — 567,657 scored entries, semicolon-delimited format nearly identical to ours. Adds ~194K words we don't have. **Integrate first.**
2. **Chris Jones' Wordlist** — 175,873 curated entries with quality scores. 99% overlap with Collaborative but has superior hand-tuned scores for common words. Useful as a **score calibration reference**.
3. **Spread the Wordlist** — ~303K entries scored 0–60. Strong community curation, updated quarterly. Good **second word list to integrate**.

**Useful for clue databases (future feature):**

4. **Saul Pwanson's xd corpus** — 6M+ clue/answer pairings across decades. The definitive open clue database. Essential if we add clue suggestion features.
5. **xword_benchmark** — 6M+ clue/answer pairs with train/val/test splits. Academic dataset, useful for ML-based clue generation.

**Niche but valuable:**

6. **Expanded Crossword Name Database** — ~2,434 entries of underrepresented names. Small but important for diversity-conscious construction.
7. **George Ho's cryptic clues dataset** — 500K+ cryptic clues. Only relevant if we add cryptic crossword support.

**Recommended integration order:** Collaborative Word List → Spread the Wordlist → xd clue corpus → Expanded Names DB

---

## 2. Per-Source Analysis

### 2.1 Collaborative Word List (Crossword Nexus)

| Property | Value |
|----------|-------|
| **URL** | https://github.com/Crossword-Nexus/collaborative-word-list |
| **File** | `xwordlist.dict` |
| **Format** | `WORD;SCORE` (semicolon-delimited, one entry per line) |
| **Encoding** | UTF-8 |
| **Total entries** | 567,657 |
| **Score range** | 0–100 |
| **Mean score** | 46.5 |
| **Size on disk** | 8.0 MB |
| **License** | Open source (MIT), community-driven |

**Length distribution:**

| Length | Count | Length | Count |
|--------|---------|--------|---------|
| 1 | 27 | 12 | 45,850 |
| 2 | 385 | 13 | 39,932 |
| 3 | 4,424 | 14 | 31,026 |
| 4 | 11,667 | 15 | 30,511 |
| 5 | 22,759 | 16 | 14,810 |
| 6 | 34,123 | 17 | 11,090 |
| 7 | 47,753 | 18 | 8,198 |
| 8 | 60,130 | 19 | 6,144 |
| 9 | 62,787 | 20 | 4,489 |
| 10 | 63,034 | 21 | 3,779 |
| 11 | 56,039 | | |

**Score distribution:**

| Range | Count | Range | Count |
|---------|---------|---------|---------|
| 0–9 | 17,190 | 50–59 | 121,893 |
| 10–19 | 1,045 | 60–69 | 22,443 |
| 20–29 | 111,040 | 70–79 | 30,737 |
| 30–39 | 68,341 | 80–89 | 30,368 |
| 40–49 | 116,905 | 90–100 | 47,695 |

**Sample entries:**

High-scoring (80+):
```
4HCLUB;80
50WAYSTOLEAVEYOURLOVER;80
21GRAMS;80
3WISEMONKEYS;80
```

Mid-scoring (40–60):
```
100GRANDBAR;50
100PERCENT;50
100PROOFAGEDINSOUL;53
```

Low-scoring (≤20):
```
100;5
30;5
AABYE;16
AACK;1
AAER;15
```

**Data quality observations:**
- All uppercase, no lowercase entries
- 992 entries contain digits (e.g., `4HCLUB`, `100PERCENT`) — these would need filtering for our app (alpha-only constraint)
- No entries with spaces
- Very clean, well-maintained via GitHub Actions CI that enforces formatting
- Scores are community-curated, not algorithmically generated

---

### 2.2 Chris Jones' Crossword Wordlist

| Property | Value |
|----------|-------|
| **URL** | https://github.com/christophsjones/crossword-wordlist |
| **File** | `crossword_wordlist.txt` |
| **Format** | `word or phrase;SCORE` (semicolon-delimited) |
| **Encoding** | UTF-8 |
| **Total entries** | 175,873 |
| **Score range** | 2–50 |
| **Mean score** | 32.1 |
| **Size on disk** | 2.3 MB |
| **License** | Open (GitHub) |

**Length distribution (alpha chars only):**

| Length | Count | Length | Count |
|--------|---------|--------|---------|
| 1 | 25 | 12 | 8,044 |
| 2 | 358 | 13 | 5,881 |
| 3 | 3,603 | 14 | 3,618 |
| 4 | 9,295 | 15 | 5,880 |
| 5 | 15,517 | 16 | 803 |
| 6 | 20,402 | 17 | 425 |
| 7 | 24,187 | 18 | 221 |
| 8 | 24,228 | 19 | 152 |
| 9 | 20,711 | 20 | 76 |
| 10 | 18,521 | 21 | 80 |
| 11 | 13,750 | | |

**Score distribution:**

| Range | Count |
|---------|---------|
| 0–9 | 870 |
| 10–19 | 11,745 |
| 20–29 | 46,260 |
| 30–39 | 66,501 |
| 40–49 | 27,140 |
| 50 | 23,357 |

**Sample entries:**

Score 50 (highest):
```
a bright future;50
A Christmas Story;50
a comedy of errors;50
A team;50
A student;50
```

Score 25–35 (mid):
```
AAABATTERY;29
AAABONDS;30
AAAGUIDE;28
```

Score ≤10 (low):
```
AAAAH;7
AAAL;9
AAGE;8
AAKER;10
AALAND;8
```

**Data quality observations:**
- **Mixed case:** 5,778 entries have lowercase letters (e.g., `a bright future`, `A Christmas Story`). Most (170,095) are all uppercase.
- **Spaces:** 4,287 entries contain spaces (multi-word phrases). These represent crossword answers as they'd appear naturally, not in grid form.
- Score 50 = "common word/phrase" (the best); 2 = lowest quality.
- Sources: NYT, WSJ, WaPo, UKACD, Peter Broda's list, frequency data.
- More curated/conservative than Collaborative — fewer entries but higher average quality.
- **Import note:** Would need uppercasing + space/punctuation stripping to match our format.

---

### 2.3 Spread the Wordlist (Brooke Husic & Enrique Henestroza Anguiano)

| Property | Value |
|----------|-------|
| **URL** | https://www.spreadthewordlist.com/ |
| **Files** | `spreadthewordlist.txt` (.dict and .txt formats) |
| **Format** | `WORD;SCORE` (semicolon-delimited) |
| **Encoding** | UTF-8 |
| **Total entries** | ~303,000 (as of Jan 2025) |
| **Score range** | 0–60 |
| **114K+ entries** scored 50+ ("clean") |
| **Size on disk** | ~4 MB (estimated) |
| **License** | CC BY-NC-SA (non-commercial) |
| **Updates** | Quarterly |

**Score meaning:**

| Score | Meaning |
|-------|---------|
| 50+ | Clean, high-quality fill |
| 40 | Questionable |
| 30 | Stale/dated |
| 20 | Thematic (niche) |
| 10 | Likely error |
| 0 | Offensive |

**Key characteristics:**
- Data-driven compilation from freely available frequency data and crossword venue usage
- Designed for new constructors who lack access to expensive proprietary word lists
- Integrated into Ingrid (web-based crossword construction tool)
- Scores are largely automated, not hand-curated
- **Requires manual download** — website blocks automated fetching (403)

**Import note:** Format is nearly identical to our `WORD;SCORE` format. Score range 0–60 would need rescaling to our 1–150 range if scores are preserved. CC BY-NC-SA license may restrict commercial use.

---

### 2.4 Saul Pwanson's xd Corpus

| Property | Value |
|----------|-------|
| **URL** | https://xd.saul.pw/data |
| **Source code** | https://github.com/century-arcade/xd |
| **xd-clues.zip** | 67 MB (6M+ answer/clue pairings) |
| **xd-metadata.zip** | 2 MB (metadata + similarity for all puzzles) |
| **xd-puzzles.zip** | 12 MB (6,000+ pre-1965 NYT puzzles) |
| **SQLite DB** | 400 MB (complete puzzle data) |
| **License** | Open / freely available |

**The .xd format:**

A plain-text UTF-8 format with sections separated by double blank lines:

```
## Metadata
Title: NY Times, Thursday, Jan 01, 1942
Author: Charles Erlenkotter
Editor: Margaret Farrar
Date: 1942-01-01

## Grid
JOKEBOOK.LAPAZ
....##...##....
ABCS.ADENOSINE

## Clues
A1. Book of humor ~ JOKEBOOK
A6. Capital of Bolivia ~ LAPAZ
D1. Letters ~ ABCS
```

**Clue database structure (xd-clues.zip):**
- TSV format with columns: `answer`, `clue`, `publication`, `year`
- Grouped by publication-year (one file per publication per year)
- 6,000,000+ total answer/clue pairings
- Coverage: Multiple publications across decades (primarily pre-1965 NYT, but also other sources)

**Metadata structure (xd-metadata.zip):**
- Puzzle metadata: publication, date, author, editor, grid dimensions
- Grid similarity scores between puzzles
- Useful for deduplication and provenance tracking

**Note:** Direct download blocked from this environment (403). Must be downloaded via browser or from a non-restricted network.

**Usefulness for our app:**
- The clue database is the single most valuable resource for a future "clue suggestion" feature
- Grid data could be used to study common black square patterns
- Publication/year metadata enables filtering by era or source
- Would need a new data layer — this isn't a word list, it's a relational clue→answer→publication database

---

### 2.5 xword_benchmark (UMass Lowell, ACL 2022)

| Property | Value |
|----------|-------|
| **URL** | https://github.com/text-machine-lab/xword_benchmark |
| **Paper** | "Down and Across: Introducing Crossword-Solving as a New NLP Benchmark" (ACL 2022) |
| **Clue-answer pairs** | 6M+ total |
| **Splits** | train/val/test (.source + .target files) |
| **Puzzle data** | Dates only (copyright: NYT) |
| **License** | Clue-answer pairs: open; NYT puzzles: requires NYT permission |

**Data format:**
- `train.source` / `val.source` / `test.source` — one clue per line
- `train.target` / `val.target` / `test.target` — one answer per line
- Line N in .source corresponds to line N in .target
- Multi-word answers are concatenated: `VERYFAST` (no spaces)
- Post-processing splits answers using dictionary-based word segmentation

**Download locations (manual):**
- [Dropbox](https://www.dropbox.com/sh/pzpaus6wxg1cozo)
- [Google Drive](https://drive.google.com/drive/folders/1rPrgx8QAgL-f884y1FuFDu9e8m0VYWz-)
- [Mediafire](https://www.mediafire.com/folder/thzqcfeirl79d/dataset)

**Includes `convert.py`:** Converts AcrossLite `.puz` files to `.json` format.

**Usefulness for our app:**
- Overlaps significantly with xd corpus for clue/answer data
- Train/val/test splits useful if we ever build ML-based clue generation
- The `convert.py` script is useful for importing `.puz` puzzles

---

### 2.6 Expanded Crossword Name Database (ECND)

| Property | Value |
|----------|-------|
| **URL** | https://sites.google.com/view/expandedcrosswordnamedatabase/home |
| **Creator** | Erica Hsiung Wojcik |
| **Total entries** | 2,434 unique entries from 934 names + 54 places/things |
| **Format** | Multiple `.txt` files (full names, first names, last names) + `.dict` for queer terms |
| **Last updated** | June 2022 |
| **License** | Free and open |

**Contents:**
- Names of notable women, non-binary, trans, and people of color
- Places and organizations
- Works of art and monuments
- Queer terminology (with scores, in `.dict` format)
- Supplemental Google Sheet with short bios for cluing inspiration

**Download:** Via Google Drive links on the Google Sites page (requires manual browser download).

**Import notes:**
- Names are in natural form (`OPRAH WINFREY`) — would need space-stripping for grid use (`OPRAHWINFREY`)
- Small enough to review manually before importing
- `.dict` files use the same `WORD;SCORE` format we support
- Useful as a curated "themed" word list in our `data/wordlists/themed/` directory

---

### 2.7 George Ho's Crossword Resources Page

| Property | Value |
|----------|-------|
| **URL** | https://www.georgeho.org/crosswords-datasets-dictionaries/ |
| **Type** | Survey/guide (not a dataset itself) |

**Additional sources mentioned (not already covered above):**

| Source | Type | Notes |
|--------|------|-------|
| **OneLook** / **OneLook Thesaurus** | Pattern search API | Supports `bl????rd` patterns; could be used as a live lookup fallback |
| **Online Etymology Dictionary** | Reference | Useful for clue writing, not word lists |
| **CMU Pronouncing Dictionary** | Pronunciation data | Could enable phonetic pattern matching |
| **Peter Broda's wordlist** | Scored word list | Widely referenced but no longer freely hosted; partially incorporated into Chris Jones' list |
| **cryptics.georgeho.org** | 500K+ cryptic clues | 12+ years of cryptic crossword clues with blogger explanations; only relevant for cryptic crossword support |

---

## 3. Word List Comparison Matrix

| Property | Collaborative | Chris Jones | Spread the Wordlist | Our App |
|----------|:------------:|:-----------:|:-------------------:|:-------:|
| **Total entries** | 567,657 | 175,873 | ~303,000 | 453,989 |
| **Score range** | 0–100 | 2–50 | 0–60 | 1–150 |
| **Format** | `WORD;SCORE` | `word;SCORE` | `WORD;SCORE` | `WORD;SCORE` |
| **Delimiter** | `;` | `;` | `;` | `;` |
| **Case** | UPPER | Mixed | UPPER | UPPER |
| **Has spaces** | No | Yes (4,287) | No | No |
| **Has digits** | Yes (992) | No | No | No |
| **Curation method** | Community | Hand + automated | Automated + community | Algorithmic |
| **Update frequency** | Ongoing (PRs) | Occasional | Quarterly | Static |
| **License** | MIT | Open | CC BY-NC-SA | — |

### Overlap Analysis

| Comparison | Shared words | % of List A | % of List B |
|-----------|:-----------:|:-----------:|:-----------:|
| Collaborative ∩ Chris Jones | 172,004 | 30.3% | 99.0% |
| Collaborative ∩ Our App | 372,751 | 65.7% | 82.1% |
| Chris Jones ∩ Our App | 173,319 | 99.7% | 38.2% |
| All external ∩ Our App | — | — | — |

**Key findings:**
- Chris Jones' list is almost entirely contained within both the Collaborative list (99.0%) and our app (99.7%). It adds only 480 new words.
- The Collaborative list has **194,213 words not in our app** — the largest source of new vocabulary.
- Our app has ~81K words not in the Collaborative list (specialized/less common entries).

---

## 4. Format Compatibility Notes

Our app's current word list format: `WORD;SCORE` (semicolon-delimited, uppercase A-Z only, 3–21 chars).
Our app's word list loader: `cli/src/fill/word_list.py` with normalization in `cli/src/fill/normalize_wordlists.py`.

### What's needed to import each source:

| Source | Import Complexity | Changes Needed |
|--------|:-----------------:|----------------|
| **Collaborative Word List** | **Trivial** | Filter 992 entries with digits. Otherwise format-compatible as-is. Rescale 0–100 → 1–150. |
| **Chris Jones' Wordlist** | **Easy** | Uppercase all entries, strip spaces/punctuation for multi-word phrases. Rescale 2–50 → 1–150. |
| **Spread the Wordlist** | **Trivial** | Format-compatible as-is. Rescale 0–60 → 1–150. Review CC BY-NC-SA license implications. |
| **ECND** | **Easy** | Strip spaces from names, uppercase. Small enough for manual review. Add as themed list. |
| **xd clue corpus** | **Medium** | New data model needed — not a word list. TSV parsing, deduplication, storage in SQLite or similar. |
| **xword_benchmark** | **Medium** | Same as xd corpus — clue/answer pairs, not word list format. Would need separate data layer. |

### Score rescaling formulas:

```python
# Collaborative (0-100) → Our app (1-150)
new_score = max(1, int(original_score * 1.5))

# Chris Jones (2-50) → Our app (1-150)
new_score = max(1, int((original_score / 50) * 150))

# Spread the Wordlist (0-60) → Our app (1-150)
new_score = max(1, int((original_score / 60) * 150))
```

### User-requested target format

The user mentioned `WORD<TAB>SCORE<TAB>SOURCE` as a desired format. This differs from the current app format (`WORD;SCORE` with semicolons). If this new format is adopted, the import pipeline would also need to emit a SOURCE column (e.g., `collaborative`, `jones`, `stw`).

---

## 5. Recommended Next Steps

### Phase 1: Word List Enhancement (Low effort, high impact)

1. **Import the Collaborative Word List** — adds ~194K words, trivial format conversion. Write a one-time import script that:
   - Filters non-alpha entries
   - Rescales scores to 1–150
   - Deduplicates against existing comprehensive list
   - Preserves higher score when duplicates exist

2. **Import Spread the Wordlist** (after manual download) — adds likely ~50–80K additional words beyond Collaborative. Review CC BY-NC-SA license.

3. **Add ECND as a themed list** — place in `data/wordlists/themed/representation.txt` for diversity-conscious construction.

### Phase 2: Score Calibration (Medium effort, medium impact)

4. **Cross-reference scores** across lists for shared words. Where three lists agree a word is high-quality, boost its score. Where lists disagree, investigate.

5. **Use Chris Jones' scores as calibration data** — his hand-tuned scores for common words are the most trustworthy quality signal.

### Phase 3: Clue Database (High effort, high impact)

6. **Download and index the xd clue corpus** into a SQLite database. Build a clue suggestion feature that, given a filled answer, shows historical clues used for that word.

7. **Consider xword_benchmark** for ML-based clue generation in the future.

---

## Appendix: Scripts

Two scripts are provided to reproduce this analysis:

- **`scripts/fetch_crossword_datasets.sh`** — Downloads all automatically-fetchable data sources to `data/analysis/`. Idempotent (skips existing files). Prints instructions for manual downloads.

- **`scripts/analyze_crossword_datasets.py`** — Runs statistical analysis on downloaded data: entry counts, score distributions, length distributions, cross-list overlap. Handles missing files gracefully.

Usage:
```bash
./scripts/fetch_crossword_datasets.sh
python scripts/analyze_crossword_datasets.py
```
