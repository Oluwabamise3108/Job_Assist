from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MatchResult:
    score: int
    matched_keywords: list[str] = field(default_factory=list)
    match_reasons: list[str] = field(default_factory=list)


# =========================================================
# SCORING WEIGHTS
# =========================================================
#
# Title is the strongest signal.
#
# A single exact keyword/phrase in the job title should be
# strong enough to pass the default 70 threshold.
#
# Maximum:
#
# Title       = 70
# Description = 20
# Company     = 5
# Coverage    = 5
#
# Total       = 100
# =========================================================

TITLE_WEIGHT = 70
DESCRIPTION_WEIGHT = 20
COMPANY_WEIGHT = 5
KEYWORD_COVERAGE_WEIGHT = 5


def _get_job_value(
    job: Any,
    key: str,
    default: Any = None,
) -> Any:
    """
    Safely read a value from either:

        - dict
        - object with attributes
    """

    if isinstance(job, dict):
        return job.get(key, default)

    return getattr(
        job,
        key,
        default,
    )


def _normalize_text(
    value: Any,
) -> str:
    """
    Normalize text before matching.

    Examples:

        Customer Support
        customer-support
        CUSTOMER SUPPORT

    become comparable.
    """

    text = str(
        value or ""
    ).lower()

    # Convert punctuation/hyphens into spaces.
    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    )

    # Collapse repeated whitespace.
    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def _normalize_keyword(
    keyword: Any,
) -> str:
    return _normalize_text(
        keyword
    )


def _contains_phrase(
    text: str,
    phrase: str,
) -> bool:
    """
    Check whether a complete phrase exists.

    Example:

        "customer support specialist"

    matches:

        "customer support"

    but avoids arbitrary substring matches.
    """

    if not text or not phrase:
        return False

    return re.search(
        rf"\b{re.escape(phrase)}\b",
        text,
    ) is not None


def score_job(
    job: Any,
    keywords: list[str],
) -> MatchResult:
    """
    Calculate a deterministic 0-100 job relevance score.

    Scoring:

        Title relevance       0-70
        Description relevance 0-20
        Company relevance     0-5
        Keyword coverage      0-5

        Maximum                100
    """

    title = _normalize_text(
        _get_job_value(
            job,
            "title",
            "",
        )
    )

    description = _normalize_text(
        _get_job_value(
            job,
            "description",
            "",
        )
    )

    company = _normalize_text(
        _get_job_value(
            job,
            "company",
            "",
        )
    )

    # ---------------------------------------------------------
    # NORMALIZE KEYWORDS
    # ---------------------------------------------------------

    normalized_keywords = []

    for keyword in keywords or []:

        normalized = _normalize_keyword(
            keyword
        )

        if (
            normalized
            and normalized
            not in normalized_keywords
        ):
            normalized_keywords.append(
                normalized
            )

    # No keywords = no relevance.
    if not normalized_keywords:

        return MatchResult(
            score=0,
            matched_keywords=[],
            match_reasons=[
                "No search keywords supplied"
            ],
        )

    # ---------------------------------------------------------
    # MATCH KEYWORDS
    # ---------------------------------------------------------

    matched_keywords = []

    title_matches = 0
    description_matches = 0
    company_matches = 0

    for keyword in normalized_keywords:

        in_title = _contains_phrase(
            title,
            keyword,
        )

        in_description = _contains_phrase(
            description,
            keyword,
        )

        in_company = _contains_phrase(
            company,
            keyword,
        )

        # -----------------------------------------------------
        # PRIORITY
        # -----------------------------------------------------
        #
        # A keyword is counted in its strongest location only.
        #
        # title > description > company
        #
        # This prevents one keyword from being counted three
        # times.
        # -----------------------------------------------------

        if in_title:

            title_matches += 1

            matched_keywords.append(
                keyword
            )

        elif in_description:

            description_matches += 1

            matched_keywords.append(
                keyword
            )

        elif in_company:

            company_matches += 1

            matched_keywords.append(
                keyword
            )

    total_keywords = len(
        normalized_keywords
    )

    # ---------------------------------------------------------
    # TITLE SCORE
    # ---------------------------------------------------------

    title_score = 0

    if title_matches:

        title_score = round(
            TITLE_WEIGHT
            * (
                title_matches
                / total_keywords
            )
        )

    # ---------------------------------------------------------
    # DESCRIPTION SCORE
    # ---------------------------------------------------------

    description_score = 0

    if description_matches:

        description_score = round(
            DESCRIPTION_WEIGHT
            * (
                description_matches
                / total_keywords
            )
        )

    # ---------------------------------------------------------
    # COMPANY SCORE
    # ---------------------------------------------------------

    company_score = 0

    if company_matches:

        company_score = round(
            COMPANY_WEIGHT
            * (
                company_matches
                / total_keywords
            )
        )

    # ---------------------------------------------------------
    # KEYWORD COVERAGE
    # ---------------------------------------------------------

    coverage = (
        len(
            set(matched_keywords)
        )
        / total_keywords
    )

    coverage_score = round(
        KEYWORD_COVERAGE_WEIGHT
        * coverage
    )

    # ---------------------------------------------------------
    # FINAL SCORE
    # ---------------------------------------------------------

    score = (
        title_score
        + description_score
        + company_score
        + coverage_score
    )

    score = max(
        0,
        min(
            100,
            score,
        ),
    )

    # ---------------------------------------------------------
    # REASONS
    # ---------------------------------------------------------

    reasons = []

    if title_matches:

        reasons.append(
            f"{title_matches} keyword(s) "
            "matched in title"
        )

    if description_matches:

        reasons.append(
            f"{description_matches} keyword(s) "
            "matched in description"
        )

    if company_matches:

        reasons.append(
            f"{company_matches} keyword(s) "
            "matched in company"
        )

    if not matched_keywords:

        reasons.append(
            "No requested keywords matched"
        )

    return MatchResult(
        score=score,
        matched_keywords=matched_keywords,
        match_reasons=reasons,
    )


def apply_match_score(
    job: Any,
    keywords: list[str],
) -> dict:
    """
    Score a job and return an enriched dictionary.

    Original job fields are preserved.
    """

    result = score_job(
        job,
        keywords,
    )

    if isinstance(job, dict):

        enriched = dict(job)

    else:

        enriched = {
            key: getattr(
                job,
                key,
            )
            for key in dir(job)
            if not key.startswith("_")
            and not callable(
                getattr(
                    job,
                    key,
                    None,
                )
            )
        }

    enriched["match_score"] = (
        result.score
    )

    enriched["matched_keywords"] = (
        result.matched_keywords
    )

    enriched["match_reasons"] = (
        result.match_reasons
    )

    return enriched