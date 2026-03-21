#!/usr/bin/env bash
# fetch_tool_sources.sh
#
# Downloads source files from open-source crossword construction tools
# for competitive analysis. Outputs go to data/research/<tool>/.
#
# Usage:
#   ./scripts/research/fetch_tool_sources.sh [--output-dir DIR]
#
# Requires: curl

set -euo pipefail

OUTPUT_DIR="${1:-data/research}"
CURL="curl -fsSL --retry 3 --retry-delay 2"

echo "==> Fetching crossword tool sources into ${OUTPUT_DIR}"

# ---------------------------------------------------------------------------
# 1. Exet  (viresh-ratnakar/exet)
# ---------------------------------------------------------------------------
EXET_DIR="${OUTPUT_DIR}/exet"
EXET_BASE="https://raw.githubusercontent.com/viresh-ratnakar/exet/master"

mkdir -p "${EXET_DIR}"
echo "--- Exet ---"

declare -a EXET_FILES=(
    "README.md"
    "CHANGELOG.md"
    "exet-autofill.js"
    "exet-lexicon.js"
    "exet.js"
    "exet.css"
    "exet-analysis.js"
    "exet-storage.js"
)

for f in "${EXET_FILES[@]}"; do
    dest="${EXET_DIR}/${f}"
    if [[ -f "${dest}" ]]; then
        echo "  [skip] ${f} (already exists)"
    else
        echo "  [fetch] ${f}"
        $CURL -o "${dest}" "${EXET_BASE}/${f}" || echo "  [WARN] failed: ${f}"
    fi
done

# ---------------------------------------------------------------------------
# 2. CrossHatch  (ben4808/crosshatch)
# ---------------------------------------------------------------------------
CH_DIR="${OUTPUT_DIR}/crosshatch"
CH_BASE="https://raw.githubusercontent.com/ben4808/crosshatch/master"

mkdir -p "${CH_DIR}/src/lib" "${CH_DIR}/src/models" "${CH_DIR}/src/components"
echo "--- CrossHatch ---"

declare -a CH_ROOT_FILES=(
    "README.md"
    "package.json"
)
for f in "${CH_ROOT_FILES[@]}"; do
    dest="${CH_DIR}/${f}"
    if [[ -f "${dest}" ]]; then
        echo "  [skip] ${f}"
    else
        echo "  [fetch] ${f}"
        $CURL -o "${dest}" "${CH_BASE}/${f}" || echo "  [WARN] failed: ${f}"
    fi
done

declare -a CH_LIB_FILES=(
    "fill.ts"
    "section.ts"
    "entryCandidates.ts"
    "wordList.ts"
    "grid.ts"
    "insertEntry.ts"
    "priorityQueue.ts"
    "puzFiles.ts"
    "util.ts"
)
for f in "${CH_LIB_FILES[@]}"; do
    dest="${CH_DIR}/src/lib/${f}"
    if [[ -f "${dest}" ]]; then
        echo "  [skip] src/lib/${f}"
    else
        echo "  [fetch] src/lib/${f}"
        $CURL -o "${dest}" "${CH_BASE}/src/lib/${f}" || echo "  [WARN] failed: src/lib/${f}"
    fi
done

declare -a CH_MODEL_FILES=(
    "Grid.ts"
    "Puzzle.ts"
    "Fill.ts"
    "Word.ts"
    "Square.ts"
)
for f in "${CH_MODEL_FILES[@]}"; do
    dest="${CH_DIR}/src/models/${f}"
    if [[ -f "${dest}" ]]; then
        echo "  [skip] src/models/${f}"
    else
        echo "  [fetch] src/models/${f}"
        $CURL -o "${dest}" "${CH_BASE}/src/models/${f}" || echo "  [WARN] failed: src/models/${f}"
    fi
done

