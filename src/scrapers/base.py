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
    "willing to sponsor", "provide sponsorship", "visa assistance",
]

NO_SPONSORSHIP_KEYWORDS = [
    "no sponsorship", "must have right to work", "citizens only",
    "no visa", "sponsorship not available", "must be eligible to work",
    "no work permit", "must already have",
]


def has_visa_sponsorship(text: str) -> bool:
    lower = text.lower()
    if any(kw in lower for kw in NO_SPONSORSHIP_KEYWORDS):
        return False
    return any(kw in lower for kw in VISA_KEYWORDS)


def build_job_id(portal: str, raw_id: str) -> str:
    return f"{portal}:{raw_id}"


RELEVANT_TITLE_KEYWORDS = [
    "engineer", "engineering", "sales", "automation", "technical", "commissioning",
    "project", "field service", "controls", "instrumentation", "scada", "plc",
    "industrial", "mechanical", "electrical", "system", "service", "technician",
    "business development", "account manager", "solutions", "pre-sales",
]

IRRELEVANT_TITLE_KEYWORDS = [
    "diesel mechanic", "tradie", "chef", "nurse", "teacher", "driver",
    "cleaner", "barista", "retail", "hospitality", "childcare", "hairdresser",
    "accountant", "lawyer", "solicitor", "dentist", "doctor",
]


def is_relevant_title(title: str) -> bool:
    lower = title.lower()
    if any(kw in lower for kw in IRRELEVANT_TITLE_KEYWORDS):
        return False
    return any(kw in lower for kw in RELEVANT_TITLE_KEYWORDS)


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
        kwargs = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        if self._session_file.exists():
            kwargs["storage_state"] = str(self._session_file)
        self._context = await self._browser.new_context(**kwargs)
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
            self._browser = None
            self._context = None
