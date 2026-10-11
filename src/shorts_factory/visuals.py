from __future__ import annotations
import math, random, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W,H=1080,1920
BG=(10,16,32)
ACCENTS=[(69,190,255),(119,225,184),(255,190,92),(224,125,255),(255,112,128)]

def _font(size: int, bold: bool=False):
    candidates = (["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"] if bold else ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf","/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"])
    for p in candidates:
        if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def _rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def _fit_lines(draw, text, font, max_width):
    words=text.split(); lines=[]; current=""
    for word in words:
        trial=f"{current} {word}".strip()
        if draw.textbbox((0,0),trial,font=font)[2] <= max_width: current=trial
        else:
            if current: lines.append(current)
            current=word
    if current: lines.append(current)
    return lines

def _draw_icon(draw, idx, cx, cy, color, rng, cue=""):
    text=cue.lower()
    if any(k in text for k in ("venus","planet","moon","orbit","saturn","mercury","neptune","sun","rotation","season","earth tilt")):
        kind=0 if idx%2==0 else 5
    elif any(k in text for k in ("chart","measure","number","percent","year","day","distance","speed","temperature","rate","record","data","statistic")):
        kind=1
    elif any(k in text for k in ("brain","memory","idea","think","belief","productivity","takeaway","lesson","why it matters")):
        kind=2
    elif any(k in text for k in ("oxygen","blood","molecule","chemical","atom","heart","plant","metal","cartilage","bone","skeleton","cell","leaf","photosynthesis")):
        kind=3
    elif any(k in text for k in ("technology","gps","signal","radio","password","phone","microwave","compass","magnetic","internet","navigation","sensor")):
        kind=4
    elif any(k in text for k in ("water","ocean","wave","sound","light","rainbow","sky","lightning","ice","cloud","wind","rain","weather","bubble")):
        kind=6
    else:
        kind=idx%7
    if kind==0:
        for r in (90,145,205): draw.ellipse((cx-r,cy-r,cx+r,cy+r),outline=color,width=5)
        draw.ellipse((cx-28,cy-28,cx+28,cy+28),fill=color)
        draw.ellipse((cx+115,cy-30,cx+145,cy),fill=ACCENTS[(idx+2)%len(ACCENTS)])
    elif kind==1:
        for j,h in enumerate([135,220,165,285]):
            x=cx-190+j*100; _rounded(draw,(x,cy+140-h,x+64,cy+140),18,ACCENTS[(idx+j)%len(ACCENTS)])
        draw.line((cx-220,cy+148,cx+250,cy+148),fill=(115,136,168),width=4)
    elif kind==2:
        draw.ellipse((cx-100,cy-145,cx+100,cy+55),outline=color,width=12)
        draw.line((cx-60,cy+70,cx+60,cy+70),fill=color,width=12); draw.line((cx-48,cy+98,cx+48,cy+98),fill=color,width=12)
        for a in range(0,360,45):
            rad=math.radians(a); x1=cx+math.cos(rad)*128; y1=cy-45+math.sin(rad)*128; x2=cx+math.cos(rad)*176; y2=cy-45+math.sin(rad)*176
            draw.line((x1,y1,x2,y2),fill=ACCENTS[(idx+1)%len(ACCENTS)],width=7)
    elif kind==3:
        pts=[(cx-130,cy-50),(cx,cy-150),(cx+130,cy-45),(cx+85,cy+110),(cx-75,cy+120)]
        for a,b in zip(pts,pts[1:]+pts[:1]): draw.line((*a,*b),fill=color,width=8)
        for j,(x,y) in enumerate(pts): draw.ellipse((x-28,y-28,x+28,y+28),fill=ACCENTS[(idx+j)%len(ACCENTS)])
    elif kind==4:
        for r in (65,125,185): draw.arc((cx-r,cy-r,cx+r,cy+r),205,335,fill=color,width=10)
        draw.ellipse((cx-26,cy+15,cx+26,cy+67),fill=color)
        draw.line((cx,cy+30,cx,cy-95),fill=color,width=10)
    elif kind==5:
        draw.ellipse((cx-118,cy-118,cx+118,cy+118),fill=color)
        draw.ellipse((cx-200,cy-42,cx+200,cy+42),outline=ACCENTS[(idx+1)%len(ACCENTS)],width=12)
        draw.ellipse((cx+45,cy-77,cx+76,cy-45),fill=(22,31,55))
    else:
        for j in range(5):
            pts=[]
            for x in range(cx-220,cx+221,6): pts.append((x,cy-90+j*48+int(18*math.sin((x-cx+j*18)/29))))
            draw.line(pts,fill=ACCENTS[(idx+j)%len(ACCENTS)],width=7)

def render_scene(beat: dict, index: int, total: int, out: Path, channel: str="FIELD NOTES") -> Path:
    """Draw original procedural scene art; does not download stock or copyrighted assets."""
    out.parent.mkdir(parents=True,exist_ok=True)
    gradient=Image.new("RGB",(1,H)); gradient_draw=ImageDraw.Draw(gradient)
    top=(13,22,46); bottom=(22,34,61)
    for y in range(H):
        t=y/(H-1); c=tuple(int(top[i]*(1-t)+bottom[i]*t) for i in range(3))
        gradient_draw.point((0,y),fill=c)
    img=gradient.resize((W,H),Image.Resampling.BILINEAR)
    draw=ImageDraw.Draw(img,"RGBA")
    seed=sum((i+1)*ord(ch) for i,ch in enumerate(beat["text"]))+index*199
    rng=random.Random(seed)
    for _ in range(70):
        x=rng.randrange(28,W-28); y=rng.randrange(140,H-180); r=rng.choice([2,3,4])
        draw.ellipse((x-r,y-r,x+r,y+r),fill=(146,178,230,rng.randrange(30,100)))
    accent=ACCENTS[index%len(ACCENTS)]
    _rounded(draw,(68,92,1012,106),7,(255,255,255,28))
    _rounded(draw,(68,92,68+int(944*(index+1)/total),106),7,(*accent,245))
    draw.text((72,135),channel.upper(),font=_font(27,True),fill=(172,192,227))
    draw.text((850,135),f"{index+1:02d} / {total:02d}",font=_font(24,True),fill=(172,192,227))
    cx,cy=540,670
    draw.ellipse((cx-260,cy-260,cx+260,cy+260),fill=(accent[0]//5,accent[1]//5,accent[2]//5,90))
    _draw_icon(draw,index,cx,cy,accent,rng," ".join([beat.get("text", ""),beat.get("visual_title", ""),beat.get("visual_note", "")]))
    headline=beat.get("visual_title") or "LOOK CLOSER"
    font=_font(63,True); lines=_fit_lines(draw,headline,font,900)
    yy=1040
    for line in lines[:3]:
        bbox=draw.textbbox((0,0),line,font=font); tw=bbox[2]-bbox[0]
        draw.text(((W-tw)//2,yy),line,font=font,fill=(247,250,255),stroke_width=1,stroke_fill=(247,250,255))
        yy += 82
    note=beat.get("visual_note","")
    note_font=_font(31); note_lines=_fit_lines(draw,note,note_font,850)
    yy=max(yy+16,1300)
    for line in note_lines[:4]:
        bbox=draw.textbbox((0,0),line,font=note_font); tw=bbox[2]-bbox[0]
        draw.text(((W-tw)//2,yy),line,font=note_font,fill=(183,201,228)); yy+=45
    draw.text((72,1778),"SCIENCE • TECH • EVERYDAY CURIOSITY",font=_font(23,True),fill=(137,160,199))
    draw.text((72,1825),"One minute. One useful idea.",font=_font(25),fill=(215,226,245))
    img.save(out,"PNG",optimize=True)
    return out
