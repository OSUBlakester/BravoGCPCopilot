"""
Utility for normalizing inflected word forms to their base forms.
Used for locale-aware search term matching in AAC image search.

This module provides functions to:
- Load the inflection lookup table (JSON-based conjugation map)
- Normalize a search query to its base/infinitive form
- Support multiple languages (currently Spanish, extensible)
"""

import json
import os
from typing import Dict, Optional


class InflectionLookup:
    """Manages inflection-to-base-form mapping for AAC search normalization."""

    def __init__(self):
        """Initialize by loading the inflection lookup table."""
        self._lookup: Dict[str, Dict[str, str]] = {}
        self._load_lookup_table()

    def _load_lookup_table(self):
        """Load the inflection lookup JSON file."""
        lookup_file = os.path.join(
            os.path.dirname(__file__), "aac_inflection_lookup.json"
        )
        if not os.path.exists(lookup_file):
            print(f"Warning: inflection lookup file not found at {lookup_file}")
            return
        try:
            with open(lookup_file, "r", encoding="utf-8") as f:
                self._lookup = json.load(f)
        except Exception as e:
            print(f"Error loading inflection lookup: {e}")
            self._lookup = {}

    def normalize(self, term: str, locale: str = "es") -> str:
        """
        Normalize a term to its base form for the given locale.

        Args:
            term: The term to normalize (e.g., "quieres")
            locale: The language locale (e.g., "es", "es-US"). If a specific
                   variant like "es-US" is not found, falls back to the base
                   language code ("es").

        Returns:
            The base form of the term (e.g., "querer"), or the original term
            if no mapping is found.

        Example:
            >>> lookup = InflectionLookup()
            >>> lookup.normalize("quieres", "es")
            "querer"
            >>> lookup.normalize("unknown", "es")
            "unknown"
        """
        term_lower = term.lower()

        # Try exact locale match first (e.g., "es-US")
        if locale in self._lookup and term_lower in self._lookup[locale]:
            return self._lookup[locale][term_lower]

        # Fall back to base language code (e.g., "es" from "es-US")
        base_locale = locale.split("-")[0] if "-" in locale else locale
        if base_locale in self._lookup and term_lower in self._lookup[base_locale]:
            return self._lookup[base_locale][term_lower]

        # No mapping found, return original term
        return term

    def has_locale(self, locale: str) -> bool:
        """Check if a locale is available in the lookup table."""
        if locale in self._lookup:
            return True
        base_locale = locale.split("-")[0] if "-" in locale else locale
        return base_locale in self._lookup

    def get_available_locales(self) -> list:
        """Return list of available language locales in the lookup table."""
        return list(self._lookup.keys())


# Global singleton instance
_inflection_lookup: Optional[InflectionLookup] = None


def get_inflection_lookup() -> InflectionLookup:
    """Get or create the global inflection lookup instance."""
    global _inflection_lookup
    if _inflection_lookup is None:
        _inflection_lookup = InflectionLookup()
    return _inflection_lookup


def normalize_search_term(term: str, locale: str = "es") -> str:
    """
    Convenience function to normalize a search term to its base form.

    Args:
        term: The search term to normalize
        locale: The language locale (e.g., "es", "en")

    Returns:
        The normalized base form of the term

    Example:
        >>> normalize_search_term("quieres", "es")
        "querer"
    """
    lookup = get_inflection_lookup()
    return lookup.normalize(term, locale)
