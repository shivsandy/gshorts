from __future__ import annotations
import json, os, shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

class ConfigurationError(RuntimeError):
    """Unsafe or invalid settings."""

def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip(): return default
    if value.strip().lower() in {"1","true","yes","on"}: return True
    if value.strip().lower() in {"0","false","no","off"}: return False
    raise ConfigurationError(f"{name} must be true or false.")

def intval(mapping: dict[str, Any], name: str, default: int) -> int:
    try: return int(mapping.get(name, default))
    except (TypeError, ValueError) as exc: raise ConfigurationError(f"Setting {name} must be an integer.") from exc

@dataclass(frozen=True)
class Settings:
    root: Path; topic_file: Path; history_file: Path; analytics_file: Path; output_dir: Path
    content_niche: str; video_language: str; timezone: str; upload_privacy: str; max_topic_attempts: int
    daily_upload_enabled: bool; allow_public_uploads: bool; dry_run: bool
    width: int; height: int; fps: int; min_duration_seconds: int; max_duration_seconds: int
    max_file_size_mb: int; max_upload_retries: int; tts_rate: int; tts_voice: str; crf: int; preset: str

    @classmethod
    def from_env(cls, root: Path | None = None, *, force_dry_run: bool = False) -> "Settings":
        project_root = (root or Path(__file__).resolve().parents[2]).resolve()
        try:
            cfg = json.loads((project_root / "config/settings.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"Unable to load config/settings.json: {exc}") from exc
        video, content, render = cfg.get("video", {}), cfg.get("content", {}), cfg.get("render", {})
        privacy = os.getenv("UPLOAD_PRIVACY", "unlisted").strip().lower()
        if privacy not in {"private", "unlisted", "public"}: raise ConfigurationError("UPLOAD_PRIVACY must be private, unlisted, or public.")
        enabled = env_bool("DAILY_UPLOAD_ENABLED", False)
        allow_public = env_bool("ALLOW_PUBLIC_UPLOADS", False)
        if privacy == "public" and not allow_public:
            raise ConfigurationError("Public uploads require both UPLOAD_PRIVACY=public and ALLOW_PUBLIC_UPLOADS=true.")
        effective_dry_run = force_dry_run or env_bool("DRY_RUN", True)
        if enabled and not effective_dry_run:
            missing = [x for x in ("YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN") if not os.getenv(x)]
            if missing: raise ConfigurationError("DAILY_UPLOAD_ENABLED=true but GitHub Secrets are missing: " + ", ".join(missing))
        minimum, maximum = intval(video,"min_duration_seconds",50), intval(video,"max_duration_seconds",60)
        if minimum < 1 or maximum < minimum or maximum > 180: raise ConfigurationError("Duration range must be valid and maximum no more than 180 seconds.")
        timezone = os.getenv("TIMEZONE", content.get("default_timezone","Asia/Kolkata"))
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(timezone)
        except Exception as exc: raise ConfigurationError("TIMEZONE must be a valid IANA time zone, e.g. Asia/Kolkata.") from exc
        out = Path(os.getenv("OUTPUT_DIR","build/output")); out = out if out.is_absolute() else project_root / out
        return cls(
            root=project_root, topic_file=project_root/"config/topics.json", history_file=project_root/"data/history.json",
            analytics_file=project_root/"data/analytics.json", output_dir=out,
            content_niche=os.getenv("CONTENT_NICHE",content.get("default_niche","all")).strip().lower() or "all",
            video_language=os.getenv("VIDEO_LANGUAGE",content.get("default_language","en")).strip() or "en",
            timezone=timezone, upload_privacy=privacy, max_topic_attempts=min(20,max(1,intval(content,"daily_topic_attempt_limit",5))),
            daily_upload_enabled=enabled, allow_public_uploads=allow_public,
            dry_run=effective_dry_run, width=intval(video,"width",1080), height=intval(video,"height",1920),
            fps=intval(video,"fps",30), min_duration_seconds=minimum, max_duration_seconds=maximum,
            max_file_size_mb=intval(video,"max_file_size_mb",100), max_upload_retries=min(3,max(0,intval(video,"max_upload_retries",3))),
            tts_rate=intval(render,"tts_rate",145), tts_voice=os.getenv("TTS_VOICE",render.get("tts_voice","en-us")),
            crf=intval(render,"crf",21), preset=os.getenv("FFMPEG_PRESET",render.get("preset","veryfast")))

    def validate_runtime(self) -> None:
        missing = [x for x in ("ffmpeg","ffprobe") if not shutil.which(x)]
        if missing: raise ConfigurationError("Missing system executable(s): " + ", ".join(missing) + ". Install FFmpeg.")
        if not (shutil.which("espeak-ng") or shutil.which("espeak")): raise ConfigurationError("Install espeak-ng; narration is generated locally.")
        if (self.width,self.height,self.fps) != (1080,1920,30): raise ConfigurationError("This release requires 1080x1920 at 30 FPS.")
        if not 90 <= self.tts_rate <= 240: raise ConfigurationError("TTS_RATE must be between 90 and 240 words per minute.")
        if not 1 <= self.max_file_size_mb <= 1000: raise ConfigurationError("MAX file size must be between 1 and 1000 MB.")
        if not 0 <= self.crf <= 51: raise ConfigurationError("FFMPEG CRF must be between 0 and 51.")
        if self.preset not in {"ultrafast","superfast","veryfast","faster","fast","medium","slow","slower","veryslow"}: raise ConfigurationError("FFMPEG_PRESET must be a supported x264 preset.")
