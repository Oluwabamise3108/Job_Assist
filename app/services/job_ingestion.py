"""
Job ingestion service.

Responsibilities:

1. Normalize job identity.
2. Generate a stable fingerprint.
3. Create or reuse the persisted job.
4. Run match analysis.
5. Run eligibility analysis.
6. Run risk analysis.
7. Make a decision.
8. Persist the complete analysis.
9. Return a normalized dictionary to callers.
"""

import hashlib
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.job import (
    create_job,
    get_job_by_fingerprint,
    update_job_analysis,
)
from app.services.matcher import analyze_match
from app.services.eligibility import analyze_eligibility
from app.services.risk import analyze_risk
from app.services.decision import make_decision


# ============================================================
# TEXT NORMALIZATION
# ============================================================


def normalize_text(
    value: Optional[str],
) -> str:
    """
    Normalize text for identity/fingerprint generation.
    """
    if not value:
        return ""

    value = str(value).lower().strip()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value


# ============================================================
# FINGERPRINT
# ============================================================


def generate_fingerprint(
    *,
    source: str,
    source_job_id: Optional[str],
    url: str,
    title: str,
    company: str,
) -> str:
    """
    Generate a stable job fingerprint.

    Prefer the source's stable job ID.

    Fall back to source + URL + title + company when no stable
    source ID is available.
    """

    if source_job_id:

        identity = (
            f"{normalize_text(source)}:"
            f"{normalize_text(source_job_id)}"
        )

    else:

        identity = "|".join(
            [
                normalize_text(source),
                normalize_text(url),
                normalize_text(title),
                normalize_text(company),
            ]
        )

    return hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()


# ============================================================
# JOB INGESTION
# ============================================================


def ingest_job(
    db: Session,
    *,
    source: str,
    source_job_id: Optional[str],
    title: str,
    company: str,
    location: Optional[str],
    url: str,
    description: str,
    is_remote: bool,
) -> dict:
    """
    Create or update a normalized job and run all analysis engines.

    The returned dictionary is the canonical object consumed by
    discovery and API layers.
    """

    # --------------------------------------------------------
    # FINGERPRINT
    # --------------------------------------------------------

    fingerprint = generate_fingerprint(
        source=source,
        source_job_id=source_job_id,
        url=url,
        title=title,
        company=company,
    )

    # --------------------------------------------------------
    # CREATE OR REUSE
    # --------------------------------------------------------

    existing_job = get_job_by_fingerprint(
        db,
        fingerprint,
    )

    if existing_job:

        job = existing_job
        created = False

    else:

        job = create_job(
            db,
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

        created = True

    # --------------------------------------------------------
    # COMBINED ANALYSIS TEXT
    # --------------------------------------------------------

    combined_text = " ".join(
        part
        for part in [
            title,
            company,
            location or "",
            "Remote" if is_remote else "",
            description,
        ]
        if part
    )

    # --------------------------------------------------------
    # MATCH
    # --------------------------------------------------------

    match = analyze_match(
        title=title,
        description=description,
    )

    # --------------------------------------------------------
    # ELIGIBILITY
    # --------------------------------------------------------

    eligibility = analyze_eligibility(
        combined_text
    )

    # --------------------------------------------------------
    # RISK
    # --------------------------------------------------------

    risk = analyze_risk(
        combined_text
    )

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    decision = make_decision(
        match=match,
        eligibility=eligibility,
        risk=risk,
    )

    # --------------------------------------------------------
    # NORMALIZE ANALYSIS
    # --------------------------------------------------------

    analysis = {
        "match": match,
        "eligibility": eligibility,
        "risk": risk,
        "decision": decision,
    }

    eligibility_score = int(
        eligibility.get(
            "eligibility_score",
            eligibility.get("score", 0),
        )
        or 0
    )

    recommendation = decision.get(
        "recommendation"
    )

    risk_severity = risk.get(
        "severity"
    )

    risk_flags = risk.get(
        "flags",
        [],
    )

    # --------------------------------------------------------
    # SAVE ANALYSIS
    # --------------------------------------------------------

    update_job_analysis(
        db,
        job,
        match_score=match["score"],
        eligibility_score=eligibility_score,
        recommendation=recommendation,
        risk_severity=risk_severity,
        risk_flags=risk_flags,
        analysis=analysis,
    )

    # --------------------------------------------------------
    # RETURN CANONICAL JOB
    # --------------------------------------------------------

    return {
        "job_id": job.id,
        "created": created,
        "fingerprint": fingerprint,
        "source": source,
        "source_job_id": source_job_id,
        "title": job.title,
        "company": job.company,
        "location": location,
        "url": url,
        "description": description,
        "is_remote": is_remote,
        "match_score": match["score"],
        "eligibility_score": eligibility_score,
        "eligibility": eligibility,
        "recommendation": recommendation,
        "risk": risk,
        "analysis": analysis,
    }