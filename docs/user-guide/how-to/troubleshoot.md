# Troubleshoot common problems

## Goal

Match a message or symptom you see while installing or using the app to its cause and fix. Every message below
is quoted from the app or its setup scripts.

## Installing and starting

### Setup stops with a line starting `Missing:`

A required tool is not installed or is too old. The line names the tool and where to get it, for example
`Missing: node 18 or later — install from https://nodejs.org`. Install it and run `./setup.sh` again. The
script stops before it creates anything when a tool is missing.

### Setup prints `Install python3-venv (for example: sudo apt install python3-venv), then run ./setup.sh again`

Your Python cannot create a virtual environment (this happens on Debian and Ubuntu systems). Install the
package the message names, then run `./setup.sh` again.

### Setup prints `Error: npm ci failed (output above). ...`

The JavaScript packages did not install. Read the npm output printed above that line, check your network
connection, and run `./setup.sh` again.

### `run.py` prints `Port 5000 is in use. Start with PORT=<other> python3 run.py`

Another program is using port 5000. Start the app on a different port and open that address:

```bash
PORT=5001 python3 run.py
```

### The browser shows "Development Mode — The frontend hasn't been built yet"

The web interface was not built. Run `./setup.sh` again (it builds the interface), or run `npm run build` in the
project folder, then restart `python3 run.py`.

## While using the app

### The top bar says `offline`

The app cannot reach its backend. Look at the terminal where `python3 run.py` is running: if it has stopped or
shows an error, start it again and reload the page. While the status is `offline`, `Verify words` and
`Clean grid` are disabled.

### The top bar says `degraded`

The backend is running but reports that part of itself is unhealthy. Restart `python3 run.py`; if it persists,
check the terminal for errors.

### Autofill finished but the grid did not change

For some endings the grid shows its pre-run state until you click a `Keep` button. See the outcome table in
[Autofill a grid](autofill-a-grid.md). If the run ended with a message about highlighted letters, the red
squares are letters already in the grid that no word fits; change them and run again.

### Autofill's result has entries that are not words

Autofill is known to be imperfect. Use `Verify words` and `Clean grid`
([Check and clean a grid](check-and-clean-a-grid.md)), or run autofill again; results differ from run to run.
Open issues are listed under "Known Limitations" in the [README](../../../README.md).

### A save fails: `Could not save: browser storage is full. Delete a saved grid or export this one.`

The browser's storage for this site is full. Delete saved grids you no longer need (`Open saved`, then
`Delete`) or export the grid ([Import and export grids](import-and-export-grids.md)).

### A word list upload is refused

The upload preview reports how many lines were skipped and why. If no line is valid the upload is refused. See
[Use your own word lists](use-your-own-word-lists.md) for what a valid line is. The shipped lists cannot be
overwritten or deleted; the app tells you to create a custom list instead.

### A theme word file is rejected

The toast starts `Invalid theme words:` and the panel lists each problem: a word that is too short (under 3
letters), longer than the grid, or contains non-letters. A file over 1 MB is refused with
`File too large (max 1MB)`. See [Add theme words](add-theme-words.md).

### An import is rejected

The message says which part of the file is wrong, for example `Invalid file type. Please select a .json file.`
or `Grid row 2 has 14 cells, expected 15`. See [Import and export grids](import-and-export-grids.md) for the
format.

## Final Result

The message you saw no longer appears, or you know which step to change.

## Next Steps

- Everything the app offers: [Web app reference](../reference/web-app.md).
