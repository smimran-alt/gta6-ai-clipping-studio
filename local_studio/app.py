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

import requests
import xml.etree.ElementTree as ET

def search_other(query, limit, platform):
    domains={"Twitch":"twitch.tv","Vimeo":"vimeo.com","Dailymotion":"dailymotion.com","Internet Archive":"archive.org"}
    domain=domains[platform]
    response=requests.get("https://www.bing.com/search",params={"q":query+" site:"+domain,"format":"rss","count":str(limit)},headers={"User-Agent":"Mozilla/5.0"},timeout=20)
    response.raise_for_status()
    root=ET.fromstring(response.text)
    rows=[]
    for item in root.findall(".//item"):
        title=item.findtext("title","")
        link=item.findtext("link","")
        if is_gta6(title) and domain in urlparse(link).netloc.lower():
            rows.append({"title":title,"url":link,"platform":platform,"comments":None,"views":None,"duration":None})
    return rows[:limit]

def search_archive(limit):
    response=requests.get("https://archive.org/advancedsearch.php",params={
        "q":'mediatype:movies AND (title:"gta 6" OR title:"grand theft auto vi")',
        "fl[]":["identifier","title","downloads"],"rows":str(limit*3),"output":"json"},timeout=25)
    response.raise_for_status()
    rows=[]
    for item in response.json().get("response",{}).get("docs",[]):
        if is_gta6(item.get("title","")):
            rows.append({"title":item["title"],"url":"https://archive.org/details/"+item["identifier"],
                         "platform":"Internet Archive","comments":None,"views":item.get("downloads"),"duration":None})
    return rows[:limit]

def search_platform(query,limit,platform):
    if platform=="YouTube":
        return [dict(row,platform="YouTube") for row in search(query,limit)]
    if platform=="Internet Archive":
        return search_archive(limit)
    if platform=="All platforms":
        found=[]
        for source in ("YouTube","Twitch","Vimeo","Dailymotion","Internet Archive"):
            try:
                found.extend(search_platform(query,limit,source))
            except Exception:
                pass
        return found
    return search_other(query,limit,platform)

def enrich(rows):
    for item in rows:
        if item.get("platform","YouTube") != "YouTube":
            continue
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

APP_VERSION="v1.3.2"
st.set_page_config(page_title=f"GTA 6 AI Clipping Studio {APP_VERSION} - Local",page_icon="🎬",layout="wide")
st.title(f"🎬 GTA 6 Clipping Studio {APP_VERSION} — Local")
st.caption("Find GTA VI videos, rank by available comments, then generate 60-second MP4 clips. No Google API key.")
if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
    st.error("FFmpeg and ffprobe are not installed or not in PATH. Install FFmpeg before processing.")
platform=st.selectbox("Search platform",["All platforms","YouTube","Twitch","Vimeo","Dailymotion","Internet Archive"])
query=st.text_input("Search videos",value="GTA 6 gameplay")
limit=st.slider("Search results",5,30,12)
if st.button("1. Find GTA 6 videos",type="primary"):
    with st.spinner("Searching public video listings..."):
        try:
            st.session_state["results"]=search_platform(query,limit,platform)
            st.success(f"Found {len(st.session_state['results'])} GTA VI-titled videos")
        except Exception as exc: st.error(f"Search unavailable: {exc}")
rows=st.session_state.get("results",[])
if rows:
    from collections import Counter
    counts=Counter(item.get("platform","YouTube") for item in rows)
    st.write("Results by source: "+", ".join(name+": "+str(counts.get(name,0)) for name in ("YouTube","Twitch","Vimeo","Dailymotion","Internet Archive")))
if rows:
    if st.button("2. Fetch comment counts and rank"):
        with st.spinner("Fetching public metadata (some videos may block access)..."):
            st.session_state["results"]=enrich(rows)
            rows=st.session_state["results"]
    st.dataframe([{"platform":r.get("platform","YouTube"),"title":r["title"],"comments":r["comments"],"views":r["views"],
                   "duration_seconds":r["duration"],"Watch video":r["url"],"url":r["url"]} for r in rows],
                 column_config={"Watch video":st.column_config.LinkColumn("Watch video",display_text="▶ Watch video",help="Open this video directly on YouTube"),
                                "url":st.column_config.TextColumn("url")},
                 use_container_width=True,hide_index=True)
    selected=st.selectbox("Choose video",list(range(len(rows))),
                          format_func=lambda i:rows[i]["title"][:105])
    url=rows[selected]["url"]
    st.markdown("#### Preview selected video")
    if rows[selected].get("platform","YouTube")=="YouTube":
        st.video(url)
    else:
        st.info("Preview may be restricted on this platform. Open the source website.")
    st.link_button("Open video on source website",url)
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
quality=st.selectbox("Maximum download resolution",["360p","480p","720p"],index=1)
size_mb=st.number_input("Maximum source download size (MB)",min_value=50,max_value=2000,value=500,step=50)
st.caption("The size limit applies to the entire selected source, not just one 60-second clip. Long videos may exceed the limit even at low resolution.")
if st.button("4. Download source and create MP4 clips",disabled=not rights or not url):
    with st.spinner("Downloading and rendering; long videos can take time..."):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                template=str(Path(tmp)/"source.%(ext)s")
                height=int(quality[:-1])
                max_bytes=int(size_mb)*1024*1024
                format_rule=f"b[height<={height}]/bv*[height<={height}]+ba"
                options={"format":format_rule,"merge_output_format":"mp4",
                         "outtmpl":template,"noplaylist":True,
                         "max_filesize":max_bytes,"quiet":True,"no_warnings":True}
                with yt_dlp.YoutubeDL(options) as ydl:
                    info=ydl.extract_info(url,download=False)
                    if not info:
                        raise RuntimeError("Video metadata unavailable. Try another source.")
                    selected=info.get("requested_formats") or [info]
                    estimated=sum((part.get("filesize") or part.get("filesize_approx") or 0)
                                  for part in selected)
                    if estimated and estimated>max_bytes:
                        raise RuntimeError(
                            f"Selected {quality} source is approximately {estimated/1024/1024:.0f} MB, "
                            f"above your {size_mb} MB limit. Choose a shorter video or increase the limit.")
                    meta=ydl.extract_info(url,download=True)
                matches=[path for path in Path(tmp).glob("source.*")
                         if path.suffix.lower() in (".mp4",".mkv",".webm",".mov")
                         and path.is_file()]
                if not matches:
                    raise RuntimeError("No video file was downloaded. This source may be restricted, "
                                       "the requested quality unavailable, or the size limit exceeded. "
                                       "Try a shorter video or another resolution.")
                candidate=max(matches,key=lambda path:path.stat().st_size)
                if candidate.stat().st_size>max_bytes:
                    raise RuntimeError(f"Downloaded file exceeds {size_mb} MB limit.")
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
st.caption("Non-YouTube discovery uses public web search; availability is not guaranteed. Search metadata can be incomplete; downloads may be blocked. Voice commentary is generic and not based on AI visual understanding.")
