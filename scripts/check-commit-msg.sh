#!/usr/bin/env bash
#
# Reject a closing trailer that names only PART of an issue.
#
# PRIMARY RECORD for the partial-closure rule. Amend this block, not a copy
# elsewhere.
#
# Genesis -- D12 of the 2026-08-19 post-M1 audit. Two commits on
# fix/post-m1-issues carried trailers naming a single item of a multi-item
# issue. GitHub's closing keywords ignore the trailing "item N": the issue
# reference is what they bind to, so the whole issue closes. The rebase-merge
# of PR #27 auto-closed #21 with items 2b and 3 unimplemented. The decision
# register had warned about exactly this and prescribed rewording to
# "Part of #NN" before landing; the reword did not happen, and nothing
# mechanical was watching. Reopened 2026-09-13.
#
# What this matches, and what it deliberately does not:
#
#   MATCHES   a closing keyword, an issue number, then the word "item".
#             The fix is to reword the trailer to "Part of #NN (item M)",
#             which references the issue without closing it.
#
#   IGNORES   a bare "Closes #13". That is a legitimate full closure and is
#             the common case -- ten such trailers exist in this history.
#
# Measured before landing, over the full history at 2026-09-20 via
# `git log --format=%B`, per the project rule that a guard is counted before
# it is adopted: 2 true positives, both the D12 commits, and 0 false
# positives. The broader form -- any closing keyword plus an issue number,
# with no "item" requirement -- was rejected on that same measurement. It
# fires on internal numbered fix-lists such as "Fix #5 (lines 1491-1495)"
# and "FIX #1:", which are not issue references at all, and a guard noisy
# enough to distrust only teaches everyone to reach for the escape hatch.
#
# Escape hatch: a line containing "closes-partial: allow". Needed because a
# commit that discusses this rule quotes the string the rule forbids -- this
# script's own landing commit is the first such case.
#
set -euo pipefail

MSG_FILE="${1:?usage: check-commit-msg.sh <commit-msg-file>}"

if [ ! -f "$MSG_FILE" ]; then
  echo "check-commit-msg: no such message file: $MSG_FILE" >&2
  exit 2
fi

if grep -qiE 'closes-partial:[[:space:]]*allow' "$MSG_FILE"; then
  exit 0
fi

PATTERN='(close[sd]?|fix(e[sd])?|resolve[sd]?)[[:space:]]+#[0-9]+[[:space:]]+item'

if grep -niE "$PATTERN" "$MSG_FILE"; then
  cat >&2 <<'MSG'

check-commit-msg: this trailer closes the WHOLE issue, not the item it names.

GitHub binds a closing keyword to the issue number and ignores what follows,
so the line above closes every item of that issue on merge. This is the D12
failure: #21 auto-closed with two items unimplemented.

  reword to:  Part of #NN (item M)

If the message genuinely needs to quote the forbidden form -- a commit about
this rule, for instance -- add a line containing:  closes-partial: allow
MSG
  exit 1
fi

exit 0
