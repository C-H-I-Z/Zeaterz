"""
comparator.py — Status assignment service.

Compares the date on file against the current published version found by
checker.py and assigns one of three statuses to each requirement:

    CURRENT    — date_year >= current published year, or regulation is
                 continuously maintained (current_version == "Current")
    OUTDATED   — date_year < current published year
    UNVERIFIED — checker found nothing, or item had no baseline date (**)
                 to compare against

Public API:
    compare_requirement(req)   -> dict   (single requirement)
    compare_requirements(reqs) -> list   (batch convenience wrapper)
"""

import re


def _year_from(s):
    """Extract a 4-digit year (1900–2099) from a version string, or None."""
    if not s:
        return None
    m = re.search(r'\b(19|20)\d{2}\b', str(s))
    return int(m.group()) if m else None


def compare_requirement(req):
    """Assign CURRENT / OUTDATED / UNVERIFIED to one requirement dict.

    Args:
        req: Requirement dict that has already been processed by checker.py
             (must contain 'current_version', 'date_year', 'needs_manual_review').

    Returns:
        The input dict with 'status' set to one of: CURRENT, OUTDATED, UNVERIFIED.
    """
    current_version     = req.get("current_version")
    date_year           = req.get("date_year")
    needs_manual_review = req.get("needs_manual_review", False)

    # Checker found nothing — cannot determine status.
    if not current_version:
        return {**req, "status": "UNVERIFIED"}

    # Date on file was ** / blank — we have a current version but no baseline to compare.
    # Show whatever the checker found so the user has something to go off of; mark UNVERIFIED.
    if needs_manual_review or date_year is None:
        return {**req, "status": "UNVERIFIED"}

    # "Current" means a continuously maintained regulation (e.g. eCFR) with no fixed version —
    # the user's copy is by definition up to date.
    if str(current_version).strip().lower() == "current":
        return {**req, "status": "CURRENT"}

    current_year = _year_from(current_version)
    if current_year is None:
        # Checker returned something but we couldn't parse a year from it.
        return {**req, "status": "UNVERIFIED"}

    if date_year >= current_year:
        return {**req, "status": "CURRENT"}
    return {**req, "status": "OUTDATED"}


def compare_requirements(requirements):
    """Batch wrapper — applies compare_requirement to every item in a list."""
    return [compare_requirement(r) for r in requirements]
