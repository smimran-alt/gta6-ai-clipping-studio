"""GTA Studio v3: search-result video -> 60s vertical narrated MP4s.

Uses the ranked discovery file. Public YouTube downloads are best effort; some
sites block automated access. Original voiceover is based on verified title and
clip position, NOT on visual scene understanding. No copyright clearance implied.
"""
import csv
import json
import math
import os
import re
import subprocess
import tempfile
from pathlib import Path

import yt_dlp

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output"
DEST=OUT/"v3_clips"
DEST.mkdir(parents=True,exist_ok=True)

def run(args, timeout=240):
    return subprocess.run(args,check=True,timeout=timeout,capture_output=True,text=True).stdout.strip()

def candidates():
    path=OUT/"ranked_by_comments.csv"
    if not path.exists(): return []
    with path.open(newline="",encoding="utf-8") as f: rows=list(csv.DictReader(f))
    gta=re.compile(r"(?i)(grand theft auto|\\bgta\\s*(?:6|vi|5|v|4|iv|san andreas|vice city|online)\\b)")
    unwanted=re.compile(r"(?i)(trailer|teaser|reaction|review|news|soundtrack|music video)")
    return [x for x in rows if gta.search(x.get("title","")) and not unwanted.search(x.get("title",""))]

def script_for(title, index, count):
    # Original neutral narration; do not pretend to identify events without video analysis.
    clean=re.sub(r"[^a-zA-Z0-9 ,.!?'-]","",title)[:90]
    parts=[
        f"Welcome to our GTA gameplay breakdown. The source video is titled {clean}. This is minute {index+1} of {count}.",
        "Watch the driving, camera movement, and how the player navigates the game world.",
        "Pay attention to the choices made during this part of the run, and decide what you would try differently.",
        "This is an original narrated segment, not a claim about specific actions we have not verified.",
        "If you enjoyed this minute, continue to the next segment for more gameplay."
    ]
    return " ".join(parts)

def create_clip(src, title, index, count, length, folder):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp=Path(tmpdir)
        voice=tmp/"narration.wav"
        caption=tmp/"caption.txt"
        heading=tmp/"heading.txt"
        narration=script_for(title,index,count)
        run(["espeak-ng","-v","en-us","-s","170","-w",str(voice),narration],timeout=45)
        heading.write_text(f"GTA GAMEPLAY | PART {index+1}/{count}",encoding="utf-8")
        caption.write_text("ORIGINAL GAMEPLAY COMMENTARY",encoding="utf-8")
        font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        vf=(f"scale=480:854:force_original_aspect_ratio=increase,crop=480:854,"
            f"drawbox=x=0:y=45:w=iw:h=95:color=black@0.7:t=fill,"
            f"drawtext=fontfile={font}:textfile={heading}:fontcolor=white:fontsize=21:x=(w-text_w)/2:y=77,"
            f"drawbox=x=0:y=730:w=iw:h=80:color=black@0.7:t=fill,"
            f"drawtext=fontfile={font}:textfile={caption}:fontcolor=white:fontsize=17:x=(w-text_w)/2:y=760")
        dest=folder/f"clip_{index+1:03d}.mp4"
        # Original soundtrack excluded; voiceover fills the full clip using apad.
        run(["ffmpeg","-hide_banner","-loglevel","error","-y",
             "-ss",str(index*60),"-i",str(src),"-i",str(voice),"-t",str(length),
             "-filter_complex",f"[0:v]{vf}[v]","-map","[v]","-map","1:a:0",
             "-c:v","libx264","-preset","ultrafast","-crf","28","-pix_fmt","yuv420p",
             "-c:a","aac","-b:a","96k","-af","apad","-shortest",
             "-movflags","+faststart",str(dest)],timeout=240)
        return {"file":str(dest.relative_to(OUT)),"minute":index+1,"duration_seconds":round(length,2),
                "narration":narration}

def main():
    report={"version":"3.0","status":"not_started","videos":[],"errors":[],
            "commentary_basis":"Title and minute number only; no visual scene understanding",
            "rights":"Review source rights and resulting videos before reuse or publication"}
    try:
        rows=candidates()
        report["candidates"]=len(rows)
        if not rows:
            report["errors"].append("No GTA gameplay candidates in ranked_by_comments.csv")
        for row in rows[:8]:
            url=row["url"]
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp=Path(tmpdir)
                    template=str(tmp/"gameplay.%(ext)s")
                    opts={"format":"best[height<=720][ext=mp4]/best[height<=720]/best",
                          "outtmpl":template,"noplaylist":True,"quiet":True,
                          "no_warnings":True,"socket_timeout":20,
                          "retries":2,"fragment_retries":2,"max_filesize":400*1024*1024,
                          "merge_output_format":"mp4"}
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info=ydl.extract_info(url,download=True)
                        file=Path(ydl.prepare_filename(info))
                    if not file.exists():
                        matches=list(tmp.glob("gameplay.*"))
                        if not matches: raise RuntimeError("Downloader returned no playable file")
                        file=matches[0]
                    seconds=float(run(["ffprobe","-v","error","-show_entries","format=duration",
                                       "-of","default=noprint_wrappers=1:nokey=1",str(file)]))
                    max_minutes=int(os.getenv("V3_MAX_MINUTES","30"))
                    count=min(math.ceil(seconds/60),max_minutes)
                    if count<1: raise RuntimeError("No video duration")
                    folder=DEST/"video_01"
                    folder.mkdir(parents=True,exist_ok=True)
                    clips=[]
                    for i in range(count):
                        clips.append(create_clip(file,info.get("title") or row["title"],i,count,
                                                 min(60,seconds-i*60),folder))
                    report["videos"].append({"source_url":url,"title":info.get("title"),
                        "duration_seconds":seconds,"clips":clips})
                    report["status"]="clips_created_review_before_publication"
                    break
            except Exception as exc:
                report["errors"].append({"url":url,"error":str(exc)[:500]})
        if not report["videos"]: report["status"]="no_downloadable_source"
    except Exception as exc:
        report["status"]="failed"
        report["errors"].append(str(exc))
    (OUT/"v3_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"status":report["status"],"videos":len(report["videos"]),
        "clips":sum(len(x["clips"]) for x in report["videos"]),"errors":report["errors"]},indent=2))
    if not report["videos"]:\n        print("No MP4 clips produced. YouTube may require authentication; see output/v3_report.json")

if __name__=="__main__":
    main()
