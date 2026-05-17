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


async def _manual_login(portal: str, session_path: str):
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
def login(portal):
    """Manually log into a portal and save the session for bot reuse."""
    session_path = f"data/sessions/{portal}_session.json"
    Path("data/sessions").mkdir(parents=True, exist_ok=True)
    print(f"\nOpening {portal.title()} login page...")
    asyncio.run(_manual_login(portal, session_path))


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
