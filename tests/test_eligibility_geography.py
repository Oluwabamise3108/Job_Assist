from app.services.eligibility import (
    evaluate_eligibility,
)


def make_job(
    *,
    title="Customer Support Specialist",
    location="Worldwide",
    description="Fully remote customer support role.",
    is_remote=True,
):
    return {
        "title": title,
        "company": "Test Company",
        "location": location,
        "description": description,
        "is_remote": is_remote,
    }


def test_worldwide_job_is_globally_eligible():

    result = evaluate_eligibility(
        make_job(
            location="Worldwide",
            description=(
                "Fully remote. "
                "Open to candidates worldwide."
            ),
        ),
        remote_only=True,
        global_allowed=True,
    )

    assert result.eligible is True
    assert result.score == 100
    assert result.geography["scope"] == "worldwide"


def test_philippines_restriction_is_not_global():

    result = evaluate_eligibility(
        make_job(
            location="Worldwide",
            description=(
                "Fully remote and open worldwide. "
                "Remote Philippines only."
            ),
        ),
        remote_only=True,
        global_allowed=True,
    )

    assert result.geography[
        "global_restriction_conflict"
    ] is True

    assert result.score == 50
    assert result.eligible is True

    assert result.warnings


def test_explicit_nigeria_restriction_is_allowed():

    result = evaluate_eligibility(
        make_job(
            location="Nigeria",
            description=(
                "Remote role. "
                "Candidates must be based in Nigeria."
            ),
        ),
        remote_only=True,
        global_allowed=True,
    )

    assert result.eligible is True


def test_us_only_job_is_not_globally_eligible():

    result = evaluate_eligibility(
        make_job(
            location="United States",
            description=(
                "Remote role. "
                "US residents only."
            ),
        ),
        remote_only=True,
        global_allowed=True,
    )

    assert result.eligible is False
    assert result.score == 0
    assert result.disqualifiers


def test_remote_without_geographic_scope_requires_review():

    result = evaluate_eligibility(
        make_job(
            location="Remote",
            description=(
                "Fully remote customer support role."
            ),
        ),
        remote_only=True,
        global_allowed=True,
    )

    assert result.eligible is True
    assert result.score == 70
    assert result.warnings


def test_non_remote_job_is_rejected():

    result = evaluate_eligibility(
        make_job(
            location="Lagos",
            description=(
                "Customer Support Specialist. "
                "On-site role."
            ),
            is_remote=False,
        ),
        remote_only=True,
        global_allowed=True,
    )

    assert result.eligible is False
    assert result.score == 0