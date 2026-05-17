# Job Application Bot — Plan A: Core Infrastructure

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core infrastructure of the job application bot — config loading, SQLite job tracker, Telegram notifier, and Claude API cover letter generator — all fully tested and wired into a working CLI skeleton.

**Architecture:** Python 3.11 package under `src/`. Config loaded from `config.yaml` via PyYAML. SQLite via stdlib `sqlite3`. Telegram via `python-telegram-bot`. Cover letters via Anthropic SDK with prompt caching. CLI via `click`.

**Tech Stack:** Python 3.11+, click, PyYAML, anthropic, python-telegram-bot 20.x, sqlite3 (stdlib), pytest, pytest-asyncio

---

## File Map

| File | Responsibility |
|------|---------------|
| `requirements.txt` | All Python dependencies pinned |
| `config.template.yaml` | Template config user copies and fills |
| `src/__init__.py` | Empty package marker |
| `src/config.py` | Load + validate `config.yaml`, expose typed `Config` dataclass |
| `src/tracker.py` | SQLite CRUD — jobs + events tables, all DB logic lives here |
| `src/notifier.py` | Telegram send functions — new job, applied, status change, digest |
| `src/cover_letter.py` | Claude API — generate tailored cover letter given job dict + resume text |
| `main.py` | CLI entry point — `run`, `search`, `apply`, `status`, `check`, `config` commands (stubs for now, wired in Plan B) |
| `tests/test_config.py` | Config loading + validation tests |
| `tests/test_tracker.py` | All tracker CRUD tests against in-memory SQLite |
| `tests/test_cover_letter.py` | Cover letter generation tests with mocked Anthropic client |
| `tests/test_notifier.py` | Telegram notifier tests with mocked bot |
| `pytest.ini` | pytest config |
| `run.bat` | Double-click launcher for Windows |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `run.bat`
- Create: `data/.gitkeep`
- Create: `output/cover_letters/.gitkeep`
- Create: `logs/.gitkeep`

- [ ] **Step 1: Create directory structure**

```powershell
mkdir src, tests, data, "output\cover_letters", logs, "data\sessions"
New-Item src\__init__.py, tests\__init__.py -ItemType File
New-Item data\.gitkeep, "output\cover_letters\.gitkeep", logs\.gitkeep -ItemType File
```

- [ ] **Step 2: Create `requirements.txt`**

```
anthropic==0.40.0
python-telegram-bot==20.7
playwright==1.49.0
playwright-stealth==1.0.6
PyYAML==6.0.2
click==8.1.8
pytest==8.3.4
pytest-asyncio==0.24.0
pytest-mock==3.14.0
```

- [ ] **Step 3: Create `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 4: Create `run.bat`**

```bat
@echo off
call .venv\Scripts\activate.bat
python main.py run
pause
```

- [ ] **Step 5: Install dependencies**

```powershell
python -m venv .venv
.venv\Scripts\activate.ps1
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 6: Commit**

```bash
git init
git add .
git commit -m "chore: project scaffolding and dependencies"
```

---

## Task 2: Config System

**Files:**
- Create: `config.template.yaml`
- Create: `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_config.py`:

