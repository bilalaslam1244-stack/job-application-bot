import asyncio
import random
from playwright.async_api import async_playwright, Page
from src.scrapers.base import BaseScraper, clean_text
from src.tracker import Job, Tracker

PROFILE = {
    "phone": "+60132216309",
    "first_name": "Bilal",
    "last_name": "Aslam",
    "location": "Johor Bahru, Malaysia",
}


class IndeedApplier(BaseScraper):
    PORTAL = "indeed"

    def __init__(self, email: str, password: str, resume_path: str):
        super().__init__(email, password)
        self._resume_path = resume_path

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
            except Exception:
                await self.close()
                raise

    async def _do_apply(self, page: Page, job: Job, cover_letter: str) -> bool:
        await page.goto(job.url)
        await self._random_delay(2, 4)

        # Fetch description if empty
        if not job.description:
            desc_el = await page.query_selector("div#jobDescriptionText")
            if desc_el:
                job.description = clean_text(await desc_el.inner_text())

        apply_btn = await page.query_selector("button[id='indeedApplyButton']")
        if not apply_btn:
            return False

        await apply_btn.click()
        await self._random_delay(2, 3)

        for _ in range(10):
            await self._fill_current_step(page, cover_letter)
            await self._random_delay(1, 2)

            submit_btn = await page.query_selector("button[data-testid='ia-continueButton']")
            next_btn = await page.query_selector("button[data-testid='continue-button']")

            if submit_btn and "submit" in (await submit_btn.inner_text()).lower():
                await submit_btn.click()
                await self._random_delay(2, 3)
                return True
            elif next_btn:
                await next_btn.click()
                await self._random_delay(1, 2)
            elif submit_btn:
                await submit_btn.click()
                await self._random_delay(2, 3)
                return True
            else:
                break

        return False

    async def _fill_current_step(self, page: Page, cover_letter: str):
        for selector, value in [
            ("textarea[name='coverletter']", cover_letter),
            ("input[name='phoneNumber']", PROFILE["phone"]),
        ]:
            try:
                el = await page.query_selector(selector)
                if el and not await el.input_value():
                    await el.fill(value)
            except Exception:
                pass

        for sel in await page.query_selector_all("select[name*='experience']"):
            try:
                opts = await sel.evaluate("el => [...el.options].map(o => o.value)")
                await sel.select_option("1" if "1" in opts else opts[0] if opts else "")
            except Exception:
                pass
