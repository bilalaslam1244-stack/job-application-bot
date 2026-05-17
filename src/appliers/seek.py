import asyncio
import re
from playwright.async_api import async_playwright, Page
from src.scrapers.base import BaseScraper, clean_text
from src.tracker import Job, Tracker

PROFILE = {
    "phone":      "+60132216309",
    "first_name": "Bilal",
    "last_name":  "Aslam",
    "email":      "b.aslamkl01@gmail.com",
}


class SeekApplier(BaseScraper):
    PORTAL = "seek"

    def __init__(self, email: str, password: str, resume_path: str):
        super().__init__(email, password)
        self._resume_path = resume_path

    async def apply(self, job: Job, cover_letter: str, tracker: Tracker) -> str:
        """
        Returns: 'applied' | 'manual_required' | 'failed'
        """
        async with async_playwright() as p:
            await self._setup_context(p)
            page = await self._new_stealth_page()
            try:
                result = await self._do_apply(page, job, cover_letter)
                if result == "applied":
                    tracker.update_status(job.id, "applied", cover_letter)
                await self.close()
                return result
            except Exception as e:
                await self.close()
                print(f"  Seek apply error: {e}")
                return "failed"

    async def _do_apply(self, page: Page, job: Job, cover_letter: str) -> str:
        await page.goto(job.url, wait_until="domcontentloaded")
        await self._random_delay(2, 3)

        # Look for Seek native Quick Apply button
        apply_btn = (
            await page.query_selector("a[data-automation='job-detail-apply']")
            or await page.query_selector("button[data-automation='job-detail-apply']")
            or await page.query_selector("a[href*='/apply/']")
        )
        if not apply_btn:
            return "manual_required"

        href = await apply_btn.get_attribute("href") or ""

        # If apply button goes to external site — manual required
        if href and not ("seek.com.au" in href or href.startswith("/")):
            return "manual_required"

        await apply_btn.click()
        await self._random_delay(2, 3)

        # Check if redirected off Seek
        if "seek.com.au" not in page.url:
            return "manual_required"

        # Seek native apply flow — walk through steps
        for _ in range(8):
            await self._fill_step(page, cover_letter)
            await self._random_delay(1, 2)

            # Submit button
            submit = (
                await page.query_selector("button[data-automation='seek-apply-submit']")
                or await page.query_selector("button[type='submit']")
            )
            if submit:
                text = (await submit.inner_text()).lower()
                if any(w in text for w in ["submit", "send", "apply"]):
                    await submit.click()
                    await self._random_delay(2, 3)
                    # Confirm success by checking URL or success message
                    if "confirmation" in page.url or "success" in page.url:
                        return "applied"
                    success_el = await page.query_selector("[data-automation='application-success']")
                    if success_el:
                        return "applied"
                    return "applied"  # assume success if no error shown

            # Next step
            next_btn = await page.query_selector("button[data-automation='next-button']")
            if next_btn:
                await next_btn.click()
                await self._random_delay(1, 2)
            else:
                break

        return "failed"

    async def _fill_step(self, page: Page, cover_letter: str):
        from pathlib import Path

        fields = {
            "input[name='firstName']":  PROFILE["first_name"],
            "input[name='lastName']":   PROFILE["last_name"],
            "input[name='email']":      PROFILE["email"],
            "input[name='phoneNumber']": PROFILE["phone"],
            "input[type='tel']":        PROFILE["phone"],
        }
        for sel, val in fields.items():
            try:
                el = await page.query_selector(sel)
                if el and not await el.input_value():
                    await el.fill(val)
            except Exception:
                pass

        # Cover letter
        for sel in ["textarea[name='coverLetter']", "textarea[placeholder*='cover']", "textarea"]:
            try:
                el = await page.query_selector(sel)
                if el and not await el.input_value():
                    await el.fill(cover_letter[:2000])
                    break
            except Exception:
                pass

        # Resume upload
        resume = Path(self._resume_path)
        if resume.exists():
            for sel in ["input[type='file']", "input[accept*='pdf']"]:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        await el.set_input_files(str(resume))
                        break
                except Exception:
                    pass
