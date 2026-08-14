from dataclasses import dataclass
from typing import Optional


@dataclass
class DiscoveredJob:
    """
    Standardized representation of a job discovered
    from an external source.
    """

    source: str
    source_job_id: Optional[str]

    title: str
    company: str

    location: Optional[str]
    url: str
    description: str

    is_remote: bool


def normalize_discovered_job(
    *,
    source: str,
    source_job_id: Optional[str],
    title: str,
    company: str,
    location: Optional[str],
    url: str,
    description: str,
    is_remote: bool,
) -> DiscoveredJob:
    """
    Convert a raw discovered job into our standardized
    internal representation.
    """

    return DiscoveredJob(
        source=source.strip(),
        source_job_id=source_job_id.strip()
        if source_job_id
        else None,
        title=title.strip(),
        company=company.strip(),
        location=location.strip()
        if location
        else None,
        url=url.strip(),
        description=description.strip(),
        is_remote=is_remote,
    )