```python
import pytest
import yaml
from pathlib import Path
from src.config import load_config, ConfigError, Config

VALID_CONFIG = {
    "resume_path": "Bilal_Aslam_Resume_v2.html",
    "anthropic_api_key": "sk-ant-test",
    "telegram_bot_token": "123456:ABC-test",
    "telegram_chat_id": "987654321",
    "search": {
        "roles": ["Sales Engineer", "Project Engineer"],
        "keywords": ["visa sponsorship"],
        "priority_regions": {
            "tier1": ["UAE", "Australia"],
            "tier2": ["Netherlands"],
            "tier3": ["Singapore"],
            "tier4": ["USA"],
        },
        "exclude_countries": ["India"],
        "max_jobs_per_run": 100,
    },
    "portals": {
        "linkedin": {"email": "test@test.com", "password": "pass", "enabled": True},
        "indeed": {"email": "test@test.com", "password": "pass", "enabled": True},
        "seek": {"email": "test@test.com", "password": "pass", "enabled": False},
        "reed": {"email": "test@test.com", "password": "pass", "enabled": False},
        "stepstone": {"email": "test@test.com", "password": "pass", "enabled": False},
    },
    "rate_limits": {
        "delay_between_applications_seconds": 30,
        "delay_randomisation_seconds": 15,
        "max_applications_per_day": {
            "linkedin": 0,
            "indeed": 30,
            "seek": 20,
            "reed": 15,
            "stepstone": 15,
        },
        "status_check_interval_hours": 4,
    },
}


def test_load_valid_config(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump(VALID_CONFIG))
    cfg = load_config(str(cfg_file))
    assert isinstance(cfg, Config)
    assert cfg.anthropic_api_key == "sk-ant-test"
    assert cfg.telegram_chat_id == "987654321"
    assert "UAE" in cfg.search.tier1
    assert cfg.portals["linkedin"].enabled is True
    assert cfg.rate_limits.status_check_interval_hours == 4


def test_missing_required_field(tmp_path):
    bad = dict(VALID_CONFIG)
    del bad["anthropic_api_key"]
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump(bad))
    with pytest.raises(ConfigError, match="anthropic_api_key"):
        load_config(str(cfg_file))


def test_file_not_found():
    with pytest.raises(ConfigError, match="not found"):
        load_config("nonexistent.yaml")


def test_all_regions_flattened(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump(VALID_CONFIG))
    cfg = load_config(str(cfg_file))
    all_regions = cfg.search.all_countries()
    assert "UAE" in all_regions
    assert "Australia" in all_regions
    assert "India" not in all_regions
```

- [ ] **Step 2: Run tests — verify they fail**

```powershell
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 3: Create `src/config.py`**

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


class ConfigError(Exception):
    pass


@dataclass
class PortalConfig:
    email: str
    password: str
    enabled: bool


@dataclass
class SearchConfig:
    roles: list[str]
    keywords: list[str]
    tier1: list[str]
    tier2: list[str]
    tier3: list[str]
    tier4: list[str]
    exclude_countries: list[str]
    max_jobs_per_run: int

    def all_countries(self) -> list[str]:
        all_c = self.tier1 + self.tier2 + self.tier3 + self.tier4
        return [c for c in all_c if c not in self.exclude_countries]


@dataclass
class RateLimits:
    delay_between_applications_seconds: int
    delay_randomisation_seconds: int
    max_applications_per_day: dict[str, int]
    status_check_interval_hours: int


@dataclass
class Config:
    resume_path: str
    anthropic_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    search: SearchConfig
    portals: dict[str, PortalConfig]
    rate_limits: RateLimits


def load_config(path: str = "config.yaml") -> Config:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Config file not found: {path}")

    with p.open() as f:
        raw = yaml.safe_load(f)

    required = ["anthropic_api_key", "telegram_bot_token", "telegram_chat_id", "resume_path"]
    for key in required:
        if key not in raw:
            raise ConfigError(f"Missing required config field: {key}")

    regions = raw["search"]["priority_regions"]
    search = SearchConfig(
        roles=raw["search"]["roles"],
        keywords=raw["search"]["keywords"],
        tier1=regions.get("tier1", []),
        tier2=regions.get("tier2", []),
        tier3=regions.get("tier3", []),
        tier4=regions.get("tier4", []),
        exclude_countries=raw["search"].get("exclude_countries", []),
        max_jobs_per_run=raw["search"].get("max_jobs_per_run", 100),
    )

    portals = {
        name: PortalConfig(**vals)
        for name, vals in raw["portals"].items()
    }

    rl = raw["rate_limits"]
    rate_limits = RateLimits(
        delay_between_applications_seconds=rl["delay_between_applications_seconds"],
        delay_randomisation_seconds=rl["delay_randomisation_seconds"],
        max_applications_per_day=rl["max_applications_per_day"],
        status_check_interval_hours=rl["status_check_interval_hours"],
    )

    return Config(
        resume_path=raw["resume_path"],
        anthropic_api_key=raw["anthropic_api_key"],
        telegram_bot_token=raw["telegram_bot_token"],
        telegram_chat_id=raw["telegram_chat_id"],
        search=search,
        portals=portals,
        rate_limits=rate_limits,
    )
```

