"""Rank public GTA YouTube search results by verified extracted comment counts.
No login, no YouTube downloads. Unknown counts are NEVER guessed.
"""
import csv
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output"
OUT.mkdir(exist_ok=True)
FIELDS=["rank","title","url","comments","views","likes","count_status","reuse_rights","review_status"]

def main():
    source=OUT/"discovery.csv"
    rows=[]
    if source.exists():
        with source.open(encoding="utf-8",newline="") as f:
            rows=list(csv.DictReader(f))
    # Optional public metadata extraction; YouTube may block unauthenticated requests.
    import yt_dlp
    seen=set()
    ranked=[]
    for row in rows[:30]:
        url=row.get("url","")
        p=urlparse(url)
        vid=parse_qs(p.query).get("v",[""])[0]
        if p.hostname not in ("www.youtube.com","youtube.com") or len(vid)!=11 or vid in seen:
            continue
        seen.add(vid)
        item={"rank":"","title":row.get("title",""),"url":"https://www.youtube.com/watch?v="+vid,
              "comments":"","views":"","likes":"","count_status":"unavailable",
              "reuse_rights":"NOT VERIFIED","review_status":"DO NOT CLIP WITHOUT RIGHTS"}
        try:
            with yt_dlp.YoutubeDL({"quiet":True,"no_warnings":True,"skip_download":True,
                                   "extract_flat":False,"noplaylist":True,"ignoreerrors":False,
                                   "socket_timeout":12}) as ydl:
                meta=ydl.extract_info(item["url"],download=False)
            if meta:
                item["title"]=meta.get("title") or item["title"]
                for src,dst in (("comment_count","comments"),("view_count","views"),("like_count","likes")):
                    value=meta.get(src)
                    if isinstance(value,int) and value>=0:
                        item[dst]=value
                if item["comments"]!="":
                    item["count_status"]="public metadata extracted (not independently verified)"
        except Exception as exc:
            item["count_status"]="unavailable: "+str(exc)[:130]
        ranked.append(item)
    ranked.sort(key=lambda r: (r["comments"]=="",-(r["comments"] if isinstance(r["comments"],int) else -1)))
    for i,row in enumerate(ranked,1):
        if row["comments"]!="":
            row["rank"]=i
    with (OUT/"ranked_by_comments.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS)
        w.writeheader()
        w.writerows(ranked)
    (OUT/"ranking_summary.json").write_text(json.dumps({
        "candidates":len(ranked),
        "ranked_with_comment_counts":sum(x["comments"]!="" for x in ranked),
        "unknown_comment_counts":sum(x["comments"]=="" for x in ranked),
        "note":"Best effort public metadata; unknown counts not estimated. Video URLs are NOT licensed media sources. No videos downloaded."
    },indent=2),encoding="utf-8")
    print("Comment ranking complete; known counts:",sum(x["comments"]!="" for x in ranked))

if __name__=="__main__":
    main()
