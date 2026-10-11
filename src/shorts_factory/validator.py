from __future__ import annotations
import json, shutil, subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any

class ValidationError(RuntimeError): pass

def probe_video(path: Path) -> dict[str,Any]:
    if not path.is_file() or path.stat().st_size == 0: raise ValidationError("Rendered MP4 does not exist or is empty.")
    p=subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],capture_output=True,text=True,timeout=15,check=False)
    if p.returncode != 0: raise ValidationError("ffprobe could not read the rendered file.")
    try: info=json.loads(p.stdout)
    except json.JSONDecodeError as exc: raise ValidationError("ffprobe returned invalid metadata.") from exc
    return info

def validate_video(path: Path, *, min_seconds: int=50, max_seconds: int=60, max_file_size_mb: int=100, expected_size: tuple[int,int]=(1080,1920), expected_fps: float=30.0) -> dict[str,Any]:
    info=probe_video(path); streams=info.get("streams",[]); video=next((s for s in streams if s.get("codec_type")=="video"),None); audio=next((s for s in streams if s.get("codec_type")=="audio"),None)
    if not video: raise ValidationError("MP4 has no video stream.")
    if not audio: raise ValidationError("MP4 has no audio stream.")
    if video.get("codec_name") != "h264": raise ValidationError(f"Expected H.264 video, got {video.get('codec_name')}.")
    if audio.get("codec_name") != "aac": raise ValidationError(f"Expected AAC audio, got {audio.get('codec_name')}.")
    if (int(video.get("width",0)),int(video.get("height",0))) != expected_size: raise ValidationError("Video resolution is not the configured vertical 1080x1920 size.")
    try: fps=float(Fraction(video.get("avg_frame_rate") or video.get("r_frame_rate","0/1")))
    except (ValueError,ZeroDivisionError): raise ValidationError("Invalid video frame rate metadata.") from None
    if abs(fps-expected_fps)>0.1: raise ValidationError(f"Expected {expected_fps:g} FPS, got {fps:g} FPS.")
    duration=float(info.get("format",{}).get("duration",0) or 0)
    if not min_seconds <= duration <= max_seconds: raise ValidationError(f"Duration {duration:.2f}s falls outside permitted {min_seconds}–{max_seconds}s range.")
    size_mb=path.stat().st_size/(1024*1024)
    if size_mb > max_file_size_mb: raise ValidationError(f"File is {size_mb:.1f} MB, over the configured {max_file_size_mb} MB limit.")
    return {"path":str(path),"duration_seconds":round(duration,3),"file_size_bytes":path.stat().st_size,"file_size_mb":round(size_mb,2),"width":int(video["width"]),"height":int(video["height"]),"video_codec":video["codec_name"],"audio_codec":audio["codec_name"],"fps":round(fps,3)}

def validate_render_tools() -> None:
    missing=[x for x in ("ffmpeg","ffprobe") if not shutil.which(x)]
    if missing: raise ValidationError("Missing system tool(s): "+", ".join(missing))
    p=subprocess.run(["ffmpeg","-hide_banner","-filters"],capture_output=True,text=True,timeout=10,check=False)
    if " subtitles " not in p.stdout and " subtitles=" not in p.stdout:
        raise ValidationError("This FFmpeg build lacks the subtitles/libass filter; install a build with libass support.")
