from app.services.matching import score_job


def test_title_match_scores_highest():
    job = {
        "title": "Customer Support Specialist",
        "company": "Acme",
        "description": "",
    }

    result = score_job(
        job,
        ["customer support"],
    )

    assert result.score >= 50
    assert "customer support" in result.matched_keywords


def test_description_match_scores():
    job = {
        "title": "Operations Specialist",
        "company": "Acme",
        "description": (
            "We are looking for someone with "
            "customer support experience."
        ),
    }

    result = score_job(
        job,
        ["customer support"],
    )

    assert result.score > 0
    assert "customer support" in result.matched_keywords


def test_company_match_scores():
    job = {
        "title": "Operations Specialist",
        "company": "Customer Support Inc",
        "description": "",
    }

    result = score_job(
        job,
        ["customer support"],
    )

    assert result.score > 0


def test_unmatched_job_scores_zero():
    job = {
        "title": "Software Engineer",
        "company": "Acme",
        "description": "Python backend development.",
    }

    result = score_job(
        job,
        ["customer support"],
    )

    assert result.score == 0
    assert result.matched_keywords == []


def test_multiple_keywords_reward_coverage():
    job = {
        "title": "Customer Support Specialist",
        "company": "Acme",
        "description": (
            "Remote position requiring CRM experience."
        ),
    }

    result = score_job(
        job,
        [
            "customer support",
            "remote",
            "crm",
        ],
    )

    assert result.score > 0
    assert "customer support" in result.matched_keywords
    assert "remote" in result.matched_keywords
    assert "crm" in result.matched_keywords


def test_keyword_matching_is_case_insensitive():
    job = {
        "title": "CUSTOMER SUPPORT SPECIALIST",
        "company": "Acme",
        "description": "",
    }

    result = score_job(
        job,
        ["Customer Support"],
    )

    assert result.score > 0


def test_hyphenated_text_matches_phrase():
    job = {
        "title": "Customer-Support Specialist",
        "company": "Acme",
        "description": "",
    }

    result = score_job(
        job,
        ["customer support"],
    )

    assert result.score > 0


def test_empty_keywords_return_zero():
    job = {
        "title": "Customer Support Specialist",
        "company": "Acme",
        "description": "",
    }

    result = score_job(
        job,
        [],
    )

    assert result.score == 0