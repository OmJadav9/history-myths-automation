from mythreels import visuals


def _page(code, short, mime="image/jpeg", width=2000, cats="Viking Age", title="File:X.jpg", name="Helmet"):
    meta = {"License": {"value": code}, "LicenseShortName": {"value": short}, "Categories": {"value": cats},
            "ObjectName": {"value": name}, "Artist": {"value": "<a href='x'>Anon</a>"}}
    return {"title": title, "imageinfo": [{"extmetadata": meta, "mime": mime, "width": width,
                                           "url": "https://u/x.jpg", "thumburl": "https://u/t.jpg"}]}


def test_only_public_domain_and_cc0_are_accepted():
    assert visuals._candidate(_page("pd", "Public domain"))["license"] == "Public domain"
    assert visuals._candidate(_page("cc0", "CC0"))["license"] == "CC0"
    assert visuals._candidate(_page("cc-by-sa-4.0", "CC BY-SA 4.0")) is None
    assert visuals._candidate(_page("cc-by-2.0", "CC BY 2.0")) is None


def test_rejects_small_unsupported_and_blocked_images():
    assert visuals._candidate(_page("pd", "Public domain", width=300)) is None
    assert visuals._candidate(_page("pd", "Public domain", mime="image/tiff")) is None
    assert visuals._candidate(_page("pd", "Public domain", cats="Living people|Portraits")) is None
    assert visuals._candidate(_page("pd", "Public domain", cats="Massacre paintings")) is None


def test_credit_fields_are_cleaned():
    c = visuals._candidate(_page("pd", "Public domain", name='Arrival of Rurik label QS:Len,"x"'))
    assert c["title"] == "Arrival of Rurik" and c["author"] == "Anon" and c["url"] == "https://u/t.jpg"


def test_wikidata_title_markup_is_stripped():
    c = visuals._candidate(_page("pd", "Public domain", name='Cleopatra title QS:P1476,en:"Cleopatra "'))
    assert c["title"] == "Cleopatra"
