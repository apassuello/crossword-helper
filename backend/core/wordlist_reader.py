"""Read the words of a list file by the rules the solver loads lists with.

novice-readiness spec 0.2.12 section 4 (L11, P5): the same line parser
(WordList.parse_line), fold and validity check as WordList.from_file, so
accented words fold, "word,score" lines load, and a word the solver rejects
is rejected here. WordList.from_file is not used because it also builds the
solver's indices and callers here only need the words.

Shared by the Verify/Clean routes (a set) and WordListManager (file order).
"""

from typing import List, Set


def read_wordlist_words_ordered(path) -> List[str]:
    """Words of one list file in file order, each once (first occurrence wins).

    A list that fails while being read contributes the words read before the
    failure, and an unreadable one contributes nothing.
    """
    from cli.src.fill.word_list import WordList

    words: List[str] = []
    seen: Set[str] = set()
    try:
        checker = WordList()
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parsed = WordList.parse_line(line)
                if not parsed:
                    continue
                w = WordList.canonical_word(parsed[0])
                if w not in seen and checker._is_valid_word(w):
                    seen.add(w)
                    words.append(w)
    except Exception:
        pass  # swallow and skip, keeping what was read before the failure
    return words


def read_wordlist_words(path) -> Set[str]:
    """The set of words of one list file (see read_wordlist_words_ordered)."""
    return set(read_wordlist_words_ordered(path))
