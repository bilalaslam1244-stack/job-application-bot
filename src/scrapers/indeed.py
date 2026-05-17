import re
from typing import Optional
from playwright.async_api import async_playwright
from src.scrapers.base import BaseScraper, build_job_id, clean_text
from src.tracker import Job

COUNTRY_DOMAINS = {
    "Australia": "au.indeed.com",
    "United Kingdom": "uk.indeed.com",
    "Canada": "ca.indeed.com",
    "Germany": "de.indeed.com",
    "France": "fr.indeed.com",
    "Netherlands": "nl.indeed.com",
    "Ireland": "ie.indeed.com",
    "Belgium": "www.indeed.com",
}


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

    def _get_domain(self, country: str) -> str:
        return COUNTRY_DOMAINS.get(country, "www.indeed.com")

    async def _search_one(self, role: str, country: str, limit: int) -> list[Job]:
        page = await self._new_stealth_page()
        domain = self._get_domain(country)
        query = f"{role} visa sponsorship".replace(" ", "+")
        location = country.replace(" ", "+")
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

    async def _parse_card(self, card, domain: str) -> Optional[Job]:
        title_el = await card.query_selector("h2.jobTitle span")
        company_el = await card.query_selector("span.companyName")
        location_el = await card.query_selector("div.companyLocation")
        link_el = await card.query_selector("h2.jobTitle a")

        if not (title_el and link_el):
            return None

        title = clean_text(await title_el.inner_text())
        company = clean_text(await company_el.inner_text()) if company_el else "Unknown"
        location = clean_text(await location_el.inner_text()) if location_el else ""
        href = await link_el.get_attribute("href") or ""
        url = f"https://{domain}{href}" if href.startswith("/") else href
        match = re.search(r"jk=([a-z0-9]+)", url)
        raw_id = match.group(1) if match else re.sub(r"[^\w]", "", href)[-16:]
        country_part = location.split(",")[-1].strip() if "," in location else location

        return Job(
            id=build_job_id(self.PORTAL, raw_id),
            portal=self.PORTAL,
            title=title,
            company=company,
            location=location,
            country=country_part,
            url=url,
            description="",
            visa_sponsorship=True,
        )
