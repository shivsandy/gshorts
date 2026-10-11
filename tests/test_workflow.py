from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]

def test_workflow_has_schedule_manual_dispatch_serialization_and_secret_refs():
    raw=(ROOT/".github/workflows/daily-shorts.yml").read_text(encoding="utf-8")
    data=yaml.safe_load(raw)
    assert "schedule:" in raw and "workflow_dispatch:" in raw
    assert data["concurrency"]["cancel-in-progress"] is False
    assert data["jobs"]["create-and-publish"]["timeout-minutes"]<=30
    assert "secrets.YOUTUBE_REFRESH_TOKEN" in raw
    assert "cron: \"17 3 * * *\"" in raw
