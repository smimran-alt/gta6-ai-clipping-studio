# GTA 6 Clipping Studio v1.9.1

New branch from v1.9.0; all previous releases remain unchanged.

## Section 3 improvements
- Added **total_seconds**, **reason_for_selection** and **approx_size_MB** to the recommendations table.
- Approximate size is calculated using a transparent bitrate assumption per selected resolution: 360p 1 Mbps, 480p 1.8 Mbps, 720p 3.5 Mbps, 1080p 6 Mbps, 1440p 12 Mbps and 2160p 25 Mbps, plus 5% overhead. This is not a real file size or an assurance of a particular download size.
- New **Recommended clips download quality** selector: 360p, 480p, 720p, 1080p, 1440p (2K), 2160p (4K).
- **Maximum size per downloaded segment (MB)** setting (50–2000 MB).
- Selected quality and size limit are passed into the batch downloader.
- Batch results report **actual_size_MB** and **actual_seconds** for each successful clip.
- Section 4 manual source download also supports 1080p, 1440p and 2160p.

## Important limitations
- 4K is only possible if the source platform offers a downloadable 2160p stream; the studio cannot invent native 4K resolution.
- Downloaded 4K may take longer and consume more storage. Source format selection and transcoding may fail on certain hosts or machines.
- The size estimate is based on assumed bitrates and can differ substantially from actual results. No online bitrate metadata is fetched for estimates.
- Existing Section 8 exports vertical 480x854 video; its editing output is not 4K even if the downloaded source is 4K.
- All video downloads and republishing require appropriate rights.
- Windows runtime testing has not been confirmed.

## Start
Extract the release ZIP to a new folder and run `local_studio/start_windows.bat`. Search and select a video, analyze comments, choose resolution in Section 3 and batch-download recommended clips.
