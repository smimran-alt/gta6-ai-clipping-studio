# v1.8.4 — Explain recommendations and optional blur

This release is based on v1.8.3 and preserves all previous release branches.

## Section 3
The recommendations table now includes **reason_for_selection**, which explains whether the segment has the highest timestamp mention count or is ranked by the number of sampled mentions. These are evidence-based ranking reasons, not claims that the video contains a crash, stunt or other specific event.

## Optional localized blur
Under **Automatically download recommended clips**, users with the necessary rights may enable **Blur a selected logo/watermark area after download (keep originals)**. Set left/top/width/height as percentages of the video frame. The app first downloads and verifies each source segment, then blurs the selected rectangle and adds the edited version to the ZIP. Original clips remain in the batch folder. If an edit fails, the original is retained and the error is reported.

The tool does not remove watermarks from the remote source before download. Blurring cannot reconstruct image details beneath a logo. It is disabled by default. Respect creator attribution and license terms.

## Start
Extract the v1.8.4 ZIP and run `local_studio/start_windows.bat`. Test with one authorized video before batch processing. Windows runtime validation has not been confirmed.
