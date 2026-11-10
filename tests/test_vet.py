import pytest

from mythreels import research, schemas


def review(dispute=False, exclusion=False, fixes=(), minor=()):
    return {"genuine_dispute": dispute, "exclusion_hit": exclusion, "blocking_fixes": list(fixes),
            "minor_fixes": list(minor), "reason": "r"}


@pytest.fixture
def fake_claude(monkeypatch, myth):
    """Queue of responses per schema; records which prompts were sent."""
    plain = {k: v for k, v in myth.items() if k not in ("id",)}
    queues = {"research": [], "review": []}
    calls = []

    def run(prompt, schema, **_):
        kind = "review" if schema is schemas.ADVERSARIAL else "research"
        calls.append("revise" if "requires the fixes" in prompt else kind)
        return queues[kind].pop(0)

    monkeypatch.setattr(research.claude_cli, "run", run)
    good = {"keep": True, "reason": "ok", "myth": plain}
    return queues, calls, good


def test_clean_review_approves(fake_claude, myth, cfg):
    queues, calls, good = fake_claude
    queues["research"] = [good]
    queues["review"] = [review()]
    approved, log = research.vet(cfg, myth, [], [])
    assert approved and approved["id"].startswith("vikings-wore-horned-helmets")
    assert calls == ["research", "review"]


def test_fixable_points_get_one_revision_then_approve(fake_claude, myth, cfg):
    queues, calls, good = fake_claude
    queues["research"] = [good, good]
    queues["review"] = [review(fixes=["soften the hook"]), review()]
    approved, _ = research.vet(cfg, myth, [], [])
    assert approved and approved["review"]["fixes_applied"] == ["soften the hook"]
    assert calls == ["research", "review", "revise", "review"]


def test_minor_points_alone_approve_without_revision(fake_claude, myth, cfg):
    queues, calls, good = fake_claude
    queues["research"] = [good]
    queues["review"] = [review(minor=["swap syndicated URL"])]
    approved, _ = research.vet(cfg, myth, [], [])
    assert approved["review"]["open_minor_points"] == ["swap syndicated URL"]
    assert calls == ["research", "review"]


def test_two_revisions_allowed_then_reject(fake_claude, myth, cfg):
    queues, calls, good = fake_claude
    queues["research"] = [good, good, good]
    queues["review"] = [review(fixes=["a"]), review(fixes=["b"]), review(fixes=["c"])]
    approved, log = research.vet(cfg, myth, [], [])
    assert approved is None and "blocking fixes still needed" in log["rejected_by"]
    assert calls == ["research", "review", "revise", "review", "revise", "review"]


@pytest.mark.parametrize("verdict", [review(dispute=True), review(exclusion=True)])
def test_dispute_or_exclusion_rejects_without_revision(fake_claude, myth, cfg, verdict):
    queues, calls, good = fake_claude
    queues["research"] = [good]
    queues["review"] = [verdict]
    approved, log = research.vet(cfg, myth, [], [])
    assert approved is None and log["rejected_by"] == "adversarial"
    assert "revise" not in calls


def test_research_drop_rejects_before_review(fake_claude, myth, cfg):
    queues, calls, good = fake_claude
    queues["research"] = [{**good, "keep": False}]
    approved, log = research.vet(cfg, myth, [], [])
    assert approved is None and log["rejected_by"] == "research" and calls == ["research"]
