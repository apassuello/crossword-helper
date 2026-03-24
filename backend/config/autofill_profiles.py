"""
Autofill algorithm profiles optimized for different grid sizes and use cases.

These profiles provide recommended settings for the autofill algorithms
based on extensive testing with various grid configurations.
"""

# Profile for 21×21 birthday/themed puzzles with 10-20 theme words
BIRTHDAY_21X21_PROFILE = {
    "algorithm": "beam",  # Beam search handles large grids better
    "beam_width": 15,  # Increased from default 5 for better exploration
    "candidates_per_slot": 30,  # More candidates for difficult slots
    "min_score": 25,  # Lower threshold to find more words
    "diversity_bonus": 0.2,  # Encourage diverse solutions
    "timeout": 900,  # 15 minutes max (21×21 takes time)
    "max_attempts_per_slot": 5,  # More retries for stuck slots
    "progressive_fill": True,  # Fill in stages if needed
    "notes": "Optimized for 21×21 grids with 10-20 locked theme words",
}

# Profile for 15×15 standard puzzles
STANDARD_15X15_PROFILE = {
    "algorithm": "beam",
    "beam_width": 10,
    "candidates_per_slot": 20,
    "min_score": 30,
    "diversity_bonus": 0.15,
    "timeout": 300,  # 5 minutes
    "max_attempts_per_slot": 3,
    "progressive_fill": False,
    "notes": "Standard settings for 15×15 daily-style puzzles",
}

# Profile for 11×11 quick puzzles
QUICK_11X11_PROFILE = {
    "algorithm": "csp",  # CSP is faster for small grids
    "beam_width": None,  # Not used for CSP
    "candidates_per_slot": None,
    "min_score": 40,
    "diversity_bonus": None,
    "timeout": 60,  # 1 minute
    "max_attempts_per_slot": None,
    "progressive_fill": False,
    "notes": "Fast fill for small 11×11 grids",
}

# Profile for heavily themed puzzles (many locked entries)
HEAVY_THEME_PROFILE = {
    "algorithm": "hybrid",  # Try beam first, fall back to CSP
    "beam_width": 20,  # Maximum exploration
    "candidates_per_slot": 50,  # Many candidates
    "min_score": 20,  # Very low threshold
    "diversity_bonus": 0.3,
    "timeout": 1200,  # 20 minutes
    "max_attempts_per_slot": 10,
    "progressive_fill": True,
    "use_theme_priority": True,  # Prioritize theme wordlist
    "notes": "For puzzles with 20+ theme words or difficult patterns",
}


def get_profile(grid_size: int, theme_word_count: int = 0, difficulty: str = "medium"):
    """
    Get the recommended autofill profile based on grid characteristics.

    Args:
        grid_size: Size of the grid (11, 15, or 21)
        theme_word_count: Number of theme words to be placed
        difficulty: Expected difficulty ("easy", "medium", "hard")

    Returns:
        Dict with recommended autofill settings
    """
    # Birthday puzzle scenario
    if grid_size == 21 and theme_word_count >= 10:
        return BIRTHDAY_21X21_PROFILE

    # Heavy theming
    if theme_word_count >= 20:
        return HEAVY_THEME_PROFILE

    # Standard cases by size
    if grid_size == 11:
        return QUICK_11X11_PROFILE
    elif grid_size == 15:
        return STANDARD_15X15_PROFILE
    elif grid_size == 21:
        # Regular 21×21 without heavy theming
        profile = BIRTHDAY_21X21_PROFILE.copy()
        profile["timeout"] = 600  # 10 minutes for non-themed
        profile["beam_width"] = 10
        return profile

    # Default fallback
    return STANDARD_15X15_PROFILE


def apply_profile_to_options(options: dict, profile: dict):
    """
    Apply a profile's settings to an options dictionary.

    Args:
        options: Current options dict
        profile: Profile to apply

    Returns:
        Updated options dict
    """
    for key, value in profile.items():
        if key != "notes" and value is not None:
            options[key] = value
    return options
