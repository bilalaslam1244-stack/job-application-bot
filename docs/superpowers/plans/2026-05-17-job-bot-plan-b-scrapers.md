# Job Application Bot — Plan B: Scrapers, Appliers, Status Checkers & Installer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire all job scrapers (LinkedIn, Indeed, Seek, Reed, StepStone), appliers (Indeed full-auto, others semi-auto), status checkers, and Windows installer into the working CLI from Plan A.

**Architecture:** Playwright browser automation with playwright-stealth for all portals. Each portal has a dedicated scraper and applier module inheriting from a shared base. Status checkers run on a separate schedule. LinkedIn uses stealth scraping only — no form submission. Full run orchestrated in `main.py`.

**Tech Stack:** playwright, playwright-stealth, asyncio, click (from Plan A), all Plan A dependencies

**Prerequisite:** Plan A complete and all tests passing.

---

## File Map

| File | Responsibility |
|------|---------------|
| `src/scrapers/base.py` | Shared Playwright session, stealth setup, session cookie save/load, visa sponsorship keyword filter |
| `src/scrapers/linkedin.py` | LinkedIn job search + scrape (stealth, discovery only, no apply) |
| `src/scrapers/indeed.py` | Indeed job search + scrape |
| `src/scrapers/seek.py` | Seek job search + scrape |
| `src/scrapers/reed.py` | Reed job search + scrape |
| `src/scrapers/stepstone.py` | StepStone job search + scrape |
| `src/appliers/indeed.py` | Indeed Quick Apply full automation |
| `src/appliers/semi_auto.py` | Semi-auto applier for Seek, Reed, StepStone — fills fields, opens browser for user |
| `src/status_checker/base.py` | Shared status check logic, diff against DB, fire events |
| `src/status_checker/linkedin.py` | LinkedIn My Applications page scraper |
| `src/status_checker/indeed.py` | Indeed application dashboard scraper |
| `src/status_checker/seek.py` | Seek application centre scraper |
| `src/status_checker/reed.py` | Reed applied jobs scraper |
| `src/status_checker/stepstone.py` | StepStone application status scraper |
| `src/runner.py` | Orchestrates full run: scrape → filter → generate letters → apply → notify |
| `install.ps1` | One-command Windows installer |
| `README.md` | Setup and usage guide |

---

## Task 1: Install Playwright + Stealth

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Verify Playwright installed from Plan A**

```powershell
python -c "from playwright.sync_api import sync_playwright; print('OK')"
```

Expected: `OK`

- [ ] **Step 2: Install Playwright browsers**

```powershell
playwright install chromium
```

Expected: Chromium downloaded to local cache (~150MB).

- [ ] **Step 3: Verify playwright-stealth**

```python
# run in Python shell
from playwright_stealth import stealth_async
print("stealth OK")
```

Expected: `stealth OK`

- [ ] **Step 4: Create scraper package**

```powershell
mkdir src\scrapers, src\appliers, src\status_checker
New-Item src\scrapers\__init__.py, src\appliers\__init__.py, src\status_checker\__init__.py -ItemType File
```

- [ ] **Step 5: Commit**

```bash
git add src/scrapers/__init__.py src/appliers/__init__.py src/status_checker/__init__.py
git commit -m "chore: create scraper, applier, status_checker packages"
```

---

## Task 2: Base Scraper

**Files:**
- Create: `src/scrapers/base.py`
- Create: `tests/scrapers/__init__.py`
- Create: `tests/scrapers/test_base.py`

- [ ] **Step 1: Write failing tests**

Create `tests/scrapers/__init__.py` (empty).

Create `tests/scrapers/test_base.py`:

```python
import pytest
from src.scrapers.base import has_visa_sponsorship, build_job_id, clean_text

def test_visa_sponsorship_detected():
    assert has_visa_sponsorship("We offer visa sponsorship for the right candidate.") is True
    assert has_visa_sponsorship("Company will sponsor work permit.") is True
    assert has_visa_sponsorship("Relocation support available, we sponsor visas.") is True

def test_visa_sponsorship_not_detected():
    assert has_visa_sponsorship("Must have right to work in the UK.") is False
    assert has_visa_sponsorship("No sponsorship available.") is False
    assert has_visa_sponsorship("Citizens only.") is False

def test_build_job_id():
    assert build_job_id("linkedin", "12345") == "linkedin:12345"
    assert build_job_id("indeed", "abc-xyz") == "indeed:abc-xyz"

def test_clean_text_strips_whitespace():
    assert clean_text("  hello   world  ") == "hello world"
    assert clean_text("\n\nfoo\n\nbar\n") == "foo bar"
```

- [ ] **Step 2: Run tests — verify they fail**

```powershell
pytest tests/scrapers/test_base.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.scrapers.base'`

- [ ] **Step 3: Create `src/scrapers/base.py`**

```python
import asyncio
import json
import random
import re
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import stealth_async

VISA_KEYWORDS = [
    "visa sponsorship", "sponsor visa", "work permit", "sponsorship provided",
    "we will sponsor", "visa support", "relocation support", "sponsor work",
    "willing to sponsor", "provide sponsorship",
]

NO_SPONSORSHIP_KEYWORDS = [
    "no sponsorship", "must have right to work", "citizens only",
    "no visa", "sponsorship not available", "must be eligible to work",
]


def has_visa_sponsorship(text: str) -> bool:
    lower = text.lower()
    if any(kw in lower for kw in NO_SPONSORSHIP_KEYWORDS):
        return False
    return any(kw in lower for kw in VISA_KEYWORDS)


def build_job_id(portal: str, raw_id: str) -> str:
    return f"{portal}:{raw_id}"


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class BaseScraper:
    PORTAL = "base"
    SESSION_DIR = Path("data/sessions")

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self.SESSION_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def _session_file(self) -> Path:
        return self.SESSION_DIR / f"{self.PORTAL}_session.json"

    async def _setup_context(self, playwright) -> BrowserContext:
        self._browser = await playwright.chromium.launch(headless=True)
        context_kwargs = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        if self._session_file.exists():
            context_kwargs["storage_state"] = str(self._session_file)
        self._context = await self._browser.new_context(**context_kwargs)
        return self._context

    async def _new_stealth_page(self) -> Page:
        page = await self._context.new_page()
        await stealth_async(page)
        return page

    async def _save_session(self):
        if self._context:
            await self._context.storage_state(path=str(self._session_file))

    async def _random_delay(self, min_s: float = 1.0, max_s: float = 3.0):
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def _human_type(self, page: Page, selector: str, text: str):
        await page.click(selector)
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))

    async def close(self):
        await self._save_session()
        if self._browser:
            await self._browser.close()
```

