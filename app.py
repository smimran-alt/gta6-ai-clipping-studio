import os
import re
import subprocess
import tempfile
from pathlib import Path

import requests
import streamlit as st

st.set_page_config(page_title="GTA Viral Studio", page_icon="🎮", layout="wide")
st.title("🎮 GTA Viral Studio v1.0")
st.caption("Discover GTA video candidates and create Shorts from footage you are allowed to reuse.")

def api_key():
    try:
        return st.secrets.get("YOUTUBE_API_KEY", os.getenv("YOUTUBE_API_KEY", ""))
    except Exception:
        return os.getenv("YOUTUBE_API_KEY", "")

search_tab, clip_tab = st.tabs(["🔎 Discover videos", "✂️ Create a Short"])

with search_tab:
    query = st.text_input("YouTube search", "GTA 6 trailer")
    if st.button("Find videos"):
        key = api_key()
        if not key:
            st.warning("Configure YOUTUBE_API_KEY in Streamlit app secrets to enable search.")
        else:
            try:
                r = requests.get("https://www.googleapis.com/youtube/v3/search",
                    params={"part":"snippet","q":query,"type":"video","maxResults":12,"order":"date","key":key}, timeout=20)
                r.raise_for_status()
                items = r.json().get("items", [])
                ids = ",".join(x["id"]["videoId"] for x in items)
                stats = {}
                if ids:
                    v = requests.get("https://www.googleapis.com/youtube/v3/videos",
                        params={"part":"statistics","id":ids,"key":key}, timeout=20)
                    v.raise_for_status()
                    stats = {x["id"]:x.get("statistics", {}) for x in v.json().get("items", [])}
                for item in items:
                    vid = item["id"]["videoId"]
                    s = stats.get(vid, {})
                    views = int(s.get("viewCount", 0))
                    likes = int(s.get("likeCount", 0))
                    comments = int(s.get("commentCount", 0))
                    engagement = (likes + comments) / max(views, 1)
                    score = min(100, round(25 * min(views / 100000, 1) + 75 * min(engagement / .08, 1)))
                    st.subheader(item["snippet"]["title"])
                    st.write(f"Channel: {item['snippet']['channelTitle']} · Views: {views:,} · Engagement: {engagement:.2%} · Opportunity score: {score}/100")
                    st.link_button("View original on YouTube", f"https://www.youtube.com/watch?v={vid}")
                    st.divider()
                st.info("The opportunity score is a simple heuristic, not a prediction of virality. Verify reuse rights.")
            except (requests.RequestException, ValueError, KeyError) as exc:
                st.error(f"YouTube search failed: {exc}")

with clip_tab:
    st.write("Upload footage you own or have permission to edit and republish.")
    approved = st.checkbox("I own this footage or have permission to edit and republish it.")
    uploaded = st.file_uploader("Choose a video", type=["mp4","mov","mkv"])
    start = st.number_input("Start time (seconds)", min_value=0.0, value=0.0, step=1.0)
    duration = st.slider("Clip length (seconds)", 5, 60, 20)
    caption = st.text_input("Optional headline", "INSANE GTA MOMENT!")
    if st.button("Create vertical Short", disabled=not (uploaded and approved)):
        if not re.fullmatch(r"[\w\s!?.,:()\-]{0,100}", caption):
            st.error("Headline contains unsupported characters.")
        else:
            with tempfile.TemporaryDirectory() as td:
                source = Path(td) / ("source." + uploaded.name.rsplit(".",1)[-1].lower())
                source.write_bytes(uploaded.getbuffer())
                target = Path(td) / "short.mp4"
                vf = "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1"
                if caption:
                    escaped = caption.replace("\\","\\\\").replace(":","\\:").replace("'","\\'").replace("%","\\%")
                    vf += f",drawtext=text='{escaped}':fontcolor=white:fontsize=42:borderw=3:bordercolor=black:x=(w-text_w)/2:y=110"
                cmd = ["ffmpeg","-hide_banner","-loglevel","error","-y","-ss",str(start),"-i",str(source),"-t",str(duration),"-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","25","-c:a","aac","-movflags","+faststart",str(target)]
                try:
                    with st.spinner("Rendering your Short..."):
                        p = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
                    if p.returncode != 0:
                        st.error("FFmpeg failed: " + p.stderr[-1200:])
                    elif target.exists():
                        data = target.read_bytes()
                        st.video(data)
                        st.download_button("Download Short", data, file_name="gta_short.mp4", mime="video/mp4")
                except FileNotFoundError:
                    st.error("FFmpeg is not installed.")
                except subprocess.TimeoutExpired:
                    st.error("Rendering timed out. Try a shorter video.")
