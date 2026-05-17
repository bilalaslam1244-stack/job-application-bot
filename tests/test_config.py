import pytest
import yaml
from src.config import load_config, ConfigError, Config

VALID_CONFIG = {
    "resume_path": "Bilal_Aslam_Resume_v2.html",
    "anthropic_api_key": "sk-ant-test",
    "telegram_bot_token": "123456:ABC-test",
    "telegram_chat_id": "987654321",
    "search": {
        "roles": ["Sales Engineer"],
        "keywords": ["visa sponsorship"],
        "priority_regions": {
            "tier1": ["UAE", "Australia"],
            "tier2": ["Netherlands"],
            "tier3": ["Singapore"],
            "tier4": ["USA"],
        },
        "exclude_countries": ["India"],
        "max_jobs_per_run": 100,
    },
    "portals": {
        "linkedin": {"email": "t@t.com", "password": "pass", "enabled": True},
        "indeed": {"email": "t@t.com", "password": "pass", "enabled": True},
        "seek": {"email": "t@t.com", "password": "pass", "enabled": False},
        "reed": {"email": "t@t.com", "password": "pass", "enabled": False},
        "stepstone": {"email": "t@t.com", "password": "pass", "enabled": False},
    },
    "rate_limits": {
        "delay_between_applications_seconds": 30,
        "delay_randomisation_seconds": 15,
        "max_applications_per_day": {"linkedin": 0, "indeed": 30, "seek": 20, "reed": 15, "stepstone": 15},
        "status_check_interval_hours": 4,
    },
}


def test_load_valid_config(tmp_path):
    f = tmp_path / "config.yaml"
    f.write_text(yaml.dump(VALID_CONFIG))
    cfg = load_config(str(f))
    assert isinstance(cfg, Config)
    assert cfg.anthropic_api_key == "sk-ant-test"
    assert "UAE" in cfg.search.tier1
    assert cfg.portals["linkedin"].enabled is True


def test_missing_field_raises(tmp_path):
    bad = dict(VALID_CONFIG)
    del bad["anthropic_api_key"]
    f = tmp_path / "config.yaml"
    f.write_text(yaml.dump(bad))
    with pytest.raises(ConfigError, match="anthropic_api_key"):
        load_config(str(f))


def test_file_not_found():
    with pytest.raises(ConfigError, match="not found"):
        load_config("nonexistent.yaml")


def test_all_countries_excludes_india(tmp_path):
    f = tmp_path / "config.yaml"
    f.write_text(yaml.dump(VALID_CONFIG))
    cfg = load_config(str(f))
    assert "India" not in cfg.search.all_countries()
    assert "UAE" in cfg.search.all_countries()
