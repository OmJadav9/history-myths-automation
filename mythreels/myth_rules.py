"""Local checks applied on top of the Claude passes: sources, exclusions, recency, dedup, picking."""
import re
from collections import Counter
from datetime import date, timedelta
from urllib.parse import urlparse

from rapidfuzz import fuzz

_SECOND_LEVEL = {"co", "ac", "org", "gov", "edu", "nic", "net", "com"}


def domain_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in _SECOND_LEVEL and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _counts(source: dict, cfg: dict) -> bool:
    d = domain_of(source["url"])
    c = cfg["content"]
    return not any(d == b or d.endswith("." + b) for b in c["wikipedia_domains"] + c["blocked_source_domains"])


def _independent_domains(sources: list[dict], cfg: dict) -> set[str]:
    return {domain_of(s["url"]) for s in sources if _counts(s, cfg)}


def without_weak_sources(myth: dict, cfg: dict) -> dict:
    """Copy of `myth` with Wikipedia/blocked sources removed, so they never reach the screen or caption."""
    def keep(sources: list[dict]) -> list[dict]:
        return [s for s in sources if _counts(s, cfg)]
    return {**myth, "verdict_sources": keep(myth.get("verdict_sources", [])),
            "reality": [{**b, "sources": keep(b["sources"])} for b in myth["reality"]],
            "origin": [{**b, "sources": keep(b["sources"])} for b in myth["origin"]]}


def source_problems(myth: dict, cfg: dict) -> list[str]:
    need = cfg["content"]["min_sources"]
    checks = [("verdict", myth.get("verdict_sources", []))]
    checks += [(f"reality {i + 1}", b.get("sources", [])) for i, b in enumerate(myth["reality"])]
    checks += [(f"origin {i + 1}", b.get("sources", [])) for i, b in enumerate(myth["origin"])]
    return [f"{name}: only {len(_independent_domains(srcs, cfg))} independent reliable source(s), need {need}"
            for name, srcs in checks if len(_independent_domains(srcs, cfg)) < need]


def exclusion_hits(myth: dict, cfg: dict) -> list[str]:
    topic = " ".join([myth["claim"], myth.get("event", ""), *myth.get("key_people", [])]).lower()
    return [k for k in cfg["content"]["excluded_keywords"] if re.search(rf"\b{re.escape(k.lower())}\b", topic)]


def too_recent(myth: dict, cfg: dict, year_now: int) -> bool:
    return myth["year"] > year_now - cfg["content"]["min_years_ago"]


_STOPWORDS = {"the", "a", "an", "of", "with", "was", "were", "is", "are", "in", "on", "to", "and", "their",
              "they", "his", "her", "its", "that", "had", "have", "did", "do"}


def _norm(text: str) -> str:
    """Lowercase, drop stopwords, crude stemming, so 'horned helmets' ~ 'helmets with horns'."""
    words = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in _STOPWORDS:
            continue
        for suffix in ("ing", "ed", "es", "s"):
            if w.endswith(suffix) and len(w) - len(suffix) >= 3:
                w = w[: -len(suffix)]
                break
        words.append(w)
    return " ".join(words)


def _similar(a: str, b: str, limit: int) -> bool:
    return bool(a and b) and fuzz.token_set_ratio(_norm(a), _norm(b)) >= limit


def duplicate_reason(myth: dict, seen: list[dict], cfg: dict) -> str | None:
    limit = cfg["content"]["claim_similarity"]
    for other in seen:
        if _similar(myth["claim"], other.get("claim", ""), limit):
            return f"claim duplicates '{other.get('claim')}'"
        if _similar(myth.get("event", ""), other.get("event", ""), limit):
            return f"event duplicates '{other['event']}'"
    return None


def narration_words(myth: dict) -> int:
    return sum(len(b["narration"].split()) for b in myth["reality"] + myth["origin"])


def length_fix(myth: dict, cfg: dict) -> str | None:
    """A revision instruction if the script is too long to fit the reel, else None."""
    c = cfg["content"]
    total = narration_words(myth)
    longest = max(len(b["narration"].split()) for b in myth["reality"] + myth["origin"])
    if total <= c["max_narration_words"] and longest <= c["max_beat_words"]:
        return None
    return (f"Too long for a 75-second reel: the reality + origin narration totals {total} words (longest beat "
            f"{longest}). Cut it to at most {c['max_narration_words']} words in total and {c['max_beat_words']} per "
            "beat, by dropping the weakest details or the weakest beat (keep 3 reality beats and 1-2 origin beats). "
            "Keep every remaining sentence accurate, hedged and sourced exactly as before.")


def validate(myth: dict, cfg: dict, history: list[dict], others: list[dict], year_now: int) -> list[str]:
    problems = source_problems(myth, cfg)
    if hits := exclusion_hits(myth, cfg):
        problems.append(f"excluded topic keywords: {', '.join(hits)}")
    if too_recent(myth, cfg, year_now):
        problems.append(f"too recent (year {myth['year']})")
    if dup := duplicate_reason(myth, history + others, cfg):
        problems.append(dup)
    if myth["category"] not in cfg["content"]["categories"]:
        problems.append(f"unknown category {myth['category']}")
    return problems


def _same_person(a: str, b: str) -> bool:
    return fuzz.token_set_ratio(a.lower(), b.lower()) >= 90


def pick_next(backlog: list[dict], history: list[dict], today: date, cfg: dict) -> dict | None:
    """Next approved myth: no category twice a day, person cooldown, prefer under-used verdict/category."""
    published = [h for h in history if h.get("status") == "published"]
    cutoff = (today - timedelta(days=cfg["content"]["person_cooldown_days"])).isoformat()
    recent_people = [p for h in published if h["date_ist"] > cutoff for p in h.get("key_people", [])]
    used_today = {h["category"] for h in published if h["date_ist"] == today.isoformat()}

    eligible = [m for m in backlog
                if m["category"] not in used_today
                and not any(_same_person(p, r) for p in m.get("key_people", [])[:1] for r in recent_people)
                and not duplicate_reason(m, published, cfg)]
    if not eligible:
        return None

    last = published[-10:]
    fact_share = sum(h.get("verdict") == "FACT" for h in last) / len(last) if last else 1.0
    want = "FACT" if fact_share < cfg["content"]["fact_ratio"] else "MYTH"
    category_uses = Counter(h["category"] for h in published[-30:])
    return min(eligible, key=lambda m: (m["verdict"] != want, category_uses[m["category"]]))
