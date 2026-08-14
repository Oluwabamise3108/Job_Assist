import re
from typing import Any


def _normalize_text(value: Any) -> str:
    """
    Normalize text for stable comparison.

    Examples:
        "Senior Customer Support Specialist"
        " senior   customer support specialist "
        -> "senior customer support specialist"
    """
    if value is None:
        return ""

    value = str(value).strip().lower()

    # Remove URLs/protocol noise where applicable.
    value = re.sub(r"https?://", "", value)

    # Normalize punctuation/whitespace.
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def _normalize_url(url: Any) -> str:
    """
    Normalize a job URL so tracking parameters don't create duplicates.
    """
    if not url:
        return ""

    value = str(url).strip().lower()

    # Remove protocol.
    value = re.sub(r"^https?://", "", value)

    # Remove www.
    value = re.sub(r"^www\.", "", value)

    # Remove query string and fragment.
    value = value.split("?", 1)[0]
    value = value.split("#", 1)[0]

    # Remove trailing slash.
    return value.rstrip("/")


def job_deduplication_key(job: dict) -> str:
    """
    Generate the strongest available identity key for a discovered job.

    Priority:
        1. source + source_job_id
        2. normalized URL
        3. company + title + location
    """

    source = _normalize_text(job.get("source"))
    source_job_id = _normalize_text(job.get("source_job_id"))

    if source and source_job_id:
        return f"source:{source}|id:{source_job_id}"

    url = _normalize_url(job.get("url"))

    if url:
        return f"url:{url}"

    company = _normalize_text(job.get("company"))
    title = _normalize_text(job.get("title"))
    location = _normalize_text(job.get("location"))

    return (
        f"job:"
        f"{company}|"
        f"{title}|"
        f"{location}"
    )


def deduplicate_jobs(jobs: list[dict]) -> list[dict]:
    """
    Remove duplicate jobs while preserving discovery order.

    The first occurrence wins.
    """

    seen: set[str] = set()
    unique_jobs: list[dict] = []

    for job in jobs:
        key = job_deduplication_key(job)

        if key in seen:
            continue

        seen.add(key)
        unique_jobs.append(job)

    return unique_jobs