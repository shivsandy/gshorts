from __future__ import annotations
import subprocess
from pathlib import Path
from PIL import Image
from .captions import write_captions
from .visuals import render_scene
from .validator import validate_render_tools, validate_video

class RenderError(RuntimeError): pass

def _filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\","/").replace(":","\\:").replace("'","\\'")

def render_video(script: dict, narration_path: Path, segments: list[dict], output_dir: Path, *, min_seconds: int=50, max_seconds: int=60, max_file_size_mb: int=100, fps: int=30, crf: int=21, preset: str="veryfast") -> dict:
    validate_render_tools()
    output_dir.mkdir(parents=True,exist_ok=True)
    scene_dir=output_dir/"scenes"; scene_dir.mkdir(parents=True,exist_ok=True)
    beats=script["beats"]
    if len(beats)!=len(segments): raise RenderError("Narration and visual beat counts do not match.")
    scenes=[]
    for i,beat in enumerate(beats): scenes.append(render_scene(beat,i,len(beats),scene_dir/f"scene_{i:02d}.png"))
    captions_ass,captions_srt=write_captions(segments,output_dir)
    concat=output_dir/"scenes.txt"; lines=[]
    transition_dir=output_dir/"transitions"; transition_dir.mkdir(parents=True,exist_ok=True)
    transition_frames=max(1,round(fps*0.32)); transition_duration=transition_frames/fps
    trans_paths=[]
    for i in range(len(scenes)-1):
        with Image.open(scenes[i]) as previous, Image.open(scenes[i+1]) as nxt:
            a=previous.convert("RGB"); b=nxt.convert("RGB")
            frames=[]
            for f in range(transition_frames):
                alpha=(f+1)/(transition_frames+1)
                frame=Image.blend(a,b,alpha)
                frame_path=transition_dir/f"transition_{i:02d}_{f:02d}.png"
                frame.save(frame_path,"PNG",optimize=False)
                frames.append(frame_path)
            trans_paths.append(frames)
    for i,(scene,segment) in enumerate(zip(scenes,segments)):
        scene_duration=segment["duration"]+(0.12 if i < len(scenes)-1 else 0)
        hold=max(0.1,scene_duration-transition_duration) if i < len(scenes)-1 else scene_duration
        lines.extend([f"file '{scene.resolve().as_posix()}'",f"duration {hold:.5f}"])
        if i < len(scenes)-1:
            for frame in trans_paths[i]: lines.extend([f"file '{frame.resolve().as_posix()}'",f"duration {1/fps:.7f}"])
    lines.append(f"file '{scenes[-1].resolve().as_posix()}'")
    concat.write_text("\n".join(lines)+"\n",encoding="utf-8")
    output=output_dir/"short.mp4"
    vf=f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},subtitles='{_filter_path(captions_ass)}'"
    cmd=["ffmpeg","-y","-hide_banner","-loglevel","error","-f","concat","-safe","0","-i",str(concat),"-i",str(narration_path),"-map","0:v:0","-map","1:a:0","-vf",vf,"-t",str(max_seconds+0.1),"-c:v","libx264","-preset",preset,"-crf",str(crf),"-pix_fmt","yuv420p","-r",str(fps),"-c:a","aac","-b:a","128k","-ar","44100","-movflags","+faststart","-shortest",str(output)]
    try: p=subprocess.run(cmd,capture_output=True,text=True,timeout=300,check=False)
    except subprocess.TimeoutExpired as exc: raise RenderError("FFmpeg exceeded the 5-minute render limit.") from exc
    if p.returncode != 0: raise RenderError("FFmpeg failed to render video: "+(p.stderr or "unknown error")[-1200:])
    details=validate_video(output,min_seconds=min_seconds,max_seconds=max_seconds,max_file_size_mb=max_file_size_mb)
    details["captions_srt"]=str(captions_srt)
    details["caption_count"]=len([x for x in captions_srt.read_text(encoding="utf-8").split("\n\n") if x.strip()])
    return details
