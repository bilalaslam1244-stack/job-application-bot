import asyncio
import random
from src.config import Config
from src.tracker import Tracker, Job
from src.notifier import Notifier
from src.cover_letter import CoverLetterGenerator
from src.scrapers.linkedin import LinkedInScraper
from src.scrapers.indeed import IndeedScraper
from src.scrapers.seek import SeekScraper
from src.scrapers.reed import ReedScraper
from src.scrapers.stepstone import StepStoneScraper
from src.appliers.indeed import IndeedApplier
from src.appliers.semi_auto import SemiAutoApplier
from src.status_checker.linkedin import LinkedInStatusChecker
from src.status_checker.indeed import IndeedStatusChecker


class Runner:
    def __init__(self, config: Config):
        self.cfg = config
        self.tracker = Tracker()
        self.tracker.init_db()
        self.notifier = Notifier(config.telegram_bot_token, config.telegram_chat_id)
        resume_text = CoverLetterGenerator.load_resume(config.resume_path)
        self.cover_gen = CoverLetterGenerator(config.anthropic_api_key, resume_text)

    async def run_search(self) -> list[Job]:
        cfg = self.cfg
        countries = cfg.search.all_countries()
        roles = cfg.search.roles
        limit = cfg.search.max_jobs_per_run
        all_jobs: list[Job] = []

        # Limit combinations per run — too many = timeout
        # Rotate through roles/countries across runs so everything gets covered over time
        import hashlib, datetime
        day_seed = int(datetime.date.today().strftime("%j"))
        active_roles = roles[day_seed % max(1, len(roles)):][:2] + roles[:day_seed % max(1, len(roles))]
        active_roles = list(dict.fromkeys(active_roles))[:3]
        tier1 = cfg.search.tier1[:3]

        scrapers = [
            ("linkedin",  lambda p: LinkedInScraper(p.email, p.password).search_jobs(active_roles, tier1, 20)),
            ("indeed",    lambda p: IndeedScraper(p.email, p.password).search_jobs(active_roles, tier1, 20)),
            ("seek",      lambda p: SeekScraper(p.email, p.password).search_jobs(active_roles, 20)),
            ("reed",      lambda p: ReedScraper(p.email, p.password).search_jobs(active_roles, 20)),
            ("stepstone", lambda p: StepStoneScraper(p.email, p.password).search_jobs(active_roles, 20)),
        ]
        print(f"Roles this run: {active_roles}")
        print(f"Countries this run: {tier1}")

        for portal_name, scrape_fn in scrapers:
            portal = cfg.portals[portal_name]
            if not portal.enabled:
                print(f"[{portal_name}] skipped (disabled)")
                continue
            print(f"[{portal_name}] searching...", flush=True)
            try:
                jobs = await asyncio.wait_for(scrape_fn(portal), timeout=300)
                print(f"[{portal_name}] {len(jobs)} results found")
                all_jobs.extend(jobs)
            except asyncio.TimeoutError:
                print(f"[{portal_name}] timed out — skipping")
            except Exception as e:
                print(f"[{portal_name}] ERROR: {e}")

        from src.scrapers.base import is_relevant_title
        new_jobs = []
        skipped = 0
        for job in all_jobs:
            if not is_relevant_title(job.title):
                skipped += 1
                continue
            if not self.tracker.get_job(job.id):
                self.tracker.insert_job(job)
                await self.notifier.notify_new_job(job)
                new_jobs.append(job)
                print(f"  + {job.title} | {job.company} | {job.location}")
        if skipped:
            print(f"  (filtered out {skipped} irrelevant titles)")

        print(f"\nSearch complete. {len(new_jobs)} new jobs saved.")
        return new_jobs

    async def run_apply(self):
        cfg = self.cfg
        rl = cfg.rate_limits
        applied_counts: dict[str, int] = {k: 0 for k in cfg.portals}

        for job in self.tracker.get_unapplied_jobs():
            max_today = rl.max_applications_per_day.get(job.portal, 0)

            if max_today == 0:
                # LinkedIn — open in browser for manual apply
                import webbrowser
                print(f"\n[LINKEDIN — MANUAL] {job.title} at {job.company}\n{job.url}")
                webbrowser.open(job.url)
                continue

            if applied_counts.get(job.portal, 0) >= max_today:
                continue

            letter = self.cover_gen.generate_with_fallback(job)
            self.cover_gen.save(job, letter)

            try:
                if job.portal == "indeed":
                    p = cfg.portals["indeed"]
                    success = await IndeedApplier(p.email, p.password, cfg.resume_path).apply(job, letter, self.tracker)
                else:
                    p = cfg.portals[job.portal]
                    success = await SemiAutoApplier(job.portal, p.email, p.password).apply(job, letter, self.tracker)

                if success:
                    applied_counts[job.portal] = applied_counts.get(job.portal, 0) + 1
                    await self.notifier.notify_applied(job, letter[:200])
                    print(f"Applied: {job.title} at {job.company} ({job.portal})")

            except Exception as e:
                print(f"Apply failed {job.id}: {e}")
                await self.notifier.notify_error(job.portal, str(e))

            delay = rl.delay_between_applications_seconds + random.uniform(0, rl.delay_randomisation_seconds)
            await asyncio.sleep(delay)

    async def run_check(self):
        cfg = self.cfg

        if cfg.portals["linkedin"].enabled:
            p = cfg.portals["linkedin"]
            await LinkedInStatusChecker(p.email, p.password).check_all(self.tracker)

        if cfg.portals["indeed"].enabled:
            p = cfg.portals["indeed"]
            await IndeedStatusChecker(p.email, p.password).check_all(self.tracker)

        events = self.tracker.get_unnotified_events()
        notified = []
        for event in events:
            job = self.tracker.get_job(event.job_id)
            if job:
                await self.notifier.notify_status_change(job, event)
                notified.append(event.id)
        if notified:
            self.tracker.mark_events_notified(notified)

        print(f"Status check complete. {len(events)} event(s) processed.")

    async def run_full(self):
        await self.run_search()
        await self.run_apply()
        await self.run_check()

    def close(self):
        self.tracker.close()
