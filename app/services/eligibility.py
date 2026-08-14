"""
Job eligibility analysis.

This module determines whether a job is realistically eligible
for the candidate based on:

- Remote status
- Geographic scope
- Country restrictions
- Global / worldwide availability
- Visa / sponsorship requirements
- Remote-only requirements

Public interfaces:

    evaluate_eligibility()
        Returns a structured EligibilityResult.

    analyze_eligibility()
        Returns the dictionary format expected by job ingestion.

    apply_eligibility()
        Enriches a job dictionary for the discovery pipeline.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
import re


# ============================================================
# RESULT MODEL
# ============================================================


@dataclass
class EligibilityResult:
    """
    Structured eligibility result.

    Score meanings:

        0   = disqualified
        50  = unclear / requires review
        70+ = eligible / reviewable
        100 = confirmed globally eligible
    """

    score: int
    eligible: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    disqualifiers: list[str] = field(default_factory=list)


# ============================================================
# BASIC HELPERS
# ============================================================


def _normalize_text(
    value: Optional[str],
) -> str:
    """
    Normalize text for reliable matching.
    """

    if value is None:
        return ""

    text = str(value).lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def _get_value(
    job: Any,
    key: str,
    default: Any = None,
) -> Any:
    """
    Safely retrieve a field from either:

    - dict
    - object
    """

    if isinstance(job, dict):
        return job.get(
            key,
            default,
        )

    return getattr(
        job,
        key,
        default,
    )


def _job_text(
    job: Any,
) -> str:
    """
    Build searchable text from a job.
    """

    parts = [
        _get_value(job, "title"),
        _get_value(job, "company"),
        _get_value(job, "location"),
        _get_value(job, "description"),
    ]

    return _normalize_text(
        " ".join(
            str(part)
            for part in parts
            if part
        )
    )


def _contains_any(
    text: str,
    patterns: list[str],
) -> bool:
    """
    Return True if any pattern matches.
    """

    return any(
        re.search(
            pattern,
            text,
        )
        for pattern in patterns
    )


# ============================================================
# REMOTE DETECTION
# ============================================================


def _is_remote(
    job: Any,
    text: str,
) -> bool:
    """
    Determine whether the job is explicitly remote.
    """

    explicit_remote = _get_value(
        job,
        "is_remote",
        None,
    )

    if explicit_remote is not None:
        return bool(explicit_remote)

    remote_patterns = [
        r"\bfully remote\b",
        r"\bremote role\b",
        r"\bremote position\b",
        r"\bremote job\b",
        r"\bremote work\b",
        r"\bwork remotely\b",
        r"\bremote\b",
        r"\bwork from home\b",
        r"\bwfh\b",
        r"\bwork from anywhere\b",
    ]

    return _contains_any(
        text,
        remote_patterns,
    )


# ============================================================
# GEOGRAPHIC PATTERNS
# ============================================================


GLOBAL_PATTERNS = [
    r"\bworldwide\b",
    r"\bworld wide\b",
    r"\bglobal\b",
    r"\bglobally\b",
    r"\banywhere in the world\b",
    r"\bwork from anywhere\b",
    r"\banywhere\b",
    r"\ball countries\b",
    r"\bany country\b",
    r"\binternational\b",
]


US_PATTERNS = [
    r"\bunited states\b",
    r"\busa\b",
    r"\bu\.s\.a\.\b",
    r"\bu\.s\.\b",
    r"\bunited states only\b",
    r"\bus only\b",
    r"\bbased in the united states\b",
    r"\bmust be based in the united states\b",
    r"\bmust reside in the united states\b",
    r"\bresident of the united states\b",
    r"\blocated in the united states\b",
    r"\bmust be located in the united states\b",
]


COUNTRY_RESTRICTION_PATTERNS = [
    r"\bmust be located in\b",
    r"\bmust be based in\b",
    r"\bmust reside in\b",
    r"\bbased in\b",
    r"\blocated in\b",
    r"\breside in\b",
    r"\bresident of\b",
    r"\bonly open to\b",
    r"\bonly available in\b",
    r"\bapplicants must be\b",
    r"\bcandidates must be\b",
]


VISA_PATTERNS = [
    r"\bvisa sponsorship\b",
    r"\bsponsorship required\b",
    r"\brequires sponsorship\b",
    r"\brequires visa\b",
    r"\bwork visa\b",
    r"\bvisa required\b",
]


# ============================================================
# GEOGRAPHIC HELPERS
# ============================================================


def _has_global_scope(
    text: str,
) -> bool:
    """
    Detect explicit worldwide/global availability.
    """

    return _contains_any(
        text,
        GLOBAL_PATTERNS,
    )


def _has_us_restriction(
    text: str,
) -> bool:
    """
    Detect explicit United States restriction.
    """

    return _contains_any(
        text,
        US_PATTERNS,
    )


def _has_country_restriction(
    text: str,
) -> bool:
    """
    Detect explicit geographic restriction.
    """

    return _contains_any(
        text,
        COUNTRY_RESTRICTION_PATTERNS,
    )


def _has_visa_requirement(
    text: str,
) -> bool:
    """
    Detect visa or sponsorship requirements.
    """

    return _contains_any(
        text,
        VISA_PATTERNS,
    )


# ============================================================
# CORE ELIGIBILITY ENGINE
# ============================================================


def evaluate_eligibility(
    job: Any,
    *,
    remote_only: bool = True,
    global_allowed: bool = True,
) -> EligibilityResult:
    """
    Evaluate job eligibility.

    Decision hierarchy:

    1. Remote requirement
    2. Explicit global availability
    3. Explicit geographic restriction
    4. Visa / sponsorship requirement
    5. Explicit remote without restriction
    6. Unclear eligibility
    """

    text = _job_text(job)

    remote = _is_remote(
        job,
        text,
    )

    reasons: list[str] = []
    warnings: list[str] = []
    disqualifiers: list[str] = []

    # ========================================================
    # 1. REMOTE REQUIREMENT
    # ========================================================

    if remote_only and not remote:

        disqualifiers.append(
            "Job is not explicitly remote."
        )

        return EligibilityResult(
            score=0,
            eligible=False,
            reasons=reasons,
            warnings=warnings,
            disqualifiers=disqualifiers,
        )

    if remote:

        reasons.append(
            "Job is explicitly remote."
        )

    # ========================================================
    # 2. GLOBAL AVAILABILITY
    # ========================================================

    global_scope = _has_global_scope(
        text
    )

    # ========================================================
    # 3. GEOGRAPHIC RESTRICTIONS
    # ========================================================

    us_restricted = _has_us_restriction(
        text
    )

    country_restricted = _has_country_restriction(
        text
    )

    if us_restricted:
        country_restricted = True

    # ========================================================
    # 4. EXPLICIT GLOBAL JOB
    # ========================================================

    if global_scope and not country_restricted:

        reasons.append(
            "Job explicitly supports worldwide or global employment."
        )

        return EligibilityResult(
            score=100,
            eligible=True,
            reasons=reasons,
            warnings=warnings,
            disqualifiers=disqualifiers,
        )

    # ========================================================
    # 5. COUNTRY-RESTRICTED JOB
    # ========================================================

    if country_restricted:

        if us_restricted:

            restriction_description = (
                "Job is restricted to the United States."
            )

        else:

            restriction_description = (
                "Job contains a geographic location restriction."
            )

        if global_allowed:

            reasons.append(
                restriction_description
            )

            warnings.append(
                "Job has a country or location restriction; "
                "confirm that the candidate's location is permitted."
            )

            return EligibilityResult(
                score=70,
                eligible=True,
                reasons=reasons,
                warnings=warnings,
                disqualifiers=disqualifiers,
            )

        disqualifiers.append(
            restriction_description
        )

        return EligibilityResult(
            score=0,
            eligible=False,
            reasons=reasons,
            warnings=warnings,
            disqualifiers=disqualifiers,
        )

    # ========================================================
    # 6. VISA / SPONSORSHIP
    # ========================================================

    if _has_visa_requirement(text):

        reasons.append(
            "Job mentions a visa or sponsorship requirement."
        )

        warnings.append(
            "Visa or work authorization requirements must be verified."
        )

        return EligibilityResult(
            score=70,
            eligible=True,
            reasons=reasons,
            warnings=warnings,
            disqualifiers=disqualifiers,
        )

    # ========================================================
    # 7. EXPLICIT REMOTE WITH NO RESTRICTION
    # ========================================================

    if remote:

        reasons.append(
            "Job is remote and no geographic restriction was identified."
        )

        # An explicitly remote job is sufficiently eligible for
        # normal discovery when global_allowed=True, even though
        # it is not confirmed to be worldwide.
        #
        # A score of 70 represents:
        #
        #     eligible
        #     but not globally confirmed
        #
        # This is deliberately different from a job whose
        # geographic scope is genuinely unclear.
        if global_allowed:

            return EligibilityResult(
                score=70,
                eligible=True,
                reasons=reasons,
                warnings=warnings,
                disqualifiers=disqualifiers,
            )

        warnings.append(
            "Job is remote, but its geographic scope is not "
            "explicitly confirmed as worldwide."
        )

        return EligibilityResult(
            score=50,
            eligible=True,
            reasons=reasons,
            warnings=warnings,
            disqualifiers=disqualifiers,
        )

    # ========================================================
    # 8. FALLBACK
    # ========================================================

    disqualifiers.append(
        "Job eligibility could not be established."
    )

    return EligibilityResult(
        score=0,
        eligible=False,
        reasons=reasons,
        warnings=warnings,
        disqualifiers=disqualifiers,
    )


# ============================================================
# INGESTION ADAPTER
# ============================================================


def analyze_eligibility(
    text: str,
    *,
    remote_only: bool = True,
    global_allowed: bool = False,
) -> dict:
    """
    Analyze eligibility for the ingestion pipeline.

    Ingestion supplies combined job text rather than the
    original job dictionary.

    The default global_allowed=False prevents a country-
    restricted remote job from being incorrectly classified
    as globally eligible during ingestion.
    """

    normalized_text = _normalize_text(
        text
    )

    job = {
        "description": normalized_text,
        "is_remote": _is_remote(
            {},
            normalized_text,
        ),
    }

    result = evaluate_eligibility(
        job,
        remote_only=remote_only,
        global_allowed=global_allowed,
    )

    return {
        "eligibility_score": result.score,
        "eligible": result.eligible,
        "reasons": result.reasons,
        "warnings": result.warnings,
        "disqualifiers": result.disqualifiers,
    }


# ============================================================
# DISCOVERY ADAPTER
# ============================================================


def apply_eligibility(
    job: Any,
    *,
    remote_only: bool = True,
    global_allowed: bool = True,
) -> dict:
    """
    Apply eligibility analysis to a job.

    The original job fields are preserved.

    Eligibility fields added:

        eligibility_score
        eligible
        eligibility_eligible
        eligibility_reasons
        eligibility_warnings
        eligibility_disqualifiers
    """

    if isinstance(job, dict):

        enriched_job = dict(job)

    else:

        enriched_job = {}

        for field_name in (
            "job_id",
            "id",
            "title",
            "company",
            "location",
            "description",
            "url",
            "source",
            "source_job_id",
            "is_remote",
            "match_score",
            "recommendation",
            "risk",
        ):

            if hasattr(
                job,
                field_name,
            ):

                enriched_job[field_name] = getattr(
                    job,
                    field_name,
                )

    result = evaluate_eligibility(
        enriched_job,
        remote_only=remote_only,
        global_allowed=global_allowed,
    )

    # Primary public field expected by consumers/tests.
    enriched_job[
        "eligible"
    ] = result.eligible

    enriched_job[
        "eligibility_score"
    ] = result.score

    # Backward-compatible explicit field.
    enriched_job[
        "eligibility_eligible"
    ] = result.eligible

    enriched_job[
        "eligibility_reasons"
    ] = result.reasons

    enriched_job[
        "eligibility_warnings"
    ] = result.warnings

    enriched_job[
        "eligibility_disqualifiers"
    ] = result.disqualifiers

    return enriched_job


# ============================================================
# PUBLIC API
# ============================================================


__all__ = [
    "EligibilityResult",
    "evaluate_eligibility",
    "analyze_eligibility",
    "apply_eligibility",
]