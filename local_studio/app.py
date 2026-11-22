"""Local GTA VI clipping studio: search, review, download authorized footage, split and narrate.
Run: streamlit run local_studio/app.py
Requires ffmpeg/ffprobe in PATH. Video download is opt-in and requires rights confirmation.
"""
import csv
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
import yt_dlp

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"local_output"
OUT.mkdir(exist_ok=True)

def is_gta6(text):
    return bool(re.search(r"(?i)(\bgta\s*(?:6|vi)\b|grand theft auto\s*(?:6|vi)\b)",text or ""))

def search(query,limit):
    with yt_dlp.YoutubeDL({"quiet":True,"no_warnings":True,"extract_flat":"in_playlist",
                           "skip_download":True,"socket_timeout":15}) as ydl:
        info=ydl.extract_info(f"ytsearch{limit}:{query}",download=False)
    results=[]
    for entry in (info or {}).get("entries",[]):
        if not entry: continue
        title=entry.get("title") or ""
        if not is_gta6(title): continue
        vid=entry.get("id")
        if not vid: continue
        results.append({"title":title,"url":"https://www.youtube.com/watch?v="+vid,
                        "comments":None,"views":entry.get("view_count"),"duration":entry.get("duration")})
    return results

def enrich(rows):
    for item in rows:
        try:
            with yt_dlp.YoutubeDL({"quiet":True,"no_warnings":True,"skip_download":True,
                                   "noplaylist":True,"socket_timeout":12}) as ydl:
                meta=ydl.extract_info(item["url"],download=False)
            if meta:
                item["comments"]=meta.get("comment_count")
                item["views"]=meta.get("view_count")
                item["duration"]=meta.get("duration")
        except Exception:
            pass
    return sorted(rows,key=lambda r:(r["comments"] is None,-(r["comments"] or 0),
                                      -(r["views"] or 0)))

def command(args,timeout=300):
    return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout).stdout.strip()

def length(path):
    return float(command(["ffprobe","-v","error","-show_entries","format=duration",
                          "-of","default=noprint_wrappers=1:nokey=1",str(path)]))

