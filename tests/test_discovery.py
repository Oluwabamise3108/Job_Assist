from app.database import SessionLocal
from app.schemas.search import JobSearchRequest
from app.services.discovery import search_jobs
from app.sources.linkedin import LinkedInSource


def cleanup_test_jobs():
    from sqlalchemy import delete

    from app.models.job import Job

    db = SessionLocal()

    try:
        db.execute(
            delete(Job).where(
                Job.source == "linkedin"
            )
        )

        db.commit()

    finally:
        db.close()


def test_discovery_returns_matching_jobs():
    cleanup_test_jobs()

    db = SessionLocal()

    try:
        request = JobSearchRequest(
            keywords=[
                "customer support",
            ],
            remote_only=True,
            global_allowed=True,
            minimum_match_score=70,
            recommendations=[
                "APPLY",
                "REVIEW",
            ],
        )

        result = search_jobs(
            db,
            request=request,
            sources=[
                LinkedInSource()
            ],
        )

        assert result["total_discovered"] == 1
        assert result["total_matching"] == 1

        job = result["jobs"][0]

        assert (
            job["title"]
            == "Customer Support Specialist"
        )

        assert job["company"] == (
            "Global Example Company"
        )

        assert job["match_score"] >= 70

    finally:
        db.close()
        cleanup_test_jobs()


def test_discovery_filters_low_match_jobs():
    cleanup_test_jobs()

    db = SessionLocal()

    try:
        request = JobSearchRequest(
            keywords=[
                "customer support",
            ],
            minimum_match_score=100,
        )

        result = search_jobs(
            db,
            request=request,
            sources=[
                LinkedInSource()
            ],
        )

        assert result["total_discovered"] == 1
        assert result["total_matching"] == 0

    finally:
        db.close()
        cleanup_test_jobs()


def test_discovery_filters_recommendations():
    cleanup_test_jobs()

    db = SessionLocal()

    try:
        request = JobSearchRequest(
            keywords=[
                "customer support",
            ],
            minimum_match_score=0,
            recommendations=[
                "SKIP",
            ],
        )

        result = search_jobs(
            db,
            request=request,
            sources=[
                LinkedInSource()
            ],
        )

        assert result["total_discovered"] == 1
        assert result["total_matching"] == 0

    finally:
        db.close()
        cleanup_test_jobs()