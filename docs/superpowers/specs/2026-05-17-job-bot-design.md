# Job Application Bot — Design Spec
**Date:** 2026-05-17  
**Author:** Bilal Aslam  
**Status:** Approved

---

## Overview

Automated job application bot for Bilal Aslam (Sri Lankan citizen, based in Malaysia, EEE + industrial automation background). Searches all major global job portals for roles with visa sponsorship, generates AI-tailored cover letters, auto-submits on easy-apply platforms, semi-automates complex forms, and sends real-time Telegram notifications for all events including callbacks and status changes.

---

## Goals

- Find relevant engineering roles worldwide (except India) that offer visa sponsorship
- Auto-submit on LinkedIn Easy Apply and Indeed Quick Apply
- Semi-automate complex application forms (bot fills, user submits)
- Generate a tailored cover letter per job using Claude API
- Track every application in a local SQLite database
- Notify via Telegram: new jobs, submissions, application viewed, status changes, recruiter messages
- Run on a Windows PC via Windows Task Scheduler (3x/day)
- Install via a single PowerShell script

---

## Target Roles

- Sales Engineer
- Project Engineer
- Automation / Controls Engineer
- Field Service / Commissioning Engineer

---

## Target Regions (Priority Order)

| Tier | Countries |
|------|-----------|
| 1 (highest) | UAE, Qatar, Saudi Arabia, Australia, France, Belgium, UK, Ireland |
| 2 | Netherlands, Germany, Canada, Luxembourg, New Zealand |
| 3 | Singapore, Sweden, Norway, Denmark, Switzerland, Austria, Finland |
| 4 | USA, Japan, South Korea, Portugal, Spain, Italy, Czech Republic, Poland, Hong Kong |
| Excluded | India |

Rationale:
- **Middle East**: High demand for Sri Lankan/Malaysian automation engineers, fast sponsorship
- **Australia**: Engineering on skilled occupation list, Seek.com.au strong market
- **France/Belgium**: French fluency = major differentiator, large industrial employers (Schneider, Total)
- **UK/Ireland**: Skilled Worker visa well-established for engineers
- **Netherlands/Germany**: English professional environment; Germany strong on automation (Siemens, Bosch)

---

## Architecture

```
linkedin-bot/
├── config.yaml                  # all credentials, search config, API keys
├── main.py                      # CLI entry point
├── install.ps1                  # one-command Windows installer
├── run.bat                      # double-click to run
├── requirements.txt
├── README.md
├── data/
│   ├── jobs.db                  # SQLite database
│   └── sessions/                # saved browser cookies per portal
├── output/
│   └── cover_letters/           # generated cover letters (.txt)
├── logs/
│   ├── run.log
│   ├── errors.log
│   └── applied.log
└── src/
    ├── config.py                # load + validate config.yaml
    ├── scrapers/
    │   ├── base.py              # shared Playwright session, dedup logic
    │   ├── linkedin.py
    │   ├── indeed.py
    │   ├── seek.py
    │   ├── reed.py
    │   └── stepstone.py
    ├── appliers/
    │   ├── linkedin.py          # full auto (Easy Apply)
    │   ├── indeed.py            # full auto (Quick Apply)
    │   └── semi_auto.py         # fills fields, pauses for user to submit
    ├── status_checker/
    │   ├── base.py
    │   ├── linkedin.py          # checks My Applications page
    │   ├── indeed.py
    │   ├── seek.py
    │   ├── reed.py
    │   └── stepstone.py
    ├── cover_letter.py          # Claude API cover letter generation
    ├── tracker.py               # SQLite CRUD
    └── notifier.py              # Telegram alerts
```

---

## Data Model

```sql
CREATE TABLE jobs (
    id              TEXT PRIMARY KEY,   -- "{portal}:{job_id}"
    portal          TEXT NOT NULL,
    title           TEXT NOT NULL,
    company         TEXT NOT NULL,
    location        TEXT,
    country         TEXT,
    url             TEXT NOT NULL,
    description     TEXT,
    visa_sponsorship BOOLEAN DEFAULT 0,
    status          TEXT DEFAULT 'found',
    -- status values: found | applied | viewed | in_review | interview | rejected | skipped
    applied_at      DATETIME,
    last_checked    DATETIME,
    cover_letter    TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT REFERENCES jobs(id),
    event_type  TEXT,
    -- event types: applied | status_change | message | viewed | callback
    old_status  TEXT,
    new_status  TEXT,
    detail      TEXT,   -- recruiter message content, etc.
    notified    BOOLEAN DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## Cover Letter Generation

**Model:** `claude-haiku-4-5-20251001` (fast, low cost ~$0.002/letter)  
**Prompt caching:** resume text cached — reduces cost ~90% on repeat runs  
**Output:** 200-250 words, 3 paragraphs  
**Saved to:** `output/cover_letters/{portal}_{company}_{YYYY-MM-DD}.txt`

Prompt structure:
```
Para 1: Why this role + company specifically
Para 2: 2-3 resume achievements that match the JD
Para 3: Visa status (requires sponsorship, Sri Lankan citizen, currently Malaysia),
        availability, call to action
