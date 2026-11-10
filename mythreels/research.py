"""Generate -> research (web, 2+ sources per sentence) -> adversarial review -> local checks -> backlog."""
import hashlib
import logging
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from mythreels import claude_cli, myth_rules, prompts, schemas, state

log = logging.getLogger(__name__)
RESEARCH_TIMEOUT = 600
REVIEW_TIMEOUT = 480
GENERATE_TIMEOUT = 300
MIN_MINUTES_FOR_BATCH = 15


def myth_id(claim: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", claim.lower()).strip("-")[:48].rstrip("-")
    return f"{slug}-{hashlib.sha1(claim.encode()).hexdigest()[:4]}"


def generate(cfg: dict, n: int, backlog: list[dict], history: list[dict], seed_claim: str | None = None) -> list:
    cats = cfg["content"]["categories"]
    counts = Counter(m["category"] for m in backlog)
    preferred = sorted(cats, key=lambda c: counts[c])[:4]
    avoid = [m["claim"] for m in backlog] + [h["claim"] for h in history if h.get("claim")]
    prompt = prompts.generate(n, cats, preferred, round(cfg["content"]["fact_ratio"] * 100), avoid, seed_claim)
    out = claude_cli.run(prompt, schemas.CANDIDATES, timeout=GENERATE_TIMEOUT, max_turns=4)
    return out["candidates"]


def vet(cfg: dict, candidate: dict, history: list[dict], others: list[dict]) -> tuple[dict | None, dict]:
    """Return (approved myth or None, review log)."""
    review = {"claim": candidate["claim"]}
    try:
        checked = claude_cli.run(prompts.research(candidate), schemas.RESEARCH, web=True, timeout=RESEARCH_TIMEOUT)
        review["research"] = checked["reason"]
        if not checked["keep"]:
            return None, {**review, "rejected_by": "research"}
        myth = checked["myth"]
        problems = myth_rules.validate(myth, cfg, history, others, datetime.now(timezone.utc).year)
        if problems:
            return None, {**review, "rejected_by": "local checks", "problems": problems}
        verdict = claude_cli.run(prompts.adversarial(myth), schemas.ADVERSARIAL, web=True, timeout=REVIEW_TIMEOUT)
        review["adversarial"] = verdict
        if verdict["reject"] or verdict["exclusion_hit"]:
            return None, {**review, "rejected_by": "adversarial"}
    except claude_cli.ClaudeError as e:
        return None, {**review, "rejected_by": "error", "error": str(e)}
    approved = {**myth, "id": myth_id(myth["claim"]), "approved_at": datetime.now(timezone.utc).isoformat(),
                "review": {"research": review["research"], "adversarial": verdict["reason"],
                           "minor_points": verdict["disputed_points"]}}
    return approved, {**review, "approved": True}


def refill(cfg: dict, budget_minutes: float, target: int | None = None) -> dict:
    """Top the backlog up towards `target`, saving after every approval. Stops when the time budget runs out."""
    deadline = time.monotonic() + budget_minutes * 60
    target = target or cfg["content"]["backlog_target"]
    history, stats = state.load_history(), {"approved": 0, "rejected": 0, "reviews": []}
    while time.monotonic() < deadline - MIN_MINUTES_FOR_BATCH * 60:
        backlog = state.load_backlog()
        if len(backlog) >= target:
            break
        n = min(cfg["content"]["candidates_per_call"], target - len(backlog) + 2)
        try:
            candidates = generate(cfg, n, backlog, history)
        except claude_cli.ClaudeError as e:
            stats["reviews"].append({"rejected_by": "generation", "error": str(e)})
            break
        with ThreadPoolExecutor(cfg["content"]["refill_workers"]) as pool:
            futures = [pool.submit(vet, cfg, c, history, backlog) for c in candidates]
            for fut in as_completed(futures):
                myth, review = fut.result()
                stats["reviews"].append(review)
                current = state.load_backlog()
                if myth and not myth_rules.duplicate_reason(myth, current, cfg):
                    state.save_backlog(current + [myth])
                    stats["approved"] += 1
                    log.info("approved: %s", myth["claim"])
                else:
                    stats["rejected"] += 1
                    log.info("rejected: %s (%s)", review["claim"], review.get("rejected_by", "duplicate"))
    stats["backlog_size"] = len(state.load_backlog())
    return stats


def make_one(cfg: dict, seed_claim: str | None = None, attempts: int = 2) -> dict:
    """Generate and fully vet a single myth on the fly (empty backlog, or a dry-run with a chosen claim)."""
    history, backlog = state.load_history(), state.load_backlog()
    reasons = []
    for _ in range(attempts):
        n = 1 if seed_claim else 2
        for candidate in generate(cfg, n, backlog, history, seed_claim)[:n]:
            myth, review = vet(cfg, candidate, history, [] if seed_claim else backlog)
            if myth:
                return myth
            reasons.append(review)
    raise RuntimeError(f"could not produce an approved myth: {reasons}")
