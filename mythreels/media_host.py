"""Fallback hosting: put the MP4 on a throwaway `media` branch so Instagram can fetch it by URL.

Uses git plumbing in the existing checkout (and its push credentials), so no token is handled here.
The branch holds a single file in an orphan commit and is deleted right after publishing.
"""
import logging
import os
import subprocess
import time
from pathlib import Path

import requests

from mythreels.config import ROOT, load_config

log = logging.getLogger(__name__)
BRANCH = "media"
RAW = "https://raw.githubusercontent.com"
SETTLE_SECONDS = 10
SERVE_TIMEOUT = 180


def _git(*args: str, stdin: str | None = None) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, input=stdin)
    if r.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {r.stderr.strip()[-300:]}")
    return r.stdout.strip()


def _repo() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or load_config()["repo"]


def _wait_until_served(url: str, size: int) -> None:
    """Instagram must never see a 404: wait until the raw URL serves the whole file."""
    deadline = time.monotonic() + SERVE_TIMEOUT
    last = "no response"
    while time.monotonic() < deadline:
        try:
            r = requests.head(url, timeout=20, allow_redirects=False)
            last = f"{r.status_code} {r.headers.get('Content-Length')}"
            if r.status_code == 200 and int(r.headers.get("Content-Length", -1)) == size:
                return
        except requests.RequestException as e:
            last = str(e)
        time.sleep(5)
    raise RuntimeError(f"hosted video never became available at {url} (last: {last})")


def host(mp4: Path) -> str:
    """Force-push `mp4` alone to the media branch and return its public raw URL once it is served."""
    name = mp4.name
    blob = _git("hash-object", "-w", str(mp4))
    tree = _git("mktree", stdin=f"100644 blob {blob}\t{name}\n")
    commit = _git("commit-tree", tree, "-m", "media: temporary reel upload (deleted after publishing)")
    _git("push", "--force", "origin", f"{commit}:refs/heads/{BRANCH}")
    url = f"{RAW}/{_repo()}/{BRANCH}/{name}"
    _wait_until_served(url, mp4.stat().st_size)
    time.sleep(SETTLE_SECONDS)       # a little extra so every CDN edge has it
    return url


def cleanup() -> None:
    try:
        _git("push", "origin", "--delete", BRANCH)
    except RuntimeError as e:
        log.warning("could not delete the %s branch: %s", BRANCH, e)
