#!/usr/bin/env bash
# fetch_crossword_datasets.sh
#
# Downloads freely available crossword data sources into data/analysis/.
# Idempotent: skips files that already exist.
#
# Usage:
#   ./scripts/fetch_crossword_datasets.sh
#
# Sources downloaded:
#   1. Saul Pwanson's xd corpus (clues + metadata)
#   2. xword_benchmark (UMass Lowell ACL 2022)
#   3. Crossword Nexus Collaborative Word List
#   4. Chris Jones' Crossword Wordlist

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEST="$PROJECT_ROOT/data/analysis"

mkdir -p "$DEST"

# Retry wrapper: retries up to 4 times with exponential backoff on failure
fetch_with_retry() {
    local url="$1"
    local output="$2"
    local attempt=1
    local max_attempts=4
    local wait=2

    while [ $attempt -le $max_attempts ]; do
        echo "  Attempt $attempt: downloading $url"
        if curl -fSL --max-time 300 -o "$output" "$url" 2>/dev/null; then
            return 0
        fi
        if [ $attempt -lt $max_attempts ]; then
            echo "  Failed. Retrying in ${wait}s..."
            sleep $wait
            wait=$((wait * 2))
        fi
        attempt=$((attempt + 1))
    done

    echo "  ERROR: Failed to download $url after $max_attempts attempts"
    return 1
}

echo "=== Crossword Dataset Fetcher ==="
echo "Destination: $DEST"
echo ""

# ─────────────────────────────────────────────────────────────
# 1. Saul Pwanson's xd corpus
# ─────────────────────────────────────────────────────────────
echo "[1/4] xd corpus — clues (67MB zip, 6M+ clue/answer pairings)"
if [ -f "$DEST/xd-clues.zip" ]; then
    echo "  Already exists, skipping."
else
    fetch_with_retry "https://xd.saul.pw/data/xd-clues.zip" "$DEST/xd-clues.zip" || true
fi

echo "[1b/4] xd corpus — metadata (2MB zip)"
if [ -f "$DEST/xd-metadata.zip" ]; then
    echo "  Already exists, skipping."
else
    fetch_with_retry "https://xd.saul.pw/data/xd-metadata.zip" "$DEST/xd-metadata.zip" || true
fi

# Unzip if present
for zipfile in "$DEST/xd-clues.zip" "$DEST/xd-metadata.zip"; do
    if [ -f "$zipfile" ]; then
        basename="${zipfile%.zip}"
        dirname="$basename"
        if [ ! -d "$dirname" ] && [ ! -f "$dirname.tsv" ]; then
            echo "  Extracting $(basename "$zipfile")..."
            unzip -o -d "$DEST" "$zipfile" 2>/dev/null || true
        fi
    fi
done

# ─────────────────────────────────────────────────────────────
# 2. xword_benchmark (UMass Lowell)
# ─────────────────────────────────────────────────────────────
echo ""
echo "[2/4] xword_benchmark — clue/answer dataset (ACL 2022)"
if [ -d "$DEST/xword_benchmark" ]; then
    echo "  Already cloned, skipping."
else
    echo "  Cloning repo (shallow)..."
    git clone --depth 1 https://github.com/text-machine-lab/xword_benchmark.git "$DEST/xword_benchmark" 2>/dev/null || true
fi

# The actual clue-answer data is hosted externally. Download from Dropbox.
XWB_DATA="$DEST/xword_benchmark/data"
mkdir -p "$XWB_DATA"
# Dropbox link from the README
DROPBOX_BASE="https://www.dropbox.com/sh/pzpaus6wxg1cozo"
if [ ! -f "$XWB_DATA/train.source" ]; then
    echo "  NOTE: Clue-answer data must be downloaded manually from:"
    echo "    Dropbox:  $DROPBOX_BASE"
    echo "    GDrive:   https://drive.google.com/drive/folders/1rPrgx8QAgL-f884y1FuFDu9e8m0VYWz-"
    echo "    Mediafire: https://www.mediafire.com/folder/thzqcfeirl79d/dataset"
    echo "  Place train.source, train.target, val.source, val.target, test.source, test.target in:"
    echo "    $XWB_DATA/"
else
    echo "  Data files already present."
fi

# ─────────────────────────────────────────────────────────────
# 3. Crossword Nexus Collaborative Word List
# ─────────────────────────────────────────────────────────────
echo ""
echo "[3/4] Collaborative Word List — ~568K scored entries"
if [ -f "$DEST/collaborative-word-list.dict" ]; then
    echo "  Already exists, skipping."
else
    fetch_with_retry \
        "https://raw.githubusercontent.com/Crossword-Nexus/collaborative-word-list/main/xwordlist.dict" \
        "$DEST/collaborative-word-list.dict"
fi

# ─────────────────────────────────────────────────────────────
# 4. Chris Jones' Crossword Wordlist
# ─────────────────────────────────────────────────────────────
echo ""
echo "[4/4] Chris Jones' Wordlist — ~176K scored entries"
if [ -f "$DEST/chris-jones-wordlist.txt" ]; then
    echo "  Already exists, skipping."
else
    fetch_with_retry \
        "https://raw.githubusercontent.com/christophsjones/crossword-wordlist/master/crossword_wordlist.txt" \
        "$DEST/chris-jones-wordlist.txt"
fi

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
echo ""
echo "=== Download Summary ==="
echo "Files in $DEST:"
ls -lhS "$DEST" | grep -v '^total' | grep -v '^\.'
echo ""
echo "Manual downloads still needed:"
echo "  - Spread the Wordlist:  https://www.spreadthewordlist.com/"
echo "    (download .txt and .dict, place in $DEST/)"
echo "  - Expanded Crossword Name Database:"
echo "    https://sites.google.com/view/expandedcrosswordnamedatabase/home"
echo "    (download .txt files from Google Drive links, place in $DEST/)"
echo "  - xword_benchmark clue-answer splits (see step 2 above)"
echo ""
echo "When all files are in place, run:"
echo "  python scripts/analyze_crossword_datasets.py"
