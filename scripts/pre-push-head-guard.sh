#!/usr/bin/env bash
#
# Refuse a push whose commit is not the checked-out HEAD.
#
# PRIMARY RECORD for this rule. Amend this block, not a copy elsewhere.
#
# Why: the pre-push suites in .pre-commit-config.yaml (pytest-push,
# vitest-push) run on this checkout's working tree, not on the commit being
# pushed. `git -C <main checkout> push origin <other-branch>` therefore reports
# main's result as the branch's. Recorded twice in the handoff log: PR #72's
# hook ran on feat/novice-readiness (2026-10-23), and a Phase 7 push reported
# the checked-out branch's failures (2026-10-25).
#
# Measured before landing (2026-10-29), over the 25 pushes in the
# remote-tracking reflogs, against each worktree's HEAD reflog at push time:
# 24 had a checkout at the pushed sha, so the guard need not fire on them; 1
# had none (fix/pr61-review, PR #72's push, the motivating defect). The
# reflogs do not record which worktree a push ran from, so this bounds false
# positives (0) and does not count every true one.
#
# pre-commit passes the first non-deleted pushed ref's local sha as
# PRE_COMMIT_TO_REF. Unset means a push of a root commit or nothing to push;
# both pass. `^{commit}` peels an annotated tag, so a tag at HEAD passes.
#
# Bypass for one push, deliberately: SKIP=push-head-guard git push ...

set -euo pipefail

to="${PRE_COMMIT_TO_REF:-}"
[ -n "$to" ] || exit 0

pushed=$(git rev-parse --verify --quiet "${to}^{commit}") || exit 0
head=$(git rev-parse HEAD)

if [ "$pushed" != "$head" ]; then
    echo "push-head-guard: pushing ${PRE_COMMIT_LOCAL_BRANCH:-a ref} at ${pushed:0:7}, but HEAD here is ${head:0:7}."
    echo "The pre-push suites test this checkout's tree, so their result would not be about the pushed commit."
    echo "Push from a checkout of that branch (git worktree list shows where it is checked out)."
    exit 1
fi
