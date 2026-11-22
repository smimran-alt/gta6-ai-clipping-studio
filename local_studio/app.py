"""Local GTA VI clipping studio: search, review, download authorized footage, split and narrate.
Run: streamlit run local_studio/app.py
Requires ffmpeg/ffprobe in PATH. Video download is opt-in and requires rights confirmation.
"""
import csv
import os
import sys
import time
import zipfile
import datetime
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
import yt_dlp
import discovery
import highlights
import editor
import engagement
import comment_download
import watermark_edit
import color_grade

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
    result=subprocess.run(args,capture_output=True,text=True,timeout=timeout,errors="replace")
    if result.returncode:
        raise RuntimeError(f"FFmpeg exited {result.returncode}: {(result.stderr or result.stdout)[-2000:]}")
    return result.stdout.strip()

def length(path):
    return float(command(["ffprobe","-v","error","-show_entries","format=duration",
                          "-of","default=noprint_wrappers=1:nokey=1",str(path)]))

def process(source, title, minutes, narration, vertical, clip_seconds=60):
    folder=OUT/"clips"
    folder.mkdir(parents=True,exist_ok=True)
    # Keep previous successful exports; only replace the current clip after validation.
    duration=length(source)
    count=min((int(duration+clip_seconds-0.001)//clip_seconds),minutes)
    if count==0: raise RuntimeError("Video is shorter than one second")
    files=[]
    for i in range(count):
        segment_length=min(clip_seconds,duration-i*clip_seconds)
        out=folder/f"clip_{i+1:03d}.mp4"
        pending=folder/f"clip_{i+1:03d}.pending.mp4"
        if pending.exists(): pending.unlink()
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
            vf=["scale=480:854:force_original_aspect_ratio=increase,crop=480:854"] if vertical else []
            # Text overlay disabled for Windows rendering compatibility.
            args=["ffmpeg","-hide_banner","-loglevel","error","-y","-ss",str(i*clip_seconds),"-i",str(source)]
            if narration: args+=["-i",str(audio)]
            args+=["-t",str(segment_length),"-vf",",".join(vf),"-map","0:v:0"]
            if narration: args+=["-map","1:a:0","-af","apad"]
            else: args+=["-map","0:a?"]
            args+=["-threads","2","-filter_threads","1","-c:v","libx264","-preset","ultrafast","-crf","28","-pix_fmt","yuv420p",
                   "-c:a","aac","-b:a","128k","-movflags","+faststart",str(pending)]
            try:
                command(args,timeout=420)
            except Exception as exc:
                if pending.exists(): pending.unlink()
                if vertical:
                    # Some Windows FFmpeg builds crash on crop/scale. Try a simpler, uncropped encode.
                    fallback=["ffmpeg","-hide_banner","-loglevel","error","-y",
                              "-ss",str(i*clip_seconds),"-i",str(source),"-t",str(segment_length),
                              "-map","0:v:0","-map","0:a?","-c:v","libx264","-threads","1",
                              "-preset","ultrafast","-crf","28","-pix_fmt","yuv420p",
                              "-c:a","aac","-b:a","128k","-movflags","+faststart",str(pending)]
                    try:
                        command(fallback,timeout=420)
                    except Exception as fallback_exc:
                        raise RuntimeError(f"Vertical render failed: {exc}; fallback render failed: {fallback_exc}") from fallback_exc
                else:
                    raise
            if not pending.exists() or pending.stat().st_size<1024:
                raise RuntimeError("FFmpeg returned without creating a usable MP4.")
            verified=length(pending)
            if verified<1 or abs(verified-segment_length)>3:
                raise RuntimeError(f"Output validation failed: expected {segment_length:.1f}s, got {verified:.1f}s.")
            os.replace(pending,out)
        files.append(out)
    manifest={"source":title,"source_duration":duration,"clips":[x.name for x in files],
              "commentary":"Generic original voice, not scene-aware; review before publication"}
    (folder/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return files

APP_VERSION="v1.8.5"
st.set_page_config(page_title=f"GTA 6 AI Clipping Studio {APP_VERSION} - Local",page_icon="🎬",layout="wide")
st.title(f"🎬 GTA 6 Clipping Studio {APP_VERSION} — Local")
st.caption("Search GTA 6 automatically, rank by comments, identify timestamped discussions and download authorized 30-second moments.")
st.info(f"Output folder: {OUT}")
if st.button("Open output folder on this computer"):
    try:
        if os.name=="nt": os.startfile(str(OUT))
        elif sys.platform=="darwin": subprocess.Popen(["open",str(OUT)])
        else: subprocess.Popen(["xdg-open",str(OUT)])
    except Exception as exc: st.error(f"Could not open folder: {exc}")

if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
    st.error("FFmpeg and ffprobe are not installed or not in PATH. Install FFmpeg before processing.")
platform=st.selectbox("Search platform",["All platforms","YouTube","Twitch","Vimeo","Dailymotion","Internet Archive"])
query=st.text_input("Search videos",value="GTA 6 gameplay")
limit=st.slider("Search results",5,30,12)
if st.button("1. Find GTA 6 videos",type="primary"):
    with st.spinner("Searching public video listings..."):
        try:
            found,errors=discovery.discover(query,limit,platform)
            st.session_state["results"]=found
            st.session_state["selected_video_url"]=found[0]["url"] if found else None
            st.session_state.pop("most_discussed_download",None)
            st.session_state["discovery_errors"]=errors
            st.success(f"Found {len(found)} unique GTA VI-titled video results across selected sources.")
            if errors:
                st.warning("Some sources could not be searched: "+", ".join(f"{k}: {v}" for k,v in errors.items()))
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
                   "duration_seconds":r["duration"],"availability":r.get("availability","Unverified"),"Watch video":r["url"],"url":r["url"]} for r in rows],
                 column_config={"Watch video":st.column_config.LinkColumn("Watch video",display_text="▶ Watch video",help="Open this video on its source website"),
                                "url":st.column_config.TextColumn("url")},
                 use_container_width=True,hide_index=True)
    # URL is the stable identity. Row indices change after sorting/enrichment.
    video_urls=[item["url"] for item in rows]
    if st.session_state.get("selected_video_url") not in video_urls:
        st.session_state["selected_video_url"]=video_urls[0]
    url=st.selectbox("Choose video",video_urls,
                     format_func=lambda value:next((item["title"][:105] for item in rows if item["url"]==value),value),
                     key="selected_video_url")
    selected=video_urls.index(url)
    st.markdown("#### Preview selected video")
    selected_platform=rows[selected].get("platform","YouTube")
    st.caption(f"Source: {selected_platform} | Preview availability depends on the host. A search result is not proof that the video is playable.")
    embed=discovery.embed_url(url,selected_platform)
    if embed:
        try:
            st.video(embed)
        except Exception:
            st.info("Inline preview unavailable for this host. Use the source link below.")
    else:
        st.info("This source does not provide a reliable in-app preview. Open its video page directly.")
    st.link_button("▶ Watch video on "+selected_platform,url)
    if st.button("Check selected video's availability"):
        with st.spinner("Checking public metadata..."):
            try:
                result=discovery.check_video(url)
                if result.get("playable") is False:
                    st.error(result["status"])
                else:
                    st.success(result["status"])
                    st.caption("Confirm playback on the source website. A successful metadata check does not guarantee a downloadable video.")
                    if result.get("duration"):
                        rows[selected]["duration"]=result["duration"]
                    if result.get("views") is not None:
                        rows[selected]["views"]=result["views"]
                    if result.get("comments") is not None:
                        rows[selected]["comments"]=result["comments"]
                    st.session_state["results"]=rows
            except Exception as exc:
                st.error(f"Metadata check failed: {exc}")

