import asyncio
import click
from pathlib import Path
from src.config import load_config, ConfigError
from src.tracker import Tracker
from src.runner import Runner

LOGIN_URLS = {
    "linkedin":  "https://www.linkedin.com/login",
    "indeed":    "https://secure.indeed.com/auth",
    "seek":      "https://www.seek.com.au/oauth/login",
    "reed":      "https://www.reed.co.uk/login",
    "stepstone": "https://www.stepstone.de/en/login",
}


def _find_brave() -> str | None:
    import os
    candidates = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ]
    return next((p for p in candidates if Path(p).exists()), None)


async def _manual_login(portal: str, session_path: str, apply_stealth: bool = True):
    from playwright.async_api import async_playwright
    from playwright_stealth import stealth_async

    brave_path = _find_brave()
    if brave_path:
        print(f"Using Brave browser at: {brave_path}")
    else:
        print("Brave not found — using built-in Chromium.")

    async with async_playwright() as p:
        launch_kwargs = {"headless": False}
        if brave_path:
            launch_kwargs["executable_path"] = brave_path
        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()
        if apply_stealth:
            await stealth_async(page)
        await page.goto(LOGIN_URLS[portal])

        print(f"\nBrowser open for {portal.title()}.")
        print("Log in normally (enter your email, check for the code, submit).")
        input("Press ENTER here once you are fully logged in and can see your dashboard: ")

        await context.storage_state(path=session_path)
        await browser.close()
        print(f"Session saved. Bot will reuse this login automatically.")


@click.group()
def cli():
    pass


