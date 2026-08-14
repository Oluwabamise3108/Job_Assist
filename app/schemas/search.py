from pydantic import BaseModel, Field


class JobSearchRequest(BaseModel):
    keywords: list[str] = Field(
        min_length=1,
    )

    remote_only: bool = True

    global_allowed: bool = True

    minimum_match_score: int = Field(
        default=70,
        ge=0,
        le=100,
    )

    recommendations: list[str] = Field(
        default_factory=lambda: [
            "APPLY",
            "REVIEW",
        ]
    )

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
    )


class SourceStatus(BaseModel):
    source: str
    status: str
    discovered: int
    error: str | None = None
    error_type: str | None = None


class SourceSummary(BaseModel):
    total_sources: int
    successful_sources: int
    failed_sources: int
    total_source_jobs: int
    sources: list[SourceStatus]


class JobSearchResponse(BaseModel):
    total_discovered: int
    total_processed: int
    total_unique: int
    total_matching: int
    jobs: list[dict]
    source_summary: SourceSummary