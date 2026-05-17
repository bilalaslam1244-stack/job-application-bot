from src.scrapers.base import has_visa_sponsorship, build_job_id, clean_text


def test_visa_detected():
    assert has_visa_sponsorship("We offer visa sponsorship for the right candidate.") is True
    assert has_visa_sponsorship("Company will sponsor work permit.") is True


def test_no_sponsorship():
    assert has_visa_sponsorship("Must have right to work in the UK.") is False
    assert has_visa_sponsorship("No sponsorship available.") is False


def test_build_job_id():
    assert build_job_id("linkedin", "12345") == "linkedin:12345"


def test_clean_text():
    assert clean_text("  hello   world  ") == "hello world"
    assert clean_text("\n\nfoo\n\nbar\n") == "foo bar"
