"""Text-for-the-ear helpers: spoken years, pronunciations, and subtitle cue timing."""
import re
from dataclasses import dataclass

_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen " \
        "sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
_PLURAL_TENS = {"twenty": "twenties", "thirty": "thirties", "forty": "forties", "fifty": "fifties",
                "sixty": "sixties", "seventy": "seventies", "eighty": "eighties", "ninety": "nineties"}

_YEAR = re.compile(r"^(?P<pre>\W*)(?P<year>1\d{3}|20\d{2})(?P<s>'?s)?(?P<post>\W*)$")
_WORDISH = re.compile(r"[A-Za-z0-9]")


def _two_digits(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (f"-{_ONES[ones]}" if ones else "")


def year_to_words(year: int) -> str:
    if 2000 <= year <= 2009:
        return "two thousand" + (f" {_ONES[year - 2000]}" if year > 2000 else "")
    hi, lo = divmod(year, 100)
    if lo == 0:
        return f"{_two_digits(hi)} hundred"
    if lo < 10:
        return f"{_two_digits(hi)} oh {_ONES[lo]}"
    return f"{_two_digits(hi)} {_two_digits(lo)}"


def _decade_words(year: int) -> str:
    hi, lo = divmod(year, 100)
    if lo == 0:
        return f"{_two_digits(hi)} hundreds"
    words = _two_digits(lo)
    return f"{_two_digits(hi)} {_PLURAL_TENS.get(words, words + 's')}"


@dataclass(frozen=True)
class Token:
    text: str      # as shown on screen
    spoken: str    # as sent to TTS (may be several words)


def _speak(token: str, pron: dict[str, str]) -> str:
    m = _YEAR.match(token)
    if m:
        year = int(m["year"])
        words = _decade_words(year) if m["s"] else year_to_words(year)
        return f"{m['pre']}{words}{m['post']}"
    core = re.sub(r"^\W+|\W+$", "", token)
    say = pron.get(core.lower())
    return token.replace(core, say) if say else token


def tokenize(text: str, pronunciations: dict[str, str]) -> list[Token]:
    pron = {k.lower(): v for k, v in pronunciations.items()}
    return [Token(t, _speak(t, pron)) for t in text.split()]


def spoken_text(tokens: list[Token]) -> str:
    return " ".join(t.spoken for t in tokens)


def _word_times(tokens: list[Token], boundaries: list[tuple], total: float) -> list[tuple[float, float]]:
    """(start, end) per token. Uses TTS word boundaries when they line up, else proportional timing."""
    spoken_counts = [sum(bool(_WORDISH.search(w)) for w in t.spoken.split()) for t in tokens]
    if boundaries and sum(spoken_counts) == len(boundaries):
        times, i = [], 0
        for n in spoken_counts:
            if n == 0:
                at = boundaries[min(i, len(boundaries) - 1)][1]
                times.append((at, at))
                continue
            times.append((boundaries[i][1], boundaries[i + n - 1][2]))
            i += n
        return times
    weights = [max(len(t.spoken), 1) for t in tokens]
    unit, pos, times = total / sum(weights), 0.0, []
    for w in weights:
        times.append((pos, pos + w * unit))
        pos += w * unit
    return times


def subtitle_cues(tokens: list[Token], boundaries: list[tuple], total: float, max_words: int = 3) -> list[dict]:
    """Group on-screen words into cues of up to max_words, breaking after punctuation."""
    times = _word_times(tokens, boundaries, total)
    cues, group = [], []
    for tok, span in zip(tokens, times):
        group.append((tok.text, span))
        if len(group) >= max_words or re.search(r"[.,;:!?]$", tok.text):
            cues.append(group)
            group = []
    if group:
        cues.append(group)
    return [{"text": " ".join(w for w, _ in g), "start": g[0][1][0], "end": g[-1][1][1]} for g in cues]


def split_sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def sentence_cues(sentences: list[str], spans: list[tuple[float, float]]) -> list[dict]:
    return [{"text": s, "start": a, "end": b} for s, (a, b) in zip(sentences, spans)]
