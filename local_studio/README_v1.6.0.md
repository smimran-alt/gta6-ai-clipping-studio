# GTA 6 Clipping Studio v1.6.0 — Highlight Recommendations

A new release branch based on v1.5.0. Previous branches are preserved.

## Windows quick start
1. Download the release/v1.6.0 ZIP and extract it into a new folder.
2. Open `local_studio/start_windows.bat`.
3. Confirm FFmpeg and ffprobe are installed.
4. Scroll to **6. Automatic 30-second highlight recommendations**.
5. Upload your own authorized gameplay recording (ideally longer than 30 seconds) or choose an existing saved video.
6. Select how many recommendations to generate (1–10) and click **Analyze video and recommend 30-second highlights**.
7. Review ranked 30-second windows, preview the chosen time, and click **Export selected 30-second highlight**.
8. Download the verified MP4 using **Download recommended 30-second MP4**.

## What the detector actually does
- Uses FFmpeg scene-change detection on video sampled at 2 frames per second.
- Measures average and peak audio energy.
- Scores candidate 30-second windows and returns non-overlapping top suggestions.
- Exports a 480×854 vertical MP4 by default; results are in `local_output/highlights`.
- Analyzes at most the first 20 minutes of the local source to limit processing time.

## Important limits
This is a **heuristic highlight detector**, not a trained GTA-specific computer vision model. It cannot reliably identify police pursuits, crashes, explosions, or gameplay events by meaning. A high score does not predict virality. Videos with quiet audio may rank mainly by scene changes. A 30-second source has only one possible 30-second clip.

The workflow requires local footage you have permission to use. Finding a video on YouTube or Twitch does not establish download or reuse rights. The release includes a GitHub Actions smoke test, but Windows behavior requires local verification.
