"""Remotion render (headless Chrome) + faststart remux so Instagram can stream the file."""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from mythreels.config import REMOTION_DIR

RENDER_TIMEOUT = 20 * 60
COMPOSITION = "MythReel"


def render(props: dict, props_file: Path, out_mp4: Path) -> float:
    """Render `props` to `out_mp4`. Returns render seconds."""
    props_file.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    raw = out_mp4.with_name(out_mp4.stem + "_raw.mp4")
    npx = shutil.which("npx") or "npx"
    cmd = [npx, "remotion", "render", "src/index.ts", COMPOSITION, str(raw), f"--props={props_file}",
           "--codec=h264", "--crf=23", "--x264-preset=medium", f"--concurrency={os.cpu_count() or 2}",
           "--color-space=bt709",   # standard yuv420p / TV range instead of Remotion's full-range default
           "--audio-codec=aac", "--audio-bitrate=128K", "--enforce-audio-track", "--log=error"]
    started = time.monotonic()
    proc = subprocess.run(cmd, cwd=REMOTION_DIR, capture_output=True, text=True, timeout=RENDER_TIMEOUT)
    if proc.returncode != 0:
        raise RuntimeError(f"Remotion render failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
    seconds = time.monotonic() - started
    # Instagram wants the moov atom first and no edit lists; plain remux, no re-encode.
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-c", "copy", "-movflags", "+faststart",
                    "-use_editlist", "0", str(out_mp4)], check=True)
    raw.unlink(missing_ok=True)
    return seconds
