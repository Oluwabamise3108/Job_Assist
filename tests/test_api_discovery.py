from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.sources.base import DiscoveredJob


client = TestClient(app)


def test_discover_jobs_endpoint():
    mock_job = DiscoveredJob(
        source="remoteok",
        source_job_id="test-customer-support-001",
        title="Customer Support Specialist",
        company="Test Company",
        location="Worldwide",
        url="https://example.com/test-customer-support",
        description=(
            "Customer Support Specialist. "
            "Fully remote worldwide role providing "
            "customer service through phone and email. "
            "Experience with Zendesk and HubSpot."
        ),
        is_remote=True,
    )

    with patch(
        "app.main.get_discovery_sources"
    ) as mock_sources:

        mock_source = type(
            "MockSource",
            (),
            {
                "search": lambda self, **kwargs: [
                    mock_job
                ]
            },
        )()

        mock_sources.return_value = [
            mock_source
        ]

        response = client.post(
            "/api/jobs/discover",
            json={
                "keywords": [
                    "customer support",
                ],
                "remote_only": True,
                "global_allowed": True,
                "minimum_match_score": 0,
                "recommendations": [
                    "APPLY",
                    "REVIEW",
                ],
                "limit": 20,
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["total_discovered"] >= 1
    assert data["total_matching"] >= 1
    assert len(data["jobs"]) >= 1

    job = data["jobs"][0]

    assert job["title"] == (
        "Customer Support Specialist"
    )

    assert job["company"] == (
        "Test Company"
    )

    assert job["match_score"] >= 0