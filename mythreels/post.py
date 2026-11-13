"""One posting run: reconcile -> due slots (catch-up first) -> pick -> build -> validate -> publish -> commit."""
import json
import logging
import os
import subprocess
import time
from datetime import date, datetime, timezone

import requests

from mythreels import build, claude_cli, issues, media_host, myth_rules, research, schedule, state, tts
from mythreels.config import BACKLOG_FILE, HISTORY_FILE, OUTPUT_DIR
from mythreels.instagram import AuthError, Instagram, PublishError

log = logging.getLogger(__name__)
CAPTION_HEAD = 60
EXPECTED_FAILURES = (subprocess.CalledProcessError, subprocess.TimeoutExpired, requests.RequestException,
                     claude_cli.ClaudeError, PublishError, tts.TTSFailed, RuntimeError, OSError)


class ValidationFailed(RuntimeError):
    pass


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise AuthError(f"secret {name} is not set")
    return value


def _commit(message: str) -> None:
    if os.environ.get("GITHUB_ACTIONS") or os.environ.get("MYTH_COMMIT_STATE"):
        state.commit_and_push(message, [HISTORY_FILE, BACKLOG_FILE])


def _drop_from_backlog(myth_ids: set[str]) -> None:
    state.save_backlog([m for m in state.load_backlog() if m["id"] not in myth_ids])


def reconcile(ig: Instagram) -> None:
    """Resolve records left 'pending' by a crash between media_publish and the state commit."""
    history = state.load_history()
    pending = [h for h in history if h.get("status") == "pending"]
    if not pending:
        return
    recent = ig.recent_media()
    for rec in pending:
        try:
            code = ig.status(rec["container_id"])
        except PublishError:
            code = "UNKNOWN"
        match = next((m for m in recent if (m.get("caption") or "").startswith(rec["caption_head"])), None)
        if code == "PUBLISHED" or match:
            history = state.upsert(history, {**rec, "status": "published", "reconciled": True,
                                             "media_id": (match or {}).get("id", rec.get("media_id"))})
            _drop_from_backlog({rec["myth_id"]})
        else:
            history = state.upsert(history, {**rec, "status": "failed", "error": f"container left {code}"})
    state.save_history(history)
    _commit("state: reconcile pending reels")


def _record(myth: dict, run_key: str, today: str, slot, reel: build.Reel, **extra) -> dict:
    return {"run_key": run_key, "date_ist": today, "slot": slot, "myth_id": myth["id"], "claim": myth["claim"],
            "event": myth["event"], "key_people": myth["key_people"], "category": myth["category"],
            "verdict": myth["verdict"], "caption_head": reel.caption[:CAPTION_HEAD], "voice_engine": reel.engine,
            "render_seconds": round(reel.render_seconds, 1),
            "duration_seconds": round(reel.props["durationInFrames"] / reel.props["fps"], 1), **extra}


def _choose_myth(cfg: dict, today) -> dict:
    myth = myth_rules.pick_next(state.load_backlog(), state.load_history(), today, cfg)
    if myth:
        return myth
    log.warning("no eligible approved myth in the backlog; generating one on the fly")
    return research.make_one(cfg)


def _upload(ig: Instagram, reel: build.Reel) -> tuple[str, bool]:
    """Resumable upload first; if Meta rejects it, host the MP4 on the media branch and let Instagram fetch it.
    Returns (FINISHED container id, whether the media branch was used and needs cleanup)."""
    try:
        container, upload_uri = ig.create_reel_container(reel.caption)
        ig.upload(upload_uri, reel.mp4)
        ig.wait_until_ready(container)
        return container, False
    except PublishError as e:
        log.warning("resumable upload failed (%s); falling back to a hosted video_url", e)
    url = media_host.host(reel.mp4)
    try:
        container = ig.create_reel_container_from_url(reel.caption, url)
        ig.wait_until_ready(container)
    except Exception:
        media_host.cleanup()
        raise
    return container, True