else:
    url=st.text_input("Or paste a direct video URL (only footage you can lawfully use)")
st.divider()
st.subheader("3. Most-discussed moments for your selected video")
st.caption("This section follows the video selected above. Timestamped comments are public sampled references, not actual per-segment comment totals.")
if rows:
    active=next((item for item in rows if item["url"]==url),None)
    st.write(f"**Selected video:** {active['title']}")
    st.link_button("Watch selected source",url)
    if active.get("platform","YouTube")!="YouTube":
        st.info("Timestamped comment analysis currently supports YouTube only. Choose a YouTube result above, or use section 6 for scene/audio highlights.")
    else:
        if st.button("Analyze comments for this selected video",type="primary",key="analyze_selected_comments"):
            with st.spinner("Reading available public comments for this video..."):
                try:
                    detail=engagement.fetch_youtube_comments(url)
                    st.session_state.setdefault("comment_reports_by_url",{})[url]={"detail":detail,"error":None}
                except Exception as exc:
                    st.session_state.setdefault("comment_reports_by_url",{})[url]={"detail":None,"error":str(exc)[:350]}
        current=st.session_state.get("comment_reports_by_url",{}).get(url)
        if current:
            if current["error"]:
                st.warning("Comment analysis unavailable: "+current["error"])
            else:
                detail=current["detail"]
                st.write(f"Video comments (reported): {detail.get('comment_count') if detail.get('comment_count') is not None else 'Unknown'} | Public comments scanned: {detail['comments_scanned']} | Comments containing timestamps: {detail['timestamped_comment_count']}")
                st.caption(detail["status"])
                moments=detail.get("moments",[])
                if not moments:
                    st.info("No timestamped comments found in the accessible sample. Try section 6 for scene/audio highlights.")
                else:
                    st.dataframe([{"start":f"{m['start']//3600:02d}:{(m['start']//60)%60:02d}:{m['start']%60:02d}",
                                   "end":f"{m['end']//3600:02d}:{(m['end']//60)%60:02d}:{m['end']%60:02d}",
                                   "sampled_timestamp_mentions":m["timestamped_comments"],
                                   "reason_for_selection":("Most timestamp mentions in sampled comments" if m["timestamped_comments"]==max(item["timestamped_comments"] for item in moments) else
                                       f"Ranked by {m['timestamped_comments']} sampled timestamp mention(s)")} for m in moments],
                                 hide_index=True,use_container_width=True)
                    st.markdown("#### Automatically download recommended clips")
                    st.caption("Downloads all recommended 30-second intervals from this selected video, without choosing them one by one. Only use footage you are authorized to download and reuse.")
                    st.markdown("##### Automatic Shorts colour grading")
                    grade_preset=st.selectbox("Video look",list(color_grade.PRESETS),
                                             index=0,key="grade_preset_"+url)
                    st.caption("Natural cinematic is the default. Colour grading improves appearance but does not remove watermarks or creator attribution.")
                    st.markdown("##### Optional watermark-area blur (authorized footage only)")
                    blur_requested=st.checkbox("Blur a selected logo/watermark area after download (keep originals)",value=False,key="blur_requested_"+url)
                    if blur_requested:
                        st.caption("Select an approximate rectangular region in percent of the frame. This hides pixels but cannot recover the image underneath. Respect source attribution and usage rights.")
                        blur_x=st.slider("Region left (%)",0,95,80,key="blur_x_"+url)
                        blur_y=st.slider("Region top (%)",0,95,2,key="blur_y_"+url)
                        blur_w=st.slider("Region width (%)",2,100-blur_x, min(18,100-blur_x),key="blur_w_"+url)
                        blur_h=st.slider("Region height (%)",2,100-blur_y,min(14,100-blur_y),key="blur_h_"+url)
                    else:
                        blur_x,blur_y,blur_w,blur_h=80,2,18,14
                    batch_rights=st.checkbox("I have permission to download and reuse this video",key="batch_rights_"+url)
                    if st.button("Download all recommended 30-second clips",disabled=not batch_rights,
                                 type="primary",key="batch_download_"+url):
                        batch_dir=OUT/"most_discussed"/"batch"
                        batch_dir.mkdir(parents=True,exist_ok=True)
                        with st.spinner(f"Downloading and verifying {len(moments)} separate clips..."):
                            batch_results=comment_download.download_batch(url,moments,batch_dir)
                        st.session_state["batch_results_by_url"]=st.session_state.get("batch_results_by_url",{})
                        st.session_state["batch_results_by_url"][url]=batch_results
                        completed=[item for item in batch_results if item["status"]=="saved"]
                        if completed and blur_requested:
                            for item in completed:
                                original=Path(item["file"])
                                blurred=original.with_name(original.stem+"_blurred.mp4")
                                try:
                                    watermark_edit.blur_region(original,blurred,blur_x,blur_y,blur_w,blur_h)
                                    item["edited_file"]=str(blurred)
                                except Exception as exc:
                                    item["edit_error"]=str(exc)[:250]
                            if any(item.get("edit_error") for item in completed):
                                st.warning("Some blur edits failed. Originals were preserved; see the status table.")
                        if completed:
                            for item in completed:
                                source_path=Path(item.get("edited_file",item["file"]))
                                if grade_preset!="Original":
                                    try:
                                        graded=source_path.with_name(source_path.stem+"_graded.mp4")
                                        color_grade.grade(source_path,graded,grade_preset)
                                        item["graded_file"]=str(graded)
                                    except Exception as exc:
                                        item["grade_error"]=str(exc)[:250]
                            if any(item.get("grade_error") for item in completed):
                                st.warning("Some colour edits failed. Original files were preserved; check the status table.")
                            from urllib.parse import parse_qs,urlparse
                            video_id=parse_qs(urlparse(url).query).get("v",["selected_video"])[0]
                            zip_path=OUT/"most_discussed"/f"recommended_clips_{video_id}.zip"
                            with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as archive:
                                for item in completed:
                                    archive.write(item.get("graded_file",item.get("edited_file",item["file"])),arcname=Path(item.get("graded_file",item.get("edited_file",item["file"]))).name)
                                archive.writestr("download_status.json",json.dumps(batch_results,indent=2))
                            st.session_state["batch_zip_by_url"]=st.session_state.get("batch_zip_by_url",{})
                            st.session_state["batch_zip_by_url"][url]=str(zip_path)
                            st.success(f"Saved {len(completed)} of {len(batch_results)} separate MP4 clips.")
                            if len(completed)<len(batch_results):
                                st.warning(f"{len(batch_results)-len(completed)} clips failed. See the status table below for individual errors.")
                        else:
                            st.error("No recommended clips downloaded successfully. The host may block partial downloads.")
                    batch_result=st.session_state.get("batch_results_by_url",{}).get(url)
                    if batch_result:
                        st.dataframe(batch_result,use_container_width=True,hide_index=True)
                        zip_for_video=st.session_state.get("batch_zip_by_url",{}).get(url)
                        if zip_for_video and Path(zip_for_video).exists():
                            with open(zip_for_video,"rb") as bundle:
                                st.download_button("Download all successful clips (ZIP)",data=bundle,
                                                   file_name=Path(zip_for_video).name,mime="application/zip",
                                                   key="batch_zip_"+url)
                    choice=st.selectbox("Choose a 30-second discussion window",
                                        list(range(len(moments))),
                                        format_func=lambda j:f"{moments[j]['start']}–{moments[j]['end']}s | {moments[j]['timestamped_comments']} timestamp mentions",
                                        key="comment_choice_"+url)
                    moment=moments[choice]
                    st.video(url,start_time=int(moment["start"]))
                    permission=st.checkbox("I have permission to download and reuse this footage",
                                            key="comment_rights_"+url)
                    if st.button("Download selected 30-second segment",disabled=not permission,
                                 key="comment_download_"+url):
                        with st.spinner("Downloading and validating this video's selected interval..."):
                            try:
                                result=comment_download.download_range(url,moment["start"],OUT/"most_discussed")
                                st.session_state["most_discussed_download"]={"url":url,"path":str(result)}
                                st.success(f"Saved: {result}")
                            except Exception as exc:
                                st.error(f"Download unavailable: {exc}")
    downloaded=st.session_state.get("most_discussed_download")
    if isinstance(downloaded,dict) and downloaded.get("url")==url and Path(downloaded["path"]).exists():
        st.video(downloaded["path"])
        with open(downloaded["path"],"rb") as source_file:
            st.download_button("Download this video's 30-second MP4",data=source_file,
                               file_name=Path(downloaded["path"]).name,mime="video/mp4",key="comment_mp4_download")
