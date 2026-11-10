"""Slot, ramp and catch-up logic. Pure functions; all times are timezone-aware."""
from datetime import date, datetime, time, timedelta, timezone

OCCUPIED = ("published", "pending")


def ist_date(cfg: dict, now_utc: datetime) -> date:
    return (now_utc + timedelta(minutes=cfg["ist_offset_minutes"])).date()


def day_number(cfg: dict, today_ist: date) -> int:
    start = cfg["start_date"]
    start = start if isinstance(start, date) else date.fromisoformat(str(start))
    return (today_ist - start).days + 1


def active_slots(cfg: dict, day: int) -> list[int]:
    if day < 1:
        return []
    matching = [r for r in cfg["schedule"]["ramp"] if r["from_day"] <= day]
    slots = sorted(matching[-1]["slots"]) if matching else []
    return slots[: cfg["schedule"]["max_reels_per_day"]]


def slot_time_utc(cfg: dict, today_ist: date, slot: int) -> datetime:
    hh, mm = map(int, cfg["schedule"]["slots_utc"][slot].split(":"))
    candidate = datetime.combine(today_ist, time(hh, mm), tzinfo=timezone.utc)
    shift = (ist_date(cfg, candidate) - today_ist).days
    return candidate - timedelta(days=shift)


def published_today(history: list[dict], today_ist: date) -> list[dict]:
    return [h for h in history if h.get("date_ist") == today_ist.isoformat() and h.get("status") in OCCUPIED]


def due_slots(cfg: dict, now_utc: datetime, history: list[dict]) -> list[int]:
    """Active slots for today (IST) whose time has passed and that have no reel yet, earliest first."""
    today = ist_date(cfg, now_utc)
    done = published_today(history, today)
    taken = {h.get("slot") for h in done}
    remaining = cfg["schedule"]["max_reels_per_day"] - len(done)
    due = [s for s in active_slots(cfg, day_number(cfg, today))
           if s not in taken and slot_time_utc(cfg, today, s) <= now_utc]
    return due[: max(remaining, 0)]