- [ ] **Step 4: Run tests — verify they pass**

```powershell
pytest tests/scrapers/test_base.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/scrapers/base.py tests/scrapers/ 
git commit -m "feat: base scraper with stealth setup, session management, visa keyword filter"
```

---

## Task 3: LinkedIn Scraper (Stealth Discovery Only)

**Files:**
- Create: `src/scrapers/linkedin.py`

- [ ] **Step 1: Create `src/scrapers/linkedin.py`**

```python
import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright
from src.scrapers.base import BaseScraper, has_visa_sponsorship, build_job_id, clean_text
from src.tracker import Job


class LinkedInScraper(BaseScraper):
    PORTAL = "linkedin"
    BASE_URL = "https://www.linkedin.com"

    async def login(self) -> bool:
        async with async_playwright() as p:
            await self._setup_context(p)
            page = await self._new_stealth_page()
            await page.goto(f"{self.BASE_URL}/login")
            await self._random_delay(1, 2)

            # Check if already logged in via saved session
            if await page.query_selector("div.feed-identity-module") is not None:
                await self.close()
                return True

            await self._human_type(page, "#username", self.email)
            await self._random_delay(0.5, 1)
            await self._human_type(page, "#password", self.password)
            await self._random_delay(0.5, 1)
            await page.click("button[type='submit']")
            await self._random_delay(2, 4)

            success = await page.query_selector("div.feed-identity-module") is not None
            await self.close()
            return success

    async def search_jobs(
        self,
        roles: list[str],
        countries: list[str],
        max_jobs: int = 100,
    ) -> list[Job]:
        jobs = []
        async with async_playwright() as p:
            await self._setup_context(p)
            for role in roles:
                for country in countries:
                    new_jobs = await self._search_one(role, country, max_jobs // (len(roles) * len(countries)) + 1)
                    jobs.extend(new_jobs)
                    if len(jobs) >= max_jobs:
                        break
                if len(jobs) >= max_jobs:
                    break
            await self.close()
        return jobs[:max_jobs]

    async def _search_one(self, role: str, country: str, limit: int) -> list[Job]:
        page = await self._new_stealth_page()
        query = f"{role} visa sponsorship"
        encoded_query = query.replace(" ", "%20")
        encoded_country = country.replace(" ", "%20")
        url = (
            f"{self.BASE_URL}/jobs/search/?keywords={encoded_query}"
            f"&location={encoded_country}&f_WT=2&sortBy=DD"
        )
        await page.goto(url)
        await self._random_delay(2, 4)

        jobs = []
        job_cards = await page.query_selector_all("div.job-search-card")
        for card in job_cards[:limit]:
            try:
                job = await self._parse_card(card, page)
                if job:
                    jobs.append(job)
            except Exception:
                continue
            await self._random_delay(0.5, 1.5)

        await page.close()
        return jobs

    async def _parse_card(self, card, page) -> Optional[Job]:
        title_el = await card.query_selector("h3.base-search-card__title")
        company_el = await card.query_selector("h4.base-search-card__subtitle")
        location_el = await card.query_selector("span.job-search-card__location")
        link_el = await card.query_selector("a.base-card__full-link")

        if not all([title_el, company_el, link_el]):
            return None

        title = clean_text(await title_el.inner_text())
        company = clean_text(await company_el.inner_text())
        location = clean_text(await location_el.inner_text()) if location_el else ""
        url = await link_el.get_attribute("href")
        job_id_match = re.search(r"/jobs/view/(\d+)", url or "")
        if not job_id_match:
            return None

        raw_id = job_id_match.group(1)

        # Fetch full description
        desc_page = await self._new_stealth_page()
        try:
            await desc_page.goto(url)
            await self._random_delay(1.5, 3)
            desc_el = await desc_page.query_selector("div.show-more-less-html__markup")
            description = clean_text(await desc_el.inner_text()) if desc_el else ""
        except Exception:
            description = ""
        finally:
            await desc_page.close()

        country = location.split(",")[-1].strip() if "," in location else location

        return Job(
            id=build_job_id(self.PORTAL, raw_id),
            portal=self.PORTAL,
            title=title,
            company=company,
            location=location,
            country=country,
            url=url,
            description=description,
            visa_sponsorship=has_visa_sponsorship(title + " " + description),
        )
```

- [ ] **Step 2: Manual smoke test (requires real LinkedIn credentials in config.yaml)**

```python
# run in Python shell
import asyncio
from src.config import load_config
from src.scrapers.linkedin import LinkedInScraper

cfg = load_config()
lc = cfg.portals["linkedin"]
scraper = LinkedInScraper(lc.email, lc.password)

async def test():
    jobs = await scraper.search_jobs(
        roles=["Sales Engineer"],
        countries=["Australia"],
        max_jobs=3
    )
    for j in jobs:
        print(j.title, "|", j.company, "|", j.visa_sponsorship)

asyncio.run(test())
```

Expected: prints 1-3 job listings.

- [ ] **Step 3: Commit**

```bash
git add src/scrapers/linkedin.py
git commit -m "feat: linkedin scraper with stealth session, discovery only"
```

---

## Task 4: Indeed Scraper

**Files:**
- Create: `src/scrapers/indeed.py`

- [ ] **Step 1: Create `src/scrapers/indeed.py`**

