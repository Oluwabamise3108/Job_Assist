from app.services.matcher import (
    analyze_match,
)


def test_strong_customer_support_role():
    result = analyze_match(
        title="Customer Support Specialist",
        description="""
        We are looking for a Customer Support Specialist with
        3+ years of experience.

        The successful candidate will provide customer service
        through phone and email, manage customer inquiries,
        and use Zendesk and HubSpot.
        """
    )

    assert result["score"] >= 75

    assert "customer_service" in result[
        "matched_skills"
    ]

    assert "phone_support" in result[
        "matched_skills"
    ]

    assert "email_support" in result[
        "matched_skills"
    ]

    assert "zendesk" in result[
        "matched_tools"
    ]

    assert "hubspot" in result[
        "matched_tools"
    ]

    assert result["experience"]["status"] == (
        "meets_requirement"
    )


def test_too_senior_role():
    result = analyze_match(
        title="Senior Customer Support Specialist",
        description="""
        We are looking for a customer support
        professional with 8+ years of experience.
        """
    )

    assert result["experience"]["status"] == (
        "insufficient"
    )

    assert result["experience"]["required_years"] == 8

    assert result["experience"]["candidate_years"] == 5