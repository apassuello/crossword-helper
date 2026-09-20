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

# Exclusions for the "does this citation resolve" predicates (Task 3/4 of
# docs/superpowers/plans/2026-09-20-doc-truth-guards.md). Shared by both
# predicates, defined once:
#   E2: a plan under docs/superpowers/plans/ names files it is about to
#       create -- forward reference is what a plan *is*.
#   E3: docs/resources/SOURCES.md is a bibliography indexing *other*
#       codebases; its filenames/identifiers belong to those repos, not this
#       one.
PREDICATE_EXCLUDE='^(docs/superpowers/plans/|docs/resources/SOURCES\.md)'

# Fenced code blocks are stripped before extraction for the citation
# predicates -- a line-based toggle on ``` and ~~~, because grep alone
# cannot track fence state across lines.
strip_fences() {
  awk '
    /^[[:space:]]*(```|~~~)/ { infence = !infence; next }
    !infence { print }
  ' "$1"
}

# Predicate 1: a `backtick-spanned` path-shaped citation must resolve to a
# tracked file. Resolution is git ls-files, never a filesystem check -- see
# the plan's "Implementation requirement" section. A basename living only in
# a sibling worktree, node_modules, or build output must NOT resolve here.
#
# Input is arguments, never an internal enumeration ($@ = paths to scan), so
# --selftest can feed it a fixture invisible to live_docs()'s git ls-files.
check_cited_paths() {
  local exts='py|sh|js|jsx|mjs|ts|tsx|yml|yaml|ini|cfg|toml'
  local anchor="^[A-Za-z0-9_./-]+\\.($exts)\$"
  local f line span inner base
  for f in "$@"; do
    if [[ "$f" =~ $PREDICATE_EXCLUDE ]]; then continue; fi
    while IFS= read -r line; do
      case "$line" in *'docs-check: allow'*) continue ;; esac
      while IFS= read -r span; do
        [ -z "$span" ] && continue
        inner="${span#\`}"; inner="${inner%\`}"
        if [[ "$inner" =~ $anchor ]]; then
          base=$(basename -- "$inner")
          if ! git ls-files -- "*/$base" "$base" | grep -q .; then
            echo "  DEAD PATH  $f: $inner"
            echo "deadpath" >> "$MARKER"
          fi
        fi
      done < <(grep -oE '`[^`]+`' <<<"$line")
    done < <(strip_fences "$f")
  done
}

# Predicate 2: a `backtick-spanned` identifier-shaped citation must resolve
# somewhere in the tracked tree (E5 scope: the whole tree except Markdown --
# not "cli backend"; a name defined in pytest.ini, .pre-commit-config.yaml or
# src/ is a real reference, not a dead one). Resolution is git grep, never a
# filesystem grep -- see the plan's "Implementation requirement" section. A
# symbol surviving only in a stale gitignored .pyc must NOT resolve here.
#
# Input is arguments, never an internal enumeration ($@ = paths to scan), same
# contract as check_cited_paths.
check_cited_identifiers() {
  local anchor='^[a-z_][a-z0-9_]{4,}$'
  local sha_anchor='^[0-9a-f]{7,40}$'
  local f line span inner
  for f in "$@"; do
    if [[ "$f" =~ $PREDICATE_EXCLUDE ]]; then continue; fi
    while IFS= read -r line; do
      case "$line" in *'docs-check: allow'*) continue ;; esac
      while IFS= read -r span; do
        [ -z "$span" ] && continue
        inner="${span#\`}"; inner="${inner%\`}"
        if [[ "$inner" =~ $anchor ]]; then
          [[ "$inner" =~ $sha_anchor ]] && continue   # E4: commit-SHA-shaped token
          if ! git grep -F -q -- "$inner" -- ':!*.md'; then
            echo "  DEAD ID    $f: $inner"
            echo "deadid" >> "$MARKER"
          fi
        fi
      done < <(grep -oE '`[^`]+`' <<<"$line")
    done < <(strip_fences "$f")
  done
}

# --selftest: exercises check_cited_paths against a fixture the normal run
# never sees (live_docs() is git ls-files, blind to a temp file). Covers the
# normative cases from the plan: dead path flags, live path passes, the
# docs-check: allow hatch suppresses, a fenced span is never examined, a glob
# and a shell command are rejected by the anchored charset, and -- the case
# a filesystem-based check would get wrong -- a path that exists on disk but
# is untracked by git still flags.
run_selftest() {
  local tmpdir fixture ghost rc=0 flagged
  tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/docs-check-selftest.XXXXXXXX")
  ghost="cli/src/fill/__selftest_ghost_$$.py"

  cleanup_selftest() { rm -rf "$tmpdir"; rm -f "$ghost"; }
  trap cleanup_selftest RETURN

  : > "$ghost"   # exists on disk, untracked -- must still flag as dead

  fixture="$tmpdir/fixture.md"
  cat > "$fixture" <<EOF
Live path: \`cli/src/fill/autofill.py\`
Dead path: \`cli/src/fill/inverted_index.py\`
Allowed dead path: \`cli/src/fill/inverted_index.py\` <!-- docs-check: allow (selftest) -->
Glob, not a path: \`*.py\`
A command, not a path: \`grep -n 'id:' .pre-commit-config.yaml\`
Untracked-on-disk path: \`$ghost\`

\`\`\`
Fenced dead path, must not be examined: \`cli/src/fill/inverted_index.py\`
\`\`\`
EOF

  : > "$MARKER"
  check_cited_paths "$fixture" > "$tmpdir/out.log" 2>&1
  flagged=$(grep -c '^deadpath$' "$MARKER" 2>/dev/null)
  flagged=${flagged:-0}

  if [ "$flagged" -ne 2 ]; then
    echo "SELFTEST FAILED: expected 2 flags (dead path + untracked-on-disk path), got $flagged"
    echo "--- output ---"
    cat "$tmpdir/out.log"
    rc=1
  else
    echo "SELFTEST OK: check_cited_paths flags dead/untracked-on-disk paths; passes live/glob/command/allowed/fenced"
  fi
  return $rc
}

# --selftest for check_cited_identifiers: covers the normative cases from the
# plan (Task 4) -- a defined identifier passes, the mandatory positive control
# (a name that survives only in a stale gitignored .pyc, not in tracked
# source) flags, a commit-SHA-shaped token is dropped by E4, a config key
# resolves via git grep's whole-tree scope (E5), the docs-check: allow hatch
# suppresses, a fenced span is never examined, and a multi-word span is
# rejected by the anchored single-token regex.
#
# The positive-control identifier is assembled from two literals at runtime,
# never written contiguously in this file: E5's scope is the whole tracked
# tree EXCEPT Markdown, so this .sh file is itself in-scope, and a literal
# occurrence here would make git grep find its own fixture text and silently
# stop the positive control from firing -- the exact failure mode this
# selftest exists to catch.
run_selftest_identifiers() {
  local tmpdir fixture rc=0 flagged ghost_id
  tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/docs-check-selftest-id.XXXXXXXX")
  trap 'rm -rf "$tmpdir"' RETURN

  # Same self-reference hazard as ghost_id: this .sh file is in E5's scope, so
  # the multi-word fixture's fragment word is also assembled at runtime,
  # never written contiguously.
  ghost_id="hamming_distance_at_cross""ings"
  local multiword_frag="undefined_selftest_""phrase"
  fixture="$tmpdir/fixture.md"
  cat > "$fixture" <<EOF
Live identifier: \`canonical_words\`
Positive control, must flag (removed from source, survives only in a stale
gitignored .pyc): \`${ghost_id}\`
SHA-shaped token, dropped by E4: \`cd75876\`
Config key resolved via whole-tree scope (E5): \`testpaths\`
Allowed dead identifier: \`${ghost_id}\` <!-- docs-check: allow (selftest) -->
Multi-word span, rejected by the anchor (the phrase itself is absent verbatim
from the tracked tree -- only the anchor stops the unanchored substring
match from being extracted and searched for):
\`some ${multiword_frag} here\`

\`\`\`
Fenced dead identifier, must not be examined: \`${ghost_id}\`
\`\`\`
EOF

  : > "$MARKER"
  check_cited_identifiers "$fixture" > "$tmpdir/out.log" 2>&1
  flagged=$(grep -c '^deadid$' "$MARKER" 2>/dev/null)
  flagged=${flagged:-0}

  # A bare count is not enough: a mutant that narrows scope (e.g. to "cli
  # backend" instead of the whole tree) can trade one false negative for
  # another and still land on flagged==1, passing for the wrong reason. Assert
  # WHICH identifier flagged, not just how many did.
  if [ "$flagged" -ne 1 ] \
     || ! grep -q "DEAD ID.*${ghost_id}\$" "$tmpdir/out.log" \
     || grep -q "DEAD ID.*testpaths\$" "$tmpdir/out.log" \
     || grep -q "DEAD ID.*${multiword_frag}" "$tmpdir/out.log"; then
    echo "SELFTEST FAILED: expected exactly 1 flag, naming the positive control ($ghost_id); got $flagged"
    echo "--- output ---"
    cat "$tmpdir/out.log"
    rc=1
  else
    echo "SELFTEST OK: check_cited_identifiers flags the positive control; passes live/sha/config/allowed/fenced/multi-word"
  fi
  return $rc
}

if [ "${1:-}" = "--selftest" ]; then
  rc=0
  run_selftest || rc=1
  run_selftest_identifiers || rc=1
  exit $rc
fi

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

echo "==> Checking cited paths resolve"
# git ls-files output has no spaces in this repo; check_cited_paths takes
# paths as $@ by contract (plan Task 3), not a list it enumerates itself, so
# this is the pinned call shape.
# shellcheck disable=SC2046
check_cited_paths $(live_docs)

echo "==> Checking cited identifiers exist"
# Same pinned call shape as check_cited_paths (plan Task 4).
# shellcheck disable=SC2046
check_cited_identifiers $(live_docs)

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
