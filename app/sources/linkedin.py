from app.sources.base import (
    DiscoveredJob,
    JobSource,
)


class LinkedInSource(JobSource):
    """
    LinkedIn discovery source.

    This implementation currently uses deterministic development
    data. A real LinkedIn integration can replace the data retrieval
    logic without changing the discovery engine.
    """

    name = "linkedin"

    def search(
        self,
        *,
        keywords: list[str],
        remote_only: bool = True,
    ) -> list[DiscoveredJob]:
        """
        Search LinkedIn and return normalized DiscoveredJob objects.
        """

        keywords = keywords or []

        # ---------------------------------------------------------
        # DEVELOPMENT DATA
        # ---------------------------------------------------------

        jobs = [
            DiscoveredJob(
                source=self.name,
                source_job_id="linkedin-customer-support-001",

                title="Customer Support Specialist",

                company="Global Example Company",

                location="Worldwide",

                url=(
                    "https://example.com/jobs/"
                    "customer-support-001"
                ),

                description=(
                    "Customer Support Specialist role. "
                    "Fully remote and open to candidates worldwide. "
                    "We are looking for a Customer Support Specialist "
                    "with 3+ years of experience. "
                    "The successful candidate will provide customer "
                    "service through phone and email, manage customer "
                    "inquiries, and use Zendesk and HubSpot."
                ),

                is_remote=True,
            )
        ]

        # ---------------------------------------------------------
        # KEYWORD FILTER
        # ---------------------------------------------------------

        if keywords:

            normalized_keywords = [
                str(keyword).lower().strip()
                for keyword in keywords
                if str(keyword).strip()
            ]

            if normalized_keywords:

                jobs = [
                    job
                    for job in jobs
                    if any(
                        keyword
                        in (
                            f"{job.title} "
                            f"{job.company} "
                            f"{job.description}"
                        ).lower()
                        for keyword in normalized_keywords
                    )
                ]

        # ---------------------------------------------------------
        # REMOTE FILTER
        # ---------------------------------------------------------

        if remote_only:
            jobs = [
                job
                for job in jobs
                if job.is_remote
            ]

        return jobs


__all__ = [
    "LinkedInSource",
]