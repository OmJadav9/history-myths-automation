"""Headless Claude Code calls (`claude -p`) with schema-validated JSON output, on the Claude subscription."""
import json
import logging
import os
import shutil
import subprocess

import jsonschema

log = logging.getLogger(__name__)
WEB_TOOLS = "WebSearch,WebFetch"


class ClaudeError(RuntimeError):
    pass


def run(prompt: str, schema: dict, *, web: bool = False, timeout: int = 900, attempts: int = 2,
        max_turns: int = 40) -> dict:
    exe = shutil.which("claude")
    if not exe:
        raise ClaudeError("Claude Code CLI not found on PATH")
    cmd = [exe, "-p", "--output-format", "json", "--json-schema", json.dumps(schema),
           "--max-turns", str(max_turns), "--strict-mcp-config", "--setting-sources", "project",
           "--no-session-persistence", "--tools", WEB_TOOLS if web else ""]
    if web:
        cmd += ["--allowedTools", WEB_TOOLS]
    if model := os.environ.get("MYTH_CLAUDE_MODEL"):
        cmd += ["--model", model]

    last = "no attempt"
    for attempt in range(1, attempts + 1):
        try:
            proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                                  timeout=timeout)
        except subprocess.TimeoutExpired:
            last = f"timed out after {timeout}s"
            log.warning("claude attempt %d: %s", attempt, last)
            continue
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            last = f"non-JSON output (exit {proc.returncode}): {proc.stdout[-300:]} {proc.stderr[-300:]}"
            log.warning("claude attempt %d: %s", attempt, last)
            continue
        if data.get("is_error") or data.get("subtype") != "success" or "structured_output" not in data:
            last = f"{data.get('subtype')}: {str(data.get('result'))[:300]}"
            log.warning("claude attempt %d failed: %s", attempt, last)
            continue
        try:
            jsonschema.validate(data["structured_output"], schema)
        except jsonschema.ValidationError as e:
            last = f"schema mismatch: {e.message}"
            log.warning("claude attempt %d: %s", attempt, last)
            continue
        return data["structured_output"]
    raise ClaudeError(last)
