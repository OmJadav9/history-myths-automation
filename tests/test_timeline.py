import pytest

from mythreels import timeline


def durations(reality=3, origin=1, each=4.0):
    d = {"hook": 3.0, "verdict": 1.2, "origin_intro": 1.8, "outro": 4.0}
    d.update({f"reality_{i}": each for i in range(reality)})
    d.update({f"origin_{i}": each for i in range(origin)})
    return d


def test_countdown_is_exactly_three_seconds(cfg):
    t = timeline.build(cfg["reel"], durations())
    countdown = next(s for s in t["scenes"] if s["type"] == "countdown")
    assert countdown["durationInFrames"] == 90


def test_scenes_are_contiguous_and_sum_to_total(cfg):
    t = timeline.build(cfg["reel"], durations())
    pos = 0
    for s in t["scenes"]:
        assert s["from"] == pos
        pos += s["durationInFrames"]
    assert pos == t["durationInFrames"]


def test_scene_order(cfg):
    t = timeline.build(cfg["reel"], durations(reality=3, origin=2))
    kinds = [s["type"] for s in t["scenes"]]
    assert kinds == ["hook", "countdown", "verdict", "beat", "beat", "beat",
                     "origin_intro", "beat", "beat", "sources", "outro"]


def test_no_speech_during_countdown(cfg):
    t = timeline.build(cfg["reel"], durations())
    cd = next(s for s in t["scenes"] if s["type"] == "countdown")
    start, end = cd["from"] / 30, (cd["from"] + cd["durationInFrames"]) / 30
    for sp in t["speech"]:
        seg_end = sp["start"] + durations()[sp["id"]]
        assert seg_end <= start + 1e-6 or sp["start"] >= end - 1e-6


def test_speech_never_runs_past_its_scene(cfg):
    d = durations()
    t = timeline.build(cfg["reel"], d)
    by_id = {s.get("segment"): s for s in t["scenes"] if s.get("segment")}
    for sp in t["speech"]:
        scene = by_id[sp["id"]]
        assert sp["start"] + d[sp["id"]] <= (scene["from"] + scene["durationInFrames"]) / 30 + 1e-6


def test_ticks_and_stamp_cues(cfg):
    t = timeline.build(cfg["reel"], durations())
    cd = next(s for s in t["scenes"] if s["type"] == "countdown")
    ticks = [c["start"] for c in t["sfx"] if c["kind"] == "tick"]
    assert ticks == pytest.approx([cd["from"] / 30 + i for i in range(3)])
    verdict = next(s for s in t["scenes"] if s["type"] == "verdict")
    thud = next(c for c in t["sfx"] if c["kind"] == "thud")
    assert thud["start"] == pytest.approx(verdict["from"] / 30 + timeline.STAMP_DELAY)


def test_beats_to_keep_drops_weakest_last_beats(cfg):
    reel = cfg["reel"]
    assert timeline.beats_to_keep(reel, durations(reality=5, each=4.0), 5) == 5
    long = durations(reality=5, each=10.0)
    kept = timeline.beats_to_keep(reel, long, 5)
    assert 3 <= kept < 5
    trimmed = {k: v for k, v in long.items() if not (k.startswith("reality_") and int(k[8:]) >= kept)}
    assert timeline.total_seconds(reel, trimmed) <= reel["max_seconds"]


def test_beats_to_keep_never_below_minimum(cfg):
    huge = durations(reality=4, each=20.0)
    assert timeline.beats_to_keep(cfg["reel"], huge, 4) == 3


def test_whoosh_never_overlaps_speech(cfg):
    from mythreels.audio import WHOOSH_SECONDS
    d = durations(reality=3, origin=2)
    t = timeline.build(cfg["reel"], d)
    speech = [(s["start"], s["start"] + d[s["id"]]) for s in t["speech"]]
    for cue in (c for c in t["sfx"] if c["kind"] == "whoosh"):
        a, b = cue["start"], cue["start"] + WHOOSH_SECONDS
        assert all(b <= s0 + 1e-6 or a >= s1 - 1e-6 for s0, s1 in speech), cue
