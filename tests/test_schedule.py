from datetime import datetime, timezone

from mythreels import schedule


def at(y, m, d, h, mi):
    return datetime(y, m, d, h, mi, tzinfo=timezone.utc)


def test_day_number_uses_ist_date(cfg):
    # 2026-11-11 20:00 UTC is 2026-11-12 01:30 IST, the start date -> day 1
    assert schedule.day_number(cfg, schedule.ist_date(cfg, at(2026, 11, 11, 20, 0))) == 1


def test_ramp_slots(cfg):
    assert schedule.active_slots(cfg, 0) == []
    assert schedule.active_slots(cfg, 1) == [4]
    assert schedule.active_slots(cfg, 14) == [4]
    assert schedule.active_slots(cfg, 15) == [2, 4]
    assert schedule.active_slots(cfg, 30) == [2, 4]
    assert schedule.active_slots(cfg, 31) == [1, 2, 4]
    assert schedule.active_slots(cfg, 400) == [1, 2, 4]


def test_hard_cap_limits_active_slots(cfg):
    cfg["schedule"]["max_reels_per_day"] = 1
    assert schedule.active_slots(cfg, 31) == [1]


def test_inactive_slot_exits_with_nothing_due(cfg):
    # Day 1: only slot 4 is active; a run at slot 1's time has nothing to do
    assert schedule.due_slots(cfg, at(2026, 11, 12, 2, 50), []) == []


def test_current_slot_is_due(cfg):
    assert schedule.due_slots(cfg, at(2026, 11, 12, 14, 55), []) == [4]


def test_late_cron_run_still_counts_for_its_slot(cfg):
    assert schedule.due_slots(cfg, at(2026, 11, 12, 15, 40), []) == [4]


def test_catch_up_fills_missed_earlier_slot_first(cfg):
    # Day 20 (2026-12-01): slots 2 and 4 active; slot 2 was missed
    assert schedule.due_slots(cfg, at(2026, 12, 1, 14, 50), []) == [2, 4]


def test_published_and_pending_slots_are_not_due(cfg):
    history = [{"date_ist": "2026-12-01", "slot": 2, "status": "published"}]
    assert schedule.due_slots(cfg, at(2026, 12, 1, 14, 50), history) == [4]
    history = [{"date_ist": "2026-12-01", "slot": 2, "status": "pending"}]
    assert schedule.due_slots(cfg, at(2026, 12, 1, 14, 50), history) == [4]


def test_failed_slot_is_retried_by_catch_up(cfg):
    history = [{"date_ist": "2026-12-01", "slot": 2, "status": "failed"}]
    assert schedule.due_slots(cfg, at(2026, 12, 1, 14, 50), history) == [2, 4]


def test_daily_cap_counts_publish_tests(cfg):
    # Day 39: slots 1, 2, 4 active, but 3 test reels already went out today
    history = [{"date_ist": "2026-12-20", "slot": "test", "status": "published"}] * 3
    assert schedule.due_slots(cfg, at(2026, 12, 20, 14, 50), history) == []


def test_cap_trims_catch_up(cfg):
    history = [{"date_ist": "2026-12-20", "slot": "test", "status": "published"}] * 2
    assert schedule.due_slots(cfg, at(2026, 12, 20, 14, 50), history) == [1]


def test_before_start_date_nothing_is_due(cfg):
    assert schedule.due_slots(cfg, at(2026, 11, 10, 14, 50), []) == []


def test_slot_times_match_cron(cfg):
    hours = sorted({int(v.split(":")[0]) for v in cfg["schedule"]["slots_utc"].values()})
    minutes = {int(v.split(":")[1]) for v in cfg["schedule"]["slots_utc"].values()}
    assert hours == [2, 6, 10, 14] and minutes == {41}
