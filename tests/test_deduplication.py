from app.services.deduplication import (
    deduplicate_jobs,
    job_deduplication_key,
)


def test_same_source_job_id_is_duplicate():
    jobs = [
        {
            "source": "LinkedIn",
            "source_job_id": "12345",
            "title": "Customer Support Specialist",
            "company": "Acme",
        },
        {
            "source": "LinkedIn",
            "source_job_id": "12345",
            "title": "Customer Support Specialist",
            "company": "Acme",
        },
    ]

    result = deduplicate_jobs(jobs)

    assert len(result) == 1


def test_same_job_id_from_different_sources_is_not_duplicate():
    jobs = [
        {
            "source": "LinkedIn",
            "source_job_id": "12345",
            "title": "Customer Support Specialist",
        },
        {
            "source": "Indeed",
            "source_job_id": "12345",
            "title": "Customer Support Specialist",
        },
    ]

    result = deduplicate_jobs(jobs)

    assert len(result) == 2


def test_same_url_is_duplicate():
    jobs = [
        {
            "source": "LinkedIn",
            "url": "https://www.example.com/jobs/123",
        },
        {
            "source": "Indeed",
            "url": "https://example.com/jobs/123",
        },
    ]

    result = deduplicate_jobs(jobs)

    assert len(result) == 1


def test_tracking_parameters_do_not_create_duplicate():
    jobs = [
        {
            "url": "https://example.com/jobs/123?utm_source=linkedin",
        },
        {
            "url": "https://example.com/jobs/123?utm_source=indeed",
        },
    ]

    result = deduplicate_jobs(jobs)

    assert len(result) == 1


def test_company_title_location_fallback():
    jobs = [
        {
            "company": "Acme Inc.",
            "title": "Customer Support Specialist",
            "location": "Remote",
        },
        {
            "company": "  ACME INC  ",
            "title": "customer   support specialist",
            "location": "remote",
        },
    ]

    result = deduplicate_jobs(jobs)

    assert len(result) == 1


def test_distinct_jobs_are_preserved():
    jobs = [
        {
            "source": "LinkedIn",
            "source_job_id": "1",
            "title": "Customer Support Specialist",
        },
        {
            "source": "LinkedIn",
            "source_job_id": "2",
            "title": "Customer Success Manager",
        },
    ]

    result = deduplicate_jobs(jobs)

    assert len(result) == 2


def test_first_occurrence_wins():
    jobs = [
        {
            "source": "LinkedIn",
            "source_job_id": "123",
            "title": "Original Title",
        },
        {
            "source": "LinkedIn",
            "source_job_id": "123",
            "title": "Duplicate Title",
        },
    ]

    result = deduplicate_jobs(jobs)

    assert len(result) == 1
    assert result[0]["title"] == "Original Title"