from app.services.risk import (
    analyze_risk,
)


def test_clean_job_has_low_risk():

    result = analyze_risk(
        """
        Customer Support Specialist.
        Full-time remote position.
        Competitive salary and benefits.
        """
    )

    assert result["severity"] == "low"

    assert result["flags"] == []


def test_upfront_payment_is_critical():

    result = analyze_risk(
        """
        Customer Support Representative.
        Applicants must pay a $100 registration fee
        before beginning the hiring process.
        """
    )

    assert result["severity"] == "critical"

    assert "upfront_payment" in result["flags"]


def test_whatsapp_only_application_is_high_risk():

    result = analyze_risk(
        """
        Remote customer service job.
        Contact the recruiter through WhatsApp to apply.
        """
    )

    assert result["severity"] == "high"

    assert "messaging_app_only" in result["flags"]