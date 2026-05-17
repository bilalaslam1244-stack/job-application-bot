import re
from typing import Optional
from playwright.async_api import async_playwright
from src.scrapers.base import BaseScraper, has_visa_sponsorship, build_job_id, clean_text
from src.tracker import Job


class LinkedInScraper(BaseScraper):
    PORTAL = "linkedin"
    BASE_URL = "https://www.linkedin.com"

    async def search_jobs(self, roles: list[str], countries: list[str], max_jobs: int = 100) -> list[Job]:
        jobs = []
        async with async_playwright() as p:
            await self._setup_context(p)
            per_combo = max(1, max_jobs // (len(roles) * min(len(countries), 8)))
            for role in roles:
                for country in countries[:8]:
                    batch = await self._search_one(role, country, per_combo)
                    jobs.extend(batch)
                    if len(jobs) >= max_jobs:
                        break
                if len(jobs) >= max_jobs:
                    break
            await self.close()
        return jobs[:max_jobs]

    async def _search_one(self, role: str, country: str, limit: int) -> list[Job]:
        page = await self._new_stealth_page()
        query = f"{role} visa sponsorship".replace(" ", "%20")
        location = country.replace(" ", "%20")
        url = f"{self.BASE_URL}/jobs/search/?keywords={query}&location={location}&f_WT=2&sortBy=DD"
        await page.goto(url)
        await self._random_delay(2, 4)

        jobs = []
        cards = await page.query_selector_all("div.job-search-card")
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
        match = re.search(r"/jobs/view/(\d+)", url or "")
        if not match:
            return None

        # Fetch description
        desc_page = await self._new_stealth_page()
        description = ""
        try:
            await desc_page.goto(url)
            await self._random_delay(1.5, 3)
            desc_el = await desc_page.query_selector("div.show-more-less-html__markup")
            description = clean_text(await desc_el.inner_text()) if desc_el else ""
        except Exception:
            pass
        finally:
            await desc_page.close()

        country = location.split(",")[-1].strip() if "," in location else location

        return Job(
            id=build_job_id(self.PORTAL, match.group(1)),
            portal=self.PORTAL,
            title=title,
            company=company,
            location=location,
            country=country,
            url=url,
            description=description,
            visa_sponsorship=has_visa_sponsorship(title + " " + description),
        )
