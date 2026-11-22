# GTA 6 Clipping Studio v1.5.0 — Multi-Platform Discovery

This release extends v1.4.0 without changing previous release branches.

## Run on Windows
Extract the ZIP, open `local_studio`, double-click `start_windows.bat`, and visit the local Streamlit URL.

## Find and preview videos
1. Choose **All platforms** or YouTube, Twitch, Vimeo, Dailymotion, Internet Archive.
2. Click **Find GTA 6 videos**. The result table contains **platform**, **title**, **views**, **comments**, **availability**, and **Watch video** link.
3. Choose a result. Click **▶ Watch video on [platform]** to open the original video page. YouTube and some Vimeo/Dailymotion videos may also preview inline; Twitch and Archive use external links.
4. Click **Check selected video's availability** to test public metadata. This does **not** guarantee that the video can play, download, or be reused.
5. For authorized videos, use the v1.4.0 segment clipping controls.

## Important limitations
- YouTube discovery uses yt-dlp public search; Twitch, Vimeo and Dailymotion use Bing public RSS search; Archive uses its public search API. Results depend on the source and can be empty, outdated or inaccessible.
- A title matching GTA 6 is not proof of genuine GTA 6 gameplay.
- Public search may omit results, and not all platforms support inline playback or downloads.
- The user must have permission to download and reuse video content. Adding commentary alone does not grant those rights.
- The app retains the v1.4.0 render and local output workflow; no login or API key is required for public discovery.
