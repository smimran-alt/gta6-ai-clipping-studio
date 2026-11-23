# v1.9.6 — More sensational moments + two downloadable sets

Preserves earlier branches and the general highlight mode.

## Sensational AI
Section 6 AI mode now includes more descriptive prompts for pileups, vehicle flips, ramp jumps, near misses and roadblocks. It samples nine frames per candidate rather than five, and re-ranks up to 20 candidates. The **Sensational moments emphasis** slider (40–90%, default 70%) shifts ranking toward spectacle versus car pursuit.

This uses CLIP frame-to-text similarity. It is not a validated event detector. Candidates are preselected using motion/audio proxies, and only the first 20 minutes of the local source are considered. AI similarity is not proof of any particular event.

## Two separate export sets
After analyzing a local video in Section 6, click **Generate BOTH sets for all recommended clips**.
- `vertical_9x16.zip` contains 480×854 vertical MP4 clips.
- `horizontal_16x9.zip` contains 1280×720 horizontal MP4 clips.
- Individual MP4 download buttons also appear for each successful file.
- Each aspect ratio is rendered independently. A failed render does not discard successful files in the other format.
- Exports are saved to `local_output/highlight_sets/<source-id>/vertical_9x16` and `horizontal_16x9`.

## Windows setup
1. Extract this release into a new folder.
2. Install optional AI packages in the Streamlit Python environment: `python -m pip install -r local_studio/requirements_ai.txt`
3. Start `local_studio/start_windows.bat`.
4. Upload or choose an authorized source in Section 6, choose **Car chases & sensational moments (AI)**, adjust sensational emphasis, and analyze.
5. Click **Generate BOTH sets for all recommended clips** and download the two ZIPs.

No Windows runtime testing has been confirmed.
