"""Optional localized logo-area blur for footage the user owns or can modify.

The original clip remains untouched. A blur cannot reconstruct hidden pixels.
"""
import subprocess
from pathlib import Path

def blur_region(source,destination,x_pct=80,y_pct=2,w_pct=18,h_pct=14):
    source=Path(source).resolve()
    destination=Path(destination).resolve()
    if not source.is_file(): raise FileNotFoundError(source)
    probe=subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
                          "-show_entries","stream=width,height","-of","csv=p=0",
                          str(source)],capture_output=True,text=True,check=True)
    width,height=(int(v) for v in probe.stdout.strip().split(",")[:2])
    x=max(0,min(width-4,int(width*x_pct/100)))
    y=max(0,min(height-4,int(height*y_pct/100)))
    w=max(2,min(width-x,int(width*w_pct/100)))
    h=max(2,min(height-y,int(height*h_pct/100)))
    # Crop the selected area, blur it, overlay it at the original position.
    vf=f"[0:v]split=2[base][part];[part]crop={w}:{h}:{x}:{y},boxblur=10:1[blur];[base][blur]overlay={x}:{y}[out]"
    destination.parent.mkdir(parents=True,exist_ok=True)
    pending=destination.with_name(destination.stem+".pending.mp4")
    args=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
          "-i",str(source),"-filter_complex",vf,"-map","[out]","-map","0:a?",
          "-c:v","libx264","-preset","ultrafast","-crf","26",
          "-c:a","aac","-movflags","+faststart",str(pending)]
    try:
        result=subprocess.run(args,capture_output=True,text=True,timeout=480)
        if result.returncode: raise RuntimeError(result.stderr[-1200:])
        if not pending.exists() or pending.stat().st_size<1024:
            raise RuntimeError("Blurred output is missing or empty")
        from editor import duration
        if abs(duration(pending)-duration(source))>2:
            raise RuntimeError("Edited clip duration differs from original")
        pending.replace(destination)
        return destination
    finally:
        pending.unlink(missing_ok=True)
