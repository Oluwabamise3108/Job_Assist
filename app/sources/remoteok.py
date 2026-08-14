"""RemoteOK job source adapter."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.services.source_validation import (
    SourceJobValidationError,
    validate_source_job,
)
from app.sources.base import DiscoveredJob, JobSource


class RemoteOKSource(JobSource):
    """Fetch and normalize jobs from RemoteOK's public JSON feed."""

    name = "remoteok"
    API_URL = "https://remoteok.com/api"
    DEFAULT_TIMEOUT = 15
    DEFAULT_LIMIT = 50

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
        remote_only=False,
        global_allowed=False,
    ) -> list[DiscoveredJob]:
        if request is not None:
            keywords = request.keywords
            remote_only = request.remote_only
            global_allowed = request.global_allowed

        keywords = [
            str(value).strip().lower()
            for value in (keywords or [])
            if str(value).strip()
        ]

        payload = self._fetch_feed()
        jobs: list[DiscoveredJob] = []

        for raw in payload:
            if not isinstance(raw, dict):
                continue

            if self._is_feed_metadata(raw):
                continue

            job = self._normalize_job(raw)
            if job is None:
                continue

            if remote_only and not job.is_remote:
                continue

            if keywords and not self._matches_keywords(job, keywords):
                continue

            jobs.append(job)

            if len(jobs) >= self.limit:
                break

        return jobs

    def _fetch_feed(self) -> list[dict[str, Any]]:
        request = urllib.request.Request(
            self.API_URL,
            headers={
                "Accept": "application/json",
                "User-Agent": "JobAssist/0.5 (+https://remoteok.com/)",
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
                        f"RemoteOK returned HTTP {response.status}"
                    )

                body = response.read()

        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"RemoteOK returned HTTP {exc.code}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"RemoteOK request failed: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise RuntimeError("RemoteOK request timed out") from exc

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("RemoteOK returned invalid JSON") from exc

        if not isinstance(payload, list):
            raise RuntimeError("RemoteOK response was not a JSON list")

        return payload

    @staticmethod
    def _is_feed_metadata(raw: dict[str, Any]) -> bool:
        return not raw.get("position") and not raw.get("slug") and not raw.get("id")

    def _normalize_job(self, raw: dict[str, Any]) -> DiscoveredJob | None:
        title = self._first_text(raw, "position", "title")
        company = self._first_text(raw, "company", "company_name")
        description = self._first_text(raw, "description")
        location = self._first_text(raw, "location") or "Worldwide"
        provider_id = self._first_text(raw, "id", "slug")

        canonical_url = self._first_text(raw, "url")
        if not canonical_url:
            slug = self._first_text(raw, "slug")
            if slug:
                canonical_url = f"https://remoteok.com/remote-jobs/{slug}"

        if not canonical_url:
            return None

        is_remote = True

        try:
            normalized = validate_source_job(
                source=self.name,
                source_job_id=provider_id,
                title=title,
                company=company,
                url=canonical_url,
                description=description,
                location=location,
                is_remote=is_remote,
            )
        except SourceJobValidationError:
            return None

        return DiscoveredJob(**normalized)

    @staticmethod
    def _first_text(raw: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = raw.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""

    @staticmethod
    def _matches_keywords(
        job: DiscoveredJob,
        keywords: list[str],
    ) -> bool:
        searchable = " ".join(
            (
                job.title,
                job.company,
                job.description,
                job.location or "",
            )
        ).lower()

        return any(keyword in searchable for keyword in keywords)


__all__ = ["RemoteOKSource"]
