# v1.8.2 — Automatic Batch Download

Preserves all prior release branches.

1. Search for GTA 6 videos and select a video.
2. Analyze its timestamped public comments.
3. Under **Automatically download recommended clips**, confirm you have the necessary rights.
4. Click **Download all recommended 30-second clips** once.
5. The app attempts each suggested segment, records success or failure, saves validated segments under `local_output/most_discussed/batch`, and creates `local_output/most_discussed/recommended_clips.zip` with successful downloads.

No per-clip selection is required. Partial downloading depends on the video host and FFmpeg. A failed segment does not stop subsequent attempts. The app cannot download copyrighted footage for reuse without permission. The batch feature runs on the user's Windows machine; it is not a cloud download service. Testing on Windows is still required.
