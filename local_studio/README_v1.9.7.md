# GTA 6 Clipping Studio v1.9.7 — 60-second clips and vertical download fixes

## New in Section 6
- Choose **Clip length: 30 or 60 seconds** (60 seconds by default).
- General highlight scoring and optional sensational car-chase AI now use the chosen duration.
- Individual highlights and both bulk sets export the chosen duration.
- **Generate BOTH sets** creates independent vertical 480×854 and landscape 1280×720 videos. Download each ZIP separately, or each individual MP4.
- Independent errors per format are shown for individual renders, rather than hiding a successful vertical render behind a failed horizontal one.
- Previously cached download results are cleared before each new bulk render.
- Each exported file is checked for dimensions and duration.

## Important: source length
Section 3 still downloads 30-second segments. You cannot generate a genuine 60-second highlight from one of those segments. To generate 60-second clips, upload or select an original video of at least 60 seconds in **Section 6**. Prefer several minutes of gameplay to get multiple distinct clips.

## How to use
1. Extract v1.9.7 to a fresh folder and run `local_studio/start_windows.bat`.
2. Optional: `py -m pip install -r local_studio/requirements_ai.txt` for AI mode.
3. In Section 6 upload a longer source video and click **Save uploaded video for analysis**.
4. Choose **60** seconds, select **Car chases & sensational moments (AI)**, and analyze.
5. Click **Generate BOTH sets for all recommended clips**.
6. Download **Vertical 9:16 ZIP** and **Horizontal 16:9 ZIP** separately. Each set has individually downloadable MP4 files.

If the vertical ZIP is absent, check the failure table below the buttons. The FFmpeg error for that clip/format should be visible. Confirm `ffmpeg -version` and `ffprobe -version` in Command Prompt. No files are generated in this chat; the application generates them on your computer.

## Scope
Section 3 comment-driven downloads and Section 8's existing 30-second rights-aware editor are unchanged. The 60-second feature applies to Section 6 highlight analysis and export only. Windows execution has not been verified.
