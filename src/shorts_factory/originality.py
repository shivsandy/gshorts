from __future__ import annotations
import hashlib,re
from difflib import SequenceMatcher
from typing import Any
class OriginalityError(RuntimeError): pass

def normalize_script(text: str) -> str: return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9\s'-]"," ",text.lower())).strip()
def script_fingerprint(text: str) -> str: return hashlib.sha256(normalize_script(text).encode()).hexdigest()
def _shingles(text: str, n: int=4) -> set[tuple[str,...]]:
    w=normalize_script(text).split()
    return {tuple(w[i:i+n]) for i in range(max(1,len(w)-n+1))} if w else set()
def similarity(a: str,b: str) -> float:
    if not normalize_script(a) or not normalize_script(b): return 0.0
    x,y=_shingles(a),_shingles(b); jac=len(x&y)/max(1,len(x|y))
    return max(jac,SequenceMatcher(None,normalize_script(a),normalize_script(b)).ratio())
def validate_originality(script: dict[str,Any], history: list[dict[str,Any]], threshold: float=.82) -> None:
    topic_id=script["topic_id"]; text=script["narration"]; fp=script_fingerprint(text)
    for r in history:
        if r.get("topic_id")==topic_id: raise OriginalityError(f"Topic {topic_id!r} has already been published.")
        if r.get("script_fingerprint")==fp: raise OriginalityError("This script fingerprint already exists in history.")
        old=r.get("script_text","")
        if old and similarity(text,old)>=threshold: raise OriginalityError(f"Script is too similar to a previous upload (threshold {threshold:.2f}).")
