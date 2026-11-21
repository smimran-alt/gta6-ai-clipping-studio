# GTA 6 AI Clipping Studio v2 — GitHub Actions

This is an **automated discovery + rights-gated clipping prototype**. It preserves v1 files. It does NOT download arbitrary YouTube videos, guarantee fair use, or automatically post to YouTube.

## What it does
- Daily/manual public Bing RSS search for YouTube video links without account login or API keys. Results are in `output/discovery.csv`. Search availability is not guaranteed; no verified engagement metrics or viral scoring are available.
- Reads `sources/approved.json`; only renders entries with a nonempty, explicit rights basis and permission evidence.
- Downloads only direct HTTPS media files from approved hosts listed in `APPROVED_MEDIA_HOSTS` (GitHub Actions repository variable). This is not a way to bypass source-site access rules.
- Creates 720x1280 MP4 Shorts with an original English spoken commentary track (offline espeak-ng), title overlay and burned-in commentary caption. Audio is spoken commentary only unless you supply independently licensed music.
- Produces MP4 files and `output/report.json` as downloadable GitHub Actions artifacts. Human review required before YouTube upload.

## Configure
1. No YouTube account, Google Cloud project, or API key is required for public RSS discovery.
2. Create repository **variable** `APPROVED_MEDIA_HOSTS` with comma-separated HTTPS hostnames that you control or have approval to download from (e.g. `github.com,objects.githubusercontent.com` for your own GitHub release assets). Avoid arbitrary file-hosting URLs.
3. Edit `sources/approved.json` to add an approved source, with written rights evidence. Example:

```json
{
  "sources": [
    {
      "title": "My GTA gameplay escape analysis",
      "url": "https://YOUR_APPROVED_HOST/path/to/your-owned-video.mp4",
      "rights_basis": "I recorded and own this gameplay footage",
      "permission_evidence": "My own capture recorded on 2026-11-21; game publisher policies still apply",
      "start_seconds": 15,
      "duration_seconds": 20,
      "commentary": "The driver commits to the highway too early. Watch the police roadblock ahead: the safer strategy would be to change direction before the turnoff.",
      "licensed_music_url": "",
      "music_permission_evidence": ""
    }
  ]
}
```

4. Open **Actions → GTA Clipping Studio v2 → Run workflow**. For scheduled runs, the workflow runs daily (UTC) if GitHub enables schedules on this repository.
5. After a successful run, click **gta-studio-v2-results** under Artifacts and download the ZIP.

## Important limitations
- Public RSS discovery returns only available titles and links, **not permission to download/reuse**. Search engines can return no results or block automated requests.
- Public RSS search does not provide verified views, likes, comments, engagement ranking, or viral moment detection.
- Clip start time is supplied by the user. AI visual highlight detection and automatic transcript-driven selection are future work.
- Voice uses offline English speech synthesis; it is not a natural-sounding premium AI voice.
- The prototype uses original user-supplied analytical commentary, not AI-written commentary. This avoids fabricated analysis of unseen footage.
- Captions show your commentary as a readable static text block, not word-by-word timed subtitles.
- Music is not automatically fetched or mixed in v2; use the commentary-only output until licensed-music mixing is implemented.
- Rights basis/evidence are **self-attested**, not independently verified. You must check gameplay publisher rules, third-party material, music rights and YouTube requirements.
- GitHub-hosted runners have limits. Videos over 250 MB are rejected and clips are capped at 60 seconds.
