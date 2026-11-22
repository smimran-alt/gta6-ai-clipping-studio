"""Find potential openly licensed gaming videos. Metadata is NOT legal clearance."""
import csv
import json
from pathlib import Path
import requests
import re

GTA_PATTERN = re.compile(r'(?i)(grand[ -]?theft[ -]?auto|\\bgta\\s*(?:[1-6]|i{1,3}|iv|v|vi|online|vice city|san andreas)\\b)')
GAMEPLAY_PATTERN = re.compile(r'(?i)(gameplay|walkthrough|playthrough|longplay|free[ -]?roam|mission|police chase|car theft|game footage)')
EXCLUDE_PATTERN = re.compile(r'(?i)(trailer|advert|commercial|movie|film|review|reaction|top ?\\d+|compilation|soundtrack|music video|news|announcement|daz studio)')

def relevant(row):
    title = str(row.get('title',''))
    return bool(GTA_PATTERN.search(title) and GAMEPLAY_PATTERN.search(title) and not EXCLUDE_PATTERN.search(title))

OUT = Path(__file__).resolve().parents[1] / "output"
OUT.mkdir(exist_ok=True)
HEADERS = {"User-Agent": "GTAClippingStudio/2.1 (license candidate research; contact via GitHub)"}
FIELDS = ["title","source","page_url","license","creator","media_url","license_evidence","review_status","notes"]

def archive_candidates():
    rows=[]
    for term in ['grand theft auto gameplay', 'grand theft auto longplay', 'gta san andreas gameplay', 'gta vice city gameplay']:
        params={"q": f'({term}) AND mediatype:movies AND licenseurl:*',
                "fl[]": ["identifier","title","creator","licenseurl"],
                "rows":15,"page":1,"output":"json"}
        try:
            r=requests.get("https://archive.org/advancedsearch.php",params=params,headers=HEADERS,timeout=25)
            r.raise_for_status()
            for item in r.json().get("response",{}).get("docs",[]):
                identifier=item.get("identifier","")
                lic=item.get("licenseurl","")
                if not identifier or not lic: continue
                rows.append({"title":str(item.get("title","")),"source":"Internet Archive",
                    "page_url":"https://archive.org/details/"+identifier,"license":str(lic),
                    "creator":str(item.get("creator","")),"media_url":"",
                    "license_evidence":"Uploader-provided archive metadata",
                    "review_status":"NEEDS MANUAL RIGHTS REVIEW",
                    "notes":"Check exact file, uploader authority, game publisher rights, music, commercial terms"})
        except Exception as exc:
            (OUT / "licensed_search_errors.txt").open("a",encoding="utf-8").write(f"Archive {term}: {exc}\n")
    return rows

def commons_candidates():
    rows=[]
    api="https://commons.wikimedia.org/w/api.php"
    for term in ['grand theft auto gameplay filetype:video', 'gta san andreas gameplay filetype:video']:
        try:
            r=requests.get(api,params={"action":"query","generator":"search","gsrsearch":term,
                "gsrnamespace":6,"gsrlimit":20,"prop":"imageinfo","iiprop":"extmetadata|url",
                "format":"json"},headers=HEADERS,timeout=25)
            r.raise_for_status()
            for item in r.json().get("query",{}).get("pages",{}).values():
                info=(item.get("imageinfo") or [{}])[0]
                meta=info.get("extmetadata",{})
                lic=meta.get("LicenseUrl",{}).get("value","") or meta.get("LicenseShortName",{}).get("value","")
                rows.append({"title":item.get("title",""),"source":"Wikimedia Commons",
                    "page_url":"https://commons.wikimedia.org/wiki/"+item.get("title","").replace(" ","_"),
                    "license":lic,"creator":"","media_url":"",
                    "license_evidence":"Commons file page metadata",
                    "review_status":"NEEDS MANUAL RIGHTS REVIEW",
                    "notes":"Verify author and licence on file page; third-party game IP may not be cleared"})
        except Exception as exc:
            (OUT / "licensed_search_errors.txt").open("a",encoding="utf-8").write(f"Commons {term}: {exc}\n")
    return rows

def main():
    rows=archive_candidates()+commons_candidates()
    relevant_rows=[row for row in rows if relevant(row)]
    unique={row["page_url"]:row for row in relevant_rows}
    with (OUT/"licensed_candidates.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(unique.values())
    (OUT/"licensed_discovery_summary.json").write_text(json.dumps({
        "candidate_count":len(unique),
        "total_unfiltered":len(rows),
        "excluded_irrelevant":len(rows)-len(relevant_rows),
        "rights_verified":0,
        "automatic_downloads":0,
        "note":"Candidate licences are metadata claims, not verified clearance. No automatic reuse."
    },indent=2),encoding="utf-8")
    print(f"Found {len(unique)} GTA gameplay candidates after filtering {len(rows)} search results; none approved automatically")

if __name__=="__main__":
    main()
