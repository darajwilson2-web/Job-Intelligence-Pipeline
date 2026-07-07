"""
filters.py — All job filtering logic in one place.

Previously duplicated (slightly differently) across daily_job_search.py
and company_job_search.py, causing sync bugs. Now one canonical version.

Functions:
  title_matches()    — does the job title match any target role?
  is_us_location()   — is this posting US-based or unspecified remote?
  contract_ok()      — should this posting be included given contract settings?
"""

import re
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# US LOCATION SIGNALS
# Used with word-boundary matching for short abbreviations
# to avoid "us" matching inside "australia", ", ca" inside "canada", etc.
# ---------------------------------------------------------------------------
US_LOCATION_SIGNALS = [
    "united states", "usa", "u.s.", "remote us", "remote - us",
    "remote, us", "us remote", "america",
    # States
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york", "north carolina",
    "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
    "rhode island", "south carolina", "south dakota", "tennessee", "texas",
    "utah", "vermont", "virginia", "washington", "west virginia",
    "wisconsin", "wyoming",
    # State abbreviations — matched with word boundaries (see _has_us_signal)
    "us", "ny", "ca", "tx", "wa", "nc", "ga", "il", "ma", "fl",
    "co", "az", "oh", "pa", "mi", "mn", "tn", "va", "nj", "ct",
    "sc", "or", "mo",
    # Comma-prefixed abbreviations
    ", ny", ", ca", ", tx", ", wa", ", nc", ", ga", ", il", ", ma",
    ", fl", ", co", ", az", ", oh", ", pa", ", mi", ", mn", ", tn",
    ", va", ", nj", ", ct", ", sc", ", or", ", mo",
    # Major US cities
    "charlotte", "san francisco", "new york, ny", "chicago", "austin",
    "seattle", "boston", "atlanta", "denver", "miami", "dallas",
    "houston", "phoenix", "san diego", "los angeles", "portland",
    "minneapolis", "nashville", "raleigh", "durham",
]

# Short tokens that need word-boundary matching
_SHORT_US = {
    "us", "ny", "ca", "tx", "wa", "nc", "ga", "il", "ma", "fl",
    "co", "az", "oh", "pa", "mi", "mn", "tn", "va", "nj", "ct",
    "sc", "or", "mo",
    ", ny", ", ca", ", tx", ", wa", ", nc", ", ga", ", il", ", ma",
    ", fl", ", co", ", az", ", oh", ", pa", ", mi", ", mn", ", tn",
    ", va", ", nj", ", ct", ", sc", ", or", ", mo",
}

NON_US_SIGNALS = [
    # Countries
    "canada", "united kingdom", "india", "germany", "france", "spain",
    "portugal", "brazil", "mexico", "australia", "japan", "south korea",
    "korea", "poland", "costa rica", "singapore", "netherlands", "ireland",
    "italy", "sweden", "norway", "denmark", "switzerland", "belgium",
    "austria", "new zealand",
    # Cities
    "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad", "pune",
    "london", "manchester", "edinburgh",
    "toronto", "montreal", "vancouver", "ottawa", "calgary",
    "berlin", "munich", "hamburg", "frankfurt",
    "paris", "lyon", "barcelona", "madrid",
    "milan", "rome", "amsterdam",
    "seoul", "busan", "tokyo", "osaka",
    "sydney", "melbourne", "brisbane",
    "sao paulo", "rio de janeiro", "mexico city", "guadalajara",
    "gurugram", "gurgaon", "noida",
    "lisbon", "lisboa", "porto",
    "warsaw", "krakow", "dublin",
    "tel aviv", "istanbul", "zurich", "geneva",
    "brussels", "vienna", "stockholm", "oslo", "copenhagen", "auckland",
    # Common Greenhouse/Lever location strings
    "remote, united kingdom", "remote - uk", "remote uk",
    "remote, canada", "remote - canada", "remote canada",
    "remote, india", "remote - india",
    "remote, germany", "remote - germany",
    "remote, australia", "remote - australia",
    "remote, spain", "remote - spain",
    "remote, poland", "remote - poland",
    "remote, ireland", "remote - ireland",
    "united kingdom", "uk",
]

# Hospitality companies — don't tag them as Healthcare
# ("hospital" appears in "hospitality")
HOSPITALITY_COMPANIES = {
    "airbnb", "marriott", "hilton", "hyatt", "ihg", "wyndham",
    "accor", "expedia", "booking", "vrbo", "numa",
}


# ---------------------------------------------------------------------------
# TITLE FILTER
# ---------------------------------------------------------------------------

def title_matches(title: str, title_filters: list[str]) -> bool:
    """Return True if the job title contains any of the target role phrases."""
    t = title.lower()
    return any(f in t for f in title_filters)


# ---------------------------------------------------------------------------
# LOCATION FILTER
# ---------------------------------------------------------------------------

def _has_us_signal(loc: str) -> bool:
    """
    Check for US location signals using word-boundary matching for short tokens
    to avoid false positives like "us" in "australia" or ", ca" in "canada".
    """
    for signal in US_LOCATION_SIGNALS:
        if signal in _SHORT_US:
            # Word-boundary match: signal must not be surrounded by letters
            if re.search(r"(?<![a-z])" + re.escape(signal) + r"(?![a-z])", loc):
                return True
        else:
            if signal in loc:
                return True
    return False


def is_us_location(location: str, title: str = "", description: str = "") -> bool:
    """
    Return True if the posting is US-based or location is unspecified.
    Return False if it is clearly international.

    Logic:
      - Empty / generic remote → allow (no geo restriction implied)
      - Has US signal → allow
      - Has non-US signal and no US signal → block
      - No clear signal → allow (better to show too many than miss a good fit)
    """
    loc = location.lower().strip()

    # Empty or truly generic → allow through
    if not loc or loc in ("remote", "worldwide", "anywhere", "global"):
        return True

    has_us     = _has_us_signal(loc)
    has_non_us = any(s in loc for s in NON_US_SIGNALS)

    if has_us:
        return True
    if has_non_us:
        return False
    return True  # No clear signal — allow


# ---------------------------------------------------------------------------
# CONTRACT FILTER
# ---------------------------------------------------------------------------

_CONTRACT_SIGNALS = {
    "contract", "contractor", "freelance", "temp ",
    "temporary", "fixed term", "part-time", "part time",
}


def contract_ok(title: str, description: str, include_contract: bool = True) -> bool:
    """Return False only if contract roles are excluded and this looks like one."""
    if include_contract:
        return True
    text = f"{title} {description}".lower()
    return not any(s in text for s in _CONTRACT_SIGNALS)
