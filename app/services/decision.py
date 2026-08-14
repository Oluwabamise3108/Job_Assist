"""
Job decision engine.

This module converts the outputs of:

    matcher
    eligibility
    risk

into one deterministic recommendation:

    APPLY
    REVIEW
    POSSIBLE
    SKIP

Decision priority:

    1. Geographic hard rejection
    2. Experience hard rejection
    3. Critical risk
    4. High risk
    5. Unclear geography
    6. Match quality
    7. Default fallback

The decision engine does NOT calculate match scores.
It does NOT modify eligibility scores.
It does NOT modify risk scores.

It is strictly an orchestration layer.
"""


from typing import Any


# ---------------------------------------------------------------------------
# DECISION THRESHOLDS
# ---------------------------------------------------------------------------

APPLY_THRESHOLD = 80
REVIEW_THRESHOLD = 60
POSSIBLE_THRESHOLD = 40

UNCLEAR_ELIGIBILITY_SCORE = 50
HARD_REJECT_ELIGIBILITY_SCORE = 0


# ---------------------------------------------------------------------------
# NORMALIZATION HELPERS
# ---------------------------------------------------------------------------

def _safe_score(
    value: Any,
    default: float = 0,
) -> float:
    """
    Safely convert a score-like value to float.
    """
    try:
        return float(
            value
            if value is not None
            else default
        )
    except (
        TypeError,
        ValueError,
    ):
        return float(default)


def _normalize_severity(
    value: Any,
) -> str:
    """
    Normalize risk severity.
    """
    return str(
        value or "low"
    ).strip().lower()


def _normalize_status(
    value: Any,
) -> str:
    """
    Normalize status values.
    """
    return str(
        value or ""
    ).strip().lower()


def _as_flags(
    value: Any,
) -> list[str]:
    """
    Convert risk flags into a clean list of strings.
    """
    if value is None:
        return []

    if isinstance(value, str):
        value = [value]

    if not isinstance(value, (list, tuple, set)):
        return [str(value)]

    return [
        str(flag).strip()
        for flag in value
        if str(flag).strip()
    ]


def _result(
    recommendation: str,
    *,
    hard_reject: bool = False,
    reasons: list[str] | None = None,
) -> dict:
    """
    Build the canonical decision structure.
    """
    return {
        "recommendation": recommendation,
        "hard_reject": hard_reject,
        "hard_reject_reasons": reasons or [],
    }


# ---------------------------------------------------------------------------
# HARD REJECTION HELPERS
# ---------------------------------------------------------------------------

def _geographic_rejection(
    eligibility_score: float,
) -> dict | None:
    """
    Reject jobs that are explicitly geographically ineligible.
    """
    if eligibility_score != HARD_REJECT_ELIGIBILITY_SCORE:
        return None

    return _result(
        "SKIP",
        hard_reject=True,
        reasons=[
            "Candidate is not geographically eligible."
        ],
    )


def _experience_rejection(
    experience_status: str,
) -> dict | None:
    """
    Reject jobs requiring more experience than the candidate has.
    """
    if experience_status != "insufficient":
        return None

    return _result(
        "SKIP",
        hard_reject=True,
        reasons=[
            (
                "Candidate does not meet the required "
                "experience level."
            )
        ],
    )


def _critical_risk_rejection(
    risk_severity: str,
    risk_flags: list[str],
) -> dict | None:
    """
    Critical risk is a hard rejection.
    """
    if risk_severity != "critical":
        return None

    if risk_flags:
        reason = (
            "Job has critical risk indicators: "
            + ", ".join(risk_flags)
            + "."
        )
    else:
        reason = (
            "Job has a critical risk indicator."
        )

    return _result(
        "SKIP",
        hard_reject=True,
        reasons=[reason],
    )


# ---------------------------------------------------------------------------
# HIGH RISK
# ---------------------------------------------------------------------------

def _handle_high_risk(
    risk_severity: str,
    match_score: float,
) -> dict | None:
    """
    High risk should not automatically become a hard rejection.

    A high-risk job is still potentially useful when the match is
    exceptionally strong, but it must never receive APPLY.

    Rules:

        high risk + match >= 80
            -> REVIEW

        high risk + match < 80
            -> SKIP
    """
    if risk_severity != "high":
        return None

    if match_score >= APPLY_THRESHOLD:
        return _result(
            "REVIEW",
            reasons=[
                (
                    "Strong candidate match, but the job "
                    "contains high-risk indicators and requires "
                    "manual review."
                )
            ],
        )

    return _result(
        "SKIP",
        reasons=[
            (
                "Job contains high-risk indicators and does "
                "not have a sufficiently strong candidate match."
            )
        ],
    )


