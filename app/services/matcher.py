from typing import Any
import re


CANDIDATE_PROFILE = {
    "experience_years": 5,

    "target_titles": [
        "customer service representative",
        "customer support representative",
        "customer support specialist",
        "customer experience specialist",
        "customer care representative",
        "customer care specialist",
        "client support specialist",
        "client services representative",
        "customer success associate",
        "customer success specialist",
        "support specialist",
        "member services representative",
        "customer operations specialist",
    ],

    "skills": {
        "customer_service": [
            "customer service",
            "customer care",
            "customer inquiries",
            "customer inquiry",
            "assist customers",
            "assisting customers",
            "help customers",
            "helping customers",
            "customer experience",
        ],

        "customer_support": [
            "customer support",
            "support customers",
            "supporting customers",
            "customer assistance",
            "customer issues",
            "resolve customer issues",
            "resolving customer issues",
            "handling customer issues",
            "handle customer issues",
        ],

        "email_support": [
            "email support",
            "email customer support",
            "support via email",
            "support through email",
            "customer emails",
            "respond to emails",
            "responding to emails",
            "email inquiries",
            "email inquiry",
            "email",
        ],

        "phone_support": [
            "phone support",
            "telephone support",
            "voice support",
            "support by phone",
            "support via phone",
            "support through phone",
            "through phone",
            "customer calls",
            "handling calls",
            "handle calls",
            "phone inquiries",
        ],

        "account_management": [
            "account management",
            "manage customer accounts",
            "managing customer accounts",
            "customer account management",
            "account support",
            "manage accounts",
            "managing accounts",
        ],

        "retention": [
            "customer retention",
            "retention",
            "retain customers",
            "customer loyalty",
        ],

        "de_escalation": [
            "de-escalation",
            "de escalation",
            "escalation management",
            "conflict resolution",
            "handling difficult customers",
        ],

        "first_contact_resolution": [
            "first contact resolution",
            "first call resolution",
            "resolve issues on first contact",
            "resolve issues on the first contact",
        ],

        "case_documentation": [
            "case documentation",
            "document customer interactions",
            "documenting customer interactions",
            "case notes",
            "customer records",
            "document cases",
        ],

        "quality_assurance": [
            "quality assurance",
            "quality control",
            "quality monitoring",
            "quality standards",
        ],

        "billing": [
            "billing",
            "billing support",
            "billing inquiries",
            "billing issues",
            "payment inquiries",
            "payment support",
        ],

        "insurance": [
            "insurance",
            "insurance support",
            "insurance verification",
            "health insurance",
        ],

        "healthcare": [
            "healthcare",
            "health care",
            "medical",
            "health services",
        ],
    },

    "tools": [
        "ringcentral",
        "hdms",
        "hubspot",
        "jira",
        "zendesk",
        "salesforce",
        "microsoft office",
        "google workspace",
    ],

    "industries": [
        "healthcare",
        "saas",
        "technology",
        "financial services",
        "ecommerce",
    ],
}


# ---------------------------------------------------------------------------
# SCORE WEIGHTS
# ---------------------------------------------------------------------------

MAX_SCORE = 100

TITLE_MAX = 25
SKILLS_MAX = 35
TOOLS_MAX = 10
INDUSTRY_MAX = 10
EXPERIENCE_MAX = 20


def normalize(text: str) -> str:
    """
    Normalize text for reliable matching.

    - Converts to lowercase
    - Collapses repeated whitespace
    - Strips leading/trailing whitespace
    """
    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(text).lower(),
    ).strip()


def _contains_any(
    text: str,
    patterns: list[str],
) -> bool:
    """
    Return True when at least one pattern appears in text.
    """
    normalized_text = normalize(text)

    return any(
        normalize(pattern) in normalized_text
        for pattern in patterns
    )


def _matched_aliases(
    text: str,
    aliases: list[str],
) -> list[str]:
    """
    Return unique aliases found in text.
    """
    normalized_text = normalize(text)

    matched = []

    for alias in aliases:
        normalized_alias = normalize(alias)

        if (
            normalized_alias
            and normalized_alias in normalized_text
        ):
            matched.append(
                normalized_alias
            )

    return list(
        dict.fromkeys(matched)
    )


def find_required_experience(
    text: str,
) -> int | None:
    """
    Extract the highest explicit experience requirement.

    Examples:
        3 years experience -> 3
        3+ years experience -> 3
        minimum of 4 years -> 4
        at least 5 years -> 5
        2-4 years experience -> 4
    """
    text = normalize(text)

    patterns = [
        r"(\d+)\s*[-–]\s*(\d+)\s*years?\s+(?:of\s+)?experience",
        r"(\d+)\+?\s*years?\s+(?:of\s+)?experience",
        r"minimum\s+(?:of\s+)?(\d+)\s*years?",
        r"at least\s+(\d+)\s*years?",
    ]

    values = []

    for pattern in patterns:
        matches = re.findall(
            pattern,
            text,
        )

        for match in matches:

            if isinstance(match, tuple):
                for value in match:
                    if str(value).isdigit():
                        values.append(
                            int(value)
                        )
            else:
                if str(match).isdigit():
                    values.append(
                        int(match)
                    )

    return max(values) if values else None


