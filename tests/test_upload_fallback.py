from pathlib import Path
from types import SimpleNamespace

import pytest

from mythreels import post
from mythreels.instagram import PublishError


class FakeIG:
    def __init__(self, resumable_ok=True, hosted_ok=True):
        self.resumable_ok, self.hosted_ok, self.calls = resumable_ok, hosted_ok, []

    def create_reel_container(self, caption):
        self.calls.append("create")
        return "c1", "https://rupload.facebook.com/ig-api-upload/v27.0/c1"

    def upload(self, uri, mp4):
        self.calls.append("upload")
        if not self.resumable_ok:
            raise PublishError("ProcessingFailedError")

    def create_reel_container_from_url(self, caption, url):
        self.calls.append(f"from_url:{url}")
        return "c2"

    def wait_until_ready(self, container):
        self.calls.append(f"wait:{container}")
        if container == "c2" and not self.hosted_ok:
            raise PublishError("ERROR")


@pytest.fixture
def media(monkeypatch):
    events = []
    monkeypatch.setattr(post.media_host, "host", lambda mp4: events.append("host") or "https://raw/x.mp4")
    monkeypatch.setattr(post.media_host, "cleanup", lambda: events.append("cleanup"))
    return events


REEL = SimpleNamespace(caption="cap", mp4=Path("x.mp4"))


def test_resumable_upload_used_when_it_works(media):
    ig = FakeIG()
    assert post._upload(ig, REEL) == ("c1", False)
    assert media == []


def test_falls_back_to_hosted_url_when_resumable_fails(media):
    ig = FakeIG(resumable_ok=False)
    assert post._upload(ig, REEL) == ("c2", True)
    assert media == ["host"] and "from_url:https://raw/x.mp4" in ig.calls


def test_hosted_branch_is_cleaned_up_if_fallback_fails(media):
    ig = FakeIG(resumable_ok=False, hosted_ok=False)
    with pytest.raises(PublishError):
        post._upload(ig, REEL)
    assert media == ["host", "cleanup"]