# ---------------------------------------------------------------------------
# GEOGRAPHIC UNCERTAINTY
# ---------------------------------------------------------------------------

def _handle_unclear_geography(
    eligibility_score: float,
) -> dict | None:
    """
    Unclear geography requires manual review.

    This intentionally overrides APPLY because a high match
    does not compensate for unknown geographic eligibility.
    """
    if eligibility_score != UNCLEAR_ELIGIBILITY_SCORE:
        return None

    return _result(
        "REVIEW",
        reasons=[
            (
                "Job is remote, but its geographic scope is "
                "not explicitly confirmed."
            )
        ],
    )


# ---------------------------------------------------------------------------
# MATCH-BASED DECISION
# ---------------------------------------------------------------------------

def _match_based_decision(
    match_score: float,
) -> dict:
    """
    Convert the match score into a recommendation.
    """
    if match_score >= APPLY_THRESHOLD:
        return _result(
            "APPLY",
            reasons=[
                (
                    f"Strong candidate match "
                    f"({int(match_score)}%)."
                )
            ],
        )

    if match_score >= REVIEW_THRESHOLD:
        return _result(
            "REVIEW",
            reasons=[
                (
                    f"Good candidate match "
                    f"({int(match_score)}%), but manual "
                    "review is recommended."
                )
            ],
        )

    if match_score >= POSSIBLE_THRESHOLD:
        return _result(
            "POSSIBLE",
            reasons=[
                (
                    f"Partial candidate match "
                    f"({int(match_score)}%)."
                )
            ],
        )

    return _result(
        "SKIP",
        reasons=[
            (
                f"Candidate match is too weak "
                f"({int(match_score)}%)."
            )
        ],
    )


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def make_decision(
    *,
    match: dict,
    eligibility: dict,
    risk: dict,
) -> dict:
    """
    Produce the final job recommendation.

    Decision hierarchy:

        HARD REJECTION
            geographic
            experience
            critical risk

        MANUAL REVIEW / RISK
            high risk
            unclear geography

        MATCH QUALITY
            80+  -> APPLY
            60+  -> REVIEW
            40+  -> POSSIBLE
            <40  -> SKIP
    """

    # ---------------------------------------------------------------
    # NORMALIZE INPUTS
    # ---------------------------------------------------------------

    match_score = _safe_score(
        match.get(
            "score",
            0,
        )
    )

    eligibility_score = _safe_score(
        eligibility.get(
            "eligibility_score",
            eligibility.get(
                "score",
                0,
            ),
        )
    )

    risk_severity = _normalize_severity(
        risk.get(
            "severity",
            "low",
        )
    )

    risk_flags = _as_flags(
        risk.get(
            "flags",
            [],
        )
    )

    experience = match.get(
        "experience",
        {},
    )

    if not isinstance(
        experience,
        dict,
    ):
        experience = {}

    experience_status = _normalize_status(
        experience.get(
            "status",
            "",
        )
    )

    # ---------------------------------------------------------------
    # 1. GEOGRAPHIC HARD REJECTION
    # ---------------------------------------------------------------

    decision = _geographic_rejection(
        eligibility_score
    )

    if decision is not None:
        return decision

    # ---------------------------------------------------------------
    # 2. EXPERIENCE HARD REJECTION
    # ---------------------------------------------------------------

    decision = _experience_rejection(
        experience_status
    )

    if decision is not None:
        return decision

    # ---------------------------------------------------------------
    # 3. CRITICAL RISK
    # ---------------------------------------------------------------

    decision = _critical_risk_rejection(
        risk_severity,
        risk_flags,
    )

    if decision is not None:
        return decision

    # ---------------------------------------------------------------
    # 4. HIGH RISK
    # ---------------------------------------------------------------

    decision = _handle_high_risk(
        risk_severity,
        match_score,
    )

    if decision is not None:
        return decision

    # ---------------------------------------------------------------
    # 5. UNCLEAR GEOGRAPHY
    # ---------------------------------------------------------------

    decision = _handle_unclear_geography(
        eligibility_score
    )

    if decision is not None:
        return decision

    # ---------------------------------------------------------------
    # 6. MATCH QUALITY
    # ---------------------------------------------------------------

    return _match_based_decision(
        match_score
    )


__all__ = [
    "make_decision",
    "APPLY_THRESHOLD",
    "REVIEW_THRESHOLD",
    "POSSIBLE_THRESHOLD",
    "UNCLEAR_ELIGIBILITY_SCORE",
    "HARD_REJECT_ELIGIBILITY_SCORE",
]