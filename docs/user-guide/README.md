# Crossword Helper user guide

For people who want to build crosswords with the Crossword Helper web app. It covers installing the app on a
Mac, building a puzzle, and looking up what each control does. It does not cover changing the software; for
that, see the [contributor documentation](../README.md).

Autofill is known to be imperfect: it can return entries that are not valid words, and some settings can stop
without changing the grid. The guide says so where it matters, and the open issues are listed under
"Known Limitations" in the [project README](../../README.md#known-limitations).

Once the project is on your computer, this guide also opens as a web page with a page list and the same
pictures: open `docs/user-guide/site/index.html` in your browser.

![The Crossword Helper web app with its five areas numbered](images/app-overview.png)

*The app at a glance: (1) the top bar, with the status, Undo, Redo, Verify words, Clean grid and Save grid; (2) the tool rail; (3) the Symmetry switch, the grid's statistics and its violations; (4) the grid; (5) the panel of the tool you picked.*

## Start here

1. [Install Crossword Helper on macOS](how-to/install-on-macos.md): from the GitHub repository to the app open
   in your browser.
2. [Your first crossword](tutorials/first-crossword.md): build, fill, save and export a small puzzle, step by
   step.

## How-to guides

Pick the task you are doing.

| I want to | Guide |
|---|---|
| Start a grid and shape the black squares | [Set up the grid](how-to/set-up-the-grid.md) |
| Keep my work, get it back, undo a mistake | [Save, reopen and recover your work](how-to/save-open-and-recover.md) |
| List the words that fit a pattern like `C?T` | [Find words by pattern](how-to/find-words-by-pattern.md) |
| Add words of my own to the word lists | [Use your own word lists](how-to/use-your-own-word-lists.md) |
| Place and lock theme entries | [Add theme words](how-to/add-theme-words.md) |
| Fill the empty squares automatically | [Autofill a grid](how-to/autofill-a-grid.md) |
| Find and remove entries that are not words | [Check and clean a grid](how-to/check-and-clean-a-grid.md) |
| Load a grid from a file, or save one for printing | [Import and export grids](how-to/import-and-export-grids.md) |
| Fix an error message | [Troubleshoot common problems](how-to/troubleshoot.md) |

## Reference

| Page | Contents |
|---|---|
| [Web app reference](reference/web-app.md) | Every control, option default and key |
| [File formats](reference/file-formats.md) | Grid, theme word and word list files, and the exports |

## Elsewhere in the project

- The command-line tool and the HTTP API are documented for developers in
  [`docs/specs/CLI_SPEC.md`](../specs/CLI_SPEC.md) and
  [`docs/api/API_REFERENCE.md`](../api/API_REFERENCE.md); this guide does not use them.
- [The Art of Crossword Construction](../resources/art-of-construction.pdf): a general reference on
  construction technique.
