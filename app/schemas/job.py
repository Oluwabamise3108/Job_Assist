from typing import Any, Optional

from pydantic import BaseModel, Field

class JobSearchRequest(BaseModel):
    keywords: str = Field(min_length=1)

    location: Optional[str] = None

    remote_only: bool = True

    source: Optional[str] = None

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
    )


class JobSearchResponse(BaseModel):
    discovered: int
    ingested: int
    duplicates: int
    results: list[dict]
       
# =========================================================
# JOB INGESTION
# =========================================================

class JobIngestRequest(BaseModel):
    source: str = Field(min_length=1)
    source_job_id: Optional[str] = None

    title: str = Field(min_length=1)
    company: str = Field(min_length=1)

    location: Optional[str] = None

    url: str = Field(min_length=1)

    description: str = Field(
        min_length=1
    )

    is_remote: bool = False


class JobIngestResponse(BaseModel):
    job_id: int
    created: bool
    fingerprint: str

    title: str
    company: str

    match_score: int
    eligibility_score: int

    recommendation: str

    risk: dict[str, Any]


# =========================================================
# JOB ANALYSIS
# =========================================================

class JobAnalysisRequest(BaseModel):
    title: str = Field(min_length=1)

    description: str = Field(
        min_length=1
    )


class JobAnalysisResponse(BaseModel):
    match_score: int
    eligibility_score: int

    recommendation: str

    hard_reject: bool
    hard_reject_reasons: list[str]

    match: dict[str, Any]
    eligibility: dict[str, Any]
    risk: dict[str, Any]