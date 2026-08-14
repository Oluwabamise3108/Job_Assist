from app.sources.base import (
    DiscoveredJob,
    JobSource,
)
from app.sources.linkedin import LinkedInSource


def test_discovered_job_contains_required_fields():
    job = DiscoveredJob(
        source="linkedin",
        source_job_id="123",
        title="Customer Support Specialist",
        company="Example Company",
        location="Remote - Worldwide",
        url="https://example.com/job/123",
        description="Customer support role.",
        is_remote=True,
    )

    assert job.source == "linkedin"
    assert job.source_job_id == "123"
    assert job.title == "Customer Support Specialist"
    assert job.company == "Example Company"
    assert job.is_remote is True


def test_linkedin_source_has_correct_name():
    source = LinkedInSource()

    assert source.name == "linkedin"


def test_linkedin_source_returns_normalized_jobs():
    source = LinkedInSource()

    jobs = source.search(
        keywords=[
            "customer support",
        ],
        remote_only=True,
    )

    assert isinstance(jobs, list)