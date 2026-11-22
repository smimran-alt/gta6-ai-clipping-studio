# GTA 6 Clipping Studio v1.8.0 — Most-Discussed Moments

This release is a new branch based on v1.7.0. All earlier versions are preserved.

## Use on Windows
1. Download the v1.8.0 ZIP and extract it to a new folder.
2. Run `local_studio/start_windows.bat`.
3. Choose **YouTube** or **All platforms** and click **Find GTA 6 videos**. You do not need to paste a link.
4. Scroll to **3. Find the most-discussed 30-second moments automatically**.
5. Choose the number of videos to analyze (up to 10) and click **Analyze most-discussed GTA 6 moments automatically**.
6. The app fetches available video-level comment totals and samples public YouTube comments. Timestamp references such as `2:15` count toward the 02:00–02:30 window.
7. Review the ranked windows and video preview. Confirm you have permission to download/reuse the footage, then click **Download this recommended 30-second segment**.
8. The app validates duration and saves the result under `local_output/most_discussed/`. Download it from the app.

## Accuracy and platform limits
- YouTube does not provide an official per-30-second comment count. This is an estimate based on *explicit timestamp mentions* in an accessible sample of comments, one vote per comment per 30-second bucket.
- Comment retrieval via yt-dlp is best-effort and can be blocked, incomplete or slow. If comments cannot be fetched, the app says so. It does not invent data.
- Other platforms are currently discovery sources, not timestamp-comment sources.
- YouTube public comment totals are used to rank candidate videos when available.
- Partial downloading depends on source host support. The app rejects downloads that do not measure approximately 30 seconds.
- For videos without accessible timestamped comments, use section 6 for scene/audio-based highlights.
- Do not download or republish content without necessary rights or permission.
