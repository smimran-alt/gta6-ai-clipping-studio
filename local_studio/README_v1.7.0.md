# GTA 6 Clipping Studio v1.7.0

Separate release branch based on v1.6.0. Previous releases remain unchanged.

## Run on Windows
1. Extract the ZIP and double-click `local_studio/start_windows.bat`.
2. To enable automatic captions and voiceover, open PowerShell in the extracted project and run:
   `py -m pip install -r local_studio/requirements_editing_optional.txt`
3. In the app, save a video or create a highlight. Scroll to **7. Captions, AI commentary and Shorts editor**.
4. Choose a source, start time, optional 9:16 crop, title overlay, captions and voiceover.
5. For automatic captions, select **Generate automatic speech captions** then click **Transcribe speech into captions**. The first run downloads a Whisper model.
6. For AI script drafting, enter your own scene notes, check **Use OpenAI**, and supply an API key. API requests may incur charges. The key is not written to the project files.
7. Alternatively, generate a simple non-AI script without a key. Review the script before publishing.
8. For spoken narration, enable **Generate spoken voiceover**, which requires pyttsx3. Voiceover replaces the original soundtrack.
9. Click **Render edited 30-second MP4**. The output is `local_output/editor/edited_short.mp4`.

## Limits
- Captions are generated from speech, not visual gameplay. Silent clips may yield no captions.
- The OpenAI commentary option writes a script using your supplied scene notes/transcript, not visual interpretation of the video.
- Original audio is replaced when narration is enabled. Mixing is planned for a future version.
- FFmpeg must be installed with ffprobe. Burning SRT captions requires an FFmpeg build with the subtitles/libass filter; title overlay requires drawtext support.
- Editor outputs are verified for existence and duration. Windows-specific success is not yet confirmed.
- Only use footage you are authorized to edit and publish.
