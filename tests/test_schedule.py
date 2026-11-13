from datetime import date, datetime, timezone

from mythreels import schedule


def at(y, m, d, h, mi):
    return datetime(y, m, d, h, mi, tzinfo=timezone.utc)


def slots(cfg, now, history):
    return [s for _, s in schedule.due_slots(cfg, now, history)]


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
    assert slots(cfg, at(2026, 11, 12, 2, 50), []) == []


def test_current_slot_is_due(cfg):
    assert slots(cfg, at(2026, 11, 12, 14, 55), []) == [4]


def test_late_cron_run_still_counts_for_its_slot(cfg):
    assert slots(cfg, at(2026, 11, 12, 15, 40), []) == [4]


def test_catch_up_fills_missed_earlier_slot_first(cfg):
    # Day 20 (2026-12-01): slots 2 and 4 active; slot 2 was missed
    assert slots(cfg, at(2026, 12, 1, 14, 50), []) == [2, 4]


def test_published_and_pending_slots_are_not_due(cfg):
    history = [{"date_ist": "2026-12-01", "slot": 2, "status": "published"}]
    assert slots(cfg, at(2026, 12, 1, 14, 50), history) == [4]
    history = [{"date_ist": "2026-12-01", "slot": 2, "status": "pending"}]
    assert slots(cfg, at(2026, 12, 1, 14, 50), history) == [4]


def test_failed_slot_is_retried_by_catch_up(cfg):
    history = [{"date_ist": "2026-12-01", "slot": 2, "status": "failed"}]
    assert slots(cfg, at(2026, 12, 1, 14, 50), history) == [2, 4]


def test_daily_cap_counts_publish_tests(cfg):
    # Day 39: slots 1, 2, 4 active, but 3 test reels already went out today
    history = [{"date_ist": "2026-12-20", "slot": "test", "status": "published"}] * 3
    assert slots(cfg, at(2026, 12, 20, 14, 50), history) == []


def test_cap_trims_catch_up(cfg):
    history = [{"date_ist": "2026-12-20", "slot": "test", "status": "published"}] * 2
    assert slots(cfg, at(2026, 12, 20, 14, 50), history) == [1]


def test_before_start_date_nothing_is_due(cfg):
    assert slots(cfg, at(2026, 11, 10, 14, 50), []) == []


def test_slot_times_match_cron(cfg):
    hours = sorted({int(v.split(":")[0]) for v in cfg["schedule"]["slots_utc"].values()})
    minutes = {int(v.split(":")[1]) for v in cfg["schedule"]["slots_utc"].values()}
    assert hours == [2, 6, 10, 14] and minutes == {41}


def test_evening_slot_missed_before_ist_midnight_is_caught_up(cfg):
    # Day 1's slot 4 was 2026-11-12 14:41 UTC; GitHub ran at 18:34 UTC = 00:04 IST on the 13th
    assert schedule.due_slots(cfg, at(2026, 11, 12, 18, 34), []) == [(date(2026, 11, 12), 4)]


def test_caught_up_slot_is_not_repeated(cfg):
    history = [{"date_ist": "2026-11-12", "slot": 4, "status": "published"}]
    assert schedule.due_slots(cfg, at(2026, 11, 12, 18, 34), history) == []


def test_slots_older_than_catch_up_window_are_dropped(cfg):
    # 2026-11-12 14:41 UTC slot, run 21 h later: too late, and today's slot isn't due yet
    assert schedule.due_slots(cfg, at(2026, 11, 13, 11, 45), []) == []


def test_yesterday_and_today_both_due_in_order(cfg):
    now = at(2026, 11, 13, 14, 50)   # yesterday's 14:41 slot is 24h old -> dropped; today's is due
    assert schedule.due_slots(cfg, now, []) == [(date(2026, 11, 13), 4)]
    now = at(2026, 12, 2, 7, 0)      # day 21: yesterday's slot 4 (14:41 UTC) 16h ago + today's slot 2
    assert schedule.due_slots(cfg, now, []) == [(date(2026, 12, 1), 4), (date(2026, 12, 2), 2)]