@cli.command()
def config():
    """Validate config.yaml and show summary."""
    try:
        cfg = load_config()
        click.echo("Config valid.")
        click.echo(f"  Resume:   {cfg.resume_path}")
        click.echo(f"  Portals:  {[k for k, v in cfg.portals.items() if v.enabled]}")
        click.echo(f"  Regions:  {len(cfg.search.all_countries())} countries")
        click.echo(f"  Max jobs: {cfg.search.max_jobs_per_run}/run")
    except ConfigError as e:
        click.echo(f"Config error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
def status():
    """Show application dashboard."""
    tracker = Tracker()
    tracker.init_db()
    stats = tracker.get_stats()
    tracker.close()

    click.echo("\nApplication Status\n" + "-" * 30)
    labels = {
        "found": "Found (not yet applied)",
        "applied": "Applied",
        "viewed": "Viewed by employer",
        "in_review": "In Review",
        "interview": "Interview",
        "rejected": "Rejected",
        "skipped": "Skipped",
    }
    for key, label in labels.items():
        count = stats.get(key, 0)
        if count:
            click.echo(f"  {label}: {count}")
    click.echo("-" * 30)
    click.echo(f"  Total: {sum(stats.values())}\n")


@cli.command()
@click.argument("portal", type=click.Choice(["linkedin", "indeed", "seek", "reed", "stepstone"]))
def debug(portal):
    """Test a single portal scraper and print raw results."""
    import traceback
    from src.config import load_config
    from src.scrapers.linkedin import LinkedInScraper
    from src.scrapers.indeed import IndeedScraper
    from src.scrapers.seek import SeekScraper
    from src.scrapers.reed import ReedScraper
    from src.scrapers.stepstone import StepStoneScraper

    cfg = load_config()
    p = cfg.portals[portal]
    roles = cfg.search.roles[:1]       # just first role
    countries = cfg.search.tier1[:2]   # just first 2 countries

    scrapers = {
        "linkedin":  lambda: LinkedInScraper(p.email, p.password).search_jobs(roles, countries, 3),
        "indeed":    lambda: IndeedScraper(p.email, p.password).search_jobs(roles, countries, 3),
        "seek":      lambda: SeekScraper(p.email, p.password).search_jobs(roles, 3),
        "reed":      lambda: ReedScraper(p.email, p.password).search_jobs(roles, 3),
        "stepstone": lambda: StepStoneScraper(p.email, p.password).search_jobs(roles, 3),
    }

    async def _debug_scrape():
        from playwright.async_api import async_playwright
        from playwright_stealth import stealth_async
        from pathlib import Path

        SEARCH_URLS = {
            "linkedin":  f"https://www.linkedin.com/jobs/search/?keywords=Sales+Engineer&location=Dubai&sortBy=DD",
            "indeed":    f"https://au.indeed.com/jobs?q=Sales+Engineer&l=Australia&sort=date",
            "seek":      "https://www.seek.com.au/sales-engineer-jobs?sortmode=ListedDate",
            "reed":      "https://www.reed.co.uk/jobs/sales-engineer-jobs?sortby=displaydate",
            "stepstone": "https://www.stepstone.de/jobs/Sales+Engineer?sort=2",
        }

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await stealth_async(page)

            url = SEARCH_URLS[portal]
            print(f"Loading: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            title = await page.title()
            final_url = page.url
            print(f"Page title : {title}")
            print(f"Final URL  : {final_url}")

            # Take screenshot
            shot_path = f"debug_{portal}.png"
            await page.screenshot(path=shot_path, full_page=False)
            print(f"Screenshot : {shot_path}  (open this file to see what the browser loaded)")

            # Count key elements
            counts = {}
            selectors = {
                "linkedin":  ["div.job-search-card", "ul.jobs-search__results-list li", "div[data-job-id]"],
                "indeed":    ["div.job_seen_beacon", "div.resultContent", "div[class*='job_']"],
                "seek":      ["article[data-testid='job-card']", "article[class*='job']", "div[data-automation='jobListing']"],
                "reed":      ["article.job-result", "div.job-result", "article[data-jobid]"],
                "stepstone": ["article.sc-beqWAB", "article[data-genesis-element='BASE_RESULT_ITEM']", "div[class*='ResultItem']"],
            }
            for sel in selectors[portal]:
                els = await page.query_selector_all(sel)
                counts[sel] = len(els)
                print(f"  selector '{sel}' matched: {len(els)}")

            await browser.close()

    asyncio.run(_debug_scrape())

    # Also run the actual scraper to verify end-to-end
    print("\nRunning actual scraper (3 jobs max)...")
    try:
        jobs = asyncio.run(scrapers[portal]())
        if jobs:
            for j in jobs:
                print(f"  PARSED: {j.title} | {j.company} | {j.location}")
        else:
            print("  Scraper returned 0 jobs — _parse_card failing on all cards")
    except Exception as e:
        print(f"  Scraper exception: {e}")
        traceback.print_exc()


@cli.command()
@click.argument("portal", type=click.Choice(["linkedin", "indeed", "seek", "reed", "stepstone"]))
@click.option("--no-stealth", is_flag=True, default=False, help="Disable stealth mode (try if page shows white screen)")
def login(portal, no_stealth):
    """Manually log into a portal and save the session for bot reuse."""
    session_path = f"data/sessions/{portal}_session.json"
    Path("data/sessions").mkdir(parents=True, exist_ok=True)
    print(f"\nOpening {portal.title()} login page...")
    asyncio.run(_manual_login(portal, session_path, apply_stealth=not no_stealth))


@cli.command()
def search():
    """Search for jobs without applying."""
    cfg = load_config()
    runner = Runner(cfg)
    try:
        asyncio.run(runner.run_search())
    finally:
        runner.close()


@cli.command()
def apply():
    """Apply to all unapplied jobs in DB."""
    cfg = load_config()
    runner = Runner(cfg)
    try:
        asyncio.run(runner.run_apply())
    finally:
        runner.close()


@cli.command()
def check():
    """Check application statuses on all portals."""
    cfg = load_config()
    runner = Runner(cfg)
    try:
        asyncio.run(runner.run_check())
    finally:
        runner.close()


@cli.command()
def run():
    """Full cycle: search + apply + check."""
    cfg = load_config()
    runner = Runner(cfg)
    try:
        asyncio.run(runner.run_full())
    finally:
        runner.close()


if __name__ == "__main__":
    cli()
