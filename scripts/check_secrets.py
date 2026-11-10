"""Fail if anything that looks like a credential is staged (pre-commit) or committed (CI).

Usage: python scripts/check_secrets.py --staged   (git hook)
       python scripts/check_secrets.py --all      (CI: every tracked file)
"""
import re
import subprocess
import sys

PATTERNS = {
    "Meta access token": re.compile(r"\bEAA[A-Za-z0-9]{40,}"),
    "Anthropic token": re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "App secret / token assignment": re.compile(
        r"(?i)(secret|token|password)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{24,}"),
}
SKIP_SUFFIXES = (".ttf", ".woff2", ".png", ".jpg", ".mp3", ".wav", ".mp4", ".onnx")


def find_secrets(text: str) -> list[str]:
    return [name for name, rx in PATTERNS.items() if rx.search(text)]


def redact(text: str) -> str:
    for rx in PATTERNS.values():
        text = rx.sub("[redacted]", text)
    return text


def _staged_files() -> list[str]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                         capture_output=True, text=True, check=True)
    return out.stdout.split()


def _staged_text(path: str) -> str:
    return subprocess.run(["git", "show", f":{path}"], capture_output=True, text=True,
                          encoding="utf-8", errors="ignore").stdout


def _tracked_files() -> list[str]:
    return subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split()


def main(argv: list[str]) -> int:
    staged = "--staged" in argv
    files = _staged_files() if staged else _tracked_files()
    bad = []
    for path in files:
        if path.endswith(SKIP_SUFFIXES) or path == "scripts/check_secrets.py":
            continue
        try:
            text = _staged_text(path) if staged else open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        bad += [f"{path}: {kind}" for kind in find_secrets(text)]
    if bad:
        sys.stderr.write("Possible secrets found, refusing:\n  " + "\n  ".join(bad) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
