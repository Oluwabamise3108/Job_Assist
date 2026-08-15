from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.models import Base

from app.repositories.job import (
    get_job_by_id,
    search_jobs as search_jobs_db,
)

from app.schemas.job import (
    JobAnalysisRequest,
    JobAnalysisResponse,
    JobDetailResponse,
    JobIngestRequest,
    JobIngestResponse,
)

from app.schemas.search import (
    JobSearchRequest,
    JobSearchResponse,
)

from app.services.decision import make_decision
from app.services.discovery import search_jobs
from app.services.eligibility import analyze_eligibility
from app.services.job_ingestion import ingest_job
from app.services.matcher import analyze_match
from app.services.risk import analyze_risk

from app.sources.registry import create_sources


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

API_VERSION = "0.4.0"

ENABLED_DISCOVERY_SOURCES = [
    "linkedin",
    "remoteok",
    "weworkremotely",
]


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize database tables when the application starts.
    """

    Base.metadata.create_all(bind=engine)

    yield


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title=settings.app_name,
    version=API_VERSION,
    description=(
        "Remote Job Intelligence API for discovering, "
        "analyzing, scoring, filtering, and storing "
        "remote customer support opportunities."
    ),
    lifespan=lifespan,
)


# ============================================================
# DISCOVERY SOURCES
# ============================================================

def get_discovery_sources() -> list:
    """
    Build enabled discovery source instances.
    """

    return create_sources(
        ENABLED_DISCOVERY_SOURCES
    )


# ============================================================
# RESPONSE HELPERS
# ============================================================

def serialize_job(job) -> dict:
    """
    Convert a SQLAlchemy Job model into the API response shape.
    """

    return {
        "job_id": job.id,
        "source": job.source,
        "source_job_id": job.source_job_id,
        "fingerprint": job.fingerprint,
        "url": job.url,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "description": job.description,
        "is_remote": job.is_remote,
        "match_score": job.match_score,
        "eligibility_score": job.eligibility_score,
        "recommendation": job.recommendation,
        "risk_severity": job.risk_severity,
        "risk_flags": job.risk_flags or [],
        "analysis": job.analysis,
    }


# ============================================================
# SYSTEM
# ============================================================

@app.get(
    "/health",
    tags=["System"],
)
def health_check():
    """
    Verify that the API is running.
    """

    return {
        "status": "ok",
        "environment": settings.environment,
    }


@app.get(
    "/",
    tags=["System"],
)
def root():
    """
    Return basic API information.
    """

    return {
        "name": settings.app_name,
        "version": API_VERSION,
        "status": "running",
        "docs": "/docs",
    }


# ============================================================
# JOB ANALYSIS
# ============================================================

@app.post(
    "/api/jobs/analyze",
    response_model=JobAnalysisResponse,
    tags=["Jobs"],
)
def analyze_job(
    request: JobAnalysisRequest,
):
    """
    Analyze a single job without storing it.

    Pipeline:

        Job
         |
         +-- Match
         +-- Eligibility
         +-- Risk
         |
         +-- Decision
    """

    combined_text = (
        f"{request.title} "
        f"{request.description}"
    )

    match = analyze_match(
        title=request.title,
        description=request.description,
    )

    eligibility = analyze_eligibility(
        combined_text,
    )

    risk = analyze_risk(
        combined_text,
    )

    decision = make_decision(
        match=match,
        eligibility=eligibility,
        risk=risk,
    )

    return {
        "match_score": match["score"],
        "eligibility_score": (
            eligibility["eligibility_score"]
        ),
        "recommendation": (
            decision["recommendation"]
        ),
        "hard_reject": (
            decision["hard_reject"]
        ),
        "hard_reject_reasons": (
            decision["hard_reject_reasons"]
        ),
        "match": match,
        "eligibility": eligibility,
        "risk": risk,
    }


# ============================================================
# JOB INGESTION
# ============================================================

@app.post(
    "/api/jobs/ingest",
    response_model=JobIngestResponse,
    tags=["Jobs"],
)
def ingest_job_endpoint(
    request: JobIngestRequest,
    db: Session = Depends(get_db),
):
    """
    Ingest, analyze, deduplicate, and store a job.
    """

    return ingest_job(
        db,
        source=request.source,
        source_job_id=request.source_job_id,
        title=request.title,
        company=request.company,
        location=request.location,
        url=request.url,
        description=request.description,
        is_remote=request.is_remote,
    )


# ============================================================
# DATABASE JOB SEARCH / FILTER
# ============================================================

@app.get(
    "/api/jobs",
    response_model=list[JobDetailResponse],
    tags=["Jobs"],
)
def search_stored_jobs(
    keyword: str | None = Query(
        default=None,
        description=(
            "Search stored jobs by title, company, "
            "or description."
        ),
    ),
    minimum_match_score: int | None = Query(
        default=None,
        ge=0,
        le=100,
        description=(
            "Minimum acceptable match score."
        ),
    ),
    recommendation: str | None = Query(
        default=None,
        description=(
            "Recommendation filter: APPLY, REVIEW, "
            "POSSIBLE, or SKIP."
        ),
    ),
    remote_only: bool = Query(
        default=False,
        description="Only return remote jobs.",
    ),
    eligible_only: bool = Query(
        default=False,
        description="Only return eligible jobs.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results.",
    ),
    db: Session = Depends(get_db),
):
    """
    Search jobs already stored in PostgreSQL.

    This endpoint does NOT rediscover jobs.

    Filters can be combined.
    """

    jobs = search_jobs_db(
        db,
        keyword=keyword,
        minimum_match_score=minimum_match_score,
        recommendation=recommendation,
        remote_only=remote_only,
        eligible_only=eligible_only,
        limit=limit,
    )

    return [
        serialize_job(job)
        for job in jobs
    ]


# ============================================================
# JOB DETAIL
# ============================================================

@app.get(
    "/api/jobs/{job_id}",
    response_model=JobDetailResponse,
    tags=["Jobs"],
)
def get_job_detail(
    job_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve a previously stored job by database ID.

    This endpoint does NOT rediscover the job.
    """

    job = get_job_by_id(
        db,
        job_id,
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Job with ID {job_id} not found."
            ),
        )

    return serialize_job(job)


# ============================================================
# JOB DISCOVERY
# ============================================================

@app.post(
    "/api/jobs/discover",
    response_model=JobSearchResponse,
    tags=["Jobs"],
)
def discover_jobs(
    request: JobSearchRequest,
    db: Session = Depends(get_db),
):
    """
    Discover jobs from all enabled sources.

    Discovered jobs are processed, analyzed,
    deduplicated, and persisted.
    """

    sources = get_discovery_sources()

    return search_jobs(
        db,
        request=request,
        sources=sources,
    )