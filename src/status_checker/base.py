from src.tracker import Job, Event, Tracker

STATUS_MAP = {
    "viewed": "viewed",
    "application viewed": "viewed",
    "under review": "in_review",
    "in review": "in_review",
    "reviewing": "in_review",
    "interview": "interview",
    "interview scheduled": "interview",
    "rejected": "rejected",
    "not selected": "rejected",
    "declined": "rejected",
    "withdrew": "skipped",
}


def normalise_status(raw: str) -> str:
    lower = raw.lower().strip()
    for key, value in STATUS_MAP.items():
        if key in lower:
            return value
    return lower


def record_status_change(tracker: Tracker, job: Job, new_raw_status: str, detail: str = "") -> bool:
    new_status = normalise_status(new_raw_status)
    if new_status == job.status:
        return False
    tracker.insert_event(Event(
        job_id=job.id,
        event_type="status_change",
        old_status=job.status,
        new_status=new_status,
        detail=detail,
    ))
    tracker.update_status(job.id, new_status)
    return True
