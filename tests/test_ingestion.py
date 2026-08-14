from sqlalchemy import delete

from app.database import SessionLocal
from app.models.job import Job
from app.services.job_ingestion import ingest_job


def make_job(
    *,
    source_job_id: str,
    title: str = "Customer Support Specialist",
    company: str = "Test Company",
    location: str = "Remote - Worldwide",
    url: str | None = None,
    description: str = (
        "We are looking for a Customer Support Specialist "
        "with 3+ years of experience. "
        "The role provides customer service through phone "
        "and email and uses Zendesk and HubSpot."
    ),
    is_remote: bool = True,
):
    return {
        "source": "pytest",
        "source_job_id": source_job_id,
        "title": title,
        "company": company,
        "location": location,
        "url": url or f"https://example.com/jobs/{source_job_id}",
        "description": description,
        "is_remote": is_remote,
    }


def cleanup_test_jobs():
    """
    Remove only jobs created by this test module.
    """

    db = SessionLocal()

    try:
        db.execute(
            delete(Job).where(
                Job.source == "pytest"
            )
        )

        db.commit()

    finally:
        db.close()


def test_new_job_is_created():
    cleanup_test_jobs()

    db = SessionLocal()

    try:
        result = ingest_job(
            db,
            **make_job(
                source_job_id="create-001"
            ),
        )

        assert result["created"] is True
        assert result["job_id"] is not None
        assert result["fingerprint"]

    finally:
        db.close()
        cleanup_test_jobs()


def test_duplicate_job_is_not_created():
    cleanup_test_jobs()

    db = SessionLocal()

    try:
        job_data = make_job(
            source_job_id="duplicate-001"
        )

        first = ingest_job(
            db,
            **job_data,
        )

        second = ingest_job(
            db,
            **job_data,
        )

        assert first["created"] is True
        assert second["created"] is False

        assert second["job_id"] == first["job_id"]

        assert (
            second["fingerprint"]
            == first["fingerprint"]
        )

    finally:
        db.close()
        cleanup_test_jobs()


def test_different_job_is_created():
    cleanup_test_jobs()

    db = SessionLocal()

    try:
        first = ingest_job(
            db,
            **make_job(
                source_job_id="different-001"
            ),
        )

        second = ingest_job(
            db,
            **make_job(
                source_job_id="different-002"
            ),
        )

        assert first["created"] is True
        assert second["created"] is True

        assert (
            first["job_id"]
            != second["job_id"]
        )

        assert (
            first["fingerprint"]
            != second["fingerprint"]
        )

    finally:
        db.close()
        cleanup_test_jobs()


def test_global_remote_job_is_eligible():
    cleanup_test_jobs()

    db = SessionLocal()

    try:
        result = ingest_job(
            db,
            **make_job(
                source_job_id="global-001",
                location="Remote - Worldwide",
                description=(
                    "Customer Support Specialist. "
                    "Fully remote. "
                    "Work from anywhere in the world. "
                    "Provide customer service through "
                    "phone and email."
                ),
            ),
        )

        assert result["eligibility_score"] == 100

    finally:
        db.close()
        cleanup_test_jobs()


def test_us_only_job_is_ineligible():
    cleanup_test_jobs()

    db = SessionLocal()

    try:
        result = ingest_job(
            db,
            **make_job(
                source_job_id="us-only-001",
                location="Remote - United States",
                description=(
                    "Customer Support Specialist. "
                    "Fully remote, but applicants "
                    "must be based in the United States."
                ),
            ),
        )

        assert result["eligibility_score"] == 0
        assert result["recommendation"] == "SKIP"

    finally:
        db.close()
        cleanup_test_jobs()


def test_remote_job_with_unclear_geography_requires_review():
    cleanup_test_jobs()

    db = SessionLocal()

    try:
        result = ingest_job(
            db,
            **make_job(
                source_job_id="unclear-001",
                location="Remote",
                description=(
                    "Customer Support Specialist. "
                    "This is a fully remote position."
                ),
            ),
        )

        assert result["eligibility_score"] == 50
        assert result["recommendation"] == "REVIEW"

    finally:
        db.close()
        cleanup_test_jobs()


def test_analysis_is_persisted():
    cleanup_test_jobs()

    db = SessionLocal()

    try:
        result = ingest_job(
            db,
            **make_job(
                source_job_id="persist-001"
            ),
        )

        job = db.get(
            Job,
            result["job_id"],
        )

        assert job is not None

        assert (
            job.match_score
            == result["match_score"]
        )

        assert (
            job.eligibility_score
            == result["eligibility_score"]
        )

        assert (
            job.recommendation
            == result["recommendation"]
        )

        assert (
            job.risk_severity
            == result["risk"]["severity"]
        )

        assert job.risk_flags is not None
        assert job.analysis is not None
        assert job.analyzed_at is not None

        assert "match" in job.analysis
        assert "eligibility" in job.analysis
        assert "risk" in job.analysis
        assert "decision" in job.analysis

    finally:
        db.close()
        cleanup_test_jobs()