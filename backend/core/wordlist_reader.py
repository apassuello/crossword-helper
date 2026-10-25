"""Read the words of a list file by the rules the solver loads lists with.

novice-readiness spec 0.2.12 section 4 (L11, P5): the same line parser
(WordList.parse_line), fold and validity check as WordList.from_file, so
accented words fold, "word,score" lines load, and a word the solver rejects
is rejected here. WordList.from_file is not used because it also builds the
solver's indices and callers here only need the words.

Shared by the Verify/Clean routes (a set) and WordListManager (file order).
"""

from typing import List, Set


def line_key(text: str) -> str:
    """The word a list line or a requested word stands for, as the list shows it.

    novice-readiness spec 0.2.14 section 4 item 1: ``WordList.canonical_word``
    of the word ``WordList.parse_line`` returns, so ``CAFE`` and ``CAFÉ;50``
    share a key, as do ``GRAPE`` and ``grape,40``. A line ``parse_line``
    rejects keeps the old key: its text before ``;``, uppercased.
    """
    from cli.src.fill.word_list import WordList

    text = text.strip()
    parsed = WordList.parse_line(text)
    if parsed:
        return WordList.canonical_word(parsed[0])
    return text.split(";", 1)[0].strip().upper()


def read_wordlist_words_ordered(path, strict: bool = False) -> List[str]:
    """Words of one list file in file order, each once (first occurrence wins).

    By default a list that fails while being read contributes the words read
    before the failure, and an unreadable one contributes nothing (the
    Verify/Clean behaviour). With ``strict`` the error propagates instead, so a
    caller that shows a list as a whole never shows a truncated one.
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
        if strict:
            raise
        # swallow and skip, keeping what was read before the failure
    return words


def read_wordlist_words(path) -> Set[str]:
    """The set of words of one list file (see read_wordlist_words_ordered)."""
    return set(read_wordlist_words_ordered(path))
