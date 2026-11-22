# v1.9.2 — 12-criterion viral clip selection rubric

Based on v1.9.1; previous release branches are preserved.

## Rubric (100 possible points)
1. First 2-second hook — 15
2. Action intensity — 15
3. Surprise/unexpected event — 12
4. Audience retention potential — 12
5. Emotional reaction — 10
6. Storytelling — 8
7. Visual quality — 7
8. Trending-topic relevance — 6
9. Replay potential — 5
10. Comment/share potential — 4
11. Audio excitement — 3
12. Clip duration/editability — 3

## Current implementation
Section 6 ranks nonoverlapping 30-second windows from a locally available video using scene-change frequency, initial 2-second scene/audio activity, distribution of cuts throughout the window, audio peak energy, and clip duration. It generates a per-criterion breakdown. Only the first, second, fourth, eleventh and twelfth criteria have rough observable proxies; all remaining criteria are marked **unassessed**. The score shown is normalized to the **38 observable weight points**, not presented as a verified score out of 100. If audio is unavailable, coverage decreases to 35. A high proxy score is not a guarantee of virality.

The system does **not** currently identify explosions, crashes, stunts, NPC actions, humour, emotion, narrative arc, visual clarity, topical trends or audience behaviour. Proper semantic scoring would require an additional vision/audio model and external trend data, which this release does not include.

## How to use
Extract v1.9.2, run `local_studio/start_windows.bat`, and provide an authorized source video for Section 6. Click **Analyze video and recommend 30-second highlights**, inspect the rubric breakdown, and export chosen highlights. Existing Section 3 remains a separate timestamped-comment ranking; it does not automatically apply the full rubric to remote videos. The existing analyzer processes up to 1,200 seconds of a local source, so it does not inspect every moment of longer videos.

Code committed; Windows runtime tests have not been confirmed.
