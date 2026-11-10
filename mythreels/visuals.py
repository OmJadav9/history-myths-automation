"""Public-domain / CC0 images from Wikimedia Commons, with credits. Downloaded per run, never committed."""
import html
import logging
import re
from pathlib import Path

import requests

log = logging.getLogger(__name__)
API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "MythReelsBot/1.0 (https://github.com/OmJadav9/history-myths-automation)"
THUMB_WIDTH = 1600
MIN_WIDTH = 700
MAX_BYTES = 15_000_000
TIMEOUT = 30
OK_MIME = {"image/jpeg", "image/png"}
# ponytail: keyword blocklist on Commons metadata; add an image-content check if bad pictures slip through.
BLOCKED_WORDS = re.compile(
    r"\b(living people|corpse|dead bod|execution|massacre|gore|nude|nudity|naked|torture|blood|murder|"
    r"genocide|lynch|behead|war crime|atrocit|wounded|casualt)", re.I)


def _plain(value: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", "", value or ""))
    return re.sub(r"\s*label QS:.*$", "", text, flags=re.S).strip()   # strip Wikidata label markup


def is_free_license(meta: dict) -> str | None:
    """Return a display license if the file is Public Domain or CC0, else None."""
    code = meta.get("License", {}).get("value", "").lower()
    short = _plain(meta.get("LicenseShortName", {}).get("value", ""))
    low = short.lower()
    if code == "cc0" or low.startswith("cc0") or "cc-zero" in low:
        return "CC0"
    if code.startswith("pd") or low.startswith("public domain") or low.startswith("pd"):
        return "Public domain"
    return None


def _candidate(page: dict) -> dict | None:
    info = (page.get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata", {})
    lic = is_free_license(meta)
    text = " ".join([page.get("title", ""), _plain(meta.get("Categories", {}).get("value", "")),
                     _plain(meta.get("ImageDescription", {}).get("value", ""))])
    if not lic or info.get("mime") not in OK_MIME or info.get("width", 0) < MIN_WIDTH or BLOCKED_WORDS.search(text):
        return None
    title = _plain(meta.get("ObjectName", {}).get("value", "")) or page["title"].removeprefix("File:").rsplit(".", 1)[0]
    author = _plain(meta.get("Artist", {}).get("value", "")) or "Unknown"
    return {"title": title[:80], "author": author[:60], "license": lic,
            "url": info.get("thumburl") or info["url"], "page": info.get("descriptionurl", "")}


def search(term: str, limit: int = 40) -> list[dict]:
    params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": f"{term} filetype:bitmap",
              "gsrnamespace": 6, "gsrlimit": limit, "prop": "imageinfo",
              "iiprop": "url|extmetadata|mime|size", "iiurlwidth": THUMB_WIDTH}
    r = requests.get(API, params=params, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    pages = sorted(r.json().get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    return [c for c in map(_candidate, pages) if c]


def _download(url: str, dest: Path) -> None:
    with requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, stream=True) as r:
        r.raise_for_status()
        size = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(65536):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("image too large")
                f.write(chunk)


def gather(terms: list[str], needed: int, dest_dir: Path) -> list[dict]:
    """Up to `needed` distinct free images. Returns [] (typographic fallback) if Commons has nothing usable."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    found, seen = [], set()
    for term in terms:
        try:
            results = search(term)
        except requests.RequestException as e:
            log.warning("Commons search failed for %r: %s", term, e)
            continue
        for c in results:
            if c["url"] in seen or len(found) >= needed:
                continue
            seen.add(c["url"])
            ext = ".png" if c["url"].lower().endswith(".png") else ".jpg"
            path = dest_dir / f"img{len(found)}{ext}"
            try:
                _download(c["url"], path)
            except (requests.RequestException, ValueError) as e:
                log.warning("skipping %s: %s", c["url"], e)
                continue
            found.append({**c, "file": path.name})
        if len(found) >= needed:
            break
    return found