```python
import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright
from src.scrapers.base import BaseScraper, has_visa_sponsorship, build_job_id, clean_text
from src.tracker import Job


class IndeedScraper(BaseScraper):
    PORTAL = "indeed"

    async def search_jobs(self, roles: list[str], countries: list[str], max_jobs: int = 100) -> list[Job]:
        jobs = []
        async with async_playwright() as p:
            await self._setup_context(p)
            for role in roles:
                for country in countries:
                    batch = await self._search_one(role, country, 10)
                    jobs.extend(batch)
                    if len(jobs) >= max_jobs:
                        break
                if len(jobs) >= max_jobs:
                    break
            await self.close()
        return jobs[:max_jobs]

    async def _search_one(self, role: str, country: str, limit: int) -> list[Job]:
        page = await self._new_stealth_page()
        query = f"{role} visa sponsorship".replace(" ", "+")
        location = country.replace(" ", "+")

        # Use the correct indeed domain per region
        domain = self._get_domain(country)
        url = f"https://{domain}/jobs?q={query}&l={location}&sort=date"

        await page.goto(url)
        await self._random_delay(2, 4)

        jobs = []
        cards = await page.query_selector_all("div.job_seen_beacon")
        for card in cards[:limit]:
            try:
                job = await self._parse_card(card, domain)
                if job:
                    jobs.append(job)
            except Exception:
                continue
            await self._random_delay(0.3, 1.0)

        await page.close()
        return jobs

    def _get_domain(self, country: str) -> str:
        domains = {
            "Australia": "au.indeed.com",
            "United Kingdom": "uk.indeed.com",
            "Canada": "ca.indeed.com",
            "Germany": "de.indeed.com",
            "France": "fr.indeed.com",
            "Netherlands": "nl.indeed.com",
        }
        return domains.get(country, "www.indeed.com")

    async def _parse_card(self, card, domain: str) -> Optional[Job]:
        title_el = await card.query_selector("h2.jobTitle span")
        company_el = await card.query_selector("span.companyName")
        location_el = await card.query_selector("div.companyLocation")
        link_el = await card.query_selector("h2.jobTitle a")

        if not all([title_el, link_el]):
            return None

        title = clean_text(await title_el.inner_text())
        company = clean_text(await company_el.inner_text()) if company_el else "Unknown"
        location = clean_text(await location_el.inner_text()) if location_el else ""
        href = await link_el.get_attribute("href")
        if not href:
            return None

        url = f"https://{domain}{href}" if href.startswith("/") else href
        job_id_match = re.search(r"jk=([a-z0-9]+)", url)
        raw_id = job_id_match.group(1) if job_id_match else re.sub(r"[^\w]", "", href)[-16:]

        country_part = location.split(",")[-1].strip() if "," in location else location

        return Job(
            id=build_job_id(self.PORTAL, raw_id),
            portal=self.PORTAL,
            title=title,
            company=company,
            location=location,
            country=country_part,
            url=url,
            description="",  # fetched by applier before applying
            visa_sponsorship=True,  # already filtered by search query
        )
```

- [ ] **Step 2: Commit**

```bash
git add src/scrapers/indeed.py
git commit -m "feat: indeed scraper with multi-region domain routing"
```

---

## Task 5: Seek Scraper

**Files:**
- Create: `src/scrapers/seek.py`

- [ ] **Step 1: Create `src/scrapers/seek.py`**

```python
import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright
from src.scrapers.base import BaseScraper, has_visa_sponsorship, build_job_id, clean_text
from src.tracker import Job


class SeekScraper(BaseScraper):
    PORTAL = "seek"
    BASE_URL = "https://www.seek.com.au"

    async def search_jobs(self, roles: list[str], max_jobs: int = 50) -> list[Job]:
        jobs = []
        async with async_playwright() as p:
            await self._setup_context(p)
            for role in roles:
                batch = await self._search_one(role, 10)
                jobs.extend(batch)
                if len(jobs) >= max_jobs:
                    break
            await self.close()
        return jobs[:max_jobs]

    async def _search_one(self, role: str, limit: int) -> list[Job]:
        page = await self._new_stealth_page()
        query = role.replace(" ", "-").lower()
        url = f"{self.BASE_URL}/{query}-jobs?visa=1&sortmode=ListedDate"
        await page.goto(url)
        await self._random_delay(2, 4)

        jobs = []
        cards = await page.query_selector_all("article[data-testid='job-card']")
        for card in cards[:limit]:
            try:
                job = await self._parse_card(card)
                if job:
                    jobs.append(job)
            except Exception:
                continue
        await page.close()
        return jobs

    async def _parse_card(self, card) -> Optional[Job]:
        title_el = await card.query_selector("a[data-testid='job-title']")
        company_el = await card.query_selector("a[data-testid='job-company-name']")
        location_el = await card.query_selector("span[data-testid='job-card-location']")

        if not title_el:
            return None

        title = clean_text(await title_el.inner_text())
        company = clean_text(await company_el.inner_text()) if company_el else "Unknown"
        location = clean_text(await location_el.inner_text()) if location_el else "Australia"
        url = "https://www.seek.com.au" + (await title_el.get_attribute("href") or "")
        job_id_match = re.search(r"/job/(\d+)", url)
        raw_id = job_id_match.group(1) if job_id_match else url[-10:]

        return Job(
            id=build_job_id(self.PORTAL, raw_id),
            portal=self.PORTAL,
            title=title,
            company=company,
            location=location,
            country="Australia",
            url=url,
            description="",
            visa_sponsorship=True,
        )
```

- [ ] **Step 2: Commit**

```bash
git add src/scrapers/seek.py
git commit -m "feat: seek scraper for australia jobs"
```

---

## Task 6: Reed and StepStone Scrapers

**Files:**
- Create: `src/scrapers/reed.py`
- Create: `src/scrapers/stepstone.py`

- [ ] **Step 1: Create `src/scrapers/reed.py`**

