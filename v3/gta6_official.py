"""GTA VI-only Rockstar official video clipper.

Streams portions of Rockstar's official MP4 using HTTP range requests via FFmpeg,
avoiding a 14 GB full download. Availability depends on CDN range support.
Original source remains Rockstar copyright. Commentary is not scene-aware.
"""
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

from auto_clips import OUT, DEST, create_clip

SOURCE="https://media-rockstargames-com.akamaized.net/VI/downloads/videos/GTAVI_An_Extended_Look/GTAVI_An_Extended_Look.mp4"
TITLE="Grand Theft Auto VI: An Extended Look (Official Rockstar Games)"

def command(args,timeout=150):
    return subprocess.run(args,check=True,timeout=timeout,capture_output=True,text=True).stdout.strip()

def main():
    report={"version":"3.2","source":SOURCE,"title":TITLE,"clips":[],"errors":[],
        "status":"not_started","copyright":"Rockstar Games footage; downloading does not grant redistribution permission",
        "commentary":"Generic English narration, not scene-aware"}
    try:
        # Remote ffprobe may fail if CDN disallows range requests.
        duration=float(command(["ffprobe","-v","error","-show_entries","format=duration",
            "-of","default=noprint_wrappers=1:nokey=1",SOURCE],timeout=90))
        total=math.ceil(duration/60)
        max_minutes=max(1,min(60,int(os.getenv("GTA6_MAX_MINUTES","30"))))
        count=min(total,max_minutes)
        folder=DEST/"gta6_extended_look"
        folder.mkdir(parents=True,exist_ok=True)
        for i in range(count):
            length=min(60,duration-i*60)
            if length<1: break
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    segment=Path(tmp)/"segment.mp4"
                    # Seek before input: CDN must support byte-range requests.
                    command(["ffmpeg","-hide_banner","-loglevel","error","-y",
                        "-ss",str(i*60),"-i",SOURCE,"-t",str(length),
                        "-map","0:v:0","-an","-c:v","libx264","-preset","ultrafast",
                        "-crf","30","-vf","scale=-2:720","-movflags","+faststart",
                        str(segment)],timeout=240)
                    result=create_clip(segment,TITLE,0,1,length,folder)
                    # create_clip writes clip_001.mp4; rename to minute number.
                    previous=folder/"clip_001.mp4"
                    renamed=folder/f"clip_{i+1:03d}.mp4"
                    previous.rename(renamed)
                    result["file"]=str(renamed.relative_to(OUT))
                    result["minute"]=i+1
                    report["clips"].append(result)
            except Exception as exc:
                report["errors"].append({"minute":i+1,"error":str(exc)[:350]})
                # Stop on first failure to avoid repeated CDN errors.
                break
        report["duration_seconds"]=duration
        report["status"]="clips_created_review_before_publication" if report["clips"] else "no_clips_created"
    except Exception as exc:
        report["status"]="source_unavailable"
        report["errors"].append(str(exc)[:500])
    (OUT/"gta6_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"status":report["status"],"clips":len(report["clips"]),
        "errors":report["errors"]},indent=2))

if __name__=="__main__":
    main()
