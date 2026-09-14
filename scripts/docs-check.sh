#!/usr/bin/env bash
# Documentation guard. Fails on the two ways this repo's docs rotted before:
#   1. dead relative links
#   2. derivable state asserted in prose (counts, pass rates, "FIXED")
#
# Scope note: archives, the fabrication log and imported research reports are
# EXCLUDED. Archived docs are historical records and are allowed to be stale
# (charter Rule 2); FABRICATION-LOG.md necessarily quotes the banned strings it
# exists to document; and docs/resources/research/ holds verbatim reports of
# external literature whose figures describe that literature's scope, not this
# repo's state. Those reports are also mirrored in the gitignored research
# bundle, so editing them here to satisfy a guard would fork the two copies.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

# Marker file: the link check runs its inner loop in a subshell (grep | while),
# so a plain variable would not survive. Clear any stale marker from a prior run.
MARKER=$(mktemp "${TMPDIR:-/tmp}/docs-check.XXXXXXXX")
trap 'rm -f "$MARKER"' EXIT

EXCLUDE='^(docs/archive/|\.archive/|docs/resources/research/|docs/dev/FABRICATION-LOG\.md)'

live_docs() { git ls-files '*.md' | grep -vE "$EXCLUDE"; }

# Source comments are documentation too. The 2026-08 audit found the SAME false
# figure ("454k words") in cli/ docstrings as in the docs, which is why checking  # docs-check: allow (names the banned figure to explain the rule)
# docs against code silently failed - see docs/dev/FABRICATION-LOG.md. Only the
# banned-claim check runs over these; the link check stays markdown-only.
#
# Defined by EXCLUSION, deliberately. This function used to read
#   git ls-files '*.py' | grep -E '^(cli|backend)/'
# and that shape is the repo's third recorded instance of a filter that
# enumerates what it covers and so goes stale in silence - after pytest.ini's
# testpaths and the pre-commit ruff hook. It cost two real misses: scripts/ and
# src/ were never scanned at all (src/components/PatternMatcher.jsx asserted a
# speedup that matches a BANNED pattern exactly and was never fed to it), and
# globbing '*.py' missed cli/crossword and cli/cli/crossword, which are tracked
# Python scripts with no extension - found only because pre-commit detects them
# by shebang. An exclusion cannot orphan a new file; an include list always can.
#
# .handoff/ is out of scope BY DESIGN, not by oversight: it is gitignored, so
# git ls-files cannot reach it either way, and its entries are dated records
# whose Build: fields assert test counts as their whole purpose. See
# CONTRIBUTING.md section 4.
# docs/resources/research/ is excluded here for the same reason EXCLUDE carries
# it: those files are imported verbatim from external papers, so a banned string
# inside one is a quotation nobody may edit. 786d369 added it to EXCLUDE and not
# to CODE_EXCLUDE, and the gap stayed invisible only because live_code() then
# scanned three extensions, none of which it matched.
CODE_EXCLUDE='^(docs/archive/|\.archive/|data/research/|docs/resources/research/)'
live_code() {
  git ls-files | grep -vE "$CODE_EXCLUDE" | while IFS= read -r f; do
    case "$f" in
      # The ONLY filter is this skip list, and it holds formats with no prose to
      # check: rendered/binary assets, lockfiles, and *.md (live_docs already
      # yields those). Everything else is scanned.
      #
      # This case statement used to read `*.py|*.js|*.jsx) echo` first, with a
      # `*)` arm that echoed a file only if its first line was a python shebang.
      # That made the whole function an include list one layer below the one this
      # comment claims to have abolished: a .sh, .ts or .rs file matched neither
      # arm, failed the shebang test, and was never scanned. Measured cost: the
      # guard's own source violated it -- scripts/docs-check.sh:26 quotes the
      # "454k words" figure, matches BANNED, and passed for as long as the include  # docs-check: allow (names the banned figure to explain the rule)
      # list existed. Inverting is a strict superset, 209 files -> 326.
      *.md|*.pdf|*.png|*.jpg|*.jpeg|*.gif|*.ico|*.pkl|*.lock|*.woff|*.woff2|*.ttf) ;;
      *) [ -f "$f" ] && echo "$f" ;;
    esac
  done
}

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
  '[0-9]+[x×] faster'
  '[0-9]+[-–][0-9]+[x×] (faster|speedup)'
  # Coverage percentages, both orders. Anchored on the vocabulary rather than on
  # '%' alone: a bare percent pattern fires on black-square density, fill
  # thresholds, timeout ratios and URL-encoded badge links, none of which go
  # stale, and a guard with that many false positives just teaches everyone to
  # reach for the escape hatch.
  '(coverage|covered|pass rate)[^0-9]{0,40}[0-9]+(\.[0-9]+)?[[:space:]]*%'
  '[0-9]+(\.[0-9]+)?[[:space:]]*%[^0-9]{0,40}(coverage|covered|pass rate)'
)
# Escape hatch: a line containing "docs-check: allow" is exempt. Needed for lines
# that legitimately quote a banned string - the contributing guide documenting the
# rule, or a complexity discussion citing a capacity rather than a stale count.
# Deliberately per-line and greppable, so every exemption stays auditable. Use a
# pathspec-free enumeration -- the guard no longer scans only .md and .py, and an
# audit command that names extensions is the same include list this file just
# stopped using:
#   git ls-files | xargs grep -n "docs-check: allow\" 
for pat in "${BANNED[@]}"; do
  while IFS= read -r f; do
    if out=$(grep -InE "$pat" "$f" 2>/dev/null | grep -v 'docs-check: allow'); then
      echo "  BANNED     $f"
      echo "$out" | sed 's/^/               /'
      echo "banned" >> "$MARKER"
    fi
  done < <(live_docs; live_code)
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
