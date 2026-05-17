import re
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
                    link_el = await row.query_selector("a[data-testid='jobTitle']")
                    status_el = await row.query_selector("span[data-testid='applicationStatus']")
                    if not link_el:
                        continue

                    href = await link_el.get_attribute("href") or ""
                    match = re.search(r"jk=([a-z0-9]+)", href)
                    if not match:
                        continue

                    job = tracker.get_job(f"indeed:{match.group(1)}")
                    if not job or not status_el:
                        continue

                    raw = clean_text(await status_el.inner_text())
                    if record_status_change(tracker, job, raw):
                        changes.append({"job_id": job.id, "new_status": raw})
                except Exception:
                    continue

            await self.close()
        return changes
