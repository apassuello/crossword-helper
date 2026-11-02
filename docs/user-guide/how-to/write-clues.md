# Write clues

## Goal

Write a clue for each word in your grid, see which clues no longer match their word after you change the
grid, and decide what to do with them. Clues are saved with the grid, undone with it and carried by the JSON
export.

## Prerequisites

- The app is running ([Install on macOS](install-on-macos.md)).
- A grid with at least one white run of two or more squares. Clues belong to those runs, called entries
  here. Squares that start no entry of two or more letters have no row.

## Write a clue

### 1. Open the Clues tool

Click **Clues** in the tool rail, between **Autofill** and **Theme**. The panel is headed `Clues`, with a line
in the form `N across · N down` under it, giving the number of entries in each direction. Below come two groups, `Across · N` and `Down · N`, with one row for
every entry in the grid, in reading order of its first square. A group with no entries says `No across words
yet.` or `No down words yet.`

Each row has the entry's number (`–` before numbering has given it one), one small box for each square (a
letter, or `·` for an empty square) and a field with the placeholder `Write a clue…`.

### 2. Write and commit

Click a row's field and type. Clicking the field, or the row's number, also selects that entry in the grid, so
you can see the word you are writing for. Selecting a square in the grid does the reverse: the row of the entry
under it is highlighted.

A clue is committed, and so saved into the document, when you:

- leave the field (click elsewhere, or press `Tab`),
- press `Enter`, which commits and moves to the next row's field (after the last Across row comes the first
  Down row), or
- switch to another tool.

Press `Escape` instead to throw the draft away and keep the committed text.

What a commit does:

| You committed | Result |
|---|---|
| The same text as before | Nothing. No undo step is added |
| New or changed text | The clue is stored with the entry's letters at that moment. Spaces at either end are dropped |
| An empty field | The clue is removed |
| More than 200 characters | Refused: `At most 200 characters.` shows under the field, the field keeps your text, and focus stays on the row. Shorten it and commit again |

### 3. Save and undo

`Save grid` saves the clues with the grid, and opening that grid brings them back. Each commit that changes a
clue, each `Keep` and each `Delete` is one undo step in the top bar's `Undo`. Typing inside a field is not a
step; while the cursor is in a field, `Cmd+Z` or `Ctrl+Z` undoes the text in the field. Click the grid first to
undo the commit itself.

## Handle stale clues

A clue remembers the letters its entry had when you committed it. When the entry's letters later differ, the
clue is **stale**: it may describe a word that is no longer there. Any change counts, including filling an
empty square and changing the entry's length.

A stale row shows `Written for` and the old letters, with `·` for a square that was empty, and a `Keep`
button. The sub-line under `Clues` gains ` · N stale`.

- Click `Keep` if the clue still fits the new letters. It records the entry's current letters and leaves the
  text alone, and the `Written for` line goes away.
- Rewrite the text and commit it if it does not fit. A committed change also records the current letters.
- Commit the same text again and nothing happens: a stale clue stays stale until you click `Keep` or change
  the text.

### Clues written before the entry was filled

You can clue an entry while it is still empty. The clue remembers an entry of empty squares, so as soon as a
fill puts letters into that entry, whether autofill or your own typing, the clue becomes stale and reads
`Written for ····`. This is intended: a clue that was never checked against its letters should not read as
fine. `Keep` is the review step. Read the clue against the new word, and click `Keep` when it fits.

## Handle orphaned clues

When the entry a clue belongs to stops existing, the clue is **orphaned**, not lost. For example, you made the
entry's first square black, or turned a two-letter entry into one letter. The sub-line gains
` · N orphaned`, and an `Orphaned · N` section appears after the Down group with the line
`These entries no longer exist. Copy a clue into an entry, or delete it.`

Each orphan shows the letters it was written for, its text and a `Delete` button. The text cannot be edited but
can be selected and copied, so you can paste it into a row of a new entry. Click `Delete` to remove the clue;
`Undo` brings it back.

If you undo the change, or an entry starts at that square again, the clue returns to its row on its own.

## While autofill runs

The fields, `Keep` and `Delete` are disabled while an autofill run is going, and the grid shows
`Editing is paused while autofill runs.` The row numbers still select entries.

## Clues in files

- The **JSON** export carries the clues, and the Import tool restores them, orphaned clues included. See
  [Import and export grids](import-and-export-grids.md).
- The **HTML** and text exports hold the grid only, with no clues.
- A grid that has no letters or black squares but has a clue counts as having content: New grid and Import ask
  `Replace the current grid? Unsaved changes are lost.` before replacing it.

## Final Result

Each entry you wrote for shows its clue in the panel, no row reads `Written for` unless you chose to leave it,
and the `Orphaned` section is empty or gone.

## Next Steps

- Every control of the panel: [Web app reference](../reference/web-app.md).
- The `clues` entry of the grid file: [File formats](../reference/file-formats.md).
