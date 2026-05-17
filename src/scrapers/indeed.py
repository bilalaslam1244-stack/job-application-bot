import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright
from src.scrapers.base import BaseScraper, build_job_id, clean_text
from src.tracker import Job

# Indeed regional domains
COUNTRY_DOMAINS = {
    "Australia": "au.indeed.com",
    "United Kingdom": "uk.indeed.com",
    "Canada": "ca.indeed.com",
    "Germany": "de.indeed.com",
    "France": "fr.indeed.com",
    "Netherlands": "nl.indeed.com",
    "Ireland": "ie.indeed.com",
    "Singapore": "sg.indeed.com",
    "New Zealand": "nz.indeed.com",
    "Sweden": "se.indeed.com",
    "Norway": "no.indeed.com",
    "Finland": "fi.indeed.com",
    "South Korea": "kr.indeed.com",
    "Japan": "jp.indeed.com",
    "Hong Kong": "hk.indeed.com",
}

# Indeed uses city/region names, not country names
LOCATION_NAMES = {
    "UAE": "Dubai",
    "Qatar": "Doha",
    "Saudi Arabia": "Riyadh",
    "Australia": "Australia",
    "United Kingdom": "United Kingdom",
    "Ireland": "Ireland",
    "France": "France",
    "Belgium": "Brussels",
    "Germany": "Germany",
    "Netherlands": "Netherlands",
    "Canada": "Canada",
    "Luxembourg": "Luxembourg",
    "New Zealand": "New Zealand",
    "Singapore": "Singapore",
    "Sweden": "Sweden",
    "Norway": "Oslo",
    "Denmark": "Copenhagen",
    "Switzerland": "Zurich",
    "Austria": "Vienna",
    "Finland": "Finland",
    "USA": "United States",
    "Japan": "Japan",
    "South Korea": "South Korea",
    "Portugal": "Lisbon",
    "Spain": "Madrid",
    "Italy": "Milan",
    "Czech Republic": "Prague",
    "Poland": "Warsaw",
    "Hong Kong": "Hong Kong",
    "Bahrain": "Manama",
    "Kuwait": "Kuwait City",
    "Oman": "Muscat",
}

# Indeed selectors — multiple fallbacks as they change frequently
CARD_SELECTORS = [
    "div.job_seen_beacon",
    "div.resultContent",
    "li.css-5lfssm",
    "div[class*='result ']",
    "td.resultContent",
]
TITLE_SELECTORS = ["h2.jobTitle span[title]", "h2.jobTitle span", "h2 a span"]
COMPANY_SELECTORS = ["span.companyName", "[data-testid='company-name']", "span[class*='companyName']"]
LOCATION_SELECTORS = ["div.companyLocation", "[data-testid='text-location']", "div[class*='companyLocation']"]
LINK_SELECTORS = ["h2.jobTitle a", "h2 a[id*='job_']", "a[data-jk]"]


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

    def _get_location(self, country: str) -> str:
        return LOCATION_NAMES.get(country, country)

    async def _search_one(self, role: str, country: str, limit: int) -> list[Job]:
        page = await self._new_stealth_page()
        domain = self._get_domain(country)
        location = self._get_location(country)
        # Search role only — no "visa sponsorship" in query (kills results)
        query = role.replace(" ", "+")
        loc = location.replace(" ", "+")
        url = f"https://{domain}/jobs?q={query}&l={loc}&sort=date&fromage=14"
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(3)  # wait for JS render

        # Try multiple card selectors
        cards = []
        for sel in CARD_SELECTORS:
            cards = await page.query_selector_all(sel)
            if cards:
                break

        jobs = []
        for card in cards[:limit]:
            try:
                job = await self._parse_card(card, domain, country)
                if job:
                    jobs.append(job)
            except Exception:
                continue
            await self._random_delay(0.2, 0.5)

        await page.close()
        return jobs

    async def _parse_card(self, card, domain: str, country: str) -> Optional[Job]:
        # Try multiple selectors for each field
        title_el = None
        for sel in TITLE_SELECTORS:
            title_el = await card.query_selector(sel)
            if title_el:
                break

        link_el = None
        for sel in LINK_SELECTORS:
            link_el = await card.query_selector(sel)
            if link_el:
                break

        if not (title_el and link_el):
            return None

        title = clean_text(await title_el.inner_text())
        if not title or title.lower() in ("", "full job title"):
            return None

        company_el = None
        for sel in COMPANY_SELECTORS:
            company_el = await card.query_selector(sel)
            if company_el:
                break
        company = clean_text(await company_el.inner_text()) if company_el else "Unknown"

        location_el = None
        for sel in LOCATION_SELECTORS:
            location_el = await card.query_selector(sel)
            if location_el:
                break
        location = clean_text(await location_el.inner_text()) if location_el else country

        href = await link_el.get_attribute("href") or ""
        url = f"https://{domain}{href}" if href.startswith("/") else href
        match = re.search(r"jk=([a-z0-9]+)", url)
        jk = match.group(1) if match else re.sub(r"[^\w]", "", href)[-16:]

        return Job(
            id=build_job_id(self.PORTAL, jk),
            portal=self.PORTAL,
            title=title,
            company=company,
            location=location,
            country=country,
            url=url,
            description="",
            visa_sponsorship=True,  # will verify at apply time
        )
