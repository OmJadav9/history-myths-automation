"""Synthesized SFX and the single pre-mixed master track (narration + tick/thud/whoosh + ducked music)."""
import hashlib
import json
import subprocess
import wave
from pathlib import Path

import numpy as np

from mythreels.config import MUSIC_DIR

RNG_SEED = 7
DUCK_SMOOTH_SECONDS = 0.25
TRUE_PEAK = -1.5


def read_wav(path: Path) -> np.ndarray:
    """Mono float32 samples in [-1, 1]."""
    with wave.open(str(path)) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        return data.reshape(-1, w.getnchannels()).mean(axis=1)


def write_wav(path: Path, samples: np.ndarray, rate: int) -> None:
    pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def db(x: float) -> float:
    return 10 ** (x / 20)


def _env(n: int, rate: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / rate
    return np.minimum(t / attack, 1.0) * np.exp(-t / decay)


def tick(rate: int) -> np.ndarray:
    n = int(0.06 * rate)
    t = np.arange(n) / rate
    return np.sin(2 * np.pi * 1800 * t) * _env(n, rate, 0.001, 0.012)


def thud(rate: int) -> np.ndarray:
    n = int(0.45 * rate)
    t = np.arange(n) / rate
    sweep = np.sin(2 * np.pi * (95 - 45 * t / t[-1]) * t)
    noise = np.random.default_rng(RNG_SEED).standard_normal(n) * _env(n, rate, 0.001, 0.02) * 0.4
    return (sweep * _env(n, rate, 0.002, 0.12) + noise) / 1.4


WHOOSH_SECONDS = 0.14     # must stay shorter than timeline.BEAT_SPEECH_DELAY


def whoosh(rate: int) -> np.ndarray:
    """Soft page-turn swish: heavily smoothed noise with a falling brightness, over before speech starts."""
    n = int(WHOOSH_SECONDS * rate)
    noise = np.random.default_rng(RNG_SEED + 1).standard_normal(n)
    smooth = np.convolve(np.convolve(noise, np.ones(48) / 48, mode="same"), np.ones(48) / 48, mode="same")
    shape = np.sin(np.pi * np.arange(n) / n) ** 3
    return smooth * shape * 6


SFX = {"tick": tick, "thud": thud, "whoosh": whoosh}


def _place(track: np.ndarray, clip: np.ndarray, start: float, rate: int, gain: float = 1.0) -> None:
    i = int(round(start * rate))
    end = min(len(track), i + len(clip))
    if i < end:
        track[i:end] += clip[: end - i] * gain


def _music(duration: float, rate: int, seed: str) -> np.ndarray | None:
    tracks = sorted(p for p in MUSIC_DIR.glob("*") if p.suffix.lower() in (".mp3", ".wav", ".ogg", ".m4a"))
    if not tracks:
        return None
    pick = tracks[int(hashlib.sha1(seed.encode()).hexdigest(), 16) % len(tracks)]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(pick), "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    music = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    reps = int(np.ceil(duration * rate / max(len(music), 1)))
    return np.tile(music, reps)[: int(duration * rate)]


def mix(speech: list[tuple[Path, float]], sfx: list[dict], duration: float, cfg: dict, out: Path,
        seed: str) -> Path:
    """speech: (wav, start seconds). Writes a loudness-normalised 48 kHz stereo WAV and returns its path."""
    a, rate = cfg["audio"], cfg["audio"]["sample_rate"]
    n = int(np.ceil(duration * rate))
    voice, effects = np.zeros(n, np.float32), np.zeros(n, np.float32)
    for wav, start in speech:
        _place(voice, read_wav(wav), start, rate)
    for cue in sfx:
        _place(effects, SFX[cue["kind"]](rate), cue["start"], rate, db(a[f"{cue['kind']}_db"]))
    master = voice + effects
    music = _music(duration, rate, seed)
    if music is not None:
        active = (np.abs(voice) > 0.01).astype(np.float32)
        width = int(DUCK_SMOOTH_SECONDS * rate)
        presence = np.clip(np.convolve(active, np.ones(width) / width * 4, mode="same"), 0, 1)
        master += music * db(a["music_db"]) * (1 - presence * (1 - db(a["duck_db"])))
    premix = out.with_name(out.stem + "_premix.wav")
    write_wav(premix, master / max(1.0, float(np.abs(master).max())), rate)
    normalize(premix, out, a["target_lufs"], rate, duration)
    return out


def normalize(src: Path, dst: Path, target_lufs: float, rate: int, duration: float) -> None:
    """Two-pass loudnorm in linear mode: one constant gain, so the voice never 'pumps'."""
    base = f"loudnorm=I={target_lufs}:TP={TRUE_PEAK}:LRA=11"
    probe = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
                            f"{base}:print_format=json", "-f", "null", "-"], capture_output=True, text=True, check=True)
    m = json.loads(probe.stderr[probe.stderr.rindex("{"): probe.stderr.rindex("}") + 1])
    second = (f"{base}:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
              f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", f"{second},aresample={rate}:resampler=soxr",
                    "-ac", "2", "-t", f"{duration:.3f}", str(dst)], check=True)
