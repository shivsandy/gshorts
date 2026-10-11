from __future__ import annotations
import os, re, time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

RUN_MARKER_PREFIX="[SHORTS_FACTORY_RUN:"

def run_marker(run_key: str) -> str: return f"{RUN_MARKER_PREFIX}{run_key}]"

def _get_uploads_playlist(youtube: Any) -> str | None:
    response=youtube.channels().list(part="contentDetails",mine=True,maxResults=1).execute(num_retries=1)
    items=response.get("items",[])
    return items[0].get("contentDetails",{}).get("relatedPlaylists",{}).get("uploads") if items else None

def list_recent_uploads(youtube: Any, *, max_pages: int=4) -> list[dict]:
    """Return a bounded window of recent channel uploads and metadata for duplicate prevention."""
    playlist=_get_uploads_playlist(youtube)
    if not playlist: return []
    page=None; ids=[]
    for _ in range(max_pages):
        kwargs={"part":"contentDetails,snippet","playlistId":playlist,"maxResults":50}
        if page: kwargs["pageToken"]=page
        result=youtube.playlistItems().list(**kwargs).execute(num_retries=1)
        for item in result.get("items",[]):
            snippet=item.get("snippet",{}); resource=snippet.get("resourceId",{})
            if resource.get("kind")=="youtube#video" and resource.get("videoId"):
                ids.append(resource["videoId"])
        page=result.get("nextPageToken")
        if not page: break
    uploads=[]
    for start in range(0,len(ids),50):
        batch=ids[start:start+50]
        if not batch: continue
        response=youtube.videos().list(part="snippet,status,contentDetails",id=",".join(batch)).execute(num_retries=1)
        for item in response.get("items",[]):
            snippet=item.get("snippet",{}); description=snippet.get("description","")
            uploads.append({"video_id":item["id"],"title":snippet.get("title",""),"description":description,
                "published_at":snippet.get("publishedAt"),"privacy_status":item.get("status",{}).get("privacyStatus"),
                "duration":item.get("contentDetails",{}).get("duration"),"url":f"https://www.youtube.com/watch?v={item['id']}"})
    return uploads

def find_existing_upload(youtube: Any, marker: str, *, max_pages: int=4) -> dict | None:
    """Search recent uploads for this run marker to recover after a lost response."""
    return next((item for item in list_recent_uploads(youtube,max_pages=max_pages) if marker in item.get("description","")),None)

def remote_used_topic_ids(uploads: list[dict], topics: list[dict]) -> set[str]:
    """Identify topic IDs already present in recent channel uploads, including markerless title matches."""
    title_to_ids={str(t.get("title", "")).strip().casefold():str(t.get("id")) for t in topics}
    used=set()
    for item in uploads:
        description=str(item.get("description", ""))
        for match in re.findall(r"\[SHORTS_FACTORY_TOPIC:([a-zA-Z0-9_-]+)\]",description): used.add(match)
        title=str(item.get("title", "")).strip().casefold()
        if title in title_to_ids: used.add(title_to_ids[title])
    return used

def upload_short(youtube: Any, video_path: str, script: dict, *, run_key: str, privacy: str="unlisted", language: str="en", max_retries: int=3) -> dict:
    """Perform one resumable videos.insert call. Never blindly repeat an ambiguous upload."""
    if privacy not in {"private","unlisted","public"}: raise ValueError("Invalid upload privacy.")
    try:
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError
    except ImportError as exc: raise RuntimeError("Install google-api-python-client before uploading.") from exc
    marker=run_marker(run_key)
    existing=find_existing_upload(youtube,marker)
    if existing: return {**existing,"recovered":True,"url":f"https://www.youtube.com/watch?v={existing['video_id']}"}
    topic_marker=f"[SHORTS_FACTORY_TOPIC:{script['topic_id']}]"
    description=(script["description"].strip()+"\n\n"+marker+"\n"+topic_marker)[:4900]
    tags=[]
    for tag in script.get("hashtags",[]):
        clean=re.sub(r"[^A-Za-z0-9]","",str(tag).lstrip("#"))
        if clean and clean.lower() not in {t.lower() for t in tags}: tags.append(clean[:50])
    body={"snippet":{"title":script["title"][:100],"description":description,"tags":tags[:12],"categoryId":"27","defaultLanguage":language,"defaultAudioLanguage":language},
          "status":{"privacyStatus":privacy,"selfDeclaredMadeForKids":False}}
    media=MediaFileUpload(video_path,mimetype="video/mp4",resumable=True,chunksize=8*1024*1024)
    request=youtube.videos().insert(part="snippet,status",body=body,media_body=media)
    try:
        response=None; attempts=0
        while response is None:
            status,response=request.next_chunk(num_retries=max_retries)
            attempts+=1
            if attempts>100: raise RuntimeError("Upload exceeded the chunk-count safety limit.")
    except Exception as exc:
        try:
            recovered=find_existing_upload(youtube,marker)
            if recovered: return {**recovered,"recovered":True,"url":f"https://www.youtube.com/watch?v={recovered['video_id']}"}
        except Exception:
            pass
        if isinstance(exc,HttpError) and getattr(exc,"resp",None) is not None:
            code=getattr(exc.resp,"status",None)
            raise RuntimeError(f"YouTube upload failed with HTTP {code}. No automatic second insert was attempted; inspect the channel before rerunning.") from None
        raise RuntimeError(f"YouTube upload result is uncertain ({type(exc).__name__}). No automatic second insert was attempted; inspect the channel before rerunning.") from None
    video_id=response.get("id") if isinstance(response,dict) else None
    if not video_id: raise RuntimeError("YouTube API returned no video ID; upload cannot be recorded as successful.")
    return {"video_id":video_id,"url":f"https://www.youtube.com/watch?v={video_id}","title":script["title"],"published_at":datetime.now(ZoneInfo(os.getenv("TIMEZONE","UTC"))).isoformat(),"privacy_status":privacy,"recovered":False}
