"""Never publish a reel that fails these checks."""
import json
import re
import subprocess
from pathlib import Path

from mythreels import myth_rules

MIN_SPEECH_RATIO = 0.5
SILENCE_DB = -40
SILENCE_MIN_SECONDS = 0.6
AV_TOLERANCE = 0.5
HEADER_SCAN_BYTES = 8_000_000


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def probe_problems(info: dict, reel: dict) -> list[str]:
    problems = []
    video = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    duration = float(info["format"]["duration"])
    if not reel["min_seconds"] <= duration <= reel["max_seconds"]:
        problems.append(f"duration {duration:.1f}s outside {reel['min_seconds']}-{reel['max_seconds']}s")
    if not video:
        return problems + ["no video stream"]
    if (video["width"], video["height"]) != (reel["width"], reel["height"]):
        problems.append(f"resolution {video['width']}x{video['height']}")
    if video["codec_name"] != "h264":
        problems.append(f"video codec {video['codec_name']}")
    if video.get("pix_fmt") != "yuv420p" or video.get("color_range") == "pc":
        problems.append(f"pixel format {video.get('pix_fmt')} / range {video.get('color_range')} "
                        "(Instagram needs yuv420p, TV range)")
    num, den = map(int, video["r_frame_rate"].split("/"))
    if abs(num / den - reel["fps"]) > 0.01:
        problems.append(f"fps {num / den:.2f}")
    if not audio:
        return problems + ["no audio track (voiceover missing)"]
    if audio["codec_name"] != "aac":
        problems.append(f"audio codec {audio['codec_name']}")
    if int(audio["sample_rate"]) > 48000:
        problems.append(f"audio sample rate {audio['sample_rate']}")
    if abs(float(audio.get("duration", duration)) - duration) > AV_TOLERANCE:
        problems.append(f"audio length {float(audio['duration']):.1f}s != video {duration:.1f}s")
    return problems


def parse_silences(stderr: str, duration: float) -> list[tuple[float, float]]:
    spans, start = [], None
    for line in stderr.splitlines():
        if m := re.search(r"silence_start: (-?[\d.]+)", line):
            start = max(float(m[1]), 0.0)
        elif (m := re.search(r"silence_end: ([\d.]+)", line)) and start is not None:
            spans.append((start, float(m[1])))
            start = None
    if start is not None:
        spans.append((start, duration))
    return spans


def speech_ratio(silences: list[tuple[float, float]], duration: float) -> float:
    return 1 - sum(b - a for a, b in silences) / duration if duration else 0.0


def measure_speech_ratio(path: Path, duration: float) -> float:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0", "-af",
                          f"silencedetect=noise={SILENCE_DB}dB:d={SILENCE_MIN_SECONDS}", "-f", "null", "-"],
                         capture_output=True, text=True, check=True)
    return speech_ratio(parse_silences(out.stderr, duration), duration)


def package_problems(myth: dict, props: dict, caption: str, cfg: dict) -> list[str]:
    problems = myth_rules.source_problems(myth, cfg)
    if props["verdict"] != myth["verdict"]:
        problems.append(f"on-screen verdict {props['verdict']} != researched verdict {myth['verdict']}")
    if not props.get("subtitles"):
        problems.append("no subtitles")
    if not caption.strip():
        problems.append("empty caption")
    elif len(caption) > 2200 or caption.count("#") > 30:
        problems.append("caption too long or too many hashtags")
    return problems


def container_problems(path: Path) -> list[str]:
    """Instagram rejects MP4s with edit lists and needs the moov atom before the media data."""
    with open(path, "rb") as f:
        head = f.read(HEADER_SCAN_BYTES)
    moov, mdat = head.find(b"moov"), head.find(b"mdat")
    problems = []
    if moov < 0 or (0 <= mdat < moov):
        problems.append("moov atom is not at the front (needs faststart)")
    if b"elst" in head[: mdat if mdat > 0 else len(head)]:
        problems.append("MP4 contains an edit list (Instagram rejects these)")
    return problems


def check_reel(path: Path, myth: dict, props: dict, caption: str, speech_seconds: float, cfg: dict) -> list[str]:
    info = probe(path)
    problems = (probe_problems(info, cfg["reel"]) + container_problems(path)
                + package_problems(myth, props, caption, cfg))
    duration = float(info["format"]["duration"])
    if any(s["codec_type"] == "audio" for s in info["streams"]):
        ratio = measure_speech_ratio(path, duration)
        expected = speech_seconds / duration
        if ratio < min(MIN_SPEECH_RATIO, expected * 0.8):
            problems.append(f"voiceover mostly silent (speech {ratio:.0%} of reel, expected ~{expected:.0%})")
    return problems
