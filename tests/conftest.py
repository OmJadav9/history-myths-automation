import copy

import pytest

from mythreels.config import load_config


@pytest.fixture
def cfg():
    return copy.deepcopy(load_config())


PUBLISHERS = {"britannica.com": "Encyclopaedia Britannica", "natmus.dk": "National Museum of Denmark"}


def _source(url, i=0):
    publisher = next(v for k, v in PUBLISHERS.items() if k in url)
    return {"title": f"Source {i}", "url": url, "publisher": publisher}


def _beat(narration, key_line, *urls):
    return {
        "narration": narration,
        "key_line": key_line,
        "sources": [_source(u, i) for i, u in enumerate(urls)],
    }


@pytest.fixture
def myth():
    good = ("https://www.britannica.com/topic/Viking-people", "https://natmus.dk/historical-knowledge/vikings")
    return {
        "id": "vikings-wore-horned-helmets-1a2b",
        "claim": "Vikings wore horned helmets.",
        "verdict": "MYTH",
        "hook": "The most famous Viking look is fake",
        "summary": "No horned Viking-Age helmet has ever been found. The look comes from 19th-century opera costumes.",
        "category": "Medieval",
        "era": "Viking Age",
        "year": 900,
        "key_people": ["Carl Emil Doepler"],
        "event": "Viking helmets",
        "key_places": ["Scandinavia"],
        "image_search_terms": ["Viking helmet", "Gjermundbu helmet"],
        "hashtags": ["#history", "#vikings", "#mythbusting", "#didyouknow", "#historyfacts",
                     "#medieval", "#norse", "#facts"],
        "pronunciations": [{"word": "Gjermundbu", "say": "Yer-mund-boo"}],
        "verdict_sources": [_source(good[0]), _source(good[1])],
        "reality": [
            _beat("No horned Viking-Age helmet has ever been dug up.", "No horned helmets found", *good),
            _beat("The only near-complete Viking helmet is a plain iron cap.", "Plain iron caps", *good),
            _beat("Horned helmets in Denmark are about 2,900 years old.", "Bronze Age, not Vikings", *good),
        ],
        "origin": [
            _beat("In the 1870s, costume designer Carl Emil Doepler gave Wagner's singers horns.",
                  "Blame the opera", *good),
        ],
    }
