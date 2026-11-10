from datetime import date

import jsonschema
import pytest

from mythreels import myth_rules
from mythreels.schemas import APPROVED_MYTH


def test_valid_myth_matches_schema(myth):
    jsonschema.validate(myth, APPROVED_MYTH)


def test_schema_rejects_missing_sources(myth):
    del myth["reality"][0]["sources"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(myth, APPROVED_MYTH)


def test_schema_rejects_bad_verdict(myth):
    myth["verdict"] = "MAYBE"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(myth, APPROVED_MYTH)


def test_well_sourced_myth_has_no_source_problems(myth, cfg):
    assert myth_rules.source_problems(myth, cfg) == []


def test_single_domain_is_not_enough(myth, cfg):
    myth["reality"][1]["sources"] = [
        {"title": "a", "url": "https://www.britannica.com/a", "publisher": "x"},
        {"title": "b", "url": "https://kids.britannica.com/b", "publisher": "x"},
    ]
    assert len(myth_rules.source_problems(myth, cfg)) == 1


def test_wikipedia_and_blocked_sites_do_not_count(myth, cfg):
    myth["origin"][0]["sources"] = [
        {"title": "a", "url": "https://en.wikipedia.org/wiki/X", "publisher": "x"},
        {"title": "b", "url": "https://www.reddit.com/r/history", "publisher": "x"},
        {"title": "c", "url": "https://www.britannica.com/c", "publisher": "x"},
    ]
    assert len(myth_rules.source_problems(myth, cfg)) == 1


def test_verdict_needs_sources_too(myth, cfg):
    myth["verdict_sources"] = myth["verdict_sources"][:1]
    assert len(myth_rules.source_problems(myth, cfg)) == 1


def test_country_second_level_domains(cfg):
    assert myth_rules.domain_of("https://www.bbc.co.uk/history") == "bbc.co.uk"
    assert myth_rules.domain_of("https://history.ox.ac.uk/x") == "ox.ac.uk"
    assert myth_rules.domain_of("https://asi.nic.in/x") == "asi.nic.in"


def test_exclusion_hits_topic(myth, cfg):
    myth["claim"] = "The temple was built in a single night."
    assert myth_rules.exclusion_hits(myth, cfg) == ["temple"]


def test_exclusion_ignores_narration_and_partial_words(myth, cfg):
    myth["reality"][0]["narration"] = "Wagner's opera was about Norse gods."
    myth["claim"] = "Romans used a battering ram on every gate."
    assert myth_rules.exclusion_hits(myth, cfg) == []


def test_recent_events_are_rejected(myth, cfg):
    assert myth_rules.too_recent({**myth, "year": 2010}, cfg, 2026)
    assert not myth_rules.too_recent({**myth, "year": -900}, cfg, 2026)


def test_duplicate_claim_detected(myth, cfg):
    history = [{"claim": "The Vikings wore helmets with horns", "event": "x", "key_people": []}]
    assert myth_rules.duplicate_reason(myth, history, cfg)


def test_duplicate_event_detected(myth, cfg):
    history = [{"claim": "Something else entirely", "event": "Viking helmets", "key_people": []}]
    assert myth_rules.duplicate_reason(myth, history, cfg)


def test_distinct_myth_is_not_duplicate(myth, cfg):
    history = [{"claim": "Napoleon was very short", "event": "Napoleon's height", "key_people": ["Napoleon"]}]
    assert myth_rules.duplicate_reason(myth, history, cfg) is None


def test_validate_collects_all_problems(myth, cfg):
    bad = {**myth, "year": 2015, "claim": "The temple was built overnight."}
    problems = myth_rules.validate(bad, cfg, history=[], others=[], year_now=2026)
    assert any("recent" in p for p in problems)
    assert any("excluded" in p for p in problems)


def _entry(myth, **kw):
    return {**myth, **kw}


def test_pick_skips_person_on_cooldown_and_category_used_today(myth, cfg):
    today = date(2026, 12, 1)
    a = _entry(myth, id="a", key_people=["Napoleon"], category="Early Modern", claim="A")
    b = _entry(myth, id="b", key_people=["Einstein"], category="Medieval", claim="B")
    c = _entry(myth, id="c", key_people=["Marie Antoinette"], category="Early Modern", claim="C")
    history = [
        {"date_ist": "2026-11-25", "status": "published", "key_people": ["Napoleon"], "category": "Ancient World", "verdict": "MYTH"},
        {"date_ist": "2026-12-01", "status": "published", "key_people": ["Someone"], "category": "Medieval", "verdict": "MYTH"},
    ]
    assert myth_rules.pick_next([a, b, c], history, today, cfg)["id"] == "c"


def test_pick_allows_person_after_cooldown(myth, cfg):
    a = _entry(myth, id="a", key_people=["Napoleon"], category="Early Modern")
    history = [{"date_ist": "2026-10-01", "status": "published", "key_people": ["Napoleon"],
                "category": "Ancient World", "verdict": "MYTH"}]
    assert myth_rules.pick_next([a], history, date(2026, 12, 1), cfg)["id"] == "a"


def test_pick_prefers_fact_when_facts_are_underrepresented(myth, cfg):
    m = _entry(myth, id="m", verdict="MYTH", category="Medieval")
    f = _entry(myth, id="f", verdict="FACT", category="Medieval")
    history = [{"date_ist": "2026-11-20", "status": "published", "key_people": [], "category": "Medieval",
                "verdict": "MYTH"}] * 6
    assert myth_rules.pick_next([m, f], history, date(2026, 12, 1), cfg)["id"] == "f"


def test_pick_returns_none_when_nothing_eligible(myth, cfg):
    history = [{"date_ist": "2026-12-01", "status": "published", "key_people": [], "category": "Medieval",
                "verdict": "MYTH"}]
    assert myth_rules.pick_next([myth], history, date(2026, 12, 1), cfg) is None
