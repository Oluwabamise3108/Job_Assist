from app.services.decision import (
    make_decision,
)


def test_strong_eligible_job_is_apply():

    match = {
        "score": 90,
        "experience": {
            "status": "meets_requirement"
        },
    }

    eligibility = {
        "eligibility_score": 100,
        "status": "eligible",
    }

    risk = {
        "severity": "low",
        "flags": [],
    }

    result = make_decision(
        match=match,
        eligibility=eligibility,
        risk=risk,
    )

    assert result["recommendation"] == "APPLY"

    assert result["hard_reject"] is False


def test_ineligible_job_is_skip():

    match = {
        "score": 90,
        "experience": {
            "status": "meets_requirement"
        },
    }

    eligibility = {
        "eligibility_score": 0,
        "status": "not_eligible",
    }

    risk = {
        "severity": "low",
        "flags": [],
    }

    result = make_decision(
        match=match,
        eligibility=eligibility,
        risk=risk,
    )

    assert result["recommendation"] == "SKIP"

    assert result["hard_reject"] is True


def test_unclear_geography_is_review():

    match = {
        "score": 84,
        "experience": {
            "status": "meets_requirement"
        },
    }

    eligibility = {
        "eligibility_score": 50,
        "status": "uncertain",
    }

    risk = {
        "severity": "low",
        "flags": [],
    }

    result = make_decision(
        match=match,
        eligibility=eligibility,
        risk=risk,
    )

    assert result["recommendation"] == "REVIEW"

    assert result["hard_reject"] is False


def test_too_senior_is_skip():

    match = {
        "score": 85,
        "experience": {
            "status": "insufficient"
        },
    }

    eligibility = {
        "eligibility_score": 100,
        "status": "eligible",
    }

    risk = {
        "severity": "low",
        "flags": [],
    }

    result = make_decision(
        match=match,
        eligibility=eligibility,
        risk=risk,
    )

    assert result["recommendation"] == "SKIP"

    assert result["hard_reject"] is True


def test_critical_risk_is_skip():

    match = {
        "score": 90,
        "experience": {
            "status": "meets_requirement"
        },
    }

    eligibility = {
        "eligibility_score": 100,
        "status": "eligible",
    }

    risk = {
        "severity": "critical",
        "flags": ["upfront_payment"],
    }

    result = make_decision(
        match=match,
        eligibility=eligibility,
        risk=risk,
    )

    assert result["recommendation"] == "SKIP"

    assert result["hard_reject"] is True