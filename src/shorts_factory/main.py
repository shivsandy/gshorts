from __future__ import annotations
import argparse, json, os, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from .analytics import snapshot_published_stats
from .config import ConfigurationError, Settings
from .fact_checker import FactCheckError, validate_topic_sources
from .narration import NarrationError, render_narration
from .originality import OriginalityError, validate_originality
from .renderer import RenderError, render_video
from .script_writer import build_script
from .state import load_json, publish_record, save_json_atomic
from .topic_engine import TopicError
from .validator import ValidationError
from .youtube_auth import YouTubeAuthError
from .topic_engine import load_topics, select_topic

class PipelineError(RuntimeError): pass

def choose_eligible_script(topics: list[dict], *, niche: str, used_topic_ids: set[str], run_key: str,
                           history: list[dict], max_attempts: int) -> tuple[dict, dict, list[str]]:
    """Try a bounded number of distinct curated topics; fail closed if all candidates fail checks."""
    excluded=set(used_topic_ids); last_error: Exception | None=None
    for attempt in range(max_attempts):
        try:
            topic=select_topic(topics,niche,excluded,f"{run_key}:candidate:{attempt}")
        except TopicError as exc:
            last_error=exc; break
        excluded.add(topic["id"])
        try:
            sources=validate_topic_sources(topic)
            script=build_script(topic)
            if not 90 <= script["word_count"] <= 180:
                raise PipelineError(f"Topic {topic['id']} has {script['word_count']} words, outside the editorial range (90–180).")
            validate_originality(script,history)
            return topic,script,sources
        except (FactCheckError,OriginalityError,PipelineError) as exc:
            last_error=exc
            continue
    detail=f" Last rejection: {last_error}" if last_error else ""
    raise PipelineError(f"No eligible source-reviewed original topic found after at most {max_attempts} attempts.{detail}") from None

def _summary(settings: Settings, *, run_key: str, topic: str="—", duration: float | None=None, status: str, url: str | None=None, note: str="") -> None:
    lines=["## YouTube Shorts Factory",f"- Run key: `{run_key}`",f"- Topic: {topic}",f"- Duration: {f'{duration:.2f}s' if duration is not None else 'n/a'}",f"- Upload status: **{status}**"]
    if url: lines.append(f"- Video: {url}")
    if note: lines.append(f"- Notes: {note}")
    content="\n".join(lines)+"\n"
    summary=os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as f: f.write(content)
    print(content)

def _duration_from_iso8601(value: str | None) -> float | None:
    import re
    if not value: return None
    m=re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?",value)
    if not m: return None
    h,mi,se=m.groups(); return int(h or 0)*3600+int(mi or 0)*60+float(se or 0)

def _record_recovered(history: dict, run_key: str, topics: list[dict], remote: dict) -> None:
    topic=next((t for t in topics if t.get("title")==remote.get("title")),None)
    if topic:
        script=build_script(topic); duration=_duration_from_iso8601(remote.get("duration")) or 0.0
        publish_record(history,run_key=run_key,video_id=remote["video_id"],script=script,duration=duration,published_at=remote.get("published_at") or datetime.now().astimezone().isoformat())
    else:
        row={"run_key":run_key,"published_at":remote.get("published_at"),"video_id":remote["video_id"],
            "video_url":remote.get("url") or f"https://www.youtube.com/watch?v={remote['video_id']}","topic_id":"remote-recovered-"+run_key,
            "category":"unknown","title":remote.get("title","Recovered upload"),"duration_seconds":_duration_from_iso8601(remote.get("duration")),"source_urls":[]}
        records=history.setdefault("published",[])
        existing_row=next((r for r in records if r.get("run_key")==run_key),None)
        if existing_row: records[records.index(existing_row)]=row
        else: records.append(row)