def match_title(
    title: str,
) -> tuple[int, list[str]]:
    """
    Score how closely the job title matches the candidate's
    target roles.

    Exact target-title matches receive the strongest score.
    Broad customer/support terminology receives partial credit.
    """
    title = normalize(title)

    if not title:
        return 0, []

    exact_matches = []

    for role in CANDIDATE_PROFILE[
        "target_titles"
    ]:
        normalized_role = normalize(role)

        if normalized_role in title:
            exact_matches.append(
                normalized_role
            )

    exact_matches = list(
        dict.fromkeys(exact_matches)
    )

    if exact_matches:
        return TITLE_MAX, exact_matches

    broad_terms = [
        "customer",
        "support",
        "service",
        "success",
        "client",
    ]

    broad_matches = [
        term
        for term in broad_terms
        if term in title
    ]

    if len(broad_matches) >= 2:
        return 15, broad_matches

    if len(broad_matches) == 1:
        return 8, broad_matches

    return 0, []


def match_skills(
    text: str,
) -> tuple[int, list[str]]:
    """
    Match the job description against the candidate's
    categorized customer-support skill profile.
    """
    text = normalize(text)

    matched = []

    for skill, aliases in CANDIDATE_PROFILE[
        "skills"
    ].items():

        if _contains_any(
            text,
            aliases,
        ):
            matched.append(skill)

    matched = list(
        dict.fromkeys(matched)
    )

    count = len(matched)

    if count >= 7:
        score = SKILLS_MAX
    elif count == 6:
        score = 32
    elif count == 5:
        score = 29
    elif count == 4:
        score = 25
    elif count == 3:
        score = 22
    elif count == 2:
        score = 14
    elif count == 1:
        score = 7
    else:
        score = 0

    return score, matched


def match_tools(
    text: str,
) -> tuple[int, list[str]]:
    """
    Match known tools from the candidate profile.
    """
    text = normalize(text)

    matched = [
        tool
        for tool in CANDIDATE_PROFILE["tools"]
        if normalize(tool) in text
    ]

    matched = list(
        dict.fromkeys(matched)
    )

    count = len(matched)

    if count >= 4:
        score = TOOLS_MAX

    elif count == 3:
        score = 8

    elif count == 2:
        score = 6

    elif count == 1:
        score = 4

    else:
        score = 0

    return score, matched


def match_industry(
    text: str,
) -> tuple[int, list[str]]:
    """
    Industry is a positive bonus.

    Lack of an industry match is neutral rather than negative.
    """
    text = normalize(text)

    matched = [
        industry
        for industry in CANDIDATE_PROFILE[
            "industries"
        ]
        if normalize(industry) in text
    ]

    matched = list(
        dict.fromkeys(matched)
    )

    if len(matched) >= 2:
        score = INDUSTRY_MAX

    elif len(matched) == 1:
        score = 6

    else:
        score = 0

    return score, matched


def match_experience(
    text: str,
) -> tuple[int, dict[str, Any]]:
    """
    Compare explicit job requirements against candidate experience.
    """
    required = find_required_experience(
        text
    )

    candidate = int(
        CANDIDATE_PROFILE[
            "experience_years"
        ]
    )

    if required is None:
        return 12, {
            "required_years": None,
            "candidate_years": candidate,
            "status": "not_specified",
        }

    if required > candidate:
        return 0, {
            "required_years": required,
            "candidate_years": candidate,
            "status": "insufficient",
        }

    if required == candidate:
        return 18, {
            "required_years": required,
            "candidate_years": candidate,
            "status": "meets_requirement",
        }

    return EXPERIENCE_MAX, {
        "required_years": required,
        "candidate_years": candidate,
        "status": "meets_requirement",
    }


def _apply_seniority_adjustment(
    title: str,
    description: str,
    score: int,
) -> tuple[int, dict[str, Any]]:
    """
    Detect seniority signals for reporting only.

    Seniority does not directly reduce the match score.
    Explicit experience requirements are handled separately.
    """
    combined = normalize(
        f"{title} {description}"
    )

    senior_terms = [
        "senior",
        "sr.",
        "lead",
        "manager",
        "director",
        "head of",
        "principal",
    ]

    matched = [
        term
        for term in senior_terms
        if term in combined
    ]

    matched = list(
        dict.fromkeys(matched)
    )

    return score, {
        "matched_terms": matched,
        "adjustment": 0,
    }


def analyze_match(
    title: str,
    description: str,
) -> dict[str, Any]:
    """
    Produce a normalized 0-100 job-match score.

    Scoring model:

        Title       25
        Skills      30
        Tools       10
        Industry    10
        Experience  25
        ----------------
        Total      100

    The function preserves the existing return structure expected
    by the ingestion and discovery layers.
    """
    title = normalize(title)
    description = normalize(description)

    text = f"{title} {description}".strip()

    title_score, titles = match_title(
        title
    )

    skill_score, skills = match_skills(
        text
    )

    tool_score, tools = match_tools(
        text
    )

    industry_score, industries = match_industry(
        text
    )

    experience_score, experience = match_experience(
        text
    )

    raw_score = (
        title_score
        + skill_score
        + tool_score
        + industry_score
        + experience_score
    )

    # The component maxima sum to exactly 100.
    base_score = min(
        MAX_SCORE,
        max(
            0,
            raw_score,
        ),
    )

    score, seniority = _apply_seniority_adjustment(
        title=title,
        description=description,
        score=base_score,
    )

    return {
        "score": score,

        "breakdown": {
            "title": title_score,
            "skills": skill_score,
            "tools": tool_score,
            "industry": industry_score,
            "experience": experience_score,
            "seniority_adjustment": seniority[
                "adjustment"
            ],
        },

        "matched_titles": titles,

        "matched_skills": skills,

        "matched_tools": tools,

        "matched_industries": industries,

        "experience": experience,

        "seniority": seniority,
    }