```

---

## CLI Commands

```
python main.py run       Full cycle: scrape → filter → generate letters → apply → notify
python main.py search    Scrape + filter only (preview, no applications)
python main.py apply     Apply to all unapplied jobs already in DB
python main.py status    Print dashboard: found / applied / viewed / interviews
python main.py check     Status checker: log into portals, check for callbacks/updates
python main.py config    Validate config.yaml
```

---

## Automation Levels

| Portal | Mode | Reason |
|--------|------|--------|
| LinkedIn | Discovery + manual apply | Primary professional account — bot scrapes with stealth browser, opens job page, user clicks Apply. Protects account. |
| Indeed | Full auto (Quick Apply) | Lower-stakes account, Quick Apply is simple form |
| Seek | Full auto where possible, semi-auto on complex forms | |
| Reed | Semi-auto (fills form, user submits) | |
| StepStone | Semi-auto (fills form, user submits) | |

### LinkedIn Stealth Measures
- `playwright-stealth` plugin masks all automation signals
- Session cookies reused for days (avoids repeated login detection)
- Only scraping/browsing — no form submissions
- Random delays, scroll behaviour, human-like mouse movement
- Runs only during business hours (8am–7pm local time)

---

## Rate Limits (per portal per day)

| Portal | Max Applications | Delay Between |
|--------|-----------------|---------------|
| LinkedIn | N/A (manual apply) | N/A |
| Indeed | 30 | 25-40s randomised |
| Seek | 20 | 30-45s randomised |
| Reed | 15 | 30-45s randomised |
| StepStone | 15 | 30-45s randomised |

---

## Error Handling

| Scenario | Response |
|----------|----------|
| CAPTCHA detected | Pause bot, Telegram alert, wait for manual solve |
| Login failed | Telegram alert with portal name, skip portal for this run |
| Scraper broken (portal HTML changed) | Log error, Telegram alert, skip portal — run continues |
| Claude API failure | Retry 3x with exponential backoff, fall back to template cover letter |
| Daily limit reached | Stop applying on that portal, log, continue others |

---

## Telegram Notifications

| Event | Message |
|-------|---------|
| New matching job found | Title, company, location, portal, url |
| Application auto-submitted | Title, company, cover letter excerpt |
| Application viewed by employer | Company name, time |
| Status changed | Old → new status |
| New recruiter message | Company, message excerpt |
| CAPTCHA required | Portal name, action needed |
| Daily digest (9am) | X found, Y applied, Z status updates |

---

## config.yaml Structure

```yaml
resume_path: "Bilal_Aslam_Resume.pdf"

anthropic_api_key: "sk-ant-..."
telegram_bot_token: "..."
telegram_chat_id: "..."

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
    email: ""
    password: ""
    enabled: true
  indeed:
    email: ""
    password: ""
    enabled: true
  seek:
    email: ""
    password: ""
    enabled: true
  reed:
    email: ""
    password: ""
    enabled: true
  stepstone:
    email: ""
    password: ""
    enabled: true

rate_limits:
  delay_between_applications_seconds: 30
  delay_randomisation_seconds: 15
  max_applications_per_day:
    linkedin: 20
    indeed: 30
    seek: 20
    reed: 15
    stepstone: 15
  status_check_interval_hours: 4
```

---

## Installation

Single PowerShell command on target PC (run as Administrator):
```powershell
irm https://raw.githubusercontent.com/YOUR_REPO/main/install.ps1 | iex
```

`install.ps1` does:
1. Installs Python 3.11 via winget if not present
2. Clones the repo
3. Creates virtual environment + installs requirements
4. Downloads Playwright Chromium browser
5. Copies `config.template.yaml` → `config.yaml`
6. Creates Windows Task Scheduler task (runs 3x/day: 8am, 1pm, 6pm)

After install, user fills in `config.yaml` then double-clicks `run.bat`.

---

## Cost Estimate

| Item | Cost |
|------|------|
| Claude API (Haiku, ~50 letters/day) | ~$3-6/month |
| Telegram Bot | Free |
| Hosting (own PC) | Free |
| All job portals | Free |
| **Total** | **~$3-6/month** |
