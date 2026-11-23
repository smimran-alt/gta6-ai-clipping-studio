# GTA 6 Clipping Studio v1.9.5 — Car Chase & Sensational AI

v1.9.5 adds an optional **Car chases & sensational moments (AI)** selection mode to Section 6. The existing general selection mode, 12-point rubric, 9:16 vertical and 16:9 landscape exports, and all earlier releases are retained.

## Setup on Windows
1. Extract this version to a NEW folder.
2. Open Command Prompt in the extracted folder.
3. Install the optional AI dependencies using the same Python environment as Streamlit:
   `python -m pip install -r local_studio/requirements_ai.txt`
4. Start `local_studio/start_windows.bat`.
5. Upload or choose a longer source video in Section 6.
6. Choose **Car chases & sensational moments (AI)** and click Analyze.
7. Review the suggested clips, then export 9:16, 16:9, or both.

The first AI run downloads pretrained CLIP weights from Hugging Face (roughly 600 MB) and requires an internet connection. Subsequent runs reuse the local cache. CPU-only operation is supported but may be slow.

## What the AI actually does
- Takes 5 frames from each of the 12 highest-ranked non-overlapping 30-second candidate windows, chosen using the existing scene-change and audio heuristic.
- Uses OpenAI CLIP image-text similarity against prompts describing car pursuits, police chases, collisions, stunts, explosions and ordinary driving.
- Ranks those candidates using visual similarity and existing hook/pacing/audio proxies.
- Displays a reason and separate chase/sensational similarity scores.
- These are **relative similarity estimates, not calibrated probabilities**. It cannot guarantee that an actual chase or crash occurs; sampled frames may miss events.
- This is not full-video semantic scanning: the local video analyzer still examines only the first 20 minutes, and AI only re-ranks preselected candidates. No automatic clip recognition is claimed beyond these limits.

If you see an error about missing torch/transformers/Pillow, install `requirements_ai.txt` into the Python environment used to run Streamlit.

Windows runtime tests have not been completed.
