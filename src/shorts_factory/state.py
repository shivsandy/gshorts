from __future__ import annotations
import json,os,tempfile
from pathlib import Path
from typing import Any

def load_json(path: Path, default: dict[str,Any]) -> dict[str,Any]:
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError: return default.copy()
    except json.JSONDecodeError as exc: raise RuntimeError(f"Invalid JSON state {path}: {exc}") from exc
    if not isinstance(value,dict): raise RuntimeError(f"State {path} must be a JSON object.")
    return value

def save_json_atomic(path: Path,value: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("w",encoding="utf-8",dir=path.parent,delete=False) as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write("\n"); temp=Path(f.name)
    os.replace(temp,path)

def publish_record(history: dict[str,Any], *,run_key: str,video_id: str,script: dict[str,Any],duration: float,published_at: str) -> None:
    records=history.setdefault("published",[])
    row={"run_key":run_key,"published_at":published_at,"video_id":video_id,"video_url":f"https://www.youtube.com/watch?v={video_id}",
        "topic_id":script["topic_id"],"category":script["category"],"title":script["title"],"duration_seconds":round(duration,2),
        "script_fingerprint":script["script_fingerprint"],"script_text":script["narration"],"source_urls":script["source_urls"]}
    old=next((r for r in records if r.get("run_key")==run_key),None)
    if old: records[records.index(old)]=row
    else: records.append(row)
    records.sort(key=lambda r:r.get("run_key",""))