- [ ] **Step 4: Run tests — verify they pass**

```powershell
pytest tests/test_config.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Create `config.template.yaml`**

```yaml
resume_path: "Bilal_Aslam_Resume_v2.html"

anthropic_api_key: "sk-ant-REPLACE_ME"
telegram_bot_token: "REPLACE_ME"
telegram_chat_id: "REPLACE_ME"

search:
  roles:
    - "Sales Engineer"
    - "Project Engineer"
    - "Automation Engineer"
    - "Controls Engineer"
    - "Commissioning Engineer"
    - "Field Service Engineer"
  keywords:
    - "visa sponsorship"
    - "sponsor visa"
    - "work permit"
    - "relocation support"
  priority_regions:
    tier1: ["UAE", "Qatar", "Saudi Arabia", "Australia", "France", "Belgium", "United Kingdom", "Ireland"]
    tier2: ["Netherlands", "Germany", "Canada", "Luxembourg", "New Zealand"]
    tier3: ["Singapore", "Sweden", "Norway", "Denmark", "Switzerland", "Austria", "Finland"]
    tier4: ["USA", "Japan", "South Korea", "Portugal", "Spain", "Italy", "Czech Republic", "Poland", "Hong Kong"]
  exclude_countries: ["India"]
  max_jobs_per_run: 100

portals:
  linkedin:
    email: "REPLACE_ME"
    password: "REPLACE_ME"
    enabled: true
  indeed:
    email: "REPLACE_ME"
    password: "REPLACE_ME"
    enabled: true
  seek:
    email: "REPLACE_ME"
    password: "REPLACE_ME"
    enabled: true
  reed:
    email: "REPLACE_ME"
    password: "REPLACE_ME"
    enabled: true
  stepstone:
    email: "REPLACE_ME"
    password: "REPLACE_ME"
    enabled: true

rate_limits:
  delay_between_applications_seconds: 30
  delay_randomisation_seconds: 15
  max_applications_per_day:
    linkedin: 0
    indeed: 30
    seek: 20
    reed: 15
    stepstone: 15
  status_check_interval_hours: 4
```

- [ ] **Step 6: Commit**

```bash
git add src/config.py tests/test_config.py config.template.yaml
git commit -m "feat: config loading with validation"
```

---

## Task 3: SQLite Job Tracker

**Files:**
- Create: `src/tracker.py`
- Create: `tests/test_tracker.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_tracker.py`:

```python
import pytest
from datetime import datetime
from src.tracker import Tracker, Job, Event


@pytest.fixture
def tracker(tmp_path):
    db_path = str(tmp_path / "test.db")
    t = Tracker(db_path)
    t.init_db()
    return t


