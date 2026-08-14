"""
Job discovery orchestration.

Pipeline:

    Search Sources
         ↓
    Isolate Source Failures
         ↓
    Keyword Filtering
         ↓
    Remote Filtering
         ↓
    Ingest / Analyze
         ↓
    Deduplicate
         ↓
    Eligibility
         ↓
    Match Score
         ↓
    Recommendation
         ↓
    Global Eligibility
         ↓
    Ranking
         ↓
    Result Limit
         ↓
    Return Results
"""

from typing import Any

from sqlalchemy.orm import Session

from app.services.deduplication import deduplicate_jobs
from app.services.eligibility import apply_eligibility
from app.services.job_ingestion import ingest_job


# ---------------------------------------------------------------------------
# SAFE FIELD ACCESS
# ---------------------------------------------------------------------------

def _get_job_value(
    job: Any,
    key: str,
    default=None,
):
    if isinstance(job, dict):
        return job.get(key, default)

    return getattr(
        job,
        key,
        default,
    )


# ---------------------------------------------------------------------------
# SOURCE NAME
# ---------------------------------------------------------------------------

def _get_source_name(
    source: Any,
) -> str:
    name = getattr(
        source,
        "name",
        None,
    )

    if name:
        return str(name)

    return source.__class__.__name__


# ---------------------------------------------------------------------------
# SOURCE SEARCH
# ---------------------------------------------------------------------------

