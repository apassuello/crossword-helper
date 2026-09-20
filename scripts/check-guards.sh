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
#   3. Bundle-reference guard: a def/class deleted from cli/ or backend/ whose
#      name no longer exists anywhere in those trees, while the gitignored
#      research bundle still cites it. Staged mode only. BLOCKS on name
#      extinction only — same-named-method deletion and signature drift are a
#      non-blocking NOTE and remain the re-pin gate's job. See the guard body.
#
# Two modes:
#   (no arguments)  Staged mode. Operates on STAGED blob content
#                   (git show :<file>), never the working tree, so
#                   partially-staged files are checked exactly as they will
#                   be committed. This is what the pre-commit hook runs.
#                   Runs all three guards. Exits 0 immediately if nothing is
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

  # --- Guard 3: a deleted symbol may still be cited by the untracked research bundle ---
  #
  # Why this guard exists. data/research/ and .handoff/ are BOTH gitignored
  # (.gitignore:106, :123). `git grep` sees tracked files only, and the
  # interactive recursive `grep` is a ugrep wrapper that honours .gitignore, so
  # BOTH of the searches a developer reaches for return a clean null on the
  # research bundle -- while applied.html is this repo's canonical design
  # artifact and quotes live code by symbol. A dead-code sweep that counts
  # references therefore cannot see them. That is not hypothetical: 7b0060c
  # deleted SlotIntersectionHelper.get_slot_by_id on a verified zero-reference
  # count; it was applied.html's cp-model evidence, the applied_gate went red on
  # code-symbol and code-verbatim, and b4253fd restored it.
  #
  # What made it load-bearing rather than merely cited: that bare
  # (row, col, direction) lookup is applied.html's evidence that this codebase
  # links its two views WITHOUT a declared channelling constraint -- the premise
  # of the open Beacham-m3-vs-Botea decision. Deleting the symbol deleted the
  # evidence for a question that is still undecided.
  #
  # Rule family: this is the fourth instance of the null-result trap, and the
  # first whose mechanism the global ~/.claude/CLAUDE.md does not cover. That
  # note describes the ugrep-honours-gitignore wrapper and zsh's unmatched-glob
  # abort; this is a third mechanism -- a whole tree ignored, so both searches a
  # developer reaches for agree on the same false null.
  #
  # SCOPE -- read before trusting this guard. It BLOCKS on one condition only:
  # the deleted name has no surviving definition anywhere in cli/ or backend/
  # (name extinction) AND the bundle cites it. Two related breakages are a
  # non-blocking NOTE, not a block, because the name still resolves and this
  # guard cannot tell which definition the bundle meant without parsing:
  #   - deleting a same-named method from a class the bundle cites while other
  #     classes keep the name (6 classes define order_values in one file);
  #   - changing the signature of a quoted function, which breaks code-verbatim.
  # Both remain the re-pin gate's job. Do not read a silent Guard 3 as proof the
  # page is intact.
  #
  # Measured against 7b0060c, the only real instance available: of its 17
  # removed def/class names (dunders excluded; recount 2026-09-20 -- an
  # earlier form of this comment said 18), this rule fires on exactly one -- get_slot_by_id,
  # the symbol that actually had to be restored. Matching the bare identifier
  # instead fires on three: order_values (a surviving LCVValueOrdering method of
  # the same name) and __init__ are false positives, and a citation of a
  # different same-named symbol reads exactly like a true hit.
  bundle="data/research/deep-research-2026-09"
  bundle_paths=("$bundle/README.md" "$bundle/specs" "$bundle/presentation")

  # Dunders are excluded at extraction: a deleted class takes its __init__ with
  # it, and the class name itself is checked separately.
  removed_syms=$(git diff --cached -U0 -- 'cli/*.py' 'backend/*.py' \
    | sed -nE 's/^-[[:space:]]*(async[[:space:]]+)?(def|class)[[:space:]]+([A-Za-z_][A-Za-z0-9_]*).*/\3/p' \
    | grep -vE '^__.*__$' \
    | sort -u || true)

  if [ -n "$removed_syms" ]; then
    if [ ! -d "$bundle" ]; then
      # Deliberately NOT the silent skip Guard 1 uses for .scrub-patterns. A
      # silent skip here would be the very failure this guard exists to fix:
      # searched nothing, found nothing, reported success.
      echo "check-guards: NOTE — Guard 3 scanned NOTHING: research bundle '$bundle' is absent." >&2
      echo "check-guards:        Expected in a worktree or a fresh clone (the bundle is gitignored)." >&2
      echo "check-guards:        This is not a pass. Deleted symbols were NOT checked against applied.html." >&2
    else
      while IFS= read -r sym; do
        [ -z "$sym" ] && continue

        # Citations, excluding the fixture: it is pinned at an old sha and
        # quotes old code on purpose.
        cites=$(grep -rnw -- "$sym" "${bundle_paths[@]}" 2>/dev/null \
                 | grep -v '_build/applied/fixtures/' || true)
        [ -z "$cites" ] && continue

        # Survivors are counted in the INDEX -- what this commit will contain.
        # HEAD still holds the definition being deleted.
        # --cached MUST precede the pattern: after it, git grep parses it as a
        # revision ("fatal: unable to resolve revision: --cached") and the count
        # silently comes back 0 for every symbol -- which makes the guard fire on
        # everything it looks at, a vacuous pass in the opposite direction.
        survivors=$(git grep --cached -hE "^[[:space:]]*(async[[:space:]]+)?(def|class)[[:space:]]+${sym}[[:space:]]*[(:]" \
                      -- cli backend 2>/dev/null | wc -l | tr -d ' ' || true)
        survivors=${survivors:-0}

        cite_files=$(printf '%s\n' "$cites" | cut -d: -f1 | sort -u | sed 's|^|                |')

        if [ "$survivors" -eq 0 ]; then
          echo "BUNDLE-REF GUARD: '$sym' is deleted by this commit and no definition of that name" >&2
          echo "                remains in cli/ or backend/, but the research bundle still cites it:" >&2
          printf '%s\n' "$cite_files" >&2
          echo "                The bundle is gitignored, so git grep and recursive grep are both blind" >&2
          echo "                to it. Restore the symbol, or update the page and re-pin applied_gate.py." >&2
          violations=1
        else
          # Non-blocking: the name still resolves, so the citation probably
          # refers to a survivor. Print the qualified symbols so the developer
          # can tell in one line whether it is theirs.
          quals=$(printf '%s\n' "$cites" | grep -oE 'data-symbol="[^"]*"' \
                   | sed -E 's/data-symbol="([^"]*)"/\1/' | grep -w -- "$sym" | sort -u || true)
          echo "check-guards: NOTE — '$sym' is deleted here, but ${survivors} definition(s) of that name" >&2
          echo "              survive, and the bundle cites the name. Not blocking. Cited as:" >&2
          if [ -n "$quals" ]; then
            printf '%s\n' "$quals" | sed 's|^|                  |' >&2
          else
            printf '%s\n' "$cite_files" >&2
          fi
          echo "              If one of those is the definition you removed, update the page and re-pin." >&2
        fi
      done <<< "$removed_syms"
    fi
  fi

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
