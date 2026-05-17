from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml


class ConfigError(Exception):
    pass


@dataclass
class PortalConfig:
    email: str
    password: str
    enabled: bool


@dataclass
class SearchConfig:
    roles: list[str]
    keywords: list[str]
    tier1: list[str]
    tier2: list[str]
    tier3: list[str]
    tier4: list[str]
    exclude_countries: list[str]
    max_jobs_per_run: int

    def all_countries(self) -> list[str]:
        all_c = self.tier1 + self.tier2 + self.tier3 + self.tier4
        return [c for c in all_c if c not in self.exclude_countries]


@dataclass
class RateLimits:
    delay_between_applications_seconds: int
    delay_randomisation_seconds: int
    max_applications_per_day: dict[str, int]
    status_check_interval_hours: int


@dataclass
class Config:
    resume_path: str
    anthropic_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    search: SearchConfig
    portals: dict[str, PortalConfig]
    rate_limits: RateLimits


def load_config(path: str = "config.yaml") -> Config:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Config file not found: {path}")

    with p.open() as f:
        raw = yaml.safe_load(f)

    for key in ["anthropic_api_key", "telegram_bot_token", "telegram_chat_id", "resume_path"]:
        if key not in raw:
            raise ConfigError(f"Missing required config field: {key}")

    regions = raw["search"]["priority_regions"]
    search = SearchConfig(
        roles=raw["search"]["roles"],
        keywords=raw["search"]["keywords"],
        tier1=regions.get("tier1", []),
        tier2=regions.get("tier2", []),
        tier3=regions.get("tier3", []),
        tier4=regions.get("tier4", []),
        exclude_countries=raw["search"].get("exclude_countries", []),
        max_jobs_per_run=raw["search"].get("max_jobs_per_run", 100),
    )

    portals = {name: PortalConfig(**vals) for name, vals in raw["portals"].items()}

    rl = raw["rate_limits"]
    rate_limits = RateLimits(
        delay_between_applications_seconds=rl["delay_between_applications_seconds"],
        delay_randomisation_seconds=rl["delay_randomisation_seconds"],
        max_applications_per_day=rl["max_applications_per_day"],
        status_check_interval_hours=rl["status_check_interval_hours"],
    )

    return Config(
        resume_path=raw["resume_path"],
        anthropic_api_key=raw["anthropic_api_key"],
        telegram_bot_token=raw["telegram_bot_token"],
        telegram_chat_id=raw["telegram_chat_id"],
        search=search,
        portals=portals,
        rate_limits=rate_limits,
    )
