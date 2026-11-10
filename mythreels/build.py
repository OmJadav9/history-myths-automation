"""Turn one approved myth into a validated MP4 + caption."""
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from mythreels import audio, render, timeline, tts, video_check, visuals
from mythreels.caption import build_caption, source_names
from mythreels.config import REMOTION_DIR

log = logging.getLogger(__name__)
OUTRO = "Did you believe this one? Comment a myth you want busted next, and follow for daily history."


@dataclass
class Reel:
    myth: dict
    mp4: Path
    caption: str
    props: dict
    engine: str
    render_seconds: float
    credits: list[dict]
    problems: list[str] = field(default_factory=list)


def segment_texts(myth: dict) -> dict[str, str]:
    is_myth = myth["verdict"] == "MYTH"
    texts = {"hook": f"Myth or fact? {myth['claim']}",
             "verdict": "It's a myth." if is_myth else "Believe it or not, it's true."}
    texts |= {f"reality_{i}": b["narration"] for i, b in enumerate(myth["reality"])}
    texts["origin_intro"] = "So where did this myth come from?" if is_myth else "So why does it sound like a myth?"
    texts |= {f"origin_{i}": b["narration"] for i, b in enumerate(myth["origin"])}
    texts["outro"] = OUTRO
    return texts


def _scene_props(scene: dict, myth: dict, images: list[str]) -> dict:
    seg = scene.get("segment", "")
    out = {k: scene[k] for k in ("type", "from", "durationInFrames")}
    if seg.startswith("reality_") or (seg.startswith("origin_") and seg != "origin_intro"):
        section = "reality" if seg.startswith("reality_") else "origin"
        i = int(seg.split("_")[1])
        beats = myth[section]
        out |= {"section": section, "keyLine": beats[i]["key_line"], "beatNumber": i + 1,
                "beatTotal": len(beats)}
        offset = 1 + i + (len(myth["reality"]) if section == "origin" else 0)
        out["image"] = images[offset % len(images)] if images else None
    elif seg == "hook":
        out["image"] = images[0] if images else None
    return out


def _subtitles(tl: dict, clips: dict[str, tts.Clip]) -> list[dict]:
    fps, cues, last_end = tl["fps"], [], 0
    for sp in tl["speech"]:
        for c in clips[sp["id"]].cues:
            start = max(round((sp["start"] + c["start"]) * fps), last_end)
            end = max(round((sp["start"] + c["end"]) * fps), start + 1)
            cues.append({"text": c["text"], "from": start, "durationInFrames": end - start})
            last_end = end
    return cues


def make_props(myth: dict, tl: dict, clips: dict, images: list[dict], run: str, cfg: dict) -> dict:
    srcs = [f"run/{run}/{img['file']}" for img in images]
    return {
        "claim": myth["claim"], "verdict": myth["verdict"], "hook": myth["hook"], "category": myth["category"],
        "era": myth["era"], "year": myth["year"], "account": cfg["account"],
        "accent": cfg["era_accents"].get(myth["category"], cfg["palette"]["gold"]), "palette": cfg["palette"],
        "scenes": [_scene_props(s, myth, srcs) for s in tl["scenes"]],
        "subtitles": _subtitles(tl, clips), "sources": source_names(myth), "audio": f"run/{run}/master.wav",
        "durationInFrames": tl["durationInFrames"], "fps": tl["fps"],
        "width": cfg["reel"]["width"], "height": cfg["reel"]["height"],
    }


def build_reel(myth: dict, cfg: dict, workdir: Path, keep_assets: bool = False) -> Reel:
    workdir.mkdir(parents=True, exist_ok=True)
    pron = {**cfg["voice"]["pronunciations"], **{p["word"]: p["say"] for p in myth.get("pronunciations", [])}}
    engine, clips = tts.synthesize(segment_texts(myth), pron, cfg, workdir / "voice")
    durations = {k: c.duration for k, c in clips.items()}

    keep = timeline.beats_to_keep(cfg["reel"], durations, len(myth["reality"]))
    if keep < len(myth["reality"]):
        log.info("trimming reality beats %d -> %d to fit %ss", len(myth["reality"]), keep, cfg["reel"]["max_seconds"])
        myth = {**myth, "reality": myth["reality"][:keep]}
        durations = {k: v for k, v in durations.items() if not (k.startswith("reality_") and int(k[8:]) >= keep)}
    if timeline.total_seconds(cfg["reel"], durations) > cfg["reel"]["max_seconds"] and len(myth["origin"]) > 1:
        log.info("dropping the second origin beat to fit %ss", cfg["reel"]["max_seconds"])
        myth = {**myth, "origin": myth["origin"][:1]}
        durations = {k: v for k, v in durations.items() if k != "origin_1"}
    tl = timeline.build(cfg["reel"], durations)

    run = f"{myth['id']}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
    public_run = REMOTION_DIR / "public" / "run" / run
    try:
        images = visuals.gather(myth["image_search_terms"], len(myth["reality"]) + len(myth["origin"]) + 1, public_run)
        seconds = tl["durationInFrames"] / tl["fps"]
        audio.mix([(clips[s["id"]].wav, s["start"]) for s in tl["speech"]], tl["sfx"], seconds, cfg,
                  public_run / "master.wav", myth["id"])
        props = make_props(myth, tl, clips, images, run, cfg)
        mp4 = workdir / f"{myth['id']}.mp4"
        render_seconds = render.render(props, public_run / "props.json", mp4)
        if keep_assets:
            shutil.copy(public_run / "props.json", workdir / "props.json")
            shutil.copy(public_run / "master.wav", workdir / "master.wav")
    finally:
        shutil.rmtree(public_run, ignore_errors=True)

    credits = [{k: img[k] for k in ("title", "author", "license", "page")} for img in images]
    caption = build_caption(myth, credits)
    speech = sum(durations.values())
    problems = video_check.check_reel(mp4, myth, props, caption, speech, cfg)
    return Reel(myth, mp4, caption, props, engine, render_seconds, credits, problems)
