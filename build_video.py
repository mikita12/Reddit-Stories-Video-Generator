#!/usr/bin/env python3

from __future__ import annotations

import json
import random
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BG_VIDEO = ROOT / "scary_minecraft_bg.mp4"
BG_SOUND = ROOT / "bg_sound.wav"
NARRATION = ROOT / "out.wav"
TRANSCRIPT_JSON = ROOT / "out.wav.json"
WHISPERX_JSON = ROOT / "out.json"
OUTPUT = ROOT / "final.mp4"


@dataclass
class WordItem:
    start: float
    end: float
    text: str


@dataclass
class SubtitleItem:
    start: float
    end: float
    text: str


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)


def _parse_timecode(value: str) -> float:
    hh, mm, rest = value.split(":")
    ss, ms = rest.split(",")
    return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0


def load_json(path: Path) -> list[WordItem]:
    data = json.loads(path.read_text(encoding="utf-8"))

    words: list[WordItem] = []

    # WhisperX format (preferred): `word_segments` or segment-level `words`.
    if isinstance(data.get("word_segments"), list):
        for item in data["word_segments"]:
            text = str(item.get("word", "")).strip()
            if not text:
                continue
            start = float(item.get("start", 0.0))
            end = float(item.get("end", start))
            words.append(WordItem(start=start, end=max(start, end), text=text))
        return words

    if isinstance(data.get("segments"), list):
        for seg in data["segments"]:
            seg_words = seg.get("words") or []
            if isinstance(seg_words, list) and seg_words:
                for item in seg_words:
                    text = str(item.get("word", "")).strip()
                    if not text:
                        continue
                    start = float(item.get("start", seg.get("start", 0.0)))
                    end = float(item.get("end", start))
                    words.append(WordItem(start=start, end=max(start, end), text=text))
            else:
                text = str(seg.get("text", "")).strip()
                if not text:
                    continue
                start = float(seg.get("start", 0.0))
                end = float(seg.get("end", start))
                words.append(WordItem(start=start, end=max(start, end), text=text))
        return words

    # whisper.cpp legacy format
    transcription = data.get("transcription", [])
    for item in transcription:
        ts = item.get("timestamps") or {}
        text = str(item.get("text", ""))
        if not text.strip():
            continue
        start = _parse_timecode(ts["from"])
        end = _parse_timecode(ts["to"])
        words.append(WordItem(start=start, end=max(start, end), text=text))

    return words


def _format_group_text(tokens: list[str]) -> str:
    text = "".join(tokens).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([\(\[\{])\s+", r"\1", text)
    text = re.sub(r"\s+([\)\]\}])", r"\1", text)
    text = text.replace(".", "")
    text = _clean_rendered_word(text)
    return text

def _clean_rendered_word(text: str) -> str:
    # Keep only letters/digits/space and '?' (remove all other punctuation).
    cleaned = re.sub(r"[^\w\s?]", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def build_subtitles(words: list[WordItem]) -> list[SubtitleItem]:
    if not words:
        return []

    subtitles: list[SubtitleItem] = []
    for i, w in enumerate(words):
        text = re.sub(r"\s+", " ", w.text.strip()).upper()
        text = _clean_rendered_word(text)
        if not text:
            continue

        start = max(0.0, w.start)
        end = max(start + 0.05, w.end)

        # One-word-at-a-time: current word disappears when next starts.
        if i + 1 < len(words):
            next_start = max(start + 0.05, words[i + 1].start)
            end = min(end, next_start)

        subtitles.append(SubtitleItem(start=start, end=end, text=text))

    return subtitles


def _escape_ass_text(text: str) -> str:
    escaped = text
    escaped = escaped.replace("\\", r"\\")
    escaped = escaped.replace("{", r"\{")
    escaped = escaped.replace("}", r"\}")
    return escaped


def _seconds_to_ass_time(value: float) -> str:
    total_cs = max(0, int(round(value * 100)))
    h = total_cs // 360000
    rem = total_cs % 360000
    m = rem // 6000
    rem %= 6000
    s = rem // 100
    cs = rem % 100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _write_ass_subtitles(path: Path, subtitles: list[SubtitleItem]) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans,88,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,6,0,5,60,60,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines = [header]
    for sub in subtitles:
        start = max(0.0, sub.start)
        end = max(start + 0.01, sub.end)
        dur = end - start
        fade_in_ms = int(min(70, max(20, dur * 250)))
        fade_out_ms = int(min(90, max(30, dur * 350)))
        text = _escape_ass_text(sub.text)
        ass_text = (
            "{\\fad(" + str(fade_in_ms) + "," + str(fade_out_ms) + ")"
            "\\fscx108\\fscy108\\t(0,120,\\fscx100\\fscy100)}"
            + text
        )
        lines.append(
            "Dialogue: 0,"
            f"{_seconds_to_ass_time(start)},"
            f"{_seconds_to_ass_time(end)},"
            f"Default,,0,0,0,,{ass_text}\n"
        )

    path.write_text("".join(lines), encoding="utf-8")


def _escape_filter_path(path: Path) -> str:
    s = str(path)
    s = s.replace("\\", r"\\")
    s = s.replace(":", r"\:")
    s = s.replace("'", r"\'")
    return s


def build_ffmpeg_command(
    narration_duration: float,
    background_start: float,
    filter_complex: str,
) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-stream_loop",
        "-1",
        "-ss",
        f"{background_start:.3f}",
        "-t",
        f"{narration_duration:.3f}",
        "-i",
        str(BG_VIDEO),
        "-i",
        str(NARRATION),
        "-stream_loop",
        "-1",
        "-i",
        str(BG_SOUND),
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "veryslow",
        "-crf",
        "0",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "alac",
        "-movflags",
        "+faststart",
        "-shortest",
        str(OUTPUT),
    ]


def main() -> int:
    required = [BG_VIDEO, BG_SOUND, NARRATION]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(str(path))

    transcript_path = WHISPERX_JSON if WHISPERX_JSON.exists() else TRANSCRIPT_JSON
    if not transcript_path.exists():
        raise FileNotFoundError(str(WHISPERX_JSON))

    narration_duration = _probe_duration(NARRATION)
    bg_duration = _probe_duration(BG_VIDEO)

    if bg_duration > 0:
        max_start = max(0.0, bg_duration - narration_duration)
        background_start = random.uniform(0.0, max_start) if max_start > 0 else 0.0
    else:
        background_start = 0.0

    words = load_json(transcript_path)
    subtitles = build_subtitles(words)

    ass_path = ROOT / "temp_subs.ass"
    _write_ass_subtitles(ass_path, subtitles)

    ass_filter_path = _escape_filter_path(ass_path)
    video_chain = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setsar=1,"
        f"subtitles='{ass_filter_path}':fontsdir=fonts,"
        "format=yuv420p,"
        "tpad=stop_mode=clone:stop_duration=0.5"
    )
    filter_complex = (
        f"[0:v]{video_chain}[vout];"
        "[1:a]aformat=sample_fmts=fltp:channel_layouts=mono,volume=2.0[a1];"
        "[2:a]aformat=sample_fmts=fltp:channel_layouts=mono,volume=0.2[bg];"
        "[a1][bg]amix=inputs=2:duration=first:dropout_transition=0,"
        "aresample=async=1:first_pts=0,apad=pad_dur=0.5[aout]"
    )

    cmd = build_ffmpeg_command(narration_duration, background_start, filter_complex)
    _run(cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
