from __future__ import annotations
import base64, gzip, hashlib, json
from pathlib import Path
from typing import Any

class TopicError(RuntimeError):
    pass

def _load_payload(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and raw.get("compressed_topic_parts"):
            parts = raw["compressed_topic_parts"]
            if not isinstance(parts, list) or not parts:
                raise TopicError("compressed_topic_parts must be a non-empty list.")
            encoded = []
            for index, name in enumerate(parts):
                piece_path = (path.parent / str(name)).resolve()
                if piece_path.parent != (path.parent / "topic_bank").resolve():
                    raise TopicError("Topic data chunks must be files inside config/topic_bank.")
                piece = piece_path.read_text(encoding="ascii").strip()
                # Non-final pieces are fixed-width; ignore accidental trailing transfer padding.
                if index < len(parts) - 1:
                    piece = piece[:4000]
                encoded.append(piece)
            compressed = base64.b64decode("".join(encoded), validate=True)
            return json.loads(gzip.decompress(compressed).decode("utf-8"))
        if isinstance(raw, dict) and raw.get("compressed_topics_file"):
            compressed_path = (path.parent / str(raw["compressed_topics_file"])).resolve()
            if compressed_path.parent != path.parent.resolve():
                raise TopicError("Compressed topic bank must be a file in the config directory.")
            with gzip.open(compressed_path, "rt", encoding="utf-8") as handle:
                return json.load(handle)
        return raw
    except TopicError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, gzip.BadGzipFile) as exc:
        raise TopicError(f"Cannot load topic bank {path}: {exc}") from exc

def load_topics(path: Path) -> list[dict[str, Any]]:
    payload = _load_payload(path)
    topics = payload.get("topics") if isinstance(payload, dict) else None
    if not isinstance(topics, list) or not topics:
        raise TopicError("Topic bank must contain a non-empty topics array.")
    ids = set()
    for topic in topics:
        if not isinstance(topic, dict) or {"id", "category", "title", "beats", "claims", "source_urls"} - topic.keys():
            raise TopicError("Every topic needs id, category, title, beats, claims, and source_urls.")
        if topic["id"] in ids:
            raise TopicError(f"Duplicate topic ID: {topic['id']}")
        ids.add(topic["id"])
        if len(topic["beats"]) < 5 or any(not beat.get("text") or not beat.get("visual_title") for beat in topic["beats"]):
            raise TopicError(f"Topic {topic['id']} needs at least five complete narration/visual beats.")
    return topics

def select_topic(topics: list[dict[str, Any]], niche: str, used_topic_ids: set[str], run_key: str) -> dict[str, Any]:
    requested = {item.strip() for item in niche.split(",") if item.strip()}
    eligible = sorted(
        (topic for topic in topics if (not requested or "all" in requested or topic["category"].lower() in requested)
         and topic["id"] not in used_topic_ids),
        key=lambda item: item["id"],
    )
    if not eligible:
        raise TopicError(f"No unused topics remain for CONTENT_NICHE={niche!r}. Add source-reviewed topics; the pipeline will not recycle topics.")
    digest = hashlib.sha256(run_key.encode()).digest()
    return eligible[int.from_bytes(digest[:8], "big") % len(eligible)]
