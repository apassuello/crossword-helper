# Add theme words

## Goal

Load your theme words, place them in the grid, and lock them so autofill keeps them. Use this when your puzzle
has set entries (a theme, names, a date) that must survive the fill.

## Prerequisites

- The app is running and a grid is open, with the black squares you want
  ([Set up the grid](set-up-the-grid.md)). The panel reads the current grid size, so choose the size first.
- A plain text file with one theme word per line.

## Steps

### 1. Prepare the theme file

One word per line, letters only. The app converts words to capitals and drops duplicates. A line that
contains a space, hyphen or digit is dropped without a message, so write `ICECREAM`, not `ICE CREAM`. A word
shorter than 3 letters, or longer than the grid is wide, is reported as an error, and a very long list is
refused (the limit is `MAX_THEME_WORDS` in `backend/core/theme_placer.py`). The file must be under 1 MB.

### 2. Load the words

Open the **Theme** tool in the left rail. In `Upload Theme Words`, click `Choose File` and pick your file.

The app validates the list. If something is wrong, it shows an error toast starting `Invalid theme words:` and
lists each problem. If the list is valid, it reports `Loaded N theme words` and immediately works out where
each word could go. The words appear under `Loaded Words`.

### 3. Place the words

The `Placement Suggestions` section lists each word with its candidate positions. Hovering over a suggestion
previews it on the grid. Click `Apply` on a suggestion to place and lock that word.

To place everything at once, click `Apply All Best Placements`. It applies each word's best suggestion in
turn and skips a word that has no valid placement or whose best placement conflicts with something already in
the grid; the skipped words are listed with the reason. Positions shown in the panel are counted from 1, like
the labels on the grid.

### 4. Know what a lock does

A placed theme word is theme-locked: its squares show a small coloured corner, you cannot overwrite them by
typing or clear them with `Backspace`, you cannot make one of them black, `Clean grid` leaves them alone, and
autofill treats them as fixed.

If you change the grid so a suggestion no longer fits, the suggestions are refreshed for the changed grid.

## Final Result

The theme words are in the grid, marked as locked, and they are still there after an autofill.

## Known problems

- `Apply All Best Placements` can count a word you already placed by hand in its summary.
- A JSON export keeps letters and black squares but not which words are theme-locked, so after importing it the
  theme words can be overwritten. `Save grid` keeps the locks.

Both are tracked under "Known Limitations" in the [README](../../../README.md).

## Next Steps

- Fill around the theme: [Autofill a grid](autofill-a-grid.md).
- The theme word file: [File formats](../reference/file-formats.md).
