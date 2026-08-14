from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# JOB INGESTION
# ============================================================

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


# ============================================================
# JOB DETAIL
# ============================================================

class JobDetailResponse(BaseModel):
    """
    Response returned when retrieving a stored job
    by database ID.
    """

    model_config = ConfigDict(
        from_attributes=True
    )

    job_id: int

    source: str
    source_job_id: Optional[str] = None
    fingerprint: str

    url: str
    title: str
    company: str
    location: Optional[str] = None
    description: str

    is_remote: bool

    match_score: Optional[int] = None
    eligibility_score: Optional[int] = None

    recommendation: Optional[str] = None

    risk_severity: Optional[str] = None
    risk_flags: list[str] = Field(
        default_factory=list
    )

    analysis: Optional[dict[str, Any]] = None


# ============================================================
# JOB ANALYSIS
# ============================================================

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
