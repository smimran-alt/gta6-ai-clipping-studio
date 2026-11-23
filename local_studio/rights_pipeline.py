"""Rights-aware local Shorts pipeline. Heuristic warnings are not copyright clearance."""
from __future__ import annotations
import hashlib
import json
import math
import re
import subprocess
import tempfile
import wave
from pathlib import Path

LOOKS={"Natural":"eq=contrast=1.06:saturation=1.10",
       "Vibrant":"eq=contrast=1.12:saturation=1.20",
       "Warm":"eq=contrast=1.07:saturation=1.12:gamma_r=1.06:gamma_b=0.96",
       "Cool":"eq=contrast=1.09:saturation=1.14:gamma_r=0.97:gamma_b=1.06",
       "Original":"null"}
VIDEO_EXT={".mp4",".mov",".mkv",".webm"}
AUDIO_EXT={".mp3",".wav",".m4a",".aac",".ogg",".flac"}

def run(args,timeout=600,binary=False):
    p=subprocess.run(args,capture_output=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError(p.stderr.decode("utf-8","replace")[-1300:])
    return p.stdout if binary else p.stdout.decode("utf-8","replace")

def probe(path):
    data=json.loads(run(["ffprobe","-v","error","-show_format","-show_streams",
                         "-of","json",str(path)],40))
    streams=data.get("streams",[])
    return {"duration":float(data.get("format",{}).get("duration",0)),
            "audio":any(s.get("codec_type")=="audio" for s in streams),
            "video":any(s.get("codec_type")=="video" for s in streams)}

def fingerprint_frames(path,limit=60):
    """Find nearly identical frames within this source, not matches to external works."""
    duration=min(probe(path)["duration"],limit)
    if duration<3:return []
    # Tiny grayscale frames are robust to encoding but NOT to copyright ownership.
    raw=run(["ffmpeg","-v","error","-nostdin","-i",str(path),"-t",str(duration),
             "-vf","fps=1,scale=16:16,format=gray","-f","rawvideo","-"],binary=True)
    hashes=[]
    for i in range(0,len(raw)-255,256):
        frame=raw[i:i+256]
        mean=sum(frame)/256
        bits=bytes(1 if x>mean else 0 for x in frame)
        hashes.append(bits)
    pairs=[]
    for i in range(len(hashes)):
        for j in range(i+4,len(hashes)):
            distance=sum(a!=b for a,b in zip(hashes[i],hashes[j]))
            if distance<=8:
                pairs.append({"at_seconds":i,"similar_to_seconds":j,"difference":distance})
                if len(pairs)>=5:return pairs
    return pairs

def watermark_review(path):
    """Inspect static corner regions for overlays. Does not identify owner or remove marks."""
    info=probe(path)
    if not info["video"]:return {"status":"no video"}
    # Sample 4 still frames and check stability of corner luminance.
    duration=info["duration"]
    samples=[]
    for t in [0.5,max(.5,duration*.25),max(.5,duration*.55),max(.5,duration*.8)]:
        try:
            raw=run(["ffmpeg","-v","error","-ss",str(t),"-i",str(path),
                     "-frames:v","1","-vf","scale=80:48,format=gray",
                     "-f","rawvideo","-"],timeout=30,binary=True)
            if len(raw)>=3840:samples.append(raw[:3840])
        except Exception:pass
    if len(samples)<3:return {"status":"insufficient samples","corners":[]}
    corners={"top-left":(0,0),"top-right":(64,0),"bottom-left":(0,32),"bottom-right":(64,32)}
    possible=[]
    for name,(x,y) in corners.items():
        indexes=[(y+dy)*80+x+dx for dy in range(16) for dx in range(16)]
        changes=sum(abs(samples[0][idx]-samples[k][idx]) for k in range(1,len(samples)) for idx in indexes)
        mean_change=changes/((len(samples)-1)*len(indexes))
        if mean_change<8:
            possible.append({"corner":name,"mean_frame_change":round(mean_change,1)})
    return {"status":"review suggested" if possible else "no static corner detected",
            "corners":possible,
            "warning":"Static corners can be scenery, borders, HUD or logos. No ownership inference."}

def scan(path):
    path=Path(path)
    if not path.is_file():raise FileNotFoundError(path)
    info=probe(path)
    if not info["video"]:raise ValueError("Source has no video")
    repeated=fingerprint_frames(path)
    overlays=watermark_review(path)
    warnings=["No copyright ownership or music license can be verified automatically.",
              "Music recognition requires an external reference catalog; audio presence alone does not prove infringement."]
    if info["audio"]:
        warnings.append("Audio track detected: verify music, effects, dialogue and recording rights before publishing.")
    if repeated:
        warnings.append("Similar frames found within this clip; this does NOT establish third-party reuse.")
    if overlays.get("corners"):
        warnings.append("Some corners remain visually static; review for possible overlays or watermarks.")
    return {"source":str(path),"duration":info["duration"],"has_audio":info["audio"],
            "repeated_frames":repeated,"watermark_review":overlays,"warnings":warnings}

def subtitles_for_segment(source,destination,model="tiny"):
    from editor import transcribe,write_srt
    segs=transcribe(source,model_size=model)
    return write_srt(segs,destination,offset=0,limit=30)

def _escaped(path):
    return str(Path(path).resolve()).replace("\\","/").replace(":","\\:").replace("'","\\'").replace(",","\\,")

def render(source,destination,look="Natural",licensed_music=None,voice=None,
           srt=None,fade=True,vertical=True,landscape=False):
    """Replace source audio by default. Optional licensed track and voice mix."""
    source=Path(source).resolve()
    destination=Path(destination).resolve()
    if look not in LOOKS:raise ValueError("Invalid look")
    if not source.is_file():raise FileNotFoundError(source)
    info=probe(source)
    seconds=min(30,info["duration"])
    if seconds<25:raise ValueError("Source shorter than 25 seconds")
    for p in [licensed_music,voice,srt]:
        if p and not Path(p).is_file():raise FileNotFoundError(p)
    destination.parent.mkdir(parents=True,exist_ok=True)
    pending=destination.with_name(destination.stem+".pending.mp4")
    pending.unlink(missing_ok=True)
    args=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
          "-i",str(source)]
    audio_inputs=[]
    for item in [licensed_music,voice]:
        if item:
            args+=["-stream_loop","-1","-i",str(item)]
            audio_inputs.append(len(audio_inputs)+1)
    vf=[]
    if landscape:
        vf+=["scale=1280:720:force_original_aspect_ratio=decrease","pad=1280:720:(ow-iw)/2:(oh-ih)/2"]
    elif vertical:
        vf+=["scale=480:854:force_original_aspect_ratio=increase","crop=480:854"]
    vf.append(LOOKS[look])
    if srt:vf.append("subtitles='"+_escaped(srt)+"'")
    if fade:vf+=["fade=t=in:st=0:d=0.35",f"fade=t=out:st={max(0,seconds-.35):.2f}:d=0.35"]
    args+=["-t",str(seconds),"-vf",",".join(vf),"-map","0:v:0"]
    if licensed_music and voice:
        args+=["-filter_complex",
               "[1:a]volume=0.16[m];[2:a]volume=1.0[v];[m][v]amix=inputs=2:duration=first:dropout_transition=0[a]",
               "-map","[a]"]
    elif licensed_music:args+=["-map","1:a:0","-af","volume=0.25"]
    elif voice:args+=["-map","1:a:0"]
    else:args+=["-an"]
    args+=["-threads","2","-filter_threads","1","-c:v","libx264",
           "-preset","ultrafast","-crf","26","-pix_fmt","yuv420p"]
    if licensed_music or voice:args+=["-c:a","aac","-b:a","128k"]
    args+=["-movflags","+faststart",str(pending)]
    try:
        run(args)
        if not pending.exists() or pending.stat().st_size<1024:raise RuntimeError("No output created")
        measured=probe(pending)["duration"]
        if abs(measured-seconds)>2:raise RuntimeError("Unexpected output duration")
        pending.replace(destination)
        return destination
    finally:
        pending.unlink(missing_ok=True)
