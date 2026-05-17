import re
from typing import Optional
from playwright.async_api import async_playwright
from src.scrapers.base import BaseScraper, has_visa_sponsorship, build_job_id, clean_text
from src.tracker import Job


class LinkedInScraper(BaseScraper):
    PORTAL = "linkedin"
    BASE_URL = "https://www.linkedin.com"

    # LinkedIn uses city names better than country names
    LOCATION_MAP = {
        "UAE": "Dubai",
        "Qatar": "Doha",
        "Saudi Arabia": "Riyadh",
        "Australia": "Australia",
        "United Kingdom": "United Kingdom",
        "France": "France",
        "Germany": "Germany",
        "Netherlands": "Netherlands",
        "Canada": "Canada",
        "Singapore": "Singapore",
        "Ireland": "Ireland",
        "Belgium": "Belgium",
        "Sweden": "Sweden",
        "Norway": "Oslo",
        "Switzerland": "Zurich",
        "Denmark": "Copenhagen",
        "Austria": "Vienna",
        "Finland": "Helsinki",
        "USA": "United States",
        "New Zealand": "New Zealand",
        "Japan": "Japan",
        "South Korea": "South Korea",
        "Luxembourg": "Luxembourg",
        "Hong Kong": "Hong Kong",
    }

    async def search_jobs(self, roles: list[str], countries: list[str], max_jobs: int = 100) -> list[Job]:
        jobs = []
        async with async_playwright() as p:
            await self._setup_context(p)
            per_combo = max(2, max_jobs // max(1, len(roles) * len(countries)))
            for role in roles:
                for country in countries:
                    location = self.LOCATION_MAP.get(country, country)
                    batch = await self._search_one(role, location, per_combo)
                    jobs.extend(batch)
                    if len(jobs) >= max_jobs:
                        break
                if len(jobs) >= max_jobs:
                    break
            await self.close()
        return jobs[:max_jobs]

    async def _search_one(self, role: str, country: str, limit: int) -> list[Job]:
        page = await self._new_stealth_page()
        query = role.replace(" ", "%20")
        location = country.replace(" ", "%20")
        url = f"{self.BASE_URL}/jobs/search/?keywords={query}&location={location}&sortBy=DD&f_TPR=r604800"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await self._random_delay(2, 3)

        jobs = []
        # Try multiple selectors — LinkedIn changes these frequently
        cards = []
        for sel in ["div.job-search-card", "li.jobs-search-results__list-item", "div[data-job-id]", "li[class*='job-result']"]:
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
            await self._random_delay(0.5, 1.5)

        await page.close()
        return jobs

    async def _parse_card(self, card) -> Optional[Job]:
        # Link — try all known LinkedIn card link selectors
        link_el = (
            await card.query_selector("a.base-card__full-link")
            or await card.query_selector("a[href*='/jobs/view/']")
            or await card.query_selector("a.job-card-list__title")
            or await card.query_selector("a[data-tracking-control-name*='job']")
        )
        if not link_el:
            return None

        url = await link_el.get_attribute("href") or ""
        # Handle both /jobs/view/1234567890 and /jobs/view/title-slug-1234567890
        match = re.search(r"(\d{7,})", url)
        if not match:
            return None
        job_id = match.group(1)

        # Title
        title_el = (
            await card.query_selector("h3.base-search-card__title")
            or await card.query_selector("h3[class*='title']")
            or await card.query_selector("span.sr-only")
            or link_el  # fallback: use link text
        )
        title = clean_text(await title_el.inner_text()) if title_el else ""
        if not title:
            # Try aria-label on the link
            title = (await link_el.get_attribute("aria-label") or "").strip()
        if not title:
            return None

        # Company
        company_el = (
            await card.query_selector("h4.base-search-card__subtitle")
            or await card.query_selector("h4[class*='subtitle']")
            or await card.query_selector("a.hidden-nested-link")
            or await card.query_selector("[class*='company']")
        )
        company = clean_text(await company_el.inner_text()) if company_el else "Unknown"

        # Location
        location_el = (
            await card.query_selector("span.job-search-card__location")
            or await card.query_selector("span[class*='location']")
        )
        location = clean_text(await location_el.inner_text()) if location_el else ""
        country = location.split(",")[-1].strip() if "," in location else location

        return Job(
            id=build_job_id(self.PORTAL, job_id),
            portal=self.PORTAL,
            title=title,
            company=company,
            location=location,
            country=country,
            url=url,
            description="",
            visa_sponsorship=True,
        )