else:
    st.info("Find GTA 6 videos above to select a source.")

st.subheader("3. Generate clips")
st.warning("You must have permission to download and reuse the video. Commentary does not guarantee copyright clearance.")
rights=st.checkbox("I have the rights or permission needed to download and reuse this footage")
minutes=st.number_input("Maximum clips (60 seconds each)",min_value=1,max_value=60,value=1)
segment_mode=st.checkbox("Download only a selected 30-second segment (experimental)",value=True)
selected_duration=rows[selected].get("duration") if rows else None
if segment_mode:
    if selected_duration and selected_duration>30:
        start_second=st.slider("Clip start time (seconds)",min_value=0,max_value=int(selected_duration)-30,value=0,step=1)
    else:
        start_second=st.number_input("Clip start time (seconds)",min_value=0,value=0,step=10)
    st.caption(f"Selected interval: {int(start_second)//60:02d}:{int(start_second)%60:02d} to {(int(start_second)+30)//60:02d}:{(int(start_second)+30)%60:02d}. Partial downloads require FFmpeg and host support.")
    minutes=1
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
                         "max_filesize":max_bytes}
                if segment_mode:
                    options["download_ranges"]=yt_dlp.utils.download_range_func(None, [(float(start_second),float(start_second)+30.0)])
                    options["force_keyframes_at_cuts"]=True
                    options["external_downloader"]="ffmpeg"
                with yt_dlp.YoutubeDL(options) as ydl:
                    info=ydl.extract_info(url,download=False)
                    if not info:
                        raise RuntimeError("Video metadata unavailable.")
                    if segment_mode:
                        duration=info.get("duration")
                        if duration and float(start_second)+30>float(duration):
                            raise RuntimeError("Selected start time is too close to the end of the video.")
                    else:
                        selected_formats=info.get("requested_formats") or [info]
                        estimated=sum((part.get("filesize") or part.get("filesize_approx") or 0)
                                      for part in selected_formats)
                        if estimated and estimated>max_bytes:
                            raise RuntimeError(f"Full video is about {estimated/1024/1024:.0f} MB, above your {size_mb} MB limit. Enable 30-second segment mode.")
                    ydl.download([url])
                matches=[path for path in Path(tmp).glob("source*")
                         if path.suffix.lower() in (".mp4",".mkv",".webm",".mov")
                         and path.is_file()]
                if not matches:
                    raise RuntimeError("No video segment was saved. The host may not support partial downloads or the format may be restricted.")
                candidate=max(matches,key=lambda path:path.stat().st_size)
                if candidate.stat().st_size>max_bytes:
                    raise RuntimeError(f"Downloaded segment exceeded the {size_mb} MB limit.")
                saved_source=OUT/("downloaded_30s_source"+candidate.suffix.lower())
                shutil.copy2(candidate,saved_source)
                st.info(f"Source segment saved at: {saved_source}")
                st.session_state["saved_source"]=str(saved_source)
                st.session_state["last_source_url"]=url
                st.info("Download completed. Rendering and verifying the clip now...")
                clips=process(saved_source,info.get("title") or "GTA 6",int(minutes),narration,vertical,30 if segment_mode else 60)
            zip_path=OUT/"gta6_shorts.zip"
            with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as archive:
                for clip in clips: archive.write(clip,arcname=clip.name)
                archive.write(OUT/"clips"/"manifest.json",arcname="manifest.json")
            st.success(f"Created and verified {len(clips)} MP4 clip(s). Files are in {OUT / 'clips'}")
            st.session_state["clip_paths"]=[str(x) for x in clips]
            st.session_state["zip_path"]=str(zip_path)
        except Exception as exc:
            st.error(f"Processing failed: {exc}")
            st.warning("If downloading completed, check local_output for downloaded_30s_source.mp4 (or another source extension). The source is preserved for retry.")