```python
import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright
from src.scrapers.base import BaseScraper, build_job_id, clean_text
from src.tracker import Job


class ReedScraper(BaseScraper):
    PORTAL = "reed"
    BASE_URL = "https://www.reed.co.uk"

    async def search_jobs(self, roles: list[str], max_jobs: int = 30) -> list[Job]:
        jobs = []
        async with async_playwright() as p:
            await self._setup_context(p)
            for role in roles:
                batch = await self._search_one(role, 10)
                jobs.extend(batch)
                if len(jobs) >= max_jobs:
                    break
            await self.close()
        return jobs[:max_jobs]

    async def _search_one(self, role: str, limit: int) -> list[Job]:
        page = await self._new_stealth_page()
        query = role.replace(" ", "-").lower()
        url = f"{self.BASE_URL}/jobs/{query}-jobs?keywords=visa+sponsorship&sortby=displaydate"
        await page.goto(url)
        await self._random_delay(2, 4)

        jobs = []
        cards = await page.query_selector_all("article.job-result")
        for card in cards[:limit]:
            try:
                job = await self._parse_card(card)
                if job:
                    jobs.append(job)
            except Exception:
                continue
        await page.close()
        return jobs

    async def _parse_card(self, card) -> Optional[Job]:
        title_el = await card.query_selector("h2.title a")
        company_el = await card.query_selector("span.recruiter")
        location_el = await card.query_selector("li.location span")

        if not title_el:
            return None

        title = clean_text(await title_el.inner_text())
        company = clean_text(await company_el.inner_text()) if company_el else "Unknown"
        location = clean_text(await location_el.inner_text()) if location_el else "United Kingdom"
        href = await title_el.get_attribute("href") or ""
        url = f"{self.BASE_URL}{href}" if href.startswith("/") else href
        job_id_match = re.search(r"/jobs/(\d+)", url)
        raw_id = job_id_match.group(1) if job_id_match else re.sub(r"[^\w]", "", href)[-10:]

        return Job(
            id=build_job_id(self.PORTAL, raw_id),
            portal=self.PORTAL,
            title=title,
            company=company,
            location=location,
            country="United Kingdom",
            url=url,
            description="",
            visa_sponsorship=True,
        )
```

- [ ] **Step 2: Create `src/scrapers/stepstone.py`**

```python
import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright
from src.scrapers.base import BaseScraper, build_job_id, clean_text
from src.tracker import Job


class StepStoneScraper(BaseScraper):
    PORTAL = "stepstone"
    BASE_URL = "https://www.stepstone.de"

    async def search_jobs(self, roles: list[str], countries: list[str], max_jobs: int = 30) -> list[Job]:
        jobs = []
        async with async_playwright() as p:
            await self._setup_context(p)
            for role in roles:
                batch = await self._search_one(role, 10)
                jobs.extend(batch)
                if len(jobs) >= max_jobs:
                    break
            await self.close()
        return jobs[:max_jobs]

    async def _search_one(self, role: str, limit: int) -> list[Job]:
        page = await self._new_stealth_page()
        query = role.replace(" ", "+")
        url = f"{self.BASE_URL}/jobs/{query}?q=visa+sponsorship&sort=2"
        await page.goto(url)
        await self._random_delay(2, 4)

        jobs = []
        cards = await page.query_selector_all("article.sc-beqWAB")
        for card in cards[:limit]:
            try:
                job = await self._parse_card(card)
                if job:
                    jobs.append(job)
            except Exception:
                continue
        await page.close()
        return jobs

    async def _parse_card(self, card) -> Optional[Job]:
        title_el = await card.query_selector("h2.sc-dAlyuH a")
        company_el = await card.query_selector("span.sc-hLBbgP")
        location_el = await card.query_selector("span.sc-iGkqmO")

        if not title_el:
            return None

        title = clean_text(await title_el.inner_text())
        company = clean_text(await company_el.inner_text()) if company_el else "Unknown"
        location = clean_text(await location_el.inner_text()) if location_el else "Germany"
        href = await title_el.get_attribute("href") or ""
        url = f"{self.BASE_URL}{href}" if href.startswith("/") else href
        job_id_match = re.search(r"/(\d+)", href)
        raw_id = job_id_match.group(1) if job_id_match else re.sub(r"[^\w]", "", href)[-10:]

        return Job(
            id=build_job_id(self.PORTAL, raw_id),
            portal=self.PORTAL,
            title=title,
            company=company,
            location=location,
            country="Germany",
            url=url,
            description="",
            visa_sponsorship=True,
        )
```

- [ ] **Step 3: Commit**

```bash
git add src/scrapers/reed.py src/scrapers/stepstone.py
git commit -m "feat: reed and stepstone scrapers"
```

---

## Task 7: Indeed Full-Auto Applier

**Files:**
- Create: `src/appliers/indeed.py`

- [ ] **Step 1: Create `src/appliers/indeed.py`**

```python
import asyncio
import random
from playwright.async_api import async_playwright, Page
from src.scrapers.base import BaseScraper, clean_text
from src.tracker import Job, Tracker
from src.cover_letter import CoverLetterGenerator


BILAL_PROFILE = {
    "first_name": "Bilal",
    "last_name": "Aslam",
    "email": "",        # filled from config
    "phone": "+60132216309",
    "location": "Johor Bahru, Malaysia",
    "years_experience": "1",
    "resume_path": "Bilal_Aslam_Resume_v2.html",
}


class IndeedApplier(BaseScraper):
    PORTAL = "indeed"

    def __init__(self, email: str, password: str, resume_path: str):
        super().__init__(email, password)
        BILAL_PROFILE["email"] = email
        BILAL_PROFILE["resume_path"] = resume_path

    async def apply(self, job: Job, cover_letter: str, tracker: Tracker) -> bool:
        async with async_playwright() as p:
            await self._setup_context(p)
            page = await self._new_stealth_page()
            try:
                success = await self._do_apply(page, job, cover_letter)
                if success:
                    tracker.update_status(job.id, "applied", cover_letter)
                await self.close()
                return success
            except Exception as e:
                await self.close()
                raise

    async def _do_apply(self, page: Page, job: Job, cover_letter: str) -> bool:
        await page.goto(job.url)
        await self._random_delay(2, 4)

        # Fetch description now if empty
        if not job.description:
            desc_el = await page.query_selector("div#jobDescriptionText")
            job.description = clean_text(await desc_el.inner_text()) if desc_el else ""

        # Look for Indeed Quick Apply button
        apply_btn = await page.query_selector("button[id='indeedApplyButton']")
        if not apply_btn:
            return False  # not Quick Apply — skip

        await apply_btn.click()
        await self._random_delay(2, 3)

        # Handle multi-step application form
        max_steps = 10
        for _ in range(max_steps):
            await self._fill_current_step(page, cover_letter)
            await self._random_delay(1, 2)

            next_btn = await page.query_selector("button[data-testid='continue-button']")
            submit_btn = await page.query_selector("button[data-testid='ia-continueButton']")

            if submit_btn:
                await submit_btn.click()
                await self._random_delay(2, 3)
                return True
            elif next_btn:
                await next_btn.click()
                await self._random_delay(1, 2)
            else:
                break

        return False

    async def _fill_current_step(self, page: Page, cover_letter: str):
        # Cover letter textarea
        cl_field = await page.query_selector("textarea[name='coverletter']")
        if cl_field:
            await cl_field.fill(cover_letter)

        # Phone field
        phone_field = await page.query_selector("input[name='phoneNumber']")
        if phone_field and not await phone_field.input_value():
            await phone_field.fill(BILAL_PROFILE["phone"])

        # Years of experience dropdowns
        exp_selects = await page.query_selector_all("select[name*='experience']")
        for sel in exp_selects:
            options = await sel.evaluate("el => [...el.options].map(o => o.value)")
            if "1" in options:
                await sel.select_option("1")
            elif options:
                await sel.select_option(options[0])

        # Yes/No radio buttons — default to "Yes" for sponsorship questions
        radios = await page.query_selector_all("input[type='radio'][value='yes']")
        for radio in radios:
            label = await radio.evaluate("el => el.closest('label')?.innerText || ''")
            if "sponsor" in label.lower() or "reloc" in label.lower():
                await radio.click()
```