def run_pipeline(*, force_dry_run: bool=False) -> int:
    settings=Settings.from_env(force_dry_run=force_dry_run)
    settings.validate_runtime()
    topics=load_topics(settings.topic_file)
    history=load_json(settings.history_file,{"published":[]})
    today=datetime.now(ZoneInfo(settings.timezone)).date().isoformat()
    run_key=today
    out_dir=settings.output_dir/run_key
    out_dir.mkdir(parents=True,exist_ok=True)

    youtube=None; remote_used=set()
    should_upload=settings.daily_upload_enabled and not settings.dry_run
    if should_upload:
        from .youtube_auth import get_youtube_client
        from .youtube_upload import list_recent_uploads, remote_used_topic_ids, run_marker
        youtube=get_youtube_client()
        recent_uploads=list_recent_uploads(youtube)
        existing=next((item for item in recent_uploads if run_marker(run_key) in item.get("description", "")),None)
        if existing:
            _record_recovered(history,run_key,topics,existing)
            save_json_atomic(settings.history_file,history)
            _summary(settings,run_key=run_key,topic=existing.get("title","Previously uploaded video"),duration=_duration_from_iso8601(existing.get("duration")),status="already uploaded (recovered)",url=existing.get("url") or f"https://www.youtube.com/watch?v={existing['video_id']}")
            return 0
        remote_used=remote_used_topic_ids(recent_uploads,topics)

    used={str(r.get("topic_id")) for r in history.get("published",[]) if r.get("topic_id")} | remote_used
    topic,script,source_urls=choose_eligible_script(topics,niche=settings.content_niche,used_topic_ids=used,
        run_key=run_key,history=history.get("published",[]),max_attempts=settings.max_topic_attempts)
    narration_dir=out_dir/"audio"
    narration_path,segments=render_narration(script["beats"],narration_dir,rate=settings.tts_rate,voice=settings.tts_voice)
    report=render_video(script,narration_path,segments,out_dir,min_seconds=settings.min_duration_seconds,max_seconds=settings.max_duration_seconds,
        max_file_size_mb=settings.max_file_size_mb,fps=settings.fps,crf=settings.crf,preset=settings.preset)
    manifest={"run_key":run_key,"topic_id":topic["id"],"category":topic["category"],"title":script["title"],"script":script["narration"],
        "script_fingerprint":script["script_fingerprint"],"source_urls":source_urls,"claims":script["claims"],"video_validation":report,"dry_run":settings.dry_run or not settings.daily_upload_enabled}
    (out_dir/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Validated local render: {report['path']} ({report['duration_seconds']:.2f}s, {report['file_size_mb']:.2f} MB)")

    if not should_upload:
        status="dry run; not uploaded" if settings.dry_run else "upload disabled; not uploaded"
        _summary(settings,run_key=run_key,topic=script["title"],duration=report["duration_seconds"],status=status,note="Review build/output/"+run_key+"/short.mp4 and manifest.json.")
        return 0

    from .youtube_upload import upload_short
    result=upload_short(youtube,str(report["path"]),script,run_key=run_key,privacy=settings.upload_privacy,language=settings.video_language,max_retries=settings.max_upload_retries)
    video_id=result.get("video_id")
    if not video_id: raise PipelineError("YouTube API did not return a video ID; upload is not treated as successful.")
    publish_record(history,run_key=run_key,video_id=video_id,script=script,duration=report["duration_seconds"],published_at=result.get("published_at") or datetime.now(ZoneInfo(settings.timezone)).isoformat())
    save_json_atomic(settings.history_file,history)
    status="uploaded" if not result.get("recovered") else "already uploaded (recovered)"
    _summary(settings,run_key=run_key,topic=script["title"],duration=report["duration_seconds"],status=status,url=result.get("url"))
    return 0

def main() -> int:
    parser=argparse.ArgumentParser(description="Generate and optionally upload one original, source-reviewed YouTube Short.")
    parser.add_argument("--dry-run",action="store_true",help="Force local generation and validation only; never upload.")
    parser.add_argument("--stats",action="store_true",help="Snapshot views/likes for tracked uploads, then exit.")
    args=parser.parse_args()
    try:
        if args.stats:
            settings=Settings.from_env(force_dry_run=True)
            history=load_json(settings.history_file,{"published":[]})
            from .youtube_auth import get_youtube_client
            client=get_youtube_client()
            report=snapshot_published_stats(client,history,settings.analytics_file)
            print(json.dumps(report,indent=2)); return 0
        return run_pipeline(force_dry_run=args.dry_run)
    except (ConfigurationError,PipelineError,TopicError,NarrationError,RenderError,ValidationError,YouTubeAuthError,RuntimeError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr); return 2
    except Exception as exc:
        print(f"ERROR: Pipeline failed ({type(exc).__name__}). Inspect sanitized step logs and configuration.",file=sys.stderr)
        return 1

if __name__=="__main__": raise SystemExit(main())