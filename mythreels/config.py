from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "state"
BACKLOG_FILE = STATE_DIR / "myths_backlog.json"
HISTORY_FILE = STATE_DIR / "published_history.json"
REMOTION_DIR = ROOT / "remotion"
MUSIC_DIR = ROOT / "assets" / "music"
OUTPUT_DIR = ROOT / "output"
CACHE_DIR = ROOT / ".cache"


def load_config(path: Path = ROOT / "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