def post_slot(cfg: dict, ig: Instagram, today: date, slot) -> None:
    """`today` is the IST date the slot belongs to (yesterday's when catching up after midnight)."""
    run_key = f"{today.isoformat()}-{slot}"
    if slot == "test":
        run_key += datetime.now(timezone.utc).strftime("-%H%M%S")
    myth = _choose_myth(cfg, today)
    log.info("slot %s: %s", slot, myth["claim"])
    reel = build.build_reel(myth, cfg, OUTPUT_DIR / run_key)
    if reel.problems:
        raise ValidationFailed("reel failed validation:\n- " + "\n- ".join(reel.problems))

    hosted = False
    try:
        container, hosted = _upload(ig, reel)
        pending = _record(myth, run_key, today.isoformat(), slot, reel, status="pending", container_id=container)
        state.save_history(state.upsert(state.load_history(), pending))
        _commit(f"state: publishing slot {slot}")
        media_id = ig.publish(container)
    finally:
        if hosted:
            media_host.cleanup()
    done = {**pending, "status": "published", "media_id": media_id,
            "published_at": datetime.now(timezone.utc).isoformat()}
    state.save_history(state.upsert(state.load_history(), done))
    _drop_from_backlog({myth["id"]})
    _commit(f"state: published slot {slot} ({myth['id']})")
    log.info("published %s as media %s (voice: %s, render %.0fs)", myth["id"], media_id, reel.engine, reel.render_seconds)


def _fail_slot(cfg: dict, day: date, slot, err: Exception) -> None:
    today = day.isoformat()
    record = {"run_key": f"{today}-{slot}", "date_ist": today, "slot": slot, "status": "failed",
              "error": str(err)[:500], "failed_at": datetime.now(timezone.utc).isoformat()}
    history = state.load_history()
    if not any(h.get("run_key") == record["run_key"] and h.get("status") == "published" for h in history):
        state.save_history(state.upsert(history, record))
        _commit(f"state: slot {slot} failed")
    issues.open_issue(f"{type(err).__name__} while posting", f"Slot {slot} was skipped.\n\n```\n{err}\n```")


def _warn_if_backlog_low(cfg: dict) -> None:
    n = len(state.load_backlog())
    if n < cfg["content"]["backlog_warn_below"]:
        issues.open_issue("Myth backlog running low",
                          f"Only {n} approved myths left (warning threshold {cfg['content']['backlog_warn_below']}). "
                          "Run the 'Refill myth backlog' workflow manually, or wait for Sunday's run.")


def run(cfg: dict, mode: str) -> int:
    """mode: 'schedule' (cron) or 'publish-test' (one real reel now, still within the daily cap)."""
    try:
        ig = Instagram(cfg, _env("IG_ACCESS_TOKEN"), _env("IG_USER_ID"))
        reconcile(ig)
        now = datetime.now(timezone.utc)
        history = state.load_history()
        if mode == "publish-test":
            done = schedule.published_today(history, schedule.ist_date(cfg, now))
            slots = [(schedule.ist_date(cfg, now), "test")] if len(done) < cfg["schedule"]["max_reels_per_day"] else []
        else:
            slots = schedule.due_slots(cfg, now, history)
        if not slots:
            log.info("nothing due right now")
            return 0
        started, failed = time.monotonic(), 0
        for day, slot in slots:
            if time.monotonic() - started > cfg["schedule"]["run_budget_minutes"] * 60:
                log.warning("run budget used up; slot %s will be caught up by the next run", slot)
                break
            try:
                post_slot(cfg, ig, day, slot)
            except AuthError:
                raise
            except EXPECTED_FAILURES as e:
                log.error("slot %s failed: %s", slot, e)
                _fail_slot(cfg, day, slot, e)
                failed += 1
        _warn_if_backlog_low(cfg)
        return 1 if failed else 0
    except AuthError as e:
        issues.open_issue("Instagram auth error", f"The run was skipped.\n\n{e}\n\nCheck IG_ACCESS_TOKEN / IG_USER_ID "
                          "and that the system user still has the Instagram account assigned.")
        return 1


def dry_run(cfg: dict, claim: str | None) -> int:
    """Render one reel locally (or as a workflow artifact) with its research log. Never posts, never commits."""
    if claim:
        myth = research.make_one(cfg, seed_claim=claim)
    else:
        today = schedule.ist_date(cfg, datetime.now(timezone.utc))
        myth = myth_rules.pick_next(state.load_backlog(), state.load_history(), today, cfg) or research.make_one(cfg)
    out = OUTPUT_DIR / "dry-run" / myth["id"]
    reel = build.build_reel(myth, cfg, out, keep_assets=True)
    (out / "research_log.json").write_text(json.dumps(reel.myth, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "caption.txt").write_text(reel.caption, encoding="utf-8")
    report = {"mp4": str(reel.mp4), "voice_engine": reel.engine, "render_seconds": round(reel.render_seconds, 1),
              "duration_seconds": round(reel.props["durationInFrames"] / reel.props["fps"], 1),
              "images": reel.credits, "problems": reel.problems}
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("dry run: %s", json.dumps(report, ensure_ascii=False))
    return 1 if reel.problems else 0