if st.session_state.get("zip_path") and Path(st.session_state["zip_path"]).exists():
    with open(st.session_state["zip_path"],"rb") as f:
        st.download_button("Download all GTA 6 clips (ZIP)",data=f,
                           file_name="gta6_shorts.zip",mime="application/zip")
st.caption("Search uses public listings; platforms may block previews or metadata. Only download footage you are authorized to reuse. Voice commentary is generic, not scene-aware.")

st.divider()
st.subheader("5. Preview and download saved files")
saved=sorted((OUT/"clips").glob("clip_*.mp4")) if (OUT/"clips").exists() else []
for clip in saved:
    if clip.stat().st_size<1024: continue
    st.write(f"**{clip.name}** — {clip.stat().st_size/1024/1024:.1f} MB")
    st.video(str(clip))
    with clip.open("rb") as file:
        st.download_button(f"Download {clip.name}",data=file,file_name=clip.name,mime="video/mp4",key="dl_"+clip.name)
sources=sorted(OUT.glob("downloaded_30s_source.*"))
if sources:
    st.caption("Preserved source segment:")
    for src in sources:
        st.write(f"{src.name} — {src.stat().st_size/1024/1024:.1f} MB")
        with src.open("rb") as file:
            st.download_button(f"Download preserved source ({src.suffix})",data=file,file_name=src.name,
                               mime="video/mp4" if src.suffix==".mp4" else "application/octet-stream",
                               key="source_"+src.suffix)

