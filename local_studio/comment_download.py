"""Download a requested 30-second source interval when supported by host/yt-dlp.

Only call after explicit permission confirmation. Never silently download full
videos if range fetching fails.
"""
from pathlib import Path
import os
import shutil
import tempfile

import yt_dlp

def download_range(url,start,output_dir,quality=360,max_mb=500):
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        template=str(Path(temp)/"segment.%(ext)s")
        opts={"format":f"bv*[height<={quality}]+ba/b[height<={quality}]/b",
              "merge_output_format":"mp4","outtmpl":template,"noplaylist":True,
              "max_filesize":int(max_mb)*1024*1024,
              "download_ranges":yt_dlp.utils.download_range_func(None,[(float(start),float(start)+30.0)]),
              "force_keyframes_at_cuts":True,"external_downloader":"ffmpeg"}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info=ydl.extract_info(url,download=False)
            if not info: raise RuntimeError("Video metadata unavailable")
            duration=info.get("duration")
            if duration and float(start)+30>float(duration):
                raise ValueError("Selected interval exceeds the video duration")
            ydl.download([url])
        files=[p for p in Path(temp).glob("segment*") if p.suffix.lower() in
               (".mp4",".webm",".mkv",".mov") and p.is_file()]
        if not files: raise RuntimeError("No 30-second video saved; host may block range downloads")
        candidate=max(files,key=lambda p:p.stat().st_size)
        if candidate.stat().st_size>int(max_mb)*1024*1024:
            raise RuntimeError("Downloaded file exceeds configured size limit")
        target=output_dir/f"most_discussed_{int(start):06d}s{candidate.suffix.lower()}"
        pending=output_dir/f"most_discussed_{int(start):06d}s.pending{candidate.suffix.lower()}"
        shutil.copy2(candidate,pending)
        # Validate duration and refuse full-video downloads.
        from editor import duration as video_duration
        measured=video_duration(pending)
        if not 25<=measured<=33:
            pending.unlink(missing_ok=True)
            raise RuntimeError(f"Downloaded interval is {measured:.1f}s, not approximately 30s. Full video was not accepted.")
        os.replace(pending,target)
        return target

def download_batch(url,moments,output_dir,quality=360,max_mb=500):
    """Try independent range downloads; if some fail, optionally fetch a bounded full
    source once and cut missing windows locally. Return each clip's status.
    Never present failed downloads as successful.
    """
    from editor import edit, duration as video_duration
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    results=[]
    for index,moment in enumerate(moments,1):
        start=int(moment["start"])
        target=output_dir/f"clip_{index:02d}_{start:06d}s.mp4"
        try:
            downloaded=download_range(url,start,output_dir,quality=quality,max_mb=max_mb)
            # Remux to consistent MP4 and unique clip filename.
            edit(downloaded,target,start=0,seconds=30,vertical=False)
            if not 27<=video_duration(target)<=31:
                raise RuntimeError("Rendered segment duration is not approximately 30 seconds")
            from rights_pipeline import probe
            info=probe(target)
            results.append({"clip":index,"start":start,"end":start+30,
                            "timestamp_mentions":moment["timestamped_comments"],
                            "status":"saved","file":str(target),
                            "actual_size_MB":round(target.stat().st_size/1048576,1),
                            "actual_seconds":round(info["duration"],1)})
        except Exception as exc:
            results.append({"clip":index,"start":start,"end":start+30,
                            "timestamp_mentions":moment["timestamped_comments"],
                            "status":"failed","error":str(exc)[:300]})
    # Full source fallback is intentionally disabled: it may download large copyrighted
    # videos unexpectedly. Show failures rather than falsely claiming five clips.
    return results
