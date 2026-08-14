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