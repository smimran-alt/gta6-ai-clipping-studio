"""Multi-platform public GTA 6 video discovery.

Search results are leads, not proof of playability, download access or reuse rights.
No API keys or login required. Platform search and metadata can be rate limited.
"""
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, parse_qs, quote

import requests
import yt_dlp

PLATFORMS=("YouTube","Twitch","Vimeo","Dailymotion","Internet Archive")
DOMAINS={"YouTube":("youtube.com","youtu.be"),"Twitch":("twitch.tv",),
         "Vimeo":("vimeo.com",),"Dailymotion":("dailymotion.com","dai.ly"),
         "Internet Archive":("archive.org",)}
UA={"User-Agent":"Mozilla/5.0 (compatible; GTAClippingStudio/1.5)"}
GTA6=re.compile(r"(?i)\\b(?:gta\\s*(?:6|vi)|grand theft auto\\s*(?:6|vi))\\b")

def gta6(text):
    return bool(GTA6.search(text or ""))

def valid_url(url, platform):
    try:
        parsed=urlparse(url)
        if parsed.scheme!="https" or not parsed.hostname: return False
        host=parsed.hostname.lower()
        return any(host==domain or host.endswith("."+domain) for domain in DOMAINS[platform])
    except (ValueError, KeyError):
        return False

def normalize_url(url,platform):
    if not valid_url(url,platform): return None
    parsed=urlparse(url)
    if platform=="YouTube":
        if parsed.hostname in ("youtu.be","www.youtu.be"):
            vid=parsed.path.strip("/").split("/")[0]
        elif parsed.path=="/watch":
            vid=parse_qs(parsed.query).get("v",[""])[0]
        elif parsed.path.startswith(("/shorts/","/live/")):
            vid=parsed.path.strip("/").split("/")[1]
        else: return None
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}",vid): return None
        return "https://www.youtube.com/watch?v="+vid
    if platform=="Internet Archive":
        m=re.match(r"^/details/([^/?#]+)",parsed.path)
        return "https://archive.org/details/"+m.group(1) if m else None
    if platform=="Twitch":
        # Search results must be a VOD, clip, or channel video; channel homepages are not video previews.
        if not (re.match(r"^/videos/\\d+",parsed.path) or
                re.match(r"^/[^/]+/clip/[^/]+",parsed.path) or
                re.match(r"^/[^/]+/videos(?:/|$)",parsed.path) or
                parsed.hostname=="clips.twitch.tv"):
            return None
    if platform=="Vimeo" and not re.match(r"^/(?:\\d+|channels/[^/]+/\\d+|groups/[^/]+/videos/\\d+)",parsed.path):
        return None
    if platform=="Dailymotion" and not (re.match(r"^/video/[A-Za-z0-9]+",parsed.path) or parsed.hostname=="dai.ly"):
        return None
    return url.split("#",1)[0]

def youtube(query,limit):
    with yt_dlp.YoutubeDL({"quiet":True,"no_warnings":True,"extract_flat":"in_playlist",
                           "skip_download":True,"socket_timeout":15}) as ydl:
        info=ydl.extract_info(f"ytsearch{limit}:{query}",download=False)
    rows=[]
    for item in (info or {}).get("entries",[]):
        if not item: continue
        title=item.get("title") or ""
        if not gta6(title): continue
        vid=item.get("id")
        url=normalize_url("https://www.youtube.com/watch?v="+str(vid),"YouTube")
        if url:
            rows.append({"platform":"YouTube","title":title,"url":url,
                         "views":item.get("view_count"),"comments":None,
                         "duration":item.get("duration"),"availability":"Unverified"})
    return rows

def bing(query,limit,platform):
    domain=DOMAINS[platform][0]
    # Bing RSS is public but not guaranteed to return results for every platform.
    response=requests.get("https://www.bing.com/search",
                          params={"q":f'{query} site:{domain}',"format":"rss","count":str(min(limit*3,50))},
                          headers=UA,timeout=20)
    response.raise_for_status()
    root=ET.fromstring(response.text)
    rows=[]
    for item in root.findall(".//item"):
        title=item.findtext("title","").strip()
        raw=item.findtext("link","").strip()
        url=normalize_url(raw,platform)
        if url and gta6(title):
            rows.append({"platform":platform,"title":title,"url":url,
                         "views":None,"comments":None,"duration":None,
                         "availability":"Unverified"})
    return rows[:limit]

def archive(query,limit):
    response=requests.get("https://archive.org/advancedsearch.php",
                          params={"q":'mediatype:movies AND (title:"gta 6" OR title:"gta vi" OR title:"grand theft auto vi")',
                                  "fl[]":["identifier","title","downloads"],"rows":str(min(limit*5,100)),
                                  "output":"json"},headers=UA,timeout=25)
    response.raise_for_status()
    rows=[]
    for item in response.json().get("response",{}).get("docs",[]):
        title=item.get("title") or ""
        identifier=item.get("identifier")
        if not gta6(title) or not identifier: continue
        url=normalize_url("https://archive.org/details/"+identifier,"Internet Archive")
        if url:
            rows.append({"platform":"Internet Archive","title":title,"url":url,
                         "views":item.get("downloads"),"comments":None,
                         "duration":None,"availability":"Unverified"})
    return rows[:limit]

def discover(query,limit,platform):
    targets=PLATFORMS if platform=="All platforms" else (platform,)
    rows=[]; errors={}
    for source in targets:
        try:
            if source=="YouTube": found=youtube(query,limit)
            elif source=="Internet Archive": found=archive(query,limit)
            else: found=bing(query,limit,source)
            rows.extend(found)
        except Exception as exc:
            errors[source]=str(exc)[:240]
    unique={}
    for row in rows:
        unique.setdefault(row["url"],row)
    return list(unique.values()),errors

def check_video(url):
    """On-demand public metadata check; accessible metadata is NOT proof playback or download works."""
    with yt_dlp.YoutubeDL({"quiet":True,"no_warnings":True,"skip_download":True,
                           "noplaylist":True,"socket_timeout":15}) as ydl:
        info=ydl.extract_info(url,download=False)
    if not info: raise RuntimeError("No video metadata returned.")
    status=info.get("availability") or "public"
    if status in ("private","premium_only","subscriber_only","needs_auth"):
        return {"status":"Restricted: "+status,"playable":False}
    return {"status":"Metadata accessible (playback not guaranteed)","playable":None,
            "duration":info.get("duration"),"views":info.get("view_count"),
            "comments":info.get("comment_count"),"title":info.get("title")}

def embed_url(url,platform):
    """Only use embeds with known safe video IDs; otherwise show external watch link."""
    if platform=="YouTube": return url
    if platform=="Vimeo":
        match=re.search(r"/(\\d+)(?:$|[/?])",url)
        if match: return "https://player.vimeo.com/video/"+match.group(1)
    if platform=="Dailymotion":
        match=re.search(r"(?:/video/|dai\\.ly/)([A-Za-z0-9]+)",url)
        if match: return "https://www.dailymotion.com/embed/video/"+match.group(1)
    return None
