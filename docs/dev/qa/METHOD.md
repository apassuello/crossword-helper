# QA Run and Browser Drive Method

**Version 1.0.0** · 2026-10-29
**Document Type:** Method for acceptance runs and for driving the app in a browser to verify a change

---

## AI READING INSTRUCTION

Read `[SPEC]` and `[BUG]` blocks for authoritative facts.
Read `[NOTE]` only if additional context is needed.
`[?]` blocks are unverified.

Each rule below was learned in a run and names it. The run logs in this directory are the evidence;
`2026-10-26-novice-readiness-run.md` is the reference for format and case blocks.

---

## 1. Running an acceptance pass

**[SPEC]**
- **Stop only on a serious FAIL**: data loss, crash, 5xx, dead end, broken guard. Record a nit as a
  FAIL (nit) or an Observation and keep going (owner, 2026-10-26).
- **Cap scripted API calls per row at 20.** An unthrottled word-set search against the shared QA
  server voided TH3's request count in the 2026-10-26 run.
- **Pick a fixture by dry-running the stateless API** (`/api/theme/suggest-placements`, then
  `/api/theme/apply-placement`), not the browser. It leaves the test origin's storage untouched.
- **5xx counts come from the server's request log**, with the browser tool's count beside it. The
  browser tool logged a 503 for an SSE request the server answered 200 (F-TOUR, 2026-10-26).
- **A cloud session is a clean Linux VM with Python and Node preinstalled, not a clean macOS.**
  Acceptance for a macOS user runs on a Mac under `env -i` (spec 0.2.20 §6).

**[BUG] An install check that counts a pip log line is vacuous under `pip --quiet`.** `setup.sh`
installs quietly, so the line is never printed and the count is 0 whether the install worked or not.
Use `pip install --dry-run --only-binary=:all:` with an sdist-only control package.

**[BUG] A read route used as an oracle can change what it measures.** In the 2026-10-22 run the
readback of `get_wordlist_info` wrote into stored metadata and supplied the evidence for a false claim
(#48); it returns a copy since. Read a route's code for side effects before treating it as read-only.

---

## 2. The browser and its tools

**[SPEC]**
- **Drive in a tab you created, on a port nobody else uses.** Never use `localhost:5000` for scratch
  work: it can hold the owner's restored grid, and autosave writes to it. Serve the build under test
  with `PORT=<free port> python3 run.py` from its worktree. A shared tab contaminates a drive
  invisibly; the server request log is what shows another person's clicks, so check it for requests
  you did not make.
- **Start console and network capture before a row's first action.** The browser tool records them
  only after its first read on a tab.
- **Before a drive, grep `src` for `window.confirm|alert|prompt` (with `-P`).** A native dialog blocks
  the extension. Stub it at that one click and paste the captured message into the evidence.
- **A download-dependent row needs the owner's manual click, not a FAIL.** After a tab's first
  download, the tool's automated `Export` clicks save no file (F-EXPORT, 2026-10-26).
- **Back up page `localStorage` through a local POST receiver** into the evidence directory: no
  download prompt, and nothing large passes through the tool's output.
- **Clear the test origin's storage and stop the server when the drive ends.**

---

## 3. Reading what the app did

**[SPEC]**
- **Read React state from the root container's current fiber**, never from a DOM node's
  `__reactFiber` `memoizedProps`. That fiber can be the stale alternate, one render behind; it
  produced phantom undo steps until a screenshot refuted them.
- **An undo trail cannot show a misattributed write**: undo restores snapshots, so buggy and fixed
  code print the same trail. Mark the suspect write with a sentinel letter and pair it with a control
  where the write must appear.
- **Exercise a Web Locks race by holding the lock from a second tab**:
  `navigator.locks.request(name, () => new Promise(r => window.__release = r))`. Waiting for a
  window of a few milliseconds never hits it.

**[SPEC] Layout checks: hit-test in a sized iframe, with a forced-defect control.** jsdom has no box
model (`CONTRIBUTING.md` §3), so layout is verified in the browser. Load the app in a same-origin
iframe sized exactly 1024×768 and 1440×900 (ENV-3 of the run logs), then call `elementFromPoint` at
the centre of each control and check the target is topmost. A green hit-test proves nothing until the
same probe, with the defect forced back (for example an inline style restoring the old `z-index`),
reports the control as covered. #93 was verified this way.

**[BUG] `elementFromPoint` sees through `pointer-events: none`.** The toast stack sets it, so a
hit-test reports whatever is under a toast. Set `pointer-events: auto` on the element and its
children for the probe, then restore it.
