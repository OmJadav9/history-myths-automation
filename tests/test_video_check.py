import subprocess

import pytest

from mythreels import video_check

SILENCE_LOG = """
[silencedetect @ 0x1] silence_start: 0
[silencedetect @ 0x1] silence_end: 2.5 | silence_duration: 2.5
[silencedetect @ 0x1] silence_start: 40.25
[silencedetect @ 0x1] silence_end: 45 | silence_duration: 4.75
"""


def probe(duration=50.0, width=1080, height=1920, fps="30/1", audio=True, audio_dur=None, rate="48000",
          pix_fmt="yuv420p", color_range="tv"):
    streams = [{"codec_type": "video", "codec_name": "h264", "width": width, "height": height,
                "r_frame_rate": fps, "duration": str(duration), "pix_fmt": pix_fmt, "color_range": color_range}]
    if audio:
        streams.append({"codec_type": "audio", "codec_name": "aac", "sample_rate": rate,
                        "duration": str(audio_dur if audio_dur is not None else duration)})
    return {"streams": streams, "format": {"duration": str(duration)}}


def test_parse_silences():
    assert video_check.parse_silences(SILENCE_LOG, 50.0) == [(0.0, 2.5), (40.25, 45.0)]


def test_unterminated_silence_runs_to_end():
    log = "[silencedetect @ 0x1] silence_start: 48.0\n"
    assert video_check.parse_silences(log, 50.0) == [(48.0, 50.0)]


def test_speech_ratio():
    assert video_check.speech_ratio([(0.0, 2.5), (40.25, 45.0)], 50.0) == pytest.approx(0.855)


def test_good_probe_has_no_problems(cfg):
    assert video_check.probe_problems(probe(), cfg["reel"]) == []


@pytest.mark.parametrize("kwargs,needle", [
    ({"duration": 20.0}, "duration"),
    ({"duration": 80.0}, "duration"),
    ({"width": 720}, "resolution"),
    ({"fps": "25/1"}, "fps"),
    ({"audio": False}, "audio"),
    ({"audio_dur": 40.0}, "audio length"),
    ({"rate": "96000"}, "sample rate"),
    ({"pix_fmt": "yuvj420p", "color_range": "pc"}, "pixel format"),
])
def test_bad_probes_are_rejected(cfg, kwargs, needle):
    problems = video_check.probe_problems(probe(**kwargs), cfg["reel"])
    assert any(needle in p for p in problems), problems


def test_package_checks(myth, cfg):
    props = {"verdict": "MYTH", "subtitles": [{"text": "x", "from": 0, "durationInFrames": 10}]}
    assert video_check.package_problems(myth, props, "caption text", cfg) == []
    assert video_check.package_problems(myth, {**props, "verdict": "FACT"}, "c", cfg)
    assert video_check.package_problems(myth, {**props, "subtitles": []}, "c", cfg)
    assert video_check.package_problems(myth, props, "  ", cfg)


def test_real_file_is_probed(tmp_path, cfg):
    out = tmp_path / "t.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=108x192:r=30:d=2",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2",
                    "-c:v", "libx264", "-c:a", "aac", "-shortest", str(out)], check=True)
    info = video_check.probe(out)
    problems = video_check.probe_problems(info, cfg["reel"])
    assert any("duration" in p for p in problems) and any("resolution" in p for p in problems)
    assert video_check.measure_speech_ratio(out, 2.0) > 0.9


def test_edit_lists_and_moov_position_are_checked(tmp_path):
    src, fixed = tmp_path / "src.mp4", tmp_path / "fixed.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=s=128x128:r=30:d=1",
                    "-f", "lavfi", "-i", "sine=duration=1:sample_rate=48000",
                    "-c:v", "libx264", "-bf", "2", "-c:a", "aac", "-shortest", str(src)], check=True)
    assert video_check.container_problems(src)      # ffmpeg defaults: edit list, moov at the end
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-c", "copy", "-movflags", "+faststart",
                    "-use_editlist", "0", str(fixed)], check=True)
    assert video_check.container_problems(fixed) == []
