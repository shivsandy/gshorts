import os
from pathlib import Path
import pytest
from shorts_factory.config import ConfigurationError, Settings

ENV_KEYS=["CONTENT_NICHE","VIDEO_LANGUAGE","TIMEZONE","UPLOAD_PRIVACY","DAILY_UPLOAD_ENABLED","ALLOW_PUBLIC_UPLOADS","DRY_RUN","YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN","TTS_VOICE","OUTPUT_DIR"]

def clear_env(monkeypatch):
    for key in ENV_KEYS: monkeypatch.delenv(key,raising=False)

def test_defaults_are_safe_and_unlisted(monkeypatch):
    clear_env(monkeypatch)
    s=Settings.from_env()
    assert s.upload_privacy=="unlisted"
    assert s.daily_upload_enabled is False
    assert s.dry_run is True

def test_public_upload_requires_explicit_second_switch(monkeypatch):
    clear_env(monkeypatch); monkeypatch.setenv("UPLOAD_PRIVACY","public")
    with pytest.raises(ConfigurationError,match="ALLOW_PUBLIC_UPLOADS"):
        Settings.from_env()

def test_upload_enabled_without_secrets_fails_only_when_not_dry_run(monkeypatch):
    clear_env(monkeypatch); monkeypatch.setenv("DAILY_UPLOAD_ENABLED","true")
    assert Settings.from_env().dry_run is True
    monkeypatch.setenv("DRY_RUN","false")
    with pytest.raises(ConfigurationError,match="GitHub Secrets"):
        Settings.from_env()

def test_force_dry_run_wins_over_env(monkeypatch):
    clear_env(monkeypatch); monkeypatch.setenv("DRY_RUN","false")
    assert Settings.from_env(force_dry_run=True).dry_run is True