st.divider()
st.subheader("6. Automatic 30-second highlight recommendations")
st.caption("Analyzes local video files only. Detects scene changes and soundtrack energy, not specific gameplay events. Results are suggestions, not guaranteed viral moments.")
st.info("For meaningful recommendations, use a source longer than 30 seconds. A 30-second downloaded segment only has one possible 30-second highlight.")
uploaded=st.file_uploader("Optional: add a local video you have permission to edit",type=["mp4","mkv","webm","mov"],key="highlight_upload")
if uploaded is not None and st.button("Save uploaded video for analysis"):
    upload_dir=OUT/"analysis_sources"
    upload_dir.mkdir(parents=True,exist_ok=True)
    # Never trust client-supplied filenames as filesystem paths.
    ext=Path(uploaded.name).suffix.lower()
    target=upload_dir/("uploaded_source"+ext)
    with target.open("wb") as destination:
        shutil.copyfileobj(uploaded,destination)
    st.success(f"Saved {target}")
available_sources=[]
for directory in (OUT,OUT/"analysis_sources"):
    if directory.exists():
        available_sources.extend(path for path in directory.iterdir()
                                 if path.is_file() and path.suffix.lower() in (".mp4",".mkv",".webm",".mov"))
available_sources=sorted(set(available_sources),key=lambda item:item.name.lower())
if available_sources:
    selected_source=st.selectbox("Choose saved source for highlight analysis",available_sources,
                                 format_func=lambda path:f"{path.name} ({path.stat().st_size/1024/1024:.1f} MB)")
    suggestions=st.slider("Number of recommended highlights",1,10,5,key="highlight_count")
    if st.button("Analyze video and recommend 30-second highlights",type="primary"):
        with st.spinner("Analyzing local scene changes and audio; long videos may take several minutes..."):
            try:
                report=highlights.analyze(selected_source,count=suggestions)
                st.session_state["highlight_report"]=report
                st.success(f"Analyzed {report['analyzed_seconds']:.0f} seconds. Found {len(report['recommendations'])} recommendations.")
            except Exception as exc:
                st.error(f"Highlight analysis failed: {exc}")