- [ ] **Step 2: Commit**

```bash
git add src/appliers/indeed.py
git commit -m "feat: indeed quick apply full automation"
```

---

## Task 8: Semi-Auto Applier (Seek, Reed, StepStone)

**Files:**
- Create: `src/appliers/semi_auto.py`

- [ ] **Step 1: Create `src/appliers/semi_auto.py`**

```python
import asyncio
import subprocess
import sys
from playwright.async_api import async_playwright, Page
from src.scrapers.base import BaseScraper
from src.tracker import Job, Tracker


class SemiAutoApplier(BaseScraper):
    """
    Fills application form fields, then opens the browser visibly for the user to review
    and click Submit. Waits for user confirmation via CLI before marking as applied.
    """

    def __init__(self, portal: str, email: str, password: str):
        super().__init__(email, password)
        self.PORTAL = portal

    async def apply(self, job: Job, cover_letter: str, tracker: Tracker) -> bool:
        async with async_playwright() as p:
            # Use headful browser so user can see and submit
            self._browser = await p.chromium.launch(headless=False)
            context_kwargs = {"viewport": {"width": 1280, "height": 900}}
            if self._session_file.exists():
                context_kwargs["storage_state"] = str(self._session_file)
            self._context = await self._browser.new_context(**context_kwargs)

            page = await self._context.new_page()
            try:
                await page.goto(job.url)
                await asyncio.sleep(2)
                await self._fill_fields(page, cover_letter)

                print(f"\n[MANUAL APPLY] Browser open for: {job.title} at {job.company}")
                print(f"URL: {job.url}")
                print("Review the pre-filled form, make any changes, then click SUBMIT.")
                response = input("Did you submit the application? (yes/skip): ").strip().lower()

                if response == "yes":
                    tracker.update_status(job.id, "applied", cover_letter)
                    await self.close()
                    return True
                else:
                    await self.close()
                    return False
            except Exception:
                await self.close()
                raise

    async def _fill_fields(self, page: Page, cover_letter: str):
        await asyncio.sleep(2)

        # Generic field filling — works across most portals
        selectors = {
            "input[name*='cover'], textarea[name*='cover'], div[aria-label*='cover'] textarea": cover_letter,
            "input[name*='phone'], input[placeholder*='phone'], input[type='tel']": "+60132216309",
            "input[name*='first'], input[placeholder*='first name']": "Bilal",
            "input[name*='last'], input[placeholder*='last name']": "Aslam",
            "input[name*='email'], input[type='email']": self.email,
        }

        for selector, value in selectors.items():
            try:
                field = await page.query_selector(selector)
                if field:
                    tag = await field.evaluate("el => el.tagName.toLowerCase()")
                    if tag == "textarea" or (tag == "input" and "cover" in selector):
                        await field.fill(value)
                    else:
                        current = await field.input_value()
                        if not current:
                            await field.fill(value)
            except Exception:
                continue
```

- [ ] **Step 2: Commit**

```bash
git add src/appliers/semi_auto.py
git commit -m "feat: semi-auto applier fills form fields, hands off to user for submit"
```

---

## Task 9: Status Checkers

**Files:**
- Create: `src/status_checker/base.py`
- Create: `src/status_checker/linkedin.py`
- Create: `src/status_checker/indeed.py`

- [ ] **Step 1: Create `src/status_checker/base.py`**

```python
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
}


def normalise_status(raw: str) -> str:
    lower = raw.lower().strip()
    for key, value in STATUS_MAP.items():
        if key in lower:
            return value
    return raw.lower().strip()


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
```

- [ ] **Step 2: Write tests for base status checker**

Create `tests/test_status_checker.py`:

```python
from src.status_checker.base import normalise_status, record_status_change
from src.tracker import Tracker, Job
import pytest


@pytest.fixture
def tracker(tmp_path):
    t = Tracker(str(tmp_path / "test.db"))
    t.init_db()
    return t


def test_normalise_viewed():
    assert normalise_status("Application Viewed") == "viewed"

def test_normalise_in_review():
    assert normalise_status("Under Review") == "in_review"

def test_normalise_rejected():
    assert normalise_status("Not selected for this role") == "rejected"

def test_record_change_inserts_event(tracker):
    job = Job(id="linkedin:1", portal="linkedin", title="Eng", company="ACME",
              location="UK", country="UK", url="https://x.com", description="",
              visa_sponsorship=True, status="applied")
    tracker.insert_job(job)
    changed = record_status_change(tracker, job, "Application Viewed")
    assert changed is True
    events = tracker.get_events("linkedin:1")
    assert len(events) == 1
    assert events[0].new_status == "viewed"

def test_no_change_when_same_status(tracker):
    job = Job(id="linkedin:2", portal="linkedin", title="Eng", company="ACME",
              location="UK", country="UK", url="https://x.com", description="",
              visa_sponsorship=True, status="viewed")
    tracker.insert_job(job)
    changed = record_status_change(tracker, job, "Application Viewed")
    assert changed is False
```

