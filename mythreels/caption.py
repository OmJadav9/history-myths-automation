from mythreels.myth_rules import domain_of

MAX_CAPTION = 2200
MAX_HASHTAGS = 10
MAX_SOURCES = 3
CTA = "Did you believe this one? Comment a myth you want busted next 👇"


def source_names(myth: dict, limit: int = MAX_SOURCES) -> list[str]:
    """Distinct publishers, most-cited first (verdict sources lead)."""
    sources = myth["verdict_sources"] + [s for b in myth["reality"] + myth["origin"] for s in b["sources"]]
    names, seen = [], set()
    for s in sources:
        d = domain_of(s["url"])
        if d not in seen:
            seen.add(d)
            names.append(s.get("publisher") or d)
    return names[:limit]


def _credit(c: dict) -> str:
    lic = "public domain" if "public domain" in c["license"].lower() or c["license"].lower() == "pd" else c["license"]
    return f"{c['title']} by {c['author']}, {lic}, via Wikimedia Commons"


def build_caption(myth: dict, image_credits: list[dict]) -> str:
    tags = " ".join(myth["hashtags"][:MAX_HASHTAGS])
    sources = "Sources: " + ", ".join(source_names(myth))
    credits = list(image_credits)
    summary = myth["summary"].strip()

    def assemble() -> str:
        images = ("Images: " + "; ".join(_credit(c) for c in credits)) if credits else ""
        return "\n\n".join(p for p in [myth["hook"], summary, sources, images, CTA, tags] if p)

    text = assemble()
    while len(text) > MAX_CAPTION and len(credits) > 1:
        credits.pop()
        text = assemble()
    if len(text) > MAX_CAPTION:
        summary = summary[: max(0, len(summary) - (len(text) - MAX_CAPTION) - 1)].rsplit(" ", 1)[0] + "…"
        text = assemble()
    return text
