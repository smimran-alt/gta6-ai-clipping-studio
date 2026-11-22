# GTA 6 Clipping Studio v1.8.1 — Synchronized Video Selection

This is a new patch release based on v1.8.0. Previous versions remain unchanged.

## Fixed
- The **Choose video** dropdown now tracks the selected video by its stable source URL, not its position in the search table.
- **Preview selected video**, **Most-discussed moments**, and **Generate clips** now reference that same selected URL.
- The comment section analyzes **only the selected video**. It no longer shows separate, automatically ranked videos that could contradict the dropdown selection.
- Comment results are cached separately for each source URL. Switching videos shows that video's own previous report, if any, and otherwise prompts for analysis.
- Download preview is only displayed when it belongs to the currently selected video.
- Timestamp display now uses HH:MM:SS so long gameplay recordings do not show confusing times such as 239:00.

## Windows
Extract the v1.8.1 ZIP to a new folder and launch `local_studio/start_windows.bat`.
Search GTA 6, select a video, and check that the preview and section 3 show the exact same title. Run comment analysis for that selected video. Section 4 will use the same selected video for downloading clips.

## Limitations
Comment analysis currently supports YouTube only, and public comments may be inaccessible. The later local-file editing/highlight sections intentionally allow choosing a separate local video file.