- [ ] **Step 3: Run tests**

```powershell
pytest tests/test_status_checker.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 4: Create `src/status_checker/linkedin.py`**

```python
import asyncio
from playwright.async_api import async_playwright
from src.scrapers.base import BaseScraper, clean_text
from src.status_checker.base import record_status_change
from src.tracker import Tracker


class LinkedInStatusChecker(BaseScraper):
    PORTAL = "linkedin"

    async def check_all(self, tracker: Tracker) -> list[dict]:
        """Check My Applications page and update statuses."""
        changes = []
        async with async_playwright() as p:
            await self._setup_context(p)
            page = await self._new_stealth_page()
            await page.goto("https://www.linkedin.com/my-items/saved-jobs/?cardType=APPLIED")
            await self._random_delay(2, 4)

            cards = await page.query_selector_all("div.reusable-search__result-container")
            for card in cards:
                try:
                    title_el = await card.query_selector("span.entity-result__title-text")
                    company_el = await card.query_selector("span.entity-result__primary-subtitle")
                    status_el = await card.query_selector("span.job-application-status")
                    link_el = await card.query_selector("a.app-aware-link")

                    if not (title_el and link_el):
                        continue

                    href = await link_el.get_attribute("href") or ""
                    import re
                    job_id_match = re.search(r"/jobs/view/(\d+)", href)
                    if not job_id_match:
                        continue

                    job_id = f"linkedin:{job_id_match.group(1)}"
                    job = tracker.get_job(job_id)
                    if not job:
                        continue

                    if status_el:
                        raw_status = clean_text(await status_el.inner_text())
                        changed = record_status_change(tracker, job, raw_status)
                        if changed:
                            changes.append({"job_id": job_id, "new_status": raw_status})
                except Exception:
                    continue

            await self.close()
        return changes
```

- [ ] **Step 5: Create `src/status_checker/indeed.py`**

```python
import asyncio
from playwright.async_api import async_playwright
from src.scrapers.base import BaseScraper, clean_text
from src.status_checker.base import record_status_change
from src.tracker import Tracker


class IndeedStatusChecker(BaseScraper):
    PORTAL = "indeed"

    async def check_all(self, tracker: Tracker) -> list[dict]:
        changes = []
        async with async_playwright() as p:
            await self._setup_context(p)
            page = await self._new_stealth_page()
            await page.goto("https://my.indeed.com/applied-jobs")
            await self._random_delay(2, 4)

            rows = await page.query_selector_all("div[data-testid='jobCard']")
            for row in rows:
                try:
                    import re
                    link_el = await row.query_selector("a[data-testid='jobTitle']")
                    status_el = await row.query_selector("span[data-testid='applicationStatus']")

                    if not link_el:
                        continue

                    href = await link_el.get_attribute("href") or ""
                    jk_match = re.search(r"jk=([a-z0-9]+)", href)
                    if not jk_match:
                        continue

                    job_id = f"indeed:{jk_match.group(1)}"
                    job = tracker.get_job(job_id)
                    if not job:
                        continue

                    if status_el:
                        raw_status = clean_text(await status_el.inner_text())
                        changed = record_status_change(tracker, job, raw_status)
                        if changed:
                            changes.append({"job_id": job_id, "new_status": raw_status})
                except Exception:
                    continue

            await self.close()
        return changes
```

- [ ] **Step 6: Commit**

```bash
git add src/status_checker/ tests/test_status_checker.py
git commit -m "feat: status checkers for linkedin and indeed with event recording"
```

---

## Task 10: Runner — Orchestrate Full Run

**Files:**
- Create: `src/runner.py`

- [ ] **Step 1: Create `src/runner.py`**

```python
import asyncio
import random
from src.config import Config
from src.tracker import Tracker, Job
from src.notifier import Notifier
from src.cover_letter import CoverLetterGenerator
from src.scrapers.linkedin import LinkedInScraper
from src.scrapers.indeed import IndeedScraper
from src.scrapers.seek import SeekScraper
from src.scrapers.reed import ReedScraper
from src.scrapers.stepstone import StepStoneScraper
from src.appliers.indeed import IndeedApplier
from src.appliers.semi_auto import SemiAutoApplier
from src.status_checker.linkedin import LinkedInStatusChecker
from src.status_checker.indeed import IndeedStatusChecker


