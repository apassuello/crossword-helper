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
#   MATCHES   a closing keyword, an issue reference, then the word "item"
#             after any run of space or light punctuation. The reference may
#             be #NN, owner/repo#NN, or a full github.com/.../issues/NN URL --
#             all three are documented closing forms. "Closes #21 (item 2)",
#             "Closes #21, item 2" and "Closes #21 - item 2" are all caught:
#             the first version required a bare space before "item" and let
#             an author who followed the suggested "(item M)" form but kept
#             the keyword straight through, still closing the whole issue.
#             The fix is to reword to "Part of #NN (item M)", which
#             references the issue without closing it.
#
#   JOINS     single line breaks inside a paragraph before matching, so an
#             editor reflow that puts "item" on the next line is still seen.
#             Blank lines stay paragraph breaks, so a bare "Closes #13" whose
#             NEXT PARAGRAPH happens to begin with "item" is not joined to it.
#             CR is stripped first, so CRLF bodies behave the same.
#
#   IGNORES   a bare "Closes #13". That is a legitimate full closure and is
#             the common case -- ten such trailers exist in this history.
#             "GH-NN" is not matched: GitHub does not treat it as a closing
#             reference, so nothing is closed by it.
#
# Measured before landing, over the full history via
# `git log --format='%x1e%B'` record by record with the same normalisation,
# per the project rule that a guard is counted before it is adopted: 380
# commit bodies scanned, 2 hits, both of them the D12 commits named above,
# 0 false positives -- the same count the narrower first version scored, with
# a strictly wider net. Ten bare closures in that history are untouched by
# either. The broadest form --
# any closing keyword plus an issue number, no "item" requirement -- was
# rejected on the first measurement: it fires on internal numbered fix-lists
# such as "Fix #5 (lines 1491-1495)" and "FIX #1:", which are not issue
# references at all, and a guard noisy enough to distrust only teaches
# everyone to reach for the escape hatch.
#
# Escape hatch: a line containing "closes-partial: allow". Needed because a
# commit that discusses this rule quotes the string the rule forbids.
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

KW='(close[sd]?|fix(e[sd])?|resolve[sd]?)'
REF='(([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?#[0-9]+|https?://github\.com/[^/[:space:]]+/[^/[:space:]]+/issues/[0-9]+)'
SEP='[[:space:](),:;-]+'
PATTERN="${KW}[[:space:]]+${REF}${SEP}item"

# Paragraph-join: within a paragraph, newlines become spaces; blank lines are
# kept as record separators by awk's paragraph mode (RS="").
normalised=$(tr -d '\r' < "$MSG_FILE" | awk 'BEGIN{RS="";ORS="\n\n"}{gsub(/\n/," ");print}')

if printf '%s\n' "$normalised" | grep -qiE "$PATTERN"; then
  # Point at the line that carries the closing reference itself.
  grep -niE "${KW}[[:space:]]+${REF}" "$MSG_FILE" >&2 || true
  cat >&2 <<'MSG'

check-commit-msg: this trailer closes the WHOLE issue, not the item it names.

GitHub binds a closing keyword to the issue reference and ignores what
follows, so the line above closes every item of that issue on merge. This is
the D12 failure: #21 auto-closed with two items unimplemented.

  reword to:  Part of #NN (item M)

If the message genuinely needs to quote the forbidden form -- a commit about
this rule, for instance -- add a line containing:  closes-partial: allow
MSG
  exit 1
fi

exit 0
