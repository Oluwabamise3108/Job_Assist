from app.services.eligibility import (
    apply_eligibility,
    evaluate_eligibility,
)


def test_remote_job_is_eligible():

    job = {
        "title": "Customer Support Specialist",
        "company": "Acme",
        "description": "Fully remote customer support role.",
        "is_remote": True,
    }

    result = evaluate_eligibility(
        job,
        remote_only=True,
        global_allowed=True,
    )

    assert result.eligible is True
    assert result.score >= 70
    assert result.disqualifiers == []


def test_non_remote_job_is_disqualified():

    job = {
        "title": "Customer Support Specialist",
        "company": "Acme",
        "description": "Office-based customer support role.",
        "is_remote": False,
    }

    result = evaluate_eligibility(
        job,
        remote_only=True,
        global_allowed=True,
    )

    assert result.eligible is False
    assert result.score == 0
    assert result.disqualifiers


def test_worldwide_remote_job_is_eligible():

    job = {
        "title": "Customer Support Specialist",
        "company": "Acme",
        "description": (
            "Remote worldwide. "
            "Applicants may work from anywhere."
        ),
        "is_remote": True,
    }

    result = evaluate_eligibility(
        job,
        remote_only=True,
        global_allowed=True,
    )

    assert result.eligible is True
    assert result.score >= 70


def test_location_restriction_creates_warning():

    job = {
        "title": "Customer Support Specialist",
        "company": "Acme",
        "description": (
            "Remote role. "
            "Must be located in the United States."
        ),
        "is_remote": True,
    }

    result = evaluate_eligibility(
        job,
        remote_only=True,
        global_allowed=True,
    )

    assert result.eligible is True
    assert result.warnings
    assert any(
        "country" in warning.lower()
        or "location" in warning.lower()
        for warning in result.warnings
    )


def test_location_restriction_can_disqualify():

    job = {
        "title": "Customer Support Specialist",
        "company": "Acme",
        "description": (
            "Remote role. "
            "Must be located in the United States."
        ),
        "is_remote": True,
    }

    result = evaluate_eligibility(
        job,
        remote_only=True,
        global_allowed=False,
    )

    assert result.eligible is False
    assert result.disqualifiers


def test_visa_requirement_reduces_score():

    job = {
        "title": "Customer Support Specialist",
        "company": "Acme",
        "description": (
            "Remote role. "
            "Visa sponsorship required."
        ),
        "is_remote": True,
    }

    result = evaluate_eligibility(
        job,
        remote_only=True,
        global_allowed=True,
    )

    assert result.eligible is True
    assert result.score < 100
    assert result.warnings


def test_apply_eligibility_preserves_job():

    job = {
        "title": "Customer Support Specialist",
        "company": "Acme",
        "description": "Fully remote.",
        "is_remote": True,
        "match_score": 90,
    }

    result = apply_eligibility(
        job,
        remote_only=True,
        global_allowed=True,
    )

    assert result["title"] == (
        "Customer Support Specialist"
    )

    assert result["match_score"] == 90

    assert "eligibility_score" in result
    assert "eligible" in result
    assert "eligibility_reasons" in result
    assert "eligibility_warnings" in result
    assert "eligibility_disqualifiers" in result