def _search_source(
    source: Any,
    *,
    request: Any,
) -> tuple[list[Any], dict[str, Any]]:
    """
    Search one source safely.

    A failed source must not prevent other sources from
    returning jobs.
    """

    source_name = _get_source_name(
        source
    )

    try:
        jobs = source.search(
            keywords=request.keywords,
            remote_only=request.remote_only,
        )

        if jobs is None:
            jobs = []

        if not isinstance(jobs, list):
            jobs = list(jobs)

        return (
            jobs,
            {
                "source": source_name,
                "status": "success",
                "discovered": len(jobs),
                "error": None,
                "error_type": None,
            },
        )

    except Exception as exc:
        return (
            [],
            {
                "source": source_name,
                "status": "failed",
                "discovered": 0,
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
        )


# ---------------------------------------------------------------------------
# KEYWORD FILTER
# ---------------------------------------------------------------------------

def _matches_keywords(
    job: Any,
    keywords,
) -> bool:

    if not keywords:
        return True

    title = str(
        _get_job_value(
            job,
            "title",
            "",
        )
        or ""
    ).lower()

    company = str(
        _get_job_value(
            job,
            "company",
            "",
        )
        or ""
    ).lower()

    description = str(
        _get_job_value(
            job,
            "description",
            "",
        )
        or ""
    ).lower()

    searchable_text = (
        f"{title} "
        f"{company} "
        f"{description}"
    )

    normalized_keywords = [
        str(keyword).lower().strip()
        for keyword in keywords
        if str(keyword).strip()
    ]

    if not normalized_keywords:
        return True

    return any(
        keyword in searchable_text
        for keyword in normalized_keywords
    )


# ---------------------------------------------------------------------------
# REMOTE FILTER
# ---------------------------------------------------------------------------

def _matches_remote(
    job: Any,
    remote_only: bool,
) -> bool:

    if not remote_only:
        return True

    return bool(
        _get_job_value(
            job,
            "is_remote",
            False,
        )
    )


# ---------------------------------------------------------------------------
# SAFE SCORE
# ---------------------------------------------------------------------------

def _safe_score(
    job: Any,
    key: str,
) -> float:

    value = _get_job_value(
        job,
        key,
        0,
    )

    try:
        return float(value or 0)

    except (
        TypeError,
        ValueError,
    ):
        return 0.0


# ---------------------------------------------------------------------------
# RECOMMENDATION FILTER
# ---------------------------------------------------------------------------

def _recommendation_matches(
    recommendation,
    requested_recommendations,
) -> bool:

    if not requested_recommendations:
        return True

    if recommendation is None:
        return False

    normalized_recommendation = (
        str(recommendation)
        .strip()
        .upper()
    )

    normalized_requested = {
        str(value)
        .strip()
        .upper()
        for value in requested_recommendations
        if str(value).strip()
    }

    if not normalized_requested:
        return True

    return (
        normalized_recommendation
        in normalized_requested
    )


# ---------------------------------------------------------------------------
# GLOBAL ELIGIBILITY
# ---------------------------------------------------------------------------

def _passes_global_eligibility(
    job: Any,
    global_allowed: bool,
) -> bool:

    if global_allowed:
        return True

    eligibility_score = _safe_score(
        job,
        "eligibility_score",
    )

    return eligibility_score >= 100


# ---------------------------------------------------------------------------
# RANKING
# ---------------------------------------------------------------------------

def _ranking_key(
    job: Any,
) -> tuple[float, ...]:

    match_score = _safe_score(
        job,
        "match_score",
    )

    eligibility_score = _safe_score(
        job,
        "eligibility_score",
    )

    risk = _get_job_value(
        job,
        "risk",
        {},
    )

    if isinstance(risk, dict):
        severity = risk.get("severity")
    else:
        severity = getattr(
            risk,
            "severity",
            None,
        )

    risk_rank = {
        "low": 3,
        "medium": 2,
        "high": 1,
    }.get(
        str(
            severity or ""
        ).strip().lower(),
        0,
    )

    recommendation = str(
        _get_job_value(
            job,
            "recommendation",
            "",
        )
        or ""
    ).strip().upper()

    recommendation_rank = {
        "APPLY": 3,
        "REVIEW": 2,
        "POSSIBLE": 1,
        "SKIP": 0,
    }.get(
        recommendation,
        0,
    )

    return (
        match_score,
        eligibility_score,
        float(risk_rank),
        float(recommendation_rank),
    )


# ---------------------------------------------------------------------------
# SOURCE SUMMARY
# ---------------------------------------------------------------------------

def _build_source_summary(
    source_status: list[dict[str, Any]],
) -> dict[str, Any]:

    successful_sources = sum(
        1
        for status in source_status
        if status.get("status") == "success"
    )

    failed_sources = sum(
        1
        for status in source_status
        if status.get("status") == "failed"
    )

    total_source_jobs = sum(
        int(
            status.get(
                "discovered",
                0,
            )
            or 0
        )
        for status in source_status
    )

    return {
        "total_sources": len(
            source_status
        ),
        "successful_sources": (
            successful_sources
        ),
        "failed_sources": (
            failed_sources
        ),
        "total_source_jobs": (
            total_source_jobs
        ),
        "sources": source_status,
    }


# ---------------------------------------------------------------------------
# MAIN DISCOVERY PIPELINE
# ---------------------------------------------------------------------------

def search_jobs(
    db: Session,
    *,
    request,
    sources: list,
) -> dict:

    # =======================================================================
    # 1. SEARCH SOURCES
    # =======================================================================

    all_jobs = []
    source_status = []

    for source in sources:

        discovered_jobs, status = _search_source(
            source,
            request=request,
        )

        source_status.append(
            status
        )

        if discovered_jobs:
            all_jobs.extend(
                discovered_jobs
            )

    total_discovered = len(
        all_jobs
    )

    # =======================================================================
    # 2. FILTER + INGEST
    # =======================================================================

    processed = []

    for discovered_job in all_jobs:

        if not _matches_keywords(
            discovered_job,
            request.keywords,
        ):
            continue

        if not _matches_remote(
            discovered_job,
            request.remote_only,
        ):
            continue

        source = _get_job_value(
            discovered_job,
            "source",
        )

        source_job_id = _get_job_value(
            discovered_job,
            "source_job_id",
        )

        title = _get_job_value(
            discovered_job,
            "title",
            "",
        )

        company = _get_job_value(
            discovered_job,
            "company",
            "",
        )

        location = _get_job_value(
            discovered_job,
            "location",
        )

        url = _get_job_value(
            discovered_job,
            "url",
            "",
        )

        description = _get_job_value(
            discovered_job,
            "description",
            "",
        )

        is_remote = bool(
            _get_job_value(
                discovered_job,
                "is_remote",
                False,
            )
        )

        result = ingest_job(
            db,
            source=source,
            source_job_id=source_job_id,
            title=title,
            company=company,
            location=location,
            url=url,
            description=description,
            is_remote=is_remote,
        )

        if result is not None:
            processed.append(
                result
            )

    # =======================================================================
    # 3. DEDUPLICATE
    # =======================================================================

    unique_jobs = deduplicate_jobs(
        processed
    )

    # =======================================================================
    # 4. ELIGIBILITY
    # =======================================================================

    eligible_jobs = []

    for job in unique_jobs:

        eligible_jobs.append(
            apply_eligibility(
                job,
                remote_only=request.remote_only,
                global_allowed=request.global_allowed,
            )
        )

    # =======================================================================
    # 5. DISCOVERY FILTERS
    # =======================================================================

    matched = []

    for job in eligible_jobs:

        match_score = _safe_score(
            job,
            "match_score",
        )

        if (
            match_score
            < request.minimum_match_score
        ):
            continue

        recommendation = _get_job_value(
            job,
            "recommendation",
        )

        if not _recommendation_matches(
            recommendation,
            request.recommendations,
        ):
            continue

        if not _passes_global_eligibility(
            job,
            request.global_allowed,
        ):
            continue

        matched.append(
            job
        )

    # =======================================================================
    # 6. RANK
    # =======================================================================

    matched.sort(
        key=_ranking_key,
        reverse=True,
    )

    # =======================================================================
    # 7. LIMIT
    # =======================================================================

    if request.limit is None:
        limited_matches = matched
    else:
        limited_matches = matched[
            :max(
                0,
                int(request.limit),
            )
        ]

    # =======================================================================
    # 8. SOURCE SUMMARY
    # =======================================================================

    source_summary = _build_source_summary(
        source_status
    )

    # =======================================================================
    # 9. RESPONSE
    # =======================================================================

    return {
        "total_discovered": (
            total_discovered
        ),
        "total_processed": (
            len(processed)
        ),
        "total_unique": (
            len(unique_jobs)
        ),
        "total_matching": (
            len(matched)
        ),
        "jobs": limited_matches,
        "source_summary": source_summary,
    }