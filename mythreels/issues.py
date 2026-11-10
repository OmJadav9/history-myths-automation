"""Failure alerts as GitHub Issues (GitHub emails the repo owner). One issue per failure type per 24 h."""
import json
import logging
import os
import subprocess
from datetime import datetime, timedelta, timezone

from mythreels.config import OUTPUT_DIR
from scripts.check_secrets import redact

log = logging.getLogger(__name__)
ISSUE_MARKER = OUTPUT_DIR / "issue_opened"
LABEL = "automation-failure"
DEDUP_HOURS = 24


def run_url() -> str:
    env = os.environ
    if "GITHUB_RUN_ID" not in env:
        return "(local run)"
    return f"{env['GITHUB_SERVER_URL']}/{env['GITHUB_REPOSITORY']}/actions/runs/{env['GITHUB_RUN_ID']}"


def _gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def open_issue(kind: str, details: str) -> None:
    title = f"[automation] {kind}"
    body = redact(f"{details}\n\nRun: {run_url()}")
    if not os.environ.get("GITHUB_ACTIONS"):
        log.error("%s\n%s", title, body)
        return
    OUTPUT_DIR.mkdir(exist_ok=True)
    ISSUE_MARKER.touch()     # tells the workflow's crash step that the failure is already reported
    _gh("label", "create", LABEL, "--color", "B60205", "--description", "Opened by the reel automation", "--force")
    listed = _gh("issue", "list", "--label", LABEL, "--state", "all", "--search", f'"{kind}" in:title',
                 "--json", "title,createdAt", "--limit", "20")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=DEDUP_HOURS)
    try:
        recent = [i for i in json.loads(listed.stdout or "[]")
                  if i["title"] == title and datetime.fromisoformat(i["createdAt"].replace("Z", "+00:00")) > cutoff]
    except (ValueError, KeyError):
        recent = []
    if recent:
        log.info("issue %r already opened in the last %dh, not duplicating", title, DEDUP_HOURS)
        return
    r = _gh("issue", "create", "--title", title, "--label", LABEL, "--body", body)
    if r.returncode != 0:
        log.error("could not open issue: %s", r.stderr.strip())
