from collections import Counter

from mythreels.myth_rules import domain_of

MAX_CAPTION = 2200
MAX_HASHTAGS = 10
MAX_SOURCES = 3
CTA = "Did you believe this one? Comment a myth you want busted next 👇"


def source_names(myth: dict, limit: int = MAX_SOURCES) -> list[str]:
    """Distinct publishers, ranked by how many beats (and the verdict) cite them; ties keep first appearance."""
    groups = [myth["verdict_sources"]] + [b["sources"] for b in myth["reality"] + myth["origin"]]
    counts, names = Counter(), {}
    for group in groups:
        for d in {domain_of(s["url"]) for s in group}:
            counts[d] += 1
        for s in group:
            names.setdefault(domain_of(s["url"]), s.get("publisher") or domain_of(s["url"]))
    order = list(names)
    ranked = sorted(order, key=lambda d: (-counts[d], order.index(d)))
    return [names[d] for d in ranked[:limit]]


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
