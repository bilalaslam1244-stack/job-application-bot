import asyncio
import click
from src.config import load_config, ConfigError
from src.tracker import Tracker
from src.runner import Runner


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
