from __future__ import annotations
from pathlib import Path
import re

def _stamp(seconds: float) -> str:
    seconds=max(0.0,seconds); h=int(seconds//3600); m=int((seconds%3600)//60); s=seconds%60
    return f"{h}:{m:02d}:{s:05.2f}"

def _srt_stamp(seconds: float) -> str:
    ms=int(round(max(0,seconds)*1000)); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def _chunks(text: str, max_words: int=5) -> list[list[str]]:
    words=re.findall(r"\S+",text.strip())
    return [words[i:i+max_words] for i in range(0,len(words),max_words)]

def write_captions(segments: list[dict], output_dir: Path) -> tuple[Path,Path]:
    """Create word-highlighted ASS captions and SRT. Word timings are estimated from text length."""
    output_dir.mkdir(parents=True,exist_ok=True)
    ass_path=output_dir/"captions.ass"; srt_path=output_dir/"captions.srt"
    header="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,55,&H00FFFFFF,&H0000C8FF,&H00101A2E,&H90081020,1,0,0,0,100,100,0,0,1,4,1.5,2,70,70,275,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dialogues=[]; srt=[]; index=1
    for seg in segments:
        words_all=re.findall(r"\S+",seg["text"].strip())
        chunks=_chunks(seg["text"],5)
        if not words_all or not chunks: continue
        weights=[max(1,len(re.sub(r"[^A-Za-z0-9]","",w))) for w in words_all]
        total=sum(weights); durations=[seg["duration"]*w/total for w in weights]
        word_spans=[]; t=seg["start"]
        for w,d in zip(words_all,durations): word_spans.append((w,t,t+d,d)); t+=d
        offset=0
        for chunk in chunks:
            spans=word_spans[offset:offset+len(chunk)]; offset+=len(chunk)
            start=spans[0][1]; end=spans[-1][2]
            karaoke=[]
            for word,ws,we,d in spans:
                cs=max(1,int(round(d*100)))
                safe=word.replace("{","(").replace("}",")")
                karaoke.append(f"{{\\k{cs}}}{safe}")
            line=" ".join(karaoke)
            dialogues.append(f"Dialogue: 0,{_stamp(start)},{_stamp(end)},Caption,,0,0,0,,{line}")
            plain=" ".join(chunk)
            srt.append(f"{index}\n{_srt_stamp(start)} --> {_srt_stamp(end)}\n{plain}\n")
            index+=1
    ass_path.write_text(header+"\n".join(dialogues)+"\n",encoding="utf-8")
    srt_path.write_text("\n".join(srt),encoding="utf-8")
    return ass_path,srt_path
