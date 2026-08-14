from app.models import Job


def test_job_model_has_expected_columns():

    columns = {
        column.name
        for column in Job.__table__.columns
    }

    expected = {
        "id",
        "source",
        "source_job_id",
        "fingerprint",
        "url",
        "title",
        "company",
        "location",
        "description",
        "is_remote",
        "match_score",
        "eligibility_score",
        "recommendation",
        "risk_severity",
        "risk_flags",
        "analysis",
        "discovered_at",
        "analyzed_at",
        "created_at",
        "updated_at",
    }

    assert expected.issubset(columns)