else:
    st.info("No source video found. Download an authorized segment above or upload your own longer gameplay video.")
report=st.session_state.get("highlight_report")
if report and Path(report["source"]).exists():
    st.caption(f"Source: {Path(report['source']).name} | Method: {report['method']} | {report['audio_status']}")
    st.caption("Scores reflect motion/cuts and loudness only; they do not identify explosions, police chases or actual viewer engagement.")
    recs=report["recommendations"]
    if recs:
        st.dataframe([{"rank":i+1,"start_seconds":item["start"],"end_seconds":item["end"],
                       "highlight_score":item["score"],"scene_changes":item["scene_changes"],
                       "audio_level":item["average_audio"]} for i,item in enumerate(recs)],
                     use_container_width=True,hide_index=True)
        rank=st.selectbox("Select recommended highlight",list(range(len(recs))),
                          format_func=lambda i:f"#{i+1} — {recs[i]['start']}s to {recs[i]['end']}s | Score {recs[i]['score']}")
        chosen=recs[rank]
        st.caption(f"Selected time: {int(chosen['start'])//60:02d}:{int(chosen['start'])%60:02d}–{int(chosen['end'])//60:02d}:{int(chosen['end'])%60:02d}")
        st.video(str(report["source"]),start_time=int(chosen["start"]))
        make_vertical=st.checkbox("Export recommended highlight as vertical 9:16",value=True,key="highlight_vertical")
        if st.button("Export selected 30-second highlight"):
            with st.spinner("Rendering and verifying recommended clip..."):
                try:
                    out=OUT/"highlights"/f"highlight_{rank+1:02d}_{int(chosen['start']):05d}s.mp4"
                    highlights.export_clip(report["source"],chosen["start"],out,vertical=make_vertical)
                    st.session_state["last_highlight_export"]=str(out)
                    st.success(f"Saved verified clip: {out}")
                except Exception as exc:
                    st.error(f"Highlight export failed: {exc}")
