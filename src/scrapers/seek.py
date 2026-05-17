import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright
from src.scrapers.base import BaseScraper, build_job_id, clean_text
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
        url = f"{self.BASE_URL}/{query}-jobs?sortmode=ListedDate&daterange=7"
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        jobs = []
        cards = []
        for sel in ["article[data-testid='job-card']", "article[data-card-type='JobCard']", "div[data-automation='jobListing']"]:
            cards = await page.query_selector_all(sel)
            if cards:
                break
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
        href = await title_el.get_attribute("href") or ""
        url = f"{self.BASE_URL}{href}" if href.startswith("/") else href
        match = re.search(r"/job/(\d+)", url)
        raw_id = match.group(1) if match else url[-10:]

        return Job(
            id=build_job_id(self.PORTAL, raw_id),
            portal=self.PORTAL,
            title=title, company=company,
            location=location, country="Australia",
            url=url, description="", visa_sponsorship=True,
        )