def process(source, title, minutes, narration, vertical):
    folder=OUT/"clips"
    folder.mkdir(parents=True,exist_ok=True)
    for old in folder.glob("clip_*.mp4"): old.unlink()
    duration=length(source)
    count=min((int(duration+59.999)//60),minutes)
    if count==0: raise RuntimeError("Video is shorter than one second")
    files=[]
    for i in range(count):
        segment_length=min(60,duration-i*60)
        out=folder/f"clip_{i+1:03d}.mp4"
        with tempfile.TemporaryDirectory() as tmp:
            audio=Path(tmp)/"voice.wav"
            if narration:
                script=(f"GTA six gameplay. Segment {i+1} of {count}. "
                        "Watch the gameplay and notice the environment, driving and player decisions. "
                        "What would you do differently in this moment? "
                        "Continue watching to see the next part of this gameplay.")
                if shutil.which("espeak-ng"):
                    command(["espeak-ng","-v","en-us","-s","155","-w",str(audio),script])
                elif shutil.which("espeak"):
                    command(["espeak","-v","en-us","-s","155","-w",str(audio),script])
                else:
                    raise RuntimeError("Install eSpeak NG to generate voice commentary.")
            vf=["scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280"] if vertical else []
            vf.append(f"drawtext=text='GTA 6 - PART {i+1}':fontcolor=white:fontsize=38:x=(w-text_w)/2:y=40:box=1:boxcolor=black@0.65:boxborderw=12")
            args=["ffmpeg","-hide_banner","-loglevel","error","-y","-ss",str(i*60),"-i",str(source)]
            if narration: args+=["-i",str(audio)]
            args+=["-t",str(segment_length),"-vf",",".join(vf),"-map","0:v:0"]
            if narration: args+=["-map","1:a:0","-af","apad"]
            else: args+=["-map","0:a?"]
            args+=["-c:v","libx264","-preset","veryfast","-crf","25","-pix_fmt","yuv420p",
                   "-c:a","aac","-b:a","128k","-movflags","+faststart",str(out)]
            command(args,timeout=420)
        files.append(out)
    manifest={"source":title,"source_duration":duration,"clips":[x.name for x in files],
              "commentary":"Generic original voice, not scene-aware; review before publication"}
    (folder/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return files

st.set_page_config(page_title="GTA 6 AI Clipping Studio - Local",page_icon="🎬",layout="wide")
st.title("🎬 GTA 6 Clipping Studio — Local")
st.caption("Find GTA VI videos, rank by available comments, then generate 60-second MP4 clips. No Google API key.")
if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
    st.error("FFmpeg and ffprobe are not installed or not in PATH. Install FFmpeg before processing.")
query=st.text_input("Search YouTube",value="GTA 6 gameplay")
limit=st.slider("Search results",5,30,12)
if st.button("1. Find GTA 6 videos",type="primary"):
    with st.spinner("Searching public video listings..."):
        try:
            st.session_state["results"]=search(query,limit)
            st.success(f"Found {len(st.session_state['results'])} GTA VI-titled videos")
        except Exception as exc: st.error(f"Search unavailable: {exc}")
rows=st.session_state.get("results",[])
if rows:
    if st.button("2. Fetch comment counts and rank"):
        with st.spinner("Fetching public metadata (some videos may block access)..."):
            st.session_state["results"]=enrich(rows)
            rows=st.session_state["results"]
    st.dataframe([{"title":r["title"],"comments":r["comments"],"views":r["views"],
                   "duration_seconds":r["duration"],"url":r["url"]} for r in rows],
                 use_container_width=True,hide_index=True)
    selected=st.selectbox("Choose video",list(range(len(rows))),
                          format_func=lambda i:rows[i]["title"][:105])
    url=rows[selected]["url"]
    st.markdown("#### Preview selected video")
    st.video(url)
    st.link_button("Open video on YouTube",url)
    if st.button("Check selected video's availability"):
        with st.spinner("Checking YouTube..."):
            try:
                with yt_dlp.YoutubeDL({"quiet":True,"no_warnings":True,"skip_download":True,
                                       "noplaylist":True,"socket_timeout":15}) as ydl:
                    detail=ydl.extract_info(url,download=False)
                availability=(detail or {}).get("availability","public")
                if availability in ("private","premium_only","subscriber_only","needs_auth"):
                    st.error(f"Video is restricted: {availability}. Choose another video.")
                else:
                    st.success("Metadata is accessible. Play the preview to confirm the video actually works; downloads can still be blocked.")
            except Exception as exc:
                st.error(f"Video could not be verified: {exc}. Choose another result.")
else:
    url=st.text_input("Or paste a direct video URL (only footage you can lawfully use)")
st.subheader("3. Generate clips")
st.warning("You must have permission to download and reuse the video. Commentary does not guarantee copyright clearance.")
rights=st.checkbox("I have the rights or permission needed to download and reuse this footage")
minutes=st.number_input("Maximum clips (60 seconds each)",min_value=1,max_value=60,value=26)
narration=st.checkbox("Add English computer voice commentary",value=True)
vertical=st.checkbox("Create vertical 9:16 Shorts",value=True)
if st.button("4. Download source and create MP4 clips",disabled=not rights or not url):
    with st.spinner("Downloading and rendering; long videos can take time..."):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                template=str(Path(tmp)/"source.%(ext)s")
                with yt_dlp.YoutubeDL({"format":"bv*[height<=720]+ba/b[height<=720]/best",
                                      "merge_output_format":"mp4","outtmpl":template,
                                      "noplaylist":True,"max_filesize":1024*1024*1024}) as ydl:
                    meta=ydl.extract_info(url,download=True)
                    candidate=Path(ydl.prepare_filename(meta))
                if not candidate.exists():
                    matches=list(Path(tmp).glob("source.*"))
                    if not matches: raise RuntimeError("Download did not produce a video")
                    candidate=matches[0]
                clips=process(candidate,meta.get("title") or "GTA 6",int(minutes),narration,vertical)
            import zipfile
            zip_path=OUT/"gta6_shorts.zip"
            with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as archive:
                for clip in clips: archive.write(clip,arcname=clip.name)
                archive.write(OUT/"clips"/"manifest.json",arcname="manifest.json")
            st.success(f"Created {len(clips)} playable MP4 clips.")
            st.session_state["zip_path"]=str(zip_path)
        except Exception as exc:
            st.error(f"Processing failed: {exc}")
if st.session_state.get("zip_path") and Path(st.session_state["zip_path"]).exists():
    with open(st.session_state["zip_path"],"rb") as f:
        st.download_button("Download all GTA 6 clips (ZIP)",data=f,
                           file_name="gta6_shorts.zip",mime="application/zip")
st.caption("Search metadata can be incomplete; downloads may be blocked. Voice commentary is generic and not based on AI visual understanding.")
