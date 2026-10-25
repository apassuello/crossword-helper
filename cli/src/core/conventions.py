"""
Crossword entry convention normalization.

This module handles conversion of multi-word entries according to standard
crossword puzzle conventions (e.g., "Tina Fey" → "TINAFEY").
"""

import re
from typing import Dict, List, Tuple

from ..fill.word_list import fold_letters


class ConventionHelper:
    """Normalizes crossword entries according to standard conventions."""

    # Convention rules (checked in order)
    RULES = {
        "two_word_names": {
            "pattern": r"^[A-Z][a-z]+ [A-Z][a-z]+$",
            "transform": lambda s: s.replace(" ", "").upper(),
            "description": "Two-word proper names: remove space, capitalize all",
            "explanation": "Proper names with two words are joined without spaces",
            "examples": [
                ("Tina Fey", "TINAFEY"),
                ("Tracy Jordan", "TRACYJORDAN"),
                ("Real Madrid", "REALMADRID"),
            ],
        },
        "title_with_article": {
            "pattern": r"^(La|Le|The|A|An) ",
            "transform": lambda s: s.replace(" ", "").upper(),
            "description": "Titles with articles (La/Le/The/A/An): remove space after article",
            "explanation": "Article is kept but spaces are removed",
            "examples": [
                ("La haine", "LAHAINE"),
                ("The Office", "THEOFFICE"),
                ("A Star Is Born", "ASTARISBORN"),
            ],
        },
        "hyphenated": {
            "pattern": r"-",
            "transform": lambda s: s.replace("-", "").upper(),
            "description": "Hyphenated words: remove hyphen",
            "explanation": "Hyphens are removed to create single word",
            "examples": [
                ("self-aware", "SELFAWARE"),
                ("co-worker", "COWORKER"),
                ("real-time", "REALTIME"),
            ],
        },
        "apostrophe": {
            "pattern": r"'",
            "transform": lambda s: s.replace("'", "").upper(),
            "description": "Possessives/contractions: remove apostrophe",
            "explanation": "Apostrophes are removed",
            "examples": [
                ("driver's license", "DRIVERSLICENSE"),
                ("can't", "CANT"),
                ("it's", "ITS"),
            ],
        },
    }

    def normalize(self, text: str) -> Tuple[str, Dict]:
        """
        Normalize entry according to conventions.

        Args:
            text: Entry to normalize

        Returns:
            (normalized_text, rule_info)

        Rule info format:
            {
                'type': rule_name,
                'description': description,
                'explanation': detailed explanation,
                'examples': [(input, output), ...],
                'confidence': 'high' | 'medium' | 'low'
            }
        """
        # Try each rule in order
        for rule_name, rule in self.RULES.items():
            if re.search(rule["pattern"], text):
                normalized = rule["transform"](text)
                return (
                    normalized,
                    {
                        "type": rule_name,
                        "description": rule["description"],
                        "explanation": rule.get("explanation", rule["description"]),
                        "examples": rule["examples"],
                        "confidence": "high",
                    },
                )

        # Default rule: no pattern matched. novice-readiness spec 0.2.12 section 4
        # (CLI-normalize) and section 8 PD-L7: keep letters only, folded as section 4
        # item 1 folds them (fold_letters), uppercased; no letter gives "". Letters
        # with no NFKD decomposition (ae, o-slash, oe, sharp s) survive the fold and
        # are kept; str.upper() turns sharp s into SS.
        normalized = "".join(ch for ch in fold_letters(text) if ch.isalpha()).upper()
        return (
            normalized,
            {
                "type": "default",
                "description": "Letters only",
                "explanation": "No specific pattern matched - keeping letters only, uppercased",
                "examples": [],
                "confidence": "medium",
            },
        )

    def get_alternatives(self, text: str, normalized: str) -> List[Dict]:
        """
        Get alternative normalizations if applicable.

        Args:
            text: Original text
            normalized: Normalized text

        Returns:
            List of {'form': alternative, 'note': explanation, 'confidence': level}
        """
        alternatives = []

        # Very long entries might benefit from keeping spaces
        if len(normalized) > 15:
            with_spaces = text.upper()
            if with_spaces != normalized:
                alternatives.append(
                    {
                        "form": with_spaces,
                        "note": "Keep spaces for very long entries (easier to read)",
                        "confidence": "medium",
                    }
                )

        # Titles with articles: suggest alternative without article
        if re.match(r"^(La|Le|The|A|An) ", text):
            without_article = re.sub(r"^(La|Le|The|A|An) ", "", text).replace(" ", "").upper()
            if without_article != normalized:
                alternatives.append(
                    {
                        "form": without_article,
                        "note": "Alternative: remove article entirely",
                        "confidence": "low",
                    }
                )

        return alternatives
