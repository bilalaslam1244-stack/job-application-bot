import pytest
from src.tracker import Tracker, Job, Event


@pytest.fixture
def tracker(tmp_path):
    t = Tracker(str(tmp_path / "test.db"))
    t.init_db()
    return t


def job(**overrides) -> Job:
    base = Job(id="linkedin:1", portal="linkedin", title="Sales Engineer",
               company="Siemens", location="Munich", country="Germany",
               url="https://example.com/1", description="Visa sponsorship available.",
               visa_sponsorship=True)
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_insert_and_get(tracker):
    tracker.insert_job(job())
    result = tracker.get_job("linkedin:1")
    assert result.company == "Siemens"
    assert result.visa_sponsorship is True


def test_not_found_returns_none(tracker):
    assert tracker.get_job("nope:999") is None


def test_duplicate_ignored(tracker):
    tracker.insert_job(job())
    tracker.insert_job(job())
    assert len(tracker.get_all_jobs()) == 1


def test_update_status(tracker):
    tracker.insert_job(job())
    tracker.update_status("linkedin:1", "applied")
    assert tracker.get_job("linkedin:1").status == "applied"


def test_get_unapplied(tracker):
    tracker.insert_job(job(id="j1", status="found"))
    tracker.insert_job(job(id="j2", status="applied"))
    assert len(tracker.get_unapplied_jobs()) == 1


def test_events(tracker):
    tracker.insert_job(job())
    tracker.insert_event(Event(job_id="linkedin:1", event_type="status_change",
                                old_status="applied", new_status="viewed", detail=""))
    assert len(tracker.get_events("linkedin:1")) == 1


def test_unnotified_events(tracker):
    tracker.insert_job(job())
    tracker.insert_event(Event(job_id="linkedin:1", event_type="applied",
                                old_status=None, new_status="applied", detail=""))
    events = tracker.get_unnotified_events()
    assert len(events) == 1
    tracker.mark_events_notified([events[0].id])
    assert len(tracker.get_unnotified_events()) == 0


def test_stats(tracker):
    tracker.insert_job(job(id="j1", status="found"))
    tracker.insert_job(job(id="j2", status="applied"))
    stats = tracker.get_stats()
    assert stats["found"] == 1
    assert stats["applied"] == 1
