import re
from typing import Optional
from playwright.async_api import async_playwright
from src.scrapers.base import BaseScraper, build_job_id, clean_text
from src.tracker import Job


class StepStoneScraper(BaseScraper):
    PORTAL = "stepstone"
    BASE_URL = "https://www.stepstone.de"

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
        match = re.search(r"/(\d+)", href)
        raw_id = match.group(1) if match else re.sub(r"[^\w]", "", href)[-10:]

        return Job(
            id=build_job_id(self.PORTAL, raw_id),
            portal=self.PORTAL,
            title=title, company=company,
            location=location, country="Germany",
            url=url, description="", visa_sponsorship=True,
        )
