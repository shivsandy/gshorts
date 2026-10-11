from __future__ import annotations
import shutil, subprocess
from pathlib import Path

class NarrationError(RuntimeError):
    pass

def resolve_tts() -> str:
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if not binary:
        raise NarrationError("No local TTS executable found. Install espeak-ng (Linux) or espeak (development fallback).")
    return binary

def _duration(path: Path) -> float:
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, timeout=10, check=False)
    try: return float(probe.stdout.strip())
    except ValueError as exc: raise NarrationError(f"Cannot measure generated narration file {path.name}.") from exc

def _render_at_rate(beats: list[dict], output_dir: Path, *, rate: int, voice: str, binary: str) -> tuple[Path, list[dict]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    segments: list[dict] = []
    for idx, beat in enumerate(beats):
        wav = output_dir / f"voice_{idx:02d}.wav"
        cmd = [binary, "-v", voice, "-s", str(rate), "-w", str(wav), beat["text"]]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        except subprocess.TimeoutExpired as exc:
            raise NarrationError(f"TTS timed out on narration beat {idx + 1}.") from exc
        if result.returncode != 0 or not wav.is_file() or wav.stat().st_size < 500:
            raise NarrationError(f"TTS failed on beat {idx + 1}: {(result.stderr or '').strip()[:300]}")
        duration = _duration(wav)
        if not 0.2 <= duration <= 15:
            raise NarrationError(f"Narration beat {idx + 1} has an implausible duration ({duration:.2f}s).")
        segments.append({"path": wav, "text": beat["text"], "duration": duration, "index": idx, "beat": beat})

    concat = output_dir / "narration_concat.txt"
    normalized: list[Path] = []
    for idx, seg in enumerate(segments):
        norm = output_dir / f"voice_norm_{idx:02d}.wav"
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(seg["path"]), "-ar", "44100", "-ac", "1", "-sample_fmt", "s16", str(norm)], capture_output=True, text=True, timeout=25, check=False)
        if r.returncode != 0: raise NarrationError(f"Could not normalize narration beat {idx + 1}.")
        normalized.append(norm); seg["path"] = norm
    silence = output_dir / "pause.wav"
    p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "0.12", "-c:a", "pcm_s16le", str(silence)], capture_output=True, text=True, timeout=10, check=False)
    if p.returncode != 0: raise NarrationError("Could not create narration pauses.")
    lines=[]
    for i, path in enumerate(normalized):
        lines.append(f"file '{path.resolve().as_posix()}'")
        if i < len(normalized)-1: lines.append(f"file '{silence.resolve().as_posix()}'")
    concat.write_text("\n".join(lines)+"\n", encoding="utf-8")
    combined=output_dir/"narration.wav"
    r=subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(concat),"-c:a","pcm_s16le",str(combined)],capture_output=True,text=True,timeout=60,check=False)
    if r.returncode != 0 or not combined.is_file(): raise NarrationError("Failed to assemble narration audio.")
    cursor=0.0
    for i,seg in enumerate(segments):
        seg["start"]=cursor; cursor += seg["duration"]; seg["end"]=cursor
        if i < len(segments)-1: cursor += 0.12
    return combined,segments

def render_narration(beats: list[dict], output_dir: Path, *, rate: int = 145, voice: str = "en-us") -> tuple[Path, list[dict]]:
    """Render speech locally and adjust rate toward 56s when possible, in at most two recalibrations."""
    binary=resolve_tts(); active_rate=rate
    combined,segments=_render_at_rate(beats,output_dir,rate=active_rate,voice=voice,binary=binary)
    for _ in range(2):
        duration=_duration(combined)
        if 54.0 <= duration <= 58.0: break
        adjusted=max(90,min(240,round(active_rate*duration/56.0)))
        if adjusted==active_rate: break
        active_rate=adjusted
        combined,segments=_render_at_rate(beats,output_dir,rate=active_rate,voice=voice,binary=binary)
    return combined,segments
