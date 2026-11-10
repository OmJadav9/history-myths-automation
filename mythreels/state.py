"""JSON state files committed back to the repo, so every run sees what earlier runs did."""
import json
import logging
import subprocess
import time
from pathlib import Path

from mythreels.config import BACKLOG_FILE, HISTORY_FILE, ROOT

log = logging.getLogger(__name__)
PUSH_RETRIES = 4


def load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def load_backlog() -> list[dict]:
    return load_json(BACKLOG_FILE, [])


def save_backlog(backlog: list[dict]) -> None:
    save_json(BACKLOG_FILE, backlog)


def load_history() -> list[dict]:
    return load_json(HISTORY_FILE, [])


def save_history(history: list[dict]) -> None:
    save_json(HISTORY_FILE, history)


def upsert(history: list[dict], record: dict, key: str = "run_key") -> list[dict]:
    """Return a new history list with `record` replacing any entry with the same key."""
    return [h for h in history if h.get(key) != record[key]] + [record]


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def commit_and_push(message: str, paths: list[Path]) -> None:
    """Commit state files and push, rebasing onto any concurrent change. Raises if push keeps failing."""
    _git("add", *[str(p.relative_to(ROOT)) for p in paths])
    if _git("diff", "--cached", "--quiet").returncode == 0:
        return
    if (r := _git("commit", "-m", message)).returncode != 0:
        raise RuntimeError(f"git commit failed: {r.stderr.strip()}")
    for attempt in range(1, PUSH_RETRIES + 1):
        if _git("push").returncode == 0:
            return
        log.warning("push rejected (attempt %d), rebasing", attempt)
        if (r := _git("pull", "--rebase", "--autostash")).returncode != 0:
            raise RuntimeError(f"git pull --rebase failed: {r.stderr.strip()}")
        time.sleep(2 * attempt)
    raise RuntimeError("git push failed after retries")
