"""Mandatory voiceover: edge-tts first, Piper (offline) as fallback. One engine per reel, never mixed."""
import asyncio
import logging
import subprocess
import sys
import time
import wave
from dataclasses import dataclass
from pathlib import Path

import edge_tts
import numpy as np

from mythreels import audio, narration
from mythreels.config import CACHE_DIR

log = logging.getLogger(__name__)
TICKS_PER_SECOND = 10_000_000      # edge-tts offsets are in 100 ns units
PIPER_SENTENCE_GAP = 0.25


class TTSFailed(RuntimeError):
    pass


@dataclass(frozen=True)
class Clip:
    segment: str
    wav: Path
    duration: float
    cues: list[dict]        # subtitle cues relative to the clip start


# edge-tts only delivers 24 kHz / 48 kbps MP3: resample cleanly, cut rumble and the codec's high-end swirl,
# and soften harsh sibilants. Piper clips go through the same chain so both engines sound alike.
VOICE_CLEANUP = "aresample={rate}:resampler=soxr:precision=28,highpass=f=70,lowpass=f=11500,deesser=i=0.35"


def _to_wav(src: Path, dst: Path, rate: int) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1",
                    "-af", VOICE_CLEANUP.format(rate=rate), str(dst)], check=True)


def wav_duration(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


async def _edge(text: str, voice: str, rate: str, out_mp3: Path) -> list[tuple]:
    boundaries = []
    com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    with open(out_mp3, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / TICKS_PER_SECOND
                boundaries.append((chunk["text"], start, start + chunk["duration"] / TICKS_PER_SECOND))
    return boundaries


def _edge_clip(seg: str, text: str, pron: dict, cfg: dict, workdir: Path) -> Clip:
    tokens = narration.tokenize(text, pron)
    mp3, wav = workdir / f"{seg}.mp3", workdir / f"{seg}.wav"
    voice = cfg["voice"]
    for attempt in range(1, voice["edge_retries"] + 1):
        try:
            boundaries = asyncio.run(_edge(narration.spoken_text(tokens), voice["edge_voice"], voice["edge_rate"], mp3))
            if not boundaries or mp3.stat().st_size == 0:
                raise TTSFailed("edge-tts returned no audio")
            break
        except Exception as e:  # network/service errors surface as many exception types
            log.warning("edge-tts attempt %d for %s failed: %s", attempt, seg, e)
            if attempt == voice["edge_retries"]:
                raise TTSFailed(f"edge-tts failed: {e}") from e
            time.sleep(2 ** attempt)
    _to_wav(mp3, wav, cfg["audio"]["sample_rate"])
    duration = wav_duration(wav)
    return Clip(seg, wav, duration, narration.subtitle_cues(tokens, boundaries, duration))


def piper_model(cfg: dict) -> Path:
    folder = CACHE_DIR / "piper"
    model = folder / f"{cfg['voice']['piper_voice']}.onnx"
    if not model.exists():
        folder.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "piper.download_voices", cfg["voice"]["piper_voice"],
                        "--download-dir", str(folder)], check=True)
    return model


def _piper_clip(seg: str, text: str, pron: dict, cfg: dict, workdir: Path) -> Clip:
    model, rate = piper_model(cfg), cfg["audio"]["sample_rate"]
    sentences = narration.split_sentences(text)
    gap = np.zeros(int(PIPER_SENTENCE_GAP * rate), dtype=np.float32)
    pieces, spans, pos = [], [], 0.0
    for i, sentence in enumerate(sentences):
        raw, wav = workdir / f"{seg}_{i}_raw.wav", workdir / f"{seg}_{i}.wav"
        spoken = narration.spoken_text(narration.tokenize(sentence, pron))
        subprocess.run([sys.executable, "-m", "piper", "-m", str(model), "-f", str(raw)],
                       input=spoken, text=True, encoding="utf-8", check=True, capture_output=True)
        _to_wav(raw, wav, rate)
        samples = audio.read_wav(wav)
        spans.append((pos, pos + len(samples) / rate))
        pieces += [samples, gap]
        pos += (len(samples) + len(gap)) / rate
    out = workdir / f"{seg}.wav"
    audio.write_wav(out, np.concatenate(pieces[:-1]), rate)
    return Clip(seg, out, wav_duration(out), narration.sentence_cues(sentences, spans))


def synthesize(segments: dict[str, str], pron: dict, cfg: dict, workdir: Path) -> tuple[str, dict[str, Clip]]:
    """Voice every segment with one engine. Returns (engine name, clips). Raises TTSFailed if both fail."""
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        return "edge-tts", {s: _edge_clip(s, t, pron, cfg, workdir) for s, t in segments.items()}
    except TTSFailed as e:
        log.warning("switching the whole reel to Piper: %s", e)
    try:
        return "piper", {s: _piper_clip(s, t, pron, cfg, workdir) for s, t in segments.items()}
    except Exception as e:
        raise TTSFailed(f"edge-tts and Piper both failed; last error: {e}") from e
