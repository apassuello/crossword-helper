#!/usr/bin/env python3
"""analyze_crossword_datasets.py

Analyzes crossword data sources downloaded by fetch_crossword_datasets.sh.
Produces per-source statistics and a cross-list comparison.

Usage:
    python scripts/analyze_crossword_datasets.py [--output-dir data/analysis]

Expects files in data/analysis/:
    - collaborative-word-list.dict   (from Crossword Nexus)
    - chris-jones-wordlist.txt       (from Chris Jones)
    - spreadthewordlist.txt          (from Spread the Wordlist, manual download)
    - xd-clues/                      (extracted from xd-clues.zip)
    - xd-metadata/                   (extracted from xd-metadata.zip)
    - xword_benchmark/               (cloned repo + data files)
"""

import argparse
import collections
import csv
import glob
import json
import os
import sys
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_ANALYSIS_DIR = os.path.join(PROJECT_ROOT, "data", "analysis")
APP_WORDLIST = os.path.join(PROJECT_ROOT, "data", "wordlists", "comprehensive_scored.txt")
APP_WORDLIST_PLAIN = os.path.join(PROJECT_ROOT, "data", "wordlists", "comprehensive.txt")


def load_semicolon_wordlist(filepath):
    """Load WORD;SCORE format. Returns list of (word, score) tuples."""
    entries = []
    if not os.path.isfile(filepath):
        return entries
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(";")
            if len(parts) == 2:
                try:
                    entries.append((parts[0], int(parts[1])))
                except ValueError:
                    continue
    return entries


def load_jones_wordlist(filepath):
    """Load Chris Jones format: 'word or phrase;score'. Uses rsplit to handle
    entries that contain semicolons in the word part (unlikely but safe)."""
    entries = []
    if not os.path.isfile(filepath):
        return entries
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.rsplit(";", 1)
            if len(parts) == 2:
                try:
                    entries.append((parts[0], int(parts[1])))
                except ValueError:
                    continue
    return entries


def load_app_wordlist():
    """Load our app's comprehensive wordlist for overlap comparison."""
    words = set()
    for path in [APP_WORDLIST, APP_WORDLIST_PLAIN]:
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                word = line.split(";")[0].upper()
                if word.isalpha():
                    words.add(word)
    return words


def alpha_only(word):
    """Return only alphabetic characters, uppercased."""
    return "".join(c for c in word.upper() if c.isalpha())


