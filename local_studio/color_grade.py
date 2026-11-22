"""Non-destructive color grading for authorized video clips."""
from pathlib import Path
import subprocess

PRESETS={
    "Natural cinematic":"eq=contrast=1.07:brightness=0.01:saturation=1.10:gamma=1.02",
    "Vibrant GTA":"eq=contrast=1.12:brightness=0.015:saturation=1.20:gamma=1.02",
    "Warm sunset":"eq=contrast=1.07:saturation=1.13:gamma_r=1.07:gamma_b=0.96",
    "Cool neon":"eq=contrast=1.10:saturation=1.16:gamma_r=0.97:gamma_b=1.07",
    "Original":"null",
}

def grade(source,destination,preset="Natural cinematic"):
    if preset not in PRESETS: raise ValueError("Unknown color preset")
    source=Path(source).resolve()
    destination=Path(destination).resolve()
    if not source.is_file(): raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True,exist_ok=True)
    pending=destination.with_name(destination.stem+".pending.mp4")
    pending.unlink(missing_ok=True)
    args=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
          "-i",str(source),"-vf",PRESETS[preset],"-map","0:v:0","-map","0:a?",
          "-c:v","libx264","-preset","ultrafast","-crf","25",
          "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
          "-movflags","+faststart",str(pending)]
    try:
        result=subprocess.run(args,capture_output=True,text=True,timeout=480)
        if result.returncode: raise RuntimeError(result.stderr[-1400:])
        if not pending.exists() or pending.stat().st_size<1024:
            raise RuntimeError("Color-graded video was not created")
        from editor import duration
        if abs(duration(pending)-duration(source))>2:
            raise RuntimeError("Graded video duration did not match original")
        pending.replace(destination)
        return destination
    finally:
        pending.unlink(missing_ok=True)