def make_job(**overrides) -> Job:
    base = Job(
        id="linkedin:12345",
        portal="linkedin",
        title="Sales Engineer",
        company="Siemens",
        location="Munich, Germany",
        country="Germany",
        url="https://linkedin.com/jobs/12345",
        description="We are hiring a Sales Engineer. Visa sponsorship available.",
        visa_sponsorship=True,
        status="found",
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_insert_and_get_job(tracker):
    job = make_job()
    tracker.insert_job(job)
    result = tracker.get_job("linkedin:12345")
    assert result is not None
    assert result.company == "Siemens"
    assert result.visa_sponsorship is True


def test_job_not_found_returns_none(tracker):
    assert tracker.get_job("nonexistent:999") is None


def test_duplicate_insert_ignored(tracker):
    job = make_job()
    tracker.insert_job(job)
    tracker.insert_job(job)  # should not raise
    assert len(tracker.get_all_jobs()) == 1


def test_update_status(tracker):
    tracker.insert_job(make_job())
    tracker.update_status("linkedin:12345", "applied")
    job = tracker.get_job("linkedin:12345")
    assert job.status == "applied"


def test_get_unapplied_jobs(tracker):
    tracker.insert_job(make_job(id="linkedin:1", status="found"))
    tracker.insert_job(make_job(id="linkedin:2", status="applied"))
    tracker.insert_job(make_job(id="linkedin:3", status="found"))
    unapplied = tracker.get_unapplied_jobs()
    assert len(unapplied) == 2
    assert all(j.status == "found" for j in unapplied)


def test_insert_event(tracker):
    tracker.insert_job(make_job())
    tracker.insert_event(Event(
        job_id="linkedin:12345",
        event_type="status_change",
        old_status="applied",
        new_status="viewed",
        detail="",
    ))
    events = tracker.get_events("linkedin:12345")
    assert len(events) == 1
    assert events[0].event_type == "status_change"


def test_get_unnotified_events(tracker):
    tracker.insert_job(make_job())
    tracker.insert_event(Event(job_id="linkedin:12345", event_type="applied",
                                old_status=None, new_status="applied", detail=""))
    events = tracker.get_unnotified_events()
    assert len(events) == 1
    tracker.mark_events_notified([events[0].id])
    assert len(tracker.get_unnotified_events()) == 0


def test_stats(tracker):
    tracker.insert_job(make_job(id="j1", status="found"))
    tracker.insert_job(make_job(id="j2", status="applied"))
    tracker.insert_job(make_job(id="j3", status="interview"))
    stats = tracker.get_stats()
    assert stats["found"] == 1
    assert stats["applied"] == 1
    assert stats["interview"] == 1
```

- [ ] **Step 2: Run tests — verify they fail**

```powershell
pytest tests/test_tracker.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.tracker'`

- [ ] **Step 3: Create `src/tracker.py`**

```python
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
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
        conn.execute("""
            INSERT OR IGNORE INTO jobs
              (id, portal, title, company, location, country, url, description, visa_sponsorship, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (job.id, job.portal, job.title, job.company, job.location,
              job.country, job.url, job.description, int(job.visa_sponsorship), job.status))
        conn.commit()

    def get_job(self, job_id: str) -> Optional[Job]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def get_all_jobs(self) -> list[Job]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return [self._row_to_job(r) for r in rows]

    def get_unapplied_jobs(self) -> list[Job]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status = 'found' ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def update_status(self, job_id: str, status: str, cover_letter: str = None):
        conn = self._get_conn()
        if status == "applied":
            conn.execute(
                "UPDATE jobs SET status = ?, applied_at = datetime('now'), cover_letter = ? WHERE id = ?",
                (status, cover_letter, job_id)
            )
        else:
            conn.execute("UPDATE jobs SET status = ?, last_checked = datetime('now') WHERE id = ?",
                         (status, job_id))
        conn.commit()

    def insert_event(self, event: Event):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO events (job_id, event_type, old_status, new_status, detail)
            VALUES (?, ?, ?, ?, ?)
        """, (event.job_id, event.event_type, event.old_status, event.new_status, event.detail))
        conn.commit()

    def get_events(self, job_id: str) -> list[Event]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM events WHERE job_id = ? ORDER BY created_at DESC", (job_id,)
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def get_unnotified_events(self) -> list[Event]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM events WHERE notified = 0 ORDER BY created_at ASC"
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def mark_events_notified(self, event_ids: list[int]):
        conn = self._get_conn()
        placeholders = ",".join("?" * len(event_ids))
        conn.execute(f"UPDATE events SET notified = 1 WHERE id IN ({placeholders})", event_ids)
        conn.commit()

    def get_stats(self) -> dict[str, int]:
        conn = self._get_conn()
        rows = conn.execute(
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
            id=row["id"], portal=row["portal"], title=row["title"],
            company=row["company"], location=row["location"], country=row["country"],
            url=row["url"], description=row["description"],
            visa_sponsorship=bool(row["visa_sponsorship"]), status=row["status"],
            applied_at=row["applied_at"], last_checked=row["last_checked"],
            cover_letter=row["cover_letter"], created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Event:
        return Event(
            id=row["id"], job_id=row["job_id"], event_type=row["event_type"],
            old_status=row["old_status"], new_status=row["new_status"],
            detail=row["detail"], notified=bool(row["notified"]),
            created_at=row["created_at"],
        )
```

- [ ] **Step 4: Run tests — verify they pass**

```powershell
pytest tests/test_tracker.py -v
```

Expected: 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tracker.py tests/test_tracker.py
git commit -m "feat: SQLite job tracker with jobs and events tables"
```

---

## Task 4: Telegram Notifier

**Files:**
- Create: `src/notifier.py`
- Create: `tests/test_notifier.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_notifier.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.notifier import Notifier
from src.tracker import Job, Event


@pytest.fixture
def notifier():
    with patch("src.notifier.Bot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        n = Notifier(token="test-token", chat_id="123456")
        n._bot = mock_bot
        yield n, mock_bot


@pytest.mark.asyncio
async def test_notify_new_job(notifier):
    n, mock_bot = notifier
    job = Job(id="linkedin:1", portal="linkedin", title="Sales Engineer",
              company="Siemens", location="Munich, Germany", country="Germany",
              url="https://example.com/job/1", description="...", visa_sponsorship=True)
    await n.notify_new_job(job)
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args
    assert "Sales Engineer" in call_args.kwargs["text"]
    assert "Siemens" in call_args.kwargs["text"]


@pytest.mark.asyncio
async def test_notify_applied(notifier):
    n, mock_bot = notifier
    job = Job(id="indeed:2", portal="indeed", title="Project Engineer",
              company="ABB", location="Zurich, Switzerland", country="Switzerland",
              url="https://example.com/job/2", description="...", visa_sponsorship=True)
    await n.notify_applied(job, cover_letter_excerpt="Dear Hiring Manager, I am excited...")
    mock_bot.send_message.assert_called_once()
    text = mock_bot.send_message.call_args.kwargs["text"]
    assert "ABB" in text
    assert "applied" in text.lower()


@pytest.mark.asyncio
async def test_notify_status_change(notifier):
    n, mock_bot = notifier
    event = Event(job_id="linkedin:1", event_type="status_change",
                  old_status="applied", new_status="viewed", detail="")
    job = Job(id="linkedin:1", portal="linkedin", title="Sales Engineer",
              company="Siemens", location="Munich", country="Germany",
              url="https://example.com", description="", visa_sponsorship=True)
    await n.notify_status_change(job, event)
    text = mock_bot.send_message.call_args.kwargs["text"]
    assert "viewed" in text.lower()
    assert "Siemens" in text


@pytest.mark.asyncio
async def test_send_daily_digest(notifier):
    n, mock_bot = notifier
    stats = {"found": 12, "applied": 8, "viewed": 3, "interview": 1}
    await n.send_daily_digest(stats)
    text = mock_bot.send_message.call_args.kwargs["text"]
    assert "12" in text
    assert "8" in text


@pytest.mark.asyncio
async def test_notify_captcha(notifier):
    n, mock_bot = notifier
    await n.notify_captcha("linkedin")
    text = mock_bot.send_message.call_args.kwargs["text"]
    assert "linkedin" in text.lower()
    assert "captcha" in text.lower()
```

- [ ] **Step 2: Run tests — verify they fail**

```powershell
pytest tests/test_notifier.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.notifier'`

- [ ] **Step 3: Create `src/notifier.py`**

```python
from telegram import Bot
from src.tracker import Job, Event


class Notifier:
    def __init__(self, token: str, chat_id: str):
        self._bot = Bot(token=token)
        self._chat_id = chat_id

    async def _send(self, text: str):
        await self._bot.send_message(chat_id=self._chat_id, text=text, parse_mode="HTML")

    async def notify_new_job(self, job: Job):
        text = (
            f"🔍 <b>New Job Found</b>\n\n"
            f"<b>{job.title}</b> at <b>{job.company}</b>\n"
            f"📍 {job.location}\n"
            f"🌐 {job.portal.title()}\n"
            f"🔗 {job.url}"
        )
        await self._send(text)

    async def notify_applied(self, job: Job, cover_letter_excerpt: str = ""):
        excerpt = cover_letter_excerpt[:200] + "..." if len(cover_letter_excerpt) > 200 else cover_letter_excerpt
        text = (
            f"✅ <b>Applied</b>\n\n"
            f"<b>{job.title}</b> at <b>{job.company}</b>\n"
            f"📍 {job.location} | 🌐 {job.portal.title()}\n"
            f"🔗 {job.url}\n\n"
            f"<i>{excerpt}</i>"
        )
        await self._send(text)

    async def notify_status_change(self, job: Job, event: Event):
        emoji = {
            "viewed": "👀",
            "in_review": "📋",
            "interview": "🎉",
            "rejected": "❌",
            "message": "💬",
        }.get(event.new_status, "📌")

        text = (
            f"{emoji} <b>Status Update</b>\n\n"
            f"<b>{job.title}</b> at <b>{job.company}</b>\n"
            f"{event.old_status} → <b>{event.new_status}</b>\n"
            f"🔗 {job.url}"
        )
        if event.detail:
            text += f"\n\n<i>{event.detail[:300]}</i>"
        await self._send(text)

    async def send_daily_digest(self, stats: dict[str, int]):
        lines = ["📊 <b>Daily Digest</b>\n"]
        labels = {
            "found": "🔍 Found",
            "applied": "✅ Applied",
            "viewed": "👀 Viewed",
            "in_review": "📋 In Review",
            "interview": "🎉 Interview",
            "rejected": "❌ Rejected",
        }
        for key, label in labels.items():
            if key in stats:
                lines.append(f"{label}: {stats[key]}")
        await self._send("\n".join(lines))

    async def notify_captcha(self, portal: str):
        text = (
            f"⚠️ <b>CAPTCHA Required</b>\n\n"
            f"Portal: <b>{portal.title()}</b>\n"
            f"Please open the browser and solve the CAPTCHA manually.\n"
            f"Bot will resume automatically once session is restored."
        )
        await self._send(text)

    async def notify_error(self, portal: str, error: str):
        text = (
            f"🚨 <b>Error — {portal.title()}</b>\n\n"
            f"<code>{error[:500]}</code>"
        )
        await self._send(text)
```

- [ ] **Step 4: Run tests — verify they pass**

```powershell
pytest tests/test_notifier.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/notifier.py tests/test_notifier.py
git commit -m "feat: telegram notifier for all job event types"
```

---

## Task 5: Cover Letter Generator

**Files:**
- Create: `src/cover_letter.py`
- Create: `tests/test_cover_letter.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cover_letter.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from src.cover_letter import CoverLetterGenerator
from src.tracker import Job

RESUME_TEXT = """
Bilal Aslam — Sales Engineer, ACET Engineering. EEE graduate.
Experience: industrial automation, project coordination, commissioning.
Languages: English, French, Tamil.
"""

SAMPLE_JOB = Job(
    id="linkedin:999",
    portal="linkedin",
    title="Automation Engineer",
    company="Schneider Electric",
    location="Paris, France",
    country="France",
    url="https://example.com/job/999",
    description="We need an Automation Engineer. Visa sponsorship available for the right candidate.",
    visa_sponsorship=True,
)


@pytest.fixture
def generator():
    with patch("src.cover_letter.anthropic.Anthropic") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Dear Hiring Manager,\n\nI am excited to apply...")]
        mock_client.messages.create.return_value = mock_response
        gen = CoverLetterGenerator(api_key="sk-ant-test", resume_text=RESUME_TEXT)
        gen._client = mock_client
        yield gen, mock_client


def test_generate_returns_string(generator):
    gen, _ = generator
    result = gen.generate(SAMPLE_JOB)
    assert isinstance(result, str)
    assert len(result) > 10


def test_generate_calls_claude_with_job_details(generator):
    gen, mock_client = generator
    gen.generate(SAMPLE_JOB)
    call_kwargs = mock_client.messages.create.call_args.kwargs
    messages = call_kwargs["messages"]
    user_content = str(messages[0]["content"])
    assert "Schneider Electric" in user_content
    assert "Automation Engineer" in user_content
    assert "France" in user_content


def test_generate_uses_haiku_model(generator):
    gen, mock_client = generator
    gen.generate(SAMPLE_JOB)
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "haiku" in call_kwargs["model"]


def test_save_cover_letter(generator, tmp_path):
    gen, _ = generator
    letter = "Dear Hiring Manager,\n\nI am writing to apply..."
    path = gen.save(SAMPLE_JOB, letter, output_dir=str(tmp_path))
    assert path.exists()
    assert path.read_text() == letter
    assert "Schneider_Electric" in path.name


def test_load_resume_from_html(tmp_path):
    html_file = tmp_path / "resume.html"
    html_file.write_text("<html><body><p>Bilal Aslam Sales Engineer</p></body></html>")
    text = CoverLetterGenerator.load_resume(str(html_file))
    assert "Bilal Aslam" in text
    assert "<html>" not in text
```

- [ ] **Step 2: Run tests — verify they fail**

```powershell
pytest tests/test_cover_letter.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.cover_letter'`

- [ ] **Step 3: Create `src/cover_letter.py`**

```python
import re
from pathlib import Path
from datetime import datetime
import anthropic
from src.tracker import Job


SYSTEM_PROMPT = """You write concise, professional cover letters for engineering job applications.
Output ONLY the cover letter text — no subject line, no metadata, no explanations.
Maximum 250 words. Three paragraphs."""

USER_TEMPLATE = """Write a cover letter for {name} applying to the role below.

RESUME:
{resume}

JOB:
Title: {title}
Company: {company}
Location: {location}
Description:
{description}

INSTRUCTIONS:
- Para 1: Why this specific role and company (reference something concrete from the description)
- Para 2: 2-3 specific achievements from the resume that directly match the job requirements
- Para 3: Mention visa sponsorship requirement (Sri Lankan citizen, currently based in Malaysia, requires work visa sponsorship), availability to relocate immediately, and a call to action
- Tone: professional and direct. No clichés. No "I am writing to express my interest."
- Max 250 words."""


class CoverLetterGenerator:
    def __init__(self, api_key: str, resume_text: str):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._resume_text = resume_text

    def generate(self, job: Job) -> str:
        prompt = USER_TEMPLATE.format(
            name="Bilal Aslam",
            resume=self._resume_text,
            title=job.title,
            company=job.company,
            location=job.location,
            description=job.description[:3000],
        )
        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self._resume_text,
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )
        return response.content[0].text.strip()

    def save(self, job: Job, letter: str, output_dir: str = "output/cover_letters") -> Path:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        safe_company = re.sub(r"[^\w]", "_", job.company)
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{job.portal}_{safe_company}_{date_str}.txt"
        path = out / filename
        path.write_text(letter, encoding="utf-8")
        return path

    @staticmethod
    def load_resume(path: str) -> str:
        content = Path(path).read_text(encoding="utf-8")
        # strip HTML tags if HTML file
        if path.endswith(".html"):
            content = re.sub(r"<[^>]+>", " ", content)
            content = re.sub(r"\s+", " ", content).strip()
        return content
```

- [ ] **Step 4: Run tests — verify they pass**

```powershell
pytest tests/test_cover_letter.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cover_letter.py tests/test_cover_letter.py
git commit -m "feat: claude haiku cover letter generator with prompt caching"
```

---

## Task 6: CLI Entry Point

**Files:**
- Create: `main.py`

- [ ] **Step 1: Create `main.py`**

```python
import asyncio
import click
from pathlib import Path
from src.config import load_config, ConfigError
from src.tracker import Tracker
from src.notifier import Notifier
from src.cover_letter import CoverLetterGenerator


@click.group()
def cli():
    pass


@cli.command()
def config():
    """Validate config.yaml and report status."""
    try:
        cfg = load_config()
        click.echo("✅ Config valid.")
        click.echo(f"  Resume:   {cfg.resume_path}")
        click.echo(f"  Portals:  {[k for k,v in cfg.portals.items() if v.enabled]}")
        click.echo(f"  Regions:  {len(cfg.search.all_countries())} countries")
        click.echo(f"  Max jobs: {cfg.search.max_jobs_per_run}/run")
    except ConfigError as e:
        click.echo(f"❌ Config error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
def status():
    """Show application dashboard."""
    tracker = Tracker()
    tracker.init_db()
    stats = tracker.get_stats()
    tracker.close()

    click.echo("\n📊 Application Status\n" + "─" * 30)
    labels = {
        "found": "🔍 Found (not yet applied)",
        "applied": "✅ Applied",
        "viewed": "👀 Viewed by employer",
        "in_review": "📋 In Review",
        "interview": "🎉 Interview",
        "rejected": "❌ Rejected",
        "skipped": "⏭  Skipped",
    }
    total = sum(stats.values())
    for key, label in labels.items():
        count = stats.get(key, 0)
        if count:
            click.echo(f"  {label}: {count}")
    click.echo("─" * 30)
    click.echo(f"  Total: {total}\n")


@cli.command()
def search():
    """Search for jobs without applying. (Scrapers implemented in Plan B)"""
    click.echo("ℹ️  Search command — scrapers will be wired in Plan B.")


@cli.command()
def apply():
    """Apply to all unapplied jobs in DB. (Appliers implemented in Plan B)"""
    click.echo("ℹ️  Apply command — appliers will be wired in Plan B.")


@cli.command()
def check():
    """Check application statuses on all portals. (Status checkers in Plan B)"""
    click.echo("ℹ️  Check command — status checkers will be wired in Plan B.")


@cli.command()
def run():
    """Full cycle: search + apply + check. (Fully wired in Plan B)"""
    click.echo("ℹ️  Run command — fully wired in Plan B.")
    click.echo("Running config validation and status check for now...\n")
    ctx = click.get_current_context()
    ctx.invoke(config)
    click.echo()
    ctx.invoke(status)


if __name__ == "__main__":
    cli()
```

- [ ] **Step 2: Test CLI manually**

```powershell
python main.py config
python main.py status
```

Expected: `❌ Config error: Config file not found: config.yaml` (until config.yaml exists)

- [ ] **Step 3: Copy template and test with real config**

```powershell
Copy-Item config.template.yaml config.yaml
```

Open `config.yaml` in any text editor, fill in your `anthropic_api_key`, `telegram_bot_token`, `telegram_chat_id`. Leave portal credentials as REPLACE_ME for now.

```powershell
python main.py config
python main.py status
```

Expected: `✅ Config valid.` and empty status dashboard.

- [ ] **Step 4: Run all tests**

```powershell
pytest -v
```

Expected: all 22 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add main.py config.yaml
git commit -m "feat: CLI skeleton with config validation and status dashboard"
```

---

## Task 7: Telegram Bot Setup Guide

This task is documentation — no code. Follow these steps to get your Telegram bot token and chat ID before Plan B.

- [ ] **Step 1: Create Telegram bot**

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Choose a name (e.g. "Bilal Job Bot") and username (e.g. `bilal_jobs_bot`)
4. BotFather replies with your **bot token** — copy it to `config.yaml` → `telegram_bot_token`

- [ ] **Step 2: Get your chat ID**

1. Start a conversation with your new bot (send `/start`)
2. Open this URL in your browser (replace TOKEN):
   `https://api.telegram.org/botTOKEN/getUpdates`
3. Find `"chat":{"id":XXXXXXXXX}` — that number is your **chat ID**
4. Copy to `config.yaml` → `telegram_chat_id`

- [ ] **Step 3: Test Telegram connection**

```python
# run once in Python shell to verify
import asyncio
from telegram import Bot

async def test():
    bot = Bot(token="YOUR_TOKEN")
    await bot.send_message(chat_id="YOUR_CHAT_ID", text="Job bot connected! ✅")

asyncio.run(test())
```

Expected: message appears in your Telegram chat.

- [ ] **Step 4: Commit config (without secrets)**

Make sure `config.yaml` is in `.gitignore`:

```
# .gitignore
config.yaml
data/
logs/
output/
.venv/
__pycache__/
*.pyc
data/sessions/
```

```bash
git add .gitignore
git commit -m "chore: add gitignore to protect credentials and data"
```

---

## Plan A Complete

Run the full test suite:

```powershell
pytest -v
```

Expected: all tests PASS.

All core infrastructure is built and tested:
- ✅ Config loading + validation
- ✅ SQLite job + event tracker
- ✅ Telegram notifier
- ✅ Claude Haiku cover letter generator with prompt caching
- ✅ CLI skeleton

**Next:** Plan B wires in all scrapers, appliers, status checkers, and the Windows installer.
