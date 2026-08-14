"""Validation and stable identity helpers for external job sources."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlparse


class SourceJobValidationError(ValueError):
    """Raised when a provider job cannot be normalized safely."""


def _text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _normalized(value: Any) -> str:
    return _text(value).lower()


def _valid_http_url(value: str) -> bool:
    if not value:
        return False

    try:
        parsed = urlparse(value)
    except ValueError:
        return False

    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def generate_source_job_id(
    *,
    source: str,
    url: str,
    title: str,
    company: str,
    provider_id: str | int | None = None,
) -> str:
    """Generate a deterministic source-local ID when the provider has none."""

    provider = _text(provider_id)

    if provider:
        identity = f"{_normalized(source)}:{provider}"
    else:
        identity = "|".join(
            (
                _normalized(source),
                _normalized(url),
                _normalized(title),
                _normalized(company),
            )
        )

    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
    return f"generated-{digest}"


def validate_source_job(
    *,
    source: str,
    source_job_id: str | int | None,
    title: str,
    company: str,
    url: str,
    description: str,
    location: str | None,
    is_remote: bool,
) -> dict[str, Any]:
    """Validate and normalize the canonical fields emitted by a source."""

    normalized_source = _text(source).lower()
    normalized_id = _text(source_job_id)
    normalized_title = _text(title)
    normalized_company = _text(company)
    normalized_url = _text(url)
    normalized_description = _text(description)
    normalized_location = _text(location) or None

    errors: list[str] = []

    if not normalized_source:
        errors.append("source is required")

    if not normalized_title:
        errors.append("title is required")

    if not normalized_company:
        errors.append("company is required")

    if not _valid_http_url(normalized_url):
        errors.append("url must be a valid HTTP or HTTPS URL")

    if not normalized_description:
        errors.append("description is required")

    if not isinstance(is_remote, bool):
        errors.append("is_remote must be a boolean")

    if errors:
        raise SourceJobValidationError("; ".join(errors))

    if not normalized_id:
        normalized_id = generate_source_job_id(
            source=normalized_source,
            url=normalized_url,
            title=normalized_title,
            company=normalized_company,
        )

    return {
        "source": normalized_source,
        "source_job_id": normalized_id,
        "title": normalized_title,
        "company": normalized_company,
        "location": normalized_location,
        "url": normalized_url,
        "description": normalized_description,
        "is_remote": is_remote,
    }


__all__ = [
    "SourceJobValidationError",
    "generate_source_job_id",
    "validate_source_job",
]
