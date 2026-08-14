from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.models import Base

from app.schemas.job import (
    JobAnalysisRequest,
    JobAnalysisResponse,
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


API_VERSION = "0.4.0"


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize the database when the application starts.

    This ensures the PostgreSQL database used by Render
    contains the application's tables before requests are
    processed.
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
        "analyzing, scoring, filtering, and storing remote "
        "customer support opportunities."
    ),
    lifespan=lifespan,
)


# ============================================================
# DISCOVERY CONFIGURATION
# ============================================================

ENABLED_DISCOVERY_SOURCES = [
    "linkedin",
    "remoteok",
]


def get_discovery_sources() -> list:
    """
    Build discovery source instances from the source registry.
    """
    return create_sources(
        ENABLED_DISCOVERY_SOURCES
    )


# ============================================================
# HEALTH CHECK
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


# ============================================================
# ROOT
# ============================================================

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
    Analyze a single job posting.
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
        "eligibility_score": eligibility[
            "eligibility_score"
        ],
        "recommendation": decision[
            "recommendation"
        ],
        "hard_reject": decision[
            "hard_reject"
        ],
        "hard_reject_reasons": decision[
            "hard_reject_reasons"
        ],
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
    Ingest a job into PostgreSQL.
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
    Discover jobs from all enabled job sources.
    """

    sources = get_discovery_sources()

    return search_jobs(
        db,
        request=request,
        sources=sources,
    )