# Also fetch the crosswords-dicts README
mkdir -p "${OUTPUT_DIR}/crosswords-dicts"
dest="${OUTPUT_DIR}/crosswords-dicts/README.md"
if [[ ! -f "${dest}" ]]; then
    echo "  [fetch] crosswords-dicts README"
    $CURL -o "${dest}" "https://raw.githubusercontent.com/ben4808/crosswords-dicts/main/README.md" \
        || echo "  [WARN] no README in crosswords-dicts"
fi

# ---------------------------------------------------------------------------
# 3. Crosslift / rymuelle fork
# ---------------------------------------------------------------------------
CL_DIR="${OUTPUT_DIR}/crosslift"
CL_BASE="https://raw.githubusercontent.com/rymuelle/Automatic-Crossword-Puzzle-Filling/main"

mkdir -p "${CL_DIR}/src/crosslift"
echo "--- Crosslift (rymuelle fork) ---"

$CURL -o "${CL_DIR}/README.md" "${CL_BASE}/README.md" 2>/dev/null \
    || echo "  [WARN] failed: README.md"

declare -a CL_FILES=(
    "ConstructionAlgorithm.py"
    "create_puzzle.py"
    "crossword.py"
    "generate_grid.py"
    "make_clues.py"
    "read_clues.py"
    "scoring.py"
    "save_puzzle.py"
    "word_reader.py"
    "utils.py"
    "make_rotaitonal_grid.py"
)
for f in "${CL_FILES[@]}"; do
    dest="${CL_DIR}/src/crosslift/${f}"
    if [[ -f "${dest}" ]]; then
        echo "  [skip] ${f}"
    else
        echo "  [fetch] ${f}"
        $CURL -o "${dest}" "${CL_BASE}/src/crosslift/${f}" || echo "  [WARN] failed: ${f}"
    fi
done

# ---------------------------------------------------------------------------
# 4. MichaelWehar original
# ---------------------------------------------------------------------------
MW_DIR="${OUTPUT_DIR}/wehar-autofill"
MW_BASE="https://raw.githubusercontent.com/MichaelWehar/Automatic-Crossword-Puzzle-Filling/master"

mkdir -p "${MW_DIR}"
echo "--- MichaelWehar/Automatic-Crossword-Puzzle-Filling ---"

declare -a MW_FILES=(
    "README.md"
    "construction_algorithm.py"
    "crossword.py"
    "word_reader.py"
)
for f in "${MW_FILES[@]}"; do
    dest="${MW_DIR}/${f}"
    if [[ -f "${dest}" ]]; then
        echo "  [skip] ${f}"
    else
        echo "  [fetch] ${f}"
        $CURL -o "${dest}" "${MW_BASE}/${f}" || echo "  [WARN] failed: ${f}"
    fi
done

# ---------------------------------------------------------------------------
# 5. pycrossword  (S0mbre/crossword)
# ---------------------------------------------------------------------------
PY_DIR="${OUTPUT_DIR}/pycrossword"
PY_BASE="https://raw.githubusercontent.com/S0mbre/crossword/master"

mkdir -p "${PY_DIR}/pycross"
echo "--- pycrossword ---"

$CURL -o "${PY_DIR}/README.md" "${PY_BASE}/README.md" 2>/dev/null \
    || echo "  [WARN] failed: README.md"

declare -a PY_FILES=(
    "crossword.py"
    "cwordg.py"
    "wordsrc.py"
    "dbapi.py"
    "gui.py"
    "guisettings.py"
    "forms.py"
)
for f in "${PY_FILES[@]}"; do
    dest="${PY_DIR}/pycross/${f}"
    if [[ -f "${dest}" ]]; then
        echo "  [skip] ${f}"
    else
        echo "  [fetch] ${f}"
        $CURL -o "${dest}" "${PY_BASE}/pycross/${f}" || echo "  [WARN] failed: ${f}"
    fi
done

echo ""
echo "==> Done. Sources saved to ${OUTPUT_DIR}/"
echo "    Run scripts/research/process_tool_sources.py to analyze."
