"""Frame timeline built from measured narration lengths. Remotion places every scene where this says."""
STAMP_DELAY = 0.15      # stamp lands this long after the verdict scene starts
VERDICT_SPEECH_DELAY = 0.45
BEAT_SPEECH_DELAY = 0.2
OUTRO_TAIL = 0.6


def _segment_order(durations: dict) -> list[str]:
    reality = sorted((k for k in durations if k.startswith("reality_")), key=lambda k: int(k[8:]))
    origin = sorted((k for k in durations if k.startswith("origin_") and k != "origin_intro"),
                    key=lambda k: int(k[7:]))
    return ["hook", "COUNTDOWN", "verdict", *reality, "origin_intro", *origin, "SOURCES", "outro"]


def _plan(reel: dict, durations: dict) -> list[tuple[str, str | None, float, float]]:
    """(scene type, segment id, scene seconds, speech offset within scene)."""
    pad = reel["pad_seconds"]
    plan = []
    for seg in _segment_order(durations):
        if seg == "COUNTDOWN":
            plan.append(("countdown", None, float(reel["countdown_seconds"]), 0.0))
        elif seg == "SOURCES":
            plan.append(("sources", None, float(reel["sources_card_seconds"]), 0.0))
        elif seg == "hook":
            plan.append(("hook", seg, durations[seg] + pad, 0.0))
        elif seg == "verdict":
            plan.append(("verdict", seg, VERDICT_SPEECH_DELAY + durations[seg] + pad, VERDICT_SPEECH_DELAY))
        elif seg == "origin_intro":
            plan.append(("origin_intro", seg, BEAT_SPEECH_DELAY + durations[seg] + pad, BEAT_SPEECH_DELAY))
        elif seg == "outro":
            plan.append(("outro", seg, durations[seg] + pad + OUTRO_TAIL, 0.0))
        else:
            plan.append(("beat", seg, BEAT_SPEECH_DELAY + durations[seg] + pad, BEAT_SPEECH_DELAY))
    return plan


def total_seconds(reel: dict, durations: dict) -> float:
    return sum(p[2] for p in _plan(reel, durations))


def beats_to_keep(reel: dict, durations: dict, n_reality: int) -> int:
    """Drop reality beats from the end (they are ordered strongest first) until the reel fits."""
    keep = n_reality
    while keep > reel["min_reality_beats"]:
        trimmed = {k: v for k, v in durations.items() if not (k.startswith("reality_") and int(k[8:]) >= keep)}
        if total_seconds(reel, trimmed) <= reel["max_seconds"]:
            break
        keep -= 1
    return keep


def build(reel: dict, durations: dict) -> dict:
    fps = reel["fps"]
    scenes, speech, sfx, frame = [], [], [], 0
    countdown_frames = round(reel["countdown_seconds"] * fps)
    for kind, seg, seconds, speech_offset in _plan(reel, durations):
        n = countdown_frames if kind == "countdown" else max(1, round(seconds * fps))
        if seg and speech_offset + durations[seg] > n / fps:   # rounding must never cut speech off
            n += 1
        start = frame / fps
        scene = {"type": kind, "from": frame, "durationInFrames": n}
        if seg:
            scene["segment"] = seg
            speech.append({"id": seg, "start": start + speech_offset})
        if kind == "countdown":
            sfx += [{"kind": "tick", "start": start + i} for i in range(int(reel["countdown_seconds"]))]
        elif kind == "verdict":
            sfx.append({"kind": "thud", "start": start + STAMP_DELAY})
        elif kind in ("beat", "origin_intro", "sources"):
            sfx.append({"kind": "whoosh", "start": start})
        scenes.append(scene)
        frame += n
    return {"fps": fps, "durationInFrames": frame, "scenes": scenes, "speech": speech, "sfx": sfx}
