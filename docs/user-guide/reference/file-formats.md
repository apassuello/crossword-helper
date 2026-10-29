# File formats

The files the web app reads or writes. For instructions, see [Import and export grids](../how-to/import-and-export-grids.md),
[Use your own word lists](../how-to/use-your-own-word-lists.md) and [Add theme words](../how-to/add-theme-words.md).

## Grid file (JSON)

Written by `Export` with `JSON (for reimport)` as `crossword.json`; read by the Import tool.

| Key | Type | Meaning |
|---|---|---|
| `size` | number | Rows and columns of the square grid. The importer accepts 3 to 25 |
| `grid` | list of `size` lists of `size` strings | One string per square: `#` black, `.` empty, or a letter A-Z |
| `numbering` | object | Written by `Export`: clue numbers keyed by `"row,col"` (counted from 0). Optional on import |

The importer rejects a missing `size` or `grid`, a size outside the range, a grid that is not `size` rows of
`size` cells, and any cell that is not a string equal to `#`, `.`, an empty string or one letter A-Z. An empty
string is read as an empty square, the same as `.`. The Import tool accepts a `.json` file or pasted text.

```json
{
  "size": 3,
  "grid": [["C", "A", "T"], ["#", ".", "."], [".", ".", "."]],
  "numbering": {}
}
```

## HTML export

Written by `Export` with `HTML (printable)` as `crossword.html`: a single web page headed `Crossword Puzzle`
holding one table. Each white square is a cell showing its clue number (small, top left) and its letter;
each black square is a dark cell. It contains the grid only, with no clues. The page title is fixed.

## Text export

Written by `Export` with `Text (simple)` as `crossword.txt`: a plain-text grid with `■` for black squares.

## Theme word file

A plain text file read by the Theme tool.

| Rule | Detail |
|---|---|
| Entries | One word per line |
| Case | Converted to capitals |
| Duplicates | Dropped, keeping the first |
| Lines with a space, hyphen or digit | Dropped without a message |
| Length | At least 3 letters and no more than the grid size, else reported as an error |
| List size | More than 50 words (`MAX_THEME_WORDS`) is refused. Any one error rejects the whole list |
| File size | Under 1 MB |

## Word list file

A plain text file read by the Lists tool. One entry per line, in any of these forms:

| Form | Example | Meaning |
|---|---|---|
| Bare word | `CAFÉ` | The app calculates a score |
| Semicolon score | `ZEBRA;80` | The word with the score you give |
| Comma score | `quiz,60` | The word with the score you give |

| Rule | Detail |
|---|---|
| Blank lines, lines starting with `#` | Ignored |
| Letters | Only A-Z are kept. Accented letters are folded to plain letters (`CAFÉ` is stored as `CAFE`); a line with a space, hyphen or digit is skipped as `not letters only` |
| Length | A word must be 3 to 21 letters, else it is skipped as `length outside 3-21` |
| Case | Words are stored in capitals |
| Scores | Must be numbers; a line whose score is not a number (such as a `word,score` header) is skipped as `malformed score` |
| Duplicates | The first occurrence is kept |

Uploaded lists are stored as text files under `data/wordlists/custom/` in the project folder. The shipped
lists are read-only.

## Saved grids

`Save grid` does not create a file: saved grids are stored in the browser's local storage for this site (see
[Save, reopen and recover your work](../how-to/save-open-and-recover.md)). To get a file, use `Export`.
