# v1.9.4 — Fix missing vertical downloads

Based on v1.9.3. All previous release branches remain preserved.

## What changed
- Section 8 renders 9:16 and 16:9 independently. Failure in one aspect ratio no longer discards a successful export of the other.
- Verifies 9:16 output is 480×854 and 16:9 output is 1280×720 using ffprobe.
- Adds individual **Download short_XX_9x16.mp4** and **Download short_XX_16x9.mp4** buttons after export.
- Successful formats are included in the ZIP even when other formats fail. Per-format errors are shown in the results table.

## How to use
1. Extract v1.9.4 in a new folder and launch `local_studio/start_windows.bat`.
2. Select and analyze a video, then download recommended segments in Section 3.
3. Go to Section 8, select **9:16 vertical (Shorts)** or **Both formats**.
4. Confirm editing rights and click **Produce all available 30-second Shorts**.
5. Download each vertical file individually, or download the ZIP. Look for filenames ending in `_9x16.mp4`.

Section 3 still downloads original-aspect source footage; vertical conversion occurs in Section 8. A successful Section 3 download is not itself a vertical file.

Runtime validation on the user's Windows laptop has not been completed.
