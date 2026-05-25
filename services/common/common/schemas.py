"""Cross-service schema constants and helpers."""

from typing import Literal

PropertyType = Literal[
    "apartment",
    "house",
    "villa",
    "office",
    "retail",
    "industrial",
    "land",
    "other",
    "unknown",
]

RESIDENTIAL_TYPES = frozenset({"apartment", "house", "villa"})
COMMERCIAL_TYPES = frozenset({"office", "retail", "industrial"})


def route_listing_team(property_type: str | None) -> str:
    """Map property_type to team routing label."""
    pt = (property_type or "unknown").lower()
    if pt in RESIDENTIAL_TYPES:
        return "residential_team"
    if pt in COMMERCIAL_TYPES:
        return "commercial_team"
    return "manual_review"
