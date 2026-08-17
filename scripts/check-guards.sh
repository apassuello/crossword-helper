#!/usr/bin/env bash
#
# check-guards.sh — guard for the Constructor's Bench port.
#
#   1. Scrub guard: no staged file may contain a personal-content string listed
#      in .scrub-patterns (fixed-string match). .scrub-patterns is gitignored;
#      if it is absent (other clones / CI) the scrub check is skipped silently.
#      Staged mode only — this guard is inherently about diffs of personal
#      content, not a static tree property.
#   2. API-URL confinement: files under src/ (excluding src/api/ and
#      src/__tests__/) may not contain axios / fetch( / new EventSource — all
#      endpoint access must live in src/api/.
#
# Two modes:
#   (no arguments)  Staged mode. Operates on STAGED blob content
#                   (git show :<file>), never the working tree, so
#                   partially-staged files are checked exactly as they will
#                   be committed. This is what the pre-commit hook runs.
#                   Runs both guards. Exits 0 immediately if nothing is
#                   staged.
#   --full-tree     Full-tree mode. Enumerates every tracked file under src/
#                   (git ls-files 'src/*') and reads it from the working
#                   tree. Covers Guard 2 only — Guard 1 is a diff property
#                   and has no full-tree equivalent. This is what CI runs,
#                   to catch a Guard-2 violation sitting in a file nobody
#                   staged this commit.
#
# The Guard 2 exclusion list and forbidden-term list are defined once
# (in_api_url_scope() and api_url_terms below) and shared by both modes; only
# the file enumeration and content retrieval differ between them.

set -euo pipefail

usage() {
  echo "Usage: $0 [--full-tree]" >&2
  exit 1
}

mode="staged"
case "$#" in
  0) ;;
  1)
    case "$1" in
      --full-tree) mode="full-tree" ;;
      *) usage ;;
    esac
    ;;
  *) usage ;;
esac

# Both modes resolve paths relative to the repository root: git pathspecs and the
# .scrub-patterns lookup are cwd-relative, so a run from a subdirectory would
# enumerate nothing and exit 0 with a real violation sitting in the tree — the
# same vacuous pass --full-tree exists to abolish. Verified: from backend/,
# `git ls-files 'src/*'` returns 0 files.
cd "$(git rev-parse --show-toplevel)"

violations=0

# --- Guard 2 shared definition: exclusion list + forbidden terms ---
api_url_terms=('axios' 'fetch(' 'new EventSource')

in_api_url_scope() {
  case "$1" in
    src/api/*|src/__tests__/*) return 1 ;;  # allowed to contain endpoint access
    src/*) return 0 ;;                      # in scope
    *) return 1 ;;                          # not under src/ -> out of scope
  esac
}

if [ "$mode" = "staged" ]; then
  staged_files=$(git diff --cached --name-only --diff-filter=ACM)

  # Nothing staged → nothing to check.
  if [ -z "$staged_files" ]; then
    exit 0
  fi

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

  # --- Guard 2: confine API URLs to src/api/ (staged blob content) ---
  while IFS= read -r file; do
    [ -z "$file" ] && continue
    in_api_url_scope "$file" || continue
    content=$(git show ":$file" 2>/dev/null || true)
    for term in "${api_url_terms[@]}"; do
      if printf '%s' "$content" | grep -Fq "$term"; then
        echo "API-URL GUARD: staged file '$file' contains '$term' — endpoint access must live in src/api/." >&2
        violations=1
      fi
    done
  done <<< "$staged_files"

else
  # --- Guard 2 only: confine API URLs to src/api/ (full working tree) ---
  tracked_src=$(git ls-files 'src/*')

  # An empty enumeration is never a pass. If src/ is renamed or the pathspec
  # stops matching, every future run would report success while scanning
  # nothing — a guard that cannot fail.
  if [ -z "$tracked_src" ]; then
    echo "check-guards: --full-tree found no tracked files under src/ — refusing to report a vacuous pass." >&2
    exit 1
  fi

  while IFS= read -r file; do
    [ -z "$file" ] && continue
    in_api_url_scope "$file" || continue
    # git ls-files reads the index; a file deleted from the working tree but
    # not yet staged would still be listed here. Skip it rather than let a
    # missing-file grep abort the scan under set -e.
    [ -f "$file" ] || continue
    for term in "${api_url_terms[@]}"; do
      if grep -Fq "$term" -- "$file"; then
        echo "API-URL GUARD: file '$file' contains '$term' — endpoint access must live in src/api/." >&2
        violations=1
      fi
    done
  done <<< "$tracked_src"
fi

if [ "$violations" -ne 0 ]; then
  if [ "$mode" = "staged" ]; then
    echo "check-guards: commit blocked." >&2
  else
    echo "check-guards: full-tree scan found violations." >&2
  fi
  exit 1
fi

exit 0
