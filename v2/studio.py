"""GitHub Actions GTA clipping prototype. No third-party video scraping."""
import csv
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
MAX_BYTES = 250 * 1024 * 1024

def discover():
    key = os.getenv("YOUTUBE_API_KEY", "")
    if not key:
        (OUT / "discovery_note.txt").write_text("Set GitHub Actions secret YOUTUBE_API_KEY to enable discovery.\n")
        return
    found = []
    for query in ["GTA 6 gameplay", "GTA 6 police chase", "GTA 6 funny moments"]:
        r = requests.get("https://www.googleapis.com/youtube/v3/search",
            params={"part": "snippet", "q": query, "type": "video", "maxResults": 10, "order": "date", "key": key}, timeout=20)
        r.raise_for_status()
        found += [(x["id"]["videoId"], query, x["snippet"]["title"]) for x in r.json().get("items", [])]
    unique = {vid: (query, title) for vid, query, title in found}
    ids = list(unique)
    stats = {}
    for start in range(0, len(ids), 50):
        r = requests.get("https://www.googleapis.com/youtube/v3/videos",
            params={"part": "statistics", "id": ",".join(ids[start:start + 50]), "key": key}, timeout=20)
        r.raise_for_status()
        stats.update({v["id"]: v.get("statistics", {}) for v in r.json().get("items", [])})
    rows = []
    for vid, (query, title) in unique.items():
        s = stats.get(vid, {})
        views, likes, comments = (int(s.get(k, 0)) for k in ("viewCount", "likeCount", "commentCount"))
        engagement = (likes + comments) / max(views, 1)
        score = min(100, round(25 * min(views / 100000, 1) + 75 * min(engagement / .08, 1)))
        rows.append({"title": title, "query": query, "url": "https://www.youtube.com/watch?v=" + vid,
                     "views": views, "likes": likes, "comments": comments, "engagement": round(engagement, 4), "score": score,
                     "reuse_rights": "NOT VERIFIED - DISCOVERY ONLY"})
    rows.sort(key=lambda x: x["score"], reverse=True)
    with (OUT / "discovery.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "query", "url", "views", "likes", "comments", "engagement", "score", "reuse_rights"])
        writer.writeheader()
        writer.writerows(rows)

def download(url, dest):
    parsed = urlparse(url)
    allowed = {h.strip().lower() for h in os.getenv("APPROVED_MEDIA_HOSTS", "").split(",") if h.strip()}
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port or parsed.hostname not in allowed:
        raise ValueError("Source host is not allowlisted. Set APPROVED_MEDIA_HOSTS repository variable.")
    with requests.get(url, stream=True, timeout=40, allow_redirects=False) as r:
        r.raise_for_status()
        if r.is_redirect:
            raise ValueError("Redirected downloads are disabled for safety")
        with dest.open("wb") as f:
            size = 0
            for chunk in r.iter_content(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("Source exceeds 250 MB")
                f.write(chunk)

def run(cmd):
    subprocess.run(cmd, check=True, timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def render(entry, index):
    for key in ("title", "url", "rights_basis", "permission_evidence", "commentary"):
        if not isinstance(entry.get(key), str) or not entry[key].strip():
            raise ValueError("Missing required field: " + key)
    if entry["rights_basis"].strip().lower() in {"unknown", "public", "fair use", "none"}:
        raise ValueError("Rights basis is insufficient")
    commentary = entry["commentary"].strip()
    if len(commentary) < 70:
        raise ValueError("Write at least 70 characters of substantive original commentary")
    if entry.get("licensed_music_url"):
        raise ValueError("Licensed music mixing is not implemented in v2; leave licensed_music_url blank")
    start = float(entry.get("start_seconds", 0))
    duration = float(entry.get("duration_seconds", 20))
    if not (0 <= start <= 7200 and 5 <= duration <= 60):
        raise ValueError("Start must be 0-7200 seconds and duration 5-60 seconds")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        src, voice, video = tmp / "source.mp4", tmp / "voice.wav", OUT / f"short_{index:02d}.mp4"
        download(entry["url"], src)
        run(["espeak-ng", "-v", "en-us", "-s", "155", "-w", str(voice), commentary])
        title = re.sub(r"[^A-Za-z0-9 ,.!?'-]", "", entry["title"])[:55]
        caption = re.sub(r"[^A-Za-z0-9 ,.!?'-]", "", commentary)[:140]
        title_file, caption_file = tmp / "title.txt", tmp / "caption.txt"
        title_file.write_text(title, encoding="utf-8")
        caption_file.write_text(caption, encoding="utf-8")
        vf = ("scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
              "drawbox=x=0:y=60:w=iw:h=130:color=black@0.65:t=fill,"
              f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:textfile={title_file}:"
              "fontcolor=white:fontsize=33:x=(w-text_w)/2:y=95,"
              "drawbox=x=0:y=960:w=iw:h=270:color=black@0.65:t=fill,"
              f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:textfile={caption_file}:"
              "fontcolor=white:fontsize=24:x=35:y=990:fix_bounds=1")
        # Voice-over replaces source audio to avoid carrying unlicensed background tracks.
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", str(start), "-i", str(src),
             "-i", str(voice), "-t", str(duration), "-filter_complex", f"[0:v]{vf}[v]",
             "-map", "[v]", "-map", "1:a:0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
             "-c:a", "aac", "-ar", "44100", "-af", "apad", "-shortest", "-movflags", "+faststart", str(video)])
        return video.name

def main():
    report = {"version": "2.0", "clips": [], "errors": [], "review_required": True}
    try:
        discover()
    except Exception as exc:
        report["errors"].append("Discovery: " + str(exc))
    if os.getenv("MAKE_CLIPS", "true").lower() == "true":
        data = json.loads((ROOT / "sources" / "approved.json").read_text(encoding="utf-8"))
        for i, entry in enumerate(data.get("sources", []), 1):
            try:
                report["clips"].append({"title": entry.get("title"), "file": render(entry, i), "status": "REVIEW BEFORE UPLOAD"})
            except Exception as exc:
                report["errors"].append(f"Source {i}: {exc}")
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
