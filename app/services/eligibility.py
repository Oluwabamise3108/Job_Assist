"""
Job eligibility analysis.

Determines whether a job is realistically eligible for the candidate
based on:

- Remote status
- Geographic scope
- Country restrictions
- Global / worldwide availability
- Visa / sponsorship requirements
- Remote-only requirements

Candidate location:
    Nigeria

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
# CANDIDATE LOCATION
# ============================================================

CANDIDATE_COUNTRY = "nigeria"


# ============================================================
# RESULT MODEL
# ============================================================

@dataclass
class EligibilityResult:
    """
    Structured eligibility result.

    Score meanings:

        0   = hard disqualification
        50  = unclear / conflicting geographic information
        70  = eligible but geographic scope requires review
        100 = clearly eligible for Nigeria or globally
    """

    score: int
    eligible: bool

    reasons: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    disqualifiers: list[str] = field(
        default_factory=list
    )

    geography: dict[str, Any] = field(
        default_factory=dict
    )


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
    Safely retrieve a field from either a dictionary
    or an object.
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
    Build searchable text from the job.
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
    Return True when any regex pattern matches.
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

REMOTE_PATTERNS = [
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

    return _contains_any(
        text,
        REMOTE_PATTERNS,
    )


# ============================================================
# GLOBAL AVAILABILITY
# ============================================================

GLOBAL_PATTERNS = [
    r"\bworldwide\b",
    r"\bworld wide\b",
    r"\bglobal\b",
    r"\bglobally\b",
    r"\banywhere in the world\b",
    r"\bwork from anywhere\b",
    r"\ball countries\b",
    r"\bany country\b",
    r"\binternational\b",
]


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


# ============================================================
# COUNTRY DEFINITIONS
# ============================================================

COUNTRY_PATTERNS = {
    "nigeria": [
        r"\bnigeria\b",
        r"\bnigerian\b",
    ],

    "united states": [
        r"\bunited states\b",
        r"\busa\b",
        r"\bu\.s\.a\.\b",
        r"\bu\.s\.\b",
        r"\bunited states of america\b",
    ],

    "canada": [
        r"\bcanada\b",
        r"\bcanadian\b",
    ],

    "united kingdom": [
        r"\bunited kingdom\b",
        r"\buk\b",
        r"\bu\.k\.\b",
        r"\bbritain\b",
        r"\bbritish\b",
    ],

    "australia": [
        r"\baustralia\b",
        r"\baustralian\b",
    ],

    "new zealand": [
        r"\bnew zealand\b",
        r"\bnz\b",
        r"\bnew zealander\b",
    ],

    "philippines": [
        r"\bphilippines\b",
        r"\bphilippine\b",
    ],

    "india": [
        r"\bindia\b",
        r"\bindian\b",
    ],

    "germany": [
        r"\bgermany\b",
        r"\bgerman\b",
    ],

    "france": [
        r"\bfrance\b",
        r"\bfrench\b",
    ],

    "europe": [
        r"\beurope\b",
        r"\beuropean\b",
    ],
}


# ============================================================
# RESTRICTION PATTERNS
# ============================================================

GENERIC_RESTRICTION_PATTERNS = [
    r"\bmust be located in\b",
    r"\bmust be based in\b",
    r"\bmust reside in\b",
    r"\bbased in\b",
    r"\blocated in\b",
    r"\breside in\b",
    r"\bresident of\b",
    r"\bresidents of\b",
    r"\bonly open to\b",
    r"\bonly available in\b",
    r"\bonly for\b",
    r"\bapplicants must be\b",
    r"\bcandidates must be\b",
]


# These indicate a much stronger exclusion than a generic
# geographic statement.
HARD_RESTRICTION_PATTERNS = [
    r"\bresidents?\s+only\b",
    r"\bapplicants?\s+only\b",
    r"\bcandidates?\s+only\b",
    r"\bmust\s+be\s+based\s+in\s+[^.]{0,80}\bonly\b",
    r"\bmust\s+reside\s+in\s+[^.]{0,80}\bonly\b",
    r"\bonly\s+applicants?\s+from\b",
    r"\bonly\s+candidates?\s+from\b",
    r"\bremote\s+[^.]{0,80}\bonly\b",
    r"\b(?:us|usa|u\.s\.|united states)\s+only\b",
    r"\b(?:nigeria|philippines|india|canada|australia|"
    r"united kingdom|germany|france)\s+only\b",
]


VISA_PATTERNS = [
    r"\bvisa sponsorship\b",
    r"\bsponsorship required\b",
    r"\brequires sponsorship\b",
    r"\brequires visa\b",
    r"\bwork visa\b",
    r"\bvisa required\b",
    r"\bvisa support\b",
    r"\bwork authorization required\b",
]


# ============================================================
# COUNTRY DETECTION
# ============================================================

def _find_mentioned_countries(
    text: str,
) -> list[str]:
    """
    Return all recognized countries/regions mentioned
    in the supplied text.
    """

    normalized = _normalize_text(
        text
    )

    found: list[str] = []

    for country, patterns in COUNTRY_PATTERNS.items():

        if _contains_any(
            normalized,
            patterns,
        ):
            found.append(
                country
            )

    return list(
        dict.fromkeys(found)
    )


def _country_mentioned(
    text: str,
    country: str,
) -> bool:
    """
    Determine whether a specific country is mentioned.
    """

    patterns = COUNTRY_PATTERNS.get(
        country,
        [],
    )

    return _contains_any(
        _normalize_text(text),
        patterns,
    )


# ============================================================
# RESTRICTION DETECTION
# ============================================================

def _has_generic_restriction(
    text: str,
) -> bool:
    """
    Detect generic geographic restriction language.
    """

    return _contains_any(
        text,
        GENERIC_RESTRICTION_PATTERNS,
    )


def _has_hard_restriction(
    text: str,
) -> bool:
    """
    Detect explicit country-only / residents-only language.
    """

    return _contains_any(
        text,
        HARD_RESTRICTION_PATTERNS,
    )


def _extract_restricted_countries(
    text: str,
) -> list[str]:
    """
    Extract countries that appear to be associated with
    geographic restriction language.

    This function deliberately distinguishes ordinary country
    mentions from actual geographic restrictions.
    """

    normalized = _normalize_text(
        text
    )

    mentioned = _find_mentioned_countries(
        normalized
    )

    if not mentioned:
        return []

    restricted: list[str] = []

    # --------------------------------------------------------
    # Direct "country only" patterns
    # --------------------------------------------------------

    for country in mentioned:

        country_patterns = COUNTRY_PATTERNS.get(
            country,
            [],
        )

        country_detected = False

        for pattern in country_patterns:

            if not re.search(
                pattern,
                normalized,
            ):
                continue

            match = re.search(
                pattern,
                normalized,
            )

            if not match:
                continue

            start = max(
                0,
                match.start() - 100,
            )

            end = min(
                len(normalized),
                match.end() + 100,
            )

            context = normalized[
                start:end
            ]

            if (
                re.search(
                    r"\bonly\b",
                    context,
                )
                or re.search(
                    r"\bmust\b",
                    context,
                )
                or re.search(
                    r"\b(?:resident|residents)\b",
                    context,
                )
                or re.search(
                    r"\b(?:based|located|reside)\b",
                    context,
                )
                or re.search(
                    r"\b(?:applicant|applicants|candidate|candidates)\b",
                    context,
                )
            ):
                restricted.append(
                    country
                )
                country_detected = True
                break

        if country_detected:
            continue

    # --------------------------------------------------------
    # Explicit country-only expressions
    # --------------------------------------------------------

    for country in mentioned:

        if country == "united states":

            if re.search(
                r"\b(?:us|usa|u\.s\.|united states)"
                r"\s+only\b",
                normalized,
            ):
                restricted.append(
                    country
                )

        else:

            escaped = re.escape(
                country
            )

            if re.search(
                rf"\b{escaped}\s+only\b",
                normalized,
            ):
                restricted.append(
                    country
                )

    return list(
        dict.fromkeys(
            restricted
        )
    )


def _has_us_restriction(
    text: str,
) -> bool:
    """
    Detect explicit US restriction.
    """

    return (
        "united states"
        in _extract_restricted_countries(
            text
        )
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
# GEOGRAPHY ANALYSIS
# ============================================================

def _analyze_geography(
    job: Any,
    text: str,
) -> dict[str, Any]:
    """
    Build a normalized geographic assessment.

    Important cases:

        Worldwide
            -> globally eligible

        Worldwide + Philippines only
            -> geographic conflict / review

        Nigeria only
            -> explicitly eligible

        United States only
            -> Nigeria is excluded

        Must be located in United States
            -> restriction exists, but may be reviewable
               depending on global_allowed

        Remote with no geographic scope
            -> review
    """

    location = _normalize_text(
        _get_value(
            job,
            "location",
            "",
        )
    )

    description = _normalize_text(
        text
    )

    combined_text = _normalize_text(
        f"{location} {description}"
    )

    global_scope = _has_global_scope(
        combined_text
    )

    countries_mentioned = (
        _find_mentioned_countries(
            combined_text
        )
    )

    restricted_countries = (
        _extract_restricted_countries(
            combined_text
        )
    )

    # --------------------------------------------------------
    # Identify country from the location field.
    # --------------------------------------------------------

    location_country: Optional[str] = None

    for country, patterns in COUNTRY_PATTERNS.items():

        if _contains_any(
            location,
            patterns,
        ):
            location_country = country
            break

    # --------------------------------------------------------
    # If location explicitly says "Remote - United States"
    # or similar AND the description confirms a geographic
    # requirement, treat that country as restricted.
    # --------------------------------------------------------

    if (
        location_country
        and location_country not in restricted_countries
        and _has_generic_restriction(description)
    ):
        restricted_countries.append(
            location_country
        )

    restricted_countries = list(
        dict.fromkeys(
            restricted_countries
        )
    )

    # --------------------------------------------------------
    # Determine whether the restriction is hard.
    # --------------------------------------------------------

    hard_restriction = _has_hard_restriction(
        combined_text
    )

    # --------------------------------------------------------
    # Candidate relationship to restrictions.
    # --------------------------------------------------------

    candidate_allowed = (
        CANDIDATE_COUNTRY
        in restricted_countries
    )

    candidate_excluded = (
        bool(restricted_countries)
        and CANDIDATE_COUNTRY
        not in restricted_countries
    )

    candidate_hard_excluded = (
        candidate_excluded
        and hard_restriction
    )

    # --------------------------------------------------------
    # Nigeria-specific restriction.
    # --------------------------------------------------------

    nigeria_restricted = (
        "nigeria"
        in restricted_countries
    )

    nigeria_specific = (
        nigeria_restricted
        and restricted_countries
        == ["nigeria"]
    )

    # --------------------------------------------------------
    # Other country restrictions.
    # --------------------------------------------------------

    other_country_restricted = [
        country
        for country in restricted_countries
        if country != CANDIDATE_COUNTRY
    ]

    # --------------------------------------------------------
    # Worldwide + country restriction is always a conflict.
    # It must be reviewed rather than immediately rejected.
    # --------------------------------------------------------

    global_restriction_conflict = (
        global_scope
        and bool(restricted_countries)
    )

    # --------------------------------------------------------
    # Determine geography scope.
    # --------------------------------------------------------

    scope = "unknown"

    if (
        global_scope
        and not restricted_countries
    ):
        scope = "worldwide"

    elif (
        global_scope
        and restricted_countries
    ):
        scope = "conflict"

    elif nigeria_specific:
        scope = "nigeria"

    elif restricted_countries:
        scope = "country_restricted"

    elif location_country:
        scope = "country"

    elif location:
        scope = "unspecified"

    return {
        "scope": scope,
        "global_scope": global_scope,
        "country_restricted": bool(
            restricted_countries
        ),
        "hard_restriction": hard_restriction,
        "us_restricted": (
            "united states"
            in restricted_countries
        ),
        "nigeria_restricted": nigeria_restricted,
        "restricted_countries": restricted_countries,
        "other_country_restricted": (
            other_country_restricted
        ),
        "countries_mentioned": (
            countries_mentioned
        ),
        "candidate_country": (
            CANDIDATE_COUNTRY
        ),
        "candidate_allowed": (
            candidate_allowed
        ),
        "candidate_excluded": (
            candidate_excluded
        ),
        "candidate_hard_excluded": (
            candidate_hard_excluded
        ),
        "global_restriction_conflict": (
            global_restriction_conflict
        ),
        "location_country": (
            location_country
        ),
    }


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
    2. Worldwide + country conflict
    3. Hard country exclusion
    4. Explicit Nigeria eligibility
    5. Country restriction
    6. Visa / sponsorship
    7. Explicit worldwide availability
    8. Remote with unknown geography
    9. Fallback
    """

    text = _job_text(
        job
    )

    remote = _is_remote(
        job,
        text,
    )

    reasons: list[str] = []
    warnings: list[str] = []
    disqualifiers: list[str] = []

    geography = _analyze_geography(
        job,
        text,
    )

    # ========================================================
    # 1. REMOTE REQUIREMENT
    # ========================================================

    if (
        remote_only
        and not remote
    ):

        disqualifiers.append(
            "Job is not explicitly remote."
        )

        return EligibilityResult(
            score=0,
            eligible=False,
            reasons=reasons,
            warnings=warnings,
            disqualifiers=disqualifiers,
            geography=geography,
        )

    if remote:

        reasons.append(
            "Job is explicitly remote."
        )

    # ========================================================
    # 2. WORLDWIDE + COUNTRY CONFLICT
    # ========================================================

    if geography[
        "global_restriction_conflict"
    ]:

        restricted = ", ".join(
            geography[
                "restricted_countries"
            ]
        )

        reasons.append(
            "Job explicitly states worldwide or global "
            "availability."
        )

        warnings.append(
            "Job also contains a country-specific restriction "
            f"({restricted}); global eligibility cannot be "
            "confirmed."
        )

        # IMPORTANT:
        #
        # A worldwide + country-only contradiction is NOT
        # treated as a hard rejection.
        #
        # It requires human review.
        #
        return EligibilityResult(
            score=50,
            eligible=True,
            reasons=reasons,
            warnings=warnings,
            disqualifiers=disqualifiers,
            geography=geography,
        )

    # ========================================================
    # 3. HARD COUNTRY EXCLUSION
    # ========================================================

    if geography[
        "candidate_hard_excluded"
    ]:

        restricted = ", ".join(
            geography[
                "restricted_countries"
            ]
        )

        disqualifiers.append(
            "Job is explicitly restricted to "
            f"{restricted}, which excludes Nigeria."
        )

        return EligibilityResult(
            score=0,
            eligible=False,
            reasons=reasons,
            warnings=warnings,
            disqualifiers=disqualifiers,
            geography=geography,
        )

    # ========================================================
    # 4. EXPLICIT NIGERIA ELIGIBILITY
    # ========================================================

    if geography[
        "nigeria_restricted"
    ]:

        reasons.append(
            "Job explicitly permits or targets candidates "
            "based in Nigeria."
        )

        return EligibilityResult(
            score=100,
            eligible=True,
            reasons=reasons,
            warnings=warnings,
            disqualifiers=disqualifiers,
            geography=geography,
        )

    # ========================================================
    # 5. COUNTRY RESTRICTION
    # ========================================================

    if geography[
        "country_restricted"
    ]:

        restricted = geography[
            "restricted_countries"
        ]

        restriction_description = (
            "Job has a geographic restriction involving "
            + ", ".join(
                restricted
            )
            + "."
        )

        # ----------------------------------------------------
        # Nigeria is not included in the restriction.
        #
        # If global_allowed=True, treat a generic geographic
        # restriction as reviewable.
        #
        # If global_allowed=False, reject it.
        #
        # This is specifically what allows:
        #
        # "Must be located in the United States."
        #
        # to be REVIEW when global_allowed=True.
        # ----------------------------------------------------

        if (
            geography["candidate_excluded"]
            and not geography["hard_restriction"]
        ):

            if global_allowed:

                reasons.append(
                    restriction_description
                )

                warnings.append(
                    "Job contains a country or location "
                    "restriction; confirm whether candidates "
                    "in Nigeria are permitted."
                )

                return EligibilityResult(
                    score=70,
                    eligible=True,
                    reasons=reasons,
                    warnings=warnings,
                    disqualifiers=disqualifiers,
                    geography=geography,
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
                geography=geography,
            )

        # ----------------------------------------------------
        # Candidate explicitly allowed.
        # ----------------------------------------------------

        if geography[
            "candidate_allowed"
        ]:

            reasons.append(
                "Job's geographic restriction explicitly "
                "includes Nigeria."
            )

            return EligibilityResult(
                score=100,
                eligible=True,
                reasons=reasons,
                warnings=warnings,
                disqualifiers=disqualifiers,
                geography=geography,
            )

    # ========================================================
    # 6. VISA / SPONSORSHIP
    # ========================================================

    if _has_visa_requirement(
        text
    ):

        reasons.append(
            "Job mentions a visa or sponsorship requirement."
        )

        warnings.append(
            "Visa or work authorization requirements must "
            "be verified."
        )

        return EligibilityResult(
            score=70,
            eligible=True,
            reasons=reasons,
            warnings=warnings,
            disqualifiers=disqualifiers,
            geography=geography,
        )

    # ========================================================
    # 7. EXPLICIT WORLDWIDE JOB
    # ========================================================

    if geography[
        "global_scope"
    ]:

        reasons.append(
            "Job explicitly supports worldwide or global "
            "employment."
        )

        return EligibilityResult(
            score=100,
            eligible=True,
            reasons=reasons,
            warnings=warnings,
            disqualifiers=disqualifiers,
            geography=geography,
        )

    # ========================================================
    # 8. REMOTE WITH UNKNOWN GEOGRAPHIC SCOPE
    # ========================================================

    if remote:

        reasons.append(
            "Job is remote, but no explicit geographic "
            "scope was identified."
        )

        warnings.append(
            "Geographic eligibility is not explicitly "
            "confirmed; verify whether candidates in "
            "Nigeria are accepted."
        )

        return EligibilityResult(
            score=70 if global_allowed else 50,
            eligible=True,
            reasons=reasons,
            warnings=warnings,
            disqualifiers=disqualifiers,
            geography=geography,
        )

    # ========================================================
    # 9. FALLBACK
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
        geography=geography,
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

    global_allowed defaults to False so an unverified
    geographic restriction is not silently treated as global.
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
        "geography": result.geography,
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

    Original job fields are preserved.

    Additional fields:

        eligible
        eligibility_score
        eligibility_eligible
        eligibility_reasons
        eligibility_warnings
        eligibility_disqualifiers
        geography
    """

    if isinstance(
        job,
        dict,
    ):

        enriched_job = dict(
            job
        )

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

                enriched_job[
                    field_name
                ] = getattr(
                    job,
                    field_name,
                )

    result = evaluate_eligibility(
        enriched_job,
        remote_only=remote_only,
        global_allowed=global_allowed,
    )

    enriched_job[
        "eligible"
    ] = result.eligible

    enriched_job[
        "eligibility_score"
    ] = result.score

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

    enriched_job[
        "geography"
    ] = result.geography

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