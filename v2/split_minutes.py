"""Split an authorized local video into consecutive one-minute MP4 segments.

Usage: python v2/split_minutes.py path/to/video.mp4
Optional: --output output/minute_clips --seconds 60
Requires ffmpeg and ffprobe. Never downloads videos from YouTube.
"""
import argparse
import json
import math
import subprocess
from pathlib import Path

def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()

def main():
    p=argparse.ArgumentParser(description="Split a locally available, authorized video into one-minute clips.")
    p.add_argument("video",type=Path)
    p.add_argument("--output",type=Path,default=Path("output/minute_clips"))
    p.add_argument("--seconds",type=int,default=60)
    a=p.parse_args()
    if a.seconds<=0: p.error("--seconds must be positive")
    if not a.video.is_file(): p.error("Video file not found: "+str(a.video))
    a.output.mkdir(parents=True,exist_ok=True)
    duration=float(run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=noprint_wrappers=1:nokey=1",str(a.video)]))
    if duration<=0: p.error("Video duration must be positive")
    manifest=[]
    for index in range(math.ceil(duration/a.seconds)):
        start=index*a.seconds
        length=min(a.seconds,duration-start)
        if length<0.05: break
        target=a.output/f"clip_{index+1:03d}.mp4"
        # Re-encode so cuts are frame-accurate and files are independently playable.
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
            "-ss",str(start),"-i",str(a.video),"-t",str(length),
            "-map","0:v:0","-map","0:a?","-c:v","libx264","-preset","veryfast",
            "-crf","23","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
            "-movflags","+faststart",str(target)],check=True)
        manifest.append({"file":target.name,"start_seconds":start,"duration_seconds":round(length,3)})
        print(f"{target}: {start:.1f}s - {start+length:.1f}s")
    (a.output/"manifest.json").write_text(json.dumps({"source":a.video.name,
        "source_duration_seconds":duration,"clip_length_seconds":a.seconds,
        "clips":manifest},indent=2),encoding="utf-8")
    print(f"Created {len(manifest)} clips in {a.output}")

if __name__=="__main__":
    main()
