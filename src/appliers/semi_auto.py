import asyncio
from playwright.async_api import async_playwright, Page
from src.scrapers.base import BaseScraper
from src.tracker import Job, Tracker


class SemiAutoApplier(BaseScraper):
    """Opens visible browser, fills fields, waits for user to click Submit."""

    def __init__(self, portal: str, email: str, password: str):
        super().__init__(email, password)
        self.PORTAL = portal

    async def apply(self, job: Job, cover_letter: str, tracker: Tracker) -> bool:
        async with async_playwright() as p:
            self._browser = await p.chromium.launch(headless=False)
            kwargs = {"viewport": {"width": 1280, "height": 900}}
            if self._session_file.exists():
                kwargs["storage_state"] = str(self._session_file)
            self._context = await self._browser.new_context(**kwargs)
            page = await self._context.new_page()

            try:
                await page.goto(job.url)
                await asyncio.sleep(2)
                await self._fill_fields(page, cover_letter)

                print(f"\n{'='*60}")
                print(f"[MANUAL APPLY] {job.title} at {job.company}")
                print(f"URL: {job.url}")
                print("Form pre-filled. Review, make any changes, then SUBMIT.")
                print(f"{'='*60}")
                response = input("Did you submit? (yes/skip): ").strip().lower()

                if response == "yes":
                    tracker.update_status(job.id, "applied", cover_letter)
                    await self.close()
                    return True
                await self.close()
                return False
            except Exception:
                await self.close()
                raise

    async def _fill_fields(self, page: Page, cover_letter: str):
        await asyncio.sleep(2)
        field_map = {
            "textarea[name*='cover'], div[aria-label*='cover'] textarea": cover_letter,
            "input[name*='phone'], input[placeholder*='phone'], input[type='tel']": "+60132216309",
            "input[name*='first'], input[placeholder*='first name']": "Bilal",
            "input[name*='last'], input[placeholder*='last name']": "Aslam",
        }
        for selector, value in field_map.items():
            try:
                el = await page.query_selector(selector)
                if el:
                    current = await el.input_value()
                    if not current:
                        await el.fill(value)
            except Exception:
                continue
