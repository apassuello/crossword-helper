"""
Crosswordese dictionary and acceptance policy.

PHASE 2.1 - Research Gap #8: Crosswordese Acceptance Policy

Crosswordese = words that appear frequently in crosswords but rarely in speech.

Research (Will Shortz, NYT Crossword Construction Guidelines):
- Short words (3-4 letters): Crosswordese acceptable as "glue"
- Medium words (5-6 letters): Crosswordese discouraged but tolerated
- Long words (7+ letters): Crosswordese completely unacceptable

Examples:
- ESNE (archaic "to be") - OK at 4 letters, terrible at 8
- ALOE (plant, overused) - OK at 4 letters, bad at 7+
- OREO (cookie, overused) - OK at 4 letters, bad at 7+
"""

from typing import Set


# Common 3-letter crosswordese
CROSSWORDESE_3: Set[str] = {
    # Compass directions
    'ESE', 'ENE', 'SSE', 'SSW', 'NNE', 'NNW', 'WSW', 'WNW',
    # Common short words
    'ERA', 'ERE', 'ORE', 'ATE', 'OLE', 'ETA', 'IRE', 'ODE',
    # Names
    'ALI', 'ARI', 'ELI', 'IRA', 'IDA', 'AVA', 'EVA', 'ELI',
    'ANN', 'EVE', 'MAE', 'RAE', 'ZOE',
    # Misc
    'AWE', 'EEL', 'ERR', 'OAR', 'ORB', 'OPT', 'AWL'
}

# Common 4-letter crosswordese
CROSSWORDESE_4: Set[str] = {
    # Very common
    'ESNE', 'ALOE', 'OLEO', 'OREO', 'ARIA', 'ERNE', 'ALEE', 'ASEA',
    'EPEE', 'OLIO', 'AGAR', 'AGRA', 'AGIO', 'AGUE', 'AVER', 'AVOW',
    # Names
    'EERO', 'OMAR', 'OTIS', 'EDNA', 'ETTA', 'EZRA', 'ELIA', 'ENID',
    # Common patterns
    'ANTE', 'ANON', 'AJAR', 'ABET', 'ALES', 'AMPS', 'ARCS', 'ARES',
    'ASPS', 'ELLS', 'EROS', 'ERRS', 'ETAS', 'EWES', 'IBIS', 'ICES',
    'ODES', 'OARS', 'OKRA', 'OLES', 'OMEN', 'ONER', 'ONES', 'OPTS',
    'ORES', 'ORBS', 'OWES', 'OWLS'
}

# Common 5-letter crosswordese
CROSSWORDESE_5: Set[str] = {
    'ENURE', 'INURE', 'ARETE', 'ANISE', 'ELATE', 'ERATO', 'ARIEL',
    'OSIER', 'OTERO', 'STERE', 'ESSES', 'EDGER', 'ALLEE', 'AREAE',
    'ATONE', 'ANEAR', 'EELER', 'OATER', 'OARED', 'REATA', 'OASES',
    # Names
    'ALAMO', 'ARIES', 'EARLE', 'ELIOT', 'ENLAI', 'ERNIE', 'ESTES'
}

# Combine all crosswordese
CROSSWORDESE_ALL: Set[str] = CROSSWORDESE_3 | CROSSWORDESE_4 | CROSSWORDESE_5


def is_crosswordese(word: str) -> bool:
    """
    Check if word is crosswordese.

    Args:
        word: Word to check (will be uppercased)

    Returns:
        True if word is in crosswordese dictionary
    """
    return word.upper() in CROSSWORDESE_ALL


def get_crosswordese_penalty(word: str, length: int) -> float:
    """
    Get penalty multiplier for crosswordese word based on slot length.

    Crosswordese acceptance policy:
    - 3-4 letters: Acceptable (penalty = 1.0, no filtering)
    - 5-6 letters: Discouraged (penalty = 0.5, heavily penalized)
    - 7+ letters: Unacceptable (penalty = 0.0, completely filtered out)

    Args:
        word: Word to check (will be uppercased)
        length: Slot length (not word length - use slot length for consistency)

    Returns:
        Penalty multiplier:
        - 1.0 if not crosswordese or acceptable length
        - 0.5 if crosswordese at medium length (discouraged)
        - 0.0 if crosswordese at long length (unacceptable - will be filtered)

    Example:
        >>> get_crosswordese_penalty("ESNE", 4)
        1.0  # OK at 4 letters
        >>> get_crosswordese_penalty("ESNE", 6)
        0.5  # Discouraged at 6 letters
        >>> get_crosswordese_penalty("ESNE", 8)
        0.0  # Unacceptable at 8 letters (filtered)
    """
    if not is_crosswordese(word):
        return 1.0  # Not crosswordese, no penalty

    # Crosswordese word - apply length-based policy
    if length <= 4:
        return 1.0   # Acceptable for short slots (glue words)
    elif length <= 6:
        return 0.5   # Discouraged for medium slots (penalized)
    else:  # 7+ letters
        return 0.0   # Unacceptable for long slots (filtered out)


def filter_crosswordese(
    candidates: list,
    slot_length: int
) -> list:
    """
    Filter candidates to remove unacceptable crosswordese for given slot length.

    Args:
        candidates: List of (word, score) tuples
        slot_length: Length of slot being filled

    Returns:
        Filtered list with penalties applied:
        - Unacceptable crosswordese removed (penalty = 0.0)
        - Discouraged crosswordese score reduced by 50%
        - Acceptable words unchanged

    Example:
        >>> candidates = [("ESNE", 50), ("ARENA", 60), ("TEST", 70)]
        >>> filter_crosswordese(candidates, slot_length=4)
        [("ESNE", 50), ("ARENA", 60), ("TEST", 70)]  # All OK at 4 letters

        >>> filter_crosswordese(candidates, slot_length=8)
        [("ARENA", 60), ("TEST", 70)]  # ESNE filtered at 8 letters
    """
    filtered = []

    for word, score in candidates:
        penalty = get_crosswordese_penalty(word, slot_length)

        if penalty > 0:  # Only include if not completely filtered
            adjusted_score = int(score * penalty)
            filtered.append((word, adjusted_score))

    return filtered


def get_crosswordese_stats(words: list) -> dict:
    """
    Get statistics about crosswordese usage in word list.

    Args:
        words: List of words to analyze

    Returns:
        Dictionary with statistics:
        - total_words: Total word count
        - crosswordese_count: Number of crosswordese words
        - crosswordese_percentage: Percentage of crosswordese
        - examples: List of crosswordese words found
    """
    crosswordese_found = [w for w in words if is_crosswordese(w)]

    return {
        'total_words': len(words),
        'crosswordese_count': len(crosswordese_found),
        'crosswordese_percentage': len(crosswordese_found) / len(words) * 100 if words else 0,
        'examples': crosswordese_found[:10]  # First 10 examples
    }
