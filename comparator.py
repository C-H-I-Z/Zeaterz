import re


def _year_from(s):
    if not s:
        return None
    m = re.search(r'\b(19|20)\d{2}\b', str(s))
    return int(m.group()) if m else None


def compare_requirement(req):
    """Assign CURRENT / OUTDATED / UNVERIFIED to one requirement dict."""
    current_version    = req.get("current_version")
    date_year          = req.get("date_year")
    needs_manual_review = req.get("needs_manual_review", False)

    if not current_version:
        return {**req, "status": "UNVERIFIED"}

    # Date on file was ** / blank — we have a current version but can't compare years.
    # Show both values so the user can judge; mark UNVERIFIED.
    if needs_manual_review or date_year is None:
        return {**req, "status": "UNVERIFIED"}

    current_year = _year_from(current_version)
    if current_year is None:
        return {**req, "status": "UNVERIFIED"}

    if date_year >= current_year:
        return {**req, "status": "CURRENT"}
    return {**req, "status": "OUTDATED"}


def compare_requirements(requirements):
    return [compare_requirement(r) for r in requirements]