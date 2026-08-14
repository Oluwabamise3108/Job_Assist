from app.connectors.base import JobSourceConnector
from app.services.job_discovery import (
    DiscoveredJob,
    normalize_discovered_job,
)


class MockJobConnector(JobSourceConnector):
    """
    Development connector used to test the discovery
    pipeline without external network requests.
    """

    source_name = "mock"

    def search(
        self,
        *,
        request,
    ) -> list[DiscoveredJob]:

        jobs = [
            normalize_discovered_job(
                source=self.source_name,
                source_job_id="mock-001",
                title="Customer Support Specialist",
                company="Example Remote Company",
                location="Worldwide",
                url="https://example.com/jobs/mock-001",
                description=(
                    "Remote customer support role. "
                    "Provide customer service through phone "
                    "and email. Experience with Zendesk and "
                    "HubSpot preferred."
                ),
                is_remote=True,
            ),
            normalize_discovered_job(
                source=self.source_name,
                source_job_id="mock-002",
                title="Customer Experience Specialist",
                company="Global Support Inc.",
                location="EMEA",
                url="https://example.com/jobs/mock-002",
                description=(
                    "Fully remote customer experience position. "
                    "Candidates may work remotely from EMEA."
                ),
                is_remote=True,
            ),
        ]

        return jobs