class Runner:
    def __init__(self, config: Config):
        self.cfg = config
        self.tracker = Tracker()
        self.tracker.init_db()
        self.notifier = Notifier(config.telegram_bot_token, config.telegram_chat_id)
        resume_text = CoverLetterGenerator.load_resume(config.resume_path)
        self.cover_letter_gen = CoverLetterGenerator(config.anthropic_api_key, resume_text)

    async def run_search(self) -> list[Job]:
        """Scrape all enabled portals, return new jobs not yet in DB."""
        all_jobs = []
        cfg = self.cfg
        countries = cfg.search.all_countries()
        roles = cfg.search.roles

        if cfg.portals["linkedin"].enabled:
            p = cfg.portals["linkedin"]
            scraper = LinkedInScraper(p.email, p.password)
            jobs = await scraper.search_jobs(roles, countries[:8], cfg.search.max_jobs_per_run // 5)
            all_jobs.extend(jobs)

        if cfg.portals["indeed"].enabled:
            p = cfg.portals["indeed"]
            scraper = IndeedScraper(p.email, p.password)
            jobs = await scraper.search_jobs(roles, countries, cfg.search.max_jobs_per_run // 5)
            all_jobs.extend(jobs)

        if cfg.portals["seek"].enabled:
            p = cfg.portals["seek"]
            scraper = SeekScraper(p.email, p.password)
            jobs = await scraper.search_jobs(roles, cfg.search.max_jobs_per_run // 5)
            all_jobs.extend(jobs)

        if cfg.portals["reed"].enabled:
            p = cfg.portals["reed"]
            scraper = ReedScraper(p.email, p.password)
            jobs = await scraper.search_jobs(roles, cfg.search.max_jobs_per_run // 5)
            all_jobs.extend(jobs)

        if cfg.portals["stepstone"].enabled:
            p = cfg.portals["stepstone"]
            scraper = StepStoneScraper(p.email, p.password)
            jobs = await scraper.search_jobs(roles, countries, cfg.search.max_jobs_per_run // 5)
            all_jobs.extend(jobs)

        # Save new jobs, notify
        new_jobs = []
        for job in all_jobs:
            if job.visa_sponsorship and not self.tracker.get_job(job.id):
                self.tracker.insert_job(job)
                await self.notifier.notify_new_job(job)
                new_jobs.append(job)

        print(f"Found {len(new_jobs)} new jobs.")
        return new_jobs

    async def run_apply(self):
        """Apply to all unapplied jobs in DB."""
        jobs = self.tracker.get_unapplied_jobs()
        cfg = self.cfg
        rl = cfg.rate_limits
        applied_counts = {portal: 0 for portal in cfg.portals}

        for job in jobs:
            max_for_portal = rl.max_applications_per_day.get(job.portal, 0)
            if max_for_portal == 0:
                # LinkedIn — open in browser for manual apply
                import webbrowser
                print(f"\n[LINKEDIN] Open manually: {job.title} at {job.company}\n{job.url}")
                webbrowser.open(job.url)
                continue

            if applied_counts[job.portal] >= max_for_portal:
                continue

            # Generate cover letter
            try:
                letter = self.cover_letter_gen.generate(job)
                self.cover_letter_gen.save(job, letter)
            except Exception as e:
                print(f"Cover letter failed for {job.id}: {e}")
                letter = f"Dear Hiring Manager,\n\nI am writing to apply for the {job.title} position at {job.company}.\n\nI am an Electrical & Electronics Engineer with experience in industrial automation and project coordination. I require visa sponsorship as a Sri Lankan citizen currently based in Malaysia.\n\nI look forward to discussing this opportunity.\n\nBest regards,\nBilal Aslam"

            try:
                if job.portal == "indeed":
                    p = cfg.portals["indeed"]
                    applier = IndeedApplier(p.email, p.password, cfg.resume_path)
                    success = await applier.apply(job, letter, self.tracker)
                else:
                    p = cfg.portals[job.portal]
                    applier = SemiAutoApplier(job.portal, p.email, p.password)
                    success = await applier.apply(job, letter, self.tracker)

                if success:
                    applied_counts[job.portal] += 1
                    await self.notifier.notify_applied(job, letter[:200])
                    print(f"Applied: {job.title} at {job.company}")

            except Exception as e:
                print(f"Apply failed for {job.id}: {e}")
                await self.notifier.notify_error(job.portal, str(e))

            # Rate limit delay
            delay = rl.delay_between_applications_seconds
            jitter = rl.delay_randomisation_seconds
            await asyncio.sleep(delay + random.uniform(0, jitter))

    async def run_check(self):
        """Check all portals for status updates, fire Telegram alerts."""
        cfg = self.cfg
        all_changes = []

        if cfg.portals["linkedin"].enabled:
            p = cfg.portals["linkedin"]
            checker = LinkedInStatusChecker(p.email, p.password)
            changes = await checker.check_all(self.tracker)
            all_changes.extend(changes)

        if cfg.portals["indeed"].enabled:
            p = cfg.portals["indeed"]
            checker = IndeedStatusChecker(p.email, p.password)
            changes = await checker.check_all(self.tracker)
            all_changes.extend(changes)

        # Notify on all unnotified events
        events = self.tracker.get_unnotified_events()
        notified_ids = []
        for event in events:
            job = self.tracker.get_job(event.job_id)
            if job:
                await self.notifier.notify_status_change(job, event)
                notified_ids.append(event.id)
        if notified_ids:
            self.tracker.mark_events_notified(notified_ids)

        print(f"Status check complete. {len(all_changes)} changes found.")

    async def run_full(self):
        await self.run_search()
        await self.run_apply()
        await self.run_check()

    def close(self):
        self.tracker.close()
```

- [ ] **Step 2: Commit**

```bash
git add src/runner.py
git commit -m "feat: runner orchestrates full search-apply-check cycle"
```

---

## Task 11: Wire Runner into CLI

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update `main.py` to wire in runner**

Replace the stub command bodies in `main.py`:

```python
import asyncio
import click
from src.config import load_config, ConfigError
from src.tracker import Tracker
from src.runner import Runner


@click.group()
def cli():
    pass


@cli.command()
def config():
    """Validate config.yaml."""
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
        "found": "🔍 Found",
        "applied": "✅ Applied",
        "viewed": "👀 Viewed",
        "in_review": "📋 In Review",
        "interview": "🎉 Interview",
        "rejected": "❌ Rejected",
        "skipped": "⏭  Skipped",
    }
    for key, label in labels.items():
        count = stats.get(key, 0)
        if count:
            click.echo(f"  {label}: {count}")
    click.echo("─" * 30)
    click.echo(f"  Total: {sum(stats.values())}\n")


@cli.command()
def search():
    """Search for jobs without applying."""
    cfg = load_config()
    runner = Runner(cfg)
    try:
        asyncio.run(runner.run_search())
    finally:
        runner.close()


@cli.command()
def apply():
    """Apply to all unapplied jobs in DB."""
    cfg = load_config()
    runner = Runner(cfg)
    try:
        asyncio.run(runner.run_apply())
    finally:
        runner.close()


@cli.command()
def check():
    """Check application statuses on all portals."""
    cfg = load_config()
    runner = Runner(cfg)
    try:
        asyncio.run(runner.run_check())
    finally:
        runner.close()


@cli.command()
def run():
    """Full cycle: search + apply + check."""
    cfg = load_config()
    runner = Runner(cfg)
    try:
        asyncio.run(runner.run_full())
    finally:
        runner.close()


if __name__ == "__main__":
    cli()
```

- [ ] **Step 2: Test CLI**

```powershell
python main.py config
python main.py status
```

Expected: config valid, empty status dashboard.

- [ ] **Step 3: Run all tests**

```powershell
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: wire runner into all CLI commands"
```

---

## Task 12: Windows Installer

**Files:**
- Create: `install.ps1`
- Create: `README.md`

- [ ] **Step 1: Create `install.ps1`**

```powershell
# Job Application Bot Installer
# Run as Administrator: irm https://raw.githubusercontent.com/YOUR_REPO/main/install.ps1 | iex

$ErrorActionPreference = "Stop"
$REPO_URL = "https://github.com/YOUR_GITHUB_USERNAME/job-bot"
$INSTALL_DIR = "$env:USERPROFILE\job-bot"

Write-Host "=== Job Application Bot Installer ===" -ForegroundColor Cyan

# 1. Install Python 3.11 if not present
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Installing Python 3.11..." -ForegroundColor Yellow
    winget install Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
}
$pythonVersion = python --version 2>&1
Write-Host "Python: $pythonVersion" -ForegroundColor Green

# 2. Install Git if not present
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Host "Installing Git..." -ForegroundColor Yellow
    winget install Git.Git --silent --accept-source-agreements --accept-package-agreements
}

# 3. Clone or update repo
if (Test-Path $INSTALL_DIR) {
    Write-Host "Updating existing installation..." -ForegroundColor Yellow
    Set-Location $INSTALL_DIR
    git pull
} else {
    Write-Host "Cloning repository..." -ForegroundColor Yellow
    git clone $REPO_URL $INSTALL_DIR
    Set-Location $INSTALL_DIR
}

# 4. Create virtual environment
Write-Host "Setting up Python environment..." -ForegroundColor Yellow
python -m venv .venv
& .venv\Scripts\Activate.ps1
pip install -r requirements.txt --quiet

# 5. Install Playwright Chromium
Write-Host "Downloading Chromium browser (~150MB)..." -ForegroundColor Yellow
playwright install chromium

# 6. Create config.yaml from template
if (-not (Test-Path "config.yaml")) {
    Copy-Item config.template.yaml config.yaml
    Write-Host "Created config.yaml — FILL IN YOUR CREDENTIALS before running!" -ForegroundColor Yellow
} else {
    Write-Host "config.yaml already exists — keeping your settings." -ForegroundColor Green
}

# 7. Create Windows Task Scheduler tasks (runs 3x/day)
$taskName = "JobBot"
$scriptPath = "$INSTALL_DIR\run.bat"

$times = @("08:00", "13:00", "18:00")
foreach ($time in $times) {
    $taskNameFull = "$taskName-$($time.Replace(':', ''))"
    $existingTask = Get-ScheduledTask -TaskName $taskNameFull -ErrorAction SilentlyContinue
    if ($existingTask) {
        Unregister-ScheduledTask -TaskName $taskNameFull -Confirm:$false
    }
    $action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$scriptPath`""
    $trigger = New-ScheduledTaskTrigger -Daily -At $time
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 2)
    Register-ScheduledTask -TaskName $taskNameFull -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest | Out-Null
    Write-Host "Scheduled task created: $taskNameFull at $time" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Installation Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Open: $INSTALL_DIR\config.yaml"
Write-Host "2. Fill in: anthropic_api_key, telegram_bot_token, telegram_chat_id"
Write-Host "3. Fill in portal credentials (LinkedIn, Indeed, Seek, Reed, StepStone)"
Write-Host "4. Test: python main.py config"
Write-Host "5. Run: python main.py run"
Write-Host ""
Write-Host "Bot will run automatically at 8am, 1pm, 6pm daily." -ForegroundColor Green
```

- [ ] **Step 2: Create `README.md`**

```markdown
# Job Application Bot

Automated job application bot for engineering roles with visa sponsorship. Searches LinkedIn, Indeed, Seek, Reed, and StepStone globally, generates AI-tailored cover letters, and applies automatically or semi-automatically.

## Quick Install (Windows)

Open PowerShell as Administrator and run:

```powershell
irm https://raw.githubusercontent.com/YOUR_USERNAME/job-bot/main/install.ps1 | iex
```

This installs Python, downloads the bot, sets up the browser, and schedules 3 daily runs.

## Setup After Install

1. Open `config.yaml` in Notepad or VS Code
2. Fill in:
   - `anthropic_api_key` — from console.anthropic.com
   - `telegram_bot_token` — from @BotFather on Telegram
   - `telegram_chat_id` — your Telegram user ID
   - Portal credentials (email + password for each job site)
3. Test config: `python main.py config`
4. First run: `python main.py search` (finds jobs without applying)
5. Full run: `python main.py run`

## Commands

| Command | What it does |
|---------|-------------|
| `python main.py run` | Full cycle: search + apply + check |
| `python main.py search` | Find new jobs only |
| `python main.py apply` | Apply to found jobs |
| `python main.py check` | Check application statuses |
| `python main.py status` | View dashboard |
| `python main.py config` | Validate config |

## Cost

~$3-6/month (Claude API for cover letters only). Everything else is free.

## Notes

- LinkedIn: discovery only (no auto-apply, protects your account)
- Indeed: full auto via Quick Apply
- Seek, Reed, StepStone: semi-auto (bot fills form, you click Submit)
- Telegram alerts for every event: new jobs, applications, status changes, recruiter messages
```

- [ ] **Step 3: Commit everything**

```bash
git add install.ps1 README.md
git commit -m "feat: windows installer and readme"
```

---

## Final Test

- [ ] **Run full test suite**

```powershell
pytest -v
```

Expected: all tests PASS.

- [ ] **End-to-end smoke test**

```powershell
python main.py config
python main.py search
python main.py status
```

Expected: config valid, jobs appear in DB, status dashboard shows counts.

---

## Plan B Complete

Full bot is operational:
- ✅ LinkedIn stealth scraper (discovery + manual apply)
- ✅ Indeed scraper + full-auto Quick Apply
- ✅ Seek, Reed, StepStone scrapers + semi-auto apply
- ✅ LinkedIn + Indeed status checkers
- ✅ Full run orchestrator
- ✅ Windows installer (single PowerShell command)
- ✅ README with step-by-step setup
