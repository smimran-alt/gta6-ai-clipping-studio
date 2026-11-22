# GTA 6 Clipping Studio v1.9.0 — Rights-aware Shorts production

New branch based on v1.8.5. All previous releases remain unchanged.

## Windows setup
1. Extract the release ZIP into a new folder.
2. Double-click `local_studio/start_windows.bat`. FFmpeg and ffprobe must be installed.
3. For automatic speech captions and spoken narration, install optional packages:
   `py -m pip install -r local_studio/requirements_editing_optional.txt`
4. Search for GTA 6 videos. Select one, analyze timestamped comments, confirm footage rights and download recommended segments in Section 3.
5. Open **8. Rights-aware automatic Shorts production**. This section uses only successfully downloaded segments for the selected video.
6. Click **Scan downloaded clips for copyright and watermark risk** to see warnings. This is NOT copyright clearance.
7. Choose a colour preset; optionally upload a music file you are licensed to use, write scene notes for original commentary, enable text-to-speech, speech subtitles and fades.
8. Confirm footage rights and click **Produce all available 30-second Shorts**. Outputs are separate `short_01.mp4` through `short_05.mp4` when all five source clips were successfully downloaded and processed, plus `produced_shorts.zip` and a JSON status report.

## Rights and detection limits
- The risk scanner checks for audio tracks, nearly identical frames **within the source video**, and static corners that *may* contain overlays. It does NOT identify songs, compare against copyrighted reference works, verify licenses, or determine legal status.
- Source audio is removed in processed exports by default. This removes *all* original audio, not just music; it cannot isolate and selectively remove an unlicensed song while keeping speech or sound effects.
- Uploaded replacement music must be licensed by the user. The studio does not supply a licensed music library.
- Commentary uses user-supplied scene notes. Optional OpenAI API script generation is not visual video analysis and may incur charges. Local pyttsx3 voiceover is optional.
- Whisper subtitles are generated from spoken audio, not gameplay events. Whisper may download a model.
- Smart reframe currently means centre-crop to 9:16, not subject-tracking AI. Transitions are fade-in/fade-out, not between multiple shots.
- Watermark review flags possible static corners; it does not prove ownership or automatically remove third-party watermarks. The previous authorized manual region-blur option remains in Section 3.
- Each segment is saved as its own file. If the source host blocks some partial downloads, the app reports failed segments rather than inventing missing files.
- Outputs and licenses should be reviewed before publication. No Content ID or platform copyright guarantee is provided.

## Validation
GitHub Actions workflow `.github/workflows/validate-local-v1.9.0.yml` runs Python compilation and synthetic FFmpeg tests. Windows functionality, Whisper, and TTS require local verification.
