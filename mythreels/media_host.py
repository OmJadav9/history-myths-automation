"""Fallback hosting: put the MP4 on a throwaway `media` branch so Instagram can fetch it by URL.

Uses git plumbing in the existing checkout (and its push credentials), so no token is handled here.
The branch holds a single file in an orphan commit and is deleted right after publishing.
"""
import logging
import os
import subprocess
import time
from pathlib import Path

from mythreels.config import ROOT, load_config

log = logging.getLogger(__name__)
BRANCH = "media"
RAW = "https://raw.githubusercontent.com"
SETTLE_SECONDS = 15


def _git(*args: str, stdin: str | None = None) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, input=stdin)
    if r.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {r.stderr.strip()[-300:]}")
    return r.stdout.strip()


def _repo() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or load_config()["repo"]


def host(mp4: Path) -> str:
    """Force-push `mp4` alone to the media branch and return its public raw URL."""
    name = mp4.name
    blob = _git("hash-object", "-w", str(mp4))
    tree = _git("mktree", stdin=f"100644 blob {blob}\t{name}\n")
    commit = _git("commit-tree", tree, "-m", "media: temporary reel upload (deleted after publishing)")
    _git("push", "--force", "origin", f"{commit}:refs/heads/{BRANCH}")
    time.sleep(SETTLE_SECONDS)       # let raw.githubusercontent.com see the new branch
    return f"{RAW}/{_repo()}/{BRANCH}/{name}"


def cleanup() -> None:
    try:
        _git("push", "origin", "--delete", BRANCH)
    except RuntimeError as e:
        log.warning("could not delete the %s branch: %s", BRANCH, e)
