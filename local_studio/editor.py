"""Optional speech transcription, AI commentary and FFmpeg Shorts editing.

Requires ffmpeg/ffprobe. Optional: faster-whisper, pyttsx3 and OPENAI_API_KEY.
AI commentary is based on user notes/transcript, NOT video understanding.
"""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

def run(args, timeout=480):
    p=subprocess.run(args,capture_output=True,text=True,errors="replace",timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"FFmpeg/tool error ({p.returncode}): {(p.stderr or p.stdout)[-1600:]}")
    return p.stdout

def duration(path):
    return float(run(["ffprobe","-v","error","-show_entries","format=duration",
                      "-of","default=noprint_wrappers=1:nokey=1",str(path)],30).strip())

def timestamp(seconds):
    ms=max(0,round(float(seconds)*1000))
    hours,ms=divmod(ms,3600000)
    minutes,ms=divmod(ms,60000)
    secs,ms=divmod(ms,1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"

def write_srt(segments,path,offset=0,limit=30):
    lines=[]
    for segment in segments:
        start=max(0,float(segment["start"])-offset)
        end=min(limit,float(segment["end"])-offset)
        text=re.sub(r"\\s+"," ",str(segment["text"])).strip()
        if end<=start or not text: continue
        lines.extend([str(len(lines)//4+1),f"{timestamp(start)} --> {timestamp(end)}",text,""])
    Path(path).write_text("\n".join(lines),encoding="utf-8-sig")
    return len(lines)//4

def transcribe(source,model_size="tiny"):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Automatic captions require: py -m pip install faster-whisper") from exc
    model=WhisperModel(model_size,device="cpu",compute_type="int8")
    segments,_=model.transcribe(str(source),beam_size=1,vad_filter=True)
    return [{"start":float(x.start),"end":float(x.end),"text":x.text.strip()} for x in segments]

def commentary(notes,transcript="",api_key=None):
    notes=(notes or "").strip()[:1500]
    transcript=(transcript or "").strip()[:2500]
    if not notes and not transcript:
        raise ValueError("Provide scene notes or a transcript to write relevant commentary.")
    if not api_key:
        return "Watch this GTA gameplay highlight! "+(notes or transcript[:120]).rstrip(".")+"! What would you do next?"
    import requests
    response=requests.post("https://api.openai.com/v1/chat/completions",
       headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"},
       json={"model":"gpt-4o-mini","messages":[
           {"role":"system","content":"Write an energetic, original, factual 1-2 sentence YouTube Shorts voiceover under 45 words. Use only the provided scene notes and transcript. Never invent events or claim to have seen the video."},
           {"role":"user","content":"Scene notes: "+notes+"\nTranscript: "+transcript}]},
       timeout=45)
    if not response.ok:
        raise RuntimeError(f"AI commentary API error HTTP {response.status_code}: {response.text[:300]}")
    return response.json()["choices"][0]["message"]["content"].strip()

def synthesize(text,destination):
    try:
        import pyttsx3
    except ImportError as exc:
        raise RuntimeError("Voiceover requires: py -m pip install pyttsx3") from exc
    engine=pyttsx3.init()
    engine.setProperty("rate",165)
    engine.save_to_file(text,str(destination))
    engine.runAndWait()
    engine.stop()
    if not Path(destination).exists() or Path(destination).stat().st_size<100:
        raise RuntimeError("Speech engine did not save a usable voiceover file.")
    return Path(destination)

def _filter_path(path):
    # FFmpeg filter parser: escape path separators, Windows drive colon, quotes and brackets.
    value=Path(path).resolve().as_posix()
    return value.replace("\\","/").replace(":","\\:").replace("'","\\'").replace("[","\\[").replace("]","\\]").replace(",","\\,")

def edit(source,destination,start=0,seconds=30,vertical=True,srt=None,
         voice=None,mute_source=False,title=""):
    source=Path(source).resolve()
    destination=Path(destination).resolve()
    if not source.is_file(): raise FileNotFoundError(source)
    total=duration(source)
    if float(start)<0 or total-float(start)<1: raise ValueError("Start time is outside the source video.")
    seconds=min(float(seconds),total-float(start))
    destination.parent.mkdir(parents=True,exist_ok=True)
    pending=destination.with_name(destination.stem+".pending.mp4")
    if pending.exists(): pending.unlink()
    vf=[]
    if vertical: vf+=["scale=480:854:force_original_aspect_ratio=increase","crop=480:854"]
    if srt:
        if not Path(srt).is_file(): raise FileNotFoundError(srt)
        vf.append("subtitles='"+_filter_path(srt)+"'")
    if title:
        safe=re.sub(r"[^A-Za-z0-9 ._-]","",title)[:50].replace("'","")
        if safe: vf.append("drawtext=text='"+safe+"':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=32:box=1:boxcolor=black@0.65:boxborderw=8")
    args=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y","-ss",str(start),"-i",str(source)]
    if voice: args+=["-i",str(Path(voice).resolve())]
    args+=["-t",str(seconds),"-map","0:v:0"]
    if voice: args+=["-map","1:a:0"]
    elif not mute_source: args+=["-map","0:a?"]
    if vf: args+=["-vf",",".join(vf)]
    args+=["-filter_threads","1","-threads","2","-c:v","libx264","-preset","ultrafast",
           "-crf","27","-pix_fmt","yuv420p"]
    if voice or not mute_source: args+=["-c:a","aac","-b:a","128k"]
    else: args+=["-an"]
    args+=["-movflags","+faststart",str(pending)]
    try:
        run(args,600)
        if not pending.exists() or pending.stat().st_size<1024: raise RuntimeError("No valid MP4 created.")
        actual=duration(pending)
        if actual<0.5 or abs(actual-seconds)>3: raise RuntimeError(f"Unexpected export duration {actual:.1f}s")
        pending.replace(destination)
        return destination
    finally:
        if pending.exists(): pending.unlink()
