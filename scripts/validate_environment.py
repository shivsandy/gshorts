#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from shorts_factory.config import Settings
from shorts_factory.fact_checker import validate_topic_sources
from shorts_factory.topic_engine import load_topics

def main() -> int:
    try:
        settings=Settings.from_env(); settings.validate_runtime()
        topics=load_topics(settings.topic_file)
        for topic in topics: validate_topic_sources(topic)
        print(f"Environment valid. Topics: {len(topics)}; niche: {settings.content_niche}; privacy: {settings.upload_privacy}; uploads enabled: {settings.daily_upload_enabled}; dry run: {settings.dry_run}.")
        if settings.daily_upload_enabled and not settings.dry_run:
            print("YouTube uploads are enabled; runtime configuration includes the required secret names.")
        return 0
    except Exception as exc:
        print(f"Environment validation failed: {exc}",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
