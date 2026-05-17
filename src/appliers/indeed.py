import asyncio
import random
from pathlib import Path
from playwright.async_api import async_playwright, Page
from src.scrapers.base import BaseScraper, clean_text
from src.tracker import Job, Tracker

PROFILE = {
    "phone":      "+60132216309",
    "first_name": "Bilal",
    "last_name":  "Aslam",
    "email":      "b.aslamkl01@gmail.com",
    "location":   "Johor Bahru, Malaysia",
}


class IndeedApplier(BaseScraper):
    PORTAL = "indeed"

    def __init__(self, email: str, password: str, resume_path: str):
        super().__init__(email, password)
        self._resume_path = resume_path

    async def apply(self, job: Job, cover_letter: str, tracker: Tracker) -> bool:
        async with async_playwright() as p:
            # No saved session — guest apply, fresh context every time
            self._browser = await p.chromium.launch(headless=True)
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await self._context.new_page()
            try:
                success = await self._do_apply(page, job, cover_letter)
                if success:
                    tracker.update_status(job.id, "applied", cover_letter)
                await self._browser.close()
                return success
            except Exception:
                await self._browser.close()
                raise

    async def _do_apply(self, page: Page, job: Job, cover_letter: str) -> bool:
        await page.goto(job.url)
        await self._random_delay(2, 4)

        # Fetch description if empty
        if not job.description:
            desc_el = await page.query_selector("div#jobDescriptionText")
            if desc_el:
                job.description = clean_text(await desc_el.inner_text())

        # Click Easily Apply / Apply Now
        apply_btn = (
            await page.query_selector("button[id='indeedApplyButton']")
            or await page.query_selector("button.ia-IndeedApplyButton")
        )
        if not apply_btn:
            return False

        await apply_btn.click()
        await self._random_delay(2, 3)

        # Indeed may show sign-in prompt — dismiss it and continue as guest
        for guest_selector in [
            "button[data-testid='continue-without-account']",
            "a[data-testid='skip-sign-in']",
            "button:has-text('Continue')",
            "span:has-text('Continue without an account')",
        ]:
            try:
                btn = await page.query_selector(guest_selector)
                if btn:
                    await btn.click()
                    await self._random_delay(1, 2)
                    break
            except Exception:
                pass

        # Walk through multi-step form
        for _ in range(12):
            await self._fill_current_step(page, cover_letter)
            await self._random_delay(1, 2)

            # Check for final submit
            for submit_sel in [
                "button[data-testid='ia-continueButton']",
                "button[aria-label='Submit your application']",
                "button:has-text('Submit')",
            ]:
                btn = await page.query_selector(submit_sel)
                if btn:
                    text = (await btn.inner_text()).lower()
                    if "submit" in text:
                        await btn.click()
                        await self._random_delay(2, 3)
                        return True

            # Next step
            next_btn = (
                await page.query_selector("button[data-testid='continue-button']")
                or await page.query_selector("button[data-testid='ia-continueButton']")
            )
            if next_btn:
                await next_btn.click()
                await self._random_delay(1, 2)
            else:
                break

        return False

    async def _fill_current_step(self, page: Page, cover_letter: str):
        fields = {
            "input[name='firstName'], input[autocomplete='given-name']":   PROFILE["first_name"],
            "input[name='lastName'],  input[autocomplete='family-name']":   PROFILE["last_name"],
            "input[name='email'],     input[type='email']":                 PROFILE["email"],
            "input[name='phoneNumber'], input[type='tel']":                 PROFILE["phone"],
            "textarea[name='coverletter'], textarea[id*='cover']":          cover_letter,
        }
        for selector, value in fields.items():
            for sel in selector.split(","):
                try:
                    el = await page.query_selector(sel.strip())
                    if el and not (await el.input_value()):
                        await el.fill(value)
                        break
                except Exception:
                    pass

        # Resume upload
        resume = Path(self._resume_path)
        if resume.exists():
            for upload_sel in ["input[type='file']", "input[name='resume']"]:
                try:
                    el = await page.query_selector(upload_sel)
                    if el:
                        await el.set_input_files(str(resume))
                        break
                except Exception:
                    pass

        # Experience dropdowns — pick "1 year"
        for sel in await page.query_selector_all("select[name*='experience'], select[id*='experience']"):
            try:
                opts = await sel.evaluate("el => [...el.options].map(o => o.value)")
                await sel.select_option("1" if "1" in opts else (opts[0] if opts else ""))
            except Exception:
                pass

        # Yes/No questions — answer Yes to sponsorship/relocation
        for radio in await page.query_selector_all("input[type='radio'][value='yes'], input[type='radio'][value='Yes']"):
            try:
                label = await radio.evaluate("el => el.closest('label')?.innerText || el.labels?.[0]?.innerText || ''")
                if any(kw in label.lower() for kw in ["sponsor", "reloc", "authoris", "authoriz"]):
                    await radio.click()
            except Exception:
                pass