last_export=st.session_state.get("last_highlight_export")
if last_export and Path(last_export).exists():
    st.video(last_export)
    with open(last_export,"rb") as file:
        st.download_button("Download recommended 30-second MP4",data=file,
                           file_name=Path(last_export).name,mime="video/mp4")

st.divider()
st.subheader("7. Captions, AI commentary and Shorts editor")
st.caption("Edit a saved video. Captions use optional local Whisper speech recognition; commentary uses your scene notes and optional OpenAI API. No video-event recognition is claimed.")
edit_sources=[]
for folder in (OUT,OUT/"analysis_sources",OUT/"highlights",OUT/"clips"):
    if folder.exists():
        edit_sources.extend(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in (".mp4",".mkv",".webm",".mov"))
edit_sources=sorted(set(edit_sources),key=lambda p:str(p))
if edit_sources:
    edit_source=st.selectbox("Source video for editing",edit_sources,
                              format_func=lambda p:f"{p.parent.name}/{p.name}",key="edit_source")
    try:
        edit_length=editor.duration(edit_source)
        st.caption(f"Source duration: {edit_length:.1f} seconds")
        edit_start=st.number_input("Start time (seconds)",min_value=0.0,max_value=max(0.0,edit_length-1),value=0.0,step=1.0,key="edit_start")
    except Exception as exc:
        edit_start=0.0
        st.error(f"Could not read video duration: {exc}")
    st.video(str(edit_source),start_time=int(edit_start))
    edit_vertical=st.checkbox("Crop to vertical 9:16",value=True,key="edit_vertical")
    edit_title=st.text_input("Optional title overlay",value="",key="edit_title",max_chars=50)
    auto_captions=st.checkbox("Generate automatic speech captions (optional faster-whisper)",value=False,key="edit_captions")
    if auto_captions and st.button("Transcribe speech into captions"):
        with st.spinner("Running local Whisper speech recognition (first run downloads a model)..."):
            try:
                segments=editor.transcribe(edit_source)
                subtitle_dir=OUT/"editor"
                subtitle_dir.mkdir(parents=True,exist_ok=True)
                subtitle_file=subtitle_dir/"speech_captions.srt"
                count=editor.write_srt(segments,subtitle_file,offset=edit_start,limit=30)
                st.session_state["edit_subtitle_path"]=str(subtitle_file)
                st.session_state["edit_transcript"]=" ".join(x["text"] for x in segments if edit_start<=x["start"]<edit_start+30)[:2500]
                st.success(f"Created {count} caption lines. Saved {subtitle_file}")
            except Exception as exc: st.error(f"Caption generation failed: {exc}")
    st.caption("Caption transcription works on spoken audio. Silent gameplay will not produce meaningful captions. Change the start time? Transcribe again to align captions.")
    notes=st.text_area("Describe what happens in this clip (for commentary)",placeholder="Example: My car escapes a police pursuit and narrowly misses a truck.",key="scene_notes")
    use_ai=st.checkbox("Use OpenAI to draft commentary from my notes (optional)",value=False,key="edit_ai")
    api_key=st.text_input("OpenAI API key (used only for this request)",type="password",key="edit_api_key") if use_ai else ""
    voiceover=st.checkbox("Generate spoken voiceover with local TTS (optional pyttsx3)",value=False,key="edit_voice")
    if st.button("Generate commentary script"):
        try:
            if use_ai and not api_key: raise ValueError("Enter an API key or turn off OpenAI commentary.")
            script=editor.commentary(notes,st.session_state.get("edit_transcript",""),api_key if use_ai else None)
            st.session_state["edit_script"]=script
        except Exception as exc: st.error(f"Commentary generation failed: {exc}")
    script=st.text_area("Review or edit commentary script",value=st.session_state.get("edit_script",""),key="edit_script_review")
    st.caption("When voiceover is enabled, it replaces the original audio in the exported video. Otherwise original audio is retained.")
    burn=st.checkbox("Burn generated captions into video",value=False,key="edit_burn")
    if st.button("Render edited 30-second MP4",type="primary",key="render_edited"):
        with st.spinner("Rendering edited clip and validating MP4..."):
            try:
                outdir=OUT/"editor"
                outdir.mkdir(parents=True,exist_ok=True)
                srt=st.session_state.get("edit_subtitle_path") if burn else None
                if burn and (not srt or not Path(srt).exists()):
                    raise ValueError("Generate captions before selecting burn captions.")
                wav=None
                if voiceover:
                    if not script.strip(): raise ValueError("Write or generate a commentary script first.")
                    wav=editor.synthesize(script,outdir/"voiceover.wav")
                target=outdir/"edited_short.mp4"
                result=editor.edit(edit_source,target,start=edit_start,seconds=30,vertical=edit_vertical,
                                   srt=srt,voice=wav,title=edit_title)
                st.session_state["edited_short_path"]=str(result)
                st.success(f"Saved and verified {result}")
            except Exception as exc:
                st.error(f"Video editor failed: {exc}")
else:
    st.info("Save or upload a video in the discovery/highlight sections before editing.")
edited_path=st.session_state.get("edited_short_path")
if edited_path and Path(edited_path).exists():
    st.video(edited_path)
    with open(edited_path,"rb") as file:
        st.download_button("Download edited Short MP4",data=file,file_name="edited_short.mp4",mime="video/mp4")
