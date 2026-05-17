import pytest
from src.status_checker.base import normalise_status, record_status_change
from src.tracker import Tracker, Job


@pytest.fixture
def tracker(tmp_path):
    t = Tracker(str(tmp_path / "test.db"))
    t.init_db()
    return t


def sample_job(status="applied") -> Job:
    return Job(id="linkedin:1", portal="linkedin", title="Engineer", company="ACME",
               location="UK", country="UK", url="https://x.com", description="",
               visa_sponsorship=True, status=status)


def test_normalise_viewed():
    assert normalise_status("Application Viewed") == "viewed"


def test_normalise_in_review():
    assert normalise_status("Under Review") == "in_review"


def test_normalise_rejected():
    assert normalise_status("Not selected for this role") == "rejected"


def test_record_change(tracker):
    j = sample_job()
    tracker.insert_job(j)
    assert record_status_change(tracker, j, "Application Viewed") is True
    assert tracker.get_events("linkedin:1")[0].new_status == "viewed"


def test_no_change_same_status(tracker):
    j = sample_job(status="viewed")
    tracker.insert_job(j)
    assert record_status_change(tracker, j, "Application Viewed") is False
