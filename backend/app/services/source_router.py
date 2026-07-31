"""Source Router: maps a claim's domain to curated trusted Nepali sources.

Rules + entity based (not pure AI). Used by the verdict step to decide where
evidence *should* come from and to surface those links in the verdict card.
"""

TRUSTED_SOURCES: dict[str, list[dict]] = {
    "health": [
        {"name": "Ministry of Health and Population (MoHP)", "url": "https://mohp.gov.np"},
        {"name": "Nepal Health Research Council", "url": "https://nhrc.gov.np"},
    ],
    "election": [
        {"name": "Election Commission of Nepal", "url": "https://election.gov.np"},
    ],
    "government": [
        {"name": "Government of Nepal Portal", "url": "https://nepal.gov.np"},
        {"name": "Nepal Fact Check", "url": "https://nepalfactcheck.org"},
    ],
    "finance": [
        {"name": "Nepal Rastra Bank", "url": "https://nrb.org.np"},
    ],
    "education": [
        {"name": "Ministry of Education", "url": "https://moest.gov.np"},
    ],
    "other": [
        {"name": "South Asia Check", "url": "https://southasiacheck.org"},
        {"name": "Nepal Fact Check", "url": "https://nepalfactcheck.org"},
    ],
}


def sources_for(domain: str | None) -> list[dict]:
    """Return trusted sources for a domain, falling back to general fact-checkers."""
    return TRUSTED_SOURCES.get((domain or "other").lower(), TRUSTED_SOURCES["other"])
