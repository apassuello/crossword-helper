#!/usr/bin/env bash
# Documentation guard. Fails on the two ways this repo's docs rotted before:
#   1. dead relative links
#   2. derivable state asserted in prose (counts, pass rates, "FIXED")
#
# Scope note: archives and the fabrication log are EXCLUDED. Archived docs are
# historical records and are allowed to be stale (charter Rule 2), and
# FABRICATION-LOG.md necessarily quotes the banned strings it exists to document.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

# Marker file: the link check runs its inner loop in a subshell (grep | while),
# so a plain variable would not survive. Clear any stale marker from a prior run.
MARKER=$(mktemp -t docs-check)
trap 'rm -f "$MARKER"' EXIT

EXCLUDE='^(docs/archive/|\.archive/|docs/dev/FABRICATION-LOG\.md)'

live_docs() { git ls-files '*.md' | grep -vE "$EXCLUDE"; }

echo "==> Checking relative links"
while IFS= read -r f; do
  dir=$(dirname "$f")
  # markdown links to relative paths; skip urls, anchors, mailto
  grep -oE '\]\([^)#][^)]*\)' "$f" 2>/dev/null | sed 's/^](//;s/)$//' | while IFS= read -r link; do
    case "$link" in http*|mailto:*|'#'*) continue ;; esac
    target="${link%%#*}"
    [ -z "$target" ] && continue
    if [ ! -e "$dir/$target" ] && [ ! -e "$target" ]; then
      echo "  DEAD LINK  $f -> $link"
      echo "dead" >> "$MARKER"
    fi
  done
done < <(live_docs)

echo "==> Checking for banned derivable-state claims"
# Each pattern is a way of asserting state that goes stale silently.
BANNED=(
  '[0-9]{3,} tests'
  '[0-9]+/[0-9]+ tests passing'
  'Status:[[:space:]]*Complete'
  '✅[[:space:]]*FIXED'
  '\*\*FIXED\*\*'
  '[0-9]+k\+? words'
  '[0-9]+x faster'
)
for pat in "${BANNED[@]}"; do
  while IFS= read -r f; do
    if out=$(grep -nE "$pat" "$f" 2>/dev/null); then
      echo "  BANNED     $f"
      echo "$out" | sed 's/^/               /'
      echo "banned" >> "$MARKER"
    fi
  done < <(live_docs)
done

if [ -s "$MARKER" ]; then
  n=$(wc -l < "$MARKER" | tr -d ' ')
  echo ""
  echo "FAILED: $n documentation issue(s)."
  echo "Fix, or if the number is genuinely needed, print the command that produces it instead."
  exit 1
fi

echo ""
echo "OK: links resolve, no derivable state asserted in prose."
