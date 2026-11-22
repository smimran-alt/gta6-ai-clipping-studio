"""Local, explainable GTA gameplay highlight suggestions.

Uses FFmpeg scene-change signals and soundtrack loudness; it does NOT recognize
cars, explosions, police, or gameplay semantics. No cloud API or model required.
"""
from __future__ import annotations
import json
import math
import re
import struct
import subprocess
from pathlib import Path

CLIP_SECONDS=30
STEP_SECONDS=10
MAX_ANALYSIS_SECONDS=1200

def _run(args, timeout=240):
    result=subprocess.run(args, capture_output=True, timeout=timeout)
    if result.returncode:
        err=result.stderr.decode("utf-8","replace")[-1500:]
        raise RuntimeError(f"FFmpeg command failed ({result.returncode}): {err}")
    return result

def probe_duration(source):
    result=_run(["ffprobe","-v","error","-show_entries","format=duration",
                 "-of","default=noprint_wrappers=1:nokey=1",str(source)],timeout=25)
    return float(result.stdout.decode().strip())

def detect_scene_changes(source, seconds):
    # 2 fps analysis reduces processing; changes reflect visual cuts/motion, not meaning.
    result=_run(["ffmpeg","-hide_banner","-nostdin","-i",str(source),
                 "-t",str(seconds),"-vf",
                 "fps=2,select='gt(scene,0.28)',showinfo",
                 "-an","-f","null","-"],timeout=480)
    stderr=result.stderr.decode("utf-8","replace")
    times=[]
    for match in re.finditer(r"pts_time:([0-9.]+)",stderr):
        t=float(match.group(1))
        if 0<=t<seconds: times.append(t)
    return times

def audio_energy(source, seconds):
    # Decode low-bandwidth PCM for transparent per-second RMS. No numpy dependency.
    result=_run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin",
                 "-i",str(source),"-t",str(seconds),"-vn","-ac","1","-ar","2000",
                 "-f","s16le","-"],timeout=360)
    data=result.stdout
    rate=2000
    levels=[]
    for i in range(0,len(data),rate*2):
        chunk=data[i:i+rate*2]
        if len(chunk)<2: break
        samples=struct.iter_unpack("<h",chunk[:len(chunk)//2*2])
        sq=sum(value[0]*value[0] for value in samples)
        count=len(chunk)//2
        levels.append(math.sqrt(sq/max(count,1))/32768)
    return levels

def rank_windows(duration, scenes, levels, count=5, clip_seconds=CLIP_SECONDS, step=STEP_SECONDS):
    usable=min(float(duration),float(MAX_ANALYSIS_SECONDS))
    if usable<clip_seconds:
        return []
    starts=list(range(0,int(usable-clip_seconds)+1,step))
    final=int(usable-clip_seconds)
    if final not in starts: starts.append(final)
    candidates=[]
    for start in starts:
        end=start+clip_seconds
        changes=sum(start<=t<end for t in scenes)
        energy=levels[int(start):min(len(levels),int(end))]
        avg=sum(energy)/len(energy) if energy else 0
        peak=max(energy) if energy else 0
        # Loudness and cut frequency are heuristics, not popularity predictions.
        visual=min(changes/8,1)
        audio=min(avg/0.16,1)
        burst=min(peak/0.30,1)
        score=round(100*(0.55*visual+0.30*audio+0.15*burst),1)
        candidates.append({"start":start,"end":end,"score":score,
                           "scene_changes":changes,"average_audio":round(avg,4),
                           "peak_audio":round(peak,4)})
    candidates.sort(key=lambda item:(-item["score"],item["start"]))
    selected=[]
    for item in candidates:
        if all(abs(item["start"]-other["start"])>=clip_seconds for other in selected):
            selected.append(item)
            if len(selected)>=count: break
    return selected

def analyze(source, count=5):
    source=Path(source).resolve()
    if not source.is_file(): raise FileNotFoundError(source)
    duration=probe_duration(source)
    analyzed=min(duration,MAX_ANALYSIS_SECONDS)
    if analyzed<CLIP_SECONDS:
        raise ValueError("Source must be at least 30 seconds long for a 30-second recommendation.")
    scenes=detect_scene_changes(source,analyzed)
    try:
        levels=audio_energy(source,analyzed)
        audio_note="Audio analyzed"
    except RuntimeError as exc:
        # Silent sources still get scene-based suggestions.
        levels=[]
        audio_note="No readable audio; visual scene changes only"
    results=rank_windows(analyzed,scenes,levels,count=count)
    return {"source":str(source),"source_duration":duration,
            "analyzed_seconds":analyzed,"clip_seconds":CLIP_SECONDS,
            "method":"scene changes and audio loudness heuristics",
            "limitations":"Not semantic event detection; scores do not predict virality",
            "audio_status":audio_note,"recommendations":results}

def export_clip(source, start, destination, vertical=True):
    source=Path(source).resolve()
    destination=Path(destination).resolve()
    destination.parent.mkdir(parents=True,exist_ok=True)
    temp=destination.with_name(destination.stem+".pending.mp4")
    if temp.exists(): temp.unlink()
    filters=["scale=480:854:force_original_aspect_ratio=increase","crop=480:854"] if vertical else []
    args=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
          "-ss",str(start),"-i",str(source),"-t",str(CLIP_SECONDS),
          "-map","0:v:0","-map","0:a?"]
    if filters: args+=["-vf",",".join(filters)]
    args+=["-threads","2","-filter_threads","1","-c:v","libx264",
           "-preset","ultrafast","-crf","28","-pix_fmt","yuv420p",
           "-c:a","aac","-b:a","128k","-movflags","+faststart",str(temp)]
    try:
        _run(args,timeout=480)
        if not temp.exists() or temp.stat().st_size<1024:
            raise RuntimeError("No usable MP4 was created")
        duration=probe_duration(temp)
        if not 27<=duration<=31:
            raise RuntimeError(f"Rendered clip is {duration:.1f}s, expected about 30s")
        temp.replace(destination)
        return destination
    finally:
        if temp.exists(): temp.unlink()
