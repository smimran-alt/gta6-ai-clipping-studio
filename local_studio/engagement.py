"""Automatic GTA 6 discovery engagement ranking and timestamp-comment analysis.

YouTube public comment retrieval is best-effort through yt-dlp; no comments API key.
Counts are only comments that explicitly contain a timestamp, NOT all comments
written while a moment was playing. Other platforms use video-level metrics only.
"""
import collections
import re
from urllib.parse import urlparse

import yt_dlp

TIME_PATTERN=re.compile(r"(?<![\d:])(?:(\d{1,2}):)?([0-5]?\d):([0-5]\d)(?![\d:])")
MAX_COMMENTS=500
WINDOW=30

def seconds_from_timestamp(match):
    hour,minute,second=match.groups()
    if hour is None:
        return int(minute)*60+int(second)
    return int(hour)*3600+int(minute)*60+int(second)

def timestamps(text,duration=None):
    times=[]
    for match in TIME_PATTERN.finditer(text or ""):
        t=seconds_from_timestamp(match)
        if duration is None or t<float(duration):
            times.append(t)
    return sorted(set(times))

def rank_moments(comments,duration,window=WINDOW,top=5):
    """One vote per comment per window, with non-overlapping 30s suggestions."""
    bins=collections.Counter()
    for comment in comments:
        times=timestamps(comment.get("text") or "",duration)
        for bucket in {int(t//window)*window for t in times}:
            if bucket+window<=duration:
                bins[bucket]+=1
    ranked=sorted(bins.items(),key=lambda x:(-x[1],x[0]))
    return [{"start":start,"end":start+window,"timestamped_comments":votes}
            for start,votes in ranked[:top]]

def fetch_youtube_comments(url,max_comments=MAX_COMMENTS):
    """Public comments via yt-dlp extractor; may be unavailable or rate-limited."""
    options={"quiet":True,"no_warnings":True,"skip_download":True,
             "noplaylist":True,"socket_timeout":15,
             "extractor_args":{"youtube":{"comment_sort":["top"]}},
             "getcomments":True,
             "max_comments":[str(max_comments)]}
    with yt_dlp.YoutubeDL(options) as ydl:
        info=ydl.extract_info(url,download=False)
    if not info: raise RuntimeError("No public video metadata available")
    comments=info.get("comments") or []
    duration=info.get("duration")
    return {"title":info.get("title") or "GTA 6",
            "duration":duration,"views":info.get("view_count"),
            "comment_count":info.get("comment_count"),
            "comments_scanned":len(comments),
            "timestamped_comment_count":sum(bool(timestamps(c.get("text") or "",duration)) for c in comments),
            "moments":rank_moments(comments,float(duration),top=5) if duration and duration>=30 else [],
            "status":"Public comments sampled; not a complete count" if comments else "No accessible public comments"}

def engagement_sort(rows):
    """Unknown metrics sort after known metrics; no invented numbers."""
    return sorted(rows,key=lambda r:(r.get("comments") is None,
                                     -(r.get("comments") or 0),
                                     r.get("views") is None,
                                     -(r.get("views") or 0)))
