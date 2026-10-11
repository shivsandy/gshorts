from __future__ import annotations
import re
from .originality import script_fingerprint
from typing import Any

def clean_text(text: str) -> str: return re.sub(r"\s+"," ",text).strip()

def build_script(topic: dict[str,Any]) -> dict[str,Any]:
    beats=[{**b,"text":clean_text(b["text"])} for b in topic["beats"]]
    narration=" ".join(b["text"] for b in beats)
    fingerprint=script_fingerprint(narration)
    desc=clean_text(topic.get("description",topic["title"]))
    sources="\n".join(f"Source: {c['source_url']}" for c in topic.get("claims",[]))
    return {"topic_id":topic["id"],"category":topic["category"],"title":topic["title"][:95],
        "description":desc+"\n\n"+sources+"\n\n"+" ".join(topic.get("hashtags",["#Shorts"])),
        "hashtags":topic.get("hashtags",["#Shorts"]),"beats":beats,"narration":narration,
        "script_fingerprint":fingerprint,"word_count":len(re.findall(r"\b[\w'-]+\b",narration)),
        "source_urls":topic.get("source_urls",[]),"claims":topic.get("claims",[])}
