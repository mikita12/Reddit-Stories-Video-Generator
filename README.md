# YouTube Horror Shorts Pipeline

This README contains the full command sequence to create a new video in this workspace.

## Required background assets

Before running the pipeline, make sure these files exist in the project root:

- `scary_minecraft_bg.mp4` — background gameplay/video layer
- `bg_sound.wav` — background ambient/music layer

They are required by `build_video.py` and are used only as background video/audio for the final short.

## Install Whisper / WhisperX

You need FFmpeg and a Python virtual environment with WhisperX installed.

```bash
cd /home/mikita/Pulpit/yt
python3 -m venv whisperx-env
source whisperx-env/bin/activate
pip install -U pip
pip install openai-whisper
pip install whisperx
deactivate
```

If `whisperx` command is not found later, activate the same environment before running transcription.

## 0) Go to project folder

```bash
cd /home/mikita/Pulpit/yt
```

## 1) Create/Edit story text

Put your story in `raw/story_XXX.txt` with this structure:

- first line starts with `HOOK:`
- last line starts with `SOURCE:`

Example file to edit:

```bash
nano raw/story_002.txt
```

## 2) Generate narration audio (`out.wav`)

Use OpenAI TTS via `generate_audio.py`.
Make sure your OpenAI API key is available in environment variables (`OPENAI_API_KEY`) before running the command.

```bash
cd /home/mikita/Pulpit/yt
source whisper_env/bin/activate
export OPENAI_API_KEY="your_api_key_here"
python generate_audio.py --input raw/story_002.txt --output out.wav
deactivate
```

## 3) Generate word-level transcript (`out.json`) with WhisperX

Use the Python 3.10 WhisperX environment:

```bash
cd /home/mikita/Pulpit/yt
source whisperx-env/bin/activate
whisperx out.wav --model large-v3 --language en --align_model WAV2VEC2_ASR_LARGE_LV60K_960H --output_dir . --output_format json
deactivate
```

This should produce `out.json` in project root.

## 4) Build final vertical video (`final.mp4`)

```bash
cd /home/mikita/Pulpit/yt
python build_video.py
```

The script expects these files:

- `scary_minecraft_bg.mp4`
- `bg_sound.wav`
- `out.wav`
- `out.json` (or fallback `out.wav.json`)

## 5) Quick verification

```bash
cd /home/mikita/Pulpit/yt
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 out.wav
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 final.mp4
```

## 6) Move final file to archive folder

```bash
cd /home/mikita/Pulpit/yt
mv final.mp4 videos/final_$(date +%F_%H-%M-%S).mp4
```

---

## One-shot run (copy/paste)

```bash
cd /home/mikita/Pulpit/yt && \
source whisper_env/bin/activate && \
python generate_audio.py --input raw/story_002.txt --output out.wav && \
deactivate && \
source whisperx-env/bin/activate && \
whisperx out.wav --model large-v3 --language en --align_model WAV2VEC2_ASR_LARGE_LV60K_960H --output_dir . --output_format json && \
deactivate && \
python build_video.py
```

If WhisperX model/alignment names differ on your machine, run:

```bash
source whisperx-env/bin/activate
whisperx --help
deactivate
```
