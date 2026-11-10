"""JSON schemas for every Claude pass and for an approved backlog entry."""
import copy

_STR = {"type": "string", "minLength": 1}
_SOURCE = {
    "type": "object",
    "properties": {"title": _STR, "url": {"type": "string", "pattern": "^https?://"}, "publisher": _STR},
    "required": ["title", "url", "publisher"],
    "additionalProperties": False,
}
_PLAIN_BEAT = {
    "type": "object",
    "properties": {"narration": _STR, "key_line": {"type": "string", "minLength": 1, "maxLength": 48}},
    "required": ["narration", "key_line"],
    "additionalProperties": False,
}
_SOURCED_BEAT = {
    "type": "object",
    "properties": {**_PLAIN_BEAT["properties"], "sources": {"type": "array", "items": _SOURCE}},
    "required": ["narration", "key_line", "sources"],
    "additionalProperties": False,
}

_MYTH_FIELDS = {
    "claim": {"type": "string", "minLength": 8, "maxLength": 90},
    "verdict": {"enum": ["MYTH", "FACT"]},
    "hook": {"type": "string", "minLength": 5, "maxLength": 70},
    "summary": _STR,
    "category": _STR,
    "era": _STR,
    "year": {"type": "integer"},
    "key_people": {"type": "array", "items": _STR},
    "event": _STR,
    "key_places": {"type": "array", "items": _STR},
    "image_search_terms": {"type": "array", "items": _STR, "minItems": 1, "maxItems": 5},
    "hashtags": {"type": "array", "items": {"type": "string", "pattern": "^#\\w+$"}, "maxItems": 10},
    "pronunciations": {
        "type": "array",
        "items": {"type": "object", "properties": {"word": _STR, "say": _STR},
                  "required": ["word", "say"], "additionalProperties": False},
    },
}
_REQUIRED = list(_MYTH_FIELDS) + ["reality", "origin"]


def _myth(beat: dict, extra: dict | None = None) -> dict:
    props = {**copy.deepcopy(_MYTH_FIELDS),
             "reality": {"type": "array", "items": beat, "minItems": 3, "maxItems": 5},
             "origin": {"type": "array", "items": beat, "minItems": 1, "maxItems": 2},
             **(extra or {})}
    return {"type": "object", "properties": props, "required": _REQUIRED + list(extra or {}),
            "additionalProperties": False}


CANDIDATES = {
    "type": "object",
    "properties": {"candidates": {"type": "array", "items": _myth(_PLAIN_BEAT)}},
    "required": ["candidates"],
    "additionalProperties": False,
}

RESEARCH = {
    "type": "object",
    "properties": {
        "keep": {"type": "boolean"},
        "reason": {"type": "string"},
        "myth": _myth(_SOURCED_BEAT, {"verdict_sources": {"type": "array", "items": _SOURCE}}),
    },
    "required": ["keep", "reason", "myth"],
    "additionalProperties": False,
}

ADVERSARIAL = {
    "type": "object",
    "properties": {
        "genuine_dispute": {"type": "boolean"},
        "exclusion_hit": {"type": "boolean"},
        "fixes_needed": {"type": "array", "items": _STR},
        "reason": _STR,
    },
    "required": ["genuine_dispute", "exclusion_hit", "fixes_needed", "reason"],
    "additionalProperties": False,
}

# A backlog entry: the researched myth plus bookkeeping fields.
APPROVED_MYTH = copy.deepcopy(RESEARCH["properties"]["myth"])
APPROVED_MYTH["properties"].update({"id": _STR, "approved_at": {"type": "string"}, "review": {"type": "object"}})
APPROVED_MYTH["required"] = APPROVED_MYTH["required"] + ["id"]
