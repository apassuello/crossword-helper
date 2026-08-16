#!/usr/bin/env bash
#
# check-guards.sh — pre-commit guard for the Constructor's Bench port.
#
#   1. Scrub guard: no staged file may contain a personal-content string listed
#      in .scrub-patterns (fixed-string match). .scrub-patterns is gitignored;
#      if it is absent (other clones / CI) the scrub check is skipped silently.
#   2. API-URL confinement: staged files under src/ (excluding src/api/ and
#      src/__tests__/) may not contain axios / fetch( / new EventSource — all
#      endpoint access must live in src/api/.
#
# Operates on STAGED blob content (git show :<file>), never the working tree,
# so partially-staged files are checked exactly as they will be committed.

set -euo pipefail

staged_files=$(git diff --cached --name-only --diff-filter=ACM)

# Nothing staged → nothing to check.
if [ -z "$staged_files" ]; then
  exit 0
fi

violations=0

# --- Guard 1: scrub personal strings (fixed-string, skip if pattern file absent) ---
#
# Two locations are excluded, each because a scrub pattern legitimately lives
# there and a full-blob fixed-string scan would otherwise block every future
# commit touching it (and --no-verify is banned):
#   - .gitignore: the registry of ignored personal files, which NAMES them.
#   - data/wordlists/: public dictionaries contain real answer words that carry
#     a personal pattern as a substring (a longer dictionary word can end with a
#     personal phrase); personal custom wordlists are separately gitignored, so
#     they cannot be committed here regardless.
# This mirrors the URL guard's src/api/ exclusion: each guard skips the one
# place its target strings legitimately live.
if [ -f .scrub-patterns ]; then
  while IFS= read -r file; do
    [ -z "$file" ] && continue
    [ "$file" = ".gitignore" ] && continue
    case "$file" in data/wordlists/*) continue ;; esac
    if git show ":$file" 2>/dev/null | grep -Fqf .scrub-patterns; then
      echo "SCRUB GUARD: staged file '$file' contains a personal-content scrub pattern (.scrub-patterns)." >&2
      violations=1
    fi
  done <<< "$staged_files"
fi

# --- Guard 2: confine API URLs to src/api/ ---
while IFS= read -r file; do
  [ -z "$file" ] && continue
  case "$file" in
    src/api/*|src/__tests__/*) continue ;;  # allowed to contain endpoint access
    # Named legacy exclusions, issue #12. Both files predate this guard and came
    # from main, where it did not exist; because the guard only inspects STAGED
    # files and neither was ever modified on the bench branch, it had never seen
    # them until the main merge staged them. Listed per-file on purpose: every
    # other file under src/, including any new one, is still checked. Remove
    # these two lines when #12 ports them onto src/api/.
    src/components/PatternMatcher.jsx) continue ;;
    src/hooks/useSSEProgress.js) continue ;;
    src/*) ;;                               # in scope
    *) continue ;;                          # not under src/ → out of scope
  esac
  content=$(git show ":$file" 2>/dev/null || true)
  for term in 'axios' 'fetch(' 'new EventSource'; do
    if printf '%s' "$content" | grep -Fq "$term"; then
      echo "API-URL GUARD: staged file '$file' contains '$term' — endpoint access must live in src/api/." >&2
      violations=1
    fi
  done
done <<< "$staged_files"

if [ "$violations" -ne 0 ]; then
  echo "check-guards: commit blocked." >&2
  exit 1
fi

exit 0
