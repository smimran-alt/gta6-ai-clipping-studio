"""Produce 60-second vertical commentary clips from explicitly authorized media.

Reads sources/approved.json. Each entry must include title, url, rights_basis,
permission_evidence, and a list of original, segment-specific commentaries.
No YouTube scraping, automated rights assumptions, or publication.
"""
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

from studio import ROOT, OUT, download

def cmd(args):
    subprocess.run(args,check=True,timeout=300,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)

def duration(path):
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries",
        "format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],text=True).strip())

def main():
    approved=ROOT/"sources"/"approved.json"
    data=json.loads(approved.read_text(encoding="utf-8"))
    results={"clips":[],"skipped":[],"review_required":True,
             "notice":"Transformation does not guarantee copyright clearance. Review before publishing."}
    target=OUT/"commentary_shorts"
    target.mkdir(parents=True,exist_ok=True)
    for n,entry in enumerate(data.get("sources",[]),1):
        title=entry.get("title","Untitled")
        basis=str(entry.get("rights_basis","")).strip().lower()
        evidence=str(entry.get("permission_evidence","")).strip()
        segments=entry.get("commentary_segments",[])
        if basis in {"","unknown","public","fair use","none"} or not evidence or not isinstance(segments,list) or not segments:
            results["skipped"].append({"title":title,"reason":"Rights evidence and original segment-specific commentary required"})
            continue
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp=Path(tmp)
                src=tmp/"source.mp4"
                download(entry["url"],src)
                total=duration(src)
                count=math.ceil(total/60)
                for i in range(count):
                    if i>=len(segments) or not isinstance(segments[i],str) or len(segments[i].strip())<100:
                        results["skipped"].append({"title":title,"segment":i+1,"reason":"Missing substantive commentary for this minute"})
                        continue
                    start=i*60
                    length=min(60,total-start)
                    if length<1: continue
                    voice=tmp/f"voice_{i}.wav"
                    cmd(["espeak-ng","-v","en-us","-s","165","-w",str(voice),segments[i]])
                    label=re.sub(r"[^A-Za-z0-9 .,!?'\-]","",title)[:55]
                    caption=re.sub(r"[^A-Za-z0-9 .,!?'\-]","",segments[i])[:180]
                    titlefile=tmp/f"title_{i}.txt"
                    captionfile=tmp/f"caption_{i}.txt"
                    titlefile.write_text(label,encoding="utf-8")
                    captionfile.write_text(caption,encoding="utf-8")
                    vf=("scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
                        "drawbox=x=0:y=50:w=iw:h=135:color=black@0.7:t=fill,"
                        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:textfile={titlefile}:fontcolor=white:fontsize=30:x=(w-text_w)/2:y=92,"
                        "drawbox=x=0:y=1030:w=iw:h=220:color=black@0.7:t=fill,"
                        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:textfile={captionfile}:fontcolor=white:fontsize=22:x=25:y=1060:fix_bounds=1")
                    out=target/f"source_{n:02d}_minute_{i+1:03d}.mp4"
                    # Source audio deliberately excluded; voice narration is the only audio.
                    cmd(["ffmpeg","-hide_banner","-loglevel","error","-y",
                        "-ss",str(start),"-i",str(src),"-i",str(voice),
                        "-t",str(length),"-filter_complex",f"[0:v]{vf}[v]",
                        "-map","[v]","-map","1:a:0","-c:v","libx264","-preset","veryfast",
                        "-crf","26","-pix_fmt","yuv420p","-c:a","aac","-af","apad",
                        "-shortest","-movflags","+faststart",str(out)])
                    results["clips"].append({"title":title,"file":out.name,"minute":i+1,
                        "status":"REVIEW RIGHTS AND CONTENT BEFORE PUBLISHING"})
        except Exception as exc:
            results["skipped"].append({"title":title,"reason":str(exc)})
    (OUT/"commentary_shorts_report.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    print(json.dumps({"created":len(results["clips"]),"skipped":len(results["skipped"])},indent=2))

if __name__=="__main__":
    main()
