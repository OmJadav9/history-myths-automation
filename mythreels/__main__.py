"""python -m mythreels <command>  (see README.md)"""
import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

from mythreels import issues, post, research, schedule, state
from mythreels.config import BACKLOG_FILE, OUTPUT_DIR, load_config

SAMPLE_LINE = "Myth or fact? Napoleon was unusually short. It's a myth: in 1821 he measured about five foot seven."
VOICES = ["en-US-AndrewNeural", "en-US-ChristopherNeural", "en-GB-RyanNeural", "en-US-BrianNeural",
          "en-AU-WilliamNeural", "en-IN-PrabhatNeural"]


def cmd_due(cfg: dict, _args) -> int:
    slots = schedule.due_slots(cfg, datetime.now(timezone.utc), state.load_history())
    logging.info("due slots: %s", slots or "none")
    if out := os.environ.get("GITHUB_OUTPUT"):
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"due={'true' if slots else 'false'}\n")
    return 0


def cmd_refill(cfg: dict, args) -> int:
    stats = research.refill(cfg, args.budget_minutes, args.target)
    logging.info("refill: %d approved, %d rejected, backlog now %d", stats["approved"], stats["rejected"],
                 stats["backlog_size"])
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "refill_report.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.commit:
        state.commit_and_push(f"backlog: +{stats['approved']} approved myths", [BACKLOG_FILE])
    if stats["backlog_size"] < cfg["content"]["backlog_warn_below"]:
        issues.open_issue("Myth backlog running low", f"Backlog has {stats['backlog_size']} approved myths after refill.")
    return 0


def cmd_voices(cfg: dict, _args) -> int:
    import edge_tts

    out = OUTPUT_DIR / "voices"
    out.mkdir(parents=True, exist_ok=True)
    for v in VOICES:
        asyncio.run(edge_tts.Communicate(SAMPLE_LINE, v, rate=cfg["voice"]["edge_rate"]).save(str(out / f"{v}.mp3")))
        logging.info("wrote %s", out / f"{v}.mp3")
    return 0


def cmd_ig_check(cfg: dict, _args) -> int:
    ig = post.Instagram(cfg, post._env("IG_ACCESS_TOKEN"), post._env("IG_USER_ID"))
    logging.info("token works for %s", ig.account())
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="mythreels")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("due", help="print whether any posting slot is due now")
    pp = sub.add_parser("post", help="post due reels (or one test reel)")
    pp.add_argument("--mode", choices=["schedule", "publish-test"], default="schedule")
    dp = sub.add_parser("dry-run", help="render one reel + research log into output/dry-run, no posting")
    dp.add_argument("--claim", help="research this exact claim instead of taking one from the backlog")
    rp = sub.add_parser("refill", help="research and approve myths into the backlog")
    rp.add_argument("--budget-minutes", type=float, default=None)
    rp.add_argument("--target", type=int, default=None)
    rp.add_argument("--commit", action="store_true", help="commit and push the backlog when done")
    sub.add_parser("voices", help="render a sample line with several edge-tts voices")
    sub.add_parser("ig-check", help="check the Instagram token and IG_USER_ID")
    ip = sub.add_parser("issue", help="open a failure issue (used by the workflow's failure step)")
    ip.add_argument("kind")
    ip.add_argument("details")
    args = p.parse_args()

    cfg = load_config()
    if args.cmd == "refill" and args.budget_minutes is None:
        args.budget_minutes = cfg["content"]["refill_budget_minutes"]
    handlers = {
        "due": cmd_due, "refill": cmd_refill, "voices": cmd_voices, "ig-check": cmd_ig_check,
        "post": lambda c, a: post.run(c, a.mode),
        "dry-run": lambda c, a: post.dry_run(c, a.claim),
        "issue": lambda c, a: issues.open_issue(a.kind, a.details) or 0,
    }
    return handlers[args.cmd](cfg, args)


if __name__ == "__main__":
    sys.exit(main())
