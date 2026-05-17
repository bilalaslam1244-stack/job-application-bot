import sqlite3
from dataclasses import dataclass
from typing import Optional


@dataclass
class Job:
    id: str
    portal: str
    title: str
    company: str
    location: str
    country: str
    url: str
    description: str
    visa_sponsorship: bool
    status: str = "found"
    applied_at: Optional[str] = None
    last_checked: Optional[str] = None
    cover_letter: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class Event:
    job_id: str
    event_type: str
    old_status: Optional[str]
    new_status: Optional[str]
    detail: str
    id: Optional[int] = None
    notified: bool = False
    created_at: Optional[str] = None


class Tracker:
    def __init__(self, db_path: str = "data/jobs.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id               TEXT PRIMARY KEY,
                portal           TEXT NOT NULL,
                title            TEXT NOT NULL,
                company          TEXT NOT NULL,
                location         TEXT,
                country          TEXT,
                url              TEXT NOT NULL,
                description      TEXT,
                visa_sponsorship INTEGER DEFAULT 0,
                status           TEXT DEFAULT 'found',
                applied_at       TEXT,
                last_checked     TEXT,
                cover_letter     TEXT,
                created_at       TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id      TEXT REFERENCES jobs(id),
                event_type  TEXT,
                old_status  TEXT,
                new_status  TEXT,
                detail      TEXT,
                notified    INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );
        """)
        conn.commit()

    def insert_job(self, job: Job):
        conn = self._get_conn()
        conn.execute(
            "INSERT OR IGNORE INTO jobs "
            "(id, portal, title, company, location, country, url, description, visa_sponsorship, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (job.id, job.portal, job.title, job.company, job.location,
             job.country, job.url, job.description, int(job.visa_sponsorship), job.status),
        )
        conn.commit()

    def get_job(self, job_id: str) -> Optional[Job]:
        row = self._get_conn().execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def get_all_jobs(self) -> list[Job]:
        rows = self._get_conn().execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return [self._row_to_job(r) for r in rows]

    def get_unapplied_jobs(self) -> list[Job]:
        rows = self._get_conn().execute(
            "SELECT * FROM jobs WHERE status = 'found' ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def update_status(self, job_id: str, status: str, cover_letter: str = None):
        conn = self._get_conn()
        if status == "applied":
            conn.execute(
                "UPDATE jobs SET status = ?, applied_at = datetime('now'), cover_letter = ? WHERE id = ?",
                (status, cover_letter, job_id),
            )
        else:
            conn.execute(
                "UPDATE jobs SET status = ?, last_checked = datetime('now') WHERE id = ?",
                (status, job_id),
            )
        conn.commit()

    def insert_event(self, event: Event):
        self._get_conn().execute(
            "INSERT INTO events (job_id, event_type, old_status, new_status, detail) VALUES (?, ?, ?, ?, ?)",
            (event.job_id, event.event_type, event.old_status, event.new_status, event.detail),
        )
        self._get_conn().commit()

    def get_events(self, job_id: str) -> list[Event]:
        rows = self._get_conn().execute(
            "SELECT * FROM events WHERE job_id = ? ORDER BY created_at DESC", (job_id,)
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def get_unnotified_events(self) -> list[Event]:
        rows = self._get_conn().execute(
            "SELECT * FROM events WHERE notified = 0 ORDER BY created_at ASC"
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def mark_events_notified(self, event_ids: list[int]):
        placeholders = ",".join("?" * len(event_ids))
        self._get_conn().execute(
            f"UPDATE events SET notified = 1 WHERE id IN ({placeholders})", event_ids
        )
        self._get_conn().commit()

    def get_stats(self) -> dict[str, int]:
        rows = self._get_conn().execute(
            "SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status"
        ).fetchall()
        return {r["status"]: r["cnt"] for r in rows}

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"], portal=row["portal"], title=row["title"], company=row["company"],
            location=row["location"], country=row["country"], url=row["url"],
            description=row["description"], visa_sponsorship=bool(row["visa_sponsorship"]),
            status=row["status"], applied_at=row["applied_at"], last_checked=row["last_checked"],
            cover_letter=row["cover_letter"], created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Event:
        return Event(
            id=row["id"], job_id=row["job_id"], event_type=row["event_type"],
            old_status=row["old_status"], new_status=row["new_status"],
            detail=row["detail"], notified=bool(row["notified"]), created_at=row["created_at"],
        )
