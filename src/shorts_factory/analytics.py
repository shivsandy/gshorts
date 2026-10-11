from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .state import load_json, save_json_atomic

def snapshot_published_stats(youtube: Any, history: dict, analytics_path: Path) -> dict:
    """Snapshot authorized YouTube Data API views/likes for locally tracked uploads.
    The Data API does not expose audience-retention or revenue data through this method.
    """
    records=history.get("published",[]); ids=[r.get("video_id") for r in records if r.get("video_id")]
    record_by_id={r.get("video_id"):r for r in records if r.get("video_id")}
    existing=load_json(analytics_path,{"snapshots":[]}); rows=[]
    for start in range(0,len(ids),50):
        batch=ids[start:start+50]
        if not batch: continue
        response=youtube.videos().list(part="snippet,statistics,contentDetails",id=",".join(batch)).execute(num_retries=1)
        for item in response.get("items",[]):
            stats=item.get("statistics",{}); snippet=item.get("snippet",{}); details=item.get("contentDetails",{})
            tracked=record_by_id.get(item["id"],{})
            rows.append({"collected_at":datetime.now(timezone.utc).isoformat(),"video_id":item["id"],"title":snippet.get("title"),
                "topic_category":tracked.get("category"),"category_id":snippet.get("categoryId"),"topic_id":tracked.get("topic_id"),
                "published_at":snippet.get("publishedAt"),"duration":details.get("duration"),"views":int(stats.get("viewCount",0)),"likes":int(stats.get("likeCount",0)) if "likeCount" in stats else None})
    existing.setdefault("snapshots",[]).extend(rows)
    existing["snapshots"]=existing["snapshots"][-5000:]
    save_json_atomic(analytics_path,existing)
    return {"snapshot_count":len(rows),"analytics_file":str(analytics_path)}
