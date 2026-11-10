from mythreels.caption import build_caption
from scripts.check_secrets import find_secrets

CREDITS = [{"title": "Gjermundbu helmet", "author": "Unknown", "license": "Public domain"},
           {"title": "Veksø helmets", "author": "Natmus", "license": "CC0"}]


def test_caption_contains_required_parts(myth):
    text = build_caption(myth, CREDITS)
    assert text.startswith(myth["hook"])
    assert myth["summary"] in text
    assert "Sources: Encyclopaedia Britannica, National Museum of Denmark" in text
    assert "Images: Gjermundbu helmet by Unknown, public domain, via Wikimedia Commons" in text
    assert "Veksø helmets by Natmus, CC0, via Wikimedia Commons" in text
    assert "Comment a myth you want busted next" in text
    assert text.count("#") <= 30 and len(text) <= 2200


def test_caption_caps_hashtags_and_length(myth):
    many = {**myth, "hashtags": [f"#tag{i}" for i in range(50)], "summary": "word " * 600}
    text = build_caption(many, CREDITS * 40)
    assert text.count("#") <= 10
    assert len(text) <= 2200
    assert "Comment a myth you want busted next" in text


def test_secret_scanner_flags_tokens():
    meta = "EAA" + "B" * 60
    assert find_secrets(f"token = {meta}")
    assert find_secrets("sk-ant-oat01-" + "x" * 40)
    assert find_secrets("ghp_" + "a" * 36)
    assert find_secrets('IG_APP_SECRET="' + "0123456789abcdef" * 2 + '"')


def test_secret_scanner_ignores_normal_text():
    assert find_secrets("Vikings wore plain iron helmets in 900 AD. sha 0123456789abcdef") == []
    assert find_secrets("gh secret set IG_ACCESS_TOKEN --repo OmJadav9/history-myths-automation") == []


def test_sources_ranked_by_how_many_claims_they_back(myth):
    from mythreels.caption import source_names
    weak = {"title": "w", "url": "https://blog.oup.com/x", "publisher": "OUPblog"}
    myth = {**myth, "verdict_sources": [weak] + myth["verdict_sources"]}
    assert source_names(myth)[:2] == ["Encyclopaedia Britannica", "National Museum of Denmark"]
    assert source_names(myth)[2] == "OUPblog"
