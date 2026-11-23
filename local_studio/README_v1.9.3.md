# GTA 6 Clipping Studio v1.9.3 — 9:16 and 16:9 exports

New release branch based on v1.9.2; all earlier branches are preserved.

## New export options
Section 6 (highlight recommendations) and Section 8 (batch Shorts production) now offer:
- **9:16 vertical (Shorts)** — existing 480×854 centre-cropped output.
- **16:9 landscape (YouTube)** — new 1280×720 landscape output, with proportional scaling and padding to prevent stretching.
- **Both formats** — create one separate MP4 per aspect ratio for each successfully processed clip.

Example batch outputs for five clips when Both is selected:
`short_01_9x16.mp4`, `short_01_16x9.mp4`, ... `short_05_9x16.mp4`, `short_05_16x9.mp4`. Up to 10 separate MP4s are included in the ZIP if all five sources are available and both renders succeed.

Section 3 still downloads source intervals in their native aspect ratio; the format conversion happens in Sections 6 and 8. The Section 7 editor retains its existing controls.

## Usage
Download and extract v1.9.3 into a new folder. Run `local_studio/start_windows.bat`. Analyze and download eligible source clips in Section 3. Go to Section 8, choose Video export format, and produce your clips. Or export a single analyzed highlight from Section 6.

## Notes
- 16:9 output is currently 720p; this does not upscale to genuine 4K. The source may be downloaded at higher resolution separately.
- The 9:16 mode is unchanged in resolution and crop.
- Export may fail depending on FFmpeg, source formats and system resources; Windows runtime tests have not been confirmed.
