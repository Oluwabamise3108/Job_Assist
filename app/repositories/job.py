from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import Job


def get_job_by_fingerprint(
    db: Session,
    fingerprint: str,
) -> Optional[Job]:

    statement = select(Job).where(
        Job.fingerprint == fingerprint
    )

    return db.scalar(statement)


def create_job(
    db: Session,
    *,
    source: str,
    source_job_id: Optional[str],
    fingerprint: str,
    url: str,
    title: str,
    company: str,
    location: Optional[str],
    description: str,
    is_remote: bool,
) -> Job:

    job = Job(
        source=source,
        source_job_id=source_job_id,
        fingerprint=fingerprint,
        url=url,
        title=title,
        company=company,
        location=location,
        description=description,
        is_remote=is_remote,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def update_job_analysis(
    db: Session,
    job: Job,
    *,
    match_score: int,
    eligibility_score: int,
    recommendation: str,
    risk_severity: str,
    risk_flags: list,
    analysis: dict,
) -> Job:

    job.match_score = match_score
    job.eligibility_score = eligibility_score
    job.recommendation = recommendation
    job.risk_severity = risk_severity
    job.risk_flags = risk_flags
    job.analysis = analysis
    job.analyzed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(job)

    return job


def get_job_by_id(
    db: Session,
    job_id: int,
):
    """
    Retrieve a stored job by its database ID.
    """

    statement = select(Job).where(
        Job.id == job_id
    )

    return db.scalar(statement)


def search_jobs(
    db: Session,
    *,
    keyword: Optional[str] = None,
    minimum_match_score: Optional[int] = None,
    recommendation: Optional[str] = None,
    remote_only: bool = False,
    eligible_only: bool = False,
    limit: int = 20,
) -> list[Job]:
    """
    Search and filter jobs already stored in the database.

    This does NOT discover new jobs.
    """

    statement = select(Job)

    # Keyword filter
    if keyword:
        search_term = f"%{keyword.strip()}%"

        statement = statement.where(
            (
                Job.title.ilike(search_term)
                | Job.company.ilike(search_term)
                | Job.description.ilike(search_term)
            )
        )

    # Minimum match score
    if minimum_match_score is not None:
        statement = statement.where(
            Job.match_score >= minimum_match_score
        )

    # Recommendation filter
    if recommendation:
        statement = statement.where(
            Job.recommendation == recommendation.upper()
        )

    # Remote-only filter
    if remote_only:
        statement = statement.where(
            Job.is_remote.is_(True)
        )

    # Eligible-only filter
    if eligible_only:
        statement = statement.where(
            Job.eligibility_score >= 50
        )

    # Newest jobs first
    statement = (
        statement
        .order_by(Job.created_at.desc())
        .limit(limit)
    )

    return list(db.scalars(statement).all())