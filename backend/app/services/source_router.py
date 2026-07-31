"""Map claim domains to suggested places for further research.

These destinations are not inspected for a submitted claim and are not
citations or evidence for a verdict.
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


def research_resources_for(domain: str | None) -> list[dict]:
    """Return advisory research destinations for a domain."""
    resources = TRUSTED_SOURCES.get(
        (domain or "other").lower(), TRUSTED_SOURCES["other"]
    )
    return [
        {
            **resource,
            "advisory": "Suggested research destination; not inspected as evidence.",
        }
        for resource in resources
    ]


def sources_for(domain: str | None) -> list[dict]:
    """Backward-compatible alias for research resource lookup."""
    return research_resources_for(domain)
