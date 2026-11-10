import pytest

from mythreels import narration


@pytest.mark.parametrize("year,words", [
    (1789, "seventeen eighty-nine"),
    (1066, "ten sixty-six"),
    (1900, "nineteen hundred"),
    (1905, "nineteen oh five"),
    (1932, "nineteen thirty-two"),
    (2000, "two thousand"),
    (2008, "two thousand eight"),
    (1010, "ten ten"),
])
def test_year_to_words(year, words):
    assert narration.year_to_words(year) == words


def test_spoken_form_converts_years_decades_and_names():
    tokens = narration.tokenize("In 1765, Rousseau wrote it. By the 1870s it spread.", {"Rousseau": "Roo-so"})
    spoken = " ".join(t.spoken for t in tokens)
    assert spoken == "In seventeen sixty-five, Roo-so wrote it. By the eighteen seventies it spread."


def test_non_year_numbers_are_left_alone():
    tokens = narration.tokenize("It is 300 metres and 5,000 years old.", {})
    assert " ".join(t.spoken for t in tokens) == "It is 300 metres and 5,000 years old."


def test_pronunciation_is_case_insensitive_and_keeps_punctuation():
    tokens = narration.tokenize("ask doepler.", {"Doepler": "Dupp-ler"})
    assert tokens[-1].spoken == "Dupp-ler."
    assert tokens[-1].text == "doepler."


def test_subtitles_use_word_timings_and_show_original_text():
    tokens = narration.tokenize("In 1765, he left.", {})
    # spoken words: In seventeen sixty-five he left
    boundaries = [("In", 0.0, 0.2), ("seventeen", 0.2, 0.6), ("sixty-five", 0.6, 1.0),
                  ("he", 1.1, 1.2), ("left", 1.2, 1.5)]
    cues = narration.subtitle_cues(tokens, boundaries, total=1.6, max_words=3)
    assert [c["text"] for c in cues] == ["In 1765,", "he left."]
    assert cues[0]["start"] == 0.0 and cues[1]["start"] == pytest.approx(1.1)
    assert cues[-1]["end"] == pytest.approx(1.5)


def test_subtitles_split_at_three_words():
    tokens = narration.tokenize("one two three four five", {})
    b = [(w, i * 0.5, i * 0.5 + 0.4) for i, w in enumerate("one two three four five".split())]
    cues = narration.subtitle_cues(tokens, b, total=2.5, max_words=3)
    assert [c["text"] for c in cues] == ["one two three", "four five"]


def test_subtitles_fall_back_to_proportional_timing_on_mismatch():
    tokens = narration.tokenize("alpha bravo gamma delta", {})  # equal lengths -> equal time each
    cues = narration.subtitle_cues(tokens, [("alpha", 0, 0.5)], total=4.0, max_words=2)
    assert [c["text"] for c in cues] == ["alpha bravo", "gamma delta"]
    assert cues[0]["start"] == 0.0 and cues[1]["start"] == pytest.approx(2.0)
    assert cues[1]["end"] == pytest.approx(4.0)


def test_sentence_cues_for_piper():
    cues = narration.sentence_cues(["First one.", "Second."], [(0.0, 1.2), (1.4, 2.0)])
    assert cues == [{"text": "First one.", "start": 0.0, "end": 1.2},
                    {"text": "Second.", "start": 1.4, "end": 2.0}]


def test_split_sentences():
    assert narration.split_sentences("It's a myth. Really? Yes!") == ["It's a myth.", "Really?", "Yes!"]
