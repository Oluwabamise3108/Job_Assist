"""We Work Remotely live job source adapter."""

from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from app.services.source_validation import (
    SourceJobValidationError,
    validate_source_job,
)
from app.sources.base import DiscoveredJob, JobSource


class WeWorkRemotelySource(JobSource):
    """Fetch and normalize jobs from WWR's public RSS feed."""

    name = "weworkremotely"

    API_URL = (
        "https://weworkremotely.com/"
        "categories/remote-customer-support-jobs.rss"
    )

    DEFAULT_TIMEOUT = 20
    DEFAULT_LIMIT = 100

    def __init__(
        self,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        limit: int = DEFAULT_LIMIT,
    ) -> None:
        self.timeout = max(1, int(timeout))
        self.limit = max(1, int(limit))

    def search(
        self,
        *,
        request=None,
        keywords=None,
        remote_only=True,
        global_allowed=True,
    ) -> list[DiscoveredJob]:

        if request is not None:
            keywords = request.keywords
            remote_only = request.remote_only
            global_allowed = request.global_allowed

        requested = {
            str(value).strip().lower()
            for value in (keywords or [])
            if str(value).strip()
        }

        payload = self._fetch_feed()

        jobs: list[DiscoveredJob] = []
        seen_ids: set[str] = set()

        for item in payload:
            job = self._normalize_job(item)

            if job is None:
                continue

            provider_id = (
                job.source_job_id
                or job.url
            )

            if provider_id in seen_ids:
                continue

            seen_ids.add(provider_id)

            if remote_only and not job.is_remote:
                continue

            if requested and not self._matches_keywords(
                job,
                requested,
            ):
                continue

            if global_allowed and not self._is_global_or_eligible_location(
                job.location
            ):
                continue

            jobs.append(job)

            if len(jobs) >= self.limit:
                break

        return jobs

    def _fetch_feed(self) -> list[ET.Element]:
        request = urllib.request.Request(
            self.API_URL,
            headers={
                "Accept": "application/rss+xml, application/xml, text/xml",
                "User-Agent": (
                    "JobAssist/1.0 "
                    "(https://job-assist-api.onrender.com)"
                ),
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:

                if response.status != 200:
                    raise RuntimeError(
                        f"We Work Remotely returned HTTP "
                        f"{response.status}"
                    )

                body = response.read()

        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"We Work Remotely returned HTTP {exc.code}"
            ) from exc

        except urllib.error.URLError as exc:
            raise RuntimeError(
                "We Work Remotely request failed"
            ) from exc

        except TimeoutError as exc:
            raise RuntimeError(
                "We Work Remotely request timed out"
            ) from exc

        try:
            root = ET.fromstring(body)
        except ET.ParseError as exc:
            raise RuntimeError(
                "We Work Remotely returned invalid RSS"
            ) from exc

        return root.findall(".//item")

    def _normalize_job(
        self,
        item: ET.Element,
    ) -> DiscoveredJob | None:

        title = self._text(
            item,
            "title",
        )

        description = self._clean_html(
            self._text(
                item,
                "description",
            )
        )

        url = self._text(
            item,
            "link",
        )

        provider_id = self._text(
            item,
            "guid",
        )

        if not provider_id:
            provider_id = url

        if not title or not url:
            return None

        company = self._extract_company(
            title,
            description,
        )

        location = self._extract_location(
            description,
        )

        # WWR's Customer Support RSS feed contains remote jobs.
        is_remote = True

        try:
            normalized = validate_source_job(
                source=self.name,
                source_job_id=provider_id,
                title=title,
                company=company,
                url=url,
                description=description,
                location=location,
                is_remote=is_remote,
            )

        except SourceJobValidationError:
            return None

        return DiscoveredJob(**normalized)

    @staticmethod
    def _text(
        item: ET.Element,
        tag: str,
    ) -> str:

        element = item.find(tag)

        if element is None:
            return ""

        return (
            element.text or ""
        ).strip()

    @staticmethod
    def _clean_html(
        value: str,
    ) -> str:

        value = html.unescape(
            value or ""
        )

        value = re.sub(
            r"<[^>]+>",
            " ",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    @staticmethod
    def _extract_company(
        title: str,
        description: str,
    ) -> str:

        # WWR titles commonly contain:
        #
        # Job Title: Company
        #
        # or
        #
        # Job Title at Company

        for separator in (
            " at ",
            " - ",
            " | ",
        ):

            if separator in title:

                parts = title.split(
                    separator,
                    1,
                )

                if len(parts) == 2:
                    candidate = parts[1].strip()

                    if candidate:
                        return candidate

        match = re.search(
            r"(?:company|employer)\s*:\s*([^|,<]+)",
            description,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

        return "Unknown Company"

    @staticmethod
    def _extract_location(
        description: str,
    ) -> str:

        match = re.search(
            r"(?:location|region)\s*:\s*([^|<]+)",
            description,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

        return "Worldwide"

    @staticmethod
    def _matches_keywords(
        job: DiscoveredJob,
        keywords: set[str],
    ) -> bool:

        searchable = " ".join(
            (
                job.title,
                job.company,
                job.description,
                job.location or "",
            )
        ).lower()

        return any(
            keyword in searchable
            for keyword in keywords
        )

    @staticmethod
    def _is_global_or_eligible_location(
        location: str | None,
    ) -> bool:

        if not location:
            return True

        normalized = location.lower()

        global_terms = (
            "worldwide",
            "anywhere",
            "global",
            "africa",
            "emea",
        )

        return any(
            term in normalized
            for term in global_terms
        )


__all__ = [
    "WeWorkRemotelySource",
]