def wordlist_stats(entries, name):
    """Compute and print statistics for a scored word list."""
    if not entries:
        print(f"\n{'=' * 60}")
        print(f"{name}: FILE NOT FOUND / EMPTY")
        print(f"{'=' * 60}")
        return {}, set()

    words = [w for w, s in entries]
    scores = [s for w, s in entries]

    print(f"\n{'=' * 60}")
    print(f"{name}")
    print(f"{'=' * 60}")
    print(f"Total entries: {len(entries):,}")
    print(f"Score range: {min(scores)} – {max(scores)}")
    print(f"Unique score values: {len(set(scores))}")
    print(f"Mean score: {sum(scores) / len(scores):.1f}")
    print(f"Median score: {sorted(scores)[len(scores) // 2]}")

    # Length distribution (alpha chars only)
    lengths = collections.Counter(len(alpha_only(w)) for w in words)
    print("\nLength distribution (alpha chars only):")
    for length in sorted(lengths):
        if 1 <= length <= 21:
            print(f"  {length:2d} letters: {lengths[length]:>8,}")

    # Score distribution in buckets of 10
    score_buckets = collections.Counter((s // 10) * 10 for s in scores)
    print("\nScore distribution:")
    for bucket in sorted(score_buckets):
        print(f"  {bucket:3d}–{bucket + 9:3d}: {score_buckets[bucket]:>8,}")

    # Sample entries
    high = sorted(entries, key=lambda x: -x[1])[:5]
    mid_target = (min(scores) + max(scores)) // 2
    mid = sorted(entries, key=lambda x: abs(x[1] - mid_target))[:5]
    low = sorted(entries, key=lambda x: x[1])[:5]

    print("\nHighest-scored entries:")
    for w, s in high:
        print(f"  {w};{s}")
    print("Mid-scored entries:")
    for w, s in mid:
        print(f"  {w};{s}")
    print("Lowest-scored entries:")
    for w, s in low:
        print(f"  {w};{s}")

    # Format observations
    has_spaces = sum(1 for w in words if " " in w)
    has_lower = sum(1 for w in words if any(c.islower() for c in w))
    has_numbers = sum(1 for w in words if any(c.isdigit() for c in w))
    non_alpha = sum(1 for w in words if not w.isalpha())
    print(f"\nFormat observations:")
    print(f"  Entries with spaces: {has_spaces:,}")
    print(f"  Entries with lowercase: {has_lower:,}")
    print(f"  Entries with digits: {has_numbers:,}")
    print(f"  Entries with non-alpha chars: {non_alpha:,}")

    alpha_words = set(alpha_only(w) for w in words if alpha_only(w))
    return {"entries": entries, "scores": scores}, alpha_words


def analyze_xd_clues(analysis_dir):
    """Analyze xd-clues if extracted."""
    print(f"\n{'=' * 60}")
    print("XD CORPUS — CLUES")
    print(f"{'=' * 60}")

    # Look for extracted clue files
    clue_zip = os.path.join(analysis_dir, "xd-clues.zip")
    clue_dir = os.path.join(analysis_dir, "xd-clues")

    # Try to find TSV/CSV files from extraction
    clue_files = []
    for pattern in ["xd-clues*/*.tsv", "xd-clues*/*.csv", "xd-clues*/*.txt",
                     "*.tsv", "clues.*"]:
        clue_files.extend(glob.glob(os.path.join(analysis_dir, pattern)))

    if clue_zip and os.path.isfile(clue_zip):
        print(f"Zip file: {os.path.getsize(clue_zip) / 1024 / 1024:.1f} MB")
        try:
            with zipfile.ZipFile(clue_zip, "r") as zf:
                names = zf.namelist()
                print(f"Files in zip: {len(names)}")
                total_size = sum(i.file_size for i in zf.infolist())
                print(f"Uncompressed size: {total_size / 1024 / 1024:.1f} MB")
                print("Contents:")
                for name in names[:20]:
                    info = zf.getinfo(name)
                    print(f"  {name} ({info.file_size / 1024:.0f} KB)")
                if len(names) > 20:
                    print(f"  ... and {len(names) - 20} more files")

                # Sample first file
                first_data_file = [n for n in names if not n.endswith("/")]
                if first_data_file:
                    with zf.open(first_data_file[0]) as member:
                        lines = []
                        for i, raw_line in enumerate(member):
                            if i >= 15:
                                break
                            lines.append(raw_line.decode("utf-8", errors="replace").rstrip())
                    print(f"\nSample from {first_data_file[0]}:")
                    for line in lines:
                        print(f"  {line[:120]}")

                    # Count total lines in first file
                    with zf.open(first_data_file[0]) as member:
                        line_count = sum(1 for _ in member)
                    print(f"  Total lines in this file: {line_count:,}")
        except Exception as e:
            print(f"Error reading zip: {e}")
    elif clue_files:
        print(f"Found extracted files: {len(clue_files)}")
        for cf in clue_files[:5]:
            size = os.path.getsize(cf) / 1024 / 1024
            print(f"  {os.path.basename(cf)}: {size:.1f} MB")
    else:
        print("NOT FOUND — run fetch_crossword_datasets.sh first")
        print("Expected: xd-clues.zip (67MB, 6M+ answer/clue pairings)")
        print("Download from: https://xd.saul.pw/data")
        print("\nFormat (from documentation):")
        print("  TSV with columns: answer, clue, publication, year")
        print("  6,000,000+ rows across multiple publication-year files")
        print("  Grouped by publication and year")


def analyze_xd_metadata(analysis_dir):
    """Analyze xd-metadata if extracted."""
    print(f"\n{'=' * 60}")
    print("XD CORPUS — METADATA")
    print(f"{'=' * 60}")

    meta_zip = os.path.join(analysis_dir, "xd-metadata.zip")

    if os.path.isfile(meta_zip):
        print(f"Zip file: {os.path.getsize(meta_zip) / 1024 / 1024:.1f} MB")
        try:
            with zipfile.ZipFile(meta_zip, "r") as zf:
                names = zf.namelist()
                print(f"Files in zip: {len(names)}")
                total_size = sum(i.file_size for i in zf.infolist())
                print(f"Uncompressed size: {total_size / 1024 / 1024:.1f} MB")
                for name in names[:20]:
                    info = zf.getinfo(name)
                    print(f"  {name} ({info.file_size / 1024:.0f} KB)")

                first_data_file = [n for n in names if not n.endswith("/")]
                if first_data_file:
                    with zf.open(first_data_file[0]) as member:
                        lines = []
                        for i, raw_line in enumerate(member):
                            if i >= 10:
                                break
                            lines.append(raw_line.decode("utf-8", errors="replace").rstrip())
                    print(f"\nSample from {first_data_file[0]}:")
                    for line in lines:
                        print(f"  {line[:120]}")
        except Exception as e:
            print(f"Error reading zip: {e}")
    else:
        print("NOT FOUND — run fetch_crossword_datasets.sh first")
        print("Expected: xd-metadata.zip (2MB)")
        print("Download from: https://xd.saul.pw/data")
        print("\nFormat (from documentation):")
        print("  Metadata and similarity scores for all puzzles in the corpus")
        print("  Includes publication, date, author, editor, grid dimensions")


def analyze_xword_benchmark(analysis_dir):
    """Analyze xword_benchmark repo and data."""
    print(f"\n{'=' * 60}")
    print("XWORD_BENCHMARK (UMass Lowell, ACL 2022)")
    print(f"{'=' * 60}")

    repo_dir = os.path.join(analysis_dir, "xword_benchmark")
    if not os.path.isdir(repo_dir):
        print("NOT FOUND — run fetch_crossword_datasets.sh first")
        return

    print(f"Repo cloned: {repo_dir}")

    # Check for data files
    data_dir = os.path.join(repo_dir, "data")
    splits = ["train.source", "train.target", "val.source", "val.target",
              "test.source", "test.target"]

    found_data = False
    for split in splits:
        path = os.path.join(data_dir, split)
        if os.path.isfile(path):
            found_data = True
            lines = sum(1 for _ in open(path, encoding="utf-8", errors="replace"))
            size = os.path.getsize(path) / 1024 / 1024
            # Sample
            with open(path, encoding="utf-8", errors="replace") as f:
                samples = [next(f).strip() for _ in range(5)]
            print(f"\n  {split}: {lines:,} lines ({size:.1f} MB)")
            print(f"    Sample: {samples[:3]}")

    if not found_data:
        print("\nClue-answer data NOT YET DOWNLOADED.")
        print("Download manually from one of:")
        print("  Dropbox:    https://www.dropbox.com/sh/pzpaus6wxg1cozo")
        print("  GDrive:     https://drive.google.com/drive/folders/1rPrgx8QAgL-f884y1FuFDu9e8m0VYWz-")
        print("  Mediafire:  https://www.mediafire.com/folder/thzqcfeirl79d/dataset")
        print("Place files in:", data_dir)

    print("\nDataset structure (from README):")
    print("  - train/val/test .source files contain clues (one per line)")
    print("  - train/val/test .target files contain answers (one per line)")
    print("  - Line N in .source corresponds to line N in .target")
    print("  - Multi-word answers merged: e.g. 'VERYFAST' (no spaces)")
    print("  - 6M+ total clue-answer pairs across all splits")
    print("  - NYT puzzle .puz files require separate NYT permission")

    # Check for convert.py
    convert_py = os.path.join(repo_dir, "convert.py")
    if os.path.isfile(convert_py):
        print(f"\n  convert.py found — converts .puz → .json")


def cross_list_comparison(wordlists, app_words):
    """Compare overlap between word lists."""
    print(f"\n{'=' * 60}")
    print("CROSS-LIST OVERLAP COMPARISON")
    print(f"{'=' * 60}")

    names = list(wordlists.keys())

    print(f"\nWord counts (alpha-normalized, unique):")
    for name in names:
        print(f"  {name}: {len(wordlists[name]):,}")
    if app_words:
        print(f"  Our App (comprehensive): {len(app_words):,}")

    # Pairwise overlap
    print(f"\nPairwise overlap:")
    for i, name_a in enumerate(names):
        for name_b in names[i + 1:]:
            overlap = wordlists[name_a] & wordlists[name_b]
            pct_a = len(overlap) / len(wordlists[name_a]) * 100 if wordlists[name_a] else 0
            pct_b = len(overlap) / len(wordlists[name_b]) * 100 if wordlists[name_b] else 0
            print(f"  {name_a} ∩ {name_b}: {len(overlap):,} "
                  f"({pct_a:.1f}% of {name_a}, {pct_b:.1f}% of {name_b})")

    # Overlap with our app
    if app_words:
        print(f"\nOverlap with our app's wordlist:")
        for name in names:
            overlap = wordlists[name] & app_words
            pct_ext = len(overlap) / len(wordlists[name]) * 100 if wordlists[name] else 0
            pct_app = len(overlap) / len(app_words) * 100 if app_words else 0
            new = len(wordlists[name] - app_words)
            print(f"  {name} ∩ App: {len(overlap):,} "
                  f"({pct_ext:.1f}% of {name}, {pct_app:.1f}% of App)")
            print(f"    New words not in our app: {new:,}")

        all_external = set()
        for ws in wordlists.values():
            all_external |= ws
        new_total = all_external - app_words
        print(f"\n  All external combined: {len(all_external):,} unique words")
        print(f"  New words we could add: {len(new_total):,}")


def main():
    parser = argparse.ArgumentParser(description="Analyze crossword data sources")
    parser.add_argument("--output-dir", default=DEFAULT_ANALYSIS_DIR,
                        help="Directory containing downloaded data")
    args = parser.parse_args()

    analysis_dir = args.output_dir
    os.chdir(analysis_dir)

    print("Crossword Data Sources — Analysis Report")
    print(f"Data directory: {analysis_dir}")
    print(f"{'=' * 60}")

    # ── Scored Word Lists ──────────────────────────────────────
    collab_entries = load_semicolon_wordlist("collaborative-word-list.dict")
    _, collab_words = wordlist_stats(collab_entries, "COLLABORATIVE WORD LIST (Crossword Nexus)")

    jones_entries = load_jones_wordlist("chris-jones-wordlist.txt")
    _, jones_words = wordlist_stats(jones_entries, "CHRIS JONES' CROSSWORD WORDLIST")

    # Spread the Wordlist (manual download)
    stw_entries = load_semicolon_wordlist("spreadthewordlist.txt")
    _, stw_words = wordlist_stats(stw_entries, "SPREAD THE WORDLIST (Brooke Husic)")

    # ── xd Corpus ──────────────────────────────────────────────
    analyze_xd_clues(analysis_dir)
    analyze_xd_metadata(analysis_dir)

    # ── xword_benchmark ────────────────────────────────────────
    analyze_xword_benchmark(analysis_dir)

    # ── Cross-list comparison ──────────────────────────────────
    wordlists = {}
    if collab_words:
        wordlists["Collaborative"] = collab_words
    if jones_words:
        wordlists["ChrisJones"] = jones_words
    if stw_words:
        wordlists["SpreadTheWordlist"] = stw_words

    app_words = load_app_wordlist()
    if wordlists:
        cross_list_comparison(wordlists, app_words)

    print(f"\n{'=' * 60}")
    print("Analysis complete.")


if __name__ == "__main__":
    main()
