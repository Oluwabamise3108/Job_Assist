from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_discover_jobs_endpoint():
    response = client.post(
        "/api/jobs/discover",
        json={
            "keywords": [
                "customer support",
            ],
            "remote_only": True,
            "global_allowed": True,
            "minimum_match_score": 70,
            "recommendations": [
                "APPLY",
                "REVIEW",
            ],
            "limit": 20,
        },
    )

    assert response.status_code == 200

    data = response.json()

    # Multiple sources are now enabled, so the exact number
    # of discovered jobs must not be hard-coded.
    assert data["total_discovered"] >= 1

    # At least one job must satisfy the discovery criteria.
    assert data["total_matching"] >= 1
    assert len(data["jobs"]) >= 1

    # Verify source health.
    source_summary = data["source_summary"]

    assert source_summary["total_sources"] >= 1
    assert source_summary["successful_sources"] >= 1

    # Find the known LinkedIn development fixture.
    matching_job = next(
        (
            job
            for job in data["jobs"]
            if job["title"]
            == "Customer Support Specialist"
            and job["company"]
            == "Global Example Company"
        ),
        None,
    )

    assert matching_job is not None

    assert matching_job["match_